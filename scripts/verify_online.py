# -*- coding: utf-8 -*-
"""创空间在线推理验收脚本：传任意问题，等待冷启动+生成，打印完整输出。
用法: python _verify_online.py "问题文本"
"""
import json
import sys
import time
import urllib.request
import uuid

QUESTION = sys.argv[1] if len(sys.argv) > 1 else "A shop raises the price of a drink from RM5.00 to RM6.00 and weekly quantity sold falls from 100 to 80. Calculate the price elasticity of demand and classify the demand."

base = "https://zhao1145141919-business-admin-answer-helper.ms.show"
api = base + "/gradio_api"
session = uuid.uuid4().hex[:8]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

def _open(url, data=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "User-Agent": UA, "Referer": "https://modelscope.cn/"})
    return urllib.request.urlopen(req, timeout=timeout)

print("Q:", QUESTION, flush=True)

# 1) config
cfg = json.load(_open(base + "/config", timeout=30))
deps = cfg.get("dependencies", [])
print("CONFIG OK, deps:", [(d.get("id"), d.get("api_name")) for d in deps][:6], flush=True)

# 2) join（ChatInterface：message dict + history 空列表）
payload = {
    "data": [{"text": QUESTION, "files": []}, []],
    "event_data": None,
    "fn_index": 3,
    "session_hash": session,
    "trigger_id": 1,
}
req = urllib.request.Request(
    api + "/queue/join",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "User-Agent": UA, "Referer": "https://modelscope.cn/"},
)
try:
    resp = urllib.request.urlopen(req, timeout=30)
    print("JOIN:", resp.status, resp.read()[:200], flush=True)
except Exception as e:
    print("JOIN ERR:", e, flush=True)
    raise SystemExit(1)

# 3) SSE
print("READING EVENTS (cold start may take 3-10 min)...", flush=True)
deadline = time.time() + 720
final_txt = ""
try:
    stream = _open(api + "/queue/data?session_hash=" + session, timeout=780)
    for raw in stream:
        line = raw.decode("utf-8", "ignore").strip()
        if not line.startswith("data:"):
            continue
        ev = json.loads(line[5:])
        msg = ev.get("msg")
        if msg in ("process_completed", "process_generating"):
            out = ev.get("output", {})
            try:
                data = out.get("data", [])
                if data and isinstance(data[0], dict):
                    txt = str(data[0].get("text", ""))
                elif data:
                    txt = str(data[0])
                else:
                    txt = str(out)[:300]
            except Exception:
                txt = str(out)[:300]
            if msg == "process_generating":
                print(f"[stream] {txt[:200]}", flush=True)
            else:
                final_txt = txt
                print(f"\n[process_completed] success={ev.get('success')}", flush=True)
                print("=" * 72, flush=True)
                print(final_txt, flush=True)
        elif msg in ("queue_full", "error"):
            print(f"[{msg}] {str(ev)[:300]}", flush=True)
        if msg == "process_completed":
            print("DONE", flush=True)
            break
        if time.time() > deadline:
            print("TIMEOUT waiting", flush=True)
            break
except Exception as e:
    print("STREAM ERR:", e, flush=True)
