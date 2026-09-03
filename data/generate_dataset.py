# -*- coding: utf-8 -*-
"""
Generate the full instruction dataset data/train.jsonl.

Sources:
  - question_bank.py  : hand-written concept + essay pairs
  - this module       : parameterised calculation / case generators whose answers
                        are COMPUTED at generation time, so numbers are correct.

Types produced: calculation, concept, case, essay (see docs/answering-guide.md).

Run:  python data/generate_dataset.py   (writes data/train.jsonl)
Check: python data/build_dataset.py --validate
"""
import json
import os
import random
import statistics
from question_bank import CONCEPTS, ESSAYS, LOCAL_CASES

random.seed(42)  # reproducible

COMPANIES = [
    "Bintang Jaya Sdn. Bhd.", "Cahaya Manufacturing", "Aman Sejahtera Enterprise",
    "Mutiara Food Industries", "Kembara Tech Solutions", "Seri Indah Bakery",
    "Tunas Gemilang Sdn. Bhd.", "Lembah Ria Trading", "Permai Craft Sdn. Bhd.",
    "Desa Harmoni Furniture", "Sinar Bestari Electronics", "Utara Dinamik Logistics",
    "Mekar Suria Sdn. Bhd.", "Cempaka Digital Sdn. Bhd.", "Rimbun Agro Products",
    "Bayu Permata Holdings",
]


def rmc(rng):
    return rng.choice(COMPANIES)


def rint(rng, a, b, step=1):
    return rng.randrange(a, b + 1, step)


# --------------------------------------------------------------------------
# 1. CVP calculations
# --------------------------------------------------------------------------
def gen_cvp(rng):
    price = rng.choice([8, 10, 12, 15, 18, 20, 25, 30, 40, 50])
    vc = rng.choice([p for p in [3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 18, 20] if p < price])
    cm = price - vc
    bep = rng.choice([2000, 3000, 4000, 5000, 6000, 8000, 10000, 12000, 15000, 20000])
    fc = cm * bep
    normal = int(round(bep * rng.choice([1.25, 1.4, 1.6, 1.8, 2.0])))
    company = rmc(rng)
    mode = rng.choice(["be_units", "be_both", "mos", "target"])

    if mode == "be_units":
        q = (f"{company} sells its product at RM{price} per unit with a variable cost of "
             f"RM{vc} per unit and total fixed costs of RM{fc:,}. Calculate the break-even point in units.")
        ans = (f"Step 1: Contribution margin per unit = Selling price − Variable cost "
               f"= RM{price} − RM{vc} = RM{cm}. Step 2: Break-even point (units) = Fixed costs ÷ CM per unit "
               f"= RM{fc:,} ÷ RM{cm} = {bep:,} units. Interpretation: the company must sell {bep:,} units "
               f"to cover all costs; below this level it makes a loss, and above it each unit contributes RM{cm} to profit.")
    elif mode == "be_both":
        q = (f"{company} sells its product at RM{price} per unit, variable cost is RM{vc} per unit, "
             f"and fixed costs are RM{fc:,}. Calculate the break-even point in units and in sales value.")
        ans = (f"Step 1: Contribution margin per unit = RM{price} − RM{vc} = RM{cm}. "
               f"Step 2: Break-even (units) = Fixed costs ÷ CM per unit = RM{fc:,} ÷ RM{cm} = {bep:,} units. "
               f"Step 3: Break-even (sales value) = {bep:,} × RM{price} = RM{bep * price:,}. "
               f"Interpretation: at {bep:,} units (RM{bep * price:,} of sales) revenue exactly covers total costs; "
               f"every additional unit contributes RM{cm} to profit.")
    elif mode == "mos":
        q = (f"{company} has normal sales of {normal:,} units. Selling price is RM{price}, variable cost is "
             f"RM{vc}, and fixed costs are RM{fc:,}. Compute the break-even point and the margin of safety in units and as a percentage.")
        mos = normal - bep
        pct = round(mos / normal * 100, 1)
        ans = (f"Step 1: CM per unit = RM{price} − RM{vc} = RM{cm}. Step 2: Break-even = RM{fc:,} ÷ RM{cm} = {bep:,} units. "
               f"Step 3: Margin of safety (units) = Normal sales − Break-even = {normal:,} − {bep:,} = {mos:,} units. "
               f"Step 4: Margin of safety (%) = ({mos:,} ÷ {normal:,}) × 100% = {pct}%. "
               f"Interpretation: sales can fall by {mos:,} units ({pct}%) before the company reaches break-even and starts making a loss; "
               f"this shows the company's profit cushion.")
    else:  # target
        tp = rng.choice([10000, 20000, 30000, 50000, 80000, 100000])
        tp_units = (fc + tp) / cm
        if tp_units != int(tp_units):
            fc = cm * bep
            tp_units = int(round((fc + tp) / cm))
        else:
            tp_units = int(tp_units)
        q = (f"{company} sells at RM{price} per unit, variable cost RM{vc} per unit, fixed costs RM{fc:,}. "
             f"How many units must be sold to achieve a target profit of RM{tp:,}?")
        ans = (f"Step 1: CM per unit = RM{price} − RM{vc} = RM{cm}. "
               f"Step 2: Units for target profit = (Fixed costs + Target profit) ÷ CM per unit = "
               f"(RM{fc:,} + RM{tp:,}) ÷ RM{cm} = RM{fc + tp:,} ÷ RM{cm} = {tp_units:,} units. "
               f"Interpretation: the company must sell {tp_units:,} units to earn RM{tp:,} profit; "
               f"each unit sold contributes RM{cm} toward covering fixed costs and building profit.")
    return {"instruction": q, "input": "", "output": ans, "type": "calculation"}


# --------------------------------------------------------------------------
# 2. Ratio calculations (profitability / liquidity / leverage)
# --------------------------------------------------------------------------
def gen_ratio(rng):
    revenue = rng.choice([100000, 150000, 200000, 250000, 300000, 400000, 500000, 800000, 1000000])
    gpm = rng.choice([0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70])
    gross = int(round(revenue * gpm))
    npm = rng.choice([0.10, 0.12, 0.15, 0.18, 0.20, 0.25, 0.30])
    net = int(round(revenue * npm))
    ca = rng.choice([20000, 30000, 40000, 50000, 60000, 80000, 100000])
    cl = rng.choice([15000, 20000, 25000, 30000, 40000, 50000])
    ta = rng.choice([150000, 200000, 250000, 300000, 400000, 500000])
    debt = rng.choice([60000, 80000, 100000, 120000, 150000, 200000])
    equity = max(ta - debt, 50000)
    company = rmc(rng)
    which = rng.choice(["gpm", "npm", "cr", "dr", "de"])

    if which == "gpm":
        gp_margin = round(gross / revenue * 100, 1)
        per_rm = round(gross / revenue, 2)
        q = (f"{company} has revenue of RM{revenue:,} and gross profit of RM{gross:,}. "
             f"Calculate the gross profit margin and interpret the result.")
        ans = (f"Gross Profit Margin = (Gross Profit ÷ Revenue) × 100% = (RM{gross:,} ÷ RM{revenue:,}) × 100% = {gp_margin}%. "
               f"Interpretation: for every RM1 of revenue, RM{per_rm:.2f} remains after "
               f"covering the direct cost of goods sold; this amount must cover operating expenses and then contribute to profit. "
               f"A higher margin indicates stronger pricing power or better control of production costs.")
    elif which == "npm":
        np_margin = round(net / revenue * 100, 1)
        q = (f"{company} reported revenue of RM{revenue:,} and net profit of RM{net:,}. "
             f"Calculate the net profit margin and explain what it means for the owner.")
        ans = (f"Net Profit Margin = (Net Profit ÷ Revenue) × 100% = (RM{net:,} ÷ RM{revenue:,}) × 100% = {np_margin}%. "
               f"Interpretation: of every RM1 of sales, RM{np_margin / 100:.2f} remains as profit after all expenses, "
               f"including operating costs, interest and tax. It shows how efficiently the company converts sales into profit, "
               f"and it is used to compare profitability with other firms in the same industry.")
    elif which == "cr":
        cr = round(ca / cl, 2)
        q = (f"{company} has current assets of RM{ca:,} and current liabilities of RM{cl:,}. "
             f"Calculate the current ratio and assess the company's short-term liquidity.")
        ans = (f"Current Ratio = Current Assets ÷ Current Liabilities = RM{ca:,} ÷ RM{cl:,} = {cr:.2f} (or {cr:.2f}:1). "
               f"Interpretation: the company has RM{cr:.2f} of current assets for every RM1.00 of short-term liability, "
               f"so it can cover its short-term obligations "
               f"{'with a comfortable cushion' if cr >= 1.5 else 'but with only a modest cushion'}."
               f" A ratio below 1.5 signals tight liquidity, so lenders would require further analysis of cash flow and inventory.")
    elif which == "dr":
        dr = round(debt / ta, 2)
        q = (f"{company} has total assets of RM{ta:,} and total debt of RM{debt:,}. "
             f"Calculate the debt ratio and comment on the company's financial leverage.")
        ans = (f"Debt Ratio = Total Debt ÷ Total Assets = RM{debt:,} ÷ RM{ta:,} = {dr:.2f} (or {dr * 100:.1f}%). "
               f"Interpretation: {dr * 100:.1f}% of the company's assets are financed by debt; "
               f"{'the company relies heavily on borrowing, which increases financial risk' if dr >= 0.6 else 'the company has a balanced mix of debt and equity financing'}. "
               f"Lenders use this ratio to judge the margin of safety before granting additional credit.")
    else:  # de
        de = round(debt / equity, 2)
        q = (f"{company} has total debt of RM{debt:,} and shareholders' equity of RM{equity:,}. "
             f"Calculate the debt-to-equity ratio and explain what it indicates.")
        ans = (f"Debt-to-Equity Ratio = Total Debt ÷ Total Equity = RM{debt:,} ÷ RM{equity:,} = {de:.2f}. "
               f"Interpretation: the company owes RM{de:.2f} of debt for every RM1.00 of equity, "
               f"indicating {'a high reliance on borrowed funds and elevated financial risk' if de > 1.0 else 'a conservative capital structure with lower financial risk'}. "
               f"Creditors prefer a lower ratio because equity provides a buffer against losses.")
    return {"instruction": q, "input": "", "output": ans, "type": "calculation"}


# --------------------------------------------------------------------------
# 3. Costing calculations
# --------------------------------------------------------------------------
def gen_cost(rng):
    dm = rng.choice([12000, 15000, 18000, 22000, 26000, 30000, 35000, 40000])
    dl = rng.choice([9000, 10000, 12000, 15000, 18000, 20000, 24000, 28000])
    moh = rng.choice([6000, 7000, 8000, 9000, 10000, 12000, 14000, 16000])
    units = rng.choice([1000, 1500, 2000, 2500, 3000, 4000, 5000])
    company = rmc(rng)
    which = rng.choice(["prime", "conv", "total", "unit", "mohrate"])

    if which == "prime":
        prime = dm + dl
        q = (f"{company} incurred direct materials of RM{dm:,}, direct labour of RM{dl:,} and manufacturing "
             f"overhead of RM{moh:,}. Calculate the prime cost.")
        ans = (f"Prime Cost = Direct Materials + Direct Labour = RM{dm:,} + RM{dl:,} = RM{prime:,}. "
               f"Interpretation: prime cost represents the direct inputs that can be traced to the product; "
               f"it excludes manufacturing overhead because overhead is an indirect cost.")
    elif which == "conv":
        conv = dl + moh
        q = (f"{company} reports direct materials of RM{dm:,}, direct labour of RM{dl:,} and manufacturing "
             f"overhead of RM{moh:,}. Calculate the conversion cost.")
        ans = (f"Conversion Cost = Direct Labour + Manufacturing Overhead = RM{dl:,} + RM{moh:,} = RM{conv:,}. "
               f"Interpretation: conversion cost is the cost of turning direct materials into finished goods; "
               f"it is central to process costing and equivalent-unit calculations.")
    elif which == "total":
        total = dm + dl + moh
        q = (f"{company} has direct materials of RM{dm:,}, direct labour of RM{dl:,} and manufacturing "
             f"overhead of RM{moh:,}. Compute the total manufacturing cost.")
        ans = (f"Total Manufacturing Cost = Direct Materials + Direct Labour + Manufacturing Overhead "
               f"= RM{dm:,} + RM{dl:,} + RM{moh:,} = RM{total:,}. "
               f"Interpretation: this is the full production cost incurred during the period before considering "
               f"beginning and ending work-in-process; it is used to value output and compute unit cost.")
    elif which == "unit":
        total = dm + dl + moh
        unit = round(total / units, 2)
        q = (f"{company} produced {units:,} units with direct materials of RM{dm:,}, direct labour of RM{dl:,} "
             f"and manufacturing overhead of RM{moh:,}. Calculate the manufacturing cost per unit.")
        ans = (f"Total manufacturing cost = RM{dm:,} + RM{dl:,} + RM{moh:,} = RM{total:,}. "
               f"Cost per unit = Total cost ÷ Units produced = RM{total:,} ÷ {units:,} = RM{unit:.2f}. "
               f"Interpretation: each unit carries RM{unit:.2f} of production cost; managers use this to set selling "
               f"prices and to monitor production efficiency.")
    else:  # mohrate
        bmoh = rng.choice([400000, 500000, 600000, 800000, 1000000, 1200000])
        bbase = rng.choice([20000, 25000, 32000, 40000, 50000])
        rate = bmoh // bbase
        bmoh = rate * bbase  # ensure integer rate
        abase = rng.choice([int(bbase * r) for r in [0.9, 0.95, 1.0, 1.05, 1.1] if int(bbase * r) > 0])
        amoh = rng.choice([int(bmoh * r) for r in [0.9, 0.95, 1.0, 1.05, 1.1]])
        alloc = rate * abase
        diff = amoh - alloc
        tag = "under-allocated" if diff > 0 else "over-allocated"
        q = (f"{company} budgeted manufacturing overhead of RM{bmoh:,} and {bbase:,} direct labour hours. "
             f"During the year the actual direct labour hours were {abase:,} and actual overhead was RM{amoh:,}. "
             f"Calculate the budgeted overhead rate, the overhead allocated, and state whether overhead is "
             f"under- or over-allocated.")
        ans = (f"Step 1: Budgeted overhead rate = Budgeted MOH ÷ Budgeted allocation base = RM{bmoh:,} ÷ {bbase:,} hours = RM{rate}/hour. "
               f"Step 2: Overhead allocated = Rate × Actual hours = RM{rate} × {abase:,} = RM{alloc:,}. "
               f"Step 3: Under- or over-allocation = Actual MOH − Allocated MOH = RM{amoh:,} − RM{alloc:,} = RM{abs(diff):,} {tag}. "
               f"Interpretation: because allocated overhead differs from actual, the difference is closed at year-end to cost of goods sold; "
               f"it arises from using a budgeted rate based on planned activity.")
    return {"instruction": q, "input": "", "output": ans, "type": "calculation"}


# --------------------------------------------------------------------------
# 4. Statistics calculations
# --------------------------------------------------------------------------
def gen_stats(rng):
    n = rng.choice([6, 7, 8, 9, 10])
    data = [rng.randint(10, 95) for _ in range(n)]
    company = rmc(rng)
    which = rng.choice(["mean", "med", "range", "var", "pct", "corr"])

    if which == "mean":
        m = round(statistics.mean(data), 1)
        q = (f"The weekly sales (in units) of {company} over {n} weeks were: {', '.join(map(str, data))}. "
             f"Calculate the mean sales per week.")
        ans = (f"Mean = Sum of values ÷ Number of values = ({' + '.join(map(str, data))}) ÷ {n} = {sum(data)} ÷ {n} = {m:.1f} units. "
               f"Interpretation: on average the company sells {m:.1f} units per week; the mean is used as a central "
               f"measure of typical weekly sales, though it can be influenced by extreme weeks.")
    elif which == "med":
        med = statistics.median(data)
        ds = ", ".join(map(str, sorted(data)))
        q = (f"The daily orders recorded by {company} were: {', '.join(map(str, data))}. "
             f"Calculate the median.")
        ans = (f"Step 1: Arrange the values in ascending order: {ds}. "
               f"Step 2: Since there are {n} values, the median is the middle value. "
               f"{('The median = value at position ' + str((n + 1) // 2) + ' = ' + str(med) + '.') if n % 2 == 1 else ('The median is the average of the two middle values, ' + str(sorted(data)[n//2 - 1]) + ' and ' + str(sorted(data)[n//2]) + ', so median = ' + str(med) + '.')} "
               f"Interpretation: half of the recorded orders fall below and half above {med:.0f}, "
               f"which makes the median a robust measure less affected by extreme values than the mean.")
    elif which == "range":
        rngv = max(data) - min(data)
        q = (f"{company} recorded these daily customer counts: {', '.join(map(str, data))}. "
             f"Calculate the range and explain what it indicates.")
        ans = (f"Range = Maximum value − Minimum value = {max(data)} − {min(data)} = {rngv}. "
               f"Interpretation: the range shows the spread between the highest and lowest daily customer counts "
               f"({rngv} customers); a large range indicates high variability, while a small range indicates stable demand.")
    elif which == "var":
        var = round(statistics.variance(data), 1)
        sd = round(statistics.stdev(data), 1)
        q = (f"The monthly production volumes of {company} were: {', '.join(map(str, data))}. "
             f"Calculate the sample variance and standard deviation.")
        ans = (f"Step 1: Mean = {sum(data)} ÷ {n} = {sum(data) / n:.1f}. "
               f"Step 2: Variance = Σ(x − mean)² ÷ (n − 1) = {var:.1f} (units²). "
               f"Step 3: Standard deviation = √Variance = {sd:.1f} units. "
               f"Interpretation: the standard deviation of {sd:.1f} units measures how much monthly production "
               f"typically deviates from the mean; a larger value means more volatile production, which affects "
               f"planning and inventory decisions.")
    elif which == "pct":
        p = rng.choice([25, 50, 75, 90])
        s = sorted(data)
        lp = p / 100 * (n + 1)
        lo = int(lp)
        frac = lp - lo
        if frac == 0:
            pv = s[lo - 1]
            method = f"Lp = p/100 × (n + 1) = {p}/100 × ({n} + 1) = {lp}. This is an integer, so the {p}th percentile is the value at position {lo}: {pv}."
        elif lo >= n:
            pv = s[n - 1]
            method = (f"Lp = p/100 × (n + 1) = {p}/100 × ({n} + 1) = {lp}. "
                      f"The computed position exceeds the largest observation, so P{p} is taken as the maximum value: {pv}.")
        else:
            pv = round(s[lo - 1] + frac * (s[lo] - s[lo - 1]), 1)
            method = (f"Lp = p/100 × (n + 1) = {p}/100 × ({n} + 1) = {lp}. "
                      f"The {p}th percentile lies between the {lo}th value ({s[lo - 1]}) and the {lo + 1}th value ({s[lo]}), "
                      f"so P{p} = {s[lo - 1]} + {frac:.1f} × ({s[lo]} − {s[lo - 1]}) = {pv}.")
        q = (f"{company} gathered these {n} sample observations: {', '.join(map(str, data))}. "
             f"Calculate the {p}th percentile using the formula Lp = p/100 × (n + 1).")
        ans = (f"Step 1: Arrange values in ascending order: {', '.join(map(str, s))}. "
               f"Step 2: {method} "
               f"Interpretation: {p}% of the observations fall at or below {pv}, which helps the company "
               f"set service or stocking targets that cover the required share of demand.")
    else:  # corr
        x = [rng.randint(1, 20) for _ in range(8)]
        direction = rng.choice([1, -1])
        y = [v * direction * rng.choice([1, 2]) + rng.randint(-4, 4) for v in x]
        mx = statistics.mean(x)
        my = statistics.mean(y)
        sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
        sx = (sum((a - mx) ** 2 for a in x) ** 0.5)
        sy = (sum((b - my) ** 2 for b in y) ** 0.5)
        r = sxy / (sx * sy) if sx and sy else 0
        r = round(r, 2)
        strength = ("strong" if abs(r) >= 0.7 else "moderate" if abs(r) >= 0.4 else "weak")
        rel = "positive" if r > 0 else "negative"
        q = (f"{company} recorded advertising spend (RM'000) and sales (units) over 8 months: "
             f"X = {x}, Y = {y}. Calculate the correlation coefficient and describe the relationship.")
        ans = (f"Step 1: Covariance Sxy = Σ(x − x̄)(y − ȳ) = {sxy:.2f}. "
               f"Step 2: Sx = {sx:.2f}, Sy = {sy:.2f}. "
               f"Step 3: r = Sxy ÷ (Sx × Sy) = {sxy:.2f} ÷ ({sx:.2f} × {sy:.2f}) = {r}. "
               f"Interpretation: r = {r} indicates a {strength} {rel} linear relationship between advertising spend and sales, "
               f"meaning {'higher advertising spend is associated with higher sales' if r > 0 else 'the variables move in opposite directions'}; "
               f"correlation does not prove causation.")
    return {"instruction": q, "input": "", "output": ans, "type": "calculation"}


# --------------------------------------------------------------------------
# 5. Case: loan decision (financial health check)
# --------------------------------------------------------------------------
def gen_case(rng):
    ca = rng.choice([20000, 25000, 30000, 40000, 50000])
    cl = rng.choice([18000, 20000, 25000, 30000, 35000])
    ta = rng.choice([80000, 100000, 120000, 150000, 180000])
    debt = rng.choice([45000, 55000, 65000, 75000, 90000])
    loan = rng.choice([30000, 40000, 50000, 60000])
    company = rmc(rng)
    cr = round(ca / cl, 2)
    dr = round((debt + loan) / ta, 2)

    if cr < 1.2 or dr > 0.6:
        decision = ("should not proceed")
        reasons = (
            f"(1) the current ratio of {cr} leaves little cushion for servicing an additional loan, "
            f"(2) adding RM{loan:,} of new debt would push the debt ratio to {dr * 100:.0f}%, increasing default risk, and "
            f"(3) the business should first strengthen liquidity and cash flow before taking on expansion debt"
        )
    else:
        decision = ("should proceed")
        reasons = (
            f"(1) the current ratio of {cr} indicates the business can cover short-term obligations even after the loan, "
            f"(2) the post-loan debt ratio of {dr * 100:.0f}% remains within a manageable range, and "
            f"(3) the loan is expected to fund expansion that raises future cash flow, provided the owner keeps tight control of expenses"
        )
    q = (f"{company} is a small business applying for a loan of RM{loan:,} to expand. Its latest figures are: "
         f"current assets RM{ca:,}, current liabilities RM{cl:,}, total assets RM{ta:,}, total debt RM{debt:,}. "
         f"Compute the current ratio, estimate the debt ratio if the loan is granted, and advise whether the loan should be approved.")
    ans = (f"Step 1: Current ratio = Current assets ÷ Current liabilities = RM{ca:,} ÷ RM{cl:,} = {cr} (or {cr}:1). "
           f"Step 2: Estimated debt ratio after the loan = (Total debt + Loan) ÷ Total assets = (RM{debt:,} + RM{loan:,}) ÷ RM{ta:,} = {dr * 100:.0f}%. "
           f"Step 3: Advice. On balance, the loan {decision} as requested, because {reasons}. "
           f"Recommendation: {('the bank should first require stronger liquidity and a business plan before approving any credit' if 'should not' in decision else 'the owner should monitor the new debt closely and prepare a repayment cash-flow plan')}.")
    return {"instruction": q, "input": "", "output": ans, "type": "case"}


# --------------------------------------------------------------------------
def main():
    rng = random.Random(42)
    pairs = []

    # Hand-written concept + essay + local-case banks
    pairs += CONCEPTS
    pairs += ESSAYS
    pairs += LOCAL_CASES

    # Parameterised generators
    for _ in range(60):
        pairs.append(gen_cvp(rng))
    for _ in range(60):
        pairs.append(gen_ratio(rng))
    for _ in range(50):
        pairs.append(gen_cost(rng))
    for _ in range(45):
        pairs.append(gen_stats(rng))
    for _ in range(30):
        pairs.append(gen_case(rng))

    # Validate all pairs
    types = {}
    for p in pairs:
        types[p["type"]] = types.get(p["type"], 0) + 1
        assert p["type"] in {"calculation", "concept", "case", "essay"}, p["type"]
        assert p["instruction"].strip() and p["output"].strip()

    out = os.path.join(os.path.dirname(__file__), "train.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"Wrote {len(pairs)} pairs to {out}")
    for t, c in sorted(types.items()):
        print(f"  {t:12s}: {c}")


if __name__ == "__main__":
    main()
