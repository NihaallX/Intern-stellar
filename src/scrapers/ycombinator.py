"""
YC Work at a Startup product-role scraper.

Scrapes product-manager jobs from YC Work at a Startup role pages.
"""

import logging
from typing import List

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..models import Job

logger = logging.getLogger(__name__)


def _build_session() -> requests.Session:
    """Create a requests Session with sensible headers and retry policy."""
    session = requests.Session()
    # Sensible browser-like headers to avoid basic 406/403 blocks
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })

    # Retry on transient server errors
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def scrape_ycombinator_jobs(max_results: int = 30) -> List[Job]:
    """
    Scrape product-manager job listings from YC Work at a Startup.
    
    Args:
        max_results: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    jobs = []
    
    try:
        urls = [
            "https://www.workatastartup.com/jobs/l/product-manager",
            "https://www.workatastartup.com/jobs/r/product-manager",
        ]

        session = _build_session()

        for url in urls:
            logger.info(f"Fetching YC product jobs from {url}")
            try:
                response = session.get(url, timeout=20)
                response.raise_for_status()
            except requests.HTTPError as e:
                status = getattr(e.response, 'status_code', None)
                logger.warning("YC fetch failed %s %s", status, url)
                # Specific fallback for 406: try a more complete browser header set
                if status == 406:
                    alt_headers = {
                        "User-Agent": session.headers.get("User-Agent"),
                        "Accept": "*/*",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Referer": "https://www.google.com/",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
                    }
                    logger.info("YC fetch 406 fallback: retrying with alternate headers")
                    try:
                        response = session.get(url, headers=alt_headers, timeout=25)
                        response.raise_for_status()
                    except Exception as e2:
                        logger.error("YC fallback also failed: %s", e2)
                        continue
                else:
                    # Non-406 HTTP error: log and continue to next URL
                    logger.error("Error fetching %s: %s", url, e)
                    continue

            soup = BeautifulSoup(response.text, 'html.parser')
            # Find all job links - YC uses both workatastartup.com and ycombinator.com URLs
            all_links = soup.find_all('a', href=True)

            for link in all_links:
                href = link.get('href', '')

                # Look for actual job posting URLs (contain /jobs/ followed by ID)
                if '/jobs/' not in href:
                    continue

                # Skip generic category pages like /jobs/l/software-engineer or /jobs/r/product-manager
                if '/jobs/l/' in href or '/jobs/r/' in href:
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
                logger.debug(f"Found YC product job: {title} at {company}")

                if len(jobs) >= max_results:
                    break

            if len(jobs) >= max_results:
                break
        
        logger.info(f"Successfully scraped {len(jobs)} jobs from YC")
        
    except Exception as e:
        logger.error(f"Error scraping YC jobs: {e}")
    
    return jobs[:max_results]
