"""Greenhouse public board scraper."""
import requests
from ..models import Job

DEFAULT_COMPANIES = ["openai", "anthropic", "huggingface", "scaleai", "cursor", "perplexity"]

def scrape_greenhouse_jobs(companies=None, max_results=50):
    jobs = []
    for company in companies or DEFAULT_COMPANIES:
        try:
            data = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs", params={"content": "true"}, timeout=20).json()
            for item in data.get("jobs", []):
                title = item.get("title", "")
                text = f"{title} {item.get('content', '')}".lower()
                if not any(k in text for k in ("product", "solution", "program", "operations", "strategy")):
                    continue
                loc = (item.get("location") or {}).get("name", "Unknown")
                jobs.append(Job(title=title, company=company, url=item.get("absolute_url", ""), source="greenhouse", location=loc, remote="remote" in loc.lower(), description=item.get("content", "")[:5000]))
                if len(jobs) >= max_results: return jobs
        except Exception as exc:
            print(f"[Greenhouse] {company}: {exc}")
    return jobs
