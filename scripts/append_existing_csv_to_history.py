import csv
from pathlib import Path
from datetime import datetime

from src.models import Job
from src.main import export_csv


def load_rows(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def build_job_from_row(row):
    j = Job(
        title=row.get('title') or '',
        company=row.get('company') or '',
        url=row.get('url') or '',
        source=row.get('source') or '',
        description=row.get('description_preview') or '',
    )
    try:
        j.score = float(row.get('score') or 0)
    except Exception:
        j.score = 0.0
    pd = row.get('posted_date')
    if pd:
        try:
            j.posted_date = datetime.fromisoformat(pd)
        except Exception:
            pass
    return j


def main():
    src = Path('data') / 'jobs_2026-08-08.csv'
    if not src.exists():
        print('Source CSV not found:', src)
        return

    rows = load_rows(src)
    jobs = [build_job_from_row(r) for r in rows]

    out = export_csv(jobs)
    print('Appended', len(jobs), 'rows to', out)


if __name__ == '__main__':
    main()
