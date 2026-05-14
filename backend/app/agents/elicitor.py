"""Elicitor agent — extracts structured requirements from natural language via Q&A loop."""

import json
import logging
from datetime import datetime, timezone

from langgraph.types import interrupt

from app.config import settings
from app.models.requirements import (
    GapAnalysisResult,
    QuestionCategory,
    RequirementsDoc,
)
from app.models.state import FrankensteinState
from app.services.chroma_service import ChromaService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

CATEGORY_PRIORITY = ["Input/Output", "Process", "Data", "Edge Cases", "Quality Bar"]

# ── System prompts ───────────────────────────────────────────────────

GAP_ANALYSIS_SYSTEM = """\
You are an expert requirements analyst for AI agent systems. Your job is to evaluate how \
completely a user's natural language description addresses 5 key categories needed to build \
a working AI agent pipeline.

Categories and their required fields:

1. Input/Output: input_data_type, input_format, input_source, output_data_type, \
output_format, output_destination
2. Process: main_task_description, process_steps_count, decision_points, \
transformation_logic, sequencing_rules
3. Data: data_volume_estimate, data_frequency, data_sensitivity, \
external_data_sources, data_schema_known
4. Edge Cases: known_failure_modes, missing_data_handling, invalid_input_handling, \
timeout_behavior, partial_success_handling
5. Quality Bar: accuracy_requirement, latency_requirement, output_validation_method, \
success_criteria, acceptable_error_rate

Scoring rules:
- 1.0: All required fields clearly addressed with specific, usable values
- 0.7-0.99: Most fields addressed, minor ambiguities inferable from context
- 0.4-0.69: Some fields addressed but significant gaps remain
- 0.0-0.39: Category barely touched

Domain insights (from past builds, may be empty): {domain_insights}

Respond ONLY with valid JSON matching this exact schema:
{{
  "categories": [
    {{
      "name": "<category name>",
      "confidence": <float 0.0-1.0>,
      "addressed_fields": ["<field>", ...],
      "missing_fields": ["<field>", ...],
      "notes": "<1-2 sentence rationale>"
    }}
  ],
  "overall_quality": "<high|medium|low>"
}}"""

QUESTION_GEN_SYSTEM = """\
You are an expert requirements analyst conducting a structured interview to gather \
information needed to build an AI agent pipeline. Your questions must be specific, \
targeted, and immediately actionable. Do not ask general or open-ended questions.

You are building requirements in these gap categories: {gap_category_names}
Minimum questions per category: {min_questions}
This is round {current_round} of {max_rounds}.

Rules:
- Ask only about the missing fields identified in the gap analysis
- Questions must be specific enough that the user's answer directly fills a field
- Do not repeat questions from previous rounds
- Use plain business language — no technical jargon
- For round 2+, acknowledge what was already provided and ask only about remaining gaps

Previous questions asked (do not repeat): {previous_questions}

Respond ONLY with valid JSON:
{{
  "categories": [
    {{
      "name": "<category name>",
      "confidence": <current confidence float>,
      "questions": ["<question 1>", "<question 2>", ...]
    }}
  ]
}}
Only include categories that have gaps (confidence < 0.7)."""

ANSWER_EXTRACT_SYSTEM = """\
You are extracting structured requirement information from a user's conversational answer.
The user was answering these specific questions about building an AI agent:

Questions asked:
{questions_asked}

Extract the values for these fields from the user's answer:
{target_fields}

If the user did not address a field, use null for that field's value.
Do not infer or hallucinate — only extract explicitly stated information.

Respond ONLY with valid JSON:
{{
  "extracted_fields": {{
    "<field_name>": "<extracted value or null>",
    ...
  }},
  "coverage_notes": "<brief note on what was and wasn't answered>"
}}"""

ASSUMPTION_GEN_SYSTEM = """\
You are generating safe, conservative assumptions to fill in missing requirements \
for an AI agent pipeline. These assumptions will be flagged explicitly in the \
requirements document so the human can review them.

Make assumptions that:
- Are the simplest reasonable interpretation of the domain
- Err toward less risky defaults (e.g., assume human review is needed when uncertain)
- Are stated clearly so the user can confirm or correct them later

Respond ONLY with valid JSON:
{{
  "assumptions": [
    "<Assumption 1: e.g., 'Assuming input data arrives as a single file per run, not streaming'>",
    ...
  ]
}}"""

COMPILE_SYSTEM = """\
You are compiling a structured requirements document for an AI agent pipeline.
You will receive all information gathered from the user across multiple rounds of Q&A.
Your job is to organize this into a clean, complete RequirementsDoc.

Rules:
- Only include information that was explicitly provided or is a stated assumption
- process_steps must be ordered logically with correct depends_on references
- edge_cases must be specific and actionable (not generic)
- quality_criteria must be measurable
- constraints are hard limits (budget, time, technical)
- assumptions are gaps that could not be resolved after {max_rounds} Q&A rounds

Respond ONLY with valid JSON matching this exact schema:
{{
  "domain": "<domain string>",
  "inputs": [
    {{"name": "<str>", "format": "<str>", "description": "<str>", "example": "<str or null>"}}
  ],
  "outputs": [
    {{"name": "<str>", "format": "<str>", "description": "<str>", "example": "<str or null>"}}
  ],
  "process_steps": [
    {{
      "step_number": <int>,
      "description": "<str>",
      "rules": ["<rule>", ...],
      "depends_on": [<step_number>, ...]
    }}
  ],
  "edge_cases": [
    {{"description": "<str>", "expected_handling": "<str>"}}
  ],
  "quality_criteria": [
    {{"criterion": "<str>", "validation_method": "<str>"}}
  ],
  "constraints": ["<str>", ...],
  "assumptions": ["<str>", ...]
}}"""


# ── Agent implementation ─────────────────────────────────────────────


def elicitor_agent(
    state: FrankensteinState,
    *,
    llm: LLMService | None = None,
    chroma: ChromaService | None = None,
) -> dict:
    """Elicitor node — extracts requirements via structured Q&A loop.

    Uses LangGraph interrupt() to pause for human answers at each round.
    """
    from app.services.chroma_service import ChromaService as _CS
    from app.services.llm_service import LLMService as _LS

    if llm is None:
        llm = _LS()
    if chroma is None:
        chroma = _CS()

    raw_prompt = state.get("raw_prompt", "")
    max_rounds = settings.max_elicitor_rounds
    threshold = settings.completeness_threshold

    logger.info("Elicitor starting — prompt length: %d chars", len(raw_prompt))

    # ── Step 1: Query domain insights ────────────────────────────────
    domain_insights = _query_domain_insights(chroma, raw_prompt)

    # ── Step 2: Initial gap analysis ─────────────────────────────────
    gap_result = _run_gap_analysis(
        llm, raw_prompt, domain_insights, accumulated_answers=[]
    )
    logger.info(
        "Initial gap analysis — quality: %s, gaps: %s",
        gap_result.overall_quality,
        [c.name for c in gap_result.gaps()],
    )

    all_questions: list[dict] = state.get("elicitor_questions", [])
    all_answers: list[dict] = state.get("human_answers", [])
    previous_questions: list[str] = []
    assumptions: list[str] = []

    # ── Step 3: Q&A loop ─────────────────────────────────────────────
    current_round = 0
    while not gap_result.all_complete() and current_round < max_rounds:
        current_round += 1
        gaps = gap_result.gaps()

        # Determine min questions per category
        is_low_quality = (
            gap_result.overall_quality == "low"
            or len(raw_prompt.split()) <= 10
        )
        min_questions = 2 if is_low_quality else 1

        # Generate questions
        question_categories = _generate_questions(
            llm,
            raw_prompt,
            gaps,
            accumulated_answers=all_answers,
            previous_questions=previous_questions,
            current_round=current_round,
            max_rounds=max_rounds,
            min_questions=min_questions,
        )

        # Track questions
        round_questions: list[str] = []
        for qc in question_categories:
            round_questions.extend(qc.questions)
        previous_questions.extend(round_questions)

        question_payload = {
            "categories": [qc.model_dump() for qc in question_categories],
            "round": current_round,
            "max_rounds": max_rounds,
        }
        all_questions.append(question_payload)

        logger.info(
            "Round %d — sending %d questions across %d categories",
            current_round,
            len(round_questions),
            len(question_categories),
        )

        # ── Interrupt: pause for human answer ────────────────────────
        user_answer = interrupt(question_payload)

        # Process answer
        timestamp = datetime.now(timezone.utc).isoformat()
        answer_record = {
            "round": current_round,
            "answers": user_answer,
            "timestamp": timestamp,
        }
        all_answers.append(answer_record)

        # Extract structured fields from free-text answer
        _extract_answer_fields(llm, round_questions, gaps, user_answer)

        # Re-score
        gap_result = _run_gap_analysis(
            llm, raw_prompt, domain_insights, accumulated_answers=all_answers
        )
        logger.info(
            "Round %d complete — scores: %s",
            current_round,
            {c.name: c.confidence for c in gap_result.categories},
        )

    # ── Step 4: Flag assumptions if gaps remain ──────────────────────
    if not gap_result.all_complete():
        remaining_fields = []
        for cat in gap_result.gaps():
            remaining_fields.extend(cat.missing_fields)
        if remaining_fields:
            assumptions = _generate_assumptions(
                llm, raw_prompt, all_answers, remaining_fields
            )
            logger.info("Generated %d assumptions for remaining gaps", len(assumptions))

    # ── Step 5: Compile RequirementsDoc ──────────────────────────────
    requirements = _compile_requirements(
        llm, raw_prompt, all_answers, assumptions, domain_insights, max_rounds
    )
    logger.info("Requirements compiled — domain: %s", requirements.domain)

    return {
        "elicitor_questions": all_questions,
        "human_answers": all_answers,
        "requirements": requirements,
        "requirements_approved": False,
    }


# ── Internal helpers ─────────────────────────────────────────────────


def _query_domain_insights(chroma: ChromaService, prompt: str) -> str:
    """Query Chroma for domain insights. Returns formatted string or placeholder."""
    try:
        results = chroma.find_domain_insights(prompt)
        if results:
            return "\n".join(
                r.get("document", "") for r in results if r.get("document")
            )
    except Exception:
        logger.warning("Domain insights query failed — proceeding without", exc_info=True)
    return "No domain insights available for this domain."


def _run_gap_analysis(
    llm: LLMService,
    raw_prompt: str,
    domain_insights: str,
    accumulated_answers: list[dict],
) -> GapAnalysisResult:
    """Run gap analysis against 5 categories via LLM."""
    system = GAP_ANALYSIS_SYSTEM.format(domain_insights=domain_insights)

    if accumulated_answers:
        answers_text = "\n".join(
            f"Round {a['round']}: {a['answers']}" for a in accumulated_answers
        )
        user_msg = (
            f"Re-analyze the updated description for completeness.\n\n"
            f'Original prompt: "{raw_prompt}"\n\n'
            f"Additional information provided:\n{answers_text}\n\n"
            f"Assign updated confidence scores based on ALL information above."
        )
    else:
        user_msg = f'Analyze this agent description for completeness:\n\n"{raw_prompt}"'

    raw = llm.call(
        agent_name="elicitor",
        system_prompt=system,
        user_prompt=user_msg,
        json_mode=True,
    )
    data = json.loads(raw)
    return GapAnalysisResult(**data)


def _generate_questions(
    llm: LLMService,
    raw_prompt: str,
    gaps: list,
    accumulated_answers: list[dict],
    previous_questions: list[str],
    current_round: int,
    max_rounds: int,
    min_questions: int,
) -> list[QuestionCategory]:
    """Generate targeted questions for gap categories via LLM."""
    gap_names = ", ".join(g.name for g in gaps)
    gap_json = json.dumps(
        [{"name": g.name, "confidence": g.confidence, "missing_fields": g.missing_fields} for g in gaps],
        indent=2,
    )
    answers_text = "\n".join(
        f"Round {a['round']}: {a['answers']}" for a in accumulated_answers
    ) if accumulated_answers else "None yet"

    prev_q_text = json.dumps(previous_questions) if previous_questions else "None"

    system = QUESTION_GEN_SYSTEM.format(
        gap_category_names=gap_names,
        min_questions=min_questions,
        current_round=current_round,
        max_rounds=max_rounds,
        previous_questions=prev_q_text,
    )
    user_msg = (
        f'Gap analysis results for the following description:\n\n'
        f'Prompt: "{raw_prompt}"\n'
        f'Accumulated answers: {answers_text}\n\n'
        f'Gap categories requiring questions:\n{gap_json}\n\n'
        f'Generate targeted questions for each gap category.'
    )

    raw = llm.call(
        agent_name="elicitor",
        system_prompt=system,
        user_prompt=user_msg,
        json_mode=True,
    )
    data = json.loads(raw)
    categories = [QuestionCategory(**c) for c in data.get("categories", [])]

    # Enforce min questions per category
    for cat in categories:
        if len(cat.questions) < min_questions:
            logger.warning(
                "Category %s has %d questions, min is %d",
                cat.name, len(cat.questions), min_questions,
            )

    # Sort by priority order
    categories.sort(key=lambda c: CATEGORY_PRIORITY.index(c.name) if c.name in CATEGORY_PRIORITY else 99)
    return categories


def _extract_answer_fields(
    llm: LLMService,
    questions_asked: list[str],
    gaps: list,
    user_answer: str,
) -> dict:
    """Extract structured field values from free-text answer."""
    target_fields = []
    for g in gaps:
        target_fields.extend(g.missing_fields)

    system = ANSWER_EXTRACT_SYSTEM.format(
        questions_asked=json.dumps(questions_asked),
        target_fields=json.dumps(target_fields),
    )
    user_msg = f'User\'s answer: "{user_answer}"'

    raw = llm.call(
        agent_name="elicitor",
        system_prompt=system,
        user_prompt=user_msg,
        json_mode=True,
    )
    data = json.loads(raw)
    return data.get("extracted_fields", {})


def _generate_assumptions(
    llm: LLMService,
    raw_prompt: str,
    accumulated_answers: list[dict],
    missing_fields: list[str],
) -> list[str]:
    """Generate conservative assumptions for remaining gaps."""
    answers_text = "\n".join(
        f"Round {a['round']}: {a['answers']}" for a in accumulated_answers
    ) if accumulated_answers else "None"

    user_msg = (
        f'Domain: inferred from prompt\n'
        f'Prompt so far: "{raw_prompt}"\n'
        f'Accumulated answers: {answers_text}\n\n'
        f'Missing fields that need assumptions:\n{json.dumps(missing_fields)}\n\n'
        f'Generate one assumption per missing field.'
    )

    raw = llm.call(
        agent_name="elicitor",
        system_prompt=ASSUMPTION_GEN_SYSTEM,
        user_prompt=user_msg,
        json_mode=True,
    )
    data = json.loads(raw)
    return data.get("assumptions", [])


def _compile_requirements(
    llm: LLMService,
    raw_prompt: str,
    accumulated_answers: list[dict],
    assumptions: list[str],
    domain_insights: str,
    max_rounds: int,
) -> RequirementsDoc:
    """Compile all gathered info into a RequirementsDoc."""
    qa_history = ""
    for a in accumulated_answers:
        qa_history += f"Round {a['round']}:\n  Answer: {a['answers']}\n\n"
    if not qa_history:
        qa_history = "No Q&A rounds needed — prompt was comprehensive."

    assumptions_text = json.dumps(assumptions) if assumptions else "None"

    system = COMPILE_SYSTEM.format(max_rounds=max_rounds)
    user_msg = (
        f'Compile a RequirementsDoc from ALL of the following gathered information:\n\n'
        f'Original prompt: "{raw_prompt}"\n\n'
        f'Round-by-round Q&A:\n{qa_history}\n'
        f'Assumptions generated for missing fields:\n{assumptions_text}\n\n'
        f'Domain insights applied:\n{domain_insights}'
    )

    raw = llm.call(
        agent_name="elicitor",
        system_prompt=system,
        user_prompt=user_msg,
        json_mode=True,
    )
    data = json.loads(raw)
    return RequirementsDoc(**data)
