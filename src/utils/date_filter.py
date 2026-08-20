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
MAX_JOB_AGE_DAYS = 60  # 2 months max


def detect_posted_date(title: str, description: str, url: str) -> Optional[datetime]:
    """
    Try to extract a posted date from job content.
    
    Checks for common date patterns in titles, descriptions, and URLs.
    Returns datetime if found, None otherwise.
    """
    text = f"{title} {description} {url}".lower()
    now = datetime.now()
    
    # Pattern 1: "Posted X days ago" or "X days ago" / "X d ago"
    match = re.search(r'(?:posted\s+)?(\d+)\s*(?:days?|d)\s+ago', text)
    if match:
        days = int(match.group(1))
        return now - timedelta(days=days)
    
    # Pattern 2: "Posted X hours ago" or "X hours ago" / "X h ago"
    match = re.search(r'(?:posted\s+)?(\d+)\s*(?:hours?|hrs?|h)\s+ago', text)
    if match:
        hours = int(match.group(1))
        return now - timedelta(hours=hours)
    
    # Pattern 3: "Posted X weeks ago" or "X weeks ago" / "X w ago"
    match = re.search(r'(?:posted\s+)?(\d+)\s*(?:weeks?|wks?|w)\s+ago', text)
    if match:
        weeks = int(match.group(1))
        return now - timedelta(weeks=weeks)
    
    # Pattern 4: "Posted X months ago" or "X months ago" / "X mo ago"
    match = re.search(r'(?:posted\s+)?(\d+)\s*(?:months?|mos?)\s+ago', text)
    if match:
        months = int(match.group(1))
        return now - timedelta(days=months * 30)
    
    # Month name mapping
    month_names = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'june': 6, 'july': 7, 'august': 8, 'september': 9,
        'october': 10, 'november': 11, 'december': 12,
    }
    
    month_regex = r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
    
    # Pattern 5: "Month Day, Year" or "Month Day Year" (e.g. Feb 26th, 2026 / February 26 2026)
    match = re.search(
        month_regex + r'\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})', text
    )
    if match:
        month = month_names.get(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))
        if month and 2020 <= year <= 2030 and 1 <= day <= 31:
            try:
                return datetime(year, month, day)
            except ValueError:
                pass
    
    # Pattern 5b: "Day Month Year" (e.g. 26th Feb 2026)
    match = re.search(
        r'(\d{1,2})(?:st|nd|rd|th)?\s+' + month_regex + r',?\s*(\d{4})', text
    )
    if match:
        day = int(match.group(1))
        month = month_names.get(match.group(2))
        year = int(match.group(3))
        if month and 2020 <= year <= 2030 and 1 <= day <= 31:
            try:
                return datetime(year, month, day)
            except ValueError:
                pass
    
    # Pattern 6: Month Day WITHOUT year (e.g. "Feb 26", "February 26th", "26 Feb")
    match = re.search(
        month_regex + r'\s+(\d{1,2})(?:st|nd|rd|th)?\b', text
    )
    if match:
        month = month_names.get(match.group(1))
        day = int(match.group(2))
        if month and 1 <= day <= 31:
            try:
                candidate_year = now.year
                d = datetime(candidate_year, month, day)
                if d > now:
                    d = datetime(candidate_year - 1, month, day)
                return d
            except ValueError:
                pass
    
    match = re.search(
        r'\b(\d{1,2})(?:st|nd|rd|th)?\s+' + month_regex + r'\b', text
    )
    if match:
        day = int(match.group(1))
        month = month_names.get(match.group(2))
        if month and 1 <= day <= 31:
            try:
                candidate_year = now.year
                d = datetime(candidate_year, month, day)
                if d > now:
                    d = datetime(candidate_year - 1, month, day)
                return d
            except ValueError:
                pass
    
    # Pattern 7: ISO date: "2026-01-15" or "2026/01/15"
    match = re.search(r'(202[0-9])[-/](\d{2})[-/](\d{2})', text)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass
    
    # Pattern 8: Slash date: "02/26/2026" or "26/02/2026"
    match = re.search(r'\b(\d{1,2})/(\d{1,2})/(202[0-9])\b', text)
    if match:
        g1, g2, yr = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if 1 <= g1 <= 12 and 1 <= g2 <= 31:
            try:
                return datetime(yr, g1, g2)
            except ValueError:
                pass
        if 1 <= g2 <= 12 and 1 <= g1 <= 31:
            try:
                return datetime(yr, g2, g1)
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

