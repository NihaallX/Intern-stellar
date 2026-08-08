import csv
from pathlib import Path
from src.models import Job
from src.scrapers.llm_parser import parse_job_with_llm
from src.scoring.engine import score_job


def load_csv(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def build_job_from_row(row):
    job = Job(
        title=row.get('title') or '',
        company=row.get('company') or '',
        url=row.get('url') or '',
        source=row.get('source') or '',
        description=row.get('description_preview') or '',
    )
    return job


def main():
    csv_path = Path('data') / f"jobs_{__import__('datetime').datetime.now().strftime('%Y-%m-%d')}.csv"
    if not csv_path.exists():
        # fallback to existing file
        csv_path = Path('data') / 'jobs_2026-08-06.csv'

    rows = load_csv(csv_path)
    top10 = rows[:10]

    print(f"Loaded {len(rows)} rows from {csv_path}")

    for i, row in enumerate(top10, 1):
        job = build_job_from_row(row)
        # parse flags using fallback to avoid external LLM
        job, used_fallback = parse_job_with_llm(job, use_fallback=True)
        job = score_job(job)

        bd = job.score_breakdown
        print(f"#{i}: {job.title}\n  role_tier_bonus: {bd.role_tier_bonus}\n  seniority_fit_bonus: {bd.seniority_fit_bonus}\n  total: {bd.total}\n  fit_reason: {job.fit_reason}\n")


if __name__ == '__main__':
    main()
