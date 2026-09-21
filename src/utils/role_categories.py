"""Data-driven role-category matching for pre-filtering and scoring."""

from functools import lru_cache
from pathlib import Path
import re
import yaml


@lru_cache(maxsize=1)
def load_role_categories() -> dict:
    path = Path(__file__).parents[2] / "config" / "role_categories.yaml"
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def match_role_category(title: str) -> str | None:
    normalized = _normalize(title)
    if not normalized:
        return None
    categories = load_role_categories()
    # Prefer the most specific matching title, then preserve YAML order.
    matches = []
    for category, config in categories.items():
        for target in config.get("titles", []):
            candidate = _normalize(target)
            if candidate and (candidate in normalized or normalized in candidate):
                matches.append((len(candidate), category))
    return max(matches)[1] if matches else None
