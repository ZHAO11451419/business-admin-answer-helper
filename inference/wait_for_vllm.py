from __future__ import annotations

import os
import sys
import time
from urllib.request import Request, urlopen


base = os.environ.get("VLLM_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
api_key = os.environ.get("VLLM_API_KEY", "")
url = f"{base}/v1/models"

deadline = time.time() + int(os.environ.get("VLLM_STARTUP_TIMEOUT", "900"))

while time.time() < deadline:
    try:
        request = Request(url, headers={"Authorization": f"Bearer {api_key}"} if api_key else {})
        with urlopen(request, timeout=5) as response:
            if response.status == 200:
                print("vLLM is ready.", flush=True)
                sys.exit(0)
    except Exception as exc:
        print(f"Waiting for vLLM: {type(exc).__name__}", flush=True)
    time.sleep(3)

print("vLLM did not become ready before the timeout.", file=sys.stderr)
sys.exit(1)
