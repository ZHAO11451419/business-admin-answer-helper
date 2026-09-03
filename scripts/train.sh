#!/usr/bin/env bash
# Fine-tune a business-administration answer model with LoRA.
# Two supported paths: LLaMA-Factory (configs/lora.yaml) or Unsloth (notebook-style below).
#
# Prerequisites:
#   - Python 3.10+, a GPU with ~24GB VRAM (or use a cloud GPU / Colab)
#   - pip install -U torch transformers datasets peft trl
#
# LLaMA-Factory route (recommended, easiest):
#   pip install llama-factory
#   llamafactory-cli train configs/lora.yaml
#
# Unsloth route:
set -euo pipefail

BASE_MODEL="Qwen/Qwen2.5-7B-Instruct"
DATA_PATH="data/train.jsonl"
OUTPUT_DIR="outputs/business-admin-answer-helper"
EPOCHS=${EPOCHS:-3}
LR=${LR:-2e-4}

# Unsloth quick-start (adapted; requires: pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git")
python - <<PY
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import load_dataset

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="${BASE_MODEL}",
    max_seq_length=2048,
    dtype=None, load_in_4bit=True,
)
model = FastLanguageModel.get_peft_model(
    model, r=16, target_modules=["q_proj","k_proj","v_proj","o_proj",
                                 "gate_proj","up_proj","down_proj"],
    lora_alpha=32, lora_dropout=0.05, bias="none", use_gradient_checkpointing=True,
)

def fmt(example):
    return tokenizer.apply_chat_template(
        [{"role":"user","content":example["instruction"]},
         {"role":"assistant","content":example["output"]}],
        tokenize=False, add_generation_prompt=False)

dataset = load_dataset("json", data_files="${DATA_PATH}", split="train")
dataset = dataset.map(lambda e: {"text": fmt(e)})

trainer = SFTTrainer(
    model=model, tokenizer=tokenizer,
    train_dataset=dataset,
    args=TrainingArguments(
        per_device_train_batch_size=2, gradient_accumulation_steps=8,
        learning_rate=${LR}, num_train_epochs=${EPOCHS},
        lr_scheduler_type="cosine", warmup_ratio=0.1,
        bf16=True, logging_steps=10, save_steps=500,
        output_dir="${OUTPUT_DIR}", seed=42,
    ),
)
trainer.train()
model.save_pretrained_merged("${OUTPUT_DIR}/merged", tokenizer, save_method="merged_16bit")
print("Done. Adapter: ${OUTPUT_DIR}; merged: ${OUTPUT_DIR}/merged")
PY
