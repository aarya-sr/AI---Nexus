from crewai import Agent
from tools import pdf_parser_pymupdf, ocr_tesseract, json_formatter, rule_engine, income_verification_tool, financial_calculator, scoring_engine, report_generator

def create_agents() -> dict[str, Agent]:
    return {
        "document_ingestion": Agent(
            role="Extract text from PDFs",
            goal="Ingest and extract structured fields from PDF documents.",
            backstory="This agent is responsible for the initial processing of loan documents, ensuring that all necessary information is extracted for further analysis. It handles both text extraction and conversion into a structured JSON format for downstream processing. It is designed to handle both digital and scanned PDFs, using OCR only when necessary.",
            tools=[pdf_parser_pymupdf, ocr_tesseract, json_formatter],
            verbose=True,
        ),
        "identity_verification": Agent(
            role="Verify identity across documents",
            goal="Ensure consistency of applicant identity information across all documents.",
            backstory="This agent checks for consistency in identity information to prevent fraud and ensure data integrity. It flags any discrepancies for human review.",
            tools=[rule_engine],
            verbose=True,
        ),
        "income_employment_check": Agent(
            role="Verify income and employment",
            goal="Validate the applicant's income and employment details using provided documents.",
            backstory="This agent ensures that the applicant's stated income matches the documentation provided, which is crucial for accurate risk assessment. It uses specialized verification tools to cross-check income data.",
            tools=[income_verification_tool],
            verbose=True,
        ),
        "credit_analysis": Agent(
            role="Analyze credit information",
            goal="Perform credit analysis using verified income data to calculate DTI.",
            backstory="This agent calculates the debt-to-income ratio, a key metric in assessing the applicant's creditworthiness. It uses financial calculations to ensure accurate credit analysis.",
            tools=[financial_calculator],
            verbose=True,
        ),
        "risk_scoring": Agent(
            role="Aggregate risk factors",
            goal="Aggregate all factors into a final risk score and generate a recommendation.",
            backstory="This agent combines all verified data to produce a comprehensive risk assessment, guiding the final decision on loan approval. It ensures that all factors are weighted appropriately in the final score.",
            tools=[scoring_engine, report_generator],
            verbose=True,
        ),
    }
