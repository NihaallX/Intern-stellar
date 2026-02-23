"""
Job description enrichment using Tavily Extract.

Fetches full page content for jobs with thin descriptions,
dramatically improving LLM extraction and scoring accuracy.
"""

import time
from typing import Optional
from tavily import TavilyClient

from src.models import Job
from src.utils.config import get_tavily_api_key


# Minimum description length to consider "thin"
MIN_DESCRIPTION_LENGTH = 200

# Maximum jobs to enrich per run (to manage API costs)
MAX_ENRICHMENT_JOBS = 60

# Rate limiting
_rate_limit_delay = 0.5  # seconds between extract calls


def _get_tavily_client() -> TavilyClient:
    """Initialize Tavily client."""
    api_key = get_tavily_api_key()
    return TavilyClient(api_key=api_key)


def is_thin_description(job: Job) -> bool:
    """Check if a job has a thin (insufficient) description."""
    desc = job.description.strip()
    
    # No description at all
    if not desc or len(desc) < MIN_DESCRIPTION_LENGTH:
        return True
    
    # Description is just the title repeated
    if desc.lower().replace(job.title.lower(), "").strip() == "":
        return True
    
    return False


def enrich_job_description(job: Job, client: TavilyClient) -> Job:
    """
    Fetch full page content for a job with thin description.
    
    Uses Tavily Extract to get the actual job page content,
    then updates the job's description field.
    """
    try:
        response = client.extract(urls=[job.url])
        
        results = response.get("results", [])
        if results:
            raw_content = results[0].get("raw_content", "")
            
            if raw_content and len(raw_content) > len(job.description):
                # Clean and truncate to avoid excessive content
                cleaned = raw_content[:5000].strip()
                job.description = cleaned
                return job
        
        # If extract fails, try a search for the job
        failed = response.get("failed_results", [])
        if failed:
            # Fallback: search for the job title + company
            search_response = client.search(
                query=f'"{job.title}" "{job.company}" job description requirements',
                search_depth="basic",
                max_results=3,
                days=45,
            )
            
            # Concatenate search snippets as enriched description
            snippets = []
            for result in search_response.get("results", []):
                content = result.get("content", "")
                if content and len(content) > 50:
                    snippets.append(content)
            
            if snippets:
                enriched = "\n\n".join(snippets)
                if len(enriched) > len(job.description):
                    job.description = enriched[:5000]
        
    except Exception as e:
        # Silently continue — enrichment is best-effort
        pass
    
    return job


def enrich_thin_descriptions(jobs: list[Job], max_enrich: int = MAX_ENRICHMENT_JOBS) -> list[Job]:
    """
    Enrich jobs with thin descriptions by fetching full page content.
    
    Args:
        jobs: List of Job objects
        max_enrich: Maximum number of jobs to enrich
    
    Returns:
        Same list with descriptions updated in-place
    """
    thin_jobs = [(i, job) for i, job in enumerate(jobs) if is_thin_description(job)]
    
    if not thin_jobs:
        print("  All jobs have sufficient descriptions")
        return jobs
    
    print(f"  Found {len(thin_jobs)} jobs with thin descriptions")
    
    # Limit enrichment count
    to_enrich = thin_jobs[:max_enrich]
    
    try:
        client = _get_tavily_client()
    except Exception as e:
        print(f"  Tavily client init failed: {e}")
        return jobs
    
    enriched_count = 0
    
    # Batch extract: Tavily supports up to 20 URLs at once
    batch_size = 10
    for batch_start in range(0, len(to_enrich), batch_size):
        batch = to_enrich[batch_start:batch_start + batch_size]
        urls = [job.url for _, job in batch]
        
        try:
            time.sleep(_rate_limit_delay)
            response = client.extract(urls=urls)
            
            # Map results back by URL
            result_map = {}
            for result in response.get("results", []):
                url = result.get("url", "")
                raw_content = result.get("raw_content", "")
                if url and raw_content:
                    result_map[url] = raw_content
            
            # Update jobs with enriched content
            for idx, job in batch:
                if job.url in result_map:
                    new_desc = result_map[job.url][:5000].strip()
                    if len(new_desc) > len(job.description):
                        job.description = new_desc
                        enriched_count += 1
            
        except Exception as e:
            # Fall back to individual enrichment
            for idx, job in batch:
                try:
                    time.sleep(_rate_limit_delay)
                    enrich_job_description(job, client)
                    if len(job.description) > MIN_DESCRIPTION_LENGTH:
                        enriched_count += 1
                except:
                    pass
        
        print(f"  Progress: {min(batch_start + batch_size, len(to_enrich))}/{len(to_enrich)} checked")
    
    print(f"  Enriched {enriched_count}/{len(to_enrich)} thin descriptions")
    return jobs
