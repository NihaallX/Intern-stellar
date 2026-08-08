import os
import json
import httpx

MODEL_FILE = os.path.join('data', 'nim_models.json')
NIM_BASE = 'https://integrate.api.nvidia.com/v1'
NIM_CHAT = f"{NIM_BASE}/chat/completions"


def load_model_id():
    with open(MODEL_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    models = data.get('models') or []
    if not models:
        raise SystemExit('No models found in nim_models.json')
    # pick the first model exactly as listed
    return models[0]


def main():
    model_id = load_model_id()

    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Say hello in one word."}],
        "max_tokens": 10,
    }

    nim_key = os.environ.get('NIM_API_KEY')

    headers = {"Content-Type": "application/json"}
    if nim_key:
        headers["Authorization"] = f"Bearer {nim_key}"

    # Print exact outgoing request (with key redacted)
    redacted_headers = dict(headers)
    if 'Authorization' in redacted_headers:
        redacted_headers['Authorization'] = 'Bearer REDACTED'

    print('OUTGOING REQUEST')
    print('URL:', NIM_CHAT)
    print('HEADERS:', json.dumps(redacted_headers, indent=2))
    print('BODY:', json.dumps(body, ensure_ascii=False, indent=2))

    # Send the request
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.post(NIM_CHAT, json=body, headers=headers)
            status = resp.status_code
            text = resp.text
    except Exception as e:
        status = 'EXCEPTION'
        text = str(e)

    print('\nRESPONSE')
    print('STATUS:', status)
    print('BODY:', text)


if __name__ == '__main__':
    main()
