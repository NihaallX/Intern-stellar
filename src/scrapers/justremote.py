"""
JustRemote job scraper.
Remote job board with AI/ML category.
No authentication required.
"""

import requests
from bs4 import BeautifulSoup
from src.models import Job


def scrape_justremote_jobs(max_results: int = 50) -> list[Job]:
    """
    Scrape AI/ML jobs from JustRemote.co.
    
    Args:
        max_results: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    try:
        # JustRemote search for AI/ML jobs
        url = "https://justremote.co/remote-jobs?search=machine+learning+OR+AI"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://justremote.co/"
        }
        
        print("[JustRemote] Fetching jobs...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        jobs = []
        
        # Find job listings
        job_listings = soup.find_all('div', class_='job-card') or soup.find_all('article', class_='job')
        
        for listing in job_listings[:max_results]:
            try:
                # Extract job details
                title_elem = listing.find('h2') or listing.find('h3') or listing.find('a', class_='title')
                company_elem = listing.find('span', class_='company') or listing.find('div', class_='company-name')
                link_elem = listing.find('a', href=True)
                
                if not title_elem or not link_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                
                # Build full URL
                job_url = link_elem['href']
                if not job_url.startswith('http'):
                    job_url = f"https://justremote.co{job_url}"
                
                # Location is always remote
                location = "Remote"
                
                job = Job(
                    title=title,
                    company=company,
                    url=job_url,
                    source="justremote",
                    location=location,
                    remote=True,
                    paid=True,
                    description="",  # Would need separate request
                    requirements=[]
                )
                job.job_id = job.generate_job_id()
                jobs.append(job)
                
            except Exception as e:
                print(f"[JustRemote] Error parsing job: {e}")
                continue
        
        print(f"[JustRemote] Found {len(jobs)} jobs")
        return jobs
        
    except Exception as e:
        print(f"[JustRemote] Error: {e}")
        return []


if __name__ == "__main__":
    jobs = scrape_justremote_jobs(max_results=10)
    for job in jobs:
        print(f"- {job.company}: {job.title}")
