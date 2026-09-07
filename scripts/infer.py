# -*- coding: utf-8 -*-
"""
本地命令行推理：加载微调后的工商管理答题助手并回答问题。

用法示例：
  # 交互模式（一条一条提问）
  python scripts/infer.py --adapter zhaoweichang/business-admin-answer-helper

  # 单题模式
  python scripts/infer.py --adapter zhaoweichang/business-admin-answer-helper -q "Define CVP analysis."

  # 从本地路径加载适配器 / 基座
  python scripts/infer.py --adapter D:/ai/outputs/business-admin-answer-helper-3b/adapter \
                          --base Qwen/Qwen2.5-3B-Instruct

依赖：pip install -U torch transformers peft bitsandbytes
"""
import argparse
import os
import sys

os.environ.setdefault("HF_HOME", r"D:\ai\hf_home")   # 模型缓存放到 D 盘，避免 C 盘空间不足
# 权重已在本地缓存时跳过网络探测（如需联网下载请去掉下面两行）
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
# Windows + torch 2.11: parallel safetensors mmap->CUDA copies can segfault.
# 强制单线程加载权重，保持加载稳定（与 scripts/train_lora.py 相同的修复）。
import transformers.core_model_loading as _cml
_cml.GLOBAL_WORKERS = 1

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

try:
    from calc_assist import fix_arithmetic
except ImportError:  # 以模块方式导入时
    from scripts.calc_assist import fix_arithmetic

DEFAULT_BASE = "Qwen/Qwen2.5-3B-Instruct"
DEFAULT_ADAPTER = "zhaoweichang/business-admin-answer-helper"


def load_model(base_name: str, adapter_path: str):
    """4-bit 加载基座 + 附加 LoRA 适配器（省内存，8GB 显存可跑）。"""
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
    tok = AutoTokenizer.from_pretrained(base_name)
    print("Model ready.", flush=True)
    return model, tok


def ask(model, tok, question: str, max_new: int = 400) -> str:
    s = tok.apply_chat_template(
        [{"role": "user", "content": question}], tokenize=False, add_generation_prompt=True
    )
    inp = tok(s, return_tensors="pt").to(model.device)
    out = model.generate(
        **inp, max_new_tokens=max_new, do_sample=False, pad_token_id=tok.eos_token_id
    )
    return tok.decode(out[0][len(inp["input_ids"][0]):], skip_special_tokens=True)


def _show(answer: str) -> str:
    """输出前经计算器辅助核验：修正算术错误并汇报修正明细。"""
    fixed, corrections = fix_arithmetic(answer)
    if corrections:
        print(f"[calculator-assist] 已修正 {len(corrections)} 处算术错误:", flush=True)
        for old, new in corrections:
            print(f"    {old!r} -> {new!r}", flush=True)
    return fixed


def main():
    parser = argparse.ArgumentParser(description="工商管理答题助手 - 本地命令行推理")
    parser.add_argument("--base", default=DEFAULT_BASE, help="基座模型名或本地路径")
    parser.add_argument("--adapter", default=DEFAULT_ADAPTER, help="LoRA 适配器（HF 名或本地路径）")
    parser.add_argument("-q", "--question", help="单题模式：直接传入问题")
    parser.add_argument("--max-new", type=int, default=400, help="最大生成 token 数")
    args = parser.parse_args()

    model, tok = load_model(args.base, args.adapter)

    if args.question:
        print("\n=== Q:", args.question, flush=True)
        answer = ask(model, tok, args.question, args.max_new)
        _show(answer)
        return

    print("\n交互模式：输入问题，Ctrl+C 退出。", flush=True)
    while True:
        try:
            q = input("\nQ> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break
        if not q:
            continue
        print("A>", _show(ask(model, tok, q, args.max_new)), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.exit(f"ERROR: {e}")
