# Elicitation Stage

**Agent:** Elicitor | **Model:** gpt-4o-mini | **Input:** raw_prompt | **Output:** RequirementsDoc

The Elicitor extracts structured domain knowledge from a human's fuzzy natural-language prompt. It does NOT invent domain knowledge — it asks the right questions to pull out what the human already knows but didn't think to say.

## Data Models

```python
class DataSpec(BaseModel):
    name: str                    # "bank_statement"
    format: str                  # "pdf", "csv", "json", "text"
    description: str             # "Monthly bank statement from any major bank"
    example: str | None          # "Chase checking account statement, 3 pages"

class ProcessStep(BaseModel):
    step_number: int             # 1, 2, 3...
    description: str             # "Extract transaction data from bank statement"
    rules: list[str]             # ["Must handle multi-page PDFs", "Ignore marketing pages"]
    depends_on: list[int]        # [1] means depends on step 1's output

class EdgeCase(BaseModel):
    description: str             # "Bank statement is a scanned image, not digital PDF"
    expected_handling: str       # "Fall back to OCR extraction, flag confidence score"

class QualityCriterion(BaseModel):
    criterion: str               # "Risk score accuracy"
    validation_method: str       # "Score must be within 10% of manual underwriter assessment"

class RequirementsDoc(BaseModel):
    domain: str                  # "loan_underwriting"
    inputs: list[DataSpec]
    outputs: list[DataSpec]
    process_steps: list[ProcessStep]
    edge_cases: list[EdgeCase]
    quality_criteria: list[QualityCriterion]
    constraints: list[str]       # ["Must process within 30 seconds", "No external API calls"]
    assumptions: list[str]       # Fields that couldn't be fully resolved
```

## Internal Process

```
load_domain_context → analyze_prompt → identify_gaps → generate_questions → receive_answers → update_requirements → check_completeness
                           ^                                                                                              |
                           └──────────────────────── (if incomplete, round < MAX_ELICITOR_ROUNDS) ◄───────────────────────┘
```

### Step 0: Load Domain Context (RAG)

Before analyzing the prompt, query Chroma `domain_insights` collection for domain-specific knowledge:
```
"Find insights for domain: [inferred domain from raw_prompt]"
```
Returns domain-specific learnings from past builds — what questions were most useful, what assumptions proved wrong, what domain-specific patterns matter. If the collection is empty (first build), skip.

This context informs question generation — if past builds in the same domain revealed that "bank statement format varies widely," the Elicitor knows to ask about format early.

### Step 1: Analyze Prompt

Parse the raw prompt against the 5-category completeness checklist. For each category, assign a confidence score (0.0 - 1.0) based on how much the prompt already answers:

| Category | Required Fields | What to Look For |
|----------|----------------|------------------|
| **Input/Output** | inputs, outputs with format + description | Data types mentioned, file formats, expected deliverables |
| **Process** | process_steps with rules and dependencies | Verbs describing what should happen, sequence indicators |
| **Data** | DataSpec details — format, structure, volume | Specific file types, data sources, size expectations |
| **Edge Cases** | edge_cases with handling strategies | "What if...", error conditions, fallback behavior |
| **Quality Bar** | quality_criteria with validation methods | Success metrics, accuracy requirements, performance thresholds |

### Step 2: Identify Gaps

Any category scoring below 0.7 needs questions. Prioritize by impact:
1. **Input/Output** gaps are highest priority — without knowing what goes in and comes out, nothing else matters
2. **Process** gaps are next — the "how" that connects inputs to outputs
3. **Data** gaps clarify format details that affect tool selection downstream
4. **Edge Cases** and **Quality Bar** are lowest priority — can be inferred if the human doesn't specify

### Step 3: Generate Questions

Generate targeted questions ONLY for gaps. Rules:
- Ask no more than 5 questions per round
- Each question must target a specific gap, not fish for general information
- Questions should be concrete, not abstract ("What format are the bank statements in?" not "Tell me about your data")
- Explain WHY you're asking — the human should understand what the answer enables
- Offer examples or options when possible ("Is the output a PDF report, a JSON score, or both?")

### Step 4: Receive Answers

Parse human answers back into the relevant category fields. Partial answers are fine — update the confidence score incrementally. If the human says "I don't know" or "whatever works," that's a valid answer — flag it as an assumption and move on.

### Step 5: Update Requirements

Merge new information into the growing RequirementsDoc. Each answer should update one or more fields and raise the confidence score for that category.

### Step 6: Check Completeness

Re-score all categories. If all required fields score >= 0.7, produce the final RequirementsDoc. If gaps remain and round < MAX_ELICITOR_ROUNDS (3), loop back to Step 2. If max rounds reached, flag remaining gaps as assumptions in `RequirementsDoc.assumptions` and proceed.

## Prompt Engineering Notes

**System prompt should establish:**
- Role: "You are a domain knowledge extractor. Your job is to understand what the human wants their agent to do, not how to build it."
- Tone: Conversational, not interrogative. The human is a domain expert, not a suspect.
- Constraint: "Never invent domain knowledge. If you don't know something about the domain, ask. If the human doesn't know, flag it as an assumption."
- Output format: "Always respond with structured JSON matching the RequirementsDoc schema when producing the final output."

**Key behaviors to instruct:**
- Start by summarizing what you understood from the prompt BEFORE asking questions. This builds trust and catches misunderstandings early.
- Group related questions together — don't jump between categories randomly.
- When the human gives a vague answer, ask one clarifying follow-up, then accept and flag as assumption. Don't badger.
- If the domain is one you have knowledge about (e.g., loan underwriting), use that knowledge to offer specific options ("Bank statements usually come as PDF or CSV — which are you working with?"), but always defer to the human's answer.

## Example I/O — PS-08 Loan Underwriting

### Input (raw_prompt)
```
"Build me a loan underwriting co-pilot that reads bank statements and assesses risk"
```

### Round 1 — Gap Analysis

| Category | Score | Gaps |
|----------|-------|------|
| Input/Output | 0.3 | Format of bank statements? What does "risk assessment" output look like? |
| Process | 0.2 | What steps between reading and assessing? What rules? |
| Data | 0.2 | PDF? CSV? Scanned? How many pages? |
| Edge Cases | 0.0 | Nothing mentioned |
| Quality Bar | 0.1 | "Assesses risk" — by what standard? |

### Round 1 — Generated Questions

1. "What format are the bank statements in? (PDF, CSV, scanned images, or a mix?) — I need this to select the right extraction tools."
2. "What should the final output look like? A risk score (0-100)? A full report with reasoning? Both? — This determines what the agent needs to produce."
3. "What specific factors should the agent evaluate when assessing risk? (e.g., income stability, debt-to-income ratio, transaction patterns, overdrafts) — I need to know the underwriting rules."
4. "Is there an existing risk framework or scoring model you want the agent to follow, or should it design one from standard underwriting practices?"
5. "How fast does this need to run? Seconds? Minutes? — This affects whether I can use heavier analysis tools."

### Round 1 — Human Answers (example)

1. "PDFs mostly, sometimes scanned"
2. "A risk score from 0 to 1, plus a markdown report explaining the reasoning"
3. "Income stability, debt-to-income ratio, large unusual transactions, overdraft frequency"
4. "Use standard practices, nothing custom"
5. "Under 2 minutes is fine"

### After Round 1 — Updated Scores

| Category | Score | Status |
|----------|-------|--------|
| Input/Output | 0.8 | Resolved |
| Process | 0.5 | Need step details |
| Data | 0.6 | Need volume/structure |
| Edge Cases | 0.0 | Still unaddressed |
| Quality Bar | 0.6 | Need accuracy criteria |

### Round 2 — Remaining Questions

1. "For scanned PDFs, is OCR quality acceptable to you, or do you need the agent to flag low-confidence extractions? — Scanned documents are inherently less reliable."
2. "How many bank statements does the agent process at once? One per applicant, or multiple months?"
3. "What should happen if the agent can't extract data from a statement? Reject the application? Flag for human review?"
4. "What accuracy level do you expect for the risk score? Within 10% of a human underwriter? Or more of a directional indicator?"

### Final RequirementsDoc Output

```json
{
  "domain": "loan_underwriting",
  "inputs": [
    {
      "name": "bank_statement",
      "format": "pdf",
      "description": "Monthly bank statement, digital or scanned",
      "example": "Chase checking account statement, 3 pages, PDF"
    }
  ],
  "outputs": [
    {
      "name": "risk_score",
      "format": "json",
      "description": "Risk score from 0.0 (no risk) to 1.0 (highest risk)",
      "example": "{\"score\": 0.35, \"confidence\": 0.85}"
    },
    {
      "name": "risk_report",
      "format": "markdown",
      "description": "Detailed reasoning report explaining the risk assessment",
      "example": "## Risk Assessment\n### Income Stability: Low Risk\n..."
    }
  ],
  "process_steps": [
    {
      "step_number": 1,
      "description": "Extract text and transaction data from bank statement PDF",
      "rules": ["Handle multi-page PDFs", "Use OCR for scanned documents", "Flag low-confidence extractions"],
      "depends_on": []
    },
    {
      "step_number": 2,
      "description": "Parse transactions into structured format (date, amount, description, category)",
      "rules": ["Categorize transactions automatically", "Handle multiple account types"],
      "depends_on": [1]
    },
    {
      "step_number": 3,
      "description": "Calculate financial metrics: income stability, DTI ratio, overdraft frequency, unusual transaction flags",
      "rules": ["Use standard underwriting formulas", "Weight recent months more heavily"],
      "depends_on": [2]
    },
    {
      "step_number": 4,
      "description": "Generate risk score and detailed reasoning report",
      "rules": ["Score 0.0-1.0 scale", "Report must explain each factor's contribution", "Flag assumptions"],
      "depends_on": [3]
    }
  ],
  "edge_cases": [
    {
      "description": "Scanned PDF with poor image quality",
      "expected_handling": "Attempt OCR, flag confidence score, proceed if confidence > 0.6, else flag for human review"
    },
    {
      "description": "Bank statement in unsupported format",
      "expected_handling": "Reject with clear error message specifying supported formats"
    },
    {
      "description": "Insufficient transaction history (< 1 month)",
      "expected_handling": "Produce risk score with high uncertainty flag, note limited data in report"
    }
  ],
  "quality_criteria": [
    {
      "criterion": "Risk score accuracy",
      "validation_method": "Score within 15% of manual underwriter assessment on test cases"
    },
    {
      "criterion": "Report completeness",
      "validation_method": "Report must address all 4 risk factors with evidence from extracted data"
    }
  ],
  "constraints": ["Process time under 2 minutes", "No external API calls for financial data"],
  "assumptions": ["Standard underwriting practices are sufficient (no custom model)", "Single applicant per run"]
}
```

## Error Handling

| Error | Cause | Response |
|-------|-------|----------|
| LLM returns unstructured text instead of JSON | Prompt not constraining output format | Retry with explicit JSON schema in prompt. Max 2 retries, then parse best-effort. |
| Human provides contradictory answers | Round 1 says "PDF only", Round 2 says "also CSV" | Surface contradiction to human: "Earlier you said PDF only, now CSV too — which is it?" Update based on latest answer. |
| Human abandons mid-elicitation | Stops responding after Round 1 | After configurable timeout, flag all unresolved fields as assumptions and produce RequirementsDoc with what's available. Present at checkpoint with clear assumption warnings. |
| Prompt is too vague to analyze | "Build me an agent" with zero domain content | Ask one open-ended question: "What problem should this agent solve? Describe the task as if explaining it to a new hire." If still vague after 1 round, surface to human: "I need more context to proceed." |
| Prompt is extremely detailed | Multi-paragraph domain description covering all categories | Skip most questions. Score categories, confirm with human: "I think I have everything I need. Here's what I understood — anything wrong or missing?" Jump to RequirementsDoc production. |

## Edge Cases

- **Domain the LLM knows well** (e.g., loan underwriting): Use domain knowledge to offer specific, smart options. But never assume the human's process matches textbook — always ask.
- **Domain the LLM knows poorly** (e.g., niche industrial process): Lean harder on questions. Ask the human to explain the process step-by-step as if teaching it. More rounds may be needed.
- **Human is technical** (gives structured answers, mentions formats): Fewer questions needed. Match their precision level.
- **Human is non-technical** (vague answers, business language): Translate technical questions into business language. "What format?" becomes "How do you receive the bank statements? Email attachment? Downloaded file? Paper?"
