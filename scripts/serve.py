# -*- coding: utf-8 -*-
"""
Gradio 网页界面：在浏览器里与微调后的工商管理答题助手对话。

用法：
  pip install -U "gradio<6" transformers torch peft bitsandbytes
  python scripts/serve.py --adapter zhaoweichang/business-admin-answer-helper
  # 打开 http://127.0.0.1:7860 即可对话

注意：请使用 gradio 5.x（gradio 6.x 的前端复制/操作按钮存在兼容性问题）。

本地路径示例：
  python scripts/serve.py --adapter D:/ai/outputs/business-admin-answer-helper-3b/adapter \
                          --base Qwen/Qwen2.5-3B-Instruct
"""
import argparse
import os
import sys

# 中文 Windows 控制台默认 GBK，无法编码 Unicode 减号（−，U+2212）等字符，
# 打印 calc_assist 修正记录时会抛 UnicodeEncodeError 导致回答流程崩溃。
# 强制 stdout/stderr 使用 UTF-8，并对无法编码的字符做替换而非报错。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

os.environ.setdefault("HF_HOME", r"D:\ai\hf_home")   # 模型缓存放到 D 盘
os.environ.setdefault("HF_HUB_OFFLINE", "1")          # 本地缓存优先，避免联网超时
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
# Windows + torch 2.11: parallel safetensors mmap->CUDA copies can segfault.
import transformers.core_model_loading as _cml
_cml.GLOBAL_WORKERS = 1

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

import gradio as gr

try:
    from calc_assist import fix_arithmetic
except ImportError:  # 以模块方式导入时
    from scripts.calc_assist import fix_arithmetic

DEFAULT_BASE = "Qwen/Qwen2.5-3B-Instruct"
DEFAULT_ADAPTER = "zhaoweichang/business-admin-answer-helper"


def build(base_name: str, adapter_path: str):
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    print("Loading base model (4-bit)...", flush=True)
    base = AutoModelForCausalLM.from_pretrained(
        base_name,
        quantization_config=bnb,
        device_map="auto",
        dtype=torch.bfloat16,
    )
    print("Attaching LoRA adapter...", flush=True)
    model = PeftModel.from_pretrained(base, adapter_path)
    tokenizer = AutoTokenizer.from_pretrained(base_name)
    print("Model ready. Open http://127.0.0.1:7860", flush=True)
    return model, tokenizer


def main():
    parser = argparse.ArgumentParser(description="工商管理答题助手 - Gradio 网页界面")
    parser.add_argument("--base", default=DEFAULT_BASE, help="基座模型名或本地路径")
    parser.add_argument("--adapter", default=DEFAULT_ADAPTER, help="LoRA 适配器（HF 名或本地路径）")
    parser.add_argument("--port", type=int, default=7860, help="端口号")
    args = parser.parse_args()

    model, tokenizer = build(args.base, args.adapter)

    def respond(message, history):
        # gradio 6.x 的 history 是 openai 风格字典列表 [{"role","content"}]；
        # 兼容旧版元组列表 (user, assistant) 以防版本差异。
        messages = [{"role": "user", "content": message}]
        for item in history[-12:]:  # 只保留最近 12 轮，防止 prompt 无限膨胀
            if isinstance(item, dict):
                role = item.get("role", "user")
                content = item.get("content", "")
                if isinstance(content, list):  # multimodal 内容取纯文本
                    content = " ".join(
                        c.get("text", "") for c in content
                        if isinstance(c, dict) and c.get("type") == "text"
                    )
                messages.append({"role": role, "content": content})
            else:  # 旧版 (user, assistant) 元组
                user, assistant = item
                messages.append({"role": "user", "content": user})
                messages.append({"role": "assistant", "content": assistant})
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        try:
            out = model.generate(**inputs, max_new_tokens=512, do_sample=False,
                                 pad_token_id=tokenizer.eos_token_id)
            raw = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:],
                                   skip_special_tokens=True)
            # 计算器辅助：核验并修正算术错误
            fixed, corrections = fix_arithmetic(raw)
            if corrections:
                print(f"[calculator-assist] corrected {len(corrections)}:", flush=True)
                for old, new in corrections:
                    print(f"    {old!r} -> {new!r}", flush=True)
            return fixed
        finally:
            torch.cuda.empty_cache()  # 释放显存，避免连续对话累积

    gr.ChatInterface(
        respond,
        title="工商管理答题助手",
        description="基于 Qwen2.5-3B 微调的工商管理高分答题模型。计算题、概念题、案例题均可提问。",
    ).launch(server_port=args.port)


if __name__ == "__main__":
    main()
