"""
Deduplication utilities.
Tracks seen jobs to avoid sending duplicates.
"""

import json
from pathlib import Path
from typing import Optional

from src.models import Job
from src.utils.config import get_project_root


def get_cache_path() -> Path:
    """Get the path to the seen jobs cache file."""
    return get_project_root() / "data" / "seen_jobs.json"


def load_seen_jobs() -> set[str]:
    """Load the set of previously seen job IDs."""
    cache_path = get_cache_path()
    
    if not cache_path.exists():
        return set()
    
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("seen_ids", []))
    except Exception as e:
        print(f"[DEDUP] Error loading cache: {e}")
        return set()


def save_seen_jobs(seen_ids: set[str]) -> None:
    """Save the set of seen job IDs."""
    cache_path = get_cache_path()
    
    # Ensure directory exists
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"seen_ids": list(seen_ids)}, f, indent=2)
    except Exception as e:
        print(f"[DEDUP] Error saving cache: {e}")


def filter_new_jobs(jobs: list[Job]) -> list[Job]:
    """
    Filter out jobs that have already been seen.
    Updates the cache with new job IDs.
    """
    seen_ids = load_seen_jobs()
    
    new_jobs = []
    for job in jobs:
        # Generate ID if not set
        if not job.job_id:
            job.job_id = job.generate_job_id()
        
        if job.job_id not in seen_ids:
            new_jobs.append(job)
            seen_ids.add(job.job_id)
    
    # Save updated cache
    save_seen_jobs(seen_ids)
    
    print(f"[DEDUP] {len(new_jobs)} new jobs out of {len(jobs)} total")
    return new_jobs


def clear_cache() -> None:
    """Clear the seen jobs cache."""
    cache_path = get_cache_path()
    if cache_path.exists():
        cache_path.unlink()
        print("[DEDUP] Cache cleared")
