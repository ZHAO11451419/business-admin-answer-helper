#!/usr/bin/env bash
# Business Admin Answer Helper — LoRA / QLoRA fine-tuning entrypoint.
#
# Primary route (recommended): transformers + peft + trl, see scripts/train_lora.py
#   bash scripts/train.sh [--smoke] [--4bit]
#
# Alternative routes (see configs/lora.yaml for LLaMA-Factory):
#   pip install llama-factory && llamafactory-cli train configs/lora.yaml
#
set -euo pipefail

MODE_ARGS=()
if [[ "${1:-}" == "--smoke" ]]; then
  MODE_ARGS+=(--smoke)
fi
if [[ "${1:-}" == "--4bit" ]]; then
  MODE_ARGS+=(--use_4bit)
fi

# 1) validate + split
python scripts/prepare_dataset.py

# 2) train
python scripts/train_lora.py \
  --model_name Qwen/Qwen2.5-7B-Instruct \
  --data data/train.jsonl \
  --output_dir outputs/business-admin-answer-helper \
  --epochs 3 --lr 2e-4 --batch_size 2 --grad_accum 8 \
  "${MODE_ARGS[@]:-}"
