"""
Hugging Face Jobs scraper.

Scrapes AI/ML job listings from huggingface.co/jobs.
"""

import logging
import re
from typing import List

import requests
from bs4 import BeautifulSoup

from ..models import Job

logger = logging.getLogger(__name__)


def scrape_huggingface_jobs(max_results: int = 20) -> List[Job]:
    """
    Scrape AI/ML job listings from Hugging Face (via Workable).
    
    Args:
        max_results: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    jobs = []
    base_url = "https://apply.workable.com"
    
    try:
        logger.info(f"Fetching Hugging Face jobs from {base_url}/huggingface")
        response = requests.get(
            f"{base_url}/huggingface",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://huggingface.co/",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            },
            timeout=15
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find job listings - HF might use various structures
        job_cards = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'job|listing|card|posting', re.I))
        
        # Also look for links to job pages
        job_links = soup.find_all('a', href=re.compile(r'/jobs/'))
        
        logger.info(f"Found {len(job_cards)} job cards and {len(job_links)} job links on Hugging Face")
        
        # Process job cards
        for card in job_cards[:max_results]:
            try:
                # Extract title
                title_elem = card.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|heading', re.I))
                if not title_elem:
                    title_elem = card.find('a')
                    
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                
                # Extract company
                company_elem = card.find(['div', 'span'], class_=re.compile(r'company|employer|organization', re.I))
                company = company_elem.get_text(strip=True) if company_elem else "AI Company"
                
                # Extract location
                location_elem = card.find(['div', 'span'], class_=re.compile(r'location|place', re.I))
                location = location_elem.get_text(strip=True) if location_elem else "Remote"
                
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
                
                # Extract description
                desc_elem = card.find(['p', 'div'], class_=re.compile(r'description|summary|excerpt', re.I))
                description = desc_elem.get_text(strip=True, separator=' ')[:1000] if desc_elem else title
                
                if title and len(title) > 3:
                    jobs.append(Job(
                        title=title,
                        company=company,
                        location=location,
                        description=description,
                        url=job_url or f"{base_url}/jobs",
                        source="Hugging Face"
                    ))
                    logger.debug(f"Scraped Hugging Face job: {title} at {company}")
                    
            except Exception as e:
                logger.debug(f"Error parsing Hugging Face job card: {e}")
                continue
        
        # Process job links if needed
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
                            company="AI Company",
                            location="Remote",
                            description=title,
                            url=job_url,
                            source="Hugging Face"
                        ))
                        logger.debug(f"Scraped Hugging Face job from link: {title}")
                        
                except Exception as e:
                    logger.debug(f"Error parsing Hugging Face job link: {e}")
                    continue
        
        logger.info(f"Successfully scraped {len(jobs)} jobs from Hugging Face")
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch Hugging Face jobs: {e}")
    except Exception as e:
        logger.error(f"Unexpected error scraping Hugging Face jobs: {e}")
    
    return jobs[:max_results]
