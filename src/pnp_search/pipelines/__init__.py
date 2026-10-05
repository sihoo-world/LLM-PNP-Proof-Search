"""Auditable generation, parsing, finite verification, and counterexample revision."""

import hashlib
import importlib.metadata
import json
import logging
import platform
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

import yaml
from pydantic import BaseModel, ConfigDict, Field

from pnp_search.classifiers import classify_barriers
from pnp_search.generators import HTTPBackend, LLMBackend, MockBackend
from pnp_search.models import CandidateLemma, CandidateStatus
from pnp_search.parsers import parse_candidate
from pnp_search.pipelines.analysis import export_summary
from pnp_search.prompts import candidate_prompt, revision_prompt
from pnp_search.storage import append_jsonl
from pnp_search.verifiers import ExhaustiveVerifier

LOGGER = logging.getLogger(__name__)


class ExperimentConfig(BaseModel):
    """Bounded runtime configuration; credentials never belong in this schema."""

    model_config = ConfigDict(extra="forbid")
    seed: int = Field(default=42, ge=0, lt=2**32)
    n: int = Field(default=3, ge=0, le=4)
    max_cases: int = Field(default=1_000_000, ge=1, le=100_000_000)
    max_revisions: int = Field(default=1, ge=0, le=10)
    groups: list[Literal["A", "B"]] = Field(default_factory=lambda: ["A", "B"], min_length=1, max_length=2)
    backend: Literal["mock", "http"] = "mock"
    output_dir: Path = Path("experiments/runs")
    lean: bool = False


def load_config(path: Path) -> ExperimentConfig:
    """Parse YAML safely and reject ignored or misspelled configuration fields."""
    return ExperimentConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def code_provenance() -> dict[str, object]:
    """Capture source hashes even before the repository has its first commit."""
    root = Path(__file__).resolve().parents[3]
    hashes = {str(path.relative_to(root)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
              for folder in ("src", "configs", "lean", "tests", "docs")
              for path in sorted((root / folder).rglob("*"))
              if path.is_file() and not any(part in {"__pycache__", ".lake"} for part in path.parts)
              and path.suffix in {".py", ".txt", ".yaml", ".toml", ".lean", ".md"}}
    for filename in ("pyproject.toml", "requirements-lock.txt"):
        path = root / filename
        if path.exists():
            hashes[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
    def git(*args: str) -> str | None:
        try:
            result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=5)
            return result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None
    return {"git_commit": git("rev-parse", "HEAD"), "git_status": git("status", "--porcelain"),
            "source_sha256": hashes, "python": platform.python_version(), "platform": platform.platform(),
            "dependencies": {name: importlib.metadata.version(name) for name in ("pydantic", "PyYAML", "sympy", "z3-solver")}}


def run_experiment(config: ExperimentConfig, experiment_name: str = "baseline", backend: LLMBackend | None = None) -> Path:
    """Persist every stage before advancing; raw outputs allow exact offline replay."""
    safe_name = re.sub(r"[^A-Za-z0-9_-]", "-", experiment_name)[:60] or "experiment"
    experiment_id = safe_name + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    directory = config.output_dir / experiment_id
    directory.mkdir(parents=True, exist_ok=False)
    manifest = {"experiment_id": experiment_id, "experiment_name": experiment_name,
                "started_at": datetime.now(timezone.utc).isoformat(), "status": "running",
                "config": config.model_dump(mode="json"), "generation_parameters": {"temperature": 0, "seed": config.seed},
                "seed_scope": "Mock is deterministic; HTTP transport does not assume provider seed support.",
                "provenance": code_provenance()}
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    candidates: list[CandidateLemma] = []
    try:
        backend = backend or (MockBackend() if config.backend == "mock" else HTTPBackend())
        manifest["model"] = backend.name
        verifier = ExhaustiveVerifier(n=config.n, max_cases=config.max_cases)
        for group in dict.fromkeys(config.groups):
            for index, measure in enumerate(("truth_table_weight", "sensitivity", "algebraic_degree")):
                parent: CandidateLemma | None = None
                for revision in range(config.max_revisions + 1):
                    candidate_id = f"{experiment_id}-{group}-{index}-r{revision}"
                    prompt = revision_prompt(parent) if parent else candidate_prompt(group, measure)
                    append_jsonl(directory / "prompts.jsonl", {"candidate_id": candidate_id, "experiment_id": experiment_id,
                                 "group": group, "prompt_version": "revision-v1" if parent else "candidate-v1", "prompt": prompt})
                    try:
                        raw = backend.generate(prompt, seed=config.seed, measure=measure, revision=parent is not None)
                    except Exception as exc:
                        # Record the exception type, never provider error bodies containing credentials.
                        append_jsonl(directory / "failures.jsonl", {"candidate_id": candidate_id, "stage": "generation", "error_type": type(exc).__name__})
                        raw = ""
                    append_jsonl(directory / "raw_outputs.jsonl", {"candidate_id": candidate_id, "experiment_id": experiment_id, "model": backend.name, "output": raw})
                    candidate = parse_candidate(raw, experiment_id=experiment_id, model=backend.name,
                                                candidate_id=candidate_id, group=group, parent=parent)
                    candidate.barrier_labels = classify_barriers(candidate)
                    append_jsonl(directory / "parsed_candidates.jsonl", candidate)
                    if candidate.status != CandidateStatus.parse_failed:
                        candidate.mark_pending()
                        result = verifier.verify(candidate)
                        append_jsonl(directory / "results.jsonl", {"candidate_id": candidate_id, "result": result.model_dump(mode="json")})
                        if result.counterexample_found:
                            append_jsonl(directory / "counterexamples.jsonl", {"candidate_id": candidate_id, "counterexample": result.counterexample})
                    append_jsonl(directory / "candidates.jsonl", candidate)
                    candidates.append(candidate)
                    if candidate.status != CandidateStatus.falsified:
                        break
                    parent = candidate
        if config.lean:
            from pnp_search.verifiers.lean import LeanVerifier, CANONICAL_NATURAL_STATEMENT, CANONICAL_FORMAL_STATEMENT
            formal = CandidateLemma(experiment_id=experiment_id, model="trusted-template-v1", group="formal-smoke",
                                    title="Boolean AND commutativity", natural_language_statement=CANONICAL_NATURAL_STATEMENT,
                                    formalized_statement=CANONICAL_FORMAL_STATEMENT,
                                    lean_template="bool_and_commutative", source_output="Trusted infrastructure smoke template; not an LLM discovery.",
                                    classification="known_theorem", classification_evidence="Elementary Boolean truth table; Lean core cases/rfl.")
            formal_result = LeanVerifier(output_dir=directory / "lean").verify(formal)
            append_jsonl(directory / "results.jsonl", {"candidate_id": formal.candidate_id, "result": formal_result.model_dump(mode="json")})
            append_jsonl(directory / "candidates.jsonl", formal)
            candidates.append(formal)
        export_summary(candidates, directory)
        manifest["status"] = "completed_with_failures" if (directory / "failures.jsonl").exists() else "completed"
    except Exception as exc:
        manifest["status"] = "failed"
        append_jsonl(directory / "failures.jsonl", {"stage": "pipeline", "error_type": type(exc).__name__})
        raise
    finally:
        manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    LOGGER.info("Experiment completed: %s", directory)
    return directory
