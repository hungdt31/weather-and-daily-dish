import re
from PyPDF2 import PdfReader

def load_faq_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

def parse_faq(text):
    faq_pairs = []
    pattern = r"Q:\s*(.*?)\s*A:\s*(.*?)(?=\n\s*\d+\.\s*Q:|\Z)"
    matches = re.findall(pattern, text, re.DOTALL)
    for q, a in matches:
        faq_pairs.append({
            "question": clean_text(q.lower()),
            "answer": clean_text(a)
        })
    return faq_pairs

def route_query(query):
    weather_keywords = ["weather", "rain", "raining", "forecast", "temperature", "hot", "cold", "humidity"]
    query = query.lower()
    for word in weather_keywords:
        if word in query:
            return "weather"
    return "daily_dish"

def extract_city(query, default_city="New York"):
    # Simple regex to catch cities following "in", "at", or "for"
    match = re.search(r"\b(?:in|at|for)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b", query, re.IGNORECASE)
    if match:
        return match.group(1).strip().title()
    return default_city
