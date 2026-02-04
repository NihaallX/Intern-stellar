"""
LLM-based content parser using Groq.
Extracts structured flags from job descriptions.
DOES NOT score jobs - only extracts flags for rule-based scoring.
"""

import json
from typing import Optional
from groq import Groq

from src.models import Job, ExtractedFlags, CompanyType, ExperienceLevel
from src.utils.config import get_groq_api_key, load_settings


# System prompt for structured extraction
EXTRACTION_PROMPT = """You are a job posting parser. Extract structured information from job descriptions.

IMPORTANT RULES:
1. Output ONLY valid JSON, no explanations
2. Be conservative - only mark true if explicitly mentioned
3. For company_type, infer from context (funding, employee count, etc.)
4. For experience_level, look for "X years", "senior", "intern", "junior", etc.

Output this exact JSON structure:
{
    "has_llm": false,
    "has_rag": false,
    "has_agents": false,
    "has_langchain": false,
    "has_langgraph": false,
    "has_fastapi": false,
    "has_aws": false,
    "has_voice_ai": false,
    "has_backend": false,
    "company_type": "unknown",
    "is_ai_native": false,
    "experience_level": "unknown",
    "requires_phd": false,
    "requires_publications": false,
    "years_required": null,
    "research_heavy": false,
    "cv_heavy": false,
    "is_unpaid": false,
    "is_onsite_only": false
}

Field definitions:
- has_llm: Mentions LLM, GPT, Claude, large language model work
- has_rag: Mentions RAG, retrieval augmented generation, vector search
- has_agents: Mentions AI agents, agentic systems, autonomous agents
- has_langchain: Explicitly mentions LangChain
- has_langgraph: Explicitly mentions LangGraph
- has_fastapi: Mentions FastAPI
- has_aws: Mentions AWS, Lambda, S3, EC2, SageMaker, etc.
- has_voice_ai: Mentions voice AI, speech, conversational AI, TTS, STT
- has_backend: Mentions backend, API development, server-side
- company_type: "startup" (<200 employees, mentions funding), "midsize" (200-2000), "enterprise" (2000+), "consulting", "unknown"
- is_ai_native: Company's core product is AI/ML
- experience_level: "intern", "junior" (0-2 years), "mid" (3-5), "senior" (5+), "lead" (7+), "unknown"
- requires_phd: Explicitly requires PhD
- requires_publications: Requires research publications
- years_required: Number if specified, null otherwise
- research_heavy: Academic research focus, novel algorithms
- cv_heavy: Computer vision is primary focus
- is_unpaid: Unpaid, volunteer, equity-only
- is_onsite_only: Explicitly no remote option"""


def extract_flags_with_llm(job: Job) -> Optional[ExtractedFlags]:
    """
    Use Groq LLM to extract structured flags from a job.
    
    This is the ONLY place where LLM is used.
    The LLM does NOT score - it only extracts boolean/enum flags.
    """
    try:
        import os
        settings = load_settings()
        api_key = get_groq_api_key()
        
        # Remove any proxy environment variables that might interfere
        proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
        old_proxies = {}
        for var in proxy_vars:
            if var in os.environ:
                old_proxies[var] = os.environ[var]
                del os.environ[var]
        
        # Initialize Groq client with explicit API key
        client = Groq(api_key=api_key)
        
        # Restore proxy vars
        for var, value in old_proxies.items():
            os.environ[var] = value
        
        # Build the prompt
        user_prompt = f"""Parse this job posting:

Title: {job.title}
Company: {job.company}
Location: {job.location}
Remote: {job.remote}

Description:
{job.description[:3000]}

Requirements:
{', '.join(job.requirements) if job.requirements else 'Not specified'}

Output ONLY the JSON object with extracted flags."""

        response = client.chat.completions.create(
            model=settings.llm.get("model", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,  # Deterministic
            max_tokens=settings.llm.get("max_tokens", 1000),
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON response
        # Handle potential markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        data = json.loads(content)
        
        # Convert to ExtractedFlags
        flags = ExtractedFlags(
            has_llm=data.get("has_llm", False),
            has_rag=data.get("has_rag", False),
            has_agents=data.get("has_agents", False),
            has_langchain=data.get("has_langchain", False),
            has_langgraph=data.get("has_langgraph", False),
            has_fastapi=data.get("has_fastapi", False),
            has_aws=data.get("has_aws", False),
            has_voice_ai=data.get("has_voice_ai", False),
            has_backend=data.get("has_backend", False),
            company_type=CompanyType(data.get("company_type", "unknown")),
            is_ai_native=data.get("is_ai_native", False),
            experience_level=ExperienceLevel(data.get("experience_level", "unknown")),
            requires_phd=data.get("requires_phd", False),
            requires_publications=data.get("requires_publications", False),
            years_required=data.get("years_required"),
            research_heavy=data.get("research_heavy", False),
            cv_heavy=data.get("cv_heavy", False),
            is_unpaid=data.get("is_unpaid", False),
            is_onsite_only=data.get("is_onsite_only", False),
        )
        
        return flags
        
    except Exception as e:
        print(f"[LLM] Error extracting flags: {e}")
        return None


def extract_flags_fallback(job: Job) -> ExtractedFlags:
    """
    Fallback regex-based extraction when LLM fails.
    Less accurate but ensures pipeline continues.
    """
    text = f"{job.title} {job.description}".lower()
    
    flags = ExtractedFlags(
        has_llm="llm" in text or "gpt" in text or "large language model" in text,
        has_rag="rag" in text or "retrieval augmented" in text or "vector" in text,
        has_agents="agent" in text and "ai" in text,
        has_langchain="langchain" in text,
        has_langgraph="langgraph" in text,
        has_fastapi="fastapi" in text,
        has_aws="aws" in text or "lambda" in text or "s3" in text,
        has_voice_ai="voice" in text or "speech" in text or "tts" in text or "stt" in text,
        has_backend="backend" in text or "api" in text,
        is_ai_native="ai company" in text or "ai-first" in text,
        requires_phd="phd required" in text or "phd preferred" in text,
        requires_publications="publications required" in text,
        research_heavy="research scientist" in text or "novel algorithms" in text,
        cv_heavy="computer vision" in text and "primary" in text,
        is_unpaid="unpaid" in text or "volunteer" in text,
        is_onsite_only="on-site only" in text or "no remote" in text,
    )
    
    # Experience level detection (improved to catch more patterns)
    if "intern" in text:
        flags.experience_level = ExperienceLevel.INTERN
    elif "junior" in text or "0-2 years" in text or "entry level" in text or "entry-level" in text:
        flags.experience_level = ExperienceLevel.JUNIOR
    elif any(pattern in text for pattern in ["senior", "sr.", "staff", "principal", "lead", "5+ years", "5-7 years", "6+ years", "7+ years"]):
        flags.experience_level = ExperienceLevel.SENIOR
    elif any(pattern in text for pattern in ["3+ years", "3-5 years", "4+ years", "2-4 years", "mid-level", "mid level"]):
        flags.experience_level = ExperienceLevel.MID
    
    # Company type from text cues
    if "startup" in text or "seed" in text or "series a" in text:
        flags.company_type = CompanyType.STARTUP
    elif "enterprise" in text or "fortune 500" in text:
        flags.company_type = CompanyType.ENTERPRISE
    elif "consulting" in text or "services" in text:
        flags.company_type = CompanyType.CONSULTING
    
    return flags


def parse_job_with_llm(job: Job, use_fallback: bool = True) -> tuple[Job, bool]:
    """
    Parse a job and attach extracted flags.
    Uses LLM if available, falls back to regex if needed.
    
    Returns:
        tuple[Job, bool]: (parsed job, whether fallback was used)
    """
    # Try LLM extraction first
    flags = extract_flags_with_llm(job)
    used_fallback = False
    
    if flags is None and use_fallback:
        print(f"[LLM] Using fallback parser for: {job.title}")
        flags = extract_flags_fallback(job)
        used_fallback = True
    
    job.extracted_flags = flags
    return job, used_fallback


if __name__ == "__main__":
    # Test the parser
    test_job = Job(
        title="AI Engineer",
        company="AI Startup Inc",
        url="https://example.com/job",
        source="test",
        description="""
        We are looking for an AI Engineer to build RAG systems and LLM applications.
        You'll work with LangChain, FastAPI, and AWS Lambda.
        Requirements: 2+ years experience, Python, ML background.
        This is a remote-friendly startup with 50 employees.
        """
    )
    
    result = parse_job_with_llm(test_job)
    print(f"Extracted flags: {result.extracted_flags}")
