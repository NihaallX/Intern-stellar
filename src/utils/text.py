"""
Text processing utilities.
"""

import re
import hashlib
from typing import Optional


def clean_text(text: str) -> str:
    """
    Clean and normalize text for processing.
    - Remove excessive whitespace
    - Normalize line breaks
    - Strip HTML tags
    """
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def generate_job_hash(url: str, title: str, company: str) -> str:
    """Generate a unique hash for job deduplication."""
    content = f"{url}|{title}|{company}".lower()
    return hashlib.md5(content.encode()).hexdigest()[:16]


def extract_salary_range(text: str) -> tuple[Optional[int], Optional[int], str]:
    """
    Extract salary range from text.
    Returns (min_salary, max_salary, currency).
    """
    # Common patterns
    patterns = [
        # $100k - $150k
        r'\$(\d+)k?\s*[-–]\s*\$?(\d+)k',
        # $100,000 - $150,000
        r'\$(\d{1,3}(?:,\d{3})*)\s*[-–]\s*\$?(\d{1,3}(?:,\d{3})*)',
        # 100k-150k USD
        r'(\d+)k?\s*[-–]\s*(\d+)k?\s*(?:USD|usd)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            min_sal = match.group(1).replace(',', '')
            max_sal = match.group(2).replace(',', '')
            
            # Convert to int
            min_val = int(min_sal)
            max_val = int(max_sal)
            
            # Handle 'k' suffix
            if min_val < 1000:
                min_val *= 1000
            if max_val < 1000:
                max_val *= 1000
            
            return min_val, max_val, "USD"
    
    return None, None, "USD"


def is_likely_unpaid(text: str) -> bool:
    """Check if job description indicates unpaid position."""
    text_lower = text.lower()
    
    unpaid_indicators = [
        'unpaid',
        'volunteer',
        'no compensation',
        'equity only',
        'credit only',
        'for course credit',
    ]
    
    for indicator in unpaid_indicators:
        if indicator in text_lower:
            return True
    
    return False


def is_likely_senior(text: str, title: str) -> bool:
    """Check if role is senior-level."""
    combined = f"{title} {text}".lower()
    
    senior_indicators = [
        'senior',
        'sr.',
        'sr ',
        'lead',
        'principal',
        'staff',
        'director',
        'head of',
        'manager',
        '5+ years',
        '7+ years',
        '10+ years',
    ]
    
    for indicator in senior_indicators:
        if indicator in combined:
            return True
    
    return False


def is_likely_research(text: str, title: str) -> bool:
    """Check if role is research-heavy."""
    combined = f"{title} {text}".lower()
    
    research_indicators = [
        'research scientist',
        'research engineer',
        'phd required',
        'phd preferred',
        'publications required',
        'publish papers',
        'academic research',
        'novel algorithms',
        'theoretical',
    ]
    
    for indicator in research_indicators:
        if indicator in combined:
            return True
    
    return False
