"""
NIM client wrapper for two auxiliary agents:
 - infer_posted_date(job): Infer a posted date from description/title when parse failed
 - generate_fit_reason(job, profile): Produce a concise 1-2 sentence fit reason

Implements real HTTP integration with NVIDIA NIM (OpenAI-compatible chat endpoint).
If `NIM_API_KEY` is not present or a network call fails, falls back to local heuristics.
Responses and model lists are cached under `data/` to avoid repeated network calls.
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# Read NIM key at import time and expose for checks
NIM_API_KEY = os.environ.get('NIM_API_KEY')
if NIM_API_KEY:
    logger.info('NIM API key present in environment')
else:
    logger.info('NIM API key NOT present in environment')

# Cache paths
CACHE_DIR = os.environ.get('NIM_CACHE_DIR', 'data')
FIT_CACHE = os.path.join(CACHE_DIR, 'nim_fit_reason_cache.json')
DATE_CACHE = os.path.join(CACHE_DIR, 'nim_date_cache.json')
NIM_MODELS_CACHE = os.path.join(CACHE_DIR, 'nim_models.json')
NIM_RAW_RESP = os.path.join(CACHE_DIR, 'nim_last_raw.json')

# NIM endpoints (OpenAI-compatible)
NIM_BASE = 'https://integrate.api.nvidia.com/v1'
NIM_MODELS_URL = f"{NIM_BASE}/models"
NIM_CHAT_URL = f"{NIM_BASE}/chat/completions"

# HTTP settings
NIM_TIMEOUT = 8.0


def _ensure_cache() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    for p in (FIT_CACHE, DATE_CACHE, NIM_MODELS_CACHE, NIM_RAW_RESP):
        if not os.path.exists(p):
            try:
                with open(p, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
            except Exception:
                # best-effort
                pass


def _load_cache(path: str) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(path: str, data: dict) -> None:
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning('Failed to write cache %s: %s', path, e)


def _get_nim_models(nim_key: str | None = None) -> list:
    """List available models for the provided NIM key; cache result on disk."""
    _ensure_cache()
    cached = _load_cache(NIM_MODELS_CACHE).get('models')
    if cached:
        return cached
    # prefer provided nim_key, else fall back to env-sourced NIM_API_KEY
    nim_key = nim_key or NIM_API_KEY
    headers = {}
    if nim_key:
        headers["Authorization"] = f"Bearer {nim_key}"
    try:
        with httpx.Client(timeout=NIM_TIMEOUT) as client:
            resp = client.get(NIM_MODELS_URL, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            models = []
            if isinstance(data, dict) and 'data' in data:
                for it in data['data']:
                    mid = it.get('id') or it.get('name')
                    if mid:
                        models.append(mid)
            elif isinstance(data, list):
                for it in data:
                    mid = it.get('id') or it.get('name')
                    if mid:
                        models.append(mid)
            else:
                # fallback: try to parse keys
                for k in data.keys():
                    models.append(k)

            _save_cache(NIM_MODELS_CACHE, {'models': models})
            return models
    except Exception as e:
        logger.warning('Failed to list NIM models: %s', e)
        return []


def _choose_nim_model(models: list) -> str:
    """Choose a reasonable instruct-style model from the list or fallback."""
    if not models:
        return 'llama-3.3-instruct'
    for m in models:
        lm = m.lower()
        if 'instruct' in lm or 'llama' in lm or '3.3' in lm or '3.1' in lm:
            return m
    return models[0]


def _call_nim_chat(body: dict, nim_key: str) -> dict:
    # Allow caller to pass nim_key or use env-provided key
    nim_key = nim_key or NIM_API_KEY
    headers = {"Content-Type": "application/json"}
    if nim_key:
        headers["Authorization"] = f"Bearer {nim_key}"

    # Log redacted headers for debugging (do not log the actual key)
    try:
        redacted = dict(headers)
        if 'Authorization' in redacted:
            redacted['Authorization'] = 'Bearer REDACTED'
        logger.info('NIM request headers: %s', redacted)
    except Exception:
        pass

    with httpx.Client(timeout=NIM_TIMEOUT) as client:
        try:
            resp = client.post(NIM_CHAT_URL, json=body, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            # If endpoint not found (404), try the alternative completions endpoint
            if e.response.status_code == 404:
                try:
                    alt_url = NIM_BASE + '/completions'
                    resp2 = client.post(alt_url, json=body, headers=headers)
                    resp2.raise_for_status()
                    return resp2.json()
                except Exception:
                    raise
            raise


def _extract_content_from_nim(raw: dict) -> Optional[str]:
    try:
        choices = raw.get('choices') or []
        if not choices:
            return None
        first = choices[0]
        if 'message' in first and isinstance(first['message'], dict):
            return first['message'].get('content')
        return first.get('text') or None
    except Exception:
        return None


def infer_posted_date(job_title: str, job_description: str, job_url: str) -> Optional[datetime]:
    """Try NIM first to infer a posted date, fall back to heuristics and cache."""
    _ensure_cache()
    cache = _load_cache(DATE_CACHE)
    key = job_url or (job_title + '|' + (job_description or '')[:100])
    if key in cache:
        val = cache[key]
        try:
            return datetime.fromisoformat(val) if val else None
        except Exception:
            return None

    nim_key = os.environ.get('NIM_API_KEY')
    if nim_key:
        try:
            models = _get_nim_models(nim_key)
            model = _choose_nim_model(models)
            prompt = (
                "You are an assistant that extracts the posted or expiry date from a job posting.\n"
                "Return only a JSON object with the ISO date in field 'posted_date' (YYYY-MM-DD) or null if not present.\n"
                "Example: {\"posted_date\": \"2026-07-15\"} or {\"posted_date\": null}\n\n"
                f"Job title: {job_title}\nJob description: {job_description}\nJob URL: {job_url}\n"
            )
            body = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You extract dates from job postings as ISO dates."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.0,
                "max_tokens": 64,
            }

            raw = _call_nim_chat(body, nim_key)
            try:
                _save_cache(NIM_RAW_RESP, {"date": raw})
            except Exception:
                pass

            content = _extract_content_from_nim(raw)
            if content:
                try:
                    parsed = json.loads(content)
                    pd = parsed.get('posted_date')
                    if pd:
                        d = datetime.fromisoformat(pd)
                        cache[key] = d.isoformat()
                        _save_cache(DATE_CACHE, cache)
                        return d
                except Exception:
                    logger.debug('NIM date content not JSON: %s', content)
        except Exception as e:
            logger.warning('NIM date infer failed: %s', e)

    # Local heuristic fallback
    text = f"{job_title or ''} {job_description or ''}".lower()
    import re
    now = datetime.now()
    m = re.search(r'posted\s+(\d+)\s+days?\s+ago', text)
    if m:
        d = now - timedelta(days=int(m.group(1)))
        cache[key] = d.isoformat()
        _save_cache(DATE_CACHE, cache)
        return d
    m = re.search(r'posted\s+(\d+)\s+weeks?\s+ago', text)
    if m:
        d = now - timedelta(weeks=int(m.group(1)))
        cache[key] = d.isoformat()
        _save_cache(DATE_CACHE, cache)
        return d
    m = re.search(r'(20\d{2})-(\d{2})-(\d{2})', text)
    if m:
        try:
            d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            cache[key] = d.isoformat()
            _save_cache(DATE_CACHE, cache)
            return d
        except Exception:
            pass

    cache[key] = None
    _save_cache(DATE_CACHE, cache)
    return None


def generate_fit_reason(job_title: str, job_description: str, profile_summary: str, job_url: str) -> Tuple[str, str]:
    """Generate concise 1-2 sentence fit reason using NIM if available, else heuristic."""
    _ensure_cache()
    cache = _load_cache(FIT_CACHE)
    key = job_url or (job_title + '|' + (job_description or '')[:100])
    if key in cache and cache[key]:
        return cache[key], 'cache'

    nim_key = os.environ.get('NIM_API_KEY')
    if nim_key:
        try:
            models = _get_nim_models(nim_key)
            model = _choose_nim_model(models)
            prompt = (
                "You are an assistant that reads a job posting and a candidate profile, "
                "and writes a concise 1-2 sentence reason why the candidate is a fit. "
                "Be specific and mention concrete signals from the job posting.\n\n"
                f"Candidate profile summary: {profile_summary}\n\n"
                f"Job title: {job_title}\nJob description: {job_description}\nJob URL: {job_url}\n\n"
                "Return only the plain text reason (no JSON or explanation)."
            )
            body = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You generate a concise fit reason for a candidate given a job posting."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 128,
            }

            raw = _call_nim_chat(body, nim_key)
            try:
                _save_cache(NIM_RAW_RESP, {'fit': raw})
            except Exception:
                pass

            content = _extract_content_from_nim(raw)
            if content:
                reason = content.strip()
                cache[key] = reason
                _save_cache(FIT_CACHE, cache)
                return reason, 'nim'
        except Exception as e:
            logger.warning('NIM fit generation failed: %s', e)

    # Heuristic fallback
    text = f"{job_title or ''} {job_description or ''}".lower()
    reasons = []
    if any(k in text for k in ["ivr", "voice", "speech", "call center", "contact center"]):
        reasons.append("matches your healthcare IVR + voice agent work")
    if any(k in text for k in ["prd", "roadmap", "feature", "stakeholder", "user journey", "product"]):
        reasons.append("matches your PRD authoring and sprint alignment background")
    if any(k in text for k in ["0-to-1", "0 to 1", "founding", "mvp", "launch"]):
        reasons.append("matches your 0-to-1 shipping experience")
    if any(k in text for k in ["llm", "rag", "langgraph", "agents", "react"]):
        reasons.append("matches your LLM, RAG, LangGraph, and ReAct agent experience")

    reason = reasons[0] if reasons else "General fit with your AI Product Builder profile"
    cache[key] = reason
    _save_cache(FIT_CACHE, cache)
    return reason, 'heuristic'
