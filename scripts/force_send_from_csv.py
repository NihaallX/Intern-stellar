import csv
import sys
from pathlib import Path
# Ensure repo root is on sys.path when running from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.models import Job
from src.scoring.engine import score_job
from src.emailer import generate_email_body, send_email
from src.utils.config import load_settings


def load_jobs_from_csv(csv_path: Path) -> list[Job]:
    rows = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    jobs = []
    for row in rows:
        job = Job(
            title=row.get('title',''),
            company=row.get('company',''),
            url=row.get('url',''),
            source=row.get('source',''),
            location=row.get('location','') or 'Unknown',
            description=row.get('description_preview','')
        )
        # Rescore using current scoring (uses defaults for flags)
        score_job(job)
        jobs.append(job)
    return jobs


def main():
    csv_dir = Path('data')
    csv_files = sorted(csv_dir.glob('jobs_*.csv'))
    if not csv_files:
        print('No CSV files found in data/. Run pipeline first.')
        return

    latest = csv_files[-1]
    print(f'Loading jobs from {latest}')
    jobs = load_jobs_from_csv(latest)

    settings = load_settings()
    # Recreate subject like send_email does
    big_tech_count = sum(1 for j in jobs if 'Big Tech' in (j.tags or []))
    apm_count = sum(1 for j in jobs if 'APM Track' in (j.tags or []))
    subject_prefix = settings.email.get('subject_prefix', '[AI PM Jobs]')
    date_str = __import__('datetime').datetime.now().strftime('%Y-%m-%d')
    subject_parts = [f"{len(jobs)} matches"]
    if big_tech_count:
        subject_parts.append(f"{big_tech_count} Big Tech")
    if apm_count:
        subject_parts.append(f"{apm_count} APM")
    subject = f"{subject_prefix} {' | '.join(subject_parts)} - {date_str}"

    print(f"Subject to be sent: {subject}")

    # Send once
    ok = send_email(jobs, dry_run=False)
    print('send_email returned:', ok)


if __name__ == '__main__':
    main()
