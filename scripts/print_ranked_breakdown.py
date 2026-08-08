import csv
from pathlib import Path
from src.models import Job
from src.scoring.engine import score_job, classify_role_tier

csv_path = Path('data') / sorted(Path('data').glob('jobs_*.csv'))[-1].name

rows = []
with open(csv_path, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

print(f'Loaded {len(rows)} rows from {csv_path}')

for i, row in enumerate(rows[:10], 1):
    job = Job(
        title=row.get('title',''),
        company=row.get('company',''),
        url=row.get('url',''),
        source=row.get('source',''),
        location=row.get('location','') or 'Unknown',
        description=row.get('description_preview','')
    )
    scored = score_job(job)
    b = scored.score_breakdown
    print(f"{i}. {job.title} | tier={classify_role_tier(job)} | role_tier_bonus={b.role_tier_bonus:.2f} | seniority_fit_bonus={b.seniority_fit_bonus:.2f} | total={scored.score:.2f}")
    print(f"  why_matched: {scored.why_matched}")
    print()
