"""
YC Work at a Startup scraper.

Scrapes job listings from workatastartup.com.
"""

import logging
from typing import List

import requests
from bs4 import BeautifulSoup

from ..models import Job

logger = logging.getLogger(__name__)


def scrape_ycombinator_jobs(max_results: int = 30) -> List[Job]:
    """
    Scrape job listings from YC Work at a Startup.
    
    Args:
        max_results: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    jobs = []
    
    try:
        # Fetch main jobs page
        url = "https://www.workatastartup.com/jobs"
        
        logger.info(f"Fetching YC jobs from {url}")
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            timeout=20
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all job links - YC uses both workatastartup.com and ycombinator.com URLs
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '')
            
            # Look for actual job posting URLs (contain /jobs/ followed by ID)
            if not '/jobs/' in href:
                continue
            
            # Skip generic category pages like /jobs/l/software-engineer
            if '/jobs/l/' in href:
                continue
            
            # Build full URL
            if href.startswith('/'):
                if 'companies' in href:
                    job_url = f"https://www.ycombinator.com{href}"
                else:
                    job_url = f"https://www.workatastartup.com{href}"
            elif href.startswith('http'):
                job_url = href
            else:
                continue
            
            # Extract title from link text
            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            
            # Skip if title is generic
            if title.lower() in ['learn more', 'apply', 'view job', 'see more']:
                continue
            
            # Parse company name from URL
            company = "YC Startup"
            if '/companies/' in job_url:
                parts = job_url.split('/companies/')[1].split('/')
                if len(parts) > 0:
                    company = parts[0].replace('-', ' ').title()
            
            # Try to find location nearby
            location = "Remote"
            parent = link.parent
            if parent:
                location_text = parent.get_text()
                if 'remote' in location_text.lower():
                    location = "Remote"
                elif 'san francisco' in location_text.lower():
                    location = "San Francisco"
            
            job = Job(
                title=title,
                company=company,
                location=location,
                description=f"{title} at {company}",  # Minimal description
                url=job_url,
                source="YC Work at a Startup",
                remote='remote' in location.lower()
            )
            jobs.append(job)
            logger.debug(f"Found YC job: {title} at {company}")
            
            if len(jobs) >= max_results:
                break
        
        logger.info(f"Successfully scraped {len(jobs)} jobs from YC")
        
    except Exception as e:
        logger.error(f"Error scraping YC jobs: {e}")
    
    return jobs[:max_results]
