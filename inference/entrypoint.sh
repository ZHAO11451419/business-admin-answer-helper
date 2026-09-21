#!/usr/bin/env bash
set -euo pipefail

: "${VLLM_MODEL:=bah}"
: "${BASE_MODEL:=Qwen/Qwen2.5-3B-Instruct}"
: "${LORA_REPO:=zhaoweichang/business-admin-answer-helper}"
: "${VLLM_API_KEY:=change-me}"
: "${PUBLIC_PORT:=8080}"
: "${MAX_MODEL_LEN:=8192}"
: "${GPU_MEMORY_UTILIZATION:=0.90}"

export INFERENCE_MODE=remote
export VLLM_BASE_URL="http://127.0.0.1:8000"
export VLLM_MODEL="${VLLM_MODEL}"
export VLLM_API_KEY="${VLLM_API_KEY}"
export PYTHONPATH="/app/backend:/app"

# Your current published adapter is rank 24. vLLM's allowed maximum should
# therefore be at least 32. See the repository README and vLLM LoRA docs.
vllm serve "${BASE_MODEL}" \
  --host 127.0.0.1 \
  --port 8000 \
  --served-model-name "${VLLM_MODEL}" \
  --enable-lora \
  --max-loras 1 \
  --max-lora-rank 32 \
  --max-model-len "${MAX_MODEL_LEN}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}" \
  --lora-modules "{\"name\":\"${VLLM_MODEL}\",\"path\":\"${LORA_REPO}\",\"base_model_name\":\"${BASE_MODEL}\"}" \
  --api-key "${VLLM_API_KEY}" \
  --no-enable-log-requests &

VLLM_PID=$!
trap 'kill ${VLLM_PID} 2>/dev/null || true' EXIT

python /app/inference/wait_for_vllm.py

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PUBLIC_PORT}"
