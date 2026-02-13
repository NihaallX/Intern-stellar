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
        
        # Search queries for specific job postings (not search pages)
        search_queries = [
            "site:remotive.com/remote-jobs/ai-ml intitle:hiring OR intitle:engineer",
            "site:wellfound.com/l intitle:machine learning OR intitle:AI engineer",
            "site:boards.greenhouse.io intitle:machine learning OR intitle:AI",
            "site:jobs.lever.co intitle:machine learning OR intitle:AI engineer",
            "site:weworkremotely.com/remote-jobs intitle:AI OR intitle:machine learning",
            "site:remote.co/remote-jobs intitle:machine learning OR intitle:AI"
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
                    include_domains=["remotive.com", "wellfound.com", "greenhouse.io", "lever.co", "weworkremotely.com", "remote.co"]
                )
                
                # Parse results
                for result in response.get("results", []):
                    title = result.get("title", "")
                    url = result.get("url", "")
                    content = result.get("content", "")
                    
                    # Skip non-job pages (search results, category pages, etc.)
                    skip_keywords = ["search", "category", "browse", "all jobs", "job board", "jobs in"]
                    if any(keyword in url.lower() for keyword in skip_keywords):
                        continue
                    if any(keyword in title.lower() for keyword in skip_keywords):
                        continue
                    
                    # Extract company from URL and title
                    company = "Unknown Company"
                    
                    # Parse company from different job board formats
                    if "remotive.com" in url:
                        # Remotive format: /remote-jobs/ai-ml/job-title-1234
                        parts = title.split(" at ")
                        if len(parts) >= 2:
                            company = parts[1].split(" - ")[0].strip()
                        else:
                            company = "Remote Company"
                    
                    elif "wellfound.com" in url:
                        # Wellfound format: /l/company-name/job-title
                        parts = url.split("/l/")
                        if len(parts) > 1:
                            company_slug = parts[1].split("/")[0]
                            company = company_slug.replace("-", " ").title()
                        # Also try parsing from title
                        title_parts = title.split(" at ")
                        if len(title_parts) >= 2:
                            company = title_parts[1].split(" - ")[0].strip()
                    
                    elif "greenhouse.io" in url:
                        # Greenhouse format: boards.greenhouse.io/companyname/jobs/123456
                        if "boards.greenhouse.io/" in url:
                            parts = url.split("boards.greenhouse.io/")[1].split("/")
                            if len(parts) > 0:
                                company = parts[0].replace("-", " ").title()
                        # Also check job-boards.greenhouse.io
                        elif "job-boards.greenhouse.io/" in url:
                            parts = url.split("job-boards.greenhouse.io/")[1].split("/")
                            if len(parts) > 0:
                                company = parts[0].replace("-", " ").title()
                    
                    elif "lever.co" in url:
                        # Lever format: jobs.lever.co/companyname/job-id
                        if "jobs.lever.co/" in url:
                            parts = url.split("jobs.lever.co/")[1].split("/")
                            if len(parts) > 0:
                                company = parts[0].replace("-", " ").title()
                    
                    elif "weworkremotely.com" in url:
                        # Parse from content or title
                        parts = title.split(" at ")
                        if len(parts) >= 2:
                            company = parts[1].split(" - ")[0].strip()
                    
                    elif "remote.co" in url:
                        # Parse from content or title
                        parts = title.split(" at ")
                        if len(parts) >= 2:
                            company = parts[1].split(" - ")[0].strip()
                    
                    elif "huggingface" in url.lower():
                        company = "Hugging Face"
                    
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
