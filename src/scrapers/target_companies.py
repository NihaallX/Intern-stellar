"""
Target Companies Scraper.

Searches for PM / APM / AI PM roles at a curated list of remote-friendly
IT companies (sourced from Remote_IT_Companies.xlsx).

Strategy: batches 5 company domains per Tavily query → ~9 credits/run
instead of 41 individual lookups.
"""

import logging
import time
from typing import List
from urllib.parse import urlparse

from tavily import TavilyClient

from ..models import Job
from ..utils.config import get_tavily_api_key

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# Company list (from Remote_IT_Companies.xlsx)
# Format: (Company Name, Industry, Career Page URL)
# ─────────────────────────────────────────────────────────────────
TARGET_COMPANIES: list[tuple[str, str, str]] = [
    ("Automattic",          "Technology",               "https://automattic.com/work-with-us/"),
    ("Buffer",              "Social Media",             "https://buffer.com/journey"),
    ("Basecamp",            "Project Management",       "https://basecamp.com/jobs"),
    ("Zapier",              "Productivity Tools",       "https://zapier.com/jobs/"),
    ("GitLab",              "Technology",               "https://about.gitlab.com/jobs/"),
    ("InVision",            "Design",                   "https://www.invisionapp.com/company#jobs"),
    ("Toggl",               "Time Tracking",            "https://toggl.com/jobs/"),
    ("Hotjar",              "Analytics",                "https://careers.hotjar.com/"),
    ("Toptal",              "Freelance Platform",       "https://www.toptal.com/careers"),
    ("GitHub",              "Technology",               "https://github.com/about/careers"),
    ("DuckDuckGo",          "Search Engine",            "https://duckduckgo.com/hiring"),
    ("Dell",                "Technology",               "https://jobs.dell.com/"),
    ("Mozilla",             "Technology",               "https://www.mozilla.org/en-US/careers/"),
    ("Aha!",                "Product Management",       "https://www.aha.io/company/careers"),
    ("Twilio",              "Cloud Communications",     "https://www.twilio.com/company/jobs"),
    ("HubSpot",             "Marketing & CRM",          "https://www.hubspot.com/careers"),
    ("Zscaler",             "Cybersecurity",            "https://www.zscaler.com/careers"),
    ("Shopify",             "E-commerce",               "https://www.shopify.com/careers"),
    ("Zillow Group",        "Real Estate",              "https://www.zillowgroup.com/careers/"),
    ("Elastic",             "Search Technology",        "https://www.elastic.co/careers/"),
    ("Atlassian",           "Software Development",     "https://www.atlassian.com/company/careers"),
    ("Zoom",                "Video Communications",     "https://zoom.us/careers"),
    ("Stripe",              "Payment Processing",       "https://stripe.com/jobs"),
    ("Stack Overflow",      "Developer Community",      "https://stackoverflow.com/company/careers"),
    ("Wise",                "Financial Technology",     "https://wise.com/jobs"),
    ("Airtable",            "Collaboration Software",   "https://airtable.com/careers"),
    ("HashiCorp",           "Infrastructure Software",  "https://www.hashicorp.com/careers"),
    ("MongoDB",             "Database Technology",      "https://www.mongodb.com/careers"),
    ("Okta",                "Identity Management",      "https://www.okta.com/company/careers/"),
    ("PagerDuty",           "Incident Management",      "https://www.pagerduty.com/careers/"),
    ("Palo Alto Networks",  "Cybersecurity",            "https://www.paloaltonetworks.com/company/careers"),
    ("DigitalOcean",        "Cloud Infrastructure",     "https://www.digitalocean.com/careers"),
    ("Help Scout",          "Customer Support",         "https://www.helpscout.com/company/careers/"),
    ("Andela",              "Talent Marketplace",       "https://andela.com/careers/"),
    ("Deel",                "HR & Payroll",             "https://www.deel.com/careers"),
    ("Collibra",            "Data Intelligence",        "https://www.collibra.com/careers"),
    ("Karat",               "Technical Interviewing",   "https://karat.com/careers"),
    ("Dscout",              "Research Software",        "https://dscout.com/company/careers"),
    ("Modus Create",        "Digital Consulting",       "https://moduscreate.com/careers/"),
    ("Chainlink Labs",      "Blockchain",               "https://chainlinklabs.com/careers"),
    ("Epic Games",          "Game Development",         "https://www.epicgames.com/site/en-US/careers"),
]

# PM / AI keywords we're targeting
_ROLE_KEYWORDS = (
    '"product manager" OR "associate product manager" OR "APM" OR '
    '"AI product manager" OR "technical program manager"'
)

# How many companies to group per Tavily query
_BATCH_SIZE = 5


def _domain(url: str) -> str:
    """Extract bare domain from a URL."""
    parsed = urlparse(url)
    return parsed.netloc.lstrip("www.")


def scrape_target_companies(max_results: int = 50) -> List[Job]:
    """
    Search for PM/APM/AI PM openings at the curated list of
    remote-friendly companies using batched Tavily queries.

    Args:
        max_results: cap on returned Job objects

    Returns:
        List of Job objects
    """
    jobs: List[Job] = []

    try:
        api_key = get_tavily_api_key()
        client = TavilyClient(api_key=api_key)
    except Exception as e:
        logger.error(f"[TARGET] Tavily init failed: {e}")
        print(f"[TARGET] Tavily init failed: {e}")
        return []

    # Build batches of (company, domain) pairs
    batches: list[list[tuple[str, str, str]]] = []
    for i in range(0, len(TARGET_COMPANIES), _BATCH_SIZE):
        batches.append(TARGET_COMPANIES[i : i + _BATCH_SIZE])

    print(f"[TARGET] Searching {len(TARGET_COMPANIES)} companies in {len(batches)} batched queries…")

    for batch_idx, batch in enumerate(batches):
        # Build a combined site: query for the batch
        # e.g. (site:zapier.com OR site:gitlab.com OR site:buffer.com) "product manager"
        site_clauses = " OR ".join(
            f'site:{_domain(career_url)}' for _, _, career_url in batch
        )
        query = f'({site_clauses}) {_ROLE_KEYWORDS}'

        # Build a name→domain lookup for this batch
        name_for: dict[str, str] = {
            _domain(career_url): name for name, _, career_url in batch
        }

        try:
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=5,
                days=45,
            )

            for result in response.get("results", []):
                title   = result.get("title", "").strip()
                url     = result.get("url", "").strip()
                content = result.get("content", "")

                if not title or not url or len(title) < 5:
                    continue

                # Skip listing / search pages
                skip_kw = ["search", "all jobs", "job listings", "careers page",
                           "browse", "category", "jobs in"]
                if any(kw in url.lower() for kw in skip_kw):
                    continue
                if any(kw in title.lower() for kw in skip_kw):
                    continue

                # Resolve company name from domain
                result_domain = urlparse(url).netloc.lstrip("www.")
                company = next(
                    (name for dom, name in name_for.items() if dom in result_domain),
                    result_domain.split(".")[0].title(),
                )

                # Determine location
                text_lower = f"{title} {content}".lower()
                if "remote" in text_lower:
                    location = "Remote"
                elif "india" in text_lower or "bangalore" in text_lower or "bengaluru" in text_lower:
                    location = "India"
                else:
                    location = "Unknown"

                jobs.append(Job(
                    title=title,
                    company=company,
                    url=url,
                    source="target_companies",
                    location=location,
                    remote=(location == "Remote"),
                    description=content[:2000],
                ))

        except Exception as e:
            logger.warning(f"[TARGET] Batch {batch_idx + 1} failed: {e}")
            print(f"[TARGET] Batch {batch_idx + 1} error: {e}")

        time.sleep(1.5)  # rate-limit

    # Dedup by URL
    seen: set[str] = set()
    unique: List[Job] = []
    for j in jobs:
        if j.url not in seen:
            seen.add(j.url)
            unique.append(j)

    print(f"[TARGET] Found {len(unique)} unique roles across {len(TARGET_COMPANIES)} target companies")
    return unique[:max_results]
