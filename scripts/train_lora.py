# -*- coding: utf-8 -*-
"""
Fine-tune a business-administration answer model with LoRA / QLoRA (SFT).

Standard, reproducible path using Hugging Face transformers + peft + trl.
Designed to run on a free Colab T4 (16GB) or any CUDA GPU. Use --smoke to run
a 1-step CPU/GPU sanity check on a tiny subset (no bitsandbytes needed).

Usage (full, Colab T4):
  pip install -U torch transformers peft trl datasets accelerate bitsandbytes
  python scripts/train_lora.py \
      --model_name Qwen/Qwen2.5-7B-Instruct \
      --data data/train.jsonl \
      --output_dir outputs/business-admin-answer-helper \
      --epochs 3 --lr 2e-4 --batch_size 2 --grad_accum 8 --use_4bit

Smoke test (any machine, no GPU / no bitsandbytes):
  python scripts/train_lora.py --smoke --model_name Qwen/Qwen2.5-0.5B-Instruct
"""
import argparse
import json
import os
import sys


def load_pairs(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_formatting(tokenizer):
    def fmt(example):
        user = example["instruction"]
        if example.get("input", "").strip():
            user = user + "\n" + example["input"].strip()
        messages = [
            {"role": "user", "content": user},
            {"role": "assistant", "content": example["output"]},
        ]
        # trl 1.12: formatting_func must return the rendered text string
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False)
    return fmt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--data", default="data/train.jsonl")
    parser.add_argument("--output_dir", default="outputs/business-admin-answer-helper")
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--grad_accum", type=int, default=8)
    parser.add_argument("--max_length", type=int, default=2048)
    parser.add_argument("--lora_r", type=int, default=16)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--lora_dropout", type=float, default=0.05)
    parser.add_argument("--warmup_ratio", type=float, default=0.1)
    parser.add_argument("--use_4bit", action="store_true",
                        help="QLoRA via bitsandbytes (needs CUDA)")
    parser.add_argument("--max_steps", type=int, default=None)
    parser.add_argument("--val_size", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--smoke", action="store_true",
                        help="tiny 1-step run to verify the pipeline")
    args = parser.parse_args()

    try:
        import torch
        from transformers import (AutoModelForCausalLM, AutoTokenizer,
                                  BitsAndBytesConfig)
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from trl import SFTTrainer, SFTConfig
        from datasets import Dataset
    except ImportError as e:
        sys.exit(f"Missing deps: {e}. Run: pip install -U torch transformers peft trl datasets accelerate" +
                 (" bitsandbytes" if args.use_4bit else ""))

    if args.smoke:
        args.batch_size = 1
        args.grad_accum = 1
        args.epochs = 1.0
        args.max_steps = 2
        args.use_4bit = False
        args.max_length = 512
        print("[smoke] overriding to batch=1, max_steps=2, no 4bit")

    print(f"Loading base model: {args.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    if args.use_4bit:
        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            bnb_4bit_use_double_quant=True,
        )
    else:
        bnb = None
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        quantization_config=bnb,
        device_map="auto" if torch.cuda.is_available() else "cpu",
        trust_remote_code=True,
    )
    if args.use_4bit:
        model = prepare_model_for_kbit_training(model)

    peft_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    pairs = load_pairs(args.data)
    if args.smoke:
        pairs = pairs[:16]
    dataset = Dataset.from_list(pairs)
    if args.val_size > 0 and not args.smoke:
        split = dataset.train_test_split(test_size=args.val_size, seed=args.seed)
        train_ds, val_ds = split["train"], split["test"]
    else:
        train_ds, val_ds = dataset, None

    formatting = build_formatting(tokenizer)
    steps_per_epoch = max(1, len(train_ds) // (args.batch_size * args.grad_accum))
    total_steps = int(steps_per_epoch * args.epochs) if args.max_steps is None else args.max_steps
    warmup_steps = max(0, int(total_steps * args.warmup_ratio))
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        formatting_func=formatting,
        args=SFTConfig(
            output_dir=args.output_dir,
            max_length=args.max_length,
            dataset_text_field="text",
            packing=False,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
            learning_rate=args.lr,
            num_train_epochs=args.epochs,
            max_steps=args.max_steps,
            lr_scheduler_type="cosine",
            warmup_steps=warmup_steps,
            logging_steps=1,
            save_strategy="steps",
            save_steps=200,
            eval_strategy="steps" if val_ds else "no",
            eval_steps=200,
            bf16=torch.cuda.is_available(),
            fp16=False,
            seed=args.seed,
            report_to=[],
        ),
    )

    print("Training...")
    trainer.train()

    adapter_dir = os.path.join(args.output_dir, "adapter")
    model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)
    print(f"LoRA adapter saved to {adapter_dir}")

    if not args.smoke:
        print("Merging adapter into base model (16-bit)...")
        merged = model.merge_and_unload()
        merged_dir = os.path.join(args.output_dir, "merged")
        merged.save_pretrained(merged_dir)
        tokenizer.save_pretrained(merged_dir)
        print(f"Merged 16-bit model saved to {merged_dir}")
        print("Done. Serve it with: python scripts/serve.py --model " + merged_dir)


if __name__ == "__main__":
    main()
