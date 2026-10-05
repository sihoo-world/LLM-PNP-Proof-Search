"""A tiny arithmetic language for operation bounds, without Python execution.

Only integer literals, M(f), M(g), addition, subtraction, multiplication and
division by a nonzero constant expression are accepted. All evaluation uses
exact rational arithmetic (or symbolic rational SMT arithmetic).
"""

from __future__ import annotations

import ast
from fractions import Fraction
from typing import Any


class UnsupportedBound(ValueError):
    """The statement is outside the deliberately small executable language."""


class BoundExpression:
    """Validate and evaluate an arithmetic right-hand-side expression safely."""

    def __init__(self, source: str, *, unary: bool = False) -> None:
        if not isinstance(source, str) or len(source) > 256:
            raise UnsupportedBound("RHS must be a string of at most 256 characters")
        try:
            tree = ast.parse(source, mode="eval")
        except (SyntaxError, ValueError, RecursionError) as exc:
            raise UnsupportedBound("RHS is not valid bound arithmetic") from exc
        if len(list(ast.walk(tree))) > 64:
            raise UnsupportedBound("RHS exceeds the 64-node complexity limit")
        self.source = source
        self.unary = unary
        self._root = tree.body
        self._validate(self._root)
        # Evaluating once checks constant denominators before any search starts.
        self.evaluate(Fraction(0), Fraction(0))

    def _validate(self, node: ast.AST) -> None:
        if isinstance(node, ast.Constant):
            if type(node.value) is not int or abs(node.value) > 1_000_000:
                raise UnsupportedBound("Only integer constants of magnitude <= 1000000 are allowed")
            return
        if isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "M"
                and len(node.args) == 1
                and not node.keywords
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in ({"f"} if self.unary else {"f", "g"})
            ):
                return
            raise UnsupportedBound("Only M(f) and, for binary operations, M(g) are allowed")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            self._validate(node.operand)
            return
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            self._validate(node.left)
            self._validate(node.right)
            if isinstance(node.op, ast.Div) and any(isinstance(x, ast.Call) for x in ast.walk(node.right)):
                raise UnsupportedBound("Division is allowed only by a nonzero constant expression")
            return
        raise UnsupportedBound(f"Unsupported RHS syntax: {type(node).__name__}")

    def evaluate(self, f_value: Any, g_value: Any = None) -> Any:
        """Evaluate a previously validated AST over exact or symbolic values."""
        def visit(node: ast.AST) -> Any:
            if isinstance(node, ast.Constant):
                return Fraction(node.value)
            if isinstance(node, ast.Call):
                return f_value if node.args[0].id == "f" else g_value
            if isinstance(node, ast.UnaryOp):
                value = visit(node.operand)
                return -value if isinstance(node.op, ast.USub) else value
            if isinstance(node, ast.BinOp):
                left, right = visit(node.left), visit(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
                if right == 0:
                    raise UnsupportedBound("RHS divides by zero")
                return left / right
            raise UnsupportedBound("Unexpected AST node")

        return visit(self._root)
