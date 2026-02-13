"""
Indeed Jobs API scraper via RapidAPI.
Clean, structured job data from Indeed.
API: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
"""

import requests
from typing import Optional
from src.models import Job
from src.utils.config import get_rapidapi_key


def scrape_indeed_jobs(max_results: int = 50) -> list[Job]:
    """
    Scrape jobs from Indeed via JSearch API on RapidAPI.
    
    Args:
        max_results: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    try:
        api_key = get_rapidapi_key()
        if not api_key:
            print("[Indeed] RapidAPI key not found, skipping")
            return []
    except Exception as e:
        print(f"[Indeed] Error getting API key: {e}")
        return []
    
    url = "https://jsearch.p.rapidapi.com/search"
    
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    # Search for AI/ML jobs
    params = {
        "query": "machine learning engineer OR AI engineer",
        "page": "1",
        "num_pages": "1",
        "date_posted": "month",
        "remote_jobs_only": "false"
    }
    
    try:
        print("[Indeed] Fetching jobs...")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        jobs = []
        for result in data.get("data", [])[:max_results]:
            try:
                title = result.get("job_title", "Unknown")
                company = result.get("employer_name", "Unknown")
                location = result.get("job_city", "Unknown")
                if result.get("job_state"):
                    location += f", {result['job_state']}"
                
                url_link = result.get("job_apply_link", result.get("job_google_link", ""))
                description = result.get("job_description", "")
                
                # Check remote
                remote = result.get("job_is_remote", False)
                
                job = Job(
                    title=title,
                    company=company,
                    url=url_link,
                    source="indeed",
                    location=location,
                    remote=remote,
                    paid=True,
                    description=description[:5000],
                    requirements=result.get("job_highlights", {}).get("Qualifications", [])
                )
                job.job_id = job.generate_job_id()
                jobs.append(job)
                
            except Exception as e:
                print(f"[Indeed] Error parsing job: {e}")
                continue
        
        print(f"[Indeed] Found {len(jobs)} jobs")
        return jobs
        
    except Exception as e:
        print(f"[Indeed] API error: {e}")
        return []


if __name__ == "__main__":
    jobs = scrape_indeed_jobs(max_results=10)
    for job in jobs:
        print(f"- {job.company}: {job.title} ({job.location})")
