import csv
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.scoring.engine import build_fit_reason
from src.models import ExtractedFlags
from src.llm.nim_client import generate_fit_reason, infer_posted_date
from src.utils.date_filter import detect_posted_date

CSV = Path('data') / sorted(Path('data').glob('jobs_*.csv'))[-1].name

rows = []
with open(CSV, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

print(f'Validating NIM fit_reason and date fallback on {CSV} (showing up to 5 samples)')

excluded_by_date = 0
samples = rows[:10]
count = 0
for r in samples:
    title = r.get('title','')
    desc = r.get('description_preview','')
    url = r.get('url','')
    old = build_fit_reason(type('J', (), {'title': title, 'description': desc}), ExtractedFlags())
    new, src = generate_fit_reason(title, desc, '', url)

    parsed_date = detect_posted_date(title, desc, url)
    nim_date = None
    if parsed_date is None:
        nim_date = infer_posted_date(title, desc, url)
        if nim_date is None:
            excluded_by_date += 1

    print(f'--- Sample: {title}')
    print(f'  URL: {url}')
    print(f'  Old fit_reason: {old}')
    print(f'  New fit_reason: {new}  (source: {src})')
    print(f'  Parsed date: {parsed_date}')
    print(f'  NIM inferred date: {nim_date}')
    print('')
    count += 1
    if count >= 5:
        break

print(f'Number of inspected samples that would be excluded due to date fallback failure: {excluded_by_date}')
