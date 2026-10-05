# LLM-PNP-Proof-Search

**LLM-Assisted Search for P vs NP Proof Strategies: Generation and Verification of Candidate Boolean Circuit Lower Bounds**

## What this project is

LLM-assisted automated exploration of proof strategies related to Boolean circuit lower bounds and P vs NP. This MVP generates structured **candidate** lemmas, interprets a restricted operation-bound DSL, searches for finite counterexamples, preserves failed attempts, and feeds witnesses back into a versioned revision loop. A narrowly scoped Lean template tests the formal-verification connection.

Research question: can iterative generation, counterexample search, and formal verification improve candidates into mathematically valid auxiliary lemmas or useful proof strategies?

## What this project is NOT

- It does not claim a proof of P≠NP.
- Model text is not treated as mathematical fact.
- Finite exhaustive survival is not a general theorem.
- Heuristic barrier labels are not mathematical proofs of applicability or avoidance.
- Mock fixtures, elementary rediscoveries, and successful Lean smoke checks are not novel circuit lower bounds.

## Run the MVP

Python **3.12+** is required. From this repository:

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
python -m pytest -q
python -m pnp_search run --config configs/default.yaml --experiment-name baseline-001 --seed 42
```

Alternatively `python -m pip install -e ".[dev]"` resolves dependency ranges from `pyproject.toml`. The lock file is the validated dependency snapshot. No API key or network request is needed for the default mock experiment.

The run prints a unique directory under `experiments/runs/`. Default A/B groups each generate three root candidates (weight, sensitivity, algebraic degree); the false weight candidate receives one revision. JSONL stores exact prompts, raw responses, parsed records, final candidate versions, witnesses, and verifier results. `manifest.json` captures configuration, seed, source hashes, dependency versions, Git state, and completion/failure state. `summary.json` and `summary.csv` compare groups using documented denominators. A/B mock outputs intentionally coincide: this tests the infrastructure, not barrier prompting efficacy.

```bash
python scripts/run_experiment.py --config configs/default.yaml
python -m pnp_search generate --group B --measure sensitivity
python -m pnp_search verify experiments/runs/RUN/candidates.jsonl --output recheck.jsonl --n 3
python -m pnp_search verify experiments/runs/RUN/candidates.jsonl --output smt-recheck.jsonl --n 3 --method smt
python -m pnp_search summarize experiments/runs/RUN/candidates.jsonl --output-dir summaries
```

`verify` requires a new output path and preserves the original experiment. Rechecking saved candidates is an offline replay of the executable interpretation. Exact prompts and raw responses also support parser audits. Real API generation may remain nondeterministic; the seed is not a promise of provider determinism. No stochastic search is used in the initial verifier.

## Direct verifier API

```python
from pnp_search.measures import AlgebraicDegree, Sensitivity, TruthTableWeight
from pnp_search.models import UniversalBinaryOperationBound
from pnp_search.verifiers import ExhaustiveVerifier

candidate = UniversalBinaryOperationBound(
    operation="AND", measure=AlgebraicDegree(),
    relation="<=", rhs="M(f) + M(g)",
)
result = ExhaustiveVerifier(n=3).verify(candidate)
print(result.model_dump_json(indent=2))
# status: empirically_survived; verified_for_n: 3
# counterexample_found: false; cases_checked: 65536; complete: true

false_candidate = UniversalBinaryOperationBound(
    operation="XOR", measure=TruthTableWeight(), relation="<=", rhs="M(f)",
)
false_result = ExhaustiveVerifier(n=3).verify(false_candidate)
# falsified: f=0, g has one satisfying assignment; 1 <= 0 is false.

for measure in (AlgebraicDegree(), Sensitivity(), TruthTableWeight()):
    print(ExhaustiveVerifier(n=3).verify(UniversalBinaryOperationBound(
        operation="AND", measure=measure, rhs="M(f) + M(g)",
    )).status)
```

The algebraic-degree example is deliberately a passing baseline: multiplying GF(2) polynomials and reducing multilinearly cannot increase degree beyond the sum. It must **not** return a fabricated counterexample. The implementation still labels a finite test only `empirically_survived`; the explanatory mathematical argument is separate from machine proof.

## Mathematical conventions and limits

- `BooleanFunction(n, bits)` stores bit `i = f(i)` with input variable `j = (i >> j) & 1`. Functions support up to five variables, exact truth tables, Boolean expressions, composition, and AND/OR/NOT/XOR.
- Full function enumeration is capped at n≤4. Pair enumeration at n=3 has 65,536 pairs; n=4 has **4,294,967,296**. The default million-case limit yields `unknown` when unfinished, never survival.
- Primitive measures: truth-table weight, maximum sensitivity, average sensitivity, algebraic degree, monomial count, Fourier L1/L2, certificate complexity, decision-tree depth. Influence and individual Fourier coefficients are available on functions. Rational values are exact and serialize in witnesses as fractions where needed.
- GF(2) degree uses degree(0)=0. Fourier uses normalized Walsh coefficients of the sign function `(-1)^f`; its L2 norm is always 1, so it cannot distinguish functions by itself.
- Measure DSL allows registered primitives, small integer constants, `+ - *`, binary `min/max`. RHS DSL allows integer constants, `M(f)`, `M(g)`, `+ - *`, and division by nonzero constant expressions. NOT bounds accept only `M(f)`. No model-generated Python or Lean code is executed.
- A composite expression is only a candidate numeric measure; nonnegativity and useful lower-bound growth are not presumed.
- Free-form assumptions are `unsupported`, since the MVP cannot evaluate their predicates. Shared arity is inherent in the bound schema. Natural language/executable correspondence remains explicitly reviewable.
- Circuit DAGs can be evaluated with an explicit gate-count convention; minimum circuit size is not computed.

## Evidence and research labels

Statuses include generated, parse_failed, pending_verification, falsified, empirically_survived, formally_verified, known_result, circular, barrier_violation, unsupported, and unknown. A concrete witness immediately marks the version falsified; rechecks cannot erase it. Revisions have new IDs, a parent ID, and an incremented revision number. Five critique fields explain failure, broken assumptions, the replacement claim, trivial weakening, and remaining lower-bound relevance.

Separate classification fields distinguish unknown, known theorem, rediscovery, false claim, circular reasoning, and barrier violation. Except exact counterexample classification, these require human evidence; the tool does not automatically decide novelty, circularity, or formal barrier conditions. Duplicate metrics detect repeated executable schemas and do not establish knownness. Full verification history is retained.

The barrier classifier is transparent lexical triage. It always requests manual review; `no_obvious_barrier_detected` means only that the keyword rules did not flag text. Negation and indirect arguments can mislead it. See [proof barriers](docs/proof-barriers.md).

## Providers, SMT, and Lean

`LLMBackend.generate(prompt, **kwargs) -> str` isolates providers. `MockBackend` is deterministic. Optional `HTTPBackend` uses a chat-completions-compatible HTTPS endpoint and reads `PNP_LLM_API_KEY`, `PNP_LLM_BASE_URL`, and `PNP_LLM_MODEL` from environment variables. `.env.example` documents them; it is not automatically loaded. Select `--backend http` explicitly. Credentials are not written to configs or prompts. Real API calls were not exercised in the initial validation.

`SMTVerifier` implements real Z3 finite truth-table-weight checks for AND/OR/XOR/NOT, replays SAT witnesses using exact arithmetic, and treats UNSAT as finite survival. Other measures are currently unsupported. `SATVerifier` is an explicit unsupported skeleton.

```bash
python -m pnp_search run --config configs/default.yaml --experiment-name formal-smoke --lean
```

Lean checks only an allowlisted Boolean AND-commutativity template whose prose and formal statement match the canonical contract. Generated source and compiler evidence are saved. Only a successful supported Lean check can produce `formally_verified`, and semantic review remains required. This is a separate known Boolean identity, not formalization of arbitrary surviving measure bounds. Missing tooling produces an explicit unresolved outcome. See [Lean setup](lean/README.md); Lean/Mathlib are pinned to v4.24.0. The core proof was compiled; the Mathlib dependency is scaffolded but was not fetched or built.

## Layout and research material

`src/pnp_search/` contains models, exact Boolean calculations, measure DSL, prompts, providers, parsers, verifiers, classifiers, pipelines, and JSONL storage. `tests/` validates behavior; `configs/` controls runs; `scripts/` wraps the CLI. `experiments/runs/` holds ignored local runs, while curated examples belong in `experiments/results/`. `data/benchmark/` contains explicit fixture expectations. `lean/` isolates formal sources; `paper/` isolates report notes and figures.

- [Research plan](docs/research-plan.md)
- [Methodology](docs/methodology.md)
- [Terminology](docs/terminology.md)
- [Experiment protocol and metric denominators](docs/experiment-protocol.md)
- [Initial validation results and limitations](docs/validation.md)

Future work includes audited theorem catalogs, richer structured assumptions, held-out candidate benchmarks, stronger solver encodings, and reviewed formalization of operation bounds. Negative results and unsupported cases remain research data.
