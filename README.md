# Business Admin Answer Helper (BAH)

A fine-tuned open-source LLM that answers **business administration coursework** the way a high-scoring UPM business student would — with the correct answering format, full calculation steps, business interpretation, and proper citations.

Built by distilling real assignment briefs, completed coursework, and tutorial questions into an instruction dataset, then fine-tuning an open-source base model (Qwen / DeepSeek / Llama) with LoRA.

> **Philosophy**: This project does not just "write answers" — it teaches the *format* and *reasoning pattern* that business-school markers reward: formula → substitution → result → business meaning, clear judgements with evidence, local Malaysian sources, and Harvard-style references.

---

## Why this project exists

Business-school assignments lose marks not because the student lacks ideas, but because the **answering format** is wrong. This project captures the answering conventions observed across real UPM coursework (Accounting ACN3101, Business Analytics MGM3165, HRM, Franchising, Commercial Law, Marketing) and bakes them into an open model, so anyone can get a *format-correct, high-scoring first draft* in one pass.

## What it can do

| Capability | Example |
|---|---|
| Calculation questions | Break-even, CVP, job costing, equivalent units, ratios — with full workings |
| Concept & essay questions | Define → distinguish → discuss, numbered structure, business interpretation |
| Case analysis | Clear judgement (should/should not) + evidence + recommendation |
| Report structure | Cover page → sections → conclusion → references (Harvard style) |

## Repository structure

```
business-admin-answer-helper/
├── README.md              # This file
├── LICENSE                # Apache-2.0
├── docs/
│   ├── answering-guide.md # The answering-format specification (core asset)
│   └── TRAINING_GUIDE.md  # Full training/evaluate/publish runbook
├── data/
│   ├── train.jsonl        # Instruction dataset (question → high-score answer)
│   ├── build_dataset.py   # Script to build train.jsonl from raw materials
│   ├── generate_dataset.py# Parameterised generators + hand-written banks
│   ├── gen_advanced.py    # Advanced accounting/analytics generators
│   └── raw/               # Cleaned, copyright-safe raw materials only
├── configs/
│   └── lora.yaml          # LoRA fine-tuning config (LLaMA-Factory)
├── notebooks/
│   └── finetune_qwen25_colab.ipynb  # One-click fine-tune on free Colab T4
├── scripts/
│   ├── prepare_dataset.py # Validate + stratified train/val split (no torch needed)
│   ├── train_lora.py      # Standard LoRA/QLoRA SFT (transformers + peft + trl)
│   ├── evaluate.py        # Evaluate format adherence + calculation accuracy
│   └── serve.py           # Local Gradio demo
├── examples/
│   └── in-out-pairs.md    # Input → output examples for humans
└── .gitignore
```

## Dataset format

`data/train.jsonl` uses the Alpaca instruction format with a `type` tag:

```json
{"instruction": "Calculate the break-even point in units and sales value for Bersatu Limited. Selling price RM1.50/unit, variable cost RM0.75/unit, fixed costs RM15,000.",
 "input": "",
 "output": "Break-even (units) = Fixed Costs ÷ Contribution Margin per unit = 15,000 ÷ (1.50 − 0.75) = 15,000 ÷ 0.75 = 20,000 units. Break-even (sales) = 20,000 × RM1.50 = RM30,000. Interpretation: at 20,000 units revenue exactly covers costs; below that the company makes a loss.",
 "type": "calculation"}
```

## Quick start

> 📖 **Full runbook**: see [`docs/TRAINING_GUIDE.md`](docs/TRAINING_GUIDE.md) for the
> complete train → evaluate → publish workflow, parameter suggestions and FAQ.

### Recommended: fine-tune on free Colab (T4 GPU)

1. Open [`notebooks/finetune_qwen25_colab.ipynb`](notebooks/finetune_qwen25_colab.ipynb) in Google Colab
2. Runtime → Change runtime type → **T4 GPU**
3. Run the cells top to bottom (~25–40 min): installs deps, downloads `train.jsonl` from this repo, loads Qwen2.5-7B in 4-bit (QLoRA), trains 3 epochs, merges the adapter, and lets you test the model inline
4. Optionally push the merged weights to Hugging Face (weights are too large for GitHub)

### Alternative: train locally / on any GPU

```bash
pip install -U torch transformers peft trl datasets accelerate bitsandbytes

# full QLoRA run
python scripts/prepare_dataset.py
python scripts/train_lora.py \
    --model_name Qwen/Qwen2.5-7B-Instruct \
    --data data/train.jsonl --output_dir outputs/business-admin-answer-helper \
    --epochs 3 --lr 2e-4 --batch_size 2 --grad_accum 8 --use_4bit

# 1-step smoke test (no GPU needed) to verify the pipeline
python scripts/train_lora.py --smoke --model_name Qwen/Qwen2.5-0.5B-Instruct
```

### Evaluate

```bash
python scripts/evaluate.py --model path/to/adapter --test data/train.jsonl
```

### Run the demo

```bash
python scripts/serve.py --model path/to/adapter
```

## Model weights

Fine-tuned model weights are published on Hugging Face: **[link to be added after training]**

## Roadmap

- [x] Repository skeleton + answering-format spec
- [x] Instruction dataset — **444 high-quality pairs** (326 calculation, 53 concept, 37 case, 28 essay). Coverage: CVP, cost & financial ratios, statistics, cost classification, flexible budgets, cost-of-goods-manufactured schedules, weighted-average process costing, job costing, multi-product CVP, contribution-format statements, efficiency/return ratios, **Malaysia-context cases** (NSRF, Bursa Malaysia, Maybank, MASB, BNM, local brands). All calculation answers are machine-computed and independently re-verified
- [x] Training pipeline — `scripts/prepare_dataset.py` + `scripts/train_lora.py` + `notebooks/finetune_qwen25_colab.ipynb` (verified data pipeline & 1-step smoke run)
- [ ] Fine-tune Qwen2.5-7B with LoRA on GPU
- [ ] Evaluation report (format adherence + calculation accuracy)
- [ ] Publish weights on Hugging Face
- [ ] Multi-course question bank

## License

Apache-2.0. See [LICENSE](LICENSE).

## Disclaimer & data provenance

- The dataset is built from **openly described answering conventions** and **original example solutions** written for this project. It does **not** include copyrighted textbook content, university-internal materials, or personal information.
- The model is a writing **assistant**. Users are responsible for complying with their institution's academic-integrity policies and for verifying numbers, citations, and facts before submission.
