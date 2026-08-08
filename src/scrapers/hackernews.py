"""
Hacker News "Who's Hiring" scraper.
Uses the Algolia HN API to find and parse the monthly hiring thread.
"""

import re
import requests
from typing import Optional
from datetime import datetime

from src.models import Job
from src.utils.text import clean_text, is_likely_unpaid, is_likely_senior


# Algolia HN API endpoint
ALGOLIA_API = "https://hn.algolia.com/api/v1"


def find_latest_hiring_thread() -> Optional[dict]:
    """
    Find the latest "Who's Hiring" thread on HN.
    Returns the thread metadata including its ID.
    """
    # Search for "Ask HN: Who is hiring" posts
    current_month = datetime.now().strftime("%B %Y")
    
    params = {
        "query": f"Ask HN Who is hiring {current_month}",
        "tags": "story",
        "hitsPerPage": 5,
    }
    
    response = requests.get(f"{ALGOLIA_API}/search", params=params)
    response.raise_for_status()
    
    data = response.json()
    
    for hit in data.get("hits", []):
        title = hit.get("title", "").lower()
        if "who is hiring" in title or "who's hiring" in title:
            return hit
    
    # Fallback: try previous month
    prev_month = datetime.now().replace(day=1)
    if prev_month.month == 1:
        prev_month = prev_month.replace(year=prev_month.year - 1, month=12)
    else:
        prev_month = prev_month.replace(month=prev_month.month - 1)
    
    params["query"] = f"Ask HN Who is hiring {prev_month.strftime('%B %Y')}"
    response = requests.get(f"{ALGOLIA_API}/search", params=params)
    response.raise_for_status()
    
    data = response.json()
    for hit in data.get("hits", []):
        title = hit.get("title", "").lower()
        if "who is hiring" in title or "who's hiring" in title:
            return hit
    
    return None


def get_thread_comments(thread_id: str, max_comments: int = 500) -> list[dict]:
    """
    Get all top-level comments from a HN thread.
    Each comment represents a job posting.
    """
    params = {
        "tags": f"comment,story_{thread_id}",
        "hitsPerPage": max_comments,
    }
    
    response = requests.get(f"{ALGOLIA_API}/search", params=params)
    response.raise_for_status()
    
    data = response.json()
    
    # Filter to top-level comments only (parent_id == thread_id)
    comments = []
    for hit in data.get("hits", []):
        if hit.get("parent_id") == int(thread_id):
            comments.append(hit)
    
    return comments


def parse_hn_comment(comment: dict) -> Optional[Job]:
    """
    Parse a HN hiring thread comment into a Job object.
    
    Common format:
    Company Name | Location | Remote/Onsite | Role | Tech Stack | ...
    
    Description follows after the header line.
    """
    text = comment.get("comment_text", "")
    if not text:
        return None
    
    # Clean HTML
    text = clean_text(text)
    
    # Skip very short comments (likely not job posts)
    if len(text) < 50:
        return None
    
    # Extract first line as header
    lines = text.split('\n')
    header = lines[0] if lines else ""
    
    # Parse header (pipe-separated format)
    parts = [p.strip() for p in header.split('|')]
    
    # Default values
    company = parts[0] if parts else "Unknown"
    location = "Unknown"
    remote = False
    title = "Unknown Role"
    
    # Parse remaining parts
    for part in parts[1:]:
        part_lower = part.lower()
        
        # Check for remote indicators
        if 'remote' in part_lower:
            remote = True
            if 'only' in part_lower:
                location = "Remote Only"
            else:
                location = part
        elif 'onsite' in part_lower or 'on-site' in part_lower:
            location = part
        # Check for role titles
        elif any(role in part_lower for role in ['engineer', 'developer', 'scientist', 'manager', 'intern']):
            title = part
        # Otherwise might be location
        elif len(part) > 2 and not any(char.isdigit() for char in part[:4]):
            location = part
    
    # If title still unknown, try to extract from description
    if title == "Unknown Role":
        # Look for common role patterns
        role_patterns = [
            r'hiring\s+(?:a\s+)?([^.]+(?:engineer|developer|scientist|intern)[^.]*)',
            r'looking for\s+(?:a\s+)?([^.]+(?:engineer|developer|scientist|intern)[^.]*)',
        ]
        for pattern in role_patterns:
            match = re.search(pattern, text.lower())
            if match:
                title = match.group(1).strip().title()
                break
    
    # Check if unpaid or senior
    if is_likely_unpaid(text):
        return None  # Hard filter
    
    if is_likely_senior(text, title):
        # Keep but mark for penalty
        pass
    
    # Build URL
    hn_url = f"https://news.ycombinator.com/item?id={comment.get('objectID', '')}"
    
    return Job(
        title=title[:100],  # Truncate if needed
        company=company[:100],
        url=hn_url,
        source="hackernews",
        location=location,
        remote=remote,
        paid=True,  # HN jobs are typically paid
        description=text[:5000],  # Limit description size
        requirements=[],
    )


def scrape_hackernews(max_jobs: int = 100) -> list[Job]:
    """
    Main entry point: scrape the latest HN "Who's Hiring" thread.
    
    Args:
        max_jobs: Maximum number of jobs to return
        
    Returns:
        List of Job objects
    """
    print("[HN] Searching for latest 'Who's Hiring' thread...")
    
    thread = find_latest_hiring_thread()
    if not thread:
        print("[HN] No hiring thread found!")
        return []
    
    thread_id = thread.get("objectID")
    print(f"[HN] Found thread: {thread.get('title')} (ID: {thread_id})")
    
    print("[HN] Fetching comments...")
    comments = get_thread_comments(thread_id, max_comments=500)
    print(f"[HN] Found {len(comments)} top-level comments")
    
    jobs = []
    for comment in comments:
        try:
            job = parse_hn_comment(comment)
            if job:
                job.job_id = job.generate_job_id()
                jobs.append(job)
        except Exception as e:
            # Skip malformed comments
            continue
    
    print(f"[HN] Parsed {len(jobs)} valid job postings")
    
    # Limit to max_jobs
    return jobs[:max_jobs]


if __name__ == "__main__":
    # Test the scraper
    jobs = scrape_hackernews(max_jobs=10)
    for job in jobs:
        print(f"- {job.company}: {job.title} ({job.location})")
