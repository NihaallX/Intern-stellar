"""
Simplify.jobs Scraper via Tavily.

Simplify is popular among new grads and interns for
tech, AI, and PM roles.
"""

import logging
import time
from typing import List

from tavily import TavilyClient

from ..models import Job
from ..utils.config import get_tavily_api_key

logger = logging.getLogger(__name__)


def scrape_simplify_jobs(max_results: int = 30) -> List[Job]:
    """
    Search Simplify.jobs for AI/PM roles via Tavily.
    
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
            'site:simplify.jobs "AI Engineer" OR "Machine Learning" intern OR new grad',
            'site:simplify.jobs "Product Manager" OR "APM" intern OR new grad',
            'site:simplify.jobs "Forward Deployed" OR "Solutions Engineer"',
            'site:simplify.jobs "GenAI" OR "LLM" OR "AI intern"',
            'site:simplify.jobs "Associate Product Manager" OR "Technical PM"',
        ]
        
        print(f"[SIMPLIFY] Searching {len(search_queries)} queries via Tavily...")
        
        for idx, query in enumerate(search_queries):
            try:
                response = client.search(
                    query=query,
                    search_depth="basic",
                    max_results=5,
                    include_domains=["simplify.jobs"],
                    days=45,  # Only recent listings
                )
                
                for result in response.get("results", []):
                    title = result.get("title", "")
                    url = result.get("url", "")
                    content = result.get("content", "")
                    
                    # Extract company from title
                    company = "Unknown Company"
                    clean_title = title
                    
                    for sep in [" at ", " - ", " | "]:
                        if sep in title:
                            parts = title.split(sep)
                            clean_title = parts[0].strip()
                            if len(parts) > 1:
                                company = parts[1].split(" - ")[0].split(" | ")[0].strip()
                            break
                    
                    # Clean suffix
                    for suffix in [" | Simplify", " - Simplify"]:
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
                            source="simplify",
                        ))
                
                time.sleep(1.5)
                
            except Exception as e:
                logger.warning(f"Error in Simplify query: {e}")
                continue
        
        # Deduplicate
        seen_urls = set()
        unique_jobs = []
        for job in jobs:
            if job.url not in seen_urls:
                seen_urls.add(job.url)
                unique_jobs.append(job)
        
        print(f"[SIMPLIFY] Found {len(unique_jobs)} unique jobs")
        return unique_jobs[:max_results]
        
    except Exception as e:
        print(f"[SIMPLIFY] Error: {e}")
        return []
