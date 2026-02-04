"""
YC Work at a Startup scraper.

Scrapes job listings from workatastartup.com/jobs (YC startups).
"""

import logging
import re
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
    base_url = "https://www.workatastartup.com"
    
    try:
        # First, try to get the jobs page
        logger.info(f"Fetching YC jobs from {base_url}/jobs")
        response = requests.get(
            f"{base_url}/jobs",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            timeout=15
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find job cards - YC uses various structures, try multiple selectors
        job_cards = soup.find_all('div', class_=re.compile(r'job|listing|card', re.I))
        
        if not job_cards:
            # Fallback: look for any divs with links to /jobs/
            job_cards = soup.find_all('a', href=re.compile(r'/jobs/\d+'))
            
        logger.info(f"Found {len(job_cards)} potential job cards on YC")
        
        for card in job_cards[:max_results]:
            try:
                # Try to extract job info from the card
                # Look for job title
                title_elem = card.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|heading', re.I))
                if not title_elem:
                    title_elem = card.find('a', href=re.compile(r'/jobs/'))
                    
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                
                # Look for company name
                company_elem = card.find(['div', 'span', 'a'], class_=re.compile(r'company|startup', re.I))
                company = company_elem.get_text(strip=True) if company_elem else "YC Startup"
                
                # Look for location
                location_elem = card.find(['div', 'span'], class_=re.compile(r'location|place', re.I))
                location = location_elem.get_text(strip=True) if location_elem else "Remote"
                
                # Look for job URL
                link_elem = card.find('a', href=re.compile(r'/jobs/'))
                if not link_elem and card.name == 'a':
                    link_elem = card
                    
                job_url = ""
                if link_elem:
                    href = link_elem.get('href', '')
                    if href.startswith('/'):
                        job_url = f"{base_url}{href}"
                    else:
                        job_url = href
                
                # Get job description - try to fetch full job page
                description = title  # Default to title
                if job_url:
                    try:
                        job_response = requests.get(
                            job_url,
                            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                            timeout=10
                        )
                        if job_response.status_code == 200:
                            job_soup = BeautifulSoup(job_response.text, 'html.parser')
                            # Look for description
                            desc_elem = job_soup.find(['div', 'section'], class_=re.compile(r'description|about|details', re.I))
                            if desc_elem:
                                description = desc_elem.get_text(strip=True, separator=' ')[:2000]
                    except Exception as e:
                        logger.debug(f"Could not fetch job details from {job_url}: {e}")
                
                if title and len(title) > 3:
                    jobs.append(Job(
                        title=title,
                        company=company,
                        location=location,
                        description=description,
                        url=job_url or base_url,
                        source="YC Work at a Startup"
                    ))
                    logger.debug(f"Scraped YC job: {title} at {company}")
                    
            except Exception as e:
                logger.debug(f"Error parsing YC job card: {e}")
                continue
        
        logger.info(f"Successfully scraped {len(jobs)} jobs from YC Work at a Startup")
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch YC jobs: {e}")
    except Exception as e:
        logger.error(f"Unexpected error scraping YC jobs: {e}")
    
    return jobs[:max_results]
