"""End-to-end audit trails, reproducibility, and explicit metric denominators."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pnp_search.models import CandidateLemma, CandidateStatus, UniversalBinaryOperationBound, VerificationResult
from pnp_search.pipelines import ExperimentConfig, load_config, run_experiment
from pnp_search.pipelines.analysis import export_summary, summarize
from pnp_search.storage import read_jsonl


def records(directory: Path, filename: str) -> list[dict]:
    """Load one required persisted stage, failing if that stage is missing."""
    return list(read_jsonl(directory / filename))


@pytest.mark.parametrize("n", [2, 3])
def test_actual_mock_pipeline_persists_falsification_revision_and_groups(tmp_path, n):
    run = run_experiment(ExperimentConfig(n=n, output_dir=tmp_path), "audit-trail")
    candidates = records(run, "candidates.jsonl")
    parsed = records(run, "parsed_candidates.jsonl")
    results = records(run, "results.jsonl")
    counterexamples = records(run, "counterexamples.jsonl")
    raw = records(run, "raw_outputs.jsonl")
    prompts = records(run, "prompts.jsonl")
    manifest = json.loads((run / "manifest.json").read_text())
    summary = json.loads((run / "summary.json").read_text())

    assert manifest["status"] == "completed"
    assert manifest["config"]["n"] == n
    assert manifest["generation_parameters"]["seed"] == 42
    assert manifest["provenance"]["source_sha256"]
    assert len(candidates) == len(parsed) == len(results) == len(raw) == len(prompts) == 8
    assert len(counterexamples) == 2
    assert len({c["candidate_id"] for c in candidates}) == 8
    assert all(c["status"] == "generated" for c in parsed)
    assert all(len(c["verification_history"]) == 1 for c in candidates)
    by_id = {c["candidate_id"]: c for c in candidates}
    for c in candidates:
        assert c["experiment_id"] == manifest["experiment_id"]
        if c["parent_candidate_id"]:
            parent = by_id[c["parent_candidate_id"]]
            assert parent["status"] == "falsified"
            assert parent["counterexample"] is not None
            assert c["status"] == "empirically_survived"
            assert c["revision_number"] == 1
            assert c["revision_analysis"]["failure_explanation"]
            prompt = next(p["prompt"] for p in prompts if p["candidate_id"] == c["candidate_id"])
            assert parent["candidate_id"] in prompt
            assert '"counterexample"' in prompt
    assert summary["all"]["total_candidates"] == 8
    assert summary["all"]["status_counts"] == {"empirically_survived": 6, "falsified": 2}
    assert summary["all"]["revision_count"] == 2
    assert summary["all"]["root_count"] == 6
    assert summary["all"]["revision_survival_rate"] == 1
    assert summary["all"]["average_revisions"] == pytest.approx(1 / 3)
    assert summary["all"]["parse_success_rate"] == 1
    assert summary["all"]["falsification_rate"] == 0.25
    assert summary["all"]["empirical_survival_rate"] == 0.75
    assert summary["all"]["formal_verification_rate"] == 0
    assert summary["all"]["duplicate_or_known_count"] == 4
    assert summary["A"]["total_candidates"] == summary["B"]["total_candidates"] == 4
    for prompt in prompts:
        assert ("Barrier context" in prompt["prompt"]) == (prompt["group"] == "B")
    with (run / "summary.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert {r["group"] for r in rows} == {"all", "A", "B"}


def test_same_seed_reproduces_claims_statuses_witnesses_and_revision_structure(tmp_path):
    config = ExperimentConfig(n=2, seed=137, output_dir=tmp_path)
    first = run_experiment(config, "repeat")
    second = run_experiment(config, "repeat")
    assert first != second

    def deterministic_projection(directory):
        return [{key: c[key] for key in ("bound", "status", "counterexample", "group", "revision_number", "revision_analysis")}
                for c in records(directory, "candidates.jsonl")]

    assert deterministic_projection(first) == deterministic_projection(second)
    assert json.loads((first / "summary.json").read_text()) == json.loads((second / "summary.json").read_text())
    assert (first / "manifest.json").exists()


def test_backend_failures_are_persisted_without_exception_secret(tmp_path):
    class FailingBackend:
        name = "failure-fixture"

        def generate(self, prompt, **kwargs):
            raise RuntimeError("credential=DO_NOT_PERSIST_THIS_SECRET")

    run = run_experiment(ExperimentConfig(n=2, groups=["A"], output_dir=tmp_path), backend=FailingBackend())
    manifest = json.loads((run / "manifest.json").read_text())
    assert manifest["status"] == "completed_with_failures"
    failures = records(run, "failures.jsonl")
    assert len(failures) == 3
    assert all(f["stage"] == "generation" and f["error_type"] == "RuntimeError" for f in failures)
    candidates = records(run, "candidates.jsonl")
    assert len(candidates) == 3 and all(c["status"] == "parse_failed" for c in candidates)
    assert all(r["output"] == "" for r in records(run, "raw_outputs.jsonl"))
    assert len(records(run, "prompts.jsonl")) == 3
    assert not (run / "results.jsonl").exists()
    assert json.loads((run / "summary.json").read_text())["all"]["parse_success_rate"] == 0
    assert "DO_NOT_PERSIST_THIS_SECRET" not in "".join(p.read_text() for p in run.iterdir() if p.is_file())


def test_budget_limited_pipeline_never_labels_partial_coverage_as_survival(tmp_path):
    run = run_experiment(ExperimentConfig(n=3, groups=["A"], max_cases=1, output_dir=tmp_path))
    candidates = records(run, "candidates.jsonl")
    assert len(candidates) == 3
    assert all(c["status"] == "unknown" for c in candidates)
    assert all(not r["result"]["complete"] for r in records(run, "results.jsonl"))


def metric_candidate(candidate_id: str, **kwargs) -> CandidateLemma:
    """Synthetic persisted-record fixture for testing statistical denominators."""
    values = dict(candidate_id=candidate_id, experiment_id="metrics", model="fixture", title="Fixture",
                  natural_language_statement="Synthetic metric input, not a validated theorem.", source_output="{}")
    values.update(kwargs)
    return CandidateLemma(**values)


def claim(measure="truth_table_weight", rhs="M(f) + M(g)") -> UniversalBinaryOperationBound:
    return UniversalBinaryOperationBound(operation="AND", measure=measure, rhs=rhs)


def test_metric_denominators_duplicate_known_union_and_csv_export(tmp_path):
    false = metric_candidate("false", status="falsified", bound=claim(rhs="M(f)"))
    revision = metric_candidate("revision", status="empirically_survived", parent_candidate_id="false", revision_number=1, bound=claim())
    parsed_failed = metric_candidate("bad-json", status="parse_failed")
    unknown = metric_candidate("unknown", status="unknown", bound=claim("algebraic_degree"), barrier_labels=["possibly_natural", "manual_review_required"])
    formal = metric_candidate("formal", status="formally_verified", formalized_statement="Bool.and_comm", lean_template="bool_and_commutative", classification="known_theorem", classification_evidence="Explicit known-result fixture citation",
                              verification_history=[VerificationResult(status="formally_verified", verification_method="lean", complete=True)])
    duplicate_and_known = metric_candidate("duplicate", bound=claim(), classification="rediscovery", classification_evidence="Known fixture result")
    known = metric_candidate("known", bound=claim("sensitivity"), classification="known_theorem", classification_evidence="Independent known fixture result")
    result = export_summary([false, revision, parsed_failed, unknown, formal, duplicate_and_known, known], tmp_path)["all"]
    assert result["total_candidates"] == 7
    assert result["parse_success_rate"] == pytest.approx(6 / 7)
    for field in ("falsification_rate", "empirical_survival_rate", "formal_verification_rate", "barrier_flag_rate"):
        assert result[field] == pytest.approx(1 / 7)
    assert result["revision_survival_rate"] == 1
    assert result["average_revisions"] == pytest.approx(1 / 6)
    assert result["duplicate_or_known_count"] == 3  # The duplicate-known record is counted once.
    assert result["duplicate_or_known_result_rate"] == pytest.approx(3 / 7)
    assert result["formal_template_count"] == 1
    assert json.loads((tmp_path / "summary.json").read_text())["all"] == result


@pytest.mark.parametrize("difference", [
    {"assumptions": ["f is monotone"]},
    {"definitions": ["M denotes a different proposed semantic definition"]},
    {"domain": "restricted_monotone_circuit_complexity"},
])
def test_duplicate_fingerprint_distinguishes_semantic_context(difference):
    base = metric_candidate("base", bound=claim())
    different = metric_candidate("different", bound=claim(), **difference)
    assert summarize([base, different])["duplicate_or_known_count"] == 0


def test_duplicate_formal_statement_with_different_assumptions_is_not_same_claim():
    base = metric_candidate("base", formalized_statement="unreviewed formal statement")
    restricted = metric_candidate("restricted", formalized_statement="unreviewed formal statement", assumptions=["extra hypothesis"])
    assert summarize([base, restricted])["duplicate_or_known_count"] == 0


def test_unknown_statements_and_unsubstantiated_novelty_classifications_are_not_known():
    items = [metric_candidate("first"), metric_candidate("second"), metric_candidate("third", classification="known_theorem")]
    assert summarize(items)["duplicate_or_known_count"] == 0
    assert summarize([])["total_candidates"] == 0
    assert summarize([])["average_revisions"] == 0


@pytest.mark.parametrize("values", [
    {"n": -1}, {"n": 5}, {"seed": -1}, {"seed": 2**32},
    {"max_cases": 0}, {"max_cases": 100_000_001}, {"max_revisions": -1}, {"max_revisions": 11},
    {"groups": []}, {"groups": ["C"]}, {"backend": "unconfigured"}, {"api_key": "never-allowed"},
])
def test_configuration_rejects_invalid_bounds_or_unrecognized_keys(values):
    with pytest.raises(ValidationError):
        ExperimentConfig.model_validate(values)


def test_yaml_configuration_is_loaded_and_unknown_fields_rejected(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("n: 2\nseed: 19\ngroups: [B]\n", encoding="utf-8")
    assert load_config(path).n == 2
    assert load_config(path).groups == ["B"]
    path.write_text("n: 2\nmisspelled_option: 1\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(path)
