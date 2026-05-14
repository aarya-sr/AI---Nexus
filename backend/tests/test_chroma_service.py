"""Tests for ChromaService — all 4 collections, seeding, RAG queries, writes."""
import json
import shutil
import tempfile
from pathlib import Path

import pytest

from app.models.tools import ToolSchema
from app.services.chroma_service import ChromaService, COLLECTIONS

TOOL_LIBRARY_DIR = Path(__file__).parent.parent / "app" / "tool_library"

SAMPLE_TOOL = {
    "id": "test_tool_alpha",
    "name": "Alpha Tool",
    "description": "Processes alpha data streams",
    "category": "data_processing",
    "accepts": ["json", "csv"],
    "outputs": ["json"],
    "output_format": "json",
    "limitations": ["max 100MB input"],
    "dependencies": ["pandas>=2.0.0"],
    "code_template": "def alpha(data): return data",
    "compatible_with": ["test_tool_beta"],
    "incompatible_with": [],
}

SAMPLE_TOOL_BETA = {
    "id": "test_tool_beta",
    "name": "Beta Tool",
    "description": "Generates reports from structured data",
    "category": "generation",
    "accepts": ["json"],
    "outputs": ["markdown", "pdf"],
    "output_format": "markdown",
    "limitations": [],
    "dependencies": [],
    "code_template": "def beta(data): return str(data)",
    "compatible_with": [],
    "incompatible_with": [],
}


@pytest.fixture()
def chroma_dir():
    d = tempfile.mkdtemp(prefix="chroma_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture()
def svc(chroma_dir):
    return ChromaService(persist_dir=chroma_dir)


@pytest.fixture()
def tool_dir(tmp_path):
    for tool_data in [SAMPLE_TOOL, SAMPLE_TOOL_BETA]:
        (tmp_path / f"{tool_data['id']}.json").write_text(json.dumps(tool_data))
    return tmp_path


# ── Initialization ────────────────────────────────────────────────


class TestInit:
    def test_creates_all_four_collections(self, svc):
        for name in COLLECTIONS:
            assert svc.collection(name) is not None

    def test_stats_all_zero_on_init(self, svc):
        stats = svc.stats()
        assert stats == {c: 0 for c in COLLECTIONS}


# ── Tool Seeding ──────────────────────────────────────────────────


class TestSeedTools:
    def test_seed_from_fixture_dir(self, svc, tool_dir):
        count = svc.seed_tools(tool_dir)
        assert count == 2
        assert svc.stats()["tool_schemas"] == 2

    def test_seed_real_tool_library(self, svc):
        count = svc.seed_tools(TOOL_LIBRARY_DIR)
        json_count = len(list(TOOL_LIBRARY_DIR.glob("*.json")))
        assert count == json_count
        assert svc.stats()["tool_schemas"] == json_count

    def test_seed_is_idempotent(self, svc, tool_dir):
        svc.seed_tools(tool_dir)
        svc.seed_tools(tool_dir)
        assert svc.stats()["tool_schemas"] == 2

    def test_seed_empty_dir(self, svc, tmp_path):
        count = svc.seed_tools(tmp_path)
        assert count == 0


# ── Tool RAG Queries ──────────────────────────────────────────────


class TestFindTools:
    def test_finds_relevant_tool(self, svc, tool_dir):
        svc.seed_tools(tool_dir)
        results = svc.find_tools_for_capability("process alpha data")
        assert any(t.id == "test_tool_alpha" for t in results)

    def test_returns_tool_schema_objects(self, svc, tool_dir):
        svc.seed_tools(tool_dir)
        results = svc.find_tools_for_capability("generate reports")
        assert all(isinstance(t, ToolSchema) for t in results)

    def test_tool_fields_roundtrip(self, svc, tool_dir):
        svc.seed_tools(tool_dir)
        tool = svc.get_tool_by_id("test_tool_alpha")
        assert tool is not None
        assert tool.name == "Alpha Tool"
        assert tool.category == "data_processing"
        assert tool.accepts == ["json", "csv"]
        assert tool.outputs == ["json"]
        assert tool.output_format == "json"
        assert tool.limitations == ["max 100MB input"]
        assert tool.dependencies == ["pandas>=2.0.0"]
        assert tool.code_template == "def alpha(data): return data"
        assert tool.compatible_with == ["test_tool_beta"]
        assert tool.incompatible_with == []

    def test_get_tool_by_id_missing(self, svc, tool_dir):
        svc.seed_tools(tool_dir)
        assert svc.get_tool_by_id("nonexistent_tool") is None

    def test_n_results_caps_output(self, svc, tool_dir):
        svc.seed_tools(tool_dir)
        results = svc.find_tools_for_capability("data", n_results=1)
        assert len(results) == 1


# ── Real Tool Library RAG ────────────────────────────────────────


class TestRealToolLibrary:
    def test_pdf_extraction_query(self, svc):
        svc.seed_tools(TOOL_LIBRARY_DIR)
        results = svc.find_tools_for_capability("extract text from PDF documents")
        assert any(t.id == "pdf_parser_pymupdf" for t in results)

    def test_financial_calc_query(self, svc):
        svc.seed_tools(TOOL_LIBRARY_DIR)
        results = svc.find_tools_for_capability(
            "calculate financial metrics like debt-to-income ratio"
        )
        assert any(t.id == "financial_calculator" for t in results)

    def test_csv_ingestion_query(self, svc):
        svc.seed_tools(TOOL_LIBRARY_DIR)
        results = svc.find_tools_for_capability("parse and ingest CSV spreadsheet data")
        assert any(t.id == "csv_parser" for t in results)


# ── Spec Patterns ────────────────────────────────────────────────


class TestSpecPatterns:
    def test_empty_collection_returns_empty(self, svc):
        assert svc.find_similar_specs("anything") == []

    def test_store_and_retrieve(self, svc):
        svc.store_spec_pattern(
            "spec_001",
            "Loan underwriting: process bank statements, produce risk scores",
            {"domain": "finance", "outcome": "success"},
        )
        results = svc.find_similar_specs("credit risk assessment from bank documents")
        assert len(results) == 1
        assert "Loan underwriting" in results[0]["document"]
        assert results[0]["metadata"]["domain"] == "finance"
        assert "distance" in results[0]

    def test_upsert_overwrites(self, svc):
        svc.store_spec_pattern("spec_001", "version 1", {"v": "1"})
        svc.store_spec_pattern("spec_001", "version 2", {"v": "2"})
        results = svc.find_similar_specs("version")
        assert len(results) == 1
        assert results[0]["metadata"]["v"] == "2"


# ── Anti-Patterns ────────────────────────────────────────────────


class TestAntiPatterns:
    def test_empty_collection_returns_empty(self, svc):
        assert svc.check_anti_patterns("anything") == []

    def test_store_and_retrieve(self, svc):
        svc.store_anti_pattern(
            "anti_001",
            "Never use pymupdf alone for scanned documents — needs OCR fallback",
            {"severity": "high", "domain": "document_extraction"},
        )
        results = svc.check_anti_patterns("using pymupdf for scanned PDFs")
        assert len(results) == 1
        assert "pymupdf" in results[0]["document"]


# ── Domain Insights ──────────────────────────────────────────────


class TestDomainInsights:
    def test_empty_collection_returns_empty(self, svc):
        assert svc.find_domain_insights("anything") == []

    def test_store_and_retrieve(self, svc):
        svc.store_domain_insight(
            "insight_001",
            "Bank statement formats vary widely — extraction confidence scoring is essential",
            {"domain": "loan_underwriting"},
        )
        results = svc.find_domain_insights("processing bank statements")
        assert len(results) == 1
        assert "confidence scoring" in results[0]["document"]


# ── Tool Compatibility Updates ───────────────────────────────────


class TestToolCompatibility:
    def test_add_compatible(self, svc, tool_dir):
        svc.seed_tools(tool_dir)
        svc.update_tool_compatibility(
            "test_tool_alpha", compatible=["report_generator"]
        )
        tool = svc.get_tool_by_id("test_tool_alpha")
        assert "report_generator" in tool.compatible_with
        assert "test_tool_beta" in tool.compatible_with  # original preserved

    def test_add_incompatible(self, svc, tool_dir):
        svc.seed_tools(tool_dir)
        svc.update_tool_compatibility(
            "test_tool_alpha", incompatible=["broken_tool"]
        )
        tool = svc.get_tool_by_id("test_tool_alpha")
        assert "broken_tool" in tool.incompatible_with

    def test_update_nonexistent_tool_is_noop(self, svc, tool_dir):
        svc.seed_tools(tool_dir)
        svc.update_tool_compatibility("ghost_tool", compatible=["x"])
        # no error raised

    def test_deduplicates(self, svc, tool_dir):
        svc.seed_tools(tool_dir)
        svc.update_tool_compatibility(
            "test_tool_alpha", compatible=["test_tool_beta"]
        )
        tool = svc.get_tool_by_id("test_tool_alpha")
        assert tool.compatible_with.count("test_tool_beta") == 1
