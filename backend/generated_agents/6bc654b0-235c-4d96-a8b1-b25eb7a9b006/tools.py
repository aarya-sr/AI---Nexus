from crewai.tools import tool
import fitz
import pytesseract
from PIL import Image

@tool("PyMuPDF PDF Parser")
def pdf_parser_pymupdf(file_path: str, extract_tables: bool = True) -> dict:
    """Extracts text and tables from PDF files using PyMuPDF (fitz). Handles multi-page digital PDFs. Does not support OCR for scanned documents."""
    doc = fitz.open(file_path)
    pages = []
    for page in doc:
        page_data = {"page": page.number + 1, "text": page.get_text()}
        if extract_tables:
            page_data["tables"] = page.find_tables()
        pages.append(page_data)
    doc.close()
    return {"pages": pages, "total_pages": len(pages)}

@tool("Tesseract OCR")
def ocr_tesseract(file_path: str, language: str = "eng") -> dict:
    """Extracts text from images and scanned PDFs using Tesseract OCR engine. Accuracy varies with image quality."""
    image = Image.open(file_path)
    text = pytesseract.image_to_string(image, lang=language)
    confidence_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    avg_confidence = sum(float(c) for c in confidence_data["conf"] if c != "-1") / max(len([c for c in confidence_data["conf"] if c != "-1"]), 1)
    return {"text": text, "confidence": round(avg_confidence / 100, 2)}

@tool("Rule Engine")
def rule_engine(data: dict, rules: list[dict] | None = None) -> dict:
    """Evaluates data against a set of rules and produces pass/fail results with reasoning. Rules are defined as JSON objects with condition and threshold fields."""
    if rules is None:
        rules = [
            {"name": "dti_check", "field": "dti_ratio", "operator": "<=", "threshold": 0.43, "weight": 0.3},
            {"name": "income_stability", "field": "income_stability", "operator": ">=", "threshold": 0.5, "weight": 0.3},
            {"name": "overdraft_check", "field": "overdraft_count", "operator": "<=", "threshold": 2, "weight": 0.2},
            {"name": "unusual_tx", "field": "unusual_transactions", "operator": "<=", "threshold": 3, "weight": 0.2},
        ]
    results = []
    score = 0.0
    for rule in rules:
        value = data.get(rule["field"])
        if value is None:
            results.append({"rule": rule["name"], "passed": False, "reason": f"Missing field: {rule['field']}"})
            continue
        op = rule["operator"]
        threshold = rule["threshold"]
        passed = (op == "<=" and value <= threshold) or (op == ">=" and value >= threshold) or (op == "<" and value < threshold) or (op == ">" and value > threshold) or (op == "==" and value == threshold)
        if passed:
            score += rule.get("weight", 0)
        results.append({"rule": rule["name"], "passed": passed, "value": value, "threshold": threshold, "reason": f"{rule['field']} {'passed' if passed else 'failed'}: {value} {op} {threshold}"})
    risk_score = round(1 - score, 4)
    return {"risk_score": risk_score, "rule_results": results, "reasoning": "; ".join(r["reason"] for r in results)}

@tool("Financial Calculator")
def financial_calculator(data: dict) -> dict:
    """Calculates financial metrics from structured transaction data: debt-to-income ratio, income stability, overdraft frequency, and unusual transaction flags."""
    transactions = data.get("transactions", [])
    incomes = [t["amount"] for t in transactions if t.get("amount", 0) > 0]
    expenses = [abs(t["amount"]) for t in transactions if t.get("amount", 0) < 0]
    total_income = sum(incomes)
    total_expenses = sum(expenses)
    dti = round(total_expenses / max(total_income, 1), 4)
    overdrafts = sum(1 for t in transactions if t.get("amount", 0) < -1000)
    avg_income = total_income / max(len(incomes), 1)
    income_variance = sum((i - avg_income) ** 2 for i in incomes) / max(len(incomes), 1)
    income_stability = round(1 - min(income_variance / max(avg_income ** 2, 1), 1), 4)
    large_unusual = [t for t in transactions if abs(t.get("amount", 0)) > avg_income * 0.5 and t.get("category") not in ["payroll", "rent", "mortgage"]]
    return {"dti_ratio": dti, "income_stability": income_stability, "overdraft_count": overdrafts, "unusual_transactions": len(large_unusual), "total_income": total_income, "total_expenses": total_expenses}

@tool("Scoring Engine")
def scoring_engine(data: dict, weights: dict[str, float] | None = None) -> dict:
    """Produces weighted scores from metrics. Takes a set of metrics with weights and produces a composite score with per-metric breakdown and reasoning."""
    metrics = data.get("statistics", data)
    if weights is None:
        fields = list(metrics.keys())
        weights = {f: 1.0 / len(fields) for f in fields}
    scores = {}
    total_score = 0.0
    for field, weight in weights.items():
        if field not in metrics:
            scores[field] = {"score": 0, "weight": weight, "reason": f"Missing metric: {field}"}
            continue
        value = metrics[field] if isinstance(metrics[field], (int, float)) else metrics[field].get("mean", 0)
        normalized = min(max(value / 100, 0), 1)
        weighted = normalized * weight
        total_score += weighted
        scores[field] = {"raw_value": value, "normalized": round(normalized, 4), "weighted": round(weighted, 4), "weight": weight}
    return {"total_score": round(total_score, 4), "per_metric": scores, "reasoning": "; ".join(f"{k}: {v.get('weighted', 0):.4f} (weight {v['weight']})" for k, v in scores.items())}

@tool("Report Generator")
def report_generator(data: dict, title: str = "Analysis Report") -> dict:
    """Generates human-readable markdown or PDF reports from structured JSON analysis data. Produces formatted reports with sections, tables, and summaries."""
    sections = []
    sections.append(f"# {title}\n")
    sections.append(f"## Executive Summary\n")
    if "risk_score" in data:
        risk_level = "Low" if data["risk_score"] < 0.3 else "Medium" if data["risk_score"] < 0.6 else "High"
        sections.append(f"**Risk Score:** {data['risk_score']} ({risk_level} Risk)\n")
    if "rule_results" in data:
        sections.append("## Detailed Analysis\n")
        for result in data["rule_results"]:
            status = "PASS" if result["passed"] else "FAIL"
            sections.append(f"- **{result['rule']}**: {status}  {result['reason']}")
        sections.append("")
    if "reasoning" in data:
        sections.append(f"## Reasoning\n\n{data['reasoning']}\n")
    report_md = "\n".join(sections)
    summary = f"Risk assessment complete. Score: {data.get('risk_score', 'N/A')}."
    return {"report_markdown": report_md, "executive_summary": summary}
