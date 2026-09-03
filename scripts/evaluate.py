# -*- coding: utf-8 -*-
"""
Evaluate the fine-tuned model on held-out questions.

Checks two things markers care about:
  1. FORMAT adherence - does the answer show workings, give interpretations,
     use numbered structure (per docs/answering-guide.md)?
  2. CALCULATION accuracy - for "calculation"-type questions, does the final
     number match a reference solution?

Usage:
  python scripts/evaluate.py --model outputs/business-admin-answer-helper/merged \
      --test data/train.jsonl --split 0.2
"""
import argparse
import json
import re
import sys

FORMAT_CHECKS = {
    "calculation": {
        "shows_formula": r"(?i)(=|\bformula\b)",
        "shows_workings": r"(?i)(step|substitut|\b=\s*\d|÷|/)",
        "gives_interpretation": r"(?i)(interpret|mean|for every RM)",
    },
    "concept": {
        "has_definition": r"(?i)(is a|is the|means|refers to)",
        "has_example": r"(?i)(example|for instance|e\.g\.)",
    },
    "case": {
        "explicit_judgement": r"(?i)(should|should not|recommend|advise)",
        "numbered_reasons": r"(?i)(\(1\)|\(2\)|\(3\)|firstly|secondly|thirdly)",
    },
    "essay": {
        "numbered_sections": r"(?i)(1\.0|2\.0|3\.0|1\. |2\. )",
        "citations": r"\(([A-Z][a-z]+|MASB|BNM|Bursa|GRI|IFRS)[^)]*,\s*\d{4}\)",
    },
}


def load_pairs(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def reference_answer(pair):
    """Extract the first RM/number from a calculation output as a naive oracle."""
    m = re.search(r"=\s*(RM\s*[\d,]+\.?\d*)", pair.get("output", ""))
    return m.group(1) if m else None


def check_format(pair, generated):
    qtype = pair.get("type", "")
    checks = FORMAT_CHECKS.get(qtype, {})
    passed, total = 0, len(checks)
    for name, pattern in checks.items():
        if re.search(pattern, generated):
            passed += 1
    return passed, total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="path to merged model")
    parser.add_argument("--test", default="data/train.jsonl", help="test dataset (jsonl)")
    parser.add_argument("--split", type=float, default=0.2, help="held-out fraction")
    args = parser.parse_args()

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        sys.exit("Missing deps: pip install transformers torch")

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, device_map="auto")

    pairs = load_pairs(args.test)
    test = pairs[-int(len(pairs) * args.split):] if args.split > 0 else pairs

    format_hits, format_total = 0, 0
    calc_ok, calc_n = 0, 0
    for pair in test:
        prompt = pair["instruction"]
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        out = model.generate(**inputs, max_new_tokens=512)
        generated = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

        p, t = check_format(pair, generated)
        format_hits += p
        format_total += t

        if pair.get("type") == "calculation":
            ref = reference_answer(pair)
            if ref and re.search(re.escape(ref), generated):
                calc_ok += 1
            calc_n += 1

    fmt = format_hits / format_total if format_total else 0
    print(f"Format adherence : {format_hits}/{format_total} = {fmt:.0%}")
    if calc_n:
        print(f"Calculation match: {calc_ok}/{calc_n} = {calc_ok / calc_n:.0%}")


if __name__ == "__main__":
    main()
