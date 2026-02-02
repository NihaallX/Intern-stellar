"""
Configuration loading utilities.
"""

import os
from pathlib import Path
from typing import Optional
import yaml

from dotenv import load_dotenv

from src.models import CandidateProfile, PipelineSettings


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def load_env() -> None:
    """Load environment variables from .env file."""
    env_path = get_project_root() / ".env"
    load_dotenv(env_path)


def get_groq_api_key() -> str:
    """Get Groq API key from environment."""
    load_env()
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY not found in environment")
    return key


def get_tavily_api_key() -> str:
    """Get Tavily API key from environment or config."""
    load_env()
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        # Fallback to hardcoded key from settings
        settings = load_settings()
        key = settings.tavily.get("api_key") if hasattr(settings, 'tavily') and isinstance(settings.tavily, dict) else None
    if not key:
        raise ValueError("TAVILY_API_KEY not found in environment or settings")
    return key


def get_smtp_credentials() -> tuple[str, str]:
    """Get SMTP email and password from environment."""
    load_env()
    email = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_PASSWORD")
    if not email or not password:
        raise ValueError("SMTP credentials not found in environment")
    return email, password


def load_profile() -> CandidateProfile:
    """Load candidate profile from config/profile.yaml."""
    config_path = get_project_root() / "config" / "profile.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return CandidateProfile(**data)


def load_settings() -> PipelineSettings:
    """Load pipeline settings from config/settings.yaml."""
    config_path = get_project_root() / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return PipelineSettings(**data)


def get_candidate_summary() -> str:
    """
    Get the candidate summary text for embedding.
    This is the canonical representation used for semantic similarity.
    """
    profile = load_profile()
    
    # Build a rich text representation
    parts = [
        profile.summary,
        f"Core skills: {', '.join(profile.priority_skills)}",
        f"Secondary skills: {', '.join(profile.secondary_skills)}",
        f"Target roles: {', '.join(profile.target_roles)}",
    ]
    
    return " ".join(parts)
