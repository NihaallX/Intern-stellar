"""
Quick integration test - Run a mini pipeline to verify all components work.
"""

from src.models import Job, ExtractedFlags, ExperienceLevel, CompanyType
from src.utils.web_search import search_company_info
from src.scoring.engine import score_job


def test_full_integration():
    """Test complete flow: Job -> Enrichment -> Scoring"""
    
    print("=" * 60)
    print("FULL INTEGRATION TEST")
    print("=" * 60)
    
    # Create a sample job
    job = Job(
        title="AI Engineer Intern",
        company="Anthropic",
        url="https://jobs.lever.co/anthropic/example",
        source="test",
        location="San Francisco",
        remote=True,
        description="Build advanced AI systems with LLMs, RAG, and agents. Use Python, FastAPI, AWS.",
        requirements=["Python", "LLM experience", "RAG systems"]
    )
    
    # Add extracted flags (simulating LLM parse)
    job.extracted_flags = ExtractedFlags(
        has_llm=True,
        has_rag=True,
        has_agents=True,
        has_fastapi=True,
        has_aws=True,
        experience_level=ExperienceLevel.INTERN,
        company_type=CompanyType.STARTUP,
        is_ai_native=True
    )
    
    print(f"\n[1] Created test job: {job.title} at {job.company}")
    
    # Enrich company
    print(f"\n[2] Enriching company data...")
    try:
        enrichment = search_company_info(job.company)
        job.company_enrichment = enrichment
        
        print(f"    Employees: {enrichment.employee_count or 'Unknown'}")
        print(f"    Funding: {enrichment.funding_stage or 'Unknown'}")
        print(f"    AI company: {enrichment.is_ai_company}")
        print(f"    ✓ Enrichment successful")
    except Exception as e:
        print(f"    ✗ Enrichment failed: {e}")
    
    # Score job
    print(f"\n[3] Scoring job...")
    scored_job = score_job(job)
    
    print(f"    Total Score: {scored_job.score:.1f}/100")
    if scored_job.score_breakdown:
        bd = scored_job.score_breakdown
        print(f"    Breakdown:")
        print(f"      - Semantic similarity: {bd.similarity:.1f}/40")
        print(f"      - Skill match: {bd.skill_match:.1f}/25")
        print(f"      - Experience fit: {bd.experience_fit:.1f}/15")
        print(f"      - Company signal: {bd.company_signal:.1f}/10")
        print(f"      - Adjustments: {bd.penalties:+.1f}/10")
    
    print(f"\n    Why matched:")
    for reason in scored_job.why_matched:
        print(f"      - {reason}")
    
    # Success criteria
    print(f"\n[4] Validation:")
    checks = []
    
    if scored_job.score > 0:
        checks.append("✓ Job scored successfully")
    else:
        checks.append("✗ Scoring failed")
    
    if scored_job.company_enrichment:
        checks.append("✓ Company enrichment applied")
    else:
        checks.append("✗ No company enrichment")
    
    if scored_job.score_breakdown and scored_job.score_breakdown.company_signal > 0:
        checks.append("✓ Company scoring working")
    else:
        checks.append("✗ Company scoring issue")
    
    for check in checks:
        print(f"    {check}")
    
    print("\n" + "=" * 60)
    
    if all("✓" in check for check in checks):
        print("SUCCESS: All checks passed!")
    else:
        print("PARTIAL: Some checks failed")
    
    print("=" * 60)


if __name__ == "__main__":
    test_full_integration()
