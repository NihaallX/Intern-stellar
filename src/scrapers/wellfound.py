"""
Wellfound (AngelList) Jobs scraper.

Scrapes startup job listings from wellfound.com.
"""

import logging
import re
from typing import List

import requests
from bs4 import BeautifulSoup

from ..models import Job

logger = logging.getLogger(__name__)


def scrape_wellfound_jobs(max_results: int = 30) -> List[Job]:
    """
    Scrape startup job listings from Wellfound (formerly AngelList).
    
    Args:
        max_results: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    jobs = []
    base_url = "https://wellfound.com"
    
    try:
        # Search for ML/AI jobs on Wellfound
        search_url = f"{base_url}/role/l/machine-learning-engineer"
        logger.info(f"Fetching Wellfound jobs from {search_url}")
        
        response = requests.get(
            search_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://wellfound.com/",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none"
            },
            timeout=15
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find job cards - Wellfound uses various class names
        job_cards = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'job|listing|card|posting', re.I))
        
        # Also try finding links to /jobs/
        job_links = soup.find_all('a', href=re.compile(r'/jobs/\d+'))
        
        logger.info(f"Found {len(job_cards)} job cards and {len(job_links)} job links on Wellfound")
        
        # Process job cards
        for card in job_cards[:max_results]:
            try:
                # Extract title
                title_elem = card.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|role', re.I))
                if not title_elem:
                    title_elem = card.find('a', href=re.compile(r'/jobs/'))
                    
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                
                # Extract company
                company_elem = card.find(['div', 'span', 'a'], class_=re.compile(r'company|startup', re.I))
                company = company_elem.get_text(strip=True) if company_elem else "Startup"
                
                # Extract location
                location_elem = card.find(['div', 'span'], class_=re.compile(r'location|place', re.I))
                location = location_elem.get_text(strip=True) if location_elem else "Remote"
                
                # Extract job URL
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
                
                # Extract description
                desc_elem = card.find(['p', 'div'], class_=re.compile(r'description|summary|excerpt', re.I))
                description = desc_elem.get_text(strip=True, separator=' ')[:1000] if desc_elem else title
                
                if title and len(title) > 3:
                    jobs.append(Job(
                        title=title,
                        company=company,
                        location=location,
                        description=description,
                        url=job_url or search_url,
                        source="Wellfound"
                    ))
                    logger.debug(f"Scraped Wellfound job: {title} at {company}")
                    
            except Exception as e:
                logger.debug(f"Error parsing Wellfound job card: {e}")
                continue
        
        # Also process direct job links if we didn't get enough from cards
        if len(jobs) < 5:
            for link in job_links[:max_results]:
                try:
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if href.startswith('/'):
                        job_url = f"{base_url}{href}"
                    else:
                        job_url = href
                    
                    if title and len(title) > 3:
                        jobs.append(Job(
                            title=title,
                            company="Startup",
                            location="Remote",
                            description=title,
                            url=job_url,
                            source="Wellfound"
                        ))
                        logger.debug(f"Scraped Wellfound job from link: {title}")
                        
                except Exception as e:
                    logger.debug(f"Error parsing Wellfound job link: {e}")
                    continue
        
        logger.info(f"Successfully scraped {len(jobs)} jobs from Wellfound")
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch Wellfound jobs: {e}")
    except Exception as e:
        logger.error(f"Unexpected error scraping Wellfound jobs: {e}")
    
    return jobs[:max_results]
