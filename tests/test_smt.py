"""Z3 finite encodings are checked against independent exhaustive results."""

import pytest

pytest.importorskip("z3")

from pnp_search.models import CandidateStatus, UniversalBinaryOperationBound
from pnp_search.verifiers import ExhaustiveVerifier, SMTVerifier


@pytest.mark.parametrize("operation,rhs", [
    ("AND", "M(f) + M(g)"), ("AND", "M(f) / 2"),
    ("OR", "M(f) + M(g)"), ("OR", "M(f)"),
    ("XOR", "M(f) + M(g)"), ("XOR", "M(f)"),
    ("NOT", "4 - M(f)"), ("NOT", "M(f)"),
])
def test_smt_agrees_with_exhaustive_finite_weight_claims(operation, rhs):
    bound = UniversalBinaryOperationBound(operation=operation, measure="truth_table_weight", rhs=rhs)
    exhaustive = ExhaustiveVerifier(n=2).verify(bound)
    smt = SMTVerifier(n=2, seed=42).verify(bound)
    assert smt.status == exhaustive.status
    assert smt.complete
    assert smt.status != CandidateStatus.formally_verified
    if smt.counterexample_found:
        assert smt.counterexample["n"] == 2
        assert smt.cases_checked == 1


def test_smt_unsupported_measure_is_honest():
    bound = UniversalBinaryOperationBound(operation="AND", measure="algebraic_degree", rhs="M(f)+M(g)")
    result = SMTVerifier(n=3).verify(bound)
    assert result.status == CandidateStatus.unsupported
    assert not result.complete


def test_smt_rejects_unsafe_rhs():
    bound = UniversalBinaryOperationBound(operation="AND", measure="truth_table_weight", rhs="__import__('os')")
    assert SMTVerifier().verify(bound).status == CandidateStatus.unsupported
