# -*- coding: utf-8 -*-
"""
Gradio 网页界面：在浏览器里与微调后的工商管理答题助手对话。

推荐用法（读 .env 配置）：
  cp .env.example .env    # 首次运行
  # 编辑 .env 填写 BASE_MODEL / ADAPTER_PATH
  python scripts/serve.py

命令行用法：
  python scripts/serve.py --adapter zhaoweichang/business-admin-answer-helper
  python scripts/serve.py --adapter D:/path/to/adapter --base Qwen/Qwen2.5-3B-Instruct
  python scripts/serve.py --offline --cache_dir D:/hf_cache

注意：请使用 gradio 5.x（gradio 6.x 前端存在兼容性问题）。
"""
import argparse
import os
import sys

# --- 中文 Windows 控制台编码修复 ---
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# --- 加载 .env（优先 python-dotenv，缺失则手动解析） ---
def _load_dotenv():
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return
    except ImportError:
        pass
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k.strip(), v)


_load_dotenv()

# --- 缓存目录：在 import transformers 之前设置 ---
_cache_env = os.getenv("CACHE_DIR", "").strip()
if _cache_env and not os.getenv("HF_HOME"):
    os.environ["HF_HOME"] = _cache_env

# --- 离线模式：默认关闭，只有显式开启才启用 ---
_offline_env = os.getenv("LOCAL_FILES_ONLY", "false").strip().lower() in (
    "1", "true", "yes", "on"
)
if _offline_env:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# --- Windows + torch 2.11 加载 safetensors 段错误缓解 ---
try:
    import transformers.core_model_loading as _cml
    _cml.GLOBAL_WORKERS = 1
except Exception:
    pass


import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
import gradio as gr

try:
    from calc_assist import fix_arithmetic
except ImportError:
    try:
        from scripts.calc_assist import fix_arithmetic
    except ImportError:
        def fix_arithmetic(text):
            return text, []


DEFAULT_BASE = os.getenv("BASE_MODEL", "Qwen/Qwen2.5-3B-Instruct")
DEFAULT_ADAPTER = os.getenv("ADAPTER_PATH", "zhaoweichang/business-admin-answer-helper")
DEFAULT_HOST = os.getenv("HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("PORT", "7860"))


def build(base_name, adapter_path, cache_dir=None, local_files_only=False):
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    print(f"Loading base model: {base_name} (4-bit)...", flush=True)
    base = AutoModelForCausalLM.from_pretrained(
        base_name,
        quantization_config=bnb,
        device_map="auto",
        dtype=torch.bfloat16,
        cache_dir=cache_dir or None,
        local_files_only=local_files_only,
    )
    print(f"Attaching LoRA adapter: {adapter_path}...", flush=True)
    model = PeftModel.from_pretrained(
        base, adapter_path, cache_dir=cache_dir or None
    )
    tokenizer = AutoTokenizer.from_pretrained(
        base_name,
        cache_dir=cache_dir or None,
        local_files_only=local_files_only,
    )
    print("Model ready.", flush=True)
    return model, tokenizer


def build_messages(history, current_question, max_turns=12):
    """
    按 LLM 标准顺序构建消息列表：
      历史(user/assistant 正序交替) -> 当前 user 问题
    最新问题必须在末尾，否则会破坏模型对追问的理解（重要修复）。
    """
    messages = []
    for item in history[-max_turns:]:
        if isinstance(item, dict):
            role = item.get("role", "user")
            content = item.get("content", "")
            if isinstance(content, list):  # multimodal 内容取纯文本
                content = " ".join(
                    c.get("text", "") for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                )
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        else:  # 旧版 (user, assistant) 元组
            user, assistant = item
            if user:
                messages.append({"role": "user", "content": user})
            if assistant:
                messages.append({"role": "assistant", "content": assistant})
    # === 关键修复：最新问题放在最后 ===
    messages.append({"role": "user", "content": current_question})
    return messages


def main():
    parser = argparse.ArgumentParser(description="工商管理答题助手 - Gradio 网页界面")
    parser.add_argument("--base", default=DEFAULT_BASE,
                        help="基座模型名或本地路径（默认取 BASE_MODEL 环境变量）")
    parser.add_argument("--adapter", "--model", dest="adapter", default=DEFAULT_ADAPTER,
                        help="LoRA 适配器（HF 名或本地路径）。--model 为兼容别名。")
    parser.add_argument("--cache_dir", default=os.getenv("CACHE_DIR", ""),
                        help="HuggingFace 缓存目录（默认 ./model_cache 或 CACHE_DIR）")
    parser.add_argument("--offline", action="store_true",
                        help="强制离线模式，只使用本地缓存（首次运行请勿开启）")
    parser.add_argument("--host", default=DEFAULT_HOST, help="监听地址")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="端口号")
    args = parser.parse_args()

    cache_dir = args.cache_dir or os.getenv("CACHE_DIR", "").strip() or None
    offline = args.offline or _offline_env

    model, tokenizer = build(args.base, args.adapter,
                             cache_dir=cache_dir, local_files_only=offline)

    def respond(message, history):
        messages = build_messages(history, message)
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        try:
            out = model.generate(
                **inputs, max_new_tokens=512, do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
            raw = tokenizer.decode(
                out[0][inputs["input_ids"].shape[1]:],
                skip_special_tokens=True,
            )
            fixed, corrections = fix_arithmetic(raw)
            if corrections:
                print(f"[calculator-assist] corrected {len(corrections)}:", flush=True)
                for old, new in corrections:
                    print(f"    {old!r} -> {new!r}", flush=True)
            return fixed
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    gr.ChatInterface(
        respond,
        title="工商管理答题助手",
        description="基于 Qwen2.5-3B 微调的工商管理高分答题模型。计算题、概念题、案例题均可提问。",
    ).launch(server_name=args.host, server_port=args.port)


if __name__ == "__main__":
    main()
