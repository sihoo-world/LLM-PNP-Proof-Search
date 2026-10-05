"""Command-line entry points for reproducible, conservative research runs."""

import argparse
import json
import logging
from pathlib import Path

from pnp_search.generators import HTTPBackend, MockBackend
from pnp_search.models import CandidateLemma
from pnp_search.pipelines import load_config, run_experiment
from pnp_search.pipelines.analysis import export_summary
from pnp_search.prompts import candidate_prompt
from pnp_search.storage import append_jsonl, read_jsonl
from pnp_search.verifiers import ExhaustiveVerifier, SMTVerifier


def main(argv: list[str] | None = None) -> None:
    """Dispatch experiments, generation, saved-candidate rechecks, and summaries."""
    parser = argparse.ArgumentParser(description="Candidate Boolean lemma research; finite evidence is not a general proof.")
    parser.add_argument("--verbose", action="store_true")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Run mock/HTTP generation, verification, and revision")
    run.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    run.add_argument("--experiment-name", default="baseline-001")
    run.add_argument("--seed", type=int)
    run.add_argument("--backend", choices=("mock", "http"))
    run.add_argument("--output-dir", type=Path)
    run.add_argument("--lean", action="store_true", help="Also check the trusted Boolean identity template")
    generate = commands.add_parser("generate", help="Generate one raw response with its exact prompt")
    generate.add_argument("--group", choices=("A", "B"), default="A")
    generate.add_argument("--measure", default="truth_table_weight")
    generate.add_argument("--backend", choices=("mock", "http"), default="mock")
    generate.add_argument("--seed", type=int, default=42)
    verify = commands.add_parser("verify", help="Recheck saved candidate JSONL; never overwrite original records")
    verify.add_argument("input", type=Path)
    verify.add_argument("--output", type=Path, required=True)
    verify.add_argument("--n", type=int, default=3)
    verify.add_argument("--max-cases", type=int, default=1_000_000)
    verify.add_argument("--method", choices=("exhaustive", "smt"), default="exhaustive")
    summary = commands.add_parser("summarize", help="Export final-candidate JSONL metrics")
    summary.add_argument("input", type=Path)
    summary.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    if args.command == "run":
        config = load_config(args.config)
        values = config.model_dump()
        for key in ("seed", "backend", "output_dir"):
            if getattr(args, key) is not None:
                values[key] = getattr(args, key)
        if args.lean:
            values["lean"] = True
        config = type(config).model_validate(values)
        directory = run_experiment(config, args.experiment_name)
        print(str(directory.resolve()))
    elif args.command == "generate":
        backend = MockBackend() if args.backend == "mock" else HTTPBackend()
        prompt = candidate_prompt(args.group, args.measure)
        print(json.dumps({"prompt": prompt, "prompt_version": "candidate-v1", "model": backend.name,
                          "seed": args.seed, "output": backend.generate(prompt, measure=args.measure, seed=args.seed)}, ensure_ascii=False))
    elif args.command == "verify":
        if args.output.exists() or args.output.resolve() == args.input.resolve():
            parser.error("Verification output must be a new file")
        verifier = ExhaustiveVerifier(n=args.n, max_cases=args.max_cases) if args.method == "exhaustive" else SMTVerifier(n=args.n)
        for record in read_jsonl(args.input):
            candidate = CandidateLemma.model_validate(record)
            result = verifier.verify(candidate)
            append_jsonl(args.output, {"candidate_id": candidate.candidate_id, "result": result.model_dump(mode="json")})
        print(str(args.output.resolve()))
    elif args.command == "summarize":
        candidates = [CandidateLemma.model_validate(record) for record in read_jsonl(args.input)]
        export_summary(candidates, args.output_dir)
        print(str(args.output_dir.resolve()))

