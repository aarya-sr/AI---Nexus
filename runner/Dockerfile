FROM python:3.11-slim

RUN pip install --no-cache-dir \
    crewai \
    langgraph \
    langchain-core \
    langchain-openai \
    chromadb \
    pymupdf \
    pandas \
    requests \
    beautifulsoup4 \
    pydantic

WORKDIR /agent

CMD ["python", "main.py"]
