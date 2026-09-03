# -*- coding: utf-8 -*-
"""
Local demo - chat with your fine-tuned business-administration answer model.

Usage:
  pip install gradio transformers torch
  python scripts/serve.py --model outputs/business-admin-answer-helper/merged
"""
import argparse

import gradio as gr
from transformers import AutoModelForCausalLM, AutoTokenizer


def build(model_path):
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(model_path, device_map="auto")
    return model, tokenizer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="path to merged model")
    args = parser.parse_args()

    model, tokenizer = build(args.model)

    def respond(message, history):
        messages = [{"role": "user", "content": message}]
        for user, assistant in history:
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        out = model.generate(**inputs, max_new_tokens=1024)
        return tokenizer.decode(out[0][inputs["input_ids"].shape[1]:],
                                skip_special_tokens=True)

    gr.ChatInterface(respond, title="Business Admin Answer Helper").launch()


if __name__ == "__main__":
    main()
