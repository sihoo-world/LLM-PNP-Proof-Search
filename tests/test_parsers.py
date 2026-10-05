"""Provider output is untrusted, and failed parses remain reproducible data."""

import json
from pathlib import Path

import pytest

from pnp_search.generators import MockBackend
from pnp_search.models import CandidateStatus
from pnp_search.parsers import parse_candidate
from pnp_search.storage import append_jsonl, read_jsonl


def parse(raw: str, **overrides: object):
    """Parse with deterministic, caller-owned provenance."""
    values = {"experiment_id": "E-parser", "model": "mock", "candidate_id": "C-parser-0"}
    values.update(overrides)
    return parse_candidate(raw, **values)


def test_mock_output_is_only_generated() -> None:
    """Valid mock output receives no implicit mathematical endorsement."""
    raw = MockBackend().generate("candidate")
    record = parse(raw)
    assert record.status == CandidateStatus.generated
    assert record.source_output == raw
    assert record.bound.measure == "truth_table_weight"
    assert record.classification == "unknown"
    assert record.formalization_review_required


@pytest.mark.parametrize("injected", [
    {"status": "formally_verified"}, {"status": "known_result"},
    {"classification": "known_theorem"}, {"verification_method": "lean"},
    {"candidate_id": "C-forged"}, {"experiment_id": "E-forged"},
    {"parent_candidate_id": "C-forged"}, {"revision_number": 99},
    {"formalization_review_required": False}, {"verification_history": []},
    {"lean_template": "bool_and_commutative"},
])
def test_provider_cannot_inject_trusted_fields(injected: dict[str, object]) -> None:
    """Status/provenance fields outside the provider contract cause parse failure."""
    payload = json.loads(MockBackend().generate("candidate"))
    payload.update(injected)
    record = parse(json.dumps(payload))
    assert record.status == CandidateStatus.parse_failed
    assert record.candidate_id == "C-parser-0"
    assert record.experiment_id == "E-parser"
    assert record.classification == "unknown"
    assert record.formalization_review_required


@pytest.mark.parametrize("raw", ["", "not JSON", "{", "[]", "null", '{"lemma":"missing fields"}', "x" * 1_000_001], ids=["empty", "text", "truncated", "array", "null", "missing-fields", "oversized"])
def test_malformed_response_persistence(raw: str, tmp_path: Path) -> None:
    """Even malformed/oversized raw output survives a JSONL storage round-trip."""
    record = parse(raw)
    assert record.status == CandidateStatus.parse_failed
    path = tmp_path / "failed.jsonl"
    append_jsonl(path, record)
    saved = list(read_jsonl(path))
    assert len(saved) == 1
    assert saved[0]["source_output"] == raw
    assert saved[0]["status"] == "parse_failed"
    assert saved[0]["notes"]


@pytest.mark.parametrize("measure", [None, 7, {}, [], True])
def test_malformed_measure_is_parse_failure(measure: object) -> None:
    """Malformed JSON types must be recorded, rather than raising AttributeError."""
    payload = json.loads(MockBackend().generate("candidate"))
    payload["bound"]["measure"] = measure
    raw = json.dumps(payload)
    record = parse(raw)
    assert record.status == CandidateStatus.parse_failed
    assert record.source_output == raw


def test_revision_requires_critique_and_links_parent() -> None:
    """Revisions require every critique field and receive caller-controlled lineage."""
    backend = MockBackend()
    parent = parse(backend.generate("candidate"))
    child = parse(backend.generate("revision", revision=True), candidate_id="C-parser-1", parent=parent)
    assert child.status == CandidateStatus.generated
    assert child.parent_candidate_id == parent.candidate_id
    assert child.revision_number == 1
    assert child.prompt_version == "revision-v1"
    assert child.revision_analysis["lower_bound_relevance"]
    missing = parse(backend.generate("candidate"), candidate_id="C-parser-2", parent=child)
    assert missing.status == CandidateStatus.parse_failed
    assert missing.parent_candidate_id == child.candidate_id
    assert missing.revision_number == 2
    payload = json.loads(backend.generate("revision", revision=True))
    payload["revision_analysis"]["failure_explanation"] = "   "
    assert parse(json.dumps(payload), candidate_id="C-parser-3", parent=parent).status == CandidateStatus.parse_failed
