"""Independent finite checks for truth-table conventions and exact mathematics."""

from fractions import Fraction

import pytest

from pnp_search.boolean import BooleanFunction, enumerate_functions


def test_encoding_and_domain() -> None:
    """All two-variable tables round-trip and invalid domains fail closed."""
    for function in enumerate_functions(2):
        assert BooleanFunction.from_truth_table(function.truth_table) == function
    assert BooleanFunction.variable(3, 0).truth_table == (0, 1, 0, 1, 0, 1, 0, 1)
    assert BooleanFunction.variable(3, 2).truth_table == (0, 0, 0, 0, 1, 1, 1, 1)
    for n, bits in ((-1, 0), (6, 0), (2, -1), (2, 16), (True, 0), (2, True)):
        with pytest.raises(ValueError):
            BooleanFunction(n, bits)
    for table in ((), (0, 1, 0), (0, 2), (0.0, 1.0)):
        with pytest.raises(ValueError):
            BooleanFunction.from_truth_table(table)


def test_pointwise_operations_exhaustive() -> None:
    """Every pair of two-variable functions agrees with scalar Boolean logic."""
    for f in enumerate_functions(2):
        assert (~f).truth_table == tuple(1 - value for value in f.truth_table)
        for g in enumerate_functions(2):
            for assignment in range(4):
                assert (f & g)(assignment) == int(bool(f(assignment)) and bool(g(assignment)))
                assert (f | g)(assignment) == int(bool(f(assignment)) or bool(g(assignment)))
                assert (f ^ g)(assignment) == int(f(assignment) != g(assignment))
    with pytest.raises(ValueError):
        BooleanFunction(1, 0) & BooleanFunction(2, 0)


def test_enumeration_guard() -> None:
    """n=4 has exactly 65,536 functions; n=5 requires a different strategy."""
    assert sum(1 for _ in enumerate_functions(4)) == 65536
    assert len(list(enumerate_functions(0))) == 2
    with pytest.raises(ValueError):
        enumerate_functions(5)


def test_composition() -> None:
    """Substitution respects the documented little-endian variable order."""
    outer = BooleanFunction.variable(2, 0) & ~BooleanFunction.variable(2, 1)
    x, y, z = [BooleanFunction.variable(3, j) for j in range(3)]
    assert outer.compose([x ^ y, z]) == ((x ^ y) & ~z)
    with pytest.raises(ValueError):
        outer.compose([x])
    with pytest.raises(ValueError):
        outer.compose([x, BooleanFunction.variable(2, 0)])


def test_standard_functions() -> None:
    """Parity and conjunction have independently known exact complexities."""
    variables = [BooleanFunction.variable(3, j) for j in range(3)]
    parity = variables[0] ^ variables[1] ^ variables[2]
    conjunction = variables[0] & variables[1] & variables[2]
    assert parity.weight == 4
    assert parity.sensitivity == 3
    assert parity.average_sensitivity == 3
    assert parity.algebraic_degree == 1
    assert parity.number_of_monomials == 3
    assert parity.fourier_l1 == 1
    assert parity.decision_tree_depth == parity.certificate_complexity == 3
    assert conjunction.weight == 1
    assert conjunction.sensitivity == 3
    assert conjunction.average_sensitivity == Fraction(3, 4)
    assert conjunction.influence(0) == Fraction(1, 4)
    assert conjunction.algebraic_degree == 3
    assert conjunction.number_of_monomials == 1
    assert conjunction.fourier_l1 == Fraction(5, 2)
    assert conjunction.decision_tree_depth == conjunction.certificate_complexity == 3


def test_anf_and_fourier_inversion_exhaustive() -> None:
    """All three-variable functions reconstruct from each exact transform."""
    for f in enumerate_functions(3):
        anf = f.anf_coefficients
        spectrum = f.fourier_coefficients
        assert f.fourier_l2_squared == 1
        for assignment in range(8):
            polynomial = sum(coefficient for subset, coefficient in enumerate(anf) if (assignment & subset) == subset) % 2
            sign = sum(coefficient * (-1 if (assignment & subset).bit_count() % 2 else 1) for subset, coefficient in enumerate(spectrum))
            assert polynomial == f(assignment)
            assert sign == 1 - 2 * f(assignment)


def test_zero_variable_constants() -> None:
    """Constants include the degenerate zero-variable domain."""
    for value in (0, 1):
        f = BooleanFunction.constant(0, value)
        assert f.truth_table == (value,)
        assert f.sensitivity == f.average_sensitivity == f.algebraic_degree == 0
        assert f.decision_tree_depth == f.certificate_complexity == 0
        assert f.fourier_l1 == f.fourier_l2 == 1


def test_expression_variable_order() -> None:
    """The human-readable expression uses the same coordinate convention."""
    from sympy import Symbol

    for f in enumerate_functions(2):
        expression = f.to_expression()
        for assignment in range(4):
            values = {Symbol(f"x{j}"): bool((assignment >> j) & 1) for j in range(2)}
            assert bool(expression.subs(values)) == bool(f(assignment))
