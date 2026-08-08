import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Set the provided NIM key for this process
os.environ['NIM_API_KEY'] = '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'

from src.llm.nim_client import generate_fit_reason, infer_posted_date

title = 'Coins.ph - AI Product Manager'
desc = 'We are hiring an AI Product Manager to ship LLM-driven fintech products. Posted 3 weeks ago.'
url = 'https://jobs.lever.co/coins/test'
# Remove any cached entry for this test URL so we force a NIM call
import json
from pathlib import Path
fit_cache = Path('data') / 'nim_fit_reason_cache.json'
try:
	if fit_cache.exists():
		data = json.loads(fit_cache.read_text(encoding='utf-8') or '{}')
		if url in data:
			del data[url]
			fit_cache.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
except Exception:
	pass

reason, source = generate_fit_reason(title, desc, '', url)
date = infer_posted_date(title, desc, url)

print('generate_fit_reason ->', repr(reason), '| source=', source)
print('infer_posted_date ->', repr(date))
