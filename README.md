# Frankenstein

Meta-agentic system that builds AI agents from natural language prompts.

**Input:** One fuzzy prompt from a domain expert
**Output:** Tested, deployable multi-agent system (CrewAI or LangGraph)

## How It Works

Six-stage pipeline: Elicit → Architect → Critique → Build → Test → Learn

Human provides domain knowledge. Frankenstein provides engineering. Two human checkpoints (requirements approval + spec approval). Everything else autonomous.

## Docs

| Document | What |
|----------|------|
| [Justification](docs/Frankenstein_Justification_Document.md) | Why this problem matters |
| [Solution Approach](docs/Frankenstein_Solution_Approach.md) | Full architecture, engineering, and stack |
| [Product Description](docs/Frankenstein_Product_Description.md) | Business-side overview |
| [Dev Handoff](docs/HANDOFF.md) | Build plan for dev team |
| [Problem Statement](docs/69fe33f7e77b5_Problem_statement.docx) | Original PS-03 problem statement |

## Stack

| Layer | Tech |
|-------|------|
| Pipeline | LangGraph (StateGraph) |
| LLMs | OpenRouter — gpt-4o-mini, claude-sonnet-4-6, gpt-4o |
| Generated Agents | CrewAI or LangGraph (Architect decides) |
| Vector DB | Chroma |
| Backend | FastAPI |
| Frontend | React |
| Execution | Docker (pre-built base image) |

## Project Status

**Phase:** Pre-development — architecture and docs complete, no code yet.
