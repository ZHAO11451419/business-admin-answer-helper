# -*- coding: utf-8 -*-
"""
数据扩充：在现有 444 对的基础上扩充到 ~1500 对，重点补齐算术短板。

策略：
  1. 复用 generate_dataset / gen_advanced 的参数化生成器，用新随机种子
     批量生成数值变体（同样的题型、全新的数字组合）；
  2. 新增 gen_arith 算术强化生成器（纯除法 / 小数比率 / 复合运算 / 百分比），
     专门针对 3B 模型的除法、小数运算短板；
  3. 保留原有 444 对（含概念/论述题），合并后按 instruction 去重。

用法：
  python data/augment_dataset.py        # 写入 data/train.jsonl（扩充版）
"""
import json
import os
import random
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(__file__))

import generate_dataset as gd          # gen_cvp / gen_ratio / gen_cost / gen_stats / gen_case
import gen_advanced as ga              # gen_* / generate_advanced

COMPANY_POOL = gd.COMPANIES


def rmc(rng):
    return rng.choice(COMPANY_POOL)


def rint(rng, a, b, step=1):
    return rng.randrange(a, b + 1, step)


def fmt_money(v):
    """RM 千分位整数或保留两位小数。"""
    f = float(v)
    if f == int(f):
        return f"{int(f):,}"
    return f"{f:,.2f}"


def fmt_num(v):
    """普通数字：千分位整数或保留两位小数。"""
    f = float(v)
    if f == int(f):
        return f"{int(f):,}"
    return f"{f:.2f}"


# --------------------------------------------------------------------------
# 算术强化生成器（针对除法 / 小数 / 复合运算短板）
# --------------------------------------------------------------------------
def gen_arith(rng):
    mode = rng.choice(["div_int", "div_ratio", "combo", "mul_div", "percent"])
    company = rmc(rng)

    if mode == "div_int":  # 纯除法：总成本 ÷ 期间
        period = rng.choice([6, 8, 10, 12, 15, 20, 24])
        per = rint(rng, 500, 20000, 500)
        total = period * per
        what = rng.choice(["monthly rent", "total salaries", "annual electricity cost",
                           "total maintenance cost", "total insurance premium"])
        q = (f"{company} incurred {what} of RM{total:,} over {period} months. "
             f"Calculate the average monthly {what.split()[-1] if ' ' in what else 'cost'}.")
        ans = (f"Step 1: Average monthly cost = Total cost ÷ Number of months "
               f"= RM{total:,} ÷ {period} = RM{per:,}. "
               f"Interpretation: the company spends RM{per:,} per month on average.")
        return {"type": "calculation", "instruction": q, "output": ans}

    if mode == "div_ratio":  # 小数比率：current/quick ratio 类
        ratio = rng.choice([1.2, 1.35, 1.5, 1.6, 1.75, 2.0, 2.25, 2.5])
        liab = rint(rng, 15000, 60000, 5000)
        asset = int(round(liab * ratio / 100) * 100)  # 构造：保证两位小数结果
        if asset <= liab:
            asset = liab + int(round(liab * 0.5 / 100) * 100)
        r = Fraction(asset, liab)
        ratio_str = f"{float(r):.2f}"
        q = (f"{company} has current assets of RM{asset:,} and current liabilities of "
             f"RM{liab:,}. Calculate the current ratio.")
        ans = (f"Step 1: Current ratio = Current assets ÷ Current liabilities "
               f"= RM{asset:,} ÷ RM{liab:,} = {ratio_str} (or {ratio_str}:1). "
               f"Interpretation: for every RM1 of short-term liability, the company has "
               f"RM{ratio_str} of current assets available.")
        return {"type": "calculation", "instruction": q, "output": ans}

    if mode == "combo":  # 复合：(A + B) ÷ C 目标利润销量
        price = rng.choice([10, 12, 15, 18, 20, 25, 30])
        vc = rng.choice([4, 5, 6, 7.5, 8, 9, 10, 12, 15, 18])
        if vc >= price:
            vc = rng.choice([4, 5, 6, 7.5, 8])
        cm = Fraction(str(price)) - Fraction(str(vc))
        fc = rint(rng, 20000, 120000, 5000)
        target = rint(rng, 10000, 60000, 5000)
        units = (Fraction(fc) + Fraction(target)) / cm
        units_str = f"{int(units):,}" if units == int(units) else fmt_num(units)
        cm_str = str(cm) if cm == int(cm) else f"{float(cm):.2f}"
        q = (f"{company} sells at RM{price} per unit with variable cost RM{vc} per unit "
             f"and fixed costs of RM{fc:,}. Calculate the sales volume in units needed to "
             f"achieve a target profit of RM{target:,}.")
        ans = (f"Step 1: Contribution margin per unit = RM{price} − RM{vc} = RM{cm_str}. "
               f"Step 2: Required units = (Fixed costs + Target profit) ÷ CM per unit "
               f"= (RM{fc:,} + RM{target:,}) ÷ RM{cm_str} = {units_str} units. "
               f"Interpretation: the company must sell {units_str} units to earn the target profit.")
        return {"type": "calculation", "instruction": q, "output": ans}

    if mode == "mul_div":  # 乘除结合：总价 ÷ 数量
        units = rint(rng, 40, 500, 10)
        unit_price = rint(rng, 15, 200, 5)
        total = units * unit_price
        q = (f"{company} purchased {units} units of raw materials for a total of "
             f"RM{total:,}. Calculate the cost per unit.")
        ans = (f"Step 1: Cost per unit = Total cost ÷ Number of units "
               f"= RM{total:,} ÷ {units} = RM{unit_price:,}. "
               f"Interpretation: each unit costs RM{unit_price:,}.")
        return {"type": "calculation", "instruction": q, "output": ans}

    # percent：毛利率 / 净利率
    pct = rng.choice([20, 25, 30, 35, 40, 45, 50, 55])
    revenue = rint(rng, 100000, 900000, 10000)
    profit = int(round(revenue * pct / 100))
    kind = rng.choice(["gross profit", "net profit"])
    ratio_word = "Gross profit margin" if kind == "gross profit" else "Net profit margin"
    q = (f"{company} reported revenue of RM{revenue:,} and {kind} of RM{profit:,}. "
         f"Calculate the {ratio_word.lower()}.")
    ans = (f"Step 1: {ratio_word} = {kind.title()} ÷ Revenue × 100% "
           f"= RM{profit:,} ÷ RM{revenue:,} × 100% = {pct}%. "
           f"Interpretation: for every RM100 of revenue, RM{pct} remains as {kind}.")
    return {"type": "calculation", "instruction": q, "output": ans}


def main():
    parser = None
    if len(sys.argv) > 1:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "train.jsonl"))
        ap.add_argument("--seed", type=int, default=20260907)
        parser = ap
        args = parser.parse_args()
    else:
        class A:
            out = os.path.join(os.path.dirname(__file__), "train.jsonl")
            seed = 20260907
        args = A()

    # 1. 原数据
    orig_path = os.path.join(os.path.dirname(__file__), "train.jsonl")
    with open(orig_path, encoding="utf-8") as f:
        pairs = [json.loads(line) for line in f if line.strip()]
    print(f"Original: {len(pairs)} pairs")

    # 2. 数值变体（新种子）
    rng = random.Random(args.seed)
    new_pairs = []
    for _ in range(80):
        new_pairs.append(gd.gen_cvp(rng))
    for _ in range(80):
        new_pairs.append(gd.gen_ratio(rng))
    for _ in range(60):
        new_pairs.append(gd.gen_cost(rng))
    for _ in range(60):
        new_pairs.append(gd.gen_stats(rng))
    for _ in range(40):
        new_pairs.append(gd.gen_case(rng))
    # advanced 题型
    for _ in range(40):
        new_pairs.append(ga.gen_classification(rng))
    for _ in range(30):
        new_pairs.append(ga.gen_flexbudget(rng))
    for _ in range(25):
        new_pairs.append(ga.gen_cogm(rng))
    for _ in range(30):
        new_pairs.append(ga.gen_eu(rng))
    for _ in range(30):
        new_pairs.append(ga.gen_jobcost(rng))
    for _ in range(30):
        new_pairs.append(ga.gen_multicvp(rng))
    for _ in range(25):
        new_pairs.append(ga.gen_contribution(rng))
    for kind in ["inv", "recv", "quick", "roe", "roi"]:
        for _ in range(10):
            new_pairs.append(ga.gen_effratio(rng, kind))
    for kind in ["cov", "mode", "median", "range"]:
        for _ in range(10):
            new_pairs.append(ga.gen_stats2(rng, kind))
    # 算术强化（专项）
    for _ in range(500):
        new_pairs.append(gen_arith(rng))
    print(f"Generated new: {len(new_pairs)}")

    # 3. 合并 + 校验 + 去重
    merged = pairs + new_pairs
    seen = set()
    deduped = []
    for p in merged:
        if p["instruction"] not in seen:
            seen.add(p["instruction"])
            deduped.append(p)
    dropped = len(merged) - len(deduped)

    # 4. 算术质量门：剔除表达式与答案不自洽的计算题（防旧生成器错误固化）
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)
    from scripts.calc_assist import fix_arithmetic
    qc_dropped = 0
    kept = []
    for p in deduped:
        if p["type"] == "calculation":
            _, corr = fix_arithmetic(p["output"])
            if corr:
                qc_dropped += 1
                continue
        kept.append(p)
    deduped = kept

    types = {}
    for p in deduped:
        assert p["type"] in {"calculation", "concept", "case", "essay"}
        assert p["instruction"].strip() and p["output"].strip()
        types[p["type"]] = types.get(p["type"], 0) + 1

    with open(args.out, "w", encoding="utf-8") as f:
        for p in deduped:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"Deduplicated {dropped} duplicate(s); QC dropped {qc_dropped} inconsistent calculation(s)")
    print(f"Wrote {len(deduped)} pairs to {args.out}")
    for t, c in sorted(types.items()):
        print(f"  {t:12s}: {c}")


if __name__ == "__main__":
    main()
