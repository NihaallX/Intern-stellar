"""
Tavily Web Search Job Scraper.

Uses Tavily API to search for AI/ML jobs across multiple sources,
bypassing bot detection issues.
"""

import logging
import time
from typing import List

from tavily import TavilyClient

from ..models import Job
from ..utils.config import get_tavily_api_key

logger = logging.getLogger(__name__)


def scrape_jobs_with_tavily(max_results: int = 30) -> List[Job]:
    """
    Search for AI/ML jobs using Tavily web search API.
    
    This bypasses bot detection by using Tavily's infrastructure.
    
    Args:
        max_results: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    jobs = []
    
    try:
        api_key = get_tavily_api_key()
        client = TavilyClient(api_key=api_key)
        
        # Search queries for different job boards
        search_queries = [
            "site:remotive.com AI ML machine learning jobs remote",
            "site:wellfound.com machine learning AI engineer jobs",
            "site:apply.workable.com/huggingface jobs",
            "AI engineer jobs junior entry level 2026",
            "machine learning engineer intern junior 2026"
        ]
        
        logger.info(f"Searching for jobs with Tavily across {len(search_queries)} queries")
        
        for query in search_queries:
            try:
                logger.debug(f"Tavily search: {query}")
                
                # Search with Tavily
                response = client.search(
                    query=query,
                    search_depth="basic",
                    max_results=5,  # Get top 5 per query
                    include_domains=["remotive.com", "wellfound.com", "apply.workable.com", "greenhouse.io", "lever.co"]
                )
                
                # Parse results
                for result in response.get("results", []):
                    title = result.get("title", "")
                    url = result.get("url", "")
                    content = result.get("content", "")
                    
                    # Extract company from URL or content
                    company = "Startup"
                    if "remotive.com" in url:
                        company = "Remote Company"
                    elif "huggingface" in url.lower():
                        company = "Hugging Face"
                    elif "wellfound.com" in url:
                        company = "Wellfound Startup"
                    
                    # Determine location
                    location = "Remote"
                    if "remote" in content.lower() or "remote" in title.lower():
                        location = "Remote"
                    elif "san francisco" in content.lower():
                        location = "San Francisco, CA"
                    elif "new york" in content.lower():
                        location = "New York, NY"
                    
                    if title and url and len(title) > 5:
                        jobs.append(Job(
                            title=title,
                            company=company,
                            location=location,
                            description=content[:1000],  # Limit description length
                            url=url,
                            source="Tavily Search"
                        ))
                        logger.debug(f"Found job via Tavily: {title} at {company}")
                
                # Rate limiting - be nice to Tavily
                time.sleep(1.5)
                
            except Exception as e:
                logger.warning(f"Error searching with query '{query}': {e}")
                continue
        
        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for job in jobs:
            if job.url not in seen_urls:
                seen_urls.add(job.url)
                unique_jobs.append(job)
        
        logger.info(f"Successfully found {len(unique_jobs)} unique jobs via Tavily (from {len(jobs)} total)")
        
        return unique_jobs[:max_results]
        
    except Exception as e:
        logger.error(f"Failed to search jobs with Tavily: {e}")
        return []
