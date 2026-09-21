# Tavily Web Search Integration — Implementation Summary

## Current implementation

The project includes optional Tavily-powered company enrichment and Tavily-backed job sources.

### Company enrichment

When enabled, the pipeline runs company enrichment at Step 4.5, after hard filtering and before scoring. Enrichment can provide employee count, funding stage, AI-company status, recent result titles, a company description, and detected technology keywords.

The data is stored on `Job.company_enrichment` using the `CompanyEnrichment` model in `src/models.py`.

### Configuration

The current defaults in `config/settings.yaml` are:

```yaml
tavily:
  api_key: ""              # Prefer TAVILY_API_KEY in .env/environment
  enabled: false           # Enrichment is disabled by default
  enrich_companies: true
  max_enrichment_jobs: 4
```

To enable company enrichment, set `TAVILY_API_KEY` and change `tavily.enabled` to `true`. The key loader checks the environment first and then the YAML setting as a fallback.

The repository also uses Tavily for optional job-source scrapers. Those sources have separate configuration sections, such as `tavily_jobs`, `linkedin`, `builtin`, and `simplify`.

### Scoring behavior

`src/scoring/engine.py` uses enrichment when available. Company signal is capped at 10 points:

- Fewer than 200 employees: 10 points
- 200–1,999 employees: 7 points
- 2,000 or more employees: 4 points
- AI-company indicator: up to +3 points
- Seed, Series A, or Series B funding: up to +1 point
- Glassdoor rating of 4.0 or higher: up to +1 point

If enrichment is unavailable, scoring falls back to the LLM-extracted company type.

### Email reporting

When enrichment is present, `src/emailer.py` includes available employee count, funding stage, AI-company status, and Glassdoor rating in the plain-text report. The score breakdown also includes the company signal.

## Operational details

- Enrichment is limited to the first `max_enrichment_jobs` filtered jobs; the current default is 4.
- Each company may trigger up to two Tavily searches: company information and technology-stack information.
- A 1.5-second delay is applied between Tavily API calls.
- Duplicate company lookups use an in-memory cache during the current pipeline run.
- The cache is cleared at the start of each pipeline run; there is no persistent or seven-day cache.
- Tavily failures return empty enrichment data and allow the pipeline to continue.
- Pipeline logs report progress and the number of API calls made.

## Relevant files

| File | Responsibility |
|---|---|
| `requirements.txt` | Includes `tavily-python>=0.3.0` |
| `config/settings.yaml` | Tavily and scraper configuration |
| `src/models.py` | `CompanyEnrichment` and job fields |
| `src/utils/config.py` | Tavily API-key loading |
| `src/utils/web_search.py` | Client, parsing, rate limiting, and cache |
| `src/main.py` | Step 4.5 enrichment integration |
| `src/scoring/engine.py` | Enrichment-aware company scoring |
| `src/emailer.py` | Enrichment display in reports |
| `README.md` | Setup and configuration guidance |
| `TAVILY_INTEGRATION.md` | Detailed integration notes |

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Set the key in `.env` or the environment:

```text
TAVILY_API_KEY=your_tavily_key
```

Enable enrichment in `config/settings.yaml`, then run:

```bash
python -m src.main
```

For an email preview without sending:

```bash
python -m src.main --dry-run
```

To disable enrichment, leave `tavily.enabled` set to `false`.

## Verification status

The integration is represented in the source code and documentation. No `test_tavily.py` or `test_integration.py` files are currently present in the repository, so historical test-result claims are not included here.

The implementation is best-effort and optional: it can improve ranking when Tavily is enabled and available, while the core pipeline continues using fallback data when it is disabled or unavailable.
