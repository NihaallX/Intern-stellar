"""
Tavily Web Search Job Scraper.

Uses Tavily API to search for AI/ML jobs across multiple sources,
bypassing bot detection issues.
EXPANDED: Now searches for PM, FDE, and engineering roles.
"""

import logging
import time
from typing import List

from tavily import TavilyClient

from ..models import Job
from ..utils.config import get_tavily_api_key

logger = logging.getLogger(__name__)


def scrape_jobs_with_tavily(max_results: int = 50) -> List[Job]:
    """
    Search for AI/ML/PM jobs using Tavily web search API.
    
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
        
        # EXPANDED search queries for AI + PM + FDE roles
        search_queries = [
            # === Engineering roles ===
            "site:boards.greenhouse.io intitle:AI engineer OR intitle:ML engineer",
            "site:jobs.lever.co intitle:AI engineer OR intitle:ML engineer",
            'site:boards.greenhouse.io intitle:"GenAI" OR intitle:"LLM"',
            'site:jobs.lever.co intitle:"generative AI" OR intitle:"LLM"',
            # === PM roles - Greenhouse / Lever ===
            'site:boards.greenhouse.io intitle:"Product Manager" AI OR ML',
            'site:jobs.lever.co intitle:"Product Manager" AI OR ML',
            'site:boards.greenhouse.io intitle:"Associate Product Manager"',
            'site:jobs.lever.co intitle:"Associate Product Manager"',
            # === FDE / Solutions ===
            'site:boards.greenhouse.io intitle:"Forward Deployed" OR intitle:"Solutions Engineer"',
            'site:jobs.lever.co intitle:"Forward Deployed" OR intitle:"Solutions Engineer"',
            # === Remote job boards ===
            "site:remotive.com/remote-jobs intitle:AI OR intitle:machine learning OR intitle:product manager",
            "site:weworkremotely.com intitle:AI OR intitle:machine learning OR intitle:product manager",
            # === LinkedIn public listings (bypass detection) ===
            'site:linkedin.com/jobs/view "AI Engineer" OR "Product Manager AI" OR "Forward Deployed"',
            'site:linkedin.com/jobs/view "Associate Product Manager" OR "AI intern" OR "GenAI"',
            # === Simplify.jobs ===
            'site:simplify.jobs intitle:AI OR intitle:ML OR intitle:"Product Manager"',
            # === Builtin.com ===
            'site:builtin.com/job "AI" OR "machine learning" OR "product manager" intern OR junior',
            # === CutShort - strong for India / remote PM roles ===
            'site:cutshort.io "AI Product Manager" OR "Associate Product Manager" OR "ML Product Manager"',
            'site:cutshort.io "product manager" AI remote OR India junior OR associate',
            # === TrueUp - startup / Big Tech hiring tracker ===
            'site:trueup.io "AI Product Manager" OR "APM" OR "Associate Product Manager"',
            'site:trueup.io product manager AI OR machine-learning junior',
            # === AIJobs boards ===
            'site:aijobs.net "Product Manager" OR "APM" OR "AI PM"',
            'site:ai-jobs.net "Product Manager" OR "Associate Product Manager"',
            # === RemoteRocketShip ===
            'site:remoterocketship.com "AI Product Manager" OR "Associate Product Manager" OR "APM"',
            # === Wellfound (AngelList) - startups ===
            'site:wellfound.com/jobs "AI Product Manager" OR "Associate Product Manager" junior',
            # === Product-specific boards ===
            'site:productmanagerjobs.co "AI" OR "machine learning" OR "generative"',
            '"AI Product Manager" OR "APM program" OR "Associate PM" site:ashbyhq.com',
        ]
        
        logger.info(f"Searching for jobs with Tavily across {len(search_queries)} queries")
        print(f"[TAVILY] Searching across {len(search_queries)} queries...")
        
        for idx, query in enumerate(search_queries):
            try:
                logger.debug(f"Tavily search: {query}")
                
                # Search with Tavily
                response = client.search(
                    query=query,
                    search_depth="basic",
                    max_results=5,  # Get top 5 per query
                    days=45,  # Only results from last 45 days
                )
                
                # Parse results
                for result in response.get("results", []):
                    title = result.get("title", "")
                    url = result.get("url", "")
                    content = result.get("content", "")
                    
                    # Skip non-job pages (search results, category pages, etc.)
                    skip_keywords = ["search", "category", "browse", "all jobs", "job board", "jobs in", "job listings", "careers page"]
                    if any(keyword in url.lower() for keyword in skip_keywords):
                        continue
                    if any(keyword in title.lower() for keyword in skip_keywords):
                        continue
                    
                    # Extract company from URL and title
                    company = _extract_company(title, url)
                    
                    # Determine location
                    location = _extract_location(title, content)
                    
                    if title and url and len(title) > 5:
                        jobs.append(Job(
                            title=title,
                            company=company,
                            location=location,
                            description=content[:2000],
                            url=url,
                            source="tavily",
                        ))
                        logger.debug(f"Found job via Tavily: {title} at {company}")
                
                # Rate limiting
                time.sleep(1.5)
                
                if (idx + 1) % 5 == 0:
                    print(f"  Progress: {idx + 1}/{len(search_queries)} queries searched")
                
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
        
        print(f"[TAVILY] Found {len(unique_jobs)} unique jobs (from {len(jobs)} total)")
        logger.info(f"Successfully found {len(unique_jobs)} unique jobs via Tavily")
        
        return unique_jobs[:max_results]
        
    except Exception as e:
        logger.error(f"Failed to search jobs with Tavily: {e}")
        print(f"[TAVILY] Error: {e}")
        return []


def _extract_company(title: str, url: str) -> str:
    """Extract company name from title and URL."""
    company = "Unknown Company"
    
    # Try "at Company" pattern in title
    for sep in [" at ", " - ", " | "]:
        if sep in title:
            parts = title.split(sep)
            if len(parts) >= 2:
                candidate = parts[-1].strip() if sep == " | " else parts[1].split(" - ")[0].strip()
                if len(candidate) > 2 and len(candidate) < 60:
                    company = candidate
                    break
    
    if company == "Unknown Company":
        # Parse from URL
        if "greenhouse.io/" in url:
            slug = url.split("greenhouse.io/")[1].split("/")[0]
            company = slug.replace("-", " ").title()
        elif "lever.co/" in url:
            slug = url.split("lever.co/")[1].split("/")[0]
            company = slug.replace("-", " ").title()
        elif "ashbyhq.com/" in url:
            slug = url.split("ashbyhq.com/")[1].split("/")[0]
            company = slug.replace("-", " ").title()
        elif "linkedin.com" in url:
            company = title.split(" hiring ")[0].strip() if " hiring " in title.lower() else "Unknown Company"
        elif "cutshort.io/" in url:
            parts = url.split("cutshort.io/")[1].split("/")
            company = parts[0].replace("-", " ").title() if parts else "Unknown Company"
        elif "trueup.io/" in url:
            parts = url.split("trueup.io/")[1].split("/")
            company = parts[0].replace("-", " ").title() if parts else "Unknown Company"
        elif "wellfound.com/jobs/" in url:
            parts = url.split("wellfound.com/jobs/")[1].split("-")
            # wellfound URL format: company-name-job-title-id → extract by splitting at numeric ID
            company = parts[0].replace("-", " ").title() if parts else "Unknown Company"
        elif "remoterocketship.com/" in url:
            parts = url.rstrip("/").split("/")
            company = parts[-2].replace("-", " ").title() if len(parts) >= 2 else "Unknown Company"
    
    return company[:100]


def _extract_location(title: str, content: str) -> str:
    """Extract location from title and content."""
    text = f"{title} {content}".lower()
    
    if "remote" in text:
        return "Remote"
    elif "san francisco" in text or "sf," in text:
        return "San Francisco, CA"
    elif "new york" in text or "nyc" in text:
        return "New York, NY"
    elif "london" in text:
        return "London, UK"
    elif "bangalore" in text or "bengaluru" in text:
        return "Bangalore, India"
    elif "mumbai" in text:
        return "Mumbai, India"
    elif "delhi" in text or "gurgaon" in text or "noida" in text:
        return "Delhi NCR, India"
    elif "hyderabad" in text:
        return "Hyderabad, India"
    elif "pune" in text:
        return "Pune, India"
    elif "india" in text:
        return "India"
    elif "singapore" in text:
        return "Singapore"
    elif "berlin" in text:
        return "Berlin, Germany"
    elif "seattle" in text:
        return "Seattle, WA"
    elif "austin" in text:
        return "Austin, TX"
    elif "boston" in text:
        return "Boston, MA"
    
    return "Unknown"
