#!/usr/bin/env bash
set -euo pipefail

BASE_MODEL="${BASE_MODEL:-Qwen/Qwen2.5-3B-Instruct}"
LORA_REPO="${LORA_REPO:-zhaoweichang/business-admin-answer-helper}"
LORA_NAME="${LORA_NAME:-bah}"
LORA_DIR="${LORA_DIR:-/root/.cache/huggingface/bah-lora}"
VLLM_HOST="${VLLM_HOST:-127.0.0.1}"
VLLM_PORT="${VLLM_PORT:-8000}"
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8080}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.85}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-8}"
VLLM_STARTUP_TIMEOUT="${VLLM_STARTUP_TIMEOUT:-900}"

mkdir -p "${LORA_DIR}"

python3 - <<'PY2'
import os
from huggingface_hub import snapshot_download
repo_id = os.environ.get("LORA_REPO", "zhaoweichang/business-admin-answer-helper")
local_dir = os.environ.get("LORA_DIR", "/root/.cache/huggingface/bah-lora")
token = os.environ.get("HF_TOKEN") or None
print(f"[BAH] Checking LoRA repo: {repo_id}", flush=True)
snapshot_download(repo_id=repo_id, local_dir=local_dir, token=token)
print(f"[BAH] LoRA ready at: {local_dir}", flush=True)
PY2

echo "[BAH] Starting vLLM 0.8.5..." >&2
python3 -m vllm.entrypoints.openai.api_server \
  --model "${BASE_MODEL}" \
  --host "${VLLM_HOST}" \
  --port "${VLLM_PORT}" \
  --enable-lora \
  --lora-modules "${LORA_NAME}=${LORA_DIR}" \
  --max-loras 1 \
  --max-lora-rank 32 \
  --dtype auto \
  --max-model-len "${MAX_MODEL_LEN}" \
  --max-num-seqs "${MAX_NUM_SEQS}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}" \
  --enforce-eager \
  > /tmp/vllm.log 2>&1 &

VLLM_PID=$!
echo "[BAH] vLLM PID=${VLLM_PID}" >&2

python3 /app/inference/wait_for_vllm.py

echo "[BAH] vLLM startup log:" >&2
tail -n 80 /tmp/vllm.log >&2 || true

exec uvicorn backend.main:app --host "${API_HOST}" --port "${API_PORT}"
