import csv, sys
sys.path.insert(0, 'd:\\Intern-stellar-main')
from src.scrapers.tavily_jobs import _extract_company
from src.scoring.engine import score_job
from src.models import Job

CSV_BEFORE = 'data/jobs_2026-08-06.before.csv'

rows = []
with open(CSV_BEFORE, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

# Choose sample ranks to compare
sample_ranks = [1, 5, 6]

print('Comparing before/after for sample jobs:')
for r in sample_ranks:
    if r-1 >= len(rows):
        continue
    row = rows[r-1]
    title = row.get('title','')
    before_company = row.get('company','')
    url = row.get('url','')
    before_score = row.get('score','')

    # Recompute company using tavily heuristic
    after_company = _extract_company(title or '', url or '')

    # Rescore both variants to show breakdown (before-company vs after-company)
    job_before = Job(title=title or '', company=before_company or 'Unknown Company', url=url or '', source=row.get('source',''))
    job_after = Job(title=title or '', company=after_company or 'Unknown Company', url=url or '', source=row.get('source',''))

    scored_before = score_job(job_before)
    b_before = scored_before.score_breakdown
    scored_after = score_job(job_after)
    b_after = scored_after.score_breakdown

    print(f"Rank {r} -- Title: {title}")
    print(f"  Before - company: {before_company!r}, score: {scored_before.score:.2f}")
    print(f"    role_tier_bonus={b_before.role_tier_bonus:.2f}, seniority_fit_bonus={b_before.seniority_fit_bonus:.2f}, similarity={b_before.similarity:.2f}, skill_match={b_before.skill_match:.2f}, experience_fit={b_before.experience_fit:.2f}, company_signal={b_before.company_signal:.2f}, penalties={b_before.penalties:.2f}")
    print(f"  After  - company: {after_company!r}, score: {scored_after.score:.2f}")
    print(f"    role_tier_bonus={b_after.role_tier_bonus:.2f}, seniority_fit_bonus={b_after.seniority_fit_bonus:.2f}, similarity={b_after.similarity:.2f}, skill_match={b_after.skill_match:.2f}, experience_fit={b_after.experience_fit:.2f}, company_signal={b_after.company_signal:.2f}, penalties={b_after.penalties:.2f}")
    print()
