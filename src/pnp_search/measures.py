"""Exact complexity measures and a bounded arithmetic DSL without code execution."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from fractions import Fraction
from typing import Protocol

from .boolean import BooleanFunction


class ComplexityMeasure(Protocol):
    """A named exact numeric function of a Boolean truth table."""

    name: str

    def evaluate(self, function: BooleanFunction) -> int | Fraction:
        """Evaluate this measure exactly."""
        ...

    def __call__(self, function: BooleanFunction) -> int | Fraction:
        """Evaluate this measure exactly."""
        ...


@dataclass(frozen=True)
class PrimitiveMeasure:
    """Evaluate one predefined, audited primitive property."""

    name: str

    def __post_init__(self) -> None:
        """Reject names outside the fixed registry."""
        if self.name not in _PROPERTIES:
            raise ValueError(f"unknown measure: {self.name}")

    def evaluate(self, function: BooleanFunction) -> int | Fraction:
        """Read the explicitly registered property."""
        return getattr(function, _PROPERTIES[self.name])

    def __call__(self, function: BooleanFunction) -> int | Fraction:
        """Evaluate the primitive."""
        return self.evaluate(function)


_PROPERTIES = {
    "truth_table_weight": "weight",
    "sensitivity": "sensitivity",
    "average_sensitivity": "average_sensitivity",
    "algebraic_degree": "algebraic_degree",
    "fourier_l1": "fourier_l1",
    "fourier_l2": "fourier_l2",
    "number_of_monomials": "number_of_monomials",
    "certificate_complexity": "certificate_complexity",
    "decision_tree_depth": "decision_tree_depth",
}


class AlgebraicDegree(PrimitiveMeasure):
    """Degree of the unique multilinear polynomial over GF(2)."""

    def __init__(self) -> None:
        """Select the algebraic-degree primitive."""
        super().__init__("algebraic_degree")


class TruthTableWeight(PrimitiveMeasure):
    """Number of satisfying assignments."""

    def __init__(self) -> None:
        """Select the Hamming-weight primitive."""
        super().__init__("truth_table_weight")


class Sensitivity(PrimitiveMeasure):
    """Maximum number of sensitive coordinates at any input."""

    def __init__(self) -> None:
        """Select the sensitivity primitive."""
        super().__init__("sensitivity")


def get_measure(name: str) -> PrimitiveMeasure:
    """Resolve a primitive name; never import or execute generated code."""
    return PrimitiveMeasure(name)


def available_measures() -> tuple[str, ...]:
    """List supported primitive names in stable order."""
    return tuple(_PROPERTIES)


@dataclass(frozen=True)
class CompositeMeasure:
    """Arithmetic combination of registered primitives and small integers.

    Supported grammar: primitive names, integers 0..1000, +, -, *, and binary
    min/max.  Input length and AST size are bounded; no eval/exec is used.
    """

    name: str

    def __post_init__(self) -> None:
        """Validate the complete expression before any evaluation."""
        self._tree()

    def _tree(self) -> ast.Expression:
        """Parse a small expression and reject every non-whitelisted node."""
        if len(self.name) > 512:
            raise ValueError("measure expression exceeds 512 characters")
        try:
            tree = ast.parse(self.name, mode="eval")
        except (SyntaxError, RecursionError) as exc:
            raise ValueError("invalid measure expression") from exc
        if len(list(ast.walk(tree))) > 64:
            raise ValueError("measure expression exceeds AST size limit")
        def validate(node: ast.AST) -> None:
            if isinstance(node, ast.Name) and node.id in _PROPERTIES:
                return
            if isinstance(node, ast.Constant) and type(node.value) is int and 0 <= node.value <= 1000:
                return
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
                validate(node.left)
                validate(node.right)
                return
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("min", "max") and len(node.args) == 2 and not node.keywords:
                for argument in node.args:
                    validate(argument)
                return
            raise ValueError("unsupported measure DSL construct")
        validate(tree.body)
        return tree

    def evaluate(self, function: BooleanFunction) -> int | Fraction:
        """Evaluate the validated tree with explicit arithmetic operations."""
        def visit(node: ast.AST) -> int | Fraction:
            if isinstance(node, ast.Name):
                return get_measure(node.id).evaluate(function)
            if isinstance(node, ast.Constant):
                return node.value
            if isinstance(node, ast.BinOp):
                left, right = visit(node.left), visit(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                return left * right
            if isinstance(node, ast.Call):
                values = [visit(argument) for argument in node.args]
                return min(values) if node.func.id == "min" else max(values)
            raise AssertionError("unexpected validated DSL node")
        return visit(self._tree().body)

    def __call__(self, function: BooleanFunction) -> int | Fraction:
        """Evaluate the composite measure."""
        return self.evaluate(function)


def parse_measure(expression: str) -> PrimitiveMeasure | CompositeMeasure:
    """Resolve a primitive or validate an arithmetic measure expression."""
    return get_measure(expression) if expression in _PROPERTIES else CompositeMeasure(expression)
