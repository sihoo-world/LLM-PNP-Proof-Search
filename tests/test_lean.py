"""Trusted formal-template boundaries and real optional Lean smoke checking."""

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from pnp_search.models import CandidateLemma, CandidateStatus, UniversalBinaryOperationBound
from pnp_search.verifiers.lean import (
    AXIOM_MARKER, CANONICAL_NATURAL_STATEMENT, CANONICAL_STATEMENT,
    TRUSTED_SOURCE, LeanVerifier,
)


def candidate(**changes):
    """Create an aligned template candidate without unverified implications."""
    values = dict(
        experiment_id="test-lean", model="mock", title="AND commutativity",
        natural_language_statement=CANONICAL_NATURAL_STATEMENT,
        formalized_statement=CANONICAL_STATEMENT, lean_template="bool_and_commutative",
        source_output="mock trusted template request",
    )
    values.update(changes)
    return CandidateLemma(**values)


@pytest.mark.parametrize("changes", [
    {"formalized_statement": "True"}, {"lean_template": None},
    {"natural_language_statement": "Every Boolean function has exponential circuit complexity."},
    {"claimed_implication": "P differs from NP."},
    {"assumptions": ["An unrelated axiom"]},
    {"bound": UniversalBinaryOperationBound(operation="AND", measure="sensitivity", rhs="M(f)")},
])
def test_unrelated_or_mismatched_claim_never_compiles(monkeypatch, tmp_path, changes):
    """A valid template cannot be attached to an unrelated claim for certification."""
    def forbidden(*args, **kwargs):
        raise AssertionError("Unsupported candidates must not launch Lean")
    monkeypatch.setattr(subprocess, "run", forbidden)
    claim = candidate(**changes)
    result = LeanVerifier(output_dir=tmp_path).verify(claim)
    assert result.status == claim.status == CandidateStatus.unsupported
    assert result.formalization_review_required


def test_missing_lake_is_unknown(monkeypatch, tmp_path):
    monkeypatch.setattr(LeanVerifier, "discover_lake", lambda self: None)
    result = LeanVerifier(output_dir=tmp_path).verify(candidate())
    assert result.status == CandidateStatus.unknown
    assert not result.complete


def test_parse_failed_candidate_is_not_promoted_or_compiled(monkeypatch, tmp_path):
    """Even an aligned payload cannot turn a failed parse into formal evidence."""
    def forbidden(*args, **kwargs):
        raise AssertionError("A parse failure must never launch Lean")
    monkeypatch.setattr(subprocess, "run", forbidden)
    claim = candidate(status=CandidateStatus.parse_failed)
    result = LeanVerifier(output_dir=tmp_path).verify(claim)
    assert result.status == CandidateStatus.unsupported
    assert claim.status == CandidateStatus.parse_failed
    assert not claim.verification_history


@pytest.mark.parametrize("stdout,returncode", [("", 0), (AXIOM_MARKER, 1), (AXIOM_MARKER + " sorryAx", 0)])
def test_process_success_alone_does_not_establish_theorem(monkeypatch, tmp_path, stdout, returncode):
    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, returncode, stdout, "")
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = LeanVerifier(lake_path="fake-lake", output_dir=tmp_path).verify(candidate())
    assert result.status == CandidateStatus.unknown
    assert not result.complete


def test_timeout_is_retained_as_unknown(monkeypatch, tmp_path):
    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 0.01, output=b"partial output")
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = LeanVerifier(lake_path="fake-lake", output_dir=tmp_path, timeout_seconds=0.01).verify(candidate())
    assert result.status == CandidateStatus.unknown
    evidence = json.loads(next(tmp_path.glob("lean-check-*/evidence.json")).read_text(encoding="utf-8"))
    assert evidence["stdout"] == "partial output"


def test_source_is_fixed_and_runs_do_not_overwrite(monkeypatch, tmp_path):
    def fake_run(command, **kwargs):
        assert isinstance(command, list) and not kwargs.get("shell", False)
        return subprocess.CompletedProcess(command, 0, AXIOM_MARKER, "")
    monkeypatch.setattr(subprocess, "run", fake_run)
    verifier = LeanVerifier(lake_path="fake-lake", output_dir=tmp_path)
    for _ in range(2):
        claim = candidate(proof_sketch="#eval malicious instructions are never source")
        result = verifier.verify(claim)
        assert result.status == claim.status == CandidateStatus.formally_verified
        assert claim.verification_history == [result]
        assert result.formalization_review_required
    sources = list(tmp_path.glob("lean-check-*/Candidate.lean"))
    assert len(sources) == 2
    assert all(path.read_text(encoding="utf-8") == TRUSTED_SOURCE for path in sources)


def test_real_lean_kernel_check_when_toolchain_available(tmp_path):
    verifier = LeanVerifier(output_dir=tmp_path)
    if verifier.lake_path is None:
        pytest.skip("Lean is optional; no installed Lake executable")
    result = verifier.verify(candidate())
    assert result.status == CandidateStatus.formally_verified, result.model_dump_json()
    evidence = json.loads(result.notes[0])
    assert evidence["returncode"] == 0
    assert AXIOM_MARKER in evidence["stdout"]
    assert evidence["source_sha256"] == hashlib.sha256(TRUSTED_SOURCE.encode("utf-8")).hexdigest()
    assert Path(evidence["source_path"]).is_file()
