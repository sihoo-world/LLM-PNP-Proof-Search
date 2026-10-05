"""Barrier keyword triage never promotes candidates to mathematical facts."""

import pytest

from pnp_search.classifiers import classify_barriers
from pnp_search.models import CandidateLemma, CandidateStatus


def candidate(statement: str, *, proof_sketch: str = "", assumptions: list[str] | None = None) -> CandidateLemma:
    """Construct an unverified fixture with no mathematical status assigned."""
    return CandidateLemma(
        experiment_id="barrier-tests", model="mock", title="Unverified candidate",
        natural_language_statement=statement, proof_sketch=proof_sketch,
        assumptions=assumptions or [], source_output="{}",
    )


@pytest.mark.parametrize("statement,label", [
    ("The argument relativizes to every oracle.", "likely_relativizing"),
    ("The property has largeness and constructivity.", "possibly_natural"),
    ("Consider a natural proof.", "possibly_natural"),
    ("The statement concerns pseudorandom functions.", "possibly_natural"),
    ("Consider algebraic extensions of the oracle.", "possible_algebrization_issue"),
    ("An ALgebrization issue requires review.", "possible_algebrization_issue"),
])
def test_matching_terms_flag_review_without_status_promotion(statement, label):
    item = candidate(statement)
    original = item.model_dump(mode="json")
    labels = classify_barriers(item)
    assert label in labels
    assert "manual_review_required" in labels
    assert "no_obvious_barrier_detected" not in labels
    assert item.model_dump(mode="json") == original
    assert item.status == CandidateStatus.generated


def test_unmatched_text_means_only_no_obvious_barrier():
    item = candidate("Conjunction is commutative.")
    labels = classify_barriers(item)
    assert labels == ["no_obvious_barrier_detected", "manual_review_required"]
    assert item.status == CandidateStatus.generated
    assert item.classification == "unknown"
    assert item.formalization_review_required


def test_classifier_scans_proof_sketch_and_assumptions_and_preserves_terminal_status():
    item = candidate("Candidate inequality", proof_sketch="A natural proof is suggested.",
                     assumptions=["oracle access", "algebraic extension"])
    item.status = CandidateStatus.unknown
    labels = classify_barriers(item)
    assert set(labels) == {"likely_relativizing", "possibly_natural",
                           "possible_algebrization_issue", "manual_review_required"}
    assert item.status == CandidateStatus.unknown


def test_negation_is_still_a_keyword_flag_and_never_certifies_barrier_avoidance():
    item = candidate("This is not a natural proof and does not relativize.")
    labels = classify_barriers(item)
    assert "possibly_natural" in labels
    assert "likely_relativizing" in labels
    assert "manual_review_required" in labels
    assert item.status != CandidateStatus.formally_verified
