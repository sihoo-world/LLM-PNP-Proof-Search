"""Finite search regressions focused on mathematical evidence boundaries."""

from fractions import Fraction

import pytest

from pnp_search.boolean import BooleanFunction
from pnp_search.measures import AlgebraicDegree, parse_measure
from pnp_search.models import CandidateLemma, CandidateStatus, UniversalBinaryOperationBound, VerificationResult
from pnp_search.verifiers import ExhaustiveVerifier, SATVerifier
from pnp_search.verifiers.dsl import BoundExpression, UnsupportedBound


def bound(measure="truth_table_weight", operation="AND", rhs="M(f) + M(g)"):
    return UniversalBinaryOperationBound(measure=measure, operation=operation, rhs=rhs)


def test_degree_and_subadditivity_has_no_counterexample_at_n3():
    """GF(2) multiplication degree is subadditive, including the zero polynomial."""
    result = ExhaustiveVerifier(n=3).verify(bound(AlgebraicDegree()))
    assert result.status == CandidateStatus.empirically_survived
    assert result.verified_for_n == 3
    assert result.complete and result.cases_checked == 65_536
    assert not result.counterexample_found
    assert result.status != CandidateStatus.formally_verified


@pytest.mark.parametrize("measure", ["truth_table_weight", "sensitivity", "algebraic_degree"])
def test_three_measures_share_binary_bound_interface(measure):
    result = ExhaustiveVerifier(n=2).verify(bound(measure))
    assert result.status == CandidateStatus.empirically_survived
    assert result.cases_checked == 256


def test_false_weight_xor_bound_produces_replayable_counterexample():
    claim = bound(operation="XOR", rhs="M(f)")
    result = ExhaustiveVerifier(n=3).verify(claim)
    assert result.status == CandidateStatus.falsified
    assert result.complete and result.counterexample_found
    witness = result.counterexample
    f, g = BooleanFunction(3, witness["f"]["bits"]), BooleanFunction(3, witness["g"]["bits"])
    measure = parse_measure(claim.measure)
    assert list(f.truth_table) == witness["f"]["truth_table"]
    assert measure.evaluate(f ^ g) > measure.evaluate(f)
    assert witness["M(f op g)"] > witness["rhs_value"]
    assert witness["f"]["expression"]
    assert VerificationResult.model_validate_json(result.model_dump_json()) == result


def test_case_budget_exhaustion_is_unknown_and_incomplete():
    result = ExhaustiveVerifier(n=4, max_cases=3).verify(bound())
    assert result.status == CandidateStatus.unknown
    assert result.cases_checked == 3
    assert not result.complete and not result.counterexample_found


def test_budget_exactly_equal_to_search_space_completes():
    result = ExhaustiveVerifier(n=1, max_cases=16).verify(bound())
    assert result.status == CandidateStatus.empirically_survived
    assert result.cases_checked == 16


def test_unary_not_degree_inequality():
    result = ExhaustiveVerifier(n=3).verify(bound("algebraic_degree", "NOT", "M(f)"))
    assert result.status == CandidateStatus.empirically_survived
    assert result.cases_checked == 256


def test_weight_not_bound_is_falsified():
    result = ExhaustiveVerifier(n=3).verify(bound(operation="NOT", rhs="M(f)"))
    assert result.status == CandidateStatus.falsified
    assert result.counterexample["g"] is None
    assert result.counterexample["M(g)"] is None


@pytest.mark.parametrize("source", [
    "__import__('os').system('whoami')", "M(f).__class__", "2 ** 1000000",
    "M(f) / M(g)", "M(f) / 0", "M(f) / (1 - 1)", "True", "0.5", "M(f)[0]",
    "max(M(f), M(g))", "M(h)", "M(f, g)", "[M(f)]", "1000001",
])
def test_unsupported_rhs_never_executes_or_survives(source):
    result = ExhaustiveVerifier(n=1).verify(bound(rhs=source))
    assert result.status == CandidateStatus.unsupported
    assert result.cases_checked == 0 and not result.complete


def test_rhs_exact_rational_arithmetic():
    expression = BoundExpression("(M(f) + 1) / 3 - M(g) * 2")
    assert expression.evaluate(Fraction(1), Fraction(1, 4)) == Fraction(1, 6)


def test_rhs_complexity_limit_and_unary_scope():
    with pytest.raises(UnsupportedBound):
        BoundExpression("1+" * 100 + "1")
    with pytest.raises(UnsupportedBound):
        BoundExpression("M(g)", unary=True)


def test_composite_measure_and_fraction_witness_are_serializable():
    result = ExhaustiveVerifier(n=3).verify(bound("average_sensitivity + truth_table_weight", "OR", "M(f) / 3"))
    assert result.status == CandidateStatus.falsified
    assert result.counterexample["M(f op g)"] == "7/4"
    assert VerificationResult.model_validate_json(result.model_dump_json()) == result


def test_unknown_measure_is_unsupported():
    result = ExhaustiveVerifier(n=1).verify(bound("unimplemented_measure"))
    assert result.status == CandidateStatus.unsupported


def test_optional_pretty_print_failure_does_not_erase_falsification(monkeypatch):
    def unavailable(_function):
        raise ModuleNotFoundError("sympy")

    monkeypatch.setattr(BooleanFunction, "to_expression", unavailable)
    result = ExhaustiveVerifier(n=1).verify(bound(operation="XOR", rhs="M(f)"))
    assert result.status == CandidateStatus.falsified
    assert result.counterexample["f"]["expression"] is None
    assert result.counterexample["f"]["truth_table"] == [0, 0]


def test_candidate_is_immediately_marked_falsified():
    candidate = CandidateLemma(experiment_id="test", model="mock", title="false",
        natural_language_statement="Weight of f XOR g is at most weight of f.",
        source_output="{}", bound=bound(operation="XOR", rhs="M(f)"))
    result = ExhaustiveVerifier(n=2).verify(candidate)
    assert candidate.status == CandidateStatus.falsified
    assert candidate.counterexample == result.counterexample
    assert candidate.classification == "false_claim"
    assert candidate.verification_history == [result]


def test_missing_formalization_and_unchecked_assumptions_are_unsupported():
    candidate = CandidateLemma(experiment_id="test", model="mock", title="free prose",
        natural_language_statement="A general conjecture", source_output="{}")
    assert ExhaustiveVerifier(n=1).verify(candidate).status == CandidateStatus.unsupported
    candidate.bound = bound()
    candidate.assumptions = ["f is monotone"]
    assert ExhaustiveVerifier(n=1).verify(candidate).status == CandidateStatus.unsupported


def test_sat_skeleton_does_not_claim_success():
    assert SATVerifier().verify(bound()).status == CandidateStatus.unsupported


@pytest.mark.parametrize("kwargs", [{"n": 5}, {"n": -1}, {"n": True}, {"max_cases": 0}, {"max_cases": True}])
def test_invalid_search_budget_rejected(kwargs):
    with pytest.raises(ValueError):
        ExhaustiveVerifier(**kwargs)


def test_arity_zero_is_a_valid_two_constant_domain():
    result = ExhaustiveVerifier(n=0).verify(bound())
    assert result.status == CandidateStatus.empirically_survived
    assert result.cases_checked == 4
