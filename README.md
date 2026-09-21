# AI Job Discovery System

A deterministic, read-only AI job discovery system that scrapes, scores, and emails relevant AI engineering roles.

## Features
- **Multi-source scraping**: Hacker News, X-Ray Search (Greenhouse, Lever, Ashby, Workable, etc.)
- **Public job boards**: Optional Greenhouse and Lever board scrapers driven by configurable company lists
- **Role categories**: Product Management, Solutions, Product Ops/Strategy, and Technical Program roles
- **Web-enriched company data**: Real-time verification via Tavily API (employee count, funding, AI-native status)
- **Deterministic scoring**: LLM for parsing only, all scoring is rule-based
- **Plain-text email reports**: Top 20 ranked jobs with explanations

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (or use .env file)
export GROQ_API_KEY="your_key"
export SMTP_EMAIL="your_email@gmail.com"
export SMTP_PASSWORD="your_app_password"
export TAVILY_API_KEY="your_tavily_key"  # Optional but recommended
export NIM_API_KEY="your_nim_api_key"    # Optional: NVIDIA NIM API key for date fallback + fit reasoning

# Run the discovery pipeline
python -m src.main
```

## Configuration
- `config/profile.yaml`: Candidate profile (skills, experience)
- `config/settings.yaml`: Pipeline settings (thresholds, sources, Tavily API)
- `config/role_categories.yaml`: Data-driven title lists and role-category priorities

Optional public-board sources can be enabled in `config/settings.yaml`:
```yaml
greenhouse:
  enabled: false
lever:
  enabled: false
```

## New: Company Enrichment
Enable web search for verified company data (see [TAVILY_INTEGRATION.md](TAVILY_INTEGRATION.md)):
```yaml
# config/settings.yaml
tavily:
  enabled: true
  enrich_companies: true
  max_enrichment_jobs: 4  # Keep enrichment capped unless you raise the Tavily budget
```

## Architecture
```
src/
├── main.py          # Entry point
├── models.py        # Job & Config models
├── scrapers/        # Data acquisition
├── scoring/         # Deterministic scoring
├── emailer.py       # Report generation
└── utils/           # Helpers
```

## Scheduling
GitHub Actions runs this twice weekly (Mon & Thu at 9:00 UTC).

## Secrets to add to GitHub Actions
Add the following repository secrets in your GitHub repo settings if you want CI runs to call external services:
- `GROQ_API_KEY`
- `GROQ_API_KEY_2` (optional backup)
- `TAVILY_API_KEY`
- `NIM_API_KEY` (for NVIDIA NIM fit reasoning and date fallback)
