"""Safe measure composition and registry checks."""

import pytest

from pnp_search.boolean import BooleanFunction
from pnp_search.measures import AlgebraicDegree, Sensitivity, TruthTableWeight, available_measures, get_measure, parse_measure


def test_measure_objects() -> None:
    """The three primary measures have stable names and exact values."""
    f = BooleanFunction.variable(3, 0) ^ BooleanFunction.variable(3, 1)
    assert AlgebraicDegree().name == "algebraic_degree"
    assert AlgebraicDegree().evaluate(f) == 1
    assert Sensitivity()(f) == 2
    assert TruthTableWeight()(f) == 4
    assert all(get_measure(name).evaluate(f) >= 0 for name in available_measures())


def test_composite_arithmetic() -> None:
    """Predefined primitives compose without floating-point conversion."""
    f = BooleanFunction.variable(2, 0)
    assert parse_measure("2 * sensitivity + algebraic_degree")(f) == 3
    assert parse_measure("max(truth_table_weight, algebraic_degree) - 1")(f) == 1
    assert parse_measure("min(average_sensitivity, 0)")(f) == 0


@pytest.mark.parametrize("expression", [
    "__import__('os').system('whoami')", "sensitivity.__class__", "sensitivity[0]",
    "lambda: 0", "[sensitivity]", "2 ** 100", "1 / 0", "True", "-1",
    "max(sensitivity, key=1)", "unknown_measure", "1001", "1" * 513,
    "+".join(["sensitivity"] * 30),
])
def test_dsl_rejects_unapproved_syntax(expression: str) -> None:
    """Generated code, huge expressions, and ambiguous numeric values are rejected."""
    with pytest.raises(ValueError):
        parse_measure(expression)
