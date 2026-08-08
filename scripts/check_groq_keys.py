import pathlib
import requests
import json

ENV_PATH = pathlib.Path(__file__).resolve().parents[1] / '.env'

def load_env_keys(path):
    keys = {}
    text = path.read_text(encoding='utf-8')
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        keys[k.strip()] = v.strip()
    return keys


def check_key(name, key):
    url = 'https://api.groq.com/openai/v1/models'
    if not key:
        print(f'{name}: MISSING')
        return
    try:
        r = requests.get(url, headers={'Authorization': f'Bearer {key}'}, timeout=20)
        print(f'{name}: HTTP {r.status_code}')
        if r.status_code == 200:
            try:
                data = r.json()
                print(f'{name}: OK; models_count={len(data.get("data", []))}')
            except Exception as e:
                print(f'{name}: 200 OK but JSON parse failed: {e}')
        else:
            body = r.text.replace('\n', ' ')[:1000]
            print(f'{name}: ERROR_BODY {body}')
    except Exception as e:
        print(f'{name}: EXCEPTION {e}')


if __name__ == '__main__':
    keys = load_env_keys(ENV_PATH)
    for k in ['GROQ_API_KEY', 'GROQ_API_KEY_2']:
        check_key(k, keys.get(k, ''))
