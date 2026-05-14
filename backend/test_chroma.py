"""Quick smoke test for ChromaService — run free, no API keys needed."""
import sys
import shutil
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.chroma_service import ChromaService

TEST_DIR = "./chroma_test_data"


def main():
    # Clean slate
    if Path(TEST_DIR).exists():
        shutil.rmtree(TEST_DIR)

    svc = ChromaService(persist_dir=TEST_DIR)

    # 1. Seed tools
    tool_dir = Path(__file__).parent / "app" / "tool_library"
    count = svc.seed_tools(tool_dir)
    print(f"Seeded {count} tools")

    # 2. Check stats
    stats = svc.stats()
    print(f"Collection stats: {stats}")
    assert stats["tool_schemas"] == count, f"Expected {count} tools, got {stats['tool_schemas']}"

    # 3. RAG query: find tools for PDF extraction
    results = svc.find_tools_for_capability("extract text from PDF documents")
    print(f"\nQuery 'extract text from PDF documents' → {len(results)} results:")
    for t in results:
        print(f"  - {t.id}: accepts={t.accepts}, outputs={t.outputs}")
    assert any(t.id == "pdf_parser_pymupdf" for t in results), "pdf_parser_pymupdf should match"

    # 4. RAG query: find tools for financial calculation
    results = svc.find_tools_for_capability("calculate financial metrics like debt-to-income ratio")
    print(f"\nQuery 'calculate financial metrics' → {len(results)} results:")
    for t in results:
        print(f"  - {t.id}: category={t.category}")
    assert any(t.id == "financial_calculator" for t in results), "financial_calculator should match"

    # 5. RAG query: find tools for CSV data ingestion
    results = svc.find_tools_for_capability("parse and ingest CSV spreadsheet data")
    print(f"\nQuery 'parse CSV data' → {len(results)} results:")
    for t in results:
        print(f"  - {t.id}: accepts={t.accepts}")
    assert any(t.id == "csv_parser" for t in results), "csv_parser should match"

    # 6. Get tool by ID
    tool = svc.get_tool_by_id("rule_engine")
    print(f"\nGet by ID 'rule_engine': {tool.name}")
    assert tool is not None
    assert tool.category == "reasoning"

    # 7. Store and query spec pattern
    svc.store_spec_pattern(
        "spec_test_001",
        "Loan underwriting domain. Process bank statement PDFs to produce risk score and report.",
        {"domain": "loan_underwriting", "outcome": "success", "framework": "crewai"},
    )
    matches = svc.find_similar_specs("Process financial documents and assess credit risk")
    print(f"\nSpec pattern query → {len(matches)} matches:")
    for m in matches:
        print(f"  - {m['document'][:60]}... (distance: {m.get('distance', 'N/A')})")
    assert len(matches) == 1

    # 8. Store and query anti-pattern
    svc.store_anti_pattern(
        "anti_test_001",
        "Do not assign pdf_parser_pymupdf as sole extraction tool when requirements include scanned documents",
        {"domain": "loan_underwriting", "severity": "high"},
    )
    anti = svc.check_anti_patterns("using pymupdf for scanned document extraction")
    print(f"\nAnti-pattern query → {len(anti)} matches:")
    for a in anti:
        print(f"  - {a['document'][:60]}...")
    assert len(anti) == 1

    # 9. Store and query domain insight
    svc.store_domain_insight(
        "insight_test_001",
        "Bank statement formats vary widely — extraction confidence scoring is essential",
        {"domain": "loan_underwriting", "outcome": "success"},
    )
    insights = svc.find_domain_insights("loan underwriting document processing tips")
    print(f"\nDomain insight query → {len(insights)} matches:")
    for ins in insights:
        print(f"  - {ins['document'][:60]}...")
    assert len(insights) == 1

    # 10. Update tool compatibility
    svc.update_tool_compatibility("pdf_parser_pymupdf", compatible=["report_generator"])
    updated = svc.get_tool_by_id("pdf_parser_pymupdf")
    print(f"\nUpdated pdf_parser_pymupdf compatible_with: {updated.compatible_with}")
    assert "report_generator" in updated.compatible_with

    # Cleanup
    shutil.rmtree(TEST_DIR)
    print("\n--- ALL TESTS PASSED ---")


if __name__ == "__main__":
    main()
