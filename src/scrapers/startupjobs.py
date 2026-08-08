"""
Startup Jobs scraper adapter.

Uses Startup Jobs RSS by default for a no-auth path, with an optional API mode
if a free Startup Jobs API key is available. This source is startup-heavy and
strong for PM/APM/founding/product-engineer roles.
"""

import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional

import requests

from ..models import Job


RSS_URL = "https://startup.jobs/feeds/jobs"
API_URL = "https://api.startup.jobs/v1/jobs"


@dataclass
class StartupJobsConfig:
    role: str = "product-manager"
    workplace: str = "remote"
    max_results: int = 40
    mode: str = "rss"
    api_key: Optional[str] = None


def _get_config(max_results: int = 40) -> StartupJobsConfig:
    return StartupJobsConfig(
        max_results=max_results,
        api_key=os.environ.get("STARTUPJOBS_API_KEY"),
    )


def _parse_title_company(raw_title: str) -> tuple[str, str]:
    title = raw_title.strip()
    company = "Unknown Company"

    role_indicators = [
        "product manager", "associate product manager", "apm", "engineer",
        "intern", "junior", "senior", "lead", "principal", "product",
    ]

    for separator in [" at ", " - "]:
        if separator in raw_title.lower():
            parts = [p.strip() for p in raw_title.split(separator, 1) if p.strip()]
            if len(parts) >= 2:
                left, right = parts[0], parts[1]
                left_is_role = any(ind in left.lower() for ind in role_indicators)
                right_is_role = any(ind in right.lower() for ind in role_indicators)

                if left_is_role and not right_is_role:
                    title = left
                    company = right
                elif right_is_role and not left_is_role:
                    title = right
                    company = left
                else:
                    # Default to original ordering: assume left=title, right=company
                    title = parts[0]
                    company = parts[1]
            break

    return title[:200], company[:100]


def _fetch_rss_jobs(config: StartupJobsConfig) -> list[Job]:
    params = {"role": config.role}
    if config.workplace:
        params["workplace"] = config.workplace

    response = requests.get(RSS_URL, params=params, timeout=20)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    channel = root.find("channel")
    if channel is None:
        return []

    jobs: list[Job] = []
    for item in channel.findall("item"):
        raw_title = item.findtext("title", default="")
        url = item.findtext("link", default="")
        description = item.findtext("description", default="")

        if not raw_title or not url:
            continue

        title, company = _parse_title_company(raw_title)
        text = f"{raw_title} {description}".lower()
        location = "Remote" if "remote" in text else "Unknown"

        jobs.append(
            Job(
                title=title,
                company=company,
                url=url,
                source="startupjobs",
                location=location,
                remote=(location == "Remote"),
                description=description[:3000],
            )
        )

        if len(jobs) >= config.max_results:
            break

    return jobs


def _fetch_api_jobs(config: StartupJobsConfig) -> list[Job]:
    if not config.api_key:
        return []

    jobs: list[Job] = []
    page = 1
    headers = {"Authorization": f"Bearer {config.api_key}"}

    while len(jobs) < config.max_results:
        params = {
            "role": config.role,
            "page": page,
        }
        if config.workplace:
            params["workplace_type"] = config.workplace

        response = requests.get(API_URL, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        items = payload.get("jobs", payload.get("data", [])) or []

        if not items:
            break

        for item in items:
            title = item.get("title") or item.get("job_title") or ""
            company = item.get("company", {}).get("name") if isinstance(item.get("company"), dict) else item.get("company_name", "Unknown Company")
            url = item.get("url") or item.get("absolute_url") or item.get("job_url") or ""
            description = item.get("description") or item.get("body") or ""

            if not title or not url:
                continue

            location = item.get("location", {}).get("name", "Unknown") if isinstance(item.get("location"), dict) else item.get("location", "Unknown")

            jobs.append(
                Job(
                    title=title[:200],
                    company=(company or "Unknown Company")[:100],
                    url=url,
                    source="startupjobs",
                    location=location,
                    remote=bool(item.get("remote", False)),
                    description=description[:3000],
                )
            )

            if len(jobs) >= config.max_results:
                break

        page += 1
        time.sleep(3)  # 20 RPM limit -> keep well below it.

    return jobs


def scrape_startupjobs_jobs(max_results: int = 40, mode: str = "rss") -> List[Job]:
    """Scrape startup/PM roles from Startup Jobs via RSS or API."""
    config = _get_config(max_results=max_results)
    config.mode = mode

    try:
        if config.mode.lower() == "api":
            jobs = _fetch_api_jobs(config)
            if jobs:
                return jobs[:max_results]

        return _fetch_rss_jobs(config)[:max_results]
    except Exception as e:
        print(f"[StartupJobs] Error: {e}")
        return []