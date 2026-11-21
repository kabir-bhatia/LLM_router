"""Safe arithmetic evaluator: parses with ast, allows only numbers and + - * / ** and unary +/-.
Never calls eval()/exec(). All arithmetic is exact (fractions.Fraction)."""
from __future__ import annotations

import ast
from fractions import Fraction

_BIN = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
}


class UnsafeExpression(ValueError):
    pass


def safe_eval(expr: str) -> Fraction:
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError as e:
        raise UnsafeExpression(f"syntax: {e}") from e
    return _ev(tree.body)


def _ev(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
        return Fraction(str(n.value))
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
        v = _ev(n.operand)
        return -v if isinstance(n.op, ast.USub) else v
    if isinstance(n, ast.BinOp):
        if isinstance(n.op, ast.Pow):
            base, exp = _ev(n.left), _ev(n.right)
            if exp.denominator != 1 or not (0 <= exp <= 20):
                raise UnsafeExpression("exponent must be an integer in 0..20")
            return base ** int(exp)
        f = _BIN.get(type(n.op))
        if f is None:
            raise UnsafeExpression(f"operator {type(n.op).__name__}")
        a, b = _ev(n.left), _ev(n.right)
        if isinstance(n.op, ast.Div) and b == 0:
            raise UnsafeExpression("division by zero")
        return f(a, b)
    raise UnsafeExpression(f"node {type(n).__name__}")


def fmt(x: Fraction):
    """Integer, or a decimal with at most 2 places; anything else -> None (caller defers)."""
    if x.denominator == 1:
        return str(x.numerator)
    if (x * 100).denominator == 1:
        return f"{float(x):.2f}".rstrip("0").rstrip(".")
    return None
