"""
X-Ray Search Scraper.
Uses Google search with site: operators to find jobs across multiple ATS platforms.
"""

import time
import random
import requests
from typing import Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from src.models import Job
from src.utils.text import clean_text, is_likely_unpaid
from src.utils.config import load_settings


# Try importing googlesearch, fallback to requests-based scraping
try:
    from googlesearch import search as google_search
    HAS_GOOGLESEARCH = True
except ImportError:
    HAS_GOOGLESEARCH = False


# ATS platforms to search
ATS_SITES = [
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "workable.com",
    "breezy.hr",
    "recruitee.com",
    "jobs.lever.co",
    "boards.greenhouse.io",
    "wellfound.com/jobs",
    "apply.workable.com",
    "smartrecruiters.com",
    "jobvite.com",
]

# Search keywords for AI roles
AI_KEYWORDS = [
    '"AI Engineer"',
    '"GenAI Engineer"',
    '"LLM Engineer"',
    '"Applied AI"',
    '"Machine Learning Engineer" intern',
    '"AI intern"',
    '"Generative AI"',
    'RAG engineer',
    '"agentic" engineer',
    '"Applied ML"',
]


def build_xray_queries() -> list[str]:
    """
    Build X-Ray search queries combining sites and keywords.
    """
    queries = []
    
    for keyword in AI_KEYWORDS:
        # Combine multiple sites in one query for efficiency
        site_query = " OR ".join([f"site:{site}" for site in ATS_SITES[:5]])
        queries.append(f"({site_query}) {keyword}")
        
        site_query2 = " OR ".join([f"site:{site}" for site in ATS_SITES[5:]])
        if site_query2:
            queries.append(f"({site_query2}) {keyword}")
    
    return queries


def search_google(query: str, num_results: int = 20) -> list[str]:
    """
    Perform a Google search and return URLs.
    Uses googlesearch-python if available, otherwise falls back to scraping.
    """
    if HAS_GOOGLESEARCH:
        try:
            results = list(google_search(query, num_results=num_results, sleep_interval=2))
            return results[:num_results]
        except Exception as e:
            print(f"[XRAY] Google search error: {e}")
            return []
    else:
        # Fallback: use requests (less reliable, may get blocked)
        print("[XRAY] Warning: googlesearch-python not installed, using fallback")
        return _search_google_fallback(query, num_results)


def _search_google_fallback(query: str, num_results: int = 20) -> list[str]:
    """
    Fallback Google search using requests.
    Note: This is unreliable and may get blocked.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        url = f"https://www.google.com/search?q={query}&num={num_results}"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        urls = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/url?q=' in href:
                # Extract actual URL from Google redirect
                actual_url = href.split('/url?q=')[1].split('&')[0]
                if actual_url.startswith('http'):
                    urls.append(actual_url)
        
        return urls[:num_results]
    except Exception as e:
        print(f"[XRAY] Fallback search error: {e}")
        return []


def fetch_job_page(url: str) -> Optional[dict]:
    """
    Fetch a job page and extract relevant information.
    Handles different ATS platforms.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = None
        title_selectors = [
            'h1',
            '.job-title',
            '.posting-headline h2',
            '[data-qa="job-title"]',
            '.job-header h1',
        ]
        for selector in title_selectors:
            elem = soup.select_one(selector)
            if elem:
                title = clean_text(elem.get_text())
                break
        
        if not title:
            title = soup.title.string if soup.title else "Unknown Role"
        
        # Extract company
        company = None
        company_selectors = [
            '.company-name',
            '.posting-categories .sort-by-time',
            '[data-qa="company-name"]',
            '.job-company',
        ]
        for selector in company_selectors:
            elem = soup.select_one(selector)
            if elem:
                company = clean_text(elem.get_text())
                break
        
        if not company:
            # Try to extract from URL
            parsed = urlparse(url)
            if 'greenhouse.io' in parsed.netloc or 'boards.greenhouse.io' in parsed.netloc:
                # Format: boards.greenhouse.io/companyname/...
                parts = parsed.path.strip('/').split('/')
                if parts:
                    company = parts[0].replace('-', ' ').title()
            elif 'lever.co' in parsed.netloc:
                # Format: jobs.lever.co/companyname/...
                parts = parsed.path.strip('/').split('/')
                if parts:
                    company = parts[0].replace('-', ' ').title()
        
        if not company:
            company = "Unknown Company"
        
        # Extract location
        location = "Unknown"
        remote = False
        location_selectors = [
            '.location',
            '.job-location',
            '[data-qa="job-location"]',
            '.posting-categories .location',
        ]
        for selector in location_selectors:
            elem = soup.select_one(selector)
            if elem:
                loc_text = clean_text(elem.get_text())
                location = loc_text
                if 'remote' in loc_text.lower():
                    remote = True
                break
        
        # Check page text for remote
        page_text = clean_text(soup.get_text())
        if 'remote' in page_text.lower():
            remote = True
        
        # Extract description
        description = ""
        desc_selectors = [
            '.job-description',
            '.posting-description',
            '[data-qa="job-description"]',
            '.content',
            'article',
        ]
        for selector in desc_selectors:
            elem = soup.select_one(selector)
            if elem:
                description = clean_text(elem.get_text())
                break
        
        if not description:
            description = page_text[:3000]
        
        return {
            "title": title[:200],
            "company": company[:100],
            "location": location[:100],
            "remote": remote,
            "description": description[:5000],
            "url": url,
        }
        
    except Exception as e:
        print(f"[XRAY] Error fetching {url}: {e}")
        return None


def scrape_xray(max_jobs: int = 100) -> list[Job]:
    """
    Main entry point: Perform X-Ray search across ATS platforms.
    
    Args:
        max_jobs: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    print("[XRAY] Building search queries...")
    queries = build_xray_queries()
    print(f"[XRAY] Generated {len(queries)} queries")
    
    all_urls = set()
    
    for i, query in enumerate(queries):
        if len(all_urls) >= max_jobs * 2:  # Get extra to account for failures
            break
            
        print(f"[XRAY] Searching query {i+1}/{len(queries)}: {query[:50]}...")
        
        urls = search_google(query, num_results=20)
        all_urls.update(urls)
        
        # Rate limiting
        time.sleep(random.uniform(2, 4))
    
    print(f"[XRAY] Found {len(all_urls)} unique URLs")
    
    # Fetch and parse job pages
    jobs = []
    for url in list(all_urls)[:max_jobs * 2]:
        if len(jobs) >= max_jobs:
            break
            
        print(f"[XRAY] Fetching: {url[:60]}...")
        
        job_data = fetch_job_page(url)
        if job_data:
            # Check if unpaid
            if is_likely_unpaid(job_data["description"]):
                continue
            
            # Determine source from URL
            parsed = urlparse(url)
            source = "xray"
            for ats in ATS_SITES:
                if ats in parsed.netloc or ats in url:
                    source = ats.split('.')[0]
                    break
            
            job = Job(
                title=job_data["title"],
                company=job_data["company"],
                url=url,
                source=source,
                location=job_data["location"],
                remote=job_data["remote"],
                paid=True,
                description=job_data["description"],
            )
            job.job_id = job.generate_job_id()
            jobs.append(job)
        
        # Rate limiting
        time.sleep(random.uniform(1, 2))
    
    print(f"[XRAY] Successfully parsed {len(jobs)} jobs")
    return jobs


if __name__ == "__main__":
    # Test the scraper
    jobs = scrape_xray(max_jobs=5)
    for job in jobs:
        print(f"- {job.company}: {job.title} ({job.location})")
