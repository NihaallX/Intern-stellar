"""
Data models for the AI Job Discovery System.
All models are Pydantic for validation and serialization.
"""

from typing import Optional
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class CompanyType(str, Enum):
    """Company classification for scoring."""
    STARTUP = "startup"          # 0-200 employees, AI-native
    MIDSIZE = "midsize"          # 200-2000 employees
    ENTERPRISE = "enterprise"    # 2000+ employees
    CONSULTING = "consulting"    # Services/consulting
    UNKNOWN = "unknown"


class ExperienceLevel(str, Enum):
    """Required experience level."""
    INTERN = "intern"
    JUNIOR = "junior"           # 0-2 years
    MID = "mid"                 # 3-5 years
    SENIOR = "senior"           # 5+ years
    LEAD = "lead"               # 7+ years
    UNKNOWN = "unknown"


class Job(BaseModel):
    """
    Normalized job object.
    This is the canonical structure for all jobs regardless of source.
    """
    # Core fields (required)
    title: str
    company: str
    url: str
    source: str  # e.g., "hackernews", "greenhouse", "lever"
    
    # Location
    location: str = "Unknown"
    remote: bool = False
    hybrid: bool = False
    
    # Compensation
    paid: bool = True  # Assume paid unless explicitly unpaid
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "USD"
    
    # Description
    description: str = ""
    requirements: list[str] = Field(default_factory=list)
    
    # LLM-extracted flags (populated by parser)
    extracted_flags: Optional["ExtractedFlags"] = None
    
    # Web-enriched company data (populated by web search)
    company_enrichment: Optional["CompanyEnrichment"] = None
    
    # Scoring results (populated by scoring engine)
    score: Optional[float] = None
    score_breakdown: Optional["ScoreBreakdown"] = None
    why_matched: list[str] = Field(default_factory=list)
    
    # Deduplication
    job_id: Optional[str] = None  # hash of url or unique identifier
    
    def generate_job_id(self) -> str:
        """Generate a unique ID for deduplication."""
        import hashlib
        content = f"{self.url}|{self.title}|{self.company}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


class CompanyEnrichment(BaseModel):
    """Company information enriched from web search."""
    employee_count: Optional[int] = None
    funding_stage: Optional[str] = None  # seed, series A, B, C, etc.
    is_ai_company: bool = False
    recent_news: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    company_description: Optional[str] = None
    glassdoor_rating: Optional[float] = None
    verified_remote_policy: Optional[str] = None  # remote-first, hybrid, onsite


class ExtractedFlags(BaseModel):
    """
    Structured flags extracted by LLM from job description.
    These are used for deterministic rule-based scoring.
    The LLM ONLY outputs these flags, it does NOT score.
    """
    # Skill flags
    has_llm: bool = False
    has_rag: bool = False
    has_agents: bool = False
    has_langchain: bool = False
    has_langgraph: bool = False
    has_fastapi: bool = False
    has_aws: bool = False
    has_voice_ai: bool = False
    has_backend: bool = False
    
    # Company flags
    company_type: CompanyType = CompanyType.UNKNOWN
    is_ai_native: bool = False
    
    # Experience flags
    experience_level: ExperienceLevel = ExperienceLevel.UNKNOWN
    requires_phd: bool = False
    requires_publications: bool = False
    years_required: Optional[int] = None
    
    # Role flags
    research_heavy: bool = False
    cv_heavy: bool = False  # Computer Vision heavy
    is_unpaid: bool = False
    is_onsite_only: bool = False


class ScoreBreakdown(BaseModel):
    """
    Detailed breakdown of how a job was scored.
    Used for explainability in the email output.
    """
    similarity: float = 0.0      # 0-40 points
    skill_match: float = 0.0     # 0-25 points
    experience_fit: float = 0.0  # 0-15 points
    company_signal: float = 0.0  # 0-10 points
    penalties: float = 0.0       # -10 to +10 points
    
    @property
    def total(self) -> float:
        return (
            self.similarity +
            self.skill_match +
            self.experience_fit +
            self.company_signal +
            self.penalties
        )


class CandidateProfile(BaseModel):
    """
    Loaded from config/profile.yaml.
    Represents the candidate's skills and preferences.
    """
    name: str
    summary: str
    priority_skills: list[str] = Field(default_factory=list)
    secondary_skills: list[str] = Field(default_factory=list)
    deprioritize: list[str] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)
    experience_level: str = "intern_or_junior"
    location: dict = Field(default_factory=dict)


class PipelineSettings(BaseModel):
    """
    Loaded from config/settings.yaml.
    Controls pipeline behavior.
    """
    scoring: dict = Field(default_factory=dict)
    weights: dict = Field(default_factory=dict)
    xray: dict = Field(default_factory=dict)
    hackernews: dict = Field(default_factory=dict)
    ycombinator: dict = Field(default_factory=dict)
    remotive: dict = Field(default_factory=dict)
    wellfound: dict = Field(default_factory=dict)
    huggingface: dict = Field(default_factory=dict)
    tavily_jobs: dict = Field(default_factory=dict)
    adzuna: dict = Field(default_factory=dict)
    indeed: dict = Field(default_factory=dict)
    weworkremotely: dict = Field(default_factory=dict)
    remoteok: dict = Field(default_factory=dict)
    himalayas: dict = Field(default_factory=dict)
    justremote: dict = Field(default_factory=dict)
    linkedin: dict = Field(default_factory=dict)
    builtin: dict = Field(default_factory=dict)
    simplify: dict = Field(default_factory=dict)
    tavily: dict = Field(default_factory=dict)
    email: dict = Field(default_factory=dict)
    llm: dict = Field(default_factory=dict)
    dedup: dict = Field(default_factory=dict)
