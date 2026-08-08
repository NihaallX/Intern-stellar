"""
RemoteOK job scraper.
One of the largest remote job boards with JSON API.
No authentication required.
"""

import requests
from src.models import Job


def scrape_remoteok_jobs(max_results: int = 50) -> list[Job]:
    """
    Scrape AI/ML jobs from RemoteOK.
    Uses their public JSON API - no auth required!
    
    Args:
        max_results: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    try:
        # RemoteOK has a public JSON API
        url = "https://remoteok.com/api"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        
        print("[RemoteOK] Fetching jobs...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        jobs = []
        
        # First item is metadata, skip it
        for item in data[1:]:
            try:
                # Filter for AI/ML jobs
                tags = item.get('tags', [])
                position = item.get('position', '').lower()
                
                # Check if AI/ML related
                ai_keywords = ['ai', 'ml', 'machine learning', 'artificial intelligence', 'deep learning', 'nlp', 'llm']
                is_ai_job = any(keyword in position for keyword in ai_keywords)
                is_ai_job = is_ai_job or any(keyword in str(tags).lower() for keyword in ai_keywords)
                
                if not is_ai_job:
                    continue
                
                title = item.get('position', 'Unknown')
                company = item.get('company', 'Unknown')
                url_link = item.get('url', '')
                description = item.get('description', '')
                location = item.get('location', 'Remote')
                
                job = Job(
                    title=title,
                    company=company,
                    url=url_link,
                    source="remoteok",
                    location=location,
                    remote=True,
                    paid=True,
                    description=description[:5000],
                    requirements=[]
                )
                job.job_id = job.generate_job_id()
                jobs.append(job)
                
                if len(jobs) >= max_results:
                    break
                    
            except Exception as e:
                print(f"[RemoteOK] Error parsing job: {e}")
                continue
        
        print(f"[RemoteOK] Found {len(jobs)} AI/ML jobs")
        return jobs
        
    except Exception as e:
        print(f"[RemoteOK] Error: {e}")
        return []


if __name__ == "__main__":
    jobs = scrape_remoteok_jobs(max_results=10)
    for job in jobs:
        print(f"- {job.company}: {job.title}")
