"""
Date utilities for job freshness detection.

Parses dates from job postings and determines if jobs are too old.
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Maximum age in days for a job to be considered "fresh"
MAX_JOB_AGE_DAYS = 45  # ~6 weeks


def detect_posted_date(title: str, description: str, url: str) -> Optional[datetime]:
    """
    Try to extract a posted date from job content.
    
    Checks for common date patterns in titles, descriptions, and URLs.
    Returns datetime if found, None otherwise.
    """
    text = f"{title} {description}".lower()
    now = datetime.now()
    
    # Pattern 1: "Posted X days ago"
    match = re.search(r'posted\s+(\d+)\s+days?\s+ago', text)
    if match:
        days = int(match.group(1))
        return now - timedelta(days=days)
    
    # Pattern 2: "Posted X hours ago"
    match = re.search(r'posted\s+(\d+)\s+hours?\s+ago', text)
    if match:
        hours = int(match.group(1))
        return now - timedelta(hours=hours)
    
    # Pattern 3: "Posted X weeks ago"
    match = re.search(r'posted\s+(\d+)\s+weeks?\s+ago', text)
    if match:
        weeks = int(match.group(1))
        return now - timedelta(weeks=weeks)
    
    # Pattern 4: "Posted X months ago"
    match = re.search(r'posted\s+(\d+)\s+months?\s+ago', text)
    if match:
        months = int(match.group(1))
        return now - timedelta(days=months * 30)
    
    # Pattern 5: Explicit dates (Jan 15, 2026 / January 15, 2026 / 2026-01-15)
    month_names = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'june': 6, 'july': 7, 'august': 8, 'september': 9,
        'october': 10, 'november': 11, 'december': 12,
    }
    
    # "Month Day, Year" pattern
    match = re.search(
        r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
        r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|'
        r'dec(?:ember)?)\s+(\d{1,2}),?\s*(\d{4})', text
    )
    if match:
        month = month_names.get(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))
        if month and 2024 <= year <= 2027 and 1 <= day <= 31:
            try:
                return datetime(year, month, day)
            except ValueError:
                pass
    
    # ISO date: "2026-01-15"
    match = re.search(r'(202[4-7])-(\d{2})-(\d{2})', text)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass
    
    return None


def is_job_too_old(job_posted_date: Optional[datetime], max_age_days: int = MAX_JOB_AGE_DAYS) -> bool:
    """
    Check if a job is too old based on its posted date.
    
    Returns True if the job is older than max_age_days.
    Returns False if date is None (give benefit of the doubt).
    """
    if job_posted_date is None:
        return False  # Can't determine age, keep it
    
    age = datetime.now() - job_posted_date
    return age.days > max_age_days


def is_likely_stale(title: str, description: str) -> bool:
    """
    Heuristic check for stale job indicators in text.
    
    Catches jobs that mention old years or have "closed" indicators.
    """
    text = f"{title} {description}".lower()
    now = datetime.now()
    current_year = now.year
    
    # Check for old year references (e.g., "Summer 2024" when it's 2026)
    for old_year in range(2020, current_year - 1):
        year_patterns = [
            f'summer {old_year}', f'fall {old_year}', f'spring {old_year}',
            f'winter {old_year}', f'{old_year} intern', f'intern {old_year}',
            f'class of {old_year}', f'cohort {old_year}',
        ]
        if any(pattern in text for pattern in year_patterns):
            return True
    
    # Check for "closed" or "expired" indicators
    closed_keywords = [
        'position filled', 'no longer accepting', 'this position has been filled',
        'job closed', 'application closed', 'posting expired', 'position closed',
    ]
    if any(keyword in text for keyword in closed_keywords):
        return True
    
    return False
