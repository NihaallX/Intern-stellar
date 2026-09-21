"""Lever public postings scraper."""
import requests
from ..models import Job

DEFAULT_COMPANIES = ["anthropic", "scaleai", "openai", "perplexity"]

def scrape_lever_jobs(companies=None, max_results=50):
    jobs = []
    for company in companies or DEFAULT_COMPANIES:
        try:
            items = requests.get(f"https://api.lever.co/v0/postings/{company}", params={"mode": "json"}, timeout=20).json()
            for item in items if isinstance(items, list) else []:
                title = item.get("text", "")
                desc = item.get("descriptionPlain", "")
                if not any(k in f"{title} {desc}".lower() for k in ("product", "solution", "program", "operations", "strategy")):
                    continue
                cats = item.get("categories", {})
                loc = cats.get("location", "Unknown")
                jobs.append(Job(title=title, company=company, url=item.get("hostedUrl", ""), source="lever", location=loc, remote="remote" in loc.lower(), description=desc[:5000]))
                if len(jobs) >= max_results: return jobs
        except Exception as exc:
            print(f"[Lever] {company}: {exc}")
    return jobs
