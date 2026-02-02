"""
Web search utilities using Tavily API.
Provides company enrichment and general search capabilities.
"""

import re
import time
from typing import Optional
from tavily import TavilyClient

from src.models import CompanyEnrichment, CompanyType
from src.utils.config import get_tavily_api_key


# Lazy-loaded Tavily client
_tavily_client: Optional[TavilyClient] = None

# In-memory cache for company enrichments (cleared per pipeline run)
_company_cache: dict[str, CompanyEnrichment] = {}

# Rate limiting
_last_api_call: float = 0
_rate_limit_delay: float = 1.5  # seconds between API calls

# API call tracking (for credit monitoring)
_api_calls_made: int = 0


def get_tavily_client() -> TavilyClient:
    """Get or initialize the Tavily client."""
    global _tavily_client
    if _tavily_client is None:
        try:
            api_key = get_tavily_api_key()
            _tavily_client = TavilyClient(api_key=api_key)
            print("[WEB SEARCH] Tavily client initialized successfully")
        except Exception as e:
            print(f"[WEB SEARCH] ERROR: Failed to initialize Tavily client: {e}")
            raise
    return _tavily_client


def clear_cache():
    """Clear the company enrichment cache. Call at start of pipeline."""
    global _company_cache, _api_calls_made
    _company_cache.clear()
    _api_calls_made = 0
    print("[WEB SEARCH] Cache cleared, API counter reset")


def get_api_call_count() -> int:
    """Get the number of API calls made in current session."""
    return _api_calls_made


def _rate_limit():
    """Enforce rate limiting between API calls."""
    global _last_api_call, _api_calls_made
    current_time = time.time()
    time_since_last = current_time - _last_api_call
    
    if time_since_last < _rate_limit_delay:
        sleep_time = _rate_limit_delay - time_since_last
        time.sleep(sleep_time)
    
    _last_api_call = time.time()
    _api_calls_made += 1  # Track API calls


def search_company_info(company_name: str) -> CompanyEnrichment:
    """
    Search for company information using Tavily.
    Returns enriched company data including funding, size, tech stack.
    Uses in-memory cache to avoid duplicate API calls.
    
    Args:
        company_name: Name of the company to search
        
    Returns:
        CompanyEnrichment object with web-searched data
    """
    # Check cache first
    cache_key = company_name.lower().strip()
    if cache_key in _company_cache:
        print(f"[WEB SEARCH] Using cached data for {company_name}")
        return _company_cache[cache_key]
    
    # Rate limit
    _rate_limit()
    
    try:
        client = get_tavily_client()
        print(f"[WEB SEARCH] Fetching data for {company_name}...")
        
        # Search for company information
        query = f"{company_name} company AI machine learning funding employees"
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            include_domains=["linkedin.com", "crunchbase.com", "techcrunch.com", "pitchbook.com"],
        )
        
        enrichment = CompanyEnrichment()
        
        # Parse results
        results = response.get("results", [])
        
        for result in results:
            content = result.get("content", "").lower()
            title = result.get("title", "").lower()
            combined = f"{title} {content}"
            
            # Extract employee count
            if not enrichment.employee_count:
                employee_matches = re.findall(r'(\d+[\.,]?\d*)\s*(?:employees?|people)', combined)
                if employee_matches:
                    try:
                        count = int(employee_matches[0].replace(',', '').replace('.', ''))
                        enrichment.employee_count = count
                    except:
                        pass
            
            # Extract funding stage
            if not enrichment.funding_stage:
                if 'series a' in combined:
                    enrichment.funding_stage = "Series A"
                elif 'series b' in combined:
                    enrichment.funding_stage = "Series B"
                elif 'series c' in combined:
                    enrichment.funding_stage = "Series C"
                elif 'series d' in combined:
                    enrichment.funding_stage = "Series D"
                elif 'seed' in combined:
                    enrichment.funding_stage = "Seed"
            
            # Check if AI company
            ai_indicators = [
                'artificial intelligence', 'machine learning', 'deep learning',
                'llm', 'large language model', 'generative ai', 'ai platform',
                'ai-first', 'ai company', 'ai solutions'
            ]
            if any(indicator in combined for indicator in ai_indicators):
                enrichment.is_ai_company = True
            
            # Extract company description (from first result)
            if not enrichment.company_description and result.get("content"):
                desc = result.get("content", "")[:500]
                if len(desc) > 100:
                    enrichment.company_description = desc
            
            # Add to recent news
            if result.get("title"):
                enrichment.recent_news.append(result["title"])
        
        # Search for tech stack
        try:
            tech_query = f"{company_name} engineering blog tech stack Python AWS React"
            tech_response = client.search(
                query=tech_query,
                search_depth="basic",
                max_results=3,
                include_domains=["github.com", "medium.com", "dev.to", "stackoverflow.blog"],
            )
            
            tech_keywords = ['python', 'fastapi', 'aws', 'kubernetes', 'docker', 'react', 
                           'typescript', 'postgresql', 'redis', 'langchain', 'openai']
            
            for result in tech_response.get("results", []):
                content = result.get("content", "").lower()
                for keyword in tech_keywords:
                    if keyword in content and keyword not in enrichment.tech_stack:
                        enrichment.tech_stack.append(keyword)
        except Exception as tech_error:
            print(f"[WEB SEARCH] Warning: Tech stack search failed for {company_name}: {tech_error}")
        
        # Cache the result
        _company_cache[cache_key] = enrichment
        return enrichment
        
    except Exception as e:
        print(f"[WEB SEARCH] ERROR: Failed to enrich {company_name}: {e}")
        # Cache empty result to avoid retry
        empty_enrichment = CompanyEnrichment()
        _company_cache[cache_key] = empty_enrichment
        return empty_enrichment


def search_job_validation(job_title: str, company_name: str, url: str) -> dict:
    """
    Validate if a job posting is still active and get additional context.
    
    Args:
        job_title: Title of the job
        company_name: Company name
        url: Job posting URL
        
    Returns:
        Dict with validation info: {is_active, salary_info, etc}
    """
    _rate_limit()
    
    try:
        client = get_tavily_client()
        
        query = f"\"{company_name}\" \"{job_title}\" salary remote"
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=3,
            include_domains=["levels.fyi", "glassdoor.com", "indeed.com"],
        )
        
        validation = {
            "is_active": True,  # Assume active unless proven otherwise
            "salary_info": None,
            "glassdoor_rating": None,
        }
        
        for result in response.get("results", []):
            content = result.get("content", "").lower()
            
            # Extract salary information
            salary_matches = re.findall(r'\$(\d+)[k,]', content)
            if salary_matches and not validation["salary_info"]:
                validation["salary_info"] = f"${salary_matches[0]}k (estimated)"
            
            # Extract Glassdoor rating
            rating_matches = re.findall(r'(\d\.\d)\s*(?:star|rating)', content)
            if rating_matches:
                try:
                    validation["glassdoor_rating"] = float(rating_matches[0])
                except:
                    pass
        
        return validation
        
    except Exception as e:
        print(f"[WEB SEARCH] Error validating job: {e}")
        return {"is_active": True}


def search_ai_jobs(keywords: list[str], max_results: int = 10) -> list[dict]:
    """
    Search for AI jobs using Tavily's search API.
    More reliable than Google scraping.
    
    Args:
        keywords: List of search keywords
        max_results: Maximum number of results to return
        
    Returns:
        List of job URLs and metadata
    """
    try:
        client = get_tavily_client()
        
        jobs = []
        
        for keyword in keywords[:3]:  # Limit to avoid rate limits
            _rate_limit()  # Rate limit per search
            
            query = f"{keyword} site:greenhouse.io OR site:lever.co OR site:ashbyhq.com"
            
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=max_results,
            )
            
            for result in response.get("results", []):
                url = result.get("url", "")
                if any(domain in url for domain in ["greenhouse.io", "lever.co", "ashbyhq.com", "workable.com"]):
                    jobs.append({
                        "url": url,
                        "title": result.get("title", ""),
                        "snippet": result.get("content", "")[:200],
                    })
        
        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for job in jobs:
            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                unique_jobs.append(job)
        
        return unique_jobs[:max_results]
        
    except Exception as e:
        print(f"[WEB SEARCH] Error searching AI jobs: {e}")
        return []


def infer_company_type(enrichment: CompanyEnrichment) -> CompanyType:
    """
    Infer company type from enrichment data.
    
    Args:
        enrichment: CompanyEnrichment with web-searched data
        
    Returns:
        CompanyType enum value
    """
    if enrichment.employee_count:
        if enrichment.employee_count < 200:
            return CompanyType.STARTUP
        elif enrichment.employee_count < 2000:
            return CompanyType.MIDSIZE
        else:
            return CompanyType.ENTERPRISE
    
    # Infer from funding stage
    if enrichment.funding_stage:
        if enrichment.funding_stage.lower() in ["seed", "series a"]:
            return CompanyType.STARTUP
        elif enrichment.funding_stage.lower() in ["series b", "series c"]:
            return CompanyType.MIDSIZE
    
    return CompanyType.UNKNOWN
