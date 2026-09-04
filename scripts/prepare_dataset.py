# -*- coding: utf-8 -*-
"""
Prepare & validate the instruction dataset for SFT.

- Reads data/train.jsonl (445 pairs: calculation / concept / case / essay)
- Validates schema and reports type distribution + token-size estimate
- Splits into train / validation (stratified, seed=42) and writes:
    data/train_prepared.jsonl, data/val_prepared.jsonl
  where each line has {"type", "instruction", "input", "output"} (input kept
  for legacy fields; training pipeline formats with the Qwen chat template).

Pure standard library — no torch required.

Usage:
  python scripts/prepare_dataset.py
"""
import argparse
import json
import os
import random

# Rough token estimate: ~1 token per 0.6 English word (4 chars per token)
def est_tokens(text):
    return max(1, int(len(text) / 4))


def load_pairs(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def validate(pairs):
    errors = []
    seen = set()
    for i, p in enumerate(pairs):
        if not isinstance(p.get("instruction"), str) or not p["instruction"].strip():
            errors.append(f"line {i}: empty instruction")
        if not isinstance(p.get("output"), str) or not p["output"].strip():
            errors.append(f"line {i}: empty output")
        t = p.get("type")
        if t not in {"calculation", "concept", "case", "essay"}:
            errors.append(f"line {i}: bad type {t!r}")
        key = p["instruction"]
        if key in seen:
            errors.append(f"line {i}: exact duplicate instruction {key[:80]!r}")
        seen.add(key)
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/train.jsonl")
    parser.add_argument("--val-size", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", default="data")
    args = parser.parse_args()

    pairs = load_pairs(args.data)
    print(f"Loaded {len(pairs)} pairs from {args.data}")

    errors = validate(pairs)
    if errors:
        print("VALIDATION FAILED:")
        for e in errors[:20]:
            print("  -", e)
        raise SystemExit(1)
    print("Schema validation: OK")

    # type distribution
    dist = {}
    for p in pairs:
        dist[p["type"]] = dist.get(p["type"], 0) + 1
    print("Type distribution:", dict(sorted(dist.items())))

    # token-size estimate
    lens = [est_tokens(p["instruction"]) + est_tokens(p["output"]) for p in pairs]
    lens.sort()
    print(f"Estimated seq length: min={lens[0]}, p50={lens[len(lens)//2]}, "
          f"p90={lens[int(len(lens)*0.9)]}, max={lens[-1]}")

    # stratified split
    rng = random.Random(args.seed)
    train, val = [], []
    by_type = {}
    for p in pairs:
        by_type.setdefault(p["type"], []).append(p)
    for t, items in by_type.items():
        rng.shuffle(items)
        n_val = max(1, round(len(items) * args.val_size))
        val.extend(items[:n_val])
        train.extend(items[n_val:])
    rng.shuffle(train)
    rng.shuffle(val)

    os.makedirs(args.out_dir, exist_ok=True)
    tr_path = os.path.join(args.out_dir, "train_prepared.jsonl")
    va_path = os.path.join(args.out_dir, "val_prepared.jsonl")
    with open(tr_path, "w", encoding="utf-8") as f:
        for p in train:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    with open(va_path, "w", encoding="utf-8") as f:
        for p in val:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"Wrote {len(train)} train / {len(val)} val pairs")
    print(f"  train -> {tr_path}")
    print(f"  val   -> {va_path}")
    vdist = {}
    for p in val:
        vdist[p["type"]] = vdist.get(p["type"], 0) + 1
    print("Val type distribution:", dict(sorted(vdist.items())))


if __name__ == "__main__":
    main()
