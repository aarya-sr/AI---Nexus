# Dev Handoff — Frankenstein

## Context

Read these first:
- `Frankenstein_Solution_Approach.md` — full architecture, all data models, pipeline code, agent internals
- `Frankenstein_Justification_Document.md` — problem framing

Everything below assumes you've read the Solution Approach.

## What Exists

- Architecture designed, data models defined, stack decided
- No code written yet
- Docs + PDFs in `/docs`

## What Needs Building

### Priority Order

Build bottom-up. Each layer depends on the one below it.

---

### Layer 1: Foundation (do first)

**1.1 Project scaffold**
```
frankenstein/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # OpenRouter keys, model mapping, constants
│   │   ├── models/              # Pydantic models (ALL defined in Solution Approach)
│   │   │   ├── state.py         # FrankensteinState
│   │   │   ├── requirements.py  # RequirementsDoc, DataSpec, ProcessStep, etc.
│   │   │   ├── spec.py          # AgentSpec (the YAML schema as Pydantic)
│   │   │   ├── critique.py      # CritiqueReport, Finding
│   │   │   ├── testing.py       # TestCase, TestReport, FailureTrace
│   │   │   ├── learning.py      # BuildOutcome
│   │   │   └── tools.py         # ToolSchema
│   │   ├── agents/              # One file per pipeline agent
│   │   │   ├── elicitor.py
│   │   │   ├── architect.py
│   │   │   ├── critic.py
│   │   │   ├── builder.py
│   │   │   ├── tester.py
│   │   │   └── learner.py
│   │   ├── pipeline/
│   │   │   ├── graph.py         # LangGraph StateGraph definition
│   │   │   └── routing.py       # route_after_critique, route_after_test
│   │   ├── services/
│   │   │   ├── chroma_service.py # Chroma collection management + RAG queries
│   │   │   ├── docker_service.py # Docker container management
│   │   │   └── llm_service.py   # OpenRouter client, model-per-agent routing
│   │   └── tool_library/        # Pre-seeded tool schemas (JSON files)
│   │       ├── pdf_parser_pymupdf.json
│   │       ├── csv_parser.json
│   │       ├── web_search.json
│   │       └── ...
│   ├── Dockerfile               # FastAPI server
│   ├── requirements.txt
│   └── tests/
├── runner/
│   └── Dockerfile               # frankenstein-runner base image
├── frontend/
│   ├── src/
│   └── package.json
└── docker-compose.yaml          # backend + chroma + runner
```

**1.2 Data models**
- Copy ALL Pydantic models from Solution Approach into `models/`
- `FrankensteinState`, `RequirementsDoc`, `AgentSpec`, `CritiqueReport`, `Finding`, `TestCase`, `FailureTrace`, `BuildOutcome`, `ToolSchema`
- These are already defined — just translate from doc to code

**1.3 LLM service**
- OpenRouter client wrapping litellm or raw HTTP
- Model routing: function that takes agent name → returns model ID
- Map: elicitor→gpt-4o-mini, architect→claude-sonnet-4-6, critic→gpt-4o, builder→claude-sonnet-4-6, tester→gpt-4o-mini, learner→gpt-4o-mini

**1.4 Chroma service**
- Initialize 4 collections: `tool_schemas`, `spec_patterns`, `anti_patterns`, `domain_insights`
- Seed `tool_schemas` with pre-built tool JSON files
- RAG query functions: `find_similar_specs()`, `find_tools_for_capability()`, `check_anti_patterns()`

---

### Layer 2: Pipeline (do second)

**2.1 LangGraph pipeline**
- Build `StateGraph(FrankensteinState)` exactly as shown in Solution Approach §3.2
- Implement routing functions from §3.3
- Human checkpoint nodes: pause execution, return state to frontend, resume on approval

**2.2 Individual agents — build in this order:**

**Elicitor (simplest, good starting point):**
- Input: raw_prompt
- Analyze prompt against 5-category checklist
- Generate questions for gaps
- Structured output → RequirementsDoc
- Loop max 3 rounds

**Architect (hardest, core logic):**
- RAG query Chroma for past specs + tools
- Task decomposition from requirements
- Tool matching from library
- Agent grouping by cohesion
- Flow design (sequential/parallel/hierarchical/graph)
- Output: AgentSpec (the full YAML schema)

**Critic:**
- Input: AgentSpec
- Run 6 attack vectors (format compat, tool validation, dead-ends, dependency completeness, resource conflicts, circular deps)
- Output: CritiqueReport with severity-scored findings

**Builder:**
- Input: validated AgentSpec
- Select CrewAI or LangGraph compiler based on spec.execution_flow.pattern
- Template-driven code gen
- Output: CodeBundle (generated_agent/ directory)

**Tester:**
- Input: CodeBundle + AgentSpec
- Generate TestCases from io_contracts
- Run in Docker via docker_service
- Validate output
- Generate FailureTraces if needed

**Learner:**
- Input: final state
- Structure BuildOutcome
- Write to Chroma collections

---

### Layer 3: Docker Runner (do third)

**3.1 Base image**
- Build `frankenstein-runner` image with Python 3.11 + crewai + langgraph + common deps
- See Dockerfile in Solution Approach §6.3

**3.2 Docker service**
- Mount generated_agent/ into container
- Run with timeout (60s)
- Capture stdout/stderr
- Return to Tester for validation

---

### Layer 4: Frontend (do last)

**4.1 Chat interface**
- WebSocket connection to FastAPI
- Show Elicitor questions, accept human answers
- Display requirements doc for approval (checkpoint 1)
- Display spec + critique report for approval (checkpoint 2)
- Show build progress (which stage is running)
- Deliver final agent code (download or display)

**4.2 Spec viewer**
- Render AgentSpec as readable format
- Show agent roles, tools, flow diagram
- Show CritiqueReport findings with severity colors

---

### Layer 5: Tool Library Seeding (parallel with Layer 2)

**5.1 Write tool schema JSON files**
- Each tool needs: id, name, description, category, accepts, outputs, output_format, limitations, dependencies, code_template
- Start with tools listed in Solution Approach §7.1
- PS-08 tools: pdf_parser_pymupdf, ocr_tesseract, financial_calculator, rule_engine, report_generator, web_search
- PS-06 tools: csv_parser, statistical_analyzer, scoring_engine, data_visualizer, report_generator
- General: web_search, file_reader, json_transformer, llm_reasoner, code_executor
- `code_template` field = actual Python implementation of each tool

---

## Key Decisions Already Made

| Decision | Answer |
|----------|--------|
| LLM provider | OpenRouter |
| Pipeline framework | LangGraph StateGraph |
| Generated agent framework | CrewAI or LangGraph, Architect decides per case |
| Backend | FastAPI |
| Frontend | React |
| Vector DB | Chroma |
| Code execution | Docker pre-built base image |
| Architect model | claude-sonnet-4-6 |
| Critic model | gpt-4o (different family from Architect, on purpose) |
| Elicitor/Tester/Learner model | gpt-4o-mini |
| Builder model | claude-sonnet-4-6 |
| Human checkpoints | 2 — after requirements, after spec+critique |
| Critic-Architect loop | min 2 rounds, max cap |
| Tester failure routing | code-level → Builder, spec-level → Architect |

## What To Watch Out For

- **Architect is hardest agent to build.** It makes all architectural decisions. Start simple — get it producing valid specs for a single use case (PS-08) before generalizing.
- **Tool code_templates matter.** Builder can only produce working code if tool templates are correct. Test each tool template independently before integrating.
- **Human checkpoints need WebSocket.** Pipeline pauses at checkpoints, sends state to frontend, waits for approval. This needs async handling in LangGraph — look into `interrupt_before` nodes or manual breakpoints.
- **Docker SDK for Python** (`docker` package) — use it for container management instead of subprocess calls.
- **Structured output from LLMs** — use Pydantic models with OpenRouter's structured output support (or parse JSON from model responses). Every agent should return typed Pydantic models, not raw strings.

## Demo Plan

Once built, demo flow:

1. Open Frankenstein web app
2. Type: "Build me a loan underwriting co-pilot that reads bank statements and assesses risk"
3. Elicitor asks 3-5 questions
4. Show generated requirements → approve
5. Show spec + critique → approve
6. Watch build + test happen
7. Download working agent code
8. Run it. It works.

Then repeat with PS-06 prompt to prove generalization.
