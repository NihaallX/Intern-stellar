"""
YC Work at a Startup scraper.

Scrapes job listings from workatastartup.com using their search.
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
        # Search for AI/ML jobs on YC
        search_terms = ['machine learning', 'AI engineer', 'ML engineer', 'product manager AI']
        
        for search_term in search_terms:
            try:
                url = f"https://www.workatastartup.com/jobs?query={search_term.replace(' ', '+')}"
                
                logger.info(f"Fetching YC jobs for: {search_term}")
                response = requests.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                    timeout=20
                )
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all job links
                job_links = soup.find_all('a', href=lambda x: x and '/jobs/' in x)
                
                for link in job_links:
                    try:
                        href = link.get('href', '')
                        if not href or not '/jobs/' in href:
                            continue
                        
                        # Build full URL
                        if href.startswith('/'):
                            job_url = f"https://www.workatastartup.com{href}"
                        else:
                            job_url = href
                        
                        # Extract title from link text
                        title = link.get_text(strip=True)
                        if not title or len(title) < 3:
                            continue
                        
                        # Try to find company name nearby
                        company = "YC Startup"
                        parent = link.parent
                        if parent:
                            company_elem = parent.find('span', class_='company') or parent.find('div', class_='company')
                            if company_elem:
                                company = company_elem.get_text(strip=True)
                        
                        # Fetch job details
                        description = ""
                        location = "Remote"
                        try:
                            job_response = requests.get(
                                job_url,
                                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                                timeout=10
                            )
                            if job_response.status_code == 200:
                                job_soup = BeautifulSoup(job_response.text, 'html.parser')
                                
                                # Get company name from job page
                                company_elem = job_soup.find('h2') or job_soup.find('h1', class_='company')
                                if company_elem:
                                    company = company_elem.get_text(strip=True)
                                
                                # Get description
                                desc_elem = job_soup.find('div', class_='description') or job_soup.find('section')
                                if desc_elem:
                                    description = desc_elem.get_text(strip=True, separator=' ')[:3000]
                                
                                # Get location
                                loc_elem = job_soup.find('span', class_='location') or job_soup.find('div', class_='location')
                                if loc_elem:
                                    location = loc_elem.get_text(strip=True)
                        except Exception as e:
                            logger.debug(f"Could not fetch details for {job_url}: {e}")
                        
                        job = Job(
                            title=title,
                            company=company,
                            location=location,
                            description=description or title,
                            url=job_url,
                            source="YC Work at a Startup",
                            remote='remote' in location.lower()
                        )
                        jobs.append(job)
                        logger.debug(f"Found YC job: {title} at {company}")
                        
                        if len(jobs) >= max_results:
                            break
                            
                    except Exception as e:
                        logger.debug(f"Error parsing YC job: {e}")
                        continue
                
                if len(jobs) >= max_results:
                    break
                    
            except Exception as e:
                logger.debug(f"Error searching YC for '{search_term}': {e}")
                continue
        
        logger.info(f"Successfully scraped {len(jobs)} jobs from YC")
        
    except Exception as e:
        logger.error(f"Unexpected error scraping YC jobs: {e}")
    
    return jobs[:max_results]
