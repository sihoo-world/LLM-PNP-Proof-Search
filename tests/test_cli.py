"""Command-line workflows must preserve input evidence and export usable results."""

import json
from pathlib import Path

import pytest

from pnp_search.cli import main
from pnp_search.models import CandidateLemma, UniversalBinaryOperationBound
from pnp_search.storage import append_jsonl, read_jsonl


def write_candidate(path: Path) -> bytes:
    """Persist a false fixture while retaining bytes for overwrite detection."""
    candidate = CandidateLemma(candidate_id="cli-fixture", experiment_id="cli", model="fixture", title="False bound",
        natural_language_statement="Weight of XOR is bounded by weight of f alone.", source_output="{}",
        bound=UniversalBinaryOperationBound(operation="XOR", measure="truth_table_weight", rhs="M(f)"))
    append_jsonl(path, candidate)
    return path.read_bytes()


def test_cli_run_seed_override_and_summarize(tmp_path, capsys):
    config = tmp_path / "config.yaml"
    config.write_text("n: 2\nseed: 42\ngroups: [A]\nmax_revisions: 1\n", encoding="utf-8")
    main(["run", "--config", str(config), "--seed", "27", "--experiment-name", "cli-trial", "--output-dir", str(tmp_path / "runs")])
    directory = Path(capsys.readouterr().out.strip())
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["config"]["seed"] == 27
    assert manifest["status"] == "completed"
    assert manifest["experiment_name"] == "cli-trial"
    summary_dir = tmp_path / "resummary"
    main(["summarize", str(directory / "candidates.jsonl"), "--output-dir", str(summary_dir)])
    assert json.loads((summary_dir / "summary.json").read_text()) == json.loads((directory / "summary.json").read_text())
    assert (summary_dir / "summary.csv").exists()


@pytest.mark.parametrize("method", ["exhaustive", "smt"])
def test_cli_verify_writes_new_result_without_mutating_original(tmp_path, capsys, method):
    source = tmp_path / "input.jsonl"
    original = write_candidate(source)
    output = tmp_path / f"{method}.jsonl"
    main(["verify", str(source), "--output", str(output), "--n", "2", "--method", method])
    assert source.read_bytes() == original
    rows = list(read_jsonl(output))
    assert len(rows) == 1
    assert rows[0]["candidate_id"] == "cli-fixture"
    assert rows[0]["result"]["status"] == "falsified"
    assert rows[0]["result"]["counterexample_found"]
    assert rows[0]["result"]["verification_method"] == method
    assert Path(capsys.readouterr().out.strip()) == output.resolve()


def test_cli_verify_refuses_input_path_and_any_existing_output(tmp_path):
    source = tmp_path / "input.jsonl"
    original = write_candidate(source)
    with pytest.raises(SystemExit) as failure:
        main(["verify", str(source), "--output", str(source)])
    assert failure.value.code == 2
    assert source.read_bytes() == original
    output = tmp_path / "existing.jsonl"
    output.write_text("retain this earlier evidence", encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["verify", str(source), "--output", str(output)])
    assert output.read_text() == "retain this earlier evidence"
    assert source.read_bytes() == original


def test_cli_generate_emits_replayable_prompt_and_untrusted_raw_json(capsys):
    main(["generate", "--group", "B", "--measure", "truth_table_weight", "--seed", "9"])
    output = json.loads(capsys.readouterr().out)
    assert output["seed"] == 9
    assert output["prompt_version"] == "candidate-v1"
    assert "Barrier context" in output["prompt"]
    raw = json.loads(output["output"])
    assert raw["bound"]["measure"] == "truth_table_weight"
    assert "status" not in raw


def test_cli_budget_exhaustion_is_explicit_unknown(tmp_path):
    source = tmp_path / "input.jsonl"
    write_candidate(source)
    output = tmp_path / "limited.jsonl"
    main(["verify", str(source), "--output", str(output), "--n", "3", "--max-cases", "1"])
    result = next(read_jsonl(output))["result"]
    assert result["status"] == "unknown"
    assert result["cases_checked"] == 1
    assert not result["complete"]
