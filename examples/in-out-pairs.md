# Input → Output examples

Human-readable examples of what the model should produce after fine-tuning.
These mirror the format specification in `docs/answering-guide.md`.

---

## Example 1 — Calculation (break-even)

**Input:**
> Bersatu Limited has normal sales of 45,000 units. Selling price is RM1.50 per unit, variable cost is RM0.75 per unit, and total fixed costs are RM15,000. Calculate the break-even point in units and in sales value.

**Output:**
> Step 1: Contribution margin per unit = RM1.50 − RM0.75 = RM0.75
> Step 2: Break-even (units) = Fixed costs ÷ CM per unit = 15,000 ÷ 0.75 = **20,000 units**
> Step 3: Break-even (sales) = 20,000 × RM1.50 = **RM30,000**
> **Interpretation:** at 20,000 units revenue exactly covers costs; each unit above that contributes RM0.75 to profit.

---

## Example 2 — Concept (distinguish)

**Input:**
> Distinguish between a static budget and a flexible budget.

**Output:**
> A static budget is fixed at one planned activity level and never changes; a flexible budget adjusts to the actual activity level. Difference 1 — basis: static = one level, flexible = a range of levels. Difference 2 — use: static for planning/target-setting, flexible for fair performance evaluation. Difference 3 — example: a 15,000-unit static budget stays put even if 20,000 units are produced, while the flexible budget recalculates variable costs for 20,000 units. Therefore flexible budgeting gives fairer variance analysis.

---

## Example 3 — Case (loan decision)

**Input:**
> A small auto-detailing business has current assets of RM25,000 and current liabilities of RM18,000. A RM50,000 loan is requested. Compute the current ratio and advise.

**Output:**
> Current Ratio = 25,000 ÷ 18,000 = **1.39**. For every RM1 of liability there is RM1.39 of current assets — liquid but with a thin cushion. **Advice: the loan should not proceed as requested**, because (1) the ratio leaves little buffer for new debt service, (2) adding RM50,000 would push the ratio below 1.0, and (3) the business should strengthen cash flow first; a smaller staged loan could be considered.

---

> Note: numbers and advice in these examples are illustrative and for format demonstration only — verify against real data before any decision.
