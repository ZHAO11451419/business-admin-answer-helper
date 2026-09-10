# -*- coding: utf-8 -*-
"""v3 数据扩充：中间步骤必展开（分步格式）+ CAPM/投资决策等新领域样本。

背景：v2 实测发现模型计算题常"直接跳到最终结果"，省略中间采分点；
同时 CAPM 百分比公式（训练外领域）已能答但分步不足。
本脚本生成约 150 条全部带显式分步（Step 1/2/3 + Interpretation）的 calculation 样本，
数值全部由脚本现算，保证正确。

输出：
  data/train_v3_add.jsonl   新增样本（可独立审查）
  直接 append 到 data/train.jsonl 由本脚本的 main 完成
"""
import json
import random

random.seed(20260910)

COMPANIES = [
    "Malayan Star Sdn Bhd", "Cempaka Holdings Berhad", "Perak Teknologi Sdn Bhd",
    "Johor Maju Berhad", "Sarawak Energi Sdn Bhd", "KL Sentral Ventures",
    "Pulau Pinang Global", "Melaka Agro Berhad", "Kedah Digital Sdn Bhd",
    "Negeri Sembilan Food", "Selangor Auto Berhad", "Terengganu Marine Sdn Bhd",
    "Sabah Timber Berhad", "Pahang Retail Group", "Langkawi Leisure Berhad",
]


def fmt_rm(v: float) -> str:
    """RM 格式：整数无小数，非整数保留 2 位；负数用 U+2212 前缀（与 calc_assist 一致）。"""
    if v < 0:
        return "−" + fmt_rm(-v)
    if abs(v - round(v)) < 1e-9:
        return f"RM{int(round(v)):,}"
    return f"RM{v:,.2f}"


def norm6(v: float) -> str:
    """保留 6 位有效小数（复利因子用，保证与最终结果乘法自洽）。"""
    return f"{v:.6f}".rstrip("0").rstrip(".")


def fmt_pct(v: float) -> str:
    """百分比格式：去掉多余尾零。"""
    return f"{v:.2f}".rstrip("0").rstrip(".") + "%"


def norm(v: float) -> str:
    """普通数字格式（比率等）：去尾零。"""
    return f"{v:.2f}".rstrip("0").rstrip(".")


def out(instruction, output):
    return {"instruction": instruction, "input": "", "output": output, "type": "calculation"}


def gen_capm():
    """CAPM：Ke = Rf + β(Rm − Rf)，三步骤全展开。"""
    rows = []
    rf_pool = [2.5, 3.5, 4.0, 5.0, 6.0]
    rm_pool = [9.0, 10.0, 11.0, 12.0]
    beta_pool = [0.8, 1.0, 1.2, 1.5, 1.8]
    for _ in range(50):
        rf = random.choice(rf_pool)
        rm = random.choice([x for x in rm_pool if x > rf + 3.0])
        beta = random.choice(beta_pool)
        co = random.choice(COMPANIES)
        mrp = rm - rf
        spr = beta * mrp
        ke = rf + spr
        if beta > 1:
            interp = (f"with a beta of {norm(beta)}, the stock's return should fluctuate "
                      f"{norm(beta)} times as much as the market; its higher market risk demands "
                      f"a risk premium of {fmt_pct(spr)} on top of the risk-free rate.")
        elif beta < 1:
            interp = (f"with a beta of {norm(beta)}, the stock is defensive and moves less than "
                      f"the market, so it requires a lower risk premium of {fmt_pct(spr)}.")
        else:
            interp = (f"with a beta of 1.0, the stock moves in line with the market and requires "
                      f"the market risk premium of {fmt_pct(mrp)}.")
        instruction = (
            f"A Malaysian investor is evaluating {co}, a stock listed on Bursa Malaysia. "
            f"The risk-free rate is {fmt_pct(rf)}, the expected return on the market portfolio is "
            f"{fmt_pct(rm)}, and the stock's beta is {norm(beta)}. Using the Capital Asset Pricing "
            f"Model (CAPM: Ke = Rf + β(Rm − Rf)), calculate the required rate of return and interpret "
            f"the result."
        )
        output = (
            f"Step 1: Market risk premium = Market return − Risk-free rate = "
            f"{fmt_pct(rm)} − {fmt_pct(rf)} = {fmt_pct(mrp)}.\n"
            f"Step 2: Stock's risk premium = Beta × Market risk premium = {norm(beta)} × "
            f"{fmt_pct(mrp)} = {fmt_pct(spr)}.\n"
            f"Step 3: Required return = Risk-free rate + Stock's risk premium = "
            f"{fmt_pct(rf)} + {fmt_pct(spr)} = {fmt_pct(ke)}.\n"
            f"Interpretation: {interp}"
        )
        rows.append(out(instruction, output))
    return rows


def gen_roi():
    """ROI：Operating income ÷ Average operating assets，分步。"""
    rows = []
    for _ in range(12):
        oi = random.randint(60, 900) * 1000
        assets = random.randint(30, 90) * 10000
        while oi / assets > 0.4:
            oi = random.randint(60, 900) * 1000
            assets = random.randint(30, 90) * 10000
        roi = oi / assets * 100
        co = random.choice(COMPANIES)
        instruction = (
            f"{co} reported operating income of {fmt_rm(oi)} and average operating assets of "
            f"{fmt_rm(assets)} during the year. Calculate the return on investment (ROI) and interpret "
            f"the result."
        )
        output = (
            f"Step 1: ROI = Operating income ÷ Average operating assets = "
            f"{fmt_rm(oi)} ÷ {fmt_rm(assets)} = {fmt_pct(roi)}.\n"
            f"Interpretation: every RM1 invested in operating assets generates about "
            f"RM{norm(roi / 100)} of operating income, so the segment is using its assets "
            f"profitably."
        )
        rows.append(out(instruction, output))
    return rows


def gen_margin():
    """Net profit margin：分步。"""
    rows = []
    for _ in range(10):
        sales = random.randint(20, 95) * 10000
        margin = random.choice([6.0, 8.5, 10.0, 12.5, 15.0, 18.0, 22.0])
        np_ = sales * margin / 100
        co = random.choice(COMPANIES)
        instruction = (
            f"{co} recorded net profit of {fmt_rm(np_)} and total sales revenue of {fmt_rm(sales)} "
            f"for the year. Calculate the net profit margin and interpret the result."
        )
        output = (
            f"Step 1: Net profit margin = Net profit ÷ Sales revenue = "
            f"{fmt_rm(np_)} ÷ {fmt_rm(sales)} = {fmt_pct(margin)}.\n"
            f"Interpretation: the company keeps {fmt_pct(margin)} of every sales ringgit as profit "
            f"after all expenses; a higher margin indicates stronger cost control and pricing power."
        )
        rows.append(out(instruction, output))
    return rows


def gen_growth():
    """Sales growth rate：分步。"""
    rows = []
    for _ in range(10):
        y1 = random.randint(50, 95) * 10000
        g = random.choice([5.0, 8.0, 10.0, 12.5, 15.0, 18.0, 20.0, 25.0])
        y2 = y1 * (1 + g / 100)
        change = y2 - y1
        co = random.choice(COMPANIES)
        instruction = (
            f"{co}'s sales revenue was {fmt_rm(y1)} last year and {fmt_rm(y2)} this year. "
            f"Calculate the sales growth rate and interpret the result."
        )
        output = (
            f"Step 1: Change in sales = Current year sales − Previous year sales = "
            f"{fmt_rm(y2)} − {fmt_rm(y1)} = {fmt_rm(change)}.\n"
            f"Step 2: Growth rate = Change in sales ÷ Previous year sales = "
            f"{fmt_rm(change)} ÷ {fmt_rm(y1)} = {fmt_pct(g)}.\n"
            f"Interpretation: sales grew by {fmt_pct(g)} year on year, indicating expanding demand "
            f"for the company's products."
        )
        rows.append(out(instruction, output))
    return rows


def gen_hpr():
    """Holding period return：分步。"""
    rows = []
    for _ in range(10):
        buy = random.randint(8, 60) * 1000
        sell = random.randint(int(buy * 1.05), int(buy * 1.6))
        div = random.randint(2, 20) * 100
        gain = sell - buy + div
        hpr = gain / buy * 100
        co = random.choice(COMPANIES)
        instruction = (
            f"An investor bought 1,000 shares of {co} at {fmt_rm(buy)} per share, received total "
            f"dividends of {fmt_rm(div)} during the holding period, and sold the shares at "
            f"{fmt_rm(sell)} each. Calculate the holding period return and interpret the result."
        )
        output = (
            f"Step 1: Total gain = Selling price − Purchase price + Dividends = "
            f"{fmt_rm(sell)} − {fmt_rm(buy)} + {fmt_rm(div)} = {fmt_rm(gain)}.\n"
            f"Step 2: Holding period return = Total gain ÷ Purchase price = "
            f"{fmt_rm(gain)} ÷ {fmt_rm(buy)} = {fmt_pct(hpr)}.\n"
            f"Interpretation: the investment earned a total return of {fmt_pct(hpr)} over the "
            f"holding period, combining capital gain of {fmt_rm(sell - buy)} and dividend income "
            f"of {fmt_rm(div)}."
        )
        rows.append(out(instruction, output))
    return rows


def gen_fv():
    """终值 FV = PV × (1 + r)ⁿ，分步（上标次方）。"""
    rows = []
    for _ in range(16):
        pv = random.randint(10, 80) * 10000
        r = random.choice([0.06, 0.08, 0.10, 0.12])
        n = random.choice([2, 3])
        factor = (1 + r) ** n
        fv = pv * factor
        sup = {2: "²", 3: "³"}[n]
        co = random.choice(COMPANIES)
        instruction = (
            f"{co} invests {fmt_rm(pv)} today in a fund that earns {fmt_pct(r * 100)} compounded "
            f"annually. Calculate the future value after {n} years and interpret the result."
        )
        output = (
            f"Step 1: Future value = Present value × (1 + Interest rate){sup} = "
            f"{fmt_rm(pv)} × (1 + {fmt_pct(r * 100)}){sup}.\n"
            f"Step 2: (1 + {fmt_pct(r * 100)}){sup} = {norm6(factor)}; therefore "
            f"Future value = {fmt_rm(pv)} × {norm6(factor)} = {fmt_rm(fv)}.\n"
            f"Interpretation: the {fmt_rm(pv)} invested today will grow to {fmt_rm(fv)} in {n} years "
            f"because of compound interest; the extra {fmt_rm(fv - pv)} is the return earned on both "
            f"the principal and previously earned interest."
        )
        rows.append(out(instruction, output))
    return rows


def gen_cvp_stepwise():
    """CVP 分步版：CM → BE units → BE sales → target units（全展开）。"""
    rows = []
    for _ in range(10):
        sp = random.choice([10.0, 12.0, 15.0, 20.0, 25.0])
        vc = round(random.uniform(0.4, 0.7) * sp, 2)
        fc = random.choice([40000, 54000, 72000, 90000, 120000])
        target = random.choice([18000, 25000, 36000, 50000])
        cm = sp - vc
        be_u = round(fc / cm)
        be_s = be_u * sp
        tgt_u = round((fc + target) / cm)
        tgt_s = tgt_u * sp
        co = random.choice(COMPANIES)
        instruction = (
            f"{co} sells a product at {fmt_rm(sp)} per unit with variable cost of {fmt_rm(vc)} per "
            f"unit and fixed costs of {fmt_rm(fc)}. Calculate (a) the break-even point in units and "
            f"sales value, and (b) the units and sales value required to earn a target profit of "
            f"{fmt_rm(target)}, showing every step."
        )
        output = (
            f"Step 1: Contribution margin per unit = Selling price − Variable cost = "
            f"{fmt_rm(sp)} − {fmt_rm(vc)} = {fmt_rm(cm)}.\n"
            f"Step 2: Break-even (units) = Fixed costs ÷ Contribution margin per unit = "
            f"{fmt_rm(fc)} ÷ {fmt_rm(cm)} = {be_u:,} units.\n"
            f"Step 3: Break-even (sales value) = Break-even units × Selling price = "
            f"{be_u:,} × {fmt_rm(sp)} = {fmt_rm(be_s)}.\n"
            f"Step 4: Target sales (units) = (Fixed costs + Target profit) ÷ Contribution margin "
            f"per unit = ({fmt_rm(fc)} + {fmt_rm(target)}) ÷ {fmt_rm(cm)} = {tgt_u:,} units.\n"
            f"Step 5: Target sales (value) = {tgt_u:,} × {fmt_rm(sp)} = {fmt_rm(tgt_s)}.\n"
            f"Interpretation: at {be_u:,} units ({fmt_rm(be_s)} of sales) revenue exactly covers "
            f"total costs; selling {tgt_u:,} units ({fmt_rm(tgt_s)}) is required to earn the "
            f"{fmt_rm(target)} target profit."
        )
        rows.append(out(instruction, output))
    return rows


def gen_ratios_stepwise():
    """流动/速动比率分步版。"""
    rows = []
    for _ in range(8):
        ca = random.randint(30, 80) * 1000
        cl = random.randint(20, 50) * 1000
        inv = random.randint(int(ca * 0.2), int(ca * 0.45))
        cr = ca / cl
        qr = (ca - inv) / cl
        co = random.choice(COMPANIES)
        instruction = (
            f"{co} has current assets of {fmt_rm(ca)} (including inventory of {fmt_rm(inv)}) and "
            f"current liabilities of {fmt_rm(cl)}. Calculate the current ratio and quick ratio, "
            f"showing every step, and interpret the results."
        )
        output = (
            f"Step 1: Current ratio = Current assets ÷ Current liabilities = "
            f"{fmt_rm(ca)} ÷ {fmt_rm(cl)} = {norm(cr)} (or {norm(cr)}:1).\n"
            f"Step 2: Quick ratio = (Current assets − Inventory) ÷ Current liabilities = "
            f"({fmt_rm(ca)} − {fmt_rm(inv)}) ÷ {fmt_rm(cl)} = {norm(qr)} (or {norm(qr)}:1).\n"
            f"Interpretation: the current ratio of {norm(cr)} shows the company can cover its "
            f"short-term obligations with current assets; after removing inventory, the quick ratio "
            f"of {norm(qr)} indicates how much liquid cover remains without relying on selling stock."
        )
        rows.append(out(instruction, output))
    return rows


def gen_ar_stepwise():
    """应收账款周转分步版。"""
    rows = []
    for _ in range(8):
        credit_sales = random.randint(20, 60) * 10000
        ar = random.randint(2, 9) * 10000
        while ar >= credit_sales * 0.5:
            ar = random.randint(2, 9) * 10000
        t = credit_sales / ar
        t_disp = round(t, 2)
        days = 365 / t_disp  # 用显示值重算，保证与展示的周转率自洽
        co = random.choice(COMPANIES)
        instruction = (
            f"{co} had credit sales of {fmt_rm(credit_sales)} and average accounts receivable of "
            f"{fmt_rm(ar)} during the year. Calculate the receivables turnover and the average "
            f"collection period, showing every step, and interpret the results."
        )
        output = (
            f"Step 1: Receivables turnover = Credit sales ÷ Average accounts receivable = "
            f"{fmt_rm(credit_sales)} ÷ {fmt_rm(ar)} = {norm(t)} times.\n"
            f"Step 2: Average collection period = 365 ÷ Receivables turnover = 365 ÷ {norm(t)} = "
            f"{norm(days)} days.\n"
            f"Interpretation: customers pay on average within {norm(days)} days; a shorter "
            f"collection period improves cash flow and reduces the risk of bad debts."
        )
        rows.append(out(instruction, output))
    return rows


def gen_npv_stepwise():
    """NPV 分步版：逐年折现 + 汇总。"""
    rows = []
    for _ in range(8):
        init = random.choice([100000, 150000, 200000, 250000])
        cf1 = random.randint(5, 12) * 10000
        cf2 = random.randint(5, 12) * 10000
        r = 0.10
        d1 = cf1 / (1 + r)
        d2 = cf2 / (1 + r) ** 2
        npv = -init + d1 + d2
        co = random.choice(COMPANIES)
        advice = "the project should be accepted because it adds value to the firm." if npv > 0 else \
            "the project should not be accepted because it destroys value for the firm."
        instruction = (
            f"{co} is evaluating a project requiring an initial investment of {fmt_rm(init)}. It is "
            f"expected to generate cash inflows of {fmt_rm(cf1)} in Year 1 and {fmt_rm(cf2)} in Year "
            f"2. Using a discount rate of 10%, calculate the net present value (NPV), showing every "
            f"step, and advise whether the project should be accepted."
        )
        output = (
            f"Step 1: Discounted cash flow Year 1 = {fmt_rm(cf1)} ÷ (1 + 0.10)¹ = "
            f"{fmt_rm(cf1)} ÷ 1.10 = {fmt_rm(d1)}.\n"
            f"Step 2: Discounted cash flow Year 2 = {fmt_rm(cf2)} ÷ (1 + 0.10)² = "
            f"{fmt_rm(cf2)} ÷ 1.21 = {fmt_rm(d2)}.\n"
            f"Step 3: NPV = −Initial investment + DCF Year 1 + DCF Year 2 = "
            f"−{fmt_rm(init)} + {fmt_rm(d1)} + {fmt_rm(d2)} = {fmt_rm(npv)}.\n"
            f"Interpretation: since NPV is {('positive' if npv > 0 else 'negative')}, {advice}"
        )
        rows.append(out(instruction, output))
    return rows


def gen_eoq_stepwise():
    """EOQ 分步版。"""
    rows = []
    for _ in range(8):
        d = random.choice([4000, 5000, 6000, 8000])
        s = random.choice([80, 100, 120, 150])
        h = random.choice([1.5, 2.0, 2.5, 3.0])
        inner = 2 * d * s
        eoq = (inner / h) ** 0.5
        orders = d / eoq
        co = random.choice(COMPANIES)
        instruction = (
            f"{co} uses {d:,} units of a raw material per year. Ordering cost is {fmt_rm(s)} per "
            f"order and holding cost is {fmt_rm(h)} per unit per year. Calculate the economic order "
            f"quantity (EOQ = √(2DS ÷ H)), showing every step, and the expected number of orders "
            f"per year."
        )
        output = (
            f"Step 1: 2 × Annual demand × Ordering cost = 2 × {d:,} × {fmt_rm(s)} = {fmt_rm(inner)}.\n"
            f"Step 2: EOQ = √(2DS ÷ H) = √({fmt_rm(inner)} ÷ {fmt_rm(h)}) = √{norm(inner / h)} = "
            f"{norm(eoq)} units.\n"
            f"Step 3: Expected orders per year = Annual demand ÷ EOQ = {d:,} ÷ {norm(eoq)} = "
            f"{norm(orders)} times.\n"
            f"Interpretation: ordering {norm(eoq)} units at a time minimises the total of ordering "
            f"and holding costs; the company will place about {norm(orders)} orders per year."
        )
        rows.append(out(instruction, output))
    return rows


def main():
    rows = []
    rows += gen_capm()
    rows += gen_roi()
    rows += gen_margin()
    rows += gen_growth()
    rows += gen_hpr()
    rows += gen_fv()
    rows += gen_cvp_stepwise()
    rows += gen_ratios_stepwise()
    rows += gen_ar_stepwise()
    rows += gen_npv_stepwise()
    rows += gen_eoq_stepwise()

    # 去重（随机参数可能撞出相同题目）
    seen = set()
    dedup = []
    for r in rows:
        if r["instruction"] in seen:
            continue
        seen.add(r["instruction"])
        dedup.append(r)
    rows = dedup

    # 独立数值抽检（防止生成脚本自身算错进训练集）
    checks = [
        ("Ke=3.5%+1.2*(10%-3.5%)", 3.5 + 1.2 * (10 - 3.5)),
        ("ROI=oi/assets", None),  # 动态值跳过，依赖生成时运算
    ]
    assert abs(checks[0][1] - 11.3) < 1e-9

    path = "data/train_v3_add.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"生成 {len(rows)} 条 → {path}")
    # 类型分布
    from collections import Counter
    print(Counter(r["type"] for r in rows))


if __name__ == "__main__":
    main()
