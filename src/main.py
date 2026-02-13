"""
AI Job Discovery System - Main Entry Point

This is the main orchestration script that:
1. Scrapes jobs from multiple sources
2. Parses with LLM (extraction only)
3. Applies hard filters
4. Scores with deterministic rules
5. Ranks and sends email report
"""

import argparse
import sys
from datetime import datetime

from src.models import Job
from src.scrapers.hackernews import scrape_hackernews
from src.scrapers.ycombinator import scrape_ycombinator_jobs
from src.scrapers.remotive import scrape_remotive_jobs
from src.scrapers.wellfound import scrape_wellfound_jobs
from src.scrapers.huggingface import scrape_huggingface_jobs
from src.scrapers.tavily_jobs import scrape_jobs_with_tavily
from src.scrapers.adzuna import scrape_adzuna_jobs
from src.scrapers.indeed import scrape_indeed_jobs
from src.scrapers.weworkremotely import scrape_weworkremotely_jobs
from src.scrapers.remoteok import scrape_remoteok_jobs
from src.scrapers.himalayas import scrape_himalayas_jobs
from src.scrapers.justremote import scrape_justremote_jobs
from src.scrapers.llm_parser import parse_job_with_llm
from src.scoring.engine import apply_hard_filters, score_job, rank_jobs
from src.emailer import send_email
from src.utils.dedup import filter_new_jobs
from src.utils.config import load_settings
from src.utils.web_search import search_company_info, clear_cache, get_api_call_count


def run_pipeline(
    dry_run: bool = False,
    skip_email: bool = False,
    max_jobs_per_source: int = 50,
    skip_dedup: bool = False,
) -> list[Job]:
    """
    Run the complete job discovery pipeline.
    
    Args:
        dry_run: If True, print email instead of sending
        skip_email: If True, skip email entirely
        max_jobs_per_source: Max jobs to fetch per source
        skip_dedup: If True, don't filter previously seen jobs
        
    Returns:
        List of scored and ranked jobs
    """
    settings = load_settings()
    
    print("=" * 60)
    print("AI JOB DISCOVERY PIPELINE")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    all_jobs: list[Job] = []
    
    # =========================================
    # STEP 1: Scrape from multiple sources
    # =========================================
    print("\n[STEP 1] Scraping job sources...")
    
    # Hacker News
    if settings.hackernews.get("enabled", True):
        try:
            hn_jobs = scrape_hackernews(max_jobs=max_jobs_per_source)
            all_jobs.extend(hn_jobs)
            print(f"  - HN: {len(hn_jobs)} jobs")
        except Exception as e:
            print(f"  - HN: Error - {e}")
    
    # YC Work at a Startup
    if settings.ycombinator.get("enabled", True):
        try:
            yc_jobs = scrape_ycombinator_jobs(max_results=settings.ycombinator.get("max_results", 30))
            all_jobs.extend(yc_jobs)
            print(f"  - YC: {len(yc_jobs)} jobs")
        except Exception as e:
            print(f"  - YC: Error - {e}")
    
    # Remotive AI/ML
    if settings.remotive.get("enabled", True):
        try:
            remotive_jobs = scrape_remotive_jobs(max_results=settings.remotive.get("max_results", 30))
            all_jobs.extend(remotive_jobs)
            print(f"  - Remotive: {len(remotive_jobs)} jobs")
        except Exception as e:
            print(f"  - Remotive: Error - {e}")
    
    # Wellfound (AngelList)
    if settings.wellfound.get("enabled", True):
        try:
            wellfound_jobs = scrape_wellfound_jobs(max_results=settings.wellfound.get("max_results", 30))
            all_jobs.extend(wellfound_jobs)
            print(f"  - Wellfound: {len(wellfound_jobs)} jobs")
        except Exception as e:
            print(f"  - Wellfound: Error - {e}")
    
    # Hugging Face
    if settings.huggingface.get("enabled", True):
        try:
            hf_jobs = scrape_huggingface_jobs(max_results=settings.huggingface.get("max_results", 20))
            all_jobs.extend(hf_jobs)
            print(f"  - Hugging Face: {len(hf_jobs)} jobs")
        except Exception as e:
            print(f"  - Hugging Face: Error - {e}")
    
    # Tavily Web Search (bypasses bot detection)
    if settings.tavily_jobs.get("enabled", True):
        try:
            tavily_jobs = scrape_jobs_with_tavily(max_results=settings.tavily_jobs.get("max_results", 30))
            all_jobs.extend(tavily_jobs)
            print(f"  - Tavily Search: {len(tavily_jobs)} jobs")
        except Exception as e:
            print(f"  - Tavily Search: Error - {e}")
    
    # Adzuna Jobs API
    if settings.adzuna.get("enabled", False):
        try:
            adzuna_jobs = scrape_adzuna_jobs(max_results=settings.adzuna.get("max_results", 50))
            all_jobs.extend(adzuna_jobs)
            print(f"  - Adzuna: {len(adzuna_jobs)} jobs")
        except Exception as e:
            print(f"  - Adzuna: Error - {e}")
    
    # Indeed Jobs API
    if settings.indeed.get("enabled", False):
        try:
            indeed_jobs = scrape_indeed_jobs(max_results=settings.indeed.get("max_results", 50))
            all_jobs.extend(indeed_jobs)
            print(f"  - Indeed: {len(indeed_jobs)} jobs")
        except Exception as e:
            print(f"  - Indeed: Error - {e}")
    
    # We Work Remotely
    if settings.weworkremotely.get("enabled", False):
        try:
            wwr_jobs = scrape_weworkremotely_jobs(max_results=settings.weworkremotely.get("max_results", 30))
            all_jobs.extend(wwr_jobs)
            print(f"  - WeWorkRemotely: {len(wwr_jobs)} jobs")
        except Exception as e:
            print(f"  - WeWorkRemotely: Error - {e}")
    
    # RemoteOK (free JSON API)
    if settings.remoteok.get("enabled", False):
        try:
            ro_jobs = scrape_remoteok_jobs(max_results=settings.remoteok.get("max_results", 50))
            all_jobs.extend(ro_jobs)
            print(f"  - RemoteOK: {len(ro_jobs)} jobs")
        except Exception as e:
            print(f"  - RemoteOK: Error - {e}")
    
    # Himalayas (free scraping)
    if settings.himalayas.get("enabled", False):
        try:
            him_jobs = scrape_himalayas_jobs(max_results=settings.himalayas.get("max_results", 50))
            all_jobs.extend(him_jobs)
            print(f"  - Himalayas: {len(him_jobs)} jobs")
        except Exception as e:
            print(f"  - Himalayas: Error - {e}")
    
    # JustRemote (free scraping)
    if settings.justremote.get("enabled", False):
        try:
            jr_jobs = scrape_justremote_jobs(max_results=settings.justremote.get("max_results", 50))
            all_jobs.extend(jr_jobs)
            print(f"  - JustRemote: {len(jr_jobs)} jobs")
        except Exception as e:
            print(f"  - JustRemote: Error - {e}")
    
    print(f"  Total scraped: {len(all_jobs)} jobs")
    
    if not all_jobs:
        print("\n[ERROR] No jobs scraped. Exiting.")
        return []
    
    # =========================================
    # STEP 2: Deduplication
    # =========================================
    if not skip_dedup:
        print("\n[STEP 2] Deduplicating...")
        all_jobs = filter_new_jobs(all_jobs)
        
        if not all_jobs:
            print("  No new jobs found. Exiting.")
            return []
    else:
        print("\n[STEP 2] Skipping deduplication (--skip-dedup)")
    
    # =========================================
    # STEP 3: LLM Extraction (flags only)
    # =========================================
    print(f"\n[STEP 3] Extracting flags with LLM ({len(all_jobs)} jobs)...")
    
    # Track LLM vs fallback usage
    llm_success_count = 0
    fallback_count = 0
    
    for i, job in enumerate(all_jobs):
        try:
            job, used_fallback = parse_job_with_llm(job, use_fallback=True)
            if used_fallback:
                fallback_count += 1
            else:
                llm_success_count += 1
            
            if (i + 1) % 10 == 0:
                print(f"  Parsed {i + 1}/{len(all_jobs)}")
        except Exception as e:
            print(f"  Error parsing {job.title}: {e}")
    
    # Report extraction method used
    print(f"\n  📊 EXTRACTION REPORT:")
    if llm_success_count > 0:
        print(f"  ✓ LLM (AI) extractions: {llm_success_count}/{len(all_jobs)} ({llm_success_count/len(all_jobs)*100:.1f}%)")
    if fallback_count > 0:
        print(f"  ⚠ FALLBACK (regex) extractions: {fallback_count}/{len(all_jobs)} ({fallback_count/len(all_jobs)*100:.1f}%)")
        print(f"  ⚠ WARNING: LLM extraction failed, using keyword matching instead of AI analysis")
        print(f"  ⚠ Fix: Check Groq API key or update groq SDK version")
    
    # =========================================
    # STEP 4: Hard Filters
    # =========================================
    print("\n[STEP 4] Applying hard filters...")
    
    filtered_jobs = [job for job in all_jobs if apply_hard_filters(job)]
    print(f"  Kept: {len(filtered_jobs)}/{len(all_jobs)} jobs")
    
    if not filtered_jobs:
        print("  No jobs passed filters. Exiting.")
        return []
    
    # =========================================
    # STEP 4.5: Company Enrichment (Web Search)
    # =========================================
    tavily_settings = settings.tavily if hasattr(settings, 'tavily') and isinstance(settings.tavily, dict) else {}
    if tavily_settings.get("enabled", False) and tavily_settings.get("enrich_companies", True):
        max_enrich = tavily_settings.get("max_enrichment_jobs", 30)
        jobs_to_enrich = filtered_jobs[:max_enrich]
        
        print(f"\n[STEP 4.5] Enriching companies via web search ({len(jobs_to_enrich)} jobs)...")
        print(f"  Rate limiting: 1.5s between API calls (be nice to Tavily)")
        
        # Clear cache at start of enrichment
        clear_cache()
        
        enriched_count = 0
        failed_count = 0
        
        for i, job in enumerate(jobs_to_enrich):
            try:
                enrichment = search_company_info(job.company)
                if enrichment and (enrichment.employee_count or enrichment.is_ai_company):
                    job.company_enrichment = enrichment
                    enriched_count += 1
                
                if (i + 1) % 5 == 0:
                    print(f"  Progress: {i + 1}/{len(jobs_to_enrich)} companies processed")
            except Exception as e:
                failed_count += 1
                print(f"  ERROR: Failed to enrich {job.company}: {e}")
        
        print(f"  ✓ Successfully enriched {enriched_count}/{len(jobs_to_enrich)} companies")
        if failed_count > 0:
            print(f"  ⚠ {failed_count} enrichment(s) failed (using fallback data)")
        
        # Report API usage
        api_calls = get_api_call_count()
        print(f"  📊 API calls used: {api_calls} (cache saved {len(jobs_to_enrich) - api_calls} calls)")
        print(f"  💰 Credits used: ~{api_calls} (1000/month free tier)")
    else:
        print("\n[STEP 4.5] Company enrichment disabled (set tavily.enabled=true to enable)")
    
    # =========================================
    # STEP 5: Scoring (deterministic)
    # =========================================
    print(f"\n[STEP 5] Scoring {len(filtered_jobs)} jobs...")
    
    for job in filtered_jobs:
        score_job(job)
    
    # =========================================
    # STEP 6: Ranking
    # =========================================
    print("\n[STEP 6] Ranking...")
    
    min_score = settings.scoring.get("minimum_score", 60)
    top_n = settings.scoring.get("top_n_jobs", 20)
    
    ranked_jobs = rank_jobs(filtered_jobs, min_score=min_score, top_n=top_n)
    print(f"  Top {len(ranked_jobs)} jobs (score >= {min_score})")
    
    if not ranked_jobs:
        print("  No jobs above threshold. Consider lowering minimum_score.")
        return []
    
    # =========================================
    # STEP 7: Email Report
    # =========================================
    if not skip_email:
        print("\n[STEP 7] Sending email report...")
        success = send_email(ranked_jobs, dry_run=dry_run)
        if success:
            print("  Email sent successfully!")
        else:
            print("  Email failed!")
    else:
        print("\n[STEP 7] Skipping email (--skip-email)")
    
    # =========================================
    # Summary
    # =========================================
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print(f"Finished: {datetime.now().isoformat()}")
    print(f"Results: {len(ranked_jobs)} jobs ready")
    print("=" * 60)
    
    # Print top 5 for quick preview
    print("\nTop 5 Preview:")
    for i, job in enumerate(ranked_jobs[:5], 1):
        print(f"  {i}. {job.company}: {job.title} (Score: {job.score:.1f})")
    
    return ranked_jobs


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI Job Discovery System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main                    # Run full pipeline
  python -m src.main --dry-run          # Preview email without sending
  python -m src.main --skip-email       # Run without sending email
  python -m src.main --skip-dedup       # Include previously seen jobs
        """
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print email instead of sending"
    )
    
    parser.add_argument(
        "--skip-email",
        action="store_true",
        help="Skip sending email entirely"
    )
    
    parser.add_argument(
        "--skip-dedup",
        action="store_true",
        help="Don't filter previously seen jobs"
    )
    
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=50,
        help="Max jobs per source (default: 50)"
    )
    
    args = parser.parse_args()
    
    try:
        jobs = run_pipeline(
            dry_run=args.dry_run,
            skip_email=args.skip_email,
            skip_dedup=args.skip_dedup,
            max_jobs_per_source=args.max_jobs,
        )
        
        if jobs:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
