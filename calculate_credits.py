"""
Tavily API Credit Usage Calculator
Helps optimize settings for free tier (1000 credits/month)
"""

def calculate_credits_per_run(max_enrichment_jobs: int, duplicate_company_rate: float = 0.3) -> dict:
    """
    Calculate expected API credit usage per pipeline run.
    
    Args:
        max_enrichment_jobs: Number of jobs to enrich (from settings)
        duplicate_company_rate: Estimated % of duplicate companies (cache hits)
        
    Returns:
        Dict with usage statistics
    """
    # Each company enrichment = 2 API calls (company info + tech stack)
    calls_per_company = 2
    
    # Account for duplicates (cache hits don't use API)
    unique_companies = int(max_enrichment_jobs * (1 - duplicate_company_rate))
    
    # Total API calls
    total_calls = unique_companies * calls_per_company
    
    # Credits (1 search = 1 credit on Tavily)
    total_credits = total_calls
    
    return {
        "max_jobs": max_enrichment_jobs,
        "unique_companies": unique_companies,
        "duplicate_rate": f"{duplicate_company_rate * 100:.0f}%",
        "calls_per_company": calls_per_company,
        "total_api_calls": total_calls,
        "total_credits": total_credits,
    }


def calculate_monthly_budget(runs_per_month: int, max_enrichment_jobs: int, duplicate_rate: float = 0.3) -> dict:
    """
    Calculate monthly credit usage and optimization suggestions.
    
    Args:
        runs_per_month: How many times pipeline runs per month
        max_enrichment_jobs: Jobs to enrich per run
        duplicate_rate: % of duplicate companies
        
    Returns:
        Dict with monthly projections
    """
    per_run = calculate_credits_per_run(max_enrichment_jobs, duplicate_rate)
    
    monthly_credits = per_run["total_credits"] * runs_per_month
    free_tier_limit = 1000
    remaining = free_tier_limit - monthly_credits
    
    # Suggested optimal settings
    if monthly_credits > free_tier_limit:
        # Calculate optimal max_enrichment_jobs
        optimal_jobs = int((free_tier_limit / runs_per_month) / 2 / (1 - duplicate_rate))
        suggestion = f"Reduce max_enrichment_jobs to {optimal_jobs} to stay under 1000 credits/month"
        status = "⚠️  OVER BUDGET"
    else:
        # How many more runs possible
        additional_runs = int(remaining / per_run["total_credits"])
        suggestion = f"You can do {additional_runs} more runs/month at current settings"
        status = "✅ WITHIN BUDGET"
    
    return {
        "runs_per_month": runs_per_month,
        "credits_per_run": per_run["total_credits"],
        "monthly_total": monthly_credits,
        "free_tier_limit": free_tier_limit,
        "remaining": remaining,
        "status": status,
        "suggestion": suggestion,
        "per_run_details": per_run,
    }


def print_credit_analysis():
    """Print comprehensive credit usage analysis."""
    print("=" * 70)
    print("TAVILY API CREDIT USAGE CALCULATOR")
    print("=" * 70)
    
    # Current settings
    current_max_jobs = 30  # from settings.yaml
    
    print(f"\n📊 CURRENT SETTINGS:")
    print(f"  max_enrichment_jobs: {current_max_jobs}")
    print(f"  Estimated duplicate rate: 30% (companies appear in multiple jobs)")
    
    # Per-run analysis
    print(f"\n💳 PER-RUN CREDIT USAGE:")
    per_run = calculate_credits_per_run(current_max_jobs, 0.3)
    print(f"  Jobs to enrich: {per_run['max_jobs']}")
    print(f"  Unique companies (~70%): {per_run['unique_companies']}")
    print(f"  API calls per company: {per_run['calls_per_company']}")
    print(f"  Total API calls: {per_run['total_api_calls']}")
    print(f"  Credits used: {per_run['total_credits']}")
    
    # Monthly scenarios
    print(f"\n📅 MONTHLY PROJECTIONS (1000 free credits):")
    print("-" * 70)
    
    scenarios = [
        ("Twice weekly (8 runs/month)", 8),
        ("Weekly (4 runs/month)", 4),
        ("Bi-weekly (2 runs/month)", 2),
        ("Daily on weekdays (20 runs/month)", 20),
    ]
    
    for scenario_name, runs in scenarios:
        result = calculate_monthly_budget(runs, current_max_jobs, duplicate_rate=0.3)
        print(f"\n  {scenario_name}:")
        print(f"    Credits used: {result['monthly_total']}/1000")
        print(f"    Status: {result['status']}")
        print(f"    {result['suggestion']}")
    
    # Optimization table
    print(f"\n🎯 OPTIMIZATION TABLE:")
    print("-" * 70)
    print(f"{'Runs/Month':<15} {'max_jobs':<12} {'Credits/Run':<15} {'Monthly Total':<15} {'Status'}")
    print("-" * 70)
    
    for runs in [2, 4, 8, 12, 16, 20]:
        for max_jobs in [10, 20, 30, 40, 50]:
            result = calculate_monthly_budget(runs, max_jobs, duplicate_rate=0.3)
            if result['monthly_total'] <= 1000:
                status = "✅"
                print(f"{runs:<15} {max_jobs:<12} {result['credits_per_run']:<15} {result['monthly_total']:<15} {status}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    print("-" * 70)
    print(f"  Current: 30 jobs @ 2 runs/week = ~336 credits/month ✅")
    print(f"  Optimal: Keep at 30 jobs for best results")
    print(f"  Maximum: Can go up to 50 jobs @ 2 runs/week (700 credits/month)")
    print(f"  Budget: You have room for ~3x more usage if needed")
    
    print(f"\n💰 COST BREAKDOWN:")
    print(f"  Free tier: 1000 credits/month")
    print(f"  Each search: ~1 credit")
    print(f"  Company enrichment: 2 searches (company info + tech stack)")
    print(f"  Cache hits: 0 credits (saves ~30% of calls)")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    print_credit_analysis()
