---
license: apache-2.0
base_model: Qwen/Qwen2.5-3B-Instruct
tags:
  - business-administration
  - education
  - lora
  - qlora
  - sft
language:
  - en
datasets:
  - zhaoweichang/business-admin-answer-helper
pipeline_tag: text-generation
---

# Business Admin Answer Helper (BAH) — LoRA adapter

A **LoRA adapter** fine-tuned from `Qwen/Qwen2.5-3B-Instruct` on a 444-pair
instruction dataset distilled from real UPM business-administration coursework
answering conventions.

It answers business-school questions the way a high-scoring student would:
correct answering format, full calculation steps, business interpretation, and
proper citations — not just raw content.

## Training

| Item | Value |
|---|---|
| Base model | Qwen/Qwen2.5-3B-Instruct |
| Method | QLoRA (4-bit NF4, double quant), LoRA r=16 α=32, all linear modules |
| Data | 444 pairs (326 calculation, 53 concept, 37 case, 28 essay), train/val 95/5 split |
| Epochs / LR / scheduler | 3 / 2e-4 / cosine, warmup 10% |
| Hardware | NVIDIA RTX 4060 Laptop 8GB, ~12 min |
| Train loss | 2.46 → 0.61 |
| Eval loss | 0.56 |
| Eval token accuracy | **85.7%** |

## Usage

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
                         bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)
base = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-3B-Instruct", quantization_config=bnb,
    device_map="auto", torch_dtype=torch.bfloat16)
model = PeftModel.from_pretrained(base, "zhaoweichang/business-admin-answer-helper")
tok = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-3B-Instruct")

q = "Calculate the break-even point in units for Bersatu Limited. Price RM1.50, variable cost RM0.75, fixed costs RM15,000."
s = tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True)
out = model.generate(**tok(s, return_tensors="pt").to(model.device), max_new_tokens=200, do_sample=False)
print(tok.decode(out[0][len(tok(s)["input_ids"][0]):], skip_special_tokens=True))
```

Also available: a **merged 16-bit** version of the same model
(`...-merged`, ~2.6GB).

## Disclaimer

Training data is derived from openly described answering conventions and
original example solutions; it contains no copyrighted textbook content or
personal information. Users must comply with their institution's
academic-integrity policy and verify all numbers, citations, and facts before
submission.
