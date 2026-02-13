"""
We Work Remotely job scraper.
Focused on remote AI/ML jobs.
"""

import requests
from bs4 import BeautifulSoup
from src.models import Job


def scrape_weworkremotely_jobs(max_results: int = 30) -> list[Job]:
    """
    Scrape AI/ML jobs from We Work Remotely.
    
    Args:
        max_results: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    try:
        # We Work Remotely AI/ML category
        url = "https://weworkremotely.com/remote-jobs/search?term=machine+learning+OR+AI"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://weworkremotely.com/",
            "DNT": "1"
        }
        
        print("[WeWorkRemotely] Fetching jobs...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        jobs = []
        
        # Find job listings
        job_listings = soup.find_all('li', class_='feature')
        
        for listing in job_listings[:max_results]:
            try:
                # Extract job details
                title_elem = listing.find('span', class_='title')
                company_elem = listing.find('span', class_='company')
                link_elem = listing.find('a')
                
                if not title_elem or not link_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                job_url = f"https://weworkremotely.com{link_elem['href']}"
                
                # Get job description (requires another request)
                description = ""
                try:
                    job_response = requests.get(job_url, headers=headers, timeout=15)
                    job_soup = BeautifulSoup(job_response.content, 'html.parser')
                    desc_elem = job_soup.find('div', class_='listing-container')
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)[:5000]
                except:
                    pass
                
                job = Job(
                    title=title,
                    company=company,
                    url=job_url,
                    source="weworkremotely",
                    location="Remote",
                    remote=True,
                    paid=True,
                    description=description,
                    requirements=[]
                )
                job.job_id = job.generate_job_id()
                jobs.append(job)
                
            except Exception as e:
                print(f"[WeWorkRemotely] Error parsing job: {e}")
                continue
        
        print(f"[WeWorkRemotely] Found {len(jobs)} jobs")
        return jobs
        
    except Exception as e:
        print(f"[WeWorkRemotely] Error: {e}")
        return []


if __name__ == "__main__":
    jobs = scrape_weworkremotely_jobs(max_results=5)
    for job in jobs:
        print(f"- {job.company}: {job.title}")
