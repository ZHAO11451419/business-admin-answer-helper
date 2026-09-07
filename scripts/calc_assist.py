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
}

_TRANSLATE = str.maketrans({"÷": "/", "×": "*", "−": "-", "—": "-"})

_NUM = r"(?:[A-Za-z]*\d[\d,]*(?:\.\d+)?)"   # 数字，允许 RM/units 等字母前缀
# 操作数：纯数字，或"括号内至少两操作数一运算符"的复合表达式
_ATOM = rf"(?:\({_NUM}(?:\s*[\/÷×\*+\-−]\s*{_NUM})+\)|{_NUM})"
# 表达式 = 结果：表达式为"至少两个操作数 + 至少一个运算符"，结果紧随等号
_EXPR_EQ = re.compile(
    rf"({_ATOM}(?:\s*[\/÷×\*+\-−]\s*{_ATOM})+)\s*=\s*({_NUM})"
)


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
    """把精确结果按源数字的风格格式化（保留字母前缀 + 千分位 + 小数位）。"""
    m = re.match(r"([A-Za-z]*)(.*)", source_num.strip())
    prefix, src = m.group(1), m.group(2)
    if "." in src:
        decimals = len(src.split(".")[1])
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
    """把模型文本表达式转成 Python 可求值形式（去掉字母/货币前缀）。"""
    s = re.sub(r"[A-Za-z]", "", s)
    return s.translate(_TRANSLATE).replace(",", "").strip()


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
    fixed = text
    last_end = 0
    for m in _EXPR_EQ.finditer(fixed):
        expr_raw, result_raw = m.group(1), m.group(2)
        expr = _normalise(expr_raw)
        try:
            value = _safe_eval(expr)
        except Exception:
            continue
        if not isinstance(value, (int, float)) or value != value:  # 非数值/NaN
            continue
        correct = _fmt_result(value, result_raw)
        if correct != result_raw:
            old_frag = m.group(0)
            new_frag = f"{expr_raw.strip()} = {correct}"
            corrections.append((old_frag, new_frag))
            fixed = fixed.replace(old_frag, new_frag, 1)
            # 同值传播：修正点之后出现的孤立旧值（解读句重复）一并纠正
            result_plain = result_raw.lstrip("A-Za-z")
            if result_plain != correct.lstrip("A-Za-z"):
                start = fixed.find(new_frag, last_end) + len(new_frag)
                fixed, _ = _propagate(fixed, result_plain, correct.lstrip("A-Za-z"), start)
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
