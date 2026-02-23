"""
LinkedIn Public Jobs Scraper via Tavily.

Uses Tavily to search LinkedIn job listings, bypassing bot detection.
Focuses on AI, PM, and FDE roles.
"""

import logging
import time
from typing import List

from tavily import TavilyClient

from ..models import Job
from ..utils.config import get_tavily_api_key

logger = logging.getLogger(__name__)


def scrape_linkedin_jobs(max_results: int = 30) -> List[Job]:
    """
    Search LinkedIn public job listings via Tavily.
    
    Args:
        max_results: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    jobs = []
    
    try:
        api_key = get_tavily_api_key()
        client = TavilyClient(api_key=api_key)
        
        # LinkedIn-specific search queries
        search_queries = [
            # Engineering
            'site:linkedin.com/jobs/view "AI Engineer" OR "GenAI Engineer" intern OR junior',
            'site:linkedin.com/jobs/view "LLM Engineer" OR "Applied AI" intern OR junior',
            'site:linkedin.com/jobs/view "Machine Learning" intern OR junior 2025 OR 2026',
            # PM
            'site:linkedin.com/jobs/view "Associate Product Manager" AI OR tech 2025 OR 2026',
            'site:linkedin.com/jobs/view "AI Product Manager" OR "Product Manager AI/ML"',
            'site:linkedin.com/jobs/view "Technical Product Manager" AI OR ML junior',
            'site:linkedin.com/jobs/view "Product Manager" "generative AI" OR LLM',
            # FDE
            'site:linkedin.com/jobs/view "Forward Deployed Engineer" AI OR ML',
            'site:linkedin.com/jobs/view "Solutions Engineer" AI OR ML OR LLM',
            # Platform / Infra
            'site:linkedin.com/jobs/view "AI Platform" OR "ML Platform" intern OR junior',
        ]
        
        print(f"[LINKEDIN] Searching {len(search_queries)} queries via Tavily...")
        
        for idx, query in enumerate(search_queries):
            try:
                response = client.search(
                    query=query,
                    search_depth="basic",
                    max_results=5,
                    include_domains=["linkedin.com"],
                    days=45,  # Only recent listings
                )
                
                for result in response.get("results", []):
                    title = result.get("title", "")
                    url = result.get("url", "")
                    content = result.get("content", "")
                    
                    # Only keep actual job view pages
                    if "/jobs/view/" not in url and "/jobs/collections/" not in url:
                        continue
                    
                    # Clean LinkedIn title (usually "Company hiring Role in Location")
                    company = "Unknown Company"
                    clean_title = title
                    
                    if " hiring " in title.lower():
                        parts = title.split(" hiring ", 1)
                        company = parts[0].strip()
                        clean_title = parts[1].split(" in ")[0].strip() if " in " in parts[1] else parts[1].strip()
                    elif " - " in title:
                        parts = title.split(" - ")
                        clean_title = parts[0].strip()
                        if len(parts) > 1:
                            company = parts[1].strip()
                    
                    # Clean LinkedIn suffix
                    for suffix in [" | LinkedIn", " - LinkedIn"]:
                        clean_title = clean_title.replace(suffix, "")
                        company = company.replace(suffix, "")
                    
                    # Extract location from title or content
                    location = "Unknown"
                    text = f"{title} {content}".lower()
                    if "remote" in text:
                        location = "Remote"
                    elif " in " in title:
                        loc_part = title.split(" in ")[-1].replace(" | LinkedIn", "").strip()
                        if len(loc_part) < 50:
                            location = loc_part
                    
                    if clean_title and url and len(clean_title) > 3:
                        jobs.append(Job(
                            title=clean_title[:200],
                            company=company[:100],
                            location=location,
                            description=content[:2000],
                            url=url,
                            source="linkedin",
                        ))
                
                time.sleep(1.5)
                
                if (idx + 1) % 5 == 0:
                    print(f"  Progress: {idx + 1}/{len(search_queries)} queries")
                
            except Exception as e:
                logger.warning(f"Error in LinkedIn query: {e}")
                continue
        
        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for job in jobs:
            url_key = job.url.split("?")[0]  # Strip query params
            if url_key not in seen_urls:
                seen_urls.add(url_key)
                unique_jobs.append(job)
        
        print(f"[LINKEDIN] Found {len(unique_jobs)} unique jobs")
        return unique_jobs[:max_results]
        
    except Exception as e:
        print(f"[LINKEDIN] Error: {e}")
        return []
