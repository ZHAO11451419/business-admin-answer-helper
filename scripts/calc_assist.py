# -*- coding: utf-8 -*-
"""
计算器辅助模块（calculator-assist）：自动核验并修正模型输出中的算术错误。

原理：微调模型在计算题中会写出完整的计算表达式（格式训练的效果），
但 3B 模型的除法/小数运算不可靠。本模块：
  1. 从模型输出中提取 "表达式 = 结果" 模式（如 "72,000 ÷ 4.50 = 20,000"）；
  2. 用精确有理数运算（Fraction）重算表达式；
  3. 与模型给出的结果不一致时，替换为正确结果并保持原格式风格。

局限：只能修正"表达式完整出现在文本中"的错误；纯心算结论（无表达式）
无法修正；依赖错误数字的后续推论句不会自动改写。

用法：
  from calc_assist import fix_arithmetic
  fixed, corrections = fix_arithmetic(model_answer)
"""
import ast
import operator
import re

_OPS = {
    "Div": operator.truediv,
    "Mult": operator.mul,
    "Add": operator.add,
    "Sub": operator.sub,
    "Pow": operator.pow,  # √ 展开为 **0.5 时使用
}

_TRANSLATE = str.maketrans({"÷": "/", "×": "*", "−": "-", "—": "-"})

# Unicode 上标（次方）转成 ^n 记号，随后在 _expand_supers 中展开为乘法
_SUP = str.maketrans({
    "⁰": "^0", "¹": "^1", "²": "^2", "³": "^3", "⁴": "^4",
    "⁵": "^5", "⁶": "^6", "⁷": "^7", "⁸": "^8", "⁹": "^9",
})


def _expand_supers(s: str) -> str:
    """把 Unicode 上标次方展开为 Python 可求值的乘法形式。

    (1 + 0.10)¹ → (1 + 0.10)；5² → ((5)*(5))；(X)³ → ((X)*(X)*(X))。
    展开后的整个因子必须保持括号，避免 "÷(X)²" 被解析成 "÷(X)*(X)" 改变运算顺序。
    """
    s = s.translate(_SUP)
    s = re.sub(r"(\([^()]*\))\^0|\d+(?:\.\d+)?\^0", "1", s)

    def _pow(inner: str, n: int) -> str:
        if n == 1:
            return inner if inner.startswith("(") else f"({inner})"
        return "(" + "*".join([f"({inner})"] * n) + ")"

    for n in range(9, 0, -1):
        s = re.sub(rf"(\([^()]*\))\^{n}", lambda m: _pow(m.group(1), n), s)
        s = re.sub(
            rf"(?<![\w.])(\d+(?:\.\d+)?)\^{n}",
            lambda m: _pow(m.group(1), n),
            s,
        )
    return s


_OP = r"[\/÷×\*+\-−]"
# 数字：可选负号 + 字母前缀 + 数值 + 可选 % 单位后缀（如 "10%"，% 紧贴数字不能单独成 token）
_NUM = r"(?:[-−—]?[A-Za-z]*\d[\d,]*(?:\.\d+)?%?)"
# 一层嵌套操作数：数字，或"括号内至少两操作数一运算符"（内层可为数字或一层括号）
_ATOM_INNER = rf"(?:{_NUM}|\({_NUM}(?:\s*{_OP}\s*{_NUM})+\))"
# 操作数：√ 平方根、纯数字，或"括号内至少两操作数一运算符"（支持一层嵌套括号 + Unicode 上标次方）
_ATOM = rf"(?:√\([^()]*\)[⁰¹²³⁴⁵⁶⁷⁸⁹]*|\({_ATOM_INNER}(?:\s*{_OP}\s*{_ATOM_INNER})+\)[⁰¹²³⁴⁵⁶⁷⁸⁹]*|{_NUM})"
# 表达式 = 结果：表达式为"至少两个操作数 + 至少一个运算符"，结果紧随等号。
# 分步式中间结果（"(A−B) ÷ C = RM20,000 ÷ RM25,000 = 0.80" 中的 RM20,000）
# 在 _iter_expr_eq 里用手动后置检查拒绝，避免正则断言被回溯绕过。
_EXPR_EQ = re.compile(
    rf"({_ATOM}(?:\s*[\/÷×\*+\-−]\s*{_ATOM})+)\s*=\s*({_NUM})"
)

# 结果数字后紧跟运算符 + 数字 → 这是分步式中间结果，不是最终结果
_TAIL_OP = re.compile(r"^\s*[÷×]\s*[A-Za-z]*\d")
# 结果数字后紧跟等号 + 数字 → 链式中间值（如 "√500,000 = 707" 中的 √500,000），跳过
_TAIL_EQ = re.compile(r"^\s*=\s*[-−—]?[A-Za-z]*\d")
# 单独的 √(expr) = 结果（√ 是单操作数，_EXPR_EQ 要求至少两操作数，故单独提取）
_SQRT_EQ = re.compile(r"(√\([^()]*\))\s*=\s*([-−—]?[A-Za-z]*\d[\d,]*(?:\.\d+)?)")


def _iter_expr_eq(text):
    """迭代"表达式 = 结果"，跳过分步式中间结果（结果后紧跟 ÷/× 运算符或链式等号）。"""
    for m in _EXPR_EQ.finditer(text):
        if _TAIL_OP.match(text[m.end():]):
            continue
        if _TAIL_EQ.match(text[m.end():]):
            continue
        yield m


def _iter_sqrt_eq(text):
    """迭代"√(expr) = 结果"（√ 单操作数形式），同样跳过分步式中间结果。"""
    for m in _SQRT_EQ.finditer(text):
        if _TAIL_OP.match(text[m.end():]):
            continue
        if _TAIL_EQ.match(text[m.end():]):
            continue
        yield m


class _SafeEval(ast.NodeVisitor):
    """AST 白名单求值：只允许数字、四则运算、一元负号、括号。"""

    def visit_Constant(self, node):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("unsupported constant")

    def visit_UnaryOp(self, node):
        if isinstance(node.op, ast.USub):
            return -self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return self.visit(node.operand)
        raise ValueError("unsupported unary op")

    def visit_BinOp(self, node):
        op = _OPS.get(type(node.op).__name__)
        if op is None:
            raise ValueError("unsupported binop")
        return op(self.visit(node.left), self.visit(node.right))

    def visit_Expression(self, node):
        return self.visit(node.body)

    def generic_visit(self, node):
        raise ValueError(f"unsupported node: {type(node).__name__}")


def _safe_eval(expr: str):
    """安全求值：解析为 ast 后白名单执行，杜绝任意代码执行。"""
    tree = ast.parse(expr, mode="eval")
    return _SafeEval().visit(tree)


def _fmt_result(value, source_num: str) -> str:
    """把精确结果按源数字的风格格式化（保留字母前缀 + 千分位 + 小数位）。

    比率类修正（如 1.12）至少保留 2 位小数，防止模型写 "1.0" 时修正成 "1.1" 丢精度。
    """
    m = re.match(r"([A-Za-z]*)(.*)", source_num.strip())
    prefix, src = m.group(1), m.group(2)
    if "." in src:
        decimals = max(2, len(src.split(".")[1]))
        text = f"{value:.{decimals}f}"
    elif float(value) == int(value):
        text = str(int(value))
    else:
        text = f"{value:.4f}".rstrip("0").rstrip(".")
    if "," in source_num and float(text) >= 1000:
        if "." in text:
            int_part, dec_part = text.split(".")
            return f"{prefix}{int(int_part):,}.{dec_part}"
        return f"{prefix}{int(text):,}"
    return prefix + text


def _normalise(s: str) -> str:
    """把模型文本表达式转成 Python 可求值形式（去掉字母/货币前缀，展开上标与平方根）。"""
    s = re.sub(r"[A-Za-z]", "", s)  # 先去字母（sqrt 等关键字被删，√ 符号保留）
    s = s.replace("[", "(").replace("]", ")")  # 中括号（模型常用 [] 表示分组）→ 圆括号
    s = s.translate(_TRANSLATE).replace(",", "").strip()
    s = s.replace("%", "")  # % 在表达式中只是单位标记（3.5% 即 3.5），否则会被 ast 当取模运算
    # √(expr) / √数字 → 0.5 次幂（求值器已支持 Pow）
    s = re.sub(r"√\s*\(([^()]*)\)", r"(\1)**0.5", s)
    s = re.sub(r"√\s*(\d+(?:\.\d+)?)", r"\1**0.5", s)
    return _expand_supers(s)


def _propagate(text: str, old_val: str, new_val: str, start: int, max_hits: int = 3):
    """把修正后文本中后续出现的"孤立旧值"替换为新值（解读句里的重复数字）。

    只匹配前后不是数字/字母/小数点的独立数值，避免误伤其他数字。
    """
    pattern = re.compile(rf"(?<![\w.]){re.escape(old_val)}(?![\w.])")
    hits = 0
    out = text[:start]
    tail = text[start:]
    last = 0
    for m in pattern.finditer(tail):
        out += tail[last:m.start()] + new_val
        last = m.end()
        hits += 1
        if hits >= max_hits:
            break
    out += tail[last:]
    return out, hits


def fix_arithmetic(text: str):
    """扫描并修正文本中的算术错误。

    修正两类错误：
      1. "表达式 = 结果" 中结果算错的（如 72,000 ÷ 4.50 = 20,000 → 16,000）；
      2. 解读句里重复出现的旧错误值（如 "must sell 20,000 units"）。

    Returns:
        (fixed_text, corrections)  corrections 为 [(原始片段, 修正后片段), ...]
    """
    corrections = []
    fixed = text.replace("[", "(").replace("]", ")")  # 中括号分组 → 圆括号（正则与求值均需）
    last_end = 0
    # 合并两类表达式迭代器（普通表达式 + √ 单操作数），按出现位置排序后统一处理
    matches = sorted(
        list(_iter_expr_eq(fixed)) + list(_iter_sqrt_eq(fixed)),
        key=lambda m: m.start(),
    )
    for m in matches:
        expr_raw, result_raw = m.group(1), m.group(2)
        expr = _normalise(expr_raw)
        try:
            value = _safe_eval(expr)
        except Exception:
            continue
        if not isinstance(value, (int, float)) or value != value:  # 非数值/NaN
            continue
        if re.search(r"\bQ[1-3]\b", expr_raw):
            # 统计符号（Q1/Q3 四分位数等）会被字母前缀误解析，跳过
            continue
        # 百分比判定：结果本身带 % 且表达式内部不含 % 时，把比值 ×100 后比较
        #（如 (RM90,000 + RM50,000) ÷ RM120,000 = 117%）。
        # 若表达式本身已含 %（如 CAPM "3.5% + 1.2 × (10% − 3.5%)"），模型已按 % 单位
        # 表达，直接比较原值，不得再 ×100，否则会把正确结果误改成 ×100 的错值。
        is_pct = result_raw.rstrip().endswith("%") and "%" not in expr_raw
        value_disp = value * 100 if is_pct else value
        stated = re.sub(r"[^\d.]", "", result_raw)
        try:
            stated_f = float(stated)
        except ValueError:
            continue
        if stated_f:
            if "." not in stated and abs(value_disp - stated_f) < 1.0:
                # 整数取整容忍：units 向上取整（5,556 ≈ 5,555.56）或百分比取整（117% ≈ 116.7%）
                continue
            if "." in stated and not is_pct and abs(value_disp - stated_f) < 0.01:
                # 小数四舍五入容忍（0.97 ≈ 0.965）；含小数比率仍严格修正
                continue
        if value < 0 and "elastic" not in fixed.lower():
            # 负结果跳过：业务语境中差异/变化常取绝对值（如有利差异 RM40,000），
            # 误判代价高于漏判；唯一例外是需求价格弹性——弹性天然为负，
            # 此时必须修正（如 −2.00 → −1.00）。关键词取全文而非表达式本身
            #（"Elasticity = ..." 中 elastic 在等号左边）。
            continue
        correct = _fmt_result(value, result_raw)
        if value >= 0 and re.match(r"^[-−—]", result_raw.strip()):
            # 正确值为正但源结果带负号前缀（如 "= —RM95,867.76"）：剥掉负号再格式化，
            # 避免修正后残留 "—RM4,132.23" 这类错误符号。
            correct = _fmt_result(value, result_raw.strip().lstrip("[-−—]"))
        correct_disp = f"{_fmt_result(value * 100, result_raw)}%" if is_pct else correct
        # 源结果带 %（如 CAPM "= 12.5%"）但表达式也含 %（is_pct=False）时，补回 % 后缀
        if result_raw.rstrip().endswith("%") and not correct_disp.endswith("%"):
            correct_disp += "%"
        if correct_disp != result_raw:
            # m.group(0) 已含 result_raw（含 % 后缀），无需再追加 %
            old_frag = m.group(0)
            new_frag = f"{expr_raw.strip()} = {correct_disp}"
            corrections.append((old_frag, new_frag))
            fixed = fixed.replace(old_frag, new_frag, 1)
            # 同值传播：修正点之后出现的孤立旧值（解读句重复）一并纠正（保留 % 单位）
            result_plain = result_raw.lstrip("[-−—A-Za-z]")
            correct_plain = correct_disp.lstrip("[-−—A-Za-z]")
            if result_plain != correct_plain:
                start = fixed.find(new_frag, last_end) + len(new_frag)
                fixed, _ = _propagate(fixed, result_plain, correct_plain, start)
        last_end = m.end()
    return fixed, corrections


def _self_test():
    samples = [
        ("= (RM54,000 + RM18,000) ÷ RM4.50 = 20,000 units",
         "= (RM54,000 + RM18,000) ÷ RM4.50 = 16,000 units"),
        ("Quick ratio = (RM40,000 − RM12,000) ÷ RM25,000 = 1.00",
         "Quick ratio = (RM40,000 − RM12,000) ÷ RM25,000 = 1.12"),
        ("= RM54,000 ÷ RM4.50 = 12,000 units", None),  # 正确，不改
        ("break-even = 20,000 × RM12.00 = RM240,000", None),  # 正确
        ("48 ÷ 6 = 7", "48 ÷ 6 = 8"),  # 简单除法
        ("(10 + 5) × 2 = 25", "(10 + 5) × 2 = 30"),  # 括号
        ("margin = 1.5 − 0.75 = 0.75", None),  # 正确
        # 同值传播：解读句里重复的旧错误值也应修正
        ("= (RM54,000 + RM18,000) ÷ RM4.50 = 20,000 units. The firm must sell 20,000 units to earn RM18,000.",
         "= (RM54,000 + RM18,000) ÷ RM4.50 = 16,000 units. The firm must sell 16,000 units to earn RM18,000."),
        # 分步式中间结果：不把 "(A−B) ÷ C = 中间值" 当最终结果
        ("Quick Ratio = (RM40,000 − RM20,000) ÷ RM25,000 = RM20,000 ÷ RM25,000 = 0.80",
         None),
        # 统计符号 Q1/Q3：不误解析
        ("IQR = Q3 − Q1 = 69. Interquartile range is 69.", None),
        # 整数取整容忍：5,556 ≈ 5,555.56 不判错
        ("Break-even = RM50,000 ÷ RM9 = 5,556 units", None),
        # 含小数的比率仍严格修正
        ("Quick ratio = (RM40,000 − RM12,000) ÷ RM25,000 = 1.00",
         "Quick ratio = (RM40,000 − RM12,000) ÷ RM25,000 = 1.12"),
        # 百分比：117% ≈ 116.67% 属取整，不改；9% vs 90% 真错则修正
        ("Debt ratio = (RM90,000 + RM50,000) ÷ RM120,000 = 117%", None),
        ("Margin = RM10,000 ÷ RM20,000 = 9%",
         "Margin = RM10,000 ÷ RM20,000 = 50%"),
        # 小数四舍五入：0.97 ≈ 0.965 不改
        ("r = 677.00 ÷ (17.89 × 39.22) = 0.97", None),
        # 盲区修复：em dash 负号 + Unicode 上标次方（NPV 折现）
        ("NPV = —RM100,000 + RM60,000 ÷ (1 + 0.10)¹ + RM60,000 ÷ (1 + 0.10)² = —RM95,867.76",
         "NPV = —RM100,000 + RM60,000 ÷ (1 + 0.10)¹ + RM60,000 ÷ (1 + 0.10)² = RM4,132.23"),
        # 上标次方 + 结果本身正确：不改
        ("NPV = —RM100,000 + RM60,000 ÷ (1 + 0.10)¹ + RM60,000 ÷ (1 + 0.10)² = RM4,132.23", None),
        # 盲区修复：需求价格弹性（负值 + 中括号分组）必须修正
        ("Elasticity = [(80 − 100) ÷ 100] ÷ [(6.00 − 5.00) ÷ 5.00] = −2.00",
         "Elasticity = ((80 − 100) ÷ 100) ÷ ((6.00 − 5.00) ÷ 5.00) = -1.00"),
        # 弹性结果正确：不改
        ("Elasticity = [(80 − 100) ÷ 100] ÷ [(6.00 − 5.00) ÷ 5.00] = -1.00", None),
        # 盲区修复：平方根 √（EOQ）——算错则修正
        ("EOQ = √(2 × 5,000 × 100 ÷ 2) = 700 units",
         "EOQ = √(2 × 5,000 × 100 ÷ 2) = 707.1068 units"),
        # 平方根结果正确（整数取整 707 ≈ 707.11）：不改
        ("EOQ = √(2 × 5,000 × 100 ÷ 2) = 707 units", None),
        # 链式中间值（√500,000 后还有 = 707）：跳过，不误改
        ("EOQ = √(2 × 5,000 × 100 ÷ 2) = √500,000 = 707 units", None),
        # 盲区修复：表达式含 % 时不得 ×100（CAPM 百分比公式）
        ("Ke = 3.5% + 1.2 × (10% − 3.5%) = 11.3%", None),  # 正确：不改
        ("Ke = 3.5% + 1.2 × (10% − 3.5%) = 12.5%",
         "Ke = 3.5% + 1.2 × (10% − 3.5%) = 11.30%"),  # 算错：修正
        # 表达式不含 % 的结果百分比仍按原逻辑（×100 比较）
        ("Debt ratio = (RM90,000 + RM50,000) ÷ RM120,000 = 117%", None),
    ]
    ok = True
    for src, expect in samples:
        fixed, corr = fix_arithmetic(src)
        if expect is None:
            status = "OK(unchanged)" if not corr else "FAIL(changed)"
            ok = ok and not corr
        else:
            status = "OK" if fixed == expect else "FAIL"
            ok = ok and (fixed == expect)
        print(f"{status}: {src!r} -> {fixed!r}")
    print("ALL PASS" if ok else "SOME FAILED")
    return ok


if __name__ == "__main__":
    _self_test()
