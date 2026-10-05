"""Research-record serialization, evidence constraints, and revision invariants."""

import json

import pytest
from pydantic import ValidationError

from pnp_search.measures import AlgebraicDegree
from pnp_search.models import CandidateLemma, CandidateStatus, UniversalBinaryOperationBound, VerificationResult


def candidate(**overrides: object) -> CandidateLemma:
    """Build a minimal trusted candidate record for lifecycle tests."""
    values = {
        "candidate_id": "C-test-0", "experiment_id": "E-test", "model": "mock",
        "title": "Finite test", "natural_language_statement": "Candidate only",
        "source_output": '{"lemma":"후보"}',
    }
    values.update(overrides)
    return CandidateLemma(**values)


def evidence(status: CandidateStatus) -> VerificationResult:
    """Create internally consistent evidence for a requested serialized status."""
    values = {"status": status, "verification_method": "exhaustive", "verified_for_n": 2}
    if status == CandidateStatus.falsified:
        values.update(counterexample_found=True, counterexample={"n": 2, "f_bits": 0, "g_bits": 1})
    if status in (CandidateStatus.empirically_survived, CandidateStatus.formally_verified):
        values["complete"] = True
    if status == CandidateStatus.formally_verified:
        values["verification_method"] = "lean"
    return VerificationResult(**values)


@pytest.mark.parametrize("status", list(CandidateStatus))
def test_candidate_and_result_roundtrip(status: CandidateStatus) -> None:
    """Every declared evidence status has lossless JSON serialization."""
    result = evidence(status)
    record = candidate(status=status, verification_method=result.verification_method,
                       verification_history=[result], counterexample=result.counterexample)
    serialized = record.model_dump_json()
    assert CandidateLemma.model_validate_json(serialized) == record
    assert VerificationResult.model_validate_json(result.model_dump_json()) == result
    assert json.loads(serialized)["status"] == status.value
    assert record.timestamp.tzinfo is not None


def test_status_transition_and_sticky_falsification() -> None:
    """Later passing attempts never erase a concrete earlier counterexample."""
    record = candidate()
    record.mark_pending()
    assert record.status == CandidateStatus.pending_verification
    failed = evidence(CandidateStatus.falsified)
    record.apply_verification(failed)
    record.apply_verification(evidence(CandidateStatus.empirically_survived))
    record.apply_verification(evidence(CandidateStatus.formally_verified))
    assert record.status == CandidateStatus.falsified
    assert record.counterexample == failed.counterexample
    assert record.classification == "false_claim"
    assert record.verification_method == "exhaustive"
    assert len(record.verification_history) == 3
    with pytest.raises(ValueError):
        record.mark_pending()


def test_parse_failure_cannot_be_verified() -> None:
    """Unparsed provider output cannot acquire verification evidence."""
    record = candidate(status=CandidateStatus.parse_failed)
    with pytest.raises(ValueError):
        record.apply_verification(evidence(CandidateStatus.empirically_survived))
    assert not record.verification_history


def test_formal_record_recheck_is_atomic_and_preserves_history() -> None:
    """An unsupported follow-up must not fail halfway through a status transition."""
    record = candidate()
    record.apply_verification(evidence(CandidateStatus.formally_verified))
    record.apply_verification(evidence(CandidateStatus.unsupported))
    assert record.status == CandidateStatus.unsupported
    assert len(record.verification_history) == 2
    assert record.verification_history[0].status == CandidateStatus.formally_verified
    assert CandidateLemma.model_validate_json(record.model_dump_json()) == record


@pytest.mark.parametrize("fields", [
    {"status": "falsified"},
    {"status": "unknown", "counterexample_found": True, "counterexample": {"witness": 1}},
    {"status": "unknown", "counterexample": {"witness": 1}},
    {"status": "empirically_survived", "complete": False},
    {"status": "formally_verified", "complete": True},
    {"status": "formally_verified", "verification_method": "lean", "complete": False},
])
def test_inconsistent_evidence_rejected(fields: dict[str, object]) -> None:
    """Contradictory status, coverage, or formal-verifier evidence fails validation."""
    values = {"verification_method": "exhaustive", **fields}
    with pytest.raises(ValidationError):
        VerificationResult(**values)


def test_revision_relationship() -> None:
    """A revision names a distinct parent and has a positive revision index."""
    parent = candidate()
    child = candidate(candidate_id="C-test-1", parent_candidate_id=parent.candidate_id, revision_number=1)
    assert child.parent_candidate_id == parent.candidate_id
    assert child.revision_number == parent.revision_number + 1
    for fields in (
        {"revision_number": 1},
        {"parent_candidate_id": "C-other"},
        {"revision_number": 1, "parent_candidate_id": parent.candidate_id},
        {"revision_number": -1},
    ):
        with pytest.raises(ValidationError):
            candidate(**fields)


def test_bound_persists_measure_name() -> None:
    """Python measure objects serialize to declarative names, never executable code."""
    bound = UniversalBinaryOperationBound(operation="AND", measure=AlgebraicDegree(), rhs="M(f) + M(g)")
    assert bound.model_dump()["measure"] == "algebraic_degree"
    assert UniversalBinaryOperationBound.model_validate_json(bound.model_dump_json()) == bound


def test_result_status_cannot_be_mutated() -> None:
    """An existing unknown result cannot be promoted by direct field assignment."""
    result = evidence(CandidateStatus.unknown)
    with pytest.raises(ValidationError):
        result.status = CandidateStatus.formally_verified
    assert result.status == CandidateStatus.unknown


def test_apply_rejects_unvalidated_constructed_result() -> None:
    """The trusted apply boundary revalidates even Pydantic bypass constructions."""
    forged = VerificationResult.model_construct(
        status=CandidateStatus.formally_verified, verification_method="exhaustive", complete=True,
    )
    record = candidate()
    with pytest.raises(ValidationError):
        record.apply_verification(forged)
    assert record.status == CandidateStatus.generated
    assert not record.verification_history
    assert record.counterexample is None


def test_applied_counterexample_is_a_snapshot() -> None:
    """Changing a caller-owned nested payload cannot rewrite stored candidate evidence."""
    result = evidence(CandidateStatus.falsified)
    record = candidate()
    record.apply_verification(result)
    result.counterexample["f_bits"] = 99
    result.notes.append("Added after application")
    assert record.counterexample["f_bits"] == 0
    assert not record.verification_history[0].notes


@pytest.mark.parametrize("history", [
    [],
    [evidence(CandidateStatus.empirically_survived)],
    [evidence(CandidateStatus.formally_verified), evidence(CandidateStatus.unknown)],
    [evidence(CandidateStatus.falsified), evidence(CandidateStatus.formally_verified)],
])
def test_unbacked_formal_status_rejected(history: list[VerificationResult]) -> None:
    """Formal status imports require current Lean success and no prior falsification."""
    payload = candidate().model_dump(mode="json")
    payload.update(status="formally_verified", verification_method="lean",
                   verification_history=[result.model_dump(mode="json") for result in history])
    with pytest.raises(ValidationError):
        CandidateLemma.model_validate_json(json.dumps(payload))


def test_formal_status_with_lean_evidence_roundtrip() -> None:
    """A completed Lean result supports serialization while meaning review stays explicit."""
    record = candidate()
    record.mark_pending()
    record.apply_verification(evidence(CandidateStatus.formally_verified))
    restored = CandidateLemma.model_validate_json(record.model_dump_json())
    assert restored == record
    assert restored.status == CandidateStatus.formally_verified
    assert restored.verification_history[-1].verification_method == "lean"
    assert restored.verification_history[-1].complete
    assert restored.formalization_review_required
