# AI Job Discovery System

A deterministic, read-only AI job discovery system that scrapes, scores, and emails relevant AI engineering roles.

## Features
- **Multi-source scraping**: Hacker News, X-Ray Search (Greenhouse, Lever, Ashby, Workable, etc.)
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

# Run the discovery pipeline
python -m src.main
```

## Configuration
- `config/profile.yaml`: Candidate profile (skills, experience)
- `config/settings.yaml`: Pipeline settings (thresholds, sources)

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
