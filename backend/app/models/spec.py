from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SpecMetadata(BaseModel):
    name: str
    domain: str
    framework_target: Literal["crewai", "langgraph"]
    decision_rationale: str | None = None
    created_from_pattern: str | None = None


class AgentDef(BaseModel):
    id: str
    role: str
    goal: str
    backstory: str
    tools: list[str] = []
    reasoning_strategy: Literal["react", "cot", "plan_execute"] = "react"
    receives_from: list[str] = []
    sends_to: list[str] = []


class ToolRef(BaseModel):
    id: str
    library_ref: str
    config: dict = {}
    accepts: list[str] = []
    outputs: list[str] = []


class MemoryConfig(BaseModel):
    strategy: Literal["short_term", "long_term", "shared", "none"] = "shared"
    shared_keys: list[str] = []
    persistence: Literal["session", "permanent"] = "session"


class DataContract(BaseModel):
    fields: list[str] = []
    format: str = "json"


class GraphEdge(BaseModel):
    from_agent: str
    to_agent: str
    condition: str | None = None
    data_contract: DataContract | None = None


class ExecutionFlow(BaseModel):
    pattern: Literal["sequential", "parallel", "hierarchical", "graph"]
    graph: GraphDef | None = None


class GraphDef(BaseModel):
    nodes: list[str] = []
    edges: list[GraphEdge] = []


# Rebuild ExecutionFlow now that GraphDef is defined
ExecutionFlow.model_rebuild()


class ErrorHandler(BaseModel):
    agent_id: str
    on_failure: Literal["retry", "fallback", "skip", "abort"] = "retry"
    max_retries: int = 2
    fallback_agent: str | None = None


class SchemaField(BaseModel):
    name: str
    type: str
    required: bool = True


class IOSchema(BaseModel):
    fields: list[SchemaField] = []


class IOContract(BaseModel):
    agent_id: str
    input_schema: IOSchema = IOSchema()
    output_schema: IOSchema = IOSchema()


class AgentSpec(BaseModel):
    metadata: SpecMetadata
    agents: list[AgentDef]
    tools: list[ToolRef]
    memory: MemoryConfig = MemoryConfig()
    execution_flow: ExecutionFlow
    error_handling: list[ErrorHandler] = []
    io_contracts: list[IOContract] = []
