"""Concrete, JSON-safe counterexample records."""

from __future__ import annotations

from fractions import Fraction
from typing import Any


def exact_json(value: int | Fraction) -> int | str:
    """Preserve rational numbers without rounding them to floating point."""
    rational = Fraction(value)
    return rational.numerator if rational.denominator == 1 else str(rational)


def function_record(function: Any) -> dict[str, Any]:
    """Encode the exact truth table and a human-readable Boolean expression."""
    record: dict[str, Any] = {
        "n": function.n,
        "bits": function.bits,
        "truth_table": list(function.truth_table),
    }
    # A missing pretty-print dependency must not erase a concrete falsification.
    try:
        record["expression"] = str(function.to_expression())
    except ImportError:
        record["expression"] = None
        record["expression_note"] = "Install sympy to render a Boolean expression."
    return record


def build_counterexample(
    *, f: Any, g: Any | None, output: Any, operation: str,
    measure_name: str, f_value: Fraction, g_value: Fraction | None,
    lhs: Fraction, rhs: Fraction, rhs_source: str,
) -> dict[str, Any]:
    """Return a complete witness to a failed finite operation inequality."""
    return {
        "n": f.n,
        "f": function_record(f),
        "g": function_record(g) if g is not None else None,
        "output": function_record(output),
        "operation": operation,
        "measure": measure_name,
        "M(f)": exact_json(f_value),
        "M(g)": exact_json(g_value) if g_value is not None else None,
        "M(f op g)": exact_json(lhs),
        "rhs_value": exact_json(rhs),
        "violated_inequality": f"{exact_json(lhs)} <= {exact_json(rhs)}",
        "rhs_expression": rhs_source,
    }
