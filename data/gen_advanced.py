# -*- coding: utf-8 -*-
"""
Advanced accounting / analytics calculation generators (batch 2).

Adds question types that appear in the UPM tutorial banks but were not yet
covered by generate_dataset.py:
  - cost classification (DM / DL / MOH / period)
  - flexible budget preparation
  - schedule of cost of goods manufactured
  - equivalent units (weighted-average process costing)
  - job costing (budgeted rate, allocation, under/over-allocation)
  - multi-product CVP (weighted contribution margin)
  - contribution-format income statement
  - efficiency / return ratios (inventory, receivables, quick, ROE, ROI)
  - statistics supplement (covariance, mode, IQR, weighted mean)

ALL answers are computed at generation time, so numbers are correct.
"""
import random
import statistics

random.seed(7)  # separate seed for this batch

COMPANIES = [
    "Bintang Jaya Sdn. Bhd.", "Cahaya Manufacturing", "Aman Sejahtera Enterprise",
    "Mutiara Food Industries", "Kembara Tech Solutions", "Seri Indah Bakery",
    "Tunas Gemilang Sdn. Bhd.", "Lembah Ria Trading", "Permai Craft Sdn. Bhd.",
    "Desa Harmoni Furniture", "Sinar Bestari Electronics", "Utara Dinamik Logistics",
    "Mekar Suria Sdn. Bhd.", "Cempaka Digital Sdn. Bhd.", "Rimbun Agro Products",
    "Bayu Permata Holdings",
]

COST_ITEMS = {
    "DM": [
        "leather used to upholster sofas",
        "flour used by the bakery to make bread",
        "steel sheets used to make metal cabinets",
        "fabric used to sew sportswear",
        "touchscreens installed in smartphones",
        "wood used to build wooden furniture",
    ],
    "DL": [
        "wages of assembly line workers",
        "wages of machine operators in the factory",
        "wages of furniture makers",
        "wages of workers who pack finished goods in the factory",
    ],
    "MOH": [
        "depreciation on factory ovens",
        "electricity used to run factory machines",
        "salary of the factory supervisor",
        "lubricants and cleaning fluids used on factory equipment",
        "factory rent",
        "insurance on factory buildings",
    ],
    "PERIOD": [
        "salary of the sales manager",
        "advertising expenses for the product",
        "shipping and freight to deliver finished goods to customers",
        "rent of the administrative office",
        "salary of the corporate marketing director",
    ],
}


def rmc(rng):
    return rng.choice(COMPANIES)


def rint(rng, a, b):
    return rng.randint(a, b)


# --------------------------------------------------------------------------
# 1. Cost classification
# --------------------------------------------------------------------------
def gen_classification(rng):
    order = ["DM", "DL", "MOH", "PERIOD"] * 2
    rng.shuffle(order)
    picked = []
    used = set()
    for cat in order[:6]:
        pool = [i for i in COST_ITEMS[cat] if i not in used]
        item = rng.choice(pool)
        used.add(item)
        picked.append((cat, item))
    company = rmc(rng)
    lines = [f"{i+1}. {item}" for i, (_, item) in enumerate(picked)]
    q = (f"{company} incurred the following costs during the period:\n" + "\n".join(lines) +
         "\nClassify each cost as Direct Material (DM), Direct Labour (DL), Manufacturing Overhead (MOH) or Period Cost, and give a brief reason.")
    ans_lines = []
    labels = {"DM": "Direct Material (DM)", "DL": "Direct Labour (DL)",
              "MOH": "Manufacturing Overhead (MOH)", "PERIOD": "Period Cost"}
    reasons = {
        "DM": "it is a material that can be traced directly to the finished product",
        "DL": "it is the labour of workers who work directly on the product",
        "MOH": "it is an indirect manufacturing cost that cannot be traced to a specific unit",
        "PERIOD": "it is a selling or administrative cost expensed in the period",
    }
    for i, (cat, item) in enumerate(picked, 1):
        ans_lines.append(f"Item {i} ({item}): {labels[cat]} — {reasons[cat]}.")
    ans_lines.append("Note: DM and DL are direct and variable; MOH is indirect and may be fixed or variable; period costs are not part of product cost.")
    return {"instruction": q, "input": "", "output": " ".join(ans_lines), "type": "calculation"}


# --------------------------------------------------------------------------
# 2. Flexible budget
# --------------------------------------------------------------------------
def gen_flexbudget(rng):
    dm_u = rng.choice([3.0, 3.5, 4.0, 5.0, 6.0, 8.0])
    dl_u = rng.choice([2.0, 2.5, 3.0, 3.5, 4.0, 5.0])
    voh_u = rng.choice([1.0, 1.2, 1.5, 2.0, 2.5])
    fc = rng.choice([20000, 25000, 30000, 40000, 50000, 60000])
    lvl = sorted(rng.sample([5000, 10000, 15000, 20000, 25000, 30000], 3))
    company = rmc(rng)
    q = (f"{company} has the following cost structure: variable cost per unit — direct materials RM{dm_u:.2f}, "
         f"direct labour RM{dl_u:.2f}, variable overhead RM{voh_u:.2f}; fixed costs RM{fc:,} per period. "
         f"Prepare a flexible budget for activity levels of {lvl[0]:,}, {lvl[1]:,} and {lvl[2]:,} units.")
    parts = []
    for u in lvl:
        t_dm = round(dm_u * u)
        t_dl = round(dl_u * u)
        t_voh = round(voh_u * u)
        t_var = t_dm + t_dl + t_voh
        total = t_var + fc
        parts.append(
            f"at {u:,} units — DM RM{t_dm:,}, DL RM{t_dl:,}, variable OH RM{t_voh:,} (total variable RM{t_var:,}), "
            f"plus fixed costs RM{fc:,}, total budgeted costs RM{total:,}.")
    parts.append("Interpretation: variable costs scale with activity while fixed costs stay constant, "
                 "so the flexible budget gives a fair cost benchmark at each actual volume.")
    return {"instruction": q, "input": "", "output": " ".join(parts), "type": "calculation"}


# --------------------------------------------------------------------------
# 3. Schedule of cost of goods manufactured
# --------------------------------------------------------------------------
def gen_cogm(rng):
    beg_dm = rng.choice([5000, 8000, 10000, 12000, 15000])
    end_dm = rng.choice([6000, 9000, 11000, 14000, 16000])
    purch = rng.choice([25000, 30000, 35000, 40000, 45000])
    beg_wip = rng.choice([8000, 10000, 12000, 15000])
    end_wip = rng.choice([7000, 9000, 11000, 14000])
    dl = rng.choice([12000, 15000, 18000, 20000, 24000])
    moh = rng.choice([9000, 10000, 12000, 14000, 16000])
    dm_used = beg_dm + purch - end_dm
    total_mfg = dm_used + dl + moh
    cogm = total_mfg + beg_wip - end_wip
    company = rmc(rng)
    q = (f"{company} provides: beginning direct materials RM{beg_dm:,}, ending direct materials RM{end_dm:,}, "
         f"direct materials purchased RM{purch:,}, beginning work-in-process RM{beg_wip:,}, ending work-in-process RM{end_wip:,}, "
         f"direct labour RM{dl:,} and manufacturing overhead RM{moh:,}. Prepare a formal Schedule of Cost of Goods Manufactured.")
    ans = (f"Schedule of Cost of Goods Manufactured for {company}: "
           f"Direct materials: beginning inventory RM{beg_dm:,} + purchases RM{purch:,} − ending inventory RM{end_dm:,} "
           f"= direct materials used RM{dm_used:,}. "
           f"Direct labour RM{dl:,}. Manufacturing overhead RM{moh:,}. "
           f"Total manufacturing cost = RM{dm_used:,} + RM{dl:,} + RM{moh:,} = RM{total_mfg:,}. "
           f"Add beginning work-in-process RM{beg_wip:,} = RM{total_mfg + beg_wip:,}. "
           f"Less ending work-in-process RM{end_wip:,}. "
           f"Cost of goods manufactured = RM{cogm:,}. "
           f"Interpretation: this is the cost of units completed during the period and transferred to finished goods, "
           f"before considering finished-goods inventory and cost of sales.")
    return {"instruction": q, "input": "", "output": ans, "type": "calculation"}


# --------------------------------------------------------------------------
# 4. Equivalent units (weighted-average process costing)
# --------------------------------------------------------------------------
def gen_eu(rng):
    beg = rng.choice([60, 80, 100, 120, 150, 200])
    started = rng.choice([400, 500, 600, 800, 1000])
    completed = rng.choice([380, 460, 520, 640, 820])
    end = beg + started - completed
    if end <= 0:
        end = rng.choice([80, 120, 160])
        completed = beg + started - end
    conv_pct = rng.choice([30, 40, 50, 60, 70])
    dm_cost = rng.choice([2.0, 2.5, 3.0, 4.0, 5.0])
    conv_cost = rng.choice([3.0, 4.0, 5.0, 6.0, 7.5])
    eu_dm = completed + end  # DM 100%
    eu_conv = completed + round(end * conv_pct / 100)
    beg_dm = rng.choice([int(dm_cost * k) for k in range(40, 120, 10)])
    beg_conv = rng.choice([int(conv_cost * k) for k in range(30, 100, 10)])
    added_dm = round(dm_cost * eu_dm - beg_dm, 2)
    added_conv = round(conv_cost * eu_conv - beg_conv, 2)
    tot_dm = beg_dm + added_dm
    tot_conv = beg_conv + added_conv
    eu_dm_cost = round(tot_dm / eu_dm, 2)
    eu_conv_cost = round(tot_conv / eu_conv, 2)
    cost_completed = round(completed * (eu_dm_cost + eu_conv_cost), 2)
    cost_end_dm = round(end * eu_dm_cost, 2)
    cost_end_conv = round(end * conv_pct / 100 * eu_conv_cost, 2)
    cost_end = round(cost_end_dm + cost_end_conv, 2)
    total_acct = round(cost_completed + cost_end, 2)
    total_2acct = round(beg_dm + beg_conv + added_dm + added_conv, 2)
    company = rmc(rng)
    which = rng.choice(["eu", "cost"])
    q_head = (f"{company} uses the weighted-average method. Beginning work-in-process: {beg:,} units "
              f"(DM RM{beg_dm:,}, conversion RM{beg_conv:,}); units started in the period: {started:,}; "
              f"units completed: {completed:,}; ending work-in-process: {end:,} units "
              f"(DM 100% complete, conversion {conv_pct}% complete). ")
    if which == "eu":
        q = q_head + "Compute the equivalent units for direct materials and conversion costs."
        ans = (f"Step 1 (physical units): Beginning {beg:,} + Started {started:,} = Completed {completed:,} + Ending {end:,} "
               f"= {beg + started:,} units. "
               f"Step 2 (equivalent units, weighted-average): Direct materials = completed {completed:,} + ending {end:,} × 100% = {eu_dm:,} EU. "
               f"Conversion costs = completed {completed:,} + ending {end:,} × {conv_pct}% = {eu_conv:,} EU. "
               f"Interpretation: {eu_conv:,} of the ending units count fully for materials but only partly for conversion, "
               f"so conversion has fewer equivalent units than materials.")
    else:
        q = q_head + (f"Direct materials added RM{added_dm:,}, conversion costs added RM{added_conv:,}. "
                      f"Compute the cost per equivalent unit and assign costs to completed units and ending work-in-process.")
        ans = (f"Step 1 (physical units): Beginning {beg:,} + Started {started:,} = Completed {completed:,} + Ending {end:,} = {beg + started:,} units. "
               f"Step 2 (equivalent units): DM = {completed:,} + {end:,} × 100% = {eu_dm:,} EU; "
               f"Conversion = {completed:,} + {end:,} × {conv_pct}% = {eu_conv:,} EU. "
               f"Step 3 (cost per EU): DM = (RM{beg_dm:,} + RM{added_dm:,}) ÷ {eu_dm:,} = RM{eu_dm_cost:.2f}; "
               f"Conversion = (RM{beg_conv:,} + RM{added_conv:,}) ÷ {eu_conv:,} = RM{eu_conv_cost:.2f}. "
               f"Step 4 (cost assignment): Completed {completed:,} × (RM{eu_dm_cost:.2f} + RM{eu_conv_cost:.2f}) = RM{cost_completed:,}. "
               f"Ending WIP: DM {end:,} × RM{eu_dm_cost:.2f} = RM{cost_end_dm:,} + conversion {end:,} × {conv_pct}% × RM{eu_conv_cost:.2f} = RM{cost_end_conv:,} "
               f"→ ending WIP total RM{cost_end:,}. "
               f"Total costs accounted for = RM{cost_completed:,} + RM{cost_end:,} = RM{total_acct:,}, "
               f"which matches total costs to account for RM{total_2acct:,}.")
    return {"instruction": q, "input": "", "output": ans, "type": "calculation"}


# --------------------------------------------------------------------------
# 5. Job costing
# --------------------------------------------------------------------------
def gen_jobcost(rng):
    company = rmc(rng)
    which = rng.choice(["rate", "job", "moh"])
    if which == "rate":
        bmoh = rng.choice([800000, 1200000, 1600000, 2000000])
        bbase = rng.choice([20000, 32000, 40000, 50000])
        rate = bmoh // bbase
        bmoh = rate * bbase
        q = (f"{company} budgeted manufacturing overhead of RM{bmoh:,} and {bbase:,} direct labour hours. "
             f"Compute the budgeted manufacturing overhead rate.")
        ans = (f"Budgeted overhead rate = Budgeted MOH ÷ Budgeted allocation base = RM{bmoh:,} ÷ {bbase:,} hours = RM{rate} per direct labour hour. "
               f"Interpretation: for every direct labour hour worked, RM{rate} of overhead is allocated to the job; "
               f"this rate lets the company cost jobs during the period before actual overhead is known.")
    elif which == "job":
        rate = rng.choice([30, 40, 50, 60, 80])
        dlh = rng.choice([600, 800, 1000, 1200, 1500])
        dm = rng.choice([50000, 70000, 90000, 120000])
        dl = rng.choice([30000, 40000, 50000, 60000])
        overhead = rate * dlh
        jobcost = dm + dl + overhead
        q = (f"{company} uses a budgeted overhead rate of RM{rate} per direct labour hour. Job 626 used "
             f"RM{dm:,} of direct materials, RM{dl:,} of direct labour and {dlh:,} direct labour hours. "
             f"Compute the total cost of Job 626 under normal costing.")
        ans = (f"Step 1: Overhead allocated = Budgeted rate × Actual hours = RM{rate} × {dlh:,} = RM{overhead:,}. "
               f"Step 2: Job cost = Direct materials + Direct labour + Allocated overhead = RM{dm:,} + RM{dl:,} + RM{overhead:,} = RM{jobcost:,}. "
               f"Interpretation: under normal costing the job is charged overhead at the budgeted rate, "
               f"so the job cost is known immediately even though actual overhead is not yet known.")
    else:  # under/over allocation
        bmoh = rng.choice([800000, 1200000, 1600000, 2000000])
        bbase = rng.choice([20000, 32000, 40000, 50000])
        rate = bmoh // bbase
        bmoh = rate * bbase
        abase = int(bbase * rng.choice([0.9, 0.95, 1.0, 1.05, 1.1]))
        amoh = rng.choice([int(bmoh * r) for r in [0.9, 0.95, 1.0, 1.05, 1.1]])
        alloc = rate * abase
        diff = amoh - alloc
        tag = "under-allocated" if diff > 0 else "over-allocated"
        q = (f"{company} uses normal costing with a budgeted rate of RM{rate} per direct labour hour "
             f"(budgeted MOH RM{bmoh:,}). Actual overhead was RM{amoh:,} and actual direct labour hours were {abase:,}. "
             f"Calculate the overhead allocated and state whether overhead is under- or over-allocated.")
        ans = (f"Step 1: Overhead allocated = Budgeted rate × Actual hours = RM{rate} × {abase:,} = RM{alloc:,}. "
               f"Step 2: Under- or over-allocation = Actual MOH − Allocated MOH = RM{amoh:,} − RM{alloc:,} = RM{abs(diff):,} {tag}. "
               f"Interpretation: the difference arises because actual overhead and actual activity differ from budget; "
               f"it is closed to cost of goods sold at year-end so that reported costs reflect actual overhead.")
    return {"instruction": q, "input": "", "output": ans, "type": "calculation"}


# --------------------------------------------------------------------------
# 6. Multi-product CVP (weighted contribution margin)
# --------------------------------------------------------------------------
def gen_multicvp(rng):
    pa = rng.choice([10, 12, 15, 20, 25])
    va = rng.choice([4, 5, 6, 8, 10])
    pb = rng.choice([8, 10, 12, 15, 18])
    vb = rng.choice([3, 4, 5, 6, 8])
    cm_a = pa - va
    cm_b = pb - vb
    mix_a = rng.choice([40, 50, 60, 75])
    mix_b = 100 - mix_a
    wcm = round(cm_a * mix_a / 100 + cm_b * mix_b / 100, 2)
    target_bep = rng.choice([2000, 3000, 4000, 5000, 6000, 8000])
    fc = int(round(wcm * target_bep))
    bep = round(fc / wcm)
    wprice = round(pa * mix_a / 100 + pb * mix_b / 100, 2)
    bep_rm = round(bep * wprice, 0)
    company = rmc(rng)
    q = (f"{company} sells two products: A at RM{pa}/unit with variable cost RM{va}, and B at RM{pb}/unit "
         f"with variable cost RM{vb}. The sales mix is {mix_a}% A and {mix_b}% B, and fixed costs are RM{fc:,}. "
         f"Compute the weighted-average contribution margin per unit and the break-even point in total units and in RM.")
    ans = (f"Step 1: Unit CM — A = RM{pa} − RM{va} = RM{cm_a}; B = RM{pb} − RM{vb} = RM{cm_b}. "
           f"Step 2: Weighted-average CM = ({mix_a}% × RM{cm_a}) + ({mix_b}% × RM{cm_b}) = RM{wcm}. "
           f"Step 3: Break-even (total units) = Fixed costs ÷ Weighted CM = RM{fc:,} ÷ RM{wcm} = {bep:,} units "
           f"({round(bep * mix_a / 100):,} of A and {round(bep * mix_b / 100):,} of B). "
           f"Step 4: Weighted-average price = ({mix_a}% × RM{pa}) + ({mix_b}% × RM{pb}) = RM{wprice}, "
           f"so break-even in RM = {bep:,} × RM{wprice} = RM{bep_rm:,.0f}. "
           f"Interpretation: the sales mix determines the weighted contribution, so break-even depends on the mix; "
           f"if the mix shifts toward the higher-margin product, break-even falls.")
    return {"instruction": q, "input": "", "output": ans, "type": "calculation"}


# --------------------------------------------------------------------------
# 7. Contribution-format income statement / CVP
# --------------------------------------------------------------------------
def gen_contribution(rng):
    price = rng.choice([10, 12, 15, 20, 25, 30])
    vc = rng.choice([v for v in [4, 5, 6, 8, 10, 12] if v < price])
    units = rng.choice([8000, 10000, 12000, 15000, 20000])
    fc = rng.choice([30000, 40000, 50000, 60000, 80000])
    cm = price - vc
    sales = price * units
    tvc = vc * units
    total_cm = cm * units
    np = total_cm - fc
    bep_units = round(fc / cm)
    bep_sales = bep_units * price
    mos = units - bep_units
    mos_pct = round(mos / units * 100, 1)
    company = rmc(rng)
    q = (f"{company} sells {units:,} units at RM{price} each; variable cost is RM{vc} per unit and fixed costs are "
         f"RM{fc:,}. Prepare a contribution-format income statement and compute the break-even point and margin of safety.")
    ans = (f"Contribution-format income statement: Sales (RM{price} × {units:,}) = RM{sales:,}; "
           f"Less variable costs (RM{vc} × {units:,}) = RM{tvc:,}; "
           f"Contribution margin = RM{total_cm:,} (RM{cm} per unit); "
           f"Less fixed costs RM{fc:,}; Net profit = RM{np:,}. "
           f"Break-even (units) = Fixed costs ÷ CM per unit = RM{fc:,} ÷ RM{cm} = {bep_units:,} units "
           f"(RM{bep_sales:,}). "
           f"Margin of safety = {units:,} − {bep_units:,} = {mos:,} units ({mos_pct}% of sales). "
           f"Interpretation: sales can fall by {mos:,} units ({mos_pct}%) before the company breaks even; "
           f"at the current level it earns RM{np:,} because contribution margin exceeds fixed costs by that amount.")
    return {"instruction": q, "input": "", "output": ans, "type": "calculation"}


# --------------------------------------------------------------------------
# 8. Efficiency / return ratios
# --------------------------------------------------------------------------
def gen_effratio(rng, which=None):
    company = rmc(rng)
    if which is None:
        which = rng.choice(["inv", "recv", "quick", "roe", "roi"])
    if which == "inv":
        cogs = rng.choice([120000, 150000, 180000, 200000, 250000])
        inv_beg = rng.choice([20000, 25000, 30000, 40000])
        inv_end = rng.choice([20000, 30000, 35000, 45000])
        avg = round((inv_beg + inv_end) / 2)
        t = round(cogs / avg, 1)
        days = round(365 / t, 1) if t else 0
        q = (f"{company} has cost of goods sold of RM{cogs:,}, beginning inventory RM{inv_beg:,} and ending inventory "
             f"RM{inv_end:,}. Calculate the inventory turnover and the average days in inventory.")
        ans = (f"Step 1: Average inventory = (RM{inv_beg:,} + RM{inv_end:,}) ÷ 2 = RM{avg:,}. "
               f"Step 2: Inventory turnover = COGS ÷ Average inventory = RM{cogs:,} ÷ RM{avg:,} = {t} times. "
               f"Step 3: Days in inventory = 365 ÷ Turnover = {days} days. "
               f"Interpretation: the company sells its average inventory {t} times per year (every {days} days); "
               f"a higher turnover means inventory is managed efficiently and less cash is tied up in stock.")
    elif which == "recv":
        sales = rng.choice([200000, 250000, 300000, 400000, 500000])
        recv_beg = rng.choice([20000, 30000, 40000])
        recv_end = rng.choice([25000, 35000, 45000])
        avg = round((recv_beg + recv_end) / 2)
        t = round(sales / avg, 1)
        days = round(365 / t, 1) if t else 0
        q = (f"{company} has credit sales of RM{sales:,}, beginning accounts receivable RM{recv_beg:,} and ending "
             f"accounts receivable RM{recv_end:,}. Calculate the accounts receivable turnover and the average collection period.")
        ans = (f"Step 1: Average receivables = (RM{recv_beg:,} + RM{recv_end:,}) ÷ 2 = RM{avg:,}. "
               f"Step 2: Receivables turnover = Credit sales ÷ Average receivables = RM{sales:,} ÷ RM{avg:,} = {t} times. "
               f"Step 3: Average collection period = 365 ÷ Turnover = {days} days. "
               f"Interpretation: customers pay on average within {days} days; a shorter collection period improves "
               f"cash flow and reduces the risk of bad debts.")
    elif which == "quick":
        ca = rng.choice([40000, 50000, 60000, 80000])
        inv = rng.choice([10000, 15000, 20000, 25000])
        cl = rng.choice([20000, 25000, 30000, 40000])
        qa = round((ca - inv) / cl, 2)
        q = (f"{company} has current assets of RM{ca:,} (including inventory of RM{inv:,}) and current liabilities of "
             f"RM{cl:,}. Calculate the quick ratio and comment on liquidity.")
        ans = (f"Quick Ratio = (Current assets − Inventory) ÷ Current liabilities = (RM{ca:,} − RM{inv:,}) ÷ RM{cl:,} "
               f"= RM{ca - inv:,} ÷ RM{cl:,} = {qa:.2f}. "
               f"Interpretation: excluding inventory, the company has RM{qa:.2f} of liquid assets for every RM1.00 of "
               f"short-term liability, which is a stricter test of liquidity than the current ratio "
               f"{'and indicates a comfortable liquid position' if qa >= 1.0 else 'and signals that it relies on selling inventory to pay short-term debts'}.")
    elif which == "roe":
        np = rng.choice([40000, 50000, 60000, 80000, 100000])
        eq = rng.choice([200000, 250000, 300000, 400000])
        roe = round(np / eq * 100, 1)
        q = (f"{company} earned a net profit of RM{np:,} and has shareholders' equity of RM{eq:,}. "
             f"Calculate the return on equity (ROE).")
        ans = (f"ROE = (Net profit ÷ Shareholders' equity) × 100% = (RM{np:,} ÷ RM{eq:,}) × 100% = {roe}%. "
               f"Interpretation: for every RM1 of equity invested, the company generates RM{roe / 100:.2f} of profit "
               f"for shareholders; a higher ROE indicates the company uses shareholders' funds efficiently.")
    else:  # roi
        op = rng.choice([30000, 40000, 50000, 60000])
        capital = rng.choice([150000, 200000, 250000, 300000])
        roi = round(op / capital * 100, 1)
        q = (f"{company} earned an operating profit of RM{op:,} on invested capital of RM{capital:,}. "
             f"Calculate the return on investment (ROI).")
        ans = (f"ROI = (Operating profit ÷ Invested capital) × 100% = (RM{op:,} ÷ RM{capital:,}) × 100% = {roi}%. "
               f"Interpretation: each RM1 of invested capital returns RM{roi / 100:.2f} of operating profit; "
               f"managers use ROI to compare divisions or projects and to decide where to invest capital.")
    return {"instruction": q, "input": "", "output": ans, "type": "calculation"}


# --------------------------------------------------------------------------
# 9. Statistics supplement
# --------------------------------------------------------------------------
def gen_stats2(rng, which=None):
    company = rmc(rng)
    if which is None:
        which = rng.choice(["cov", "mode", "iqr", "wmean"])
    if which == "cov":
        x = [rng.randint(1, 20) for _ in range(8)]
        y = [rng.randint(1, 20) for _ in range(8)]
        mx = statistics.mean(x)
        my = statistics.mean(y)
        cov = round(sum((a - mx) * (b - my) for a, b in zip(x, y)) / (len(x) - 1), 2)
        q = (f"{company} recorded two variables over 8 months: X = {x}, Y = {y}. "
             f"Calculate the sample covariance and interpret its sign.")
        ans = (f"Step 1: Means — x̄ = {sum(x)} ÷ 8 = {mx:.2f}, ȳ = {sum(y)} ÷ 8 = {my:.2f}. "
               f"Step 2: Covariance = Σ(x − x̄)(y − ȳ) ÷ (n − 1) = {cov}. "
               f"Interpretation: a {'positive' if cov > 0 else 'negative'} covariance means the two variables tend to move "
               f"{'together' if cov > 0 else 'in opposite directions'}; the sign shows the direction of the linear relationship, "
               f"while its size depends on the units of the variables.")
    elif which == "mode":
        data = [rng.randint(1, 9) for _ in range(10)]
        data = sorted(data)
        from collections import Counter
        c = Counter(data)
        modes = [k for k, v in c.items() if v == max(c.values())]
        if len(modes) == 10:
            modes = modes[:1]
        mode_str = ", ".join(map(str, modes))
        q = (f"The daily orders recorded by {company} were: {', '.join(map(str, data))}. Calculate the mode.")
        ans = (f"The mode is the value that appears most frequently. Counting the frequencies: "
               f"{', '.join(f'{k} appears {v} times' for k, v in sorted(c.items()))}. "
               f"Therefore the mode = {mode_str}. "
               f"Interpretation: the mode identifies the most common daily order level, "
               f"which is useful for staffing and stocking the most frequent demand scenario.")
    elif which == "iqr":
        data = sorted(rng.randint(20, 80) for _ in range(10))
        n = len(data)
        q1 = statistics.quantiles(data, n=4, method="inclusive")[0]
        q3 = statistics.quantiles(data, n=4, method="inclusive")[2]
        iqr = round(q3 - q1, 1)
        q = (f"{company} collected these 10 values: {', '.join(map(str, data))}. "
             f"Calculate the interquartile range (IQR).")
        ans = (f"Step 1: Arrange in ascending order: {', '.join(map(str, data))}. "
               f"Step 2: Q1 (lower quartile) = {q1:.0f}; Q3 (upper quartile) = {q3:.0f}. "
               f"Step 3: IQR = Q3 − Q1 = {q3:.0f} − {q1:.0f} = {iqr}. "
               f"Interpretation: the middle 50% of the data lies within a range of {iqr}; a small IQR means the "
               f"central observations are tightly clustered, while a large IQR indicates greater spread.")
    else:  # weighted mean
        n = rng.choice([3, 4])
        vals = [rng.randint(20, 90) for _ in range(n)]
        wts = [rng.randint(1, 5) for _ in range(n)]
        wm = round(sum(v * w for v, w in zip(vals, wts)) / sum(wts), 2)
        q = (f"{company} has {n} products with scores {vals} and weights {wts}. "
             f"Calculate the weighted mean score.")
        ans = (f"Weighted mean = Σ(value × weight) ÷ Σ(weight) = "
               f"({' + '.join(f'{v}×{w}' for v, w in zip(vals, wts))}) ÷ {sum(wts)} "
               f"= {sum(v * w for v, w in zip(vals, wts))} ÷ {sum(wts)} = {wm}. "
               f"Interpretation: the weighted mean gives greater influence to items with larger weights, "
               f"so it better reflects overall performance when not all items are equally important.")
    return {"instruction": q, "input": "", "output": ans, "type": "calculation"}


# --------------------------------------------------------------------------
def generate_advanced(rng):
    pairs = []
    for _ in range(18):
        pairs.append(gen_classification(rng))
    for _ in range(12):
        pairs.append(gen_flexbudget(rng))
    for _ in range(10):
        pairs.append(gen_cogm(rng))
    for _ in range(14):
        pairs.append(gen_eu(rng))
    for _ in range(12):
        pairs.append(gen_jobcost(rng))
    for _ in range(12):
        pairs.append(gen_multicvp(rng))
    for _ in range(8):
        pairs.append(gen_contribution(rng))
    # efficiency ratios: explicit coverage of all five types
    for _ in range(3):
        pairs.append(gen_effratio(rng, "inv"))
    for _ in range(3):
        pairs.append(gen_effratio(rng, "recv"))
    for _ in range(3):
        pairs.append(gen_effratio(rng, "quick"))
    for _ in range(3):
        pairs.append(gen_effratio(rng, "roe"))
    for _ in range(2):
        pairs.append(gen_effratio(rng, "roi"))
    for _ in range(2):
        pairs.append(gen_effratio(rng))
    # statistics: explicit coverage of all four types
    for _ in range(2):
        pairs.append(gen_stats2(rng, "cov"))
    for _ in range(2):
        pairs.append(gen_stats2(rng, "mode"))
    for _ in range(2):
        pairs.append(gen_stats2(rng, "iqr"))
    for _ in range(2):
        pairs.append(gen_stats2(rng, "wmean"))
    for _ in range(2):
        pairs.append(gen_stats2(rng))
    return pairs


if __name__ == "__main__":
    rng = random.Random(7)
    pairs = generate_advanced(rng)
    print(f"advanced batch: {len(pairs)} pairs")
    from collections import Counter
    print(Counter(p["type"] for p in pairs))
