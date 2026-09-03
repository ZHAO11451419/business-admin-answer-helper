# -*- coding: utf-8 -*-
"""
Build data/train.jsonl from raw course materials.

Pipeline:
  1. Place cleaned, copyright-safe source material in data/raw/ (see data/raw/README.md).
  2. Convert each source into instruction->output pairs (Alpaca format) + a "type" tag.
  3. This script validates and writes data/train.jsonl.

The dataset format follows docs/answering-guide.md:
  - calculation : formula -> substitution -> result -> interpretation
  - concept     : definition -> points -> examples
  - case        : judgement -> evidence -> recommendation
  - essay       : definition-led, numbered sections, citations

Usage:
  python build_dataset.py                 # build from raw/*.md/.txt and append manual pairs
  python build_dataset.py --validate      # only validate existing train.jsonl
"""
import argparse
import glob
import json
import os
import sys

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw")
OUT = os.path.join(os.path.dirname(__file__), "train.jsonl")

# Manually curated pairs can be appended here as Python dicts.
# Keep answers format-compliant per docs/answering-guide.md.
MANUAL_PAIRS = [
    # {
    #     "instruction": "Compute the prime cost and conversion cost...",
    #     "input": "",
    #     "output": "Prime Cost = Direct Materials + Direct Labour = ...",
    #     "type": "calculation",
    # },
]

SUPPORTED_TYPES = {"calculation", "concept", "case", "essay"}


def read_raw_files():
    """Load cleaned text sources from data/raw/."""
    texts = []
    for pattern in ("*.md", "*.txt"):
        for path in sorted(glob.glob(os.path.join(RAW_DIR, pattern))):
            with open(path, encoding="utf-8") as f:
                texts.append({"file": os.path.basename(path), "content": f.read()})
    return texts


def validate(pairs):
    """Check every pair is well-formed and type-tagged."""
    errors = []
    for i, p in enumerate(pairs):
        if not all(k in p for k in ("instruction", "output", "type")):
            errors.append(f"line {i}: missing required key")
        if p.get("type") not in SUPPORTED_TYPES:
            errors.append(f"line {i}: unknown type '{p.get('type')}'")
        if not str(p.get("instruction", "")).strip():
            errors.append(f"line {i}: empty instruction")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true", help="only validate existing train.jsonl")
    args = parser.parse_args()

    if args.validate:
        with open(OUT, encoding="utf-8") as f:
            pairs = [json.loads(line) for line in f if line.strip()]
        errs = validate(pairs)
        if errs:
            print("VALIDATION FAILED:")
            for e in errs:
                print(" -", e)
            sys.exit(1)
        print(f"OK: {len(pairs)} valid pairs in {OUT}")
        return

    raw = read_raw_files()
    print(f"Found {len(raw)} raw source file(s) in {RAW_DIR}.")
    for r in raw:
        print("  -", r["file"])

    pairs = list(MANUAL_PAIRS)
    # TODO: convert each raw source into pairs (rule-based or reviewed manually).
    # At minimum, keep the manually curated pairs so the repo ships valid data.
    errs = validate(pairs)
    if errs:
        print("VALIDATION FAILED (fix MANUAL_PAIRS):")
        for e in errs:
            print(" -", e)
        sys.exit(1)

    with open(OUT, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"Wrote {len(pairs)} pairs to {OUT}")


if __name__ == "__main__":
    main()
