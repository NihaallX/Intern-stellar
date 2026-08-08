"""
Himalayas job scraper.
Clean remote job board with AI/ML category.
No authentication required.
"""

import requests
from bs4 import BeautifulSoup
from src.models import Job


def scrape_himalayas_jobs(max_results: int = 50) -> list[Job]:
    """
    Scrape AI/ML jobs from Himalayas.app.
    
    Args:
        max_results: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    try:
        # Himalayas AI/ML category
        url = "https://himalayas.app/jobs/ai-ml"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        
        print("[Himalayas] Fetching jobs...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        jobs = []
        
        # Find job listings (Himalayas uses article tags)
        job_listings = soup.find_all('article', class_='job')
        if not job_listings:
            # Try alternative selector
            job_listings = soup.find_all('div', class_='job-card')
        
        for listing in job_listings[:max_results]:
            try:
                # Extract job details
                title_elem = listing.find('h3') or listing.find('h2')
                company_elem = listing.find('span', class_='company-name') or listing.find('div', class_='company')
                link_elem = listing.find('a', href=True)
                
                if not title_elem or not link_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                
                # Build full URL
                job_url = link_elem['href']
                if not job_url.startswith('http'):
                    job_url = f"https://himalayas.app{job_url}"
                
                # Try to get location
                location = "Remote"
                location_elem = listing.find('span', class_='location') or listing.find('div', class_='location')
                if location_elem:
                    location = location_elem.get_text(strip=True)
                
                job = Job(
                    title=title,
                    company=company,
                    url=job_url,
                    source="himalayas",
                    location=location,
                    remote=True,
                    paid=True,
                    description="",  # Would need separate request
                    requirements=[]
                )
                job.job_id = job.generate_job_id()
                jobs.append(job)
                
            except Exception as e:
                print(f"[Himalayas] Error parsing job: {e}")
                continue
        
        print(f"[Himalayas] Found {len(jobs)} jobs")
        return jobs
        
    except Exception as e:
        print(f"[Himalayas] Error: {e}")
        return []


if __name__ == "__main__":
    jobs = scrape_himalayas_jobs(max_results=10)
    for job in jobs:
        print(f"- {job.company}: {job.title}")
