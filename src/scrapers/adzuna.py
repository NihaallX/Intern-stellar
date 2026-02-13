"""
Adzuna Jobs API scraper.
Clean, structured job data from a major job aggregator.
API Docs: https://developer.adzuna.com/
"""

import requests
from typing import Optional
from src.models import Job
from src.utils.config import get_adzuna_credentials


def scrape_adzuna_jobs(max_results: int = 50) -> list[Job]:
    """
    Scrape jobs from Adzuna API.
    
    Args:
        max_results: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    try:
        app_id, app_key = get_adzuna_credentials()
        if not app_id or not app_key:
            print("[Adzuna] API credentials not found, skipping")
            return []
    except Exception as e:
        print(f"[Adzuna] Error getting credentials: {e}")
        return []
    
    # Search parameters for AI/ML jobs
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": min(max_results, 50),  # API limit
        "what": "machine learning OR artificial intelligence OR AI engineer OR ML engineer",
        "where": "US",
        "sort_by": "date",
        "content-type": "application/json"
    }
    
    try:
        print("[Adzuna] Fetching jobs...")
        response = requests.get(
            "https://api.adzuna.com/v1/api/jobs/us/search/1",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        jobs = []
        for result in data.get("results", []):
            try:
                # Extract job data
                title = result.get("title", "Unknown")
                company = result.get("company", {}).get("display_name", "Unknown")
                location = result.get("location", {}).get("display_name", "Unknown")
                url = result.get("redirect_url", "")
                description = result.get("description", "")
                
                # Check if remote
                remote = "remote" in description.lower() or "remote" in title.lower()
                
                job = Job(
                    title=title,
                    company=company,
                    url=url,
                    source="adzuna",
                    location=location,
                    remote=remote,
                    paid=True,
                    description=description[:5000],
                    requirements=[]
                )
                job.job_id = job.generate_job_id()
                jobs.append(job)
                
            except Exception as e:
                print(f"[Adzuna] Error parsing job: {e}")
                continue
        
        print(f"[Adzuna] Found {len(jobs)} jobs")
        return jobs
        
    except Exception as e:
        print(f"[Adzuna] API error: {e}")
        return []


if __name__ == "__main__":
    jobs = scrape_adzuna_jobs(max_results=10)
    for job in jobs:
        print(f"- {job.company}: {job.title} ({job.location})")
