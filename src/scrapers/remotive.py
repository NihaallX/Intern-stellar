"""
Remotive AI/ML Jobs scraper.

Scrapes remote AI/ML job listings from remotive.com/remote-jobs/ai-ml.
"""

import logging
import re
from typing import List

import requests
from bs4 import BeautifulSoup

from ..models import Job

logger = logging.getLogger(__name__)


def scrape_remotive_jobs(max_results: int = 30) -> List[Job]:
    """
    Scrape remote AI/ML job listings from Remotive.
    
    Args:
        max_results: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    jobs = []
    base_url = "https://remotive.com"
    
    try:
        logger.info(f"Fetching Remotive AI/ML jobs from {base_url}/remote-jobs/ai-ml")
        response = requests.get(
            f"{base_url}/remote-jobs/ai-ml",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://remotive.com/",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin"
            },
            timeout=15
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find job listings - Remotive uses job-tile or similar classes
        job_cards = soup.find_all(['li', 'div', 'article'], class_=re.compile(r'job|listing|tile|card', re.I))
        
        logger.info(f"Found {len(job_cards)} potential job cards on Remotive")
        
        for card in job_cards[:max_results]:
            try:
                # Extract job title
                title_elem = card.find(['h2', 'h3', 'a'], class_=re.compile(r'title|name|heading', re.I))
                if not title_elem:
                    title_elem = card.find('a')
                    
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                
                # Extract company name
                company_elem = card.find(['div', 'span', 'p'], class_=re.compile(r'company|employer', re.I))
                company = company_elem.get_text(strip=True) if company_elem else "Remote Company"
                
                # Location is always remote for Remotive
                location = "Remote"
                
                # Extract job URL
                link_elem = card.find('a', href=True)
                job_url = ""
                if link_elem:
                    href = link_elem.get('href', '')
                    if href.startswith('/'):
                        job_url = f"{base_url}{href}"
                    elif href.startswith('http'):
                        job_url = href
                    else:
                        job_url = f"{base_url}/{href}"
                
                # Extract description snippet
                desc_elem = card.find(['p', 'div'], class_=re.compile(r'description|excerpt|summary', re.I))
                description = desc_elem.get_text(strip=True, separator=' ')[:1000] if desc_elem else title
                
                if title and len(title) > 3:
                    jobs.append(Job(
                        title=title,
                        company=company,
                        location=location,
                        description=description,
                        url=job_url or f"{base_url}/remote-jobs/ai-ml",
                        source="Remotive"
                    ))
                    logger.debug(f"Scraped Remotive job: {title} at {company}")
                    
            except Exception as e:
                logger.debug(f"Error parsing Remotive job card: {e}")
                continue
        
        logger.info(f"Successfully scraped {len(jobs)} jobs from Remotive")
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch Remotive jobs: {e}")
    except Exception as e:
        logger.error(f"Unexpected error scraping Remotive jobs: {e}")
    
    return jobs[:max_results]
