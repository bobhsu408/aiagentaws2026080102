"""公式與條件式安全求值模組

resources.json 內含兩種需要求值的字串：

1. benefit 公式（formula）：如 "avg_insured_salary * 0.6"、"hours * 70"
2. 條件式（condition_field）：如 "age >= 45"、"has_disability_cert == true"

本模組以 Python `ast` 白名單方式求值，**不使用內建 eval**，
只允許數值運算與比較，避免任意程式碼執行的風險。
"""

import ast
import operator
import re
from typing import Any

# 允許的二元運算子
_BIN_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# 允許的比較運算子
_CMP_OPS: dict[type, Any] = {
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
}

# 允許的一元運算子
_UNARY_OPS: dict[type, Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Not: operator.not_,
}


class MissingVariableError(Exception):
    """公式中引用了 context 未提供的變數時拋出。"""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"缺少變數：{name}")


def _normalize(expr: str) -> str:
    """將 JS 風格的字面量轉為 Python 可解析形式。

    condition_field 使用 `true`/`false`（小寫），Python ast 無法解析，
    需轉為 `True`/`False`。以字界限比對避免誤換變數名。

    Args:
        expr: 原始運算式字串

    Returns:
        正規化後的運算式字串
    """
    expr = re.sub(r"\btrue\b", "True", expr)
    expr = re.sub(r"\bfalse\b", "False", expr)
    return expr


def _eval_node(node: ast.AST, context: dict[str, Any]) -> Any:
    """遞迴求值單一 AST 節點（白名單）。

    Args:
        node: AST 節點
        context: 變數名 → 值的對應

    Returns:
        求值結果

    Raises:
        MissingVariableError: 變數不在 context 中
        ValueError: 遇到不允許的語法
    """
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, context)

    # 數值 / 字串 / 布林字面量
    if isinstance(node, ast.Constant):
        return node.value

    # 變數名
    if isinstance(node, ast.Name):
        if node.id in context:
            value = context[node.id]
            if value is None:
                raise MissingVariableError(node.id)
            return value
        raise MissingVariableError(node.id)

    # 二元運算
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BIN_OPS:
            raise ValueError(f"不允許的運算子：{op_type.__name__}")
        left = _eval_node(node.left, context)
        right = _eval_node(node.right, context)
        return _BIN_OPS[op_type](left, right)

    # 一元運算
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPS:
            raise ValueError(f"不允許的一元運算子：{op_type.__name__}")
        return _UNARY_OPS[op_type](_eval_node(node.operand, context))

    # 比較
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, context)
        result = True
        for op, comparator in zip(node.ops, node.comparators):
            op_type = type(op)
            if op_type not in _CMP_OPS:
                raise ValueError(f"不允許的比較運算子：{op_type.__name__}")
            right = _eval_node(comparator, context)
            result = result and _CMP_OPS[op_type](left, right)
            left = right
        return result

    # 布林運算（and / or）
    if isinstance(node, ast.BoolOp):
        values = [_eval_node(v, context) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        return any(values)

    raise ValueError(f"不允許的語法節點：{type(node).__name__}")


def evaluate_formula(formula: str, context: dict[str, Any]) -> float | None:
    """求值金額公式。

    Args:
        formula: 公式字串，如 "avg_insured_salary * 0.6"
        context: 變數對應，如 {"avg_insured_salary": 44100}

    Returns:
        計算結果（float）；若缺少變數或公式無效，回傳 None。
    """
    if not formula or not isinstance(formula, str):
        return None
    try:
        tree = ast.parse(_normalize(formula), mode="eval")
        result = _eval_node(tree, context)
        return float(result)
    except (MissingVariableError, ValueError, SyntaxError, TypeError, ZeroDivisionError):
        return None


def evaluate_condition(condition: str, context: dict[str, Any]) -> bool | None:
    """求值條件式。

    Args:
        condition: 條件字串，如 "age >= 45"
        context: 變數對應，如 {"age": 58}

    Returns:
        True / False；若缺少變數無法判斷，回傳 None（代表「待確認」）。
    """
    if not condition or not isinstance(condition, str):
        return None
    try:
        tree = ast.parse(_normalize(condition), mode="eval")
        return bool(_eval_node(tree, context))
    except MissingVariableError:
        return None
    except (ValueError, SyntaxError, TypeError):
        return None


def find_missing_variables(formula: str, context: dict[str, Any]) -> list[str]:
    """找出公式中 context 未提供（或值為 None）的變數名。

    Args:
        formula: 公式或條件字串
        context: 變數對應

    Returns:
        缺少的變數名清單。
    """
    if not formula or not isinstance(formula, str):
        return []
    try:
        tree = ast.parse(_normalize(formula), mode="eval")
    except SyntaxError:
        return []
    missing: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            name = node.id
            if name in ("True", "False"):
                continue
            if context.get(name) is None and name not in missing:
                missing.append(name)
    return missing
