import json
import logging
from pathlib import Path

import chromadb

from app.models.tools import ToolSchema

logger = logging.getLogger(__name__)

COLLECTIONS = ["tool_schemas", "spec_patterns", "anti_patterns", "domain_insights", "builder_repair_patterns"]


class ChromaService:
    def __init__(self, persist_dir: str = "./chroma_data"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self._collections: dict[str, chromadb.Collection] = {}
        for name in COLLECTIONS:
            self._collections[name] = self.client.get_or_create_collection(name)

    def collection(self, name: str) -> chromadb.Collection:
        if name not in self._collections:
            raise KeyError(
                f"Unknown collection '{name}'. Valid: {list(self._collections.keys())}"
            )
        return self._collections[name]

    # ── Tool Schema Library ──────────────────────────────────────────

    def seed_tools(self, tool_library_dir: str | Path) -> int:
        """Load all JSON tool schemas from a directory into the tool_schemas collection.
        Returns count of tools seeded."""
        tool_dir = Path(tool_library_dir)
        col = self.collection("tool_schemas")
        count = 0
        for path in sorted(tool_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text())
                tool = ToolSchema(**data)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning("Skipping invalid tool file %s: %s", path.name, e)
                continue
            # Embed on description + category + capabilities
            embed_text = f"{tool.name}: {tool.description}. Category: {tool.category}. Accepts: {', '.join(tool.accepts)}. Outputs: {', '.join(tool.outputs)}."
            col.upsert(
                ids=[tool.id],
                documents=[embed_text],
                metadatas=[{
                    "id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "category": tool.category,
                    "accepts": json.dumps(tool.accepts),
                    "outputs": json.dumps(tool.outputs),
                    "output_format": tool.output_format,
                    "limitations": json.dumps(tool.limitations),
                    "dependencies": json.dumps(tool.dependencies),
                    "compatible_with": json.dumps(tool.compatible_with),
                    "incompatible_with": json.dumps(tool.incompatible_with),
                    "code_template": tool.code_template,
                }],
            )
            count += 1
        return count

    def find_tools_for_capability(self, capability: str, n_results: int = 5) -> list[ToolSchema]:
        """RAG query: find tools matching a capability description."""
        col = self.collection("tool_schemas")
        results = col.query(query_texts=[capability], n_results=n_results)
        return self._parse_tool_results(results)

    def get_tool_by_id(self, tool_id: str) -> ToolSchema | None:
        col = self.collection("tool_schemas")
        results = col.get(ids=[tool_id])
        if not results["ids"]:
            return None
        tools = self._parse_tool_results_from_get(results)
        return tools[0] if tools else None

    def _parse_tool_results(self, results: dict) -> list[ToolSchema]:
        tools = []
        if not results["metadatas"] or not results["metadatas"][0]:
            return tools
        for meta in results["metadatas"][0]:
            tools.append(self._meta_to_tool(meta))
        return tools

    def _parse_tool_results_from_get(self, results: dict) -> list[ToolSchema]:
        tools = []
        if not results["metadatas"]:
            return tools
        for meta in results["metadatas"]:
            tools.append(self._meta_to_tool(meta))
        return tools

    @staticmethod
    def _meta_to_tool(meta: dict) -> ToolSchema:
        return ToolSchema(
            id=meta["id"],
            name=meta["name"],
            description=meta.get("description", ""),
            category=meta["category"],
            accepts=json.loads(meta["accepts"]),
            outputs=json.loads(meta["outputs"]),
            output_format=meta["output_format"],
            limitations=json.loads(meta["limitations"]),
            dependencies=json.loads(meta["dependencies"]),
            code_template=meta["code_template"],
            compatible_with=json.loads(meta["compatible_with"]),
            incompatible_with=json.loads(meta["incompatible_with"]),
        )

    # ── Spec Patterns ────────────────────────────────────────────────

    def find_similar_specs(self, requirements_summary: str, n_results: int = 3) -> list[dict]:
        """RAG query: find past specs similar to current requirements."""
        col = self.collection("spec_patterns")
        if col.count() == 0:
            return []
        results = col.query(query_texts=[requirements_summary], n_results=n_results)
        return self._flatten_results(results)

    def store_spec_pattern(
        self, spec_id: str, requirements_summary: str, metadata: dict
    ) -> None:
        col = self.collection("spec_patterns")
        col.upsert(ids=[spec_id], documents=[requirements_summary], metadatas=[metadata])

    # ── Anti-Patterns ────────────────────────────────────────────────

    def check_anti_patterns(self, pattern_description: str, n_results: int = 3) -> list[dict]:
        """RAG query: check if a proposed pattern has failed before."""
        col = self.collection("anti_patterns")
        if col.count() == 0:
            return []
        results = col.query(query_texts=[pattern_description], n_results=n_results)
        return self._flatten_results(results)

    def store_anti_pattern(self, pattern_id: str, description: str, metadata: dict) -> None:
        col = self.collection("anti_patterns")
        col.upsert(ids=[pattern_id], documents=[description], metadatas=[metadata])

    # ── Domain Insights ──────────────────────────────────────────────

    def find_domain_insights(self, domain_query: str, n_results: int = 5) -> list[dict]:
        """RAG query: find domain-specific learnings."""
        col = self.collection("domain_insights")
        if col.count() == 0:
            return []
        results = col.query(query_texts=[domain_query], n_results=n_results)
        return self._flatten_results(results)

    def store_domain_insight(self, insight_id: str, insight: str, metadata: dict) -> None:
        col = self.collection("domain_insights")
        col.upsert(ids=[insight_id], documents=[insight], metadatas=[metadata])

    # ── Builder Repair Patterns ──────────────────────────────────────

    def store_repair_pattern(
        self, pattern_id: str, error_text: str, fix_text: str, metadata: dict
    ) -> None:
        """Persist a (validator-error → applied-fix) pair for future Builder RAG."""
        col = self.collection("builder_repair_patterns")
        doc = f"ERROR: {error_text}\nFIX: {fix_text}"
        col.upsert(ids=[pattern_id], documents=[doc], metadatas=[metadata])

    def find_similar_repair_patterns(self, error_text: str, n_results: int = 3) -> list[dict]:
        col = self.collection("builder_repair_patterns")
        if col.count() == 0:
            return []
        results = col.query(query_texts=[error_text], n_results=n_results)
        return self._flatten_results(results)

    # ── Tool Compatibility Updates ───────────────────────────────────

    def update_tool_compatibility(
        self, tool_id: str, compatible: list[str] | None = None, incompatible: list[str] | None = None
    ) -> None:
        """Update a tool's compatible_with/incompatible_with from build learnings."""
        tool = self.get_tool_by_id(tool_id)
        if not tool:
            return
        if compatible:
            tool.compatible_with = list(set(tool.compatible_with + compatible))
        if incompatible:
            tool.incompatible_with = list(set(tool.incompatible_with + incompatible))
        col = self.collection("tool_schemas")
        col.update(
            ids=[tool_id],
            metadatas=[{
                "id": tool.id,
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
                "accepts": json.dumps(tool.accepts),
                "outputs": json.dumps(tool.outputs),
                "output_format": tool.output_format,
                "limitations": json.dumps(tool.limitations),
                "dependencies": json.dumps(tool.dependencies),
                "compatible_with": json.dumps(tool.compatible_with),
                "incompatible_with": json.dumps(tool.incompatible_with),
                "code_template": tool.code_template,
            }],
        )

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _flatten_results(results: dict) -> list[dict]:
        flat = []
        if not results["documents"] or not results["documents"][0]:
            return flat
        for i, doc in enumerate(results["documents"][0]):
            entry = {"document": doc}
            if results["metadatas"] and results["metadatas"][0]:
                entry["metadata"] = results["metadatas"][0][i]
            if results["distances"] and results["distances"][0]:
                entry["distance"] = results["distances"][0][i]
            flat.append(entry)
        return flat

    def stats(self) -> dict[str, int]:
        return {name: col.count() for name, col in self._collections.items()}
