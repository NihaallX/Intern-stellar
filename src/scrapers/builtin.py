"""
Builtin.com Job Scraper via Tavily.

Builtin is a great source for startup and tech jobs.
Uses Tavily to search and extract job listings.
"""

import logging
import time
from typing import List

from tavily import TavilyClient

from ..models import Job
from ..utils.config import get_tavily_api_key

logger = logging.getLogger(__name__)


def scrape_builtin_jobs(max_results: int = 30) -> List[Job]:
    """
    Search Builtin.com for AI/PM/FDE jobs via Tavily.
    
    Args:
        max_results: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    jobs = []
    
    try:
        api_key = get_tavily_api_key()
        client = TavilyClient(api_key=api_key)
        
        search_queries = [
            'site:builtin.com/job "AI Engineer" OR "Machine Learning" intern OR junior',
            'site:builtin.com/job "Product Manager" AI OR ML OR tech',
            'site:builtin.com/job "Associate Product Manager" OR "APM"',
            'site:builtin.com/job "Forward Deployed" OR "Solutions Engineer" AI',
            'site:builtin.com/job "GenAI" OR "LLM" OR "generative AI"',
        ]
        
        print(f"[BUILTIN] Searching {len(search_queries)} queries via Tavily...")
        
        for idx, query in enumerate(search_queries):
            try:
                response = client.search(
                    query=query,
                    search_depth="basic",
                    max_results=5,
                    include_domains=["builtin.com"],
                    days=45,  # Only recent listings
                )
                
                for result in response.get("results", []):
                    title = result.get("title", "")
                    url = result.get("url", "")
                    content = result.get("content", "")
                    
                    # Only keep job pages
                    if "/job/" not in url:
                        continue
                    
                    # Extract company from title ("Role at Company | Builtin")
                    company = "Unknown Company"
                    clean_title = title
                    
                    for sep in [" at ", " | "]:
                        if sep in title:
                            parts = title.split(sep)
                            clean_title = parts[0].strip()
                            if sep == " at " and len(parts) > 1:
                                company = parts[1].split(" | ")[0].strip()
                            break
                    
                    # Clean Builtin suffix
                    for suffix in [" | Built In", " | Builtin"]:
                        company = company.replace(suffix, "")
                        clean_title = clean_title.replace(suffix, "")
                    
                    location = "Unknown"
                    text = f"{title} {content}".lower()
                    if "remote" in text:
                        location = "Remote"
                    
                    if clean_title and url and len(clean_title) > 3:
                        jobs.append(Job(
                            title=clean_title[:200],
                            company=company[:100],
                            location=location,
                            description=content[:2000],
                            url=url,
                            source="builtin",
                        ))
                
                time.sleep(1.5)
                
            except Exception as e:
                logger.warning(f"Error in Builtin query: {e}")
                continue
        
        # Deduplicate
        seen_urls = set()
        unique_jobs = []
        for job in jobs:
            if job.url not in seen_urls:
                seen_urls.add(job.url)
                unique_jobs.append(job)
        
        print(f"[BUILTIN] Found {len(unique_jobs)} unique jobs")
        return unique_jobs[:max_results]
        
    except Exception as e:
        print(f"[BUILTIN] Error: {e}")
        return []
