---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain-skipped', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
releaseMode: single-release
inputDocuments:
  - docs/Frankenstein_Solution_Approach.md
  - docs/Frankenstein_Justification_Document.md
  - docs/Frankenstein_Product_Description.md
  - docs/HANDOFF.md
workflowType: 'prd'
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 0
  projectDocs: 4
classification:
  projectType: developer_tool
  domain: ai_ml_engineering
  complexity: medium
  projectContext: brownfield
---

# Product Requirements Document - Frankenstein

**Author:** Ved
**Date:** 2026-05-14

## Executive Summary

Frankenstein is a meta-agentic system that converts natural language prompts into tested, deployable multi-agent pipelines. It targets technical users — engineers and AI practitioners — who understand what agents can do but are tired of spending weeks wiring them up manually.

The system runs a six-stage autonomous pipeline: elicit requirements through targeted Q&A, generate a framework-agnostic architectural spec, attack that spec adversarially with a different model family, compile validated specs into CrewAI or LangGraph code, execute and test locally, and store learnings for future builds. Two human checkpoints — after requirements and after spec review — keep the user in control without requiring engineering effort.

Input: one fuzzy prompt. Output: working, tested multi-agent system ready to run.

## What Makes This Special

Most agent builders go prompt to code. Frankenstein goes prompt to structured requirements to framework-agnostic spec to adversarial critique to code to test to learn. The spec layer is the core innovation — it serves as both an inspectable blueprint (users validate before anything is built) and a formal quality gate (the Critic can attack it structurally for format mismatches, dead-ends, circular dependencies, and tool incompatibilities).

Cross-model adversarial review — Architect (Claude) designs, Critic (GPT-4o) attacks — catches blind spots that same-model review misses. The system doesn't just generate code; it runs the same process a senior engineering team would, compressed into minutes.

The hackathon proof: Frankenstein solves PS-03 (meta-agentic systems), then uses itself to produce working agents for PS-08 (loan underwriting) and PS-06 (supplier reliability scoring). The output is the proof.

## Project Classification

- **Project Type:** Developer Tool — meta-agentic code generation platform
- **Domain:** AI/ML Engineering
- **Complexity:** Medium — architectural complexity, no regulatory burden
- **Project Context:** Brownfield — architecture fully designed, all data models defined, zero code written

## Success Criteria

### User Success

- Generated agent code runs without errors on first delivery — no manual debugging required
- Prompt-to-working-agent completes in under 10 minutes end-to-end
- User can inspect and understand the architectural spec before code is generated (blueprint trust moment)
- Elicitor asks questions that genuinely improve the agent output vs. skipping straight to code

### Business Success

- Hackathon judges score high on all three axes: novelty (meta-agentic approach), technical depth (6-stage pipeline with cross-model adversarial review), and practical impact (solves real problem statements)
- Frankenstein generates working agents for both PS-08 (Loan Underwriting) and PS-06 (Supplier Reliability Scoring) — proving generalization, not a one-trick demo
- The demo narrative lands: "we solved PS-03, then used it to solve two other problem statements live"

### Technical Success

- All 6 pipeline stages functional: Elicitor, Architect, Critic, Builder, Tester, Learner
- Cross-model adversarial review produces real findings that improve spec quality (not theater)
- Architect-Critic feedback loop executes at least one revision cycle
- Builder-Tester feedback loop catches and fixes at least one code-level issue
- Chroma RAG retrieval returns relevant tools and past patterns to inform architecture decisions
- Generated code compiles, imports resolve, and runs cleanly

### Measurable Outcomes

| Metric | Target |
|--------|--------|
| Prompt-to-agent time | < 10 minutes |
| Generated agent error rate | 0 errors on delivery |
| Demo problem statements solved | 2 (PS-08 + PS-06) |
| Pipeline stages functional | 6/6 |
| Human checkpoints working | 2/2 |

## User Journeys

### Journey 1: Ravi — The Happy Path

**Who:** Ravi, a senior ML engineer at a lending startup. He's built agents before — CrewAI, LangGraph, the whole stack. He knows the patterns. He's sick of spending 2 weeks per agent wiring up the same boilerplate, debugging tool chains, and testing edge cases manually.

**Opening Scene:** Ravi needs a loan underwriting co-pilot. He opens Frankenstein's chat interface and types: "Build me an agent that reads bank statements, extracts financial data, calculates risk ratios, and produces an underwriting recommendation with reasoning."

**Rising Action:** Frankenstein's Elicitor responds — not with code, but with sharp questions: "What format are the bank statements — PDF, scanned images, or structured data?" / "What risk ratios matter — DTI, credit utilization, something domain-specific?" / "What does a good recommendation look like — pass/fail, or a score with reasoning?" Ravi answers 4-5 questions. The Elicitor assembles a structured requirements doc and presents it: "Here's what I understood. Approve or correct." Ravi scans it, fixes one edge case description, approves.

**Climax:** Frankenstein generates the architectural spec. Ravi sees a rendered view: three agents (Document Parser, Risk Analyzer, Report Generator), each with assigned tools, connected by a flow diagram showing data moving from PDF extraction through risk calculation to final report. The Critic's findings are displayed — it caught that the PDF parser doesn't handle scanned documents and suggested adding OCR as a fallback. Ravi reads the blueprint, sees it's solid, hits approve. Builder compiles. Tester runs. Green across the board.

**Resolution:** Ravi downloads a working generated_agent/ directory. He runs python main.py with a sample bank statement. It works. Three agents coordinate, extract data, calculate ratios, produce a risk report. What would have taken him 2 weeks took 8 minutes.

### Journey 2: Ravi — The Fix Loop

**Who:** Same Ravi, different prompt. He asks Frankenstein to build a supplier reliability scoring agent.

**Opening Scene:** Ravi types: "Build an agent that takes supplier delivery data and scores them on reliability." Deliberately vague — he wants to see how the system handles ambiguity.

**Rising Action:** Elicitor catches the gaps fast — "What data format? CSV, JSON, API?" / "What metrics define reliability — on-time delivery rate, defect rate, lead time variance?" / "How should suppliers be ranked — absolute score, relative percentile, tier buckets?" Ravi answers, requirements doc generated, approved.

**Climax:** Architect queries Chroma for past build patterns — finds the loan underwriting spec from Journey 1 and reuses the proven data-extraction-to-analysis flow structure. Architect generates the spec. Critic attacks it — finds that the statistical analyzer tool outputs raw JSON but the scoring engine expects a specific weighted-metrics format. Architect revises, adds a data transformation step. Second Critic pass — clean. Ravi approves the spec. Builder compiles. Tester runs — catches a code-level issue: the CSV parser import is misconfigured. Builder fixes, Tester re-runs. All green.

**Resolution:** The fix loop worked autonomously. Ravi didn't debug anything — the system caught a spec-level format mismatch AND a code-level import error, fixed both without human intervention. The generated agent scores suppliers correctly from CSV data. The system learned from both the format mismatch and the import fix — stored in Chroma for next time.

### Journey 3: The Hackathon Demo

**Who:** A panel of judges watching the live demo. Technical audience — they know what agents are, they've seen code generation tools.

**Opening Scene:** Presenter explains Frankenstein in one line: "An agent builder that turns a prompt into powerful, working agents in minutes." Judges nod — they've heard this before.

**Rising Action:** Presenter types a loan underwriting prompt live. Judges watch the Elicitor ask smart, domain-relevant questions — not generic templates. The requirements doc appears — structured, specific, clearly extracted from the conversation. Presenter approves. The spec renders — agents, tools, flow diagram visible. The Critic's findings appear in real-time — it found a real issue, the Architect fixed it. Judges lean forward — this isn't scripted, the adversarial review actually works.

**Climax:** Builder compiles. Tester runs. Output appears — a working underwriting report from sample data. Presenter then says: "Now watch — same system, different problem." Types a supplier scoring prompt. Different questions, different spec, different agents, different tools. Same pipeline. Works again. Two problem statements solved by one system, live.

**Resolution:** Judges see what matters: not that code was generated, but that the engineering process was automated. The Elicitor asked the right questions. The spec was inspectable. The Critic caught real issues. The code ran. And it generalized.

### Journey Requirements Summary

| Capability | Revealed By |
|-----------|-------------|
| Chat-based Q&A interface | Journey 1, 2 — Elicitor interaction |
| Structured requirements display + approve/reject | Journey 1, 2 — human checkpoint 1 |
| Rendered spec view (agents, tools, flow diagram) | Journey 1, 3 — human checkpoint 2 |
| Critique findings display with severity | Journey 1, 3 — Critic output |
| Build progress indicator | Journey 3 — demo needs visible pipeline stages |
| Code download / display | Journey 1, 2 — final delivery |
| Real-time pipeline status | Journey 3 — judges watching live |
| Autonomous fix loops (no human intervention) | Journey 2 — Architect-Critic and Builder-Tester loops |
| Learning storage after each build | Journey 2 — Learner captures patterns |

## Innovation & Novel Patterns

### Detected Innovation Areas

**1. Spec-as-contract paradigm** — Framework-agnostic specification layer that sits between requirements and code. The spec is both human-inspectable (trust) and machine-attackable (quality). No existing agent builder uses a formal, structured spec as the intermediate representation.

**2. Cross-model adversarial review** — Architect (Claude) and Critic (GPT-4o) are deliberately different model families. Same-model review has shared blind spots. Cross-model review is a novel quality assurance pattern for LLM-generated architectures.

**3. Failure-to-spec tracing** — When generated code fails tests, failures are traced back to the specific spec decision that caused them (not just the code line). This enables spec-level fixes, not code patches. No existing tool does root-cause analysis at the architectural decision level.

**4. Self-improving build memory** — Every build outcome (successes, failures, anti-patterns) feeds back into Chroma. Future builds query past outcomes via RAG. The system gets better at architecture decisions over time without retraining.

### Market Context & Competitive Landscape

Existing agent builders (ChatDev, MetaGPT, AutoGen Studio) go prompt-to-code. None implement adversarial spec review, structured intermediate representation, or failure-to-spec tracing. The closest analog is a senior engineering team's process — Frankenstein automates that process itself.

### Validation Approach

- **Demo validation:** Generate working agents for two distinct problem domains (PS-08, PS-06) from the same system
- **Adversarial review validation:** Critic produces at least one real finding that changes the spec (not theater)
- **Fix loop validation:** Builder-Tester loop catches and resolves at least one issue autonomously

## Product Scope

### Strategy

Full-capability single release. Every pipeline stage ships functional, no stubs, no hardcoded demos. The Architect agent gets disproportionate engineering investment — if the Architect is strong, everything downstream works; if it's weak, nothing saves the demo.

### Must-Have Capabilities

| Capability | Why Must-Have |
|-----------|--------------|
| Elicitor with 5-category gap analysis | Without smart questions, requirements are garbage in |
| Architect with RAG-informed task decomposition + tool matching | Core decision engine — everything depends on spec quality |
| Critic with 3+ attack vectors | Adversarial review is the key differentiator |
| Architect-Critic feedback loop | Proves the system self-corrects at the design level |
| Builder with CrewAI + LangGraph compilers | Must generate code for both frameworks |
| Tester with local execution + output validation | Generated code must actually run |
| Builder-Tester feedback loop | Proves the system self-corrects at the code level |
| Learner writing to Chroma | Completes the 6-stage pipeline, enables future RAG |
| Pre-seeded Tool Schema Library (PS-08 + PS-06 tools) | Architect can only select tools it knows about |
| Two human checkpoints with approve/reject | Trust mechanism — user stays in control |
| Chat-based WebSocket frontend | Elicitor Q&A requires real-time back-and-forth |
| Rendered spec view with flow diagram | Blueprint trust moment — user sees what will be built |
| Build progress indicator | Demo audience needs to see pipeline stages executing |
| Zip download of generated agent | User takes home working code |

### Nice-to-Have Capabilities

| Capability | Why Nice-to-Have |
|-----------|-----------------|
| Docker sandboxed execution | Stronger isolation, but local execution proves the point |
| Full 6-vector Critic | 3 vectors enough for demo, remaining 3 are polish |
| Spec-level failure routing from Tester back to Architect | Code-level routing to Builder is sufficient for demo |
| Anti-pattern memory in Chroma | Valuable but cold-start means limited utility in demo |
| Domain-specific Elicitor question templates | Generic gap analysis works for demo; templates are optimization |

### Growth Features (Post-Release)

- Docker sandboxed execution (pre-built base image, container management)
- Full 6-vector Critic (resource conflicts, circular dependency detection, dead-end analysis)
- Tester failure tracing with spec-level root cause routing back to Architect
- Richer Tool Schema Library beyond demo problem statements
- Spec pattern memory — RAG retrieval of past successful specs to inform new builds
- Anti-pattern memory — avoid known failure modes from previous builds

### Vision (Future)

- Self-improving system: Learner insights measurably improve subsequent build quality
- Domain-specific question templates in Elicitor (finance, supply chain, compliance, etc.)
- Multi-framework output: beyond CrewAI/LangGraph to AutoGen, DSPy, custom
- Agent marketplace: share and reuse generated agents across users
- Production deployment pipeline: generated agents deploy directly, not just download

### Risk Mitigation

**Technical Risks:**
- **Architect quality** — Highest risk. Mitigation: invest heavily in prompt engineering, test against both PS-08 and PS-06 iteratively, use RAG from Tool Schema Library to constrain decisions to validated tools. If spec quality is inconsistent, add more structured output constraints (Pydantic response models) to force the Architect into valid spec shapes.
- **Cross-model API reliability** — 6 agents hitting OpenRouter across 3 model families. Mitigation: implement retry with exponential backoff on all LLM calls. Cache Elicitor/Architect prompts to avoid re-running on transient failures.
- **Builder code template quality** — Generated code quality depends entirely on template quality. Mitigation: test each tool's code_template independently before integrating into the Builder. Run generated output through py_compile and import validation before delivery.
- **Spec quality risk** — If generated specs are too generic, agents won't work. Mitigation: pre-seeded Tool Schema Library constrains tool selection to validated options.
- **Cross-model latency** — Multiple LLM calls across different models add latency. Mitigation: parallelize where possible, target under 10 minutes total.
- **Learning cold start** — First builds have no past patterns in Chroma. Mitigation: pre-seed with curated spec patterns for demo domains.

**Market Risks:**
- Minimal for hackathon — the demo IS the validation. Risk is demo failure, not market rejection.

**Resource Risks:**
- Single-person or small-team build of a complex system. Mitigation: build bottom-up per HANDOFF.md layering (foundation, pipeline, runner, frontend). Get the backend pipeline working end-to-end before touching frontend polish.

## Functional Requirements

### Requirements Elicitation

- FR1: User can submit a natural language prompt describing the agent they want built
- FR2: System can analyze the prompt against a 5-category completeness checklist (Input/Output, Process, Data, Edge Cases, Quality Bar) and assign confidence scores (0-1) per field
- FR3: System can generate targeted questions only for fields scoring below 0.7 confidence
- FR4: User can answer Elicitor questions through a real-time chat interface
- FR5: System can loop up to 3 question rounds; after 3 rounds, remaining gaps are flagged as assumptions in the requirements doc
- FR6: System can compile answers into a structured RequirementsDoc (domain, inputs, outputs, process steps, edge cases, quality criteria, constraints)
- FR7: User can review the generated requirements document in a readable rendered format at human checkpoint 1
- FR8: User can approve the requirements, or provide free-text corrections that the Elicitor incorporates before re-presenting
- FR9: System can handle low-quality or empty prompts by generating at least 2 clarifying questions per identified gap to guide the user toward sufficient input

### Architecture & Specification

- FR10: System can query Chroma spec_patterns collection for similar past specs via RAG
- FR11: System can decompose requirements process_steps into discrete computational tasks, each tagged with required capability (text extraction, calculation, reasoning, generation, API call)
- FR12: System can query the Tool Schema Library for each task's capability and receive ranked tool matches with format compatibility info
- FR13: System can select tools based on format chain compatibility (upstream output format matches downstream input format)
- FR14: System can group tasks into agents based on cohesion (related tasks) and coupling (data dependencies)
- FR15: System can design memory strategy (short-term, long-term, shared, none) based on inter-agent data sharing needs
- FR16: System can analyze the dependency graph to determine execution flow pattern (sequential, parallel, hierarchical, graph)
- FR17: System can select target framework — CrewAI for role-based crews, LangGraph for state-dependent flows — based on flow pattern analysis
- FR18: System can generate a complete AgentSpec (agents, tools, memory, execution flow, error handling, I/O contracts) as structured output conforming to the defined spec schema
- FR19: System can expose decision rationale for framework selection, tool choices, and agent grouping in the spec output

### Adversarial Review

- FR20: Critic can run format compatibility checks — verify every agent's output format matches the next agent's input format across all edges
- FR21: Critic can run tool validation — verify each tool's accepts field matches the data format it will actually receive
- FR22: Critic can run dependency completeness checks — verify every agent's required input fields are provided by upstream agents
- FR23: Critic can generate a CritiqueReport with findings scored as critical, warning, or suggestion, including evidence and suggested fixes
- FR24: System can route specs with critical findings back to Architect for revision, attaching critique findings to state
- FR25: System can loop Architect-Critic review until no critical findings remain, up to a configurable max iteration cap
- FR26: Architect and Critic must use different LLM model families to ensure cross-model adversarial coverage

### Spec Review & Approval

- FR27: User can view the architectural spec rendered with agent roles, assigned tools, and a visual flow diagram (graph visualization of agent connections and data flow)
- FR28: User can view the Critic's findings with severity color coding (critical/warning/suggestion)
- FR29: User can view the Architect's decision rationale (why this framework, why these tools, why this grouping)
- FR30: User can approve the spec, or provide free-text feedback that triggers Architect revision before re-presenting

### Code Generation

- FR31: Builder can compile a validated AgentSpec into CrewAI code that follows the framework's documented patterns (Agent, Tool, Crew definitions)
- FR32: Builder can compile a validated AgentSpec into LangGraph code that follows the framework's documented patterns (StateGraph, node functions, conditional edges)
- FR33: Builder can generate a complete project directory: main.py, agents.py, tools.py, orchestration.py, config.yaml, requirements.txt, tests/
- FR34: Builder can use pre-validated code templates from the Tool Schema Library for tool implementations
- FR35: Builder can validate generated code — syntax check (py_compile), import resolution against requirements.txt, function signature match against spec I/O contracts
- FR36: Builder can generate a README.md in the output with usage instructions, config.yaml field descriptions, and run command

### Testing & Validation

- FR37: Tester can generate test cases from spec I/O contracts, including expected output schemas and quality checks
- FR38: Tester can generate synthetic test input data based on domain knowledge from the requirements doc (e.g., sample bank statement data for PS-08, sample supplier CSV for PS-06)
- FR39: Tester can execute generated agent code in an isolated process with a configurable timeout (default 60s)
- FR40: Tester can capture stdout, stderr, and exit code from execution
- FR41: Tester can validate execution output against expected output schemas and quality checks
- FR42: Tester can generate FailureTraces mapping errors to the failing agent, root cause classification (code-level vs spec-level), and suggested fix
- FR43: Tester can route code-level failures back to Builder for code fixes
- FR44: System can loop Builder-Tester until tests pass, up to a configurable max iteration cap
- FR45: System can deliver a partially successful build when max iterations are reached, with clear warnings about what failed and why

### Learning & Memory

- FR46: Learner can structure build outcomes: requirements summary, final spec, framework used, tools used, iterations needed, failure patterns, anti-patterns, success patterns
- FR47: Learner can write build outcomes to Chroma spec_patterns collection for future RAG retrieval
- FR48: Learner can write failure patterns to Chroma anti_patterns collection
- FR49: Architect can query anti_patterns collection to check if a proposed pattern has failed before

### Tool Schema Library

- FR50: System can store validated tool definitions with id, name, description, category, accepts, outputs, output_format, limitations, dependencies, code_template, compatible_with, incompatible_with
- FR51: System ships pre-seeded with tools for PS-08 (PDF parser, financial calculator, rule engine, report generator, web search)
- FR52: System ships pre-seeded with tools for PS-06 (csv_parser, statistical_analyzer, scoring_engine, data_visualizer, report_generator)
- FR53: System ships pre-seeded with general-purpose tools (web_search, file_reader, json_transformer, llm_reasoner, code_executor)
- FR54: Architect can query tool library by capability requirement and receive ranked matches with format compatibility info

### LLM Service

- FR55: System can route LLM calls through OpenRouter with model-per-agent configuration
- FR56: System can retry failed LLM calls with exponential backoff
- FR57: System can return structured, typed model outputs from LLM calls (not raw strings)
- FR58: Generated agents that require LLM access receive the API key injected via config.yaml at build time

### Frontend Experience

- FR59: User can interact with the Elicitor via real-time WebSocket chat
- FR60: User can see which pipeline stage is currently executing, with visual progress indication
- FR61: User can see test results after the Tester completes (pass/fail per test, generated agent output)
- FR62: User can download the generated agent project as a zip file
- FR63: User can start a new build session
- FR64: User can see error states when pipeline stages fail (LLM errors, build failures) with clear messaging

## Developer Tool Technical Requirements

### Output Frameworks

- CrewAI — for role-based agent crews with sequential or hierarchical execution
- LangGraph — for state-dependent flows with conditional edges and feedback loops
- Architect selects framework per build based on dependency graph analysis of the agent tasks

### Generated Project Structure

```
generated_agent/
├── main.py              # entry point
├── agents.py            # agent definitions
├── tools.py             # tool implementations
├── orchestration.py     # crew or graph definition
├── config.yaml          # agent config + user input data paths
├── requirements.txt     # Python dependencies
├── README.md            # usage instructions + config field descriptions
└── tests/
    └── test_pipeline.py # auto-generated from spec contracts
```

Core constraint: self-contained Python project that runs with `python main.py` after `pip install -r requirements.txt`. Structure will evolve as Builder implementation progresses.

### Delivery Method

- Download as zip from the web UI
- Post-release: run directly in Docker within the web interface

### User Configuration

- Zero configuration required beyond pip install
- Input data provided via config.yaml (file paths, parameters)
- OpenRouter API key injected at build time for agents that need LLM access

### Backend API (FastAPI)

- WebSocket endpoint for chat sessions (Elicitor Q&A, pipeline status streaming)
- POST endpoint to start a new build session
- GET endpoint for build status polling (fallback if WebSocket drops)
- GET endpoint to download generated agent zip
- POST endpoints for human checkpoint approvals (requirements, spec)

### Code Quality Standards

- Generated code must be framework-idiomatic — CrewAI output looks like a CrewAI developer wrote it, LangGraph output follows LangGraph patterns
- Code templates in the Builder tested independently before integration
- requirements.txt in generated output pins versions to avoid dependency conflicts
- config.yaml is the single entry point for user customization of generated agents

## Non-Functional Requirements

### Performance

- End-to-end prompt-to-working-agent completes in under 10 minutes on a standard dev machine (8GB RAM, 4-core CPU), including human interaction time
- Performance budget by stage: Elicitor Q&A ~2-3 min (human-bound), Architect+Critic ~2-3 min, Builder ~1 min, Tester ~1-2 min, Learner <30s
- WebSocket chat messages deliver to frontend within 500ms of generation
- Pipeline stage transitions reflect in the UI within 1 second
- Spec rendering (agents, tools, flow diagram) loads within 2 seconds of generation
- Zip file generation and download initiates within 3 seconds of build completion
- LLM calls that exceed 60 seconds per individual call timeout and retry

### Security

- OpenRouter API key stored server-side, never exposed to frontend
- API key for generated agents injected via config.yaml, not hardcoded in generated source code
- Generated code execution has a configurable timeout (default 60s) to prevent runaway processes
- No user authentication required for hackathon demo

### Integration

- All LLM calls route through OpenRouter API with model-per-agent routing
- Chroma runs as an embedded instance (no separate server for hackathon simplicity)
- Frontend-backend communication via WebSocket for chat and pipeline streaming, REST for file download and checkpoint approvals
- Generated agent code depends only on packages available via pip (no private registries, no custom packages)
