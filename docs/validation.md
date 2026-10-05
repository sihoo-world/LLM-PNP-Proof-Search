# Initial MVP validation

Validated locally on 2026-10-05 (Asia/Seoul), Windows, Python 3.12.14.

## Commands and outcomes

- `.venv/Scripts/python.exe -m pytest -q`: **184 passed** (7.20 seconds in the final full-suite run).
- `.venv/Scripts/python.exe -m compileall -q src scripts`: exit 0.
- `.venv/Scripts/python.exe -m pip check`: no broken requirements.
- `python -m pnp_search run --config configs/default.yaml --experiment-name mvp-final --lean --output-dir experiments/results`: completed.
- Real Z3 tests passed for finite weight bounds, including SAT witnesses replayed with exact arithmetic and finite UNSAT cases.
- Real Lean 4.24.0 compiled the admitted generated Boolean AND identity and reported that its theorem depends on no axioms.

The final full pipeline artifact is
[`mvp-final-20261004T170105Z-43130e28`](../experiments/results/mvp-final-20261004T170105Z-43130e28/manifest.json).
Its name and internal timestamps use UTC. The source hashes record the code and
tests used by that run; this retrospective report was added afterward.

The run has nine candidate versions: six finite survivors, two falsified roots,
and one separately identified trusted-template Lean result. Both falsified roots
have linked surviving revisions. Group A and B each contain four versions; the
formal smoke check is a separate group. These are deterministic infrastructure
fixtures, not a study of LLM mathematical quality or novel results.

For each of algebraic degree, sensitivity, and weight, the AND sum bound passes
all 65,536 ordered pairs at n=3. A deliberately false weight XOR bound fails
for f.bits=0 and g.bits=1: output weight 1 exceeds RHS 0. Resource-limited n=4
searches remain unknown, not proved or empirically survived.

## Limits of this validation

No real model API was called. SAT is an unsupported skeleton; SMT supports only
truth-table weight. No arbitrary generated Lean proof is executed. The pinned
Mathlib dependency was not fetched or built; the verified Boolean template uses
Lean core. Natural-language alignment outside the canonical template, novelty,
circularity, and proof-barrier applicability still require human review.

Candidate JSON imports now reject formal status without a completed Lean
verification history. This structural consistency check does not authenticate
third-party evidence: external records must still be reviewed and reverified.

At the time of this local validation, GitHub workflows had not run remotely
and no remote was configured. The project was subsequently published to the
public [GitHub repository](https://github.com/sihoo-world/LLM-PNP-Proof-Search).
Remote CI results are reported by GitHub Actions separately from this snapshot.
