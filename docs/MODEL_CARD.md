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
  - zh
  - en
datasets:
  - zhaoweichang/business-admin-answer-helper
pipeline_tag: text-generation
---

# 工商管理答题助手（BAH）— LoRA 适配器

基于 `Qwen/Qwen2.5-3B-Instruct` 微调的 **LoRA 适配器**，训练数据来自真实 UPM 工商管理课程答题规范提炼的 444 对指令数据集。

它像高分学生一样回答商学院问题：正确的答题格式、完整的计算步骤、商业解读和规范引用——而不只是罗列内容。

## 训练信息

| 项目 | 数值 |
|---|---|
| 基座模型 | Qwen/Qwen2.5-3B-Instruct |
| 方法 | QLoRA（4-bit NF4，双重量化），LoRA r=16 α=32，全部线性模块 |
| 数据 | 444 对（计算 326 / 概念 53 / 案例 37 / 论述 28），训练/验证 95/5 划分 |
| Epoch / 学习率 / 调度器 | 3 / 2e-4 / cosine，warmup 10% |
| 硬件 | NVIDIA RTX 4060 Laptop 8GB，约 12 分钟 |
| 训练 loss | 2.46 → 0.61 |
| 验证 loss | 0.56 |
| 验证集 token 准确率 | **85.7%** |

## 使用方法

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

也提供：同一模型的**合并 16-bit 完整版**（`...-merged`，约 2.6GB）。

## 免责声明

训练数据来自公开描述的答题规范和原创示例解答，**不含**受版权保护的教材内容或个人隐私信息。使用者须遵守所在院校的学术诚信政策，并在提交前核对所有数字、引用和事实。
