from crewai import Crew, Task, Process
from agents import create_agents

def create_crew() -> Crew:
    agents = create_agents()
    tasks = [
        Task(description="Ingest and extract structured fields from PDF documents.", agent=agents["document_ingestion"], expected_output="json"),
        Task(description="Ensure consistency of applicant identity information across all documents.", agent=agents["identity_verification"], expected_output="json"),
        Task(description="Validate the applicant's income and employment details using provided documents.", agent=agents["income_employment_check"], expected_output="json"),
        Task(description="Perform credit analysis using verified income data to calculate DTI.", agent=agents["credit_analysis"], expected_output="json"),
        Task(description="Aggregate all factors into a final risk score and generate a recommendation.", agent=agents["risk_scoring"], expected_output="json"),
    ]
    return Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
    )
