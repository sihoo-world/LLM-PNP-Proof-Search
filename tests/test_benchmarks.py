"""Replay committed benchmark fixtures against the exact finite verifier."""

from pathlib import Path

from pnp_search.boolean import BooleanFunction
from pnp_search.measures import parse_measure
from pnp_search.models import CandidateStatus, UniversalBinaryOperationBound
from pnp_search.storage import read_jsonl
from pnp_search.verifiers import ExhaustiveVerifier
from pnp_search.verifiers.exhaustive import apply_operation
from pnp_search.verifiers.dsl import BoundExpression


def test_committed_three_measure_benchmarks() -> None:
    """Each published n=3 benchmark matches its status and reproducible witness."""
    benchmark_path = Path(__file__).resolve().parents[1] / "data" / "benchmark" / "operation-bounds.jsonl"
    fixtures = list(read_jsonl(benchmark_path))
    assert len(fixtures) == 3
    assert {item["bound"]["measure"] for item in fixtures} == {
        "algebraic_degree", "truth_table_weight", "sensitivity",
    }
    for item in fixtures:
        assert item["n"] == 3
        claim = UniversalBinaryOperationBound.model_validate(item["bound"])
        result = ExhaustiveVerifier(n=item["n"]).verify(claim)
        assert result.status.value == item["expected_status"], item["benchmark_id"]
        assert result.complete
        assert result.verified_for_n == 3
        assert result.status != CandidateStatus.formally_verified
        if "witness" not in item:
            assert not result.counterexample_found
            assert result.cases_checked == 65_536
            continue
        assert result.counterexample_found
        witness = item["witness"]
        assert result.counterexample["f"]["bits"] == witness["f_bits"]
        assert result.counterexample["g"]["bits"] == witness["g_bits"]
        f, g = BooleanFunction(3, witness["f_bits"]), BooleanFunction(3, witness["g_bits"])
        measure = parse_measure(claim.measure)
        output = apply_operation(claim.operation, f, g)
        rhs = BoundExpression(claim.rhs).evaluate(measure(f), measure(g))
        assert measure(output) > rhs
