"""
Deterministic, rule-based scoring engine.
All scoring is done by code - no LLM scoring.
"""

from typing import Optional
from sentence_transformers import SentenceTransformer
import numpy as np

from src.models import Job, ExtractedFlags, ScoreBreakdown, CompanyType, ExperienceLevel
from src.utils.config import get_candidate_summary, load_settings


# Lazy-loaded embedding model
_embedding_model: Optional[SentenceTransformer] = None
_candidate_embedding: Optional[np.ndarray] = None


def get_embedding_model() -> SentenceTransformer:
    """Get or initialize the embedding model."""
    global _embedding_model
    if _embedding_model is None:
        print("[SCORING] Loading embedding model...")
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model


def get_candidate_embedding() -> np.ndarray:
    """Get or compute the candidate profile embedding."""
    global _candidate_embedding
    if _candidate_embedding is None:
        model = get_embedding_model()
        summary = get_candidate_summary()
        _candidate_embedding = model.encode(summary)
    return _candidate_embedding


def compute_semantic_similarity(job: Job) -> float:
    """
    Compute semantic similarity between job and candidate profile.
    Returns score in range 0-40.
    """
    model = get_embedding_model()
    candidate_emb = get_candidate_embedding()
    
    # Create job embedding from title + description
    job_text = f"{job.title} {job.description[:2000]}"
    job_emb = model.encode(job_text)
    
    # Cosine similarity
    similarity = np.dot(candidate_emb, job_emb) / (
        np.linalg.norm(candidate_emb) * np.linalg.norm(job_emb)
    )
    
    # Scale from [-1, 1] to [0, 40]
    # Typically similarities are positive, so we map [0, 1] -> [0, 40]
    scaled_score = max(0, similarity) * 40
    
    return round(scaled_score, 2)


def compute_skill_match(flags: ExtractedFlags) -> tuple[float, list[str]]:
    """
    Compute skill match score based on extracted flags.
    Returns (score, reasons) where score is in range 0-25.
    
    This is DETERMINISTIC - points are assigned by rules.
    """
    score = 0.0
    reasons = []
    
    # Priority skills (high points)
    if flags.has_llm:
        score += 5
        reasons.append("LLM experience")
    
    if flags.has_rag:
        score += 5
        reasons.append("RAG systems")
    
    if flags.has_agents:
        score += 4
        reasons.append("Agentic workflows")
    
    if flags.has_langchain or flags.has_langgraph:
        score += 3
        reasons.append("LangChain/LangGraph")
    
    if flags.has_fastapi:
        score += 3
        reasons.append("FastAPI expertise")
    
    if flags.has_aws:
        score += 3
        reasons.append("AWS infrastructure")
    
    if flags.has_voice_ai:
        score += 4
        reasons.append("Voice AI experience")
    
    if flags.has_backend:
        score += 2
        reasons.append("Backend systems")
    
    # Cap at 25
    return min(score, 25), reasons


def compute_experience_fit(flags: ExtractedFlags) -> tuple[float, list[str]]:
    """
    Compute experience fit score.
    Returns (score, reasons) where score is in range 0-15.
    
    Candidate is intern/junior level.
    """
    score = 0.0
    reasons = []
    
    if flags.experience_level == ExperienceLevel.INTERN:
        score = 15
        reasons.append("Intern-level role (perfect fit)")
    elif flags.experience_level == ExperienceLevel.JUNIOR:
        score = 15
        reasons.append("Junior-level role (perfect fit)")
    elif flags.experience_level == ExperienceLevel.UNKNOWN:
        score = 10
        reasons.append("Experience level not specified")
    elif flags.experience_level == ExperienceLevel.MID:
        score = 5
        reasons.append("Mid-level role (stretch)")
    else:  # SENIOR, LEAD
        score = 0
        reasons.append("Senior role (mismatch)")
    
    # Check years required
    if flags.years_required is not None:
        if flags.years_required <= 2:
            score = max(score, 12)
        elif flags.years_required <= 4:
            score = min(score, 7)
        else:
            score = min(score, 2)
    
    return score, reasons


def compute_company_signal(flags: ExtractedFlags) -> tuple[float, list[str]]:
    """
    Compute company signal score.
    Returns (score, reasons) where score is in range 0-10.
    """
    score = 0.0
    reasons = []
    
    if flags.company_type == CompanyType.STARTUP:
        score = 10
        reasons.append("AI-native startup")
    elif flags.company_type == CompanyType.MIDSIZE:
        score = 7
        reasons.append("Product-focused mid-size company")
    elif flags.company_type == CompanyType.ENTERPRISE:
        score = 4
        reasons.append("Enterprise company")
    elif flags.company_type == CompanyType.CONSULTING:
        score = 2
        reasons.append("Consulting/services")
    else:
        score = 5
        reasons.append("Unknown company type")
    
    # Bonus for AI-native
    if flags.is_ai_native:
        score = min(score + 2, 10)
        if "AI-native" not in " ".join(reasons):
            reasons.append("AI-native company")
    
    return score, reasons


def compute_penalties(job: Job, flags: ExtractedFlags) -> tuple[float, list[str]]:
    """
    Compute penalties and bonuses.
    Returns (adjustment, reasons) where adjustment is in range -10 to +10.
    """
    adjustment = 0.0
    reasons = []
    
    # Penalties
    if flags.research_heavy:
        adjustment -= 5
        reasons.append("Research-heavy focus")
    
    if flags.cv_heavy:
        adjustment -= 4
        reasons.append("CV-heavy role")
    
    if flags.requires_phd:
        adjustment -= 8
        reasons.append("PhD required")
    
    if flags.requires_publications:
        adjustment -= 5
        reasons.append("Publications required")
    
    if flags.is_onsite_only:
        adjustment -= 3
        reasons.append("On-site only")
    
    # Bonuses
    if job.remote:
        adjustment += 3
        reasons.append("Remote-friendly")
    
    # Clamp to range
    adjustment = max(-10, min(10, adjustment))
    
    return adjustment, reasons


def score_job(job: Job) -> Job:
    """
    Score a job using the deterministic rule-based system.
    
    Pipeline:
    1. Semantic similarity (0-40)
    2. Skill match based on flags (0-25)
    3. Experience fit (0-15)
    4. Company signal (0-10)
    5. Penalties/bonuses (-10 to +10)
    
    Total: 0-100
    """
    if job.extracted_flags is None:
        print(f"[SCORING] Warning: No flags for job {job.title}, using defaults")
        job.extracted_flags = ExtractedFlags()
    
    flags = job.extracted_flags
    why_matched = []
    
    # 1. Semantic similarity
    similarity_score = compute_semantic_similarity(job)
    
    # 2. Skill match
    skill_score, skill_reasons = compute_skill_match(flags)
    why_matched.extend(skill_reasons[:2])  # Top 2 reasons
    
    # 3. Experience fit
    exp_score, exp_reasons = compute_experience_fit(flags)
    if exp_score >= 10:
        why_matched.extend(exp_reasons[:1])
    
    # 4. Company signal
    company_score, company_reasons = compute_company_signal(flags)
    if company_score >= 7:
        why_matched.extend(company_reasons[:1])
    
    # 5. Penalties
    penalty_score, penalty_reasons = compute_penalties(job, flags)
    
    # Build breakdown
    breakdown = ScoreBreakdown(
        similarity=similarity_score,
        skill_match=skill_score,
        experience_fit=exp_score,
        company_signal=company_score,
        penalties=penalty_score,
    )
    
    job.score_breakdown = breakdown
    job.score = breakdown.total
    job.why_matched = why_matched[:3]  # Limit to 3 reasons
    
    return job


def apply_hard_filters(job: Job) -> bool:
    """
    Apply hard filters to discard jobs early.
    Returns True if job should be KEPT, False if discarded.
    """
    flags = job.extracted_flags
    
    if flags is None:
        return True  # Keep if no flags (will be parsed later)
    
    # Hard discard unpaid
    if flags.is_unpaid:
        print(f"[FILTER] Discarding unpaid: {job.title}")
        return False
    
    # Hard discard PhD-required (unless explicitly waived)
    if flags.requires_phd:
        print(f"[FILTER] Discarding PhD-required: {job.title}")
        return False
    
    # Hard discard senior roles
    if flags.experience_level in [ExperienceLevel.SENIOR, ExperienceLevel.LEAD]:
        print(f"[FILTER] Discarding senior role: {job.title}")
        return False
    
    return True


def rank_jobs(jobs: list[Job], min_score: float = 60, top_n: int = 20) -> list[Job]:
    """
    Rank jobs by score and return top N above threshold.
    """
    # Filter by minimum score
    qualified = [j for j in jobs if j.score is not None and j.score >= min_score]
    
    # Sort by score descending
    qualified.sort(key=lambda j: j.score or 0, reverse=True)
    
    # Return top N
    return qualified[:top_n]


if __name__ == "__main__":
    # Test the scoring engine
    from src.models import ExtractedFlags
    
    test_job = Job(
        title="AI Engineer",
        company="AI Startup",
        url="https://example.com",
        source="test",
        description="Build RAG systems with LangChain and FastAPI on AWS.",
    )
    
    test_job.extracted_flags = ExtractedFlags(
        has_llm=True,
        has_rag=True,
        has_langchain=True,
        has_fastapi=True,
        has_aws=True,
        company_type=CompanyType.STARTUP,
        is_ai_native=True,
        experience_level=ExperienceLevel.JUNIOR,
    )
    
    scored = score_job(test_job)
    print(f"Score: {scored.score}")
    print(f"Breakdown: {scored.score_breakdown}")
    print(f"Why matched: {scored.why_matched}")
