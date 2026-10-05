# Experiment protocol

## Before a run

Record experiment ID and human-readable name, UTC timestamp, code revision and
dirty state, configuration snapshot, Python/dependency versions, seed, model
identity, generation parameters, prompt version and exact prompt, verification
scope and resource budget. Do not store API keys in configuration or logs.
Real providers may remain nondeterministic even with a fixed seed: raw-output
replay, not an unsupported promise of API determinism, is the reproducibility
baseline. Mock experiments are deterministic infrastructure fixtures.

## Record layout

Keep prompts, raw outputs, parsed candidate versions, counterexamples, verifier
results, and summaries as separate artifacts joined by experiment and candidate
identifiers. JSONL stores one independently decodable object per line. Do not
delete failures or overwrite falsified parents. An incomplete run must retain
completed records and a failure artifact; it must not silently look complete.

Counterexamples include n, encoding convention, f and g tables, operation,
measure values, right-hand-side value, relation, and the violated inequality.
Human-readable expressions supplement rather than replace exact truth tables.
Formal evidence includes generated source, theorem identifier, source hash,
toolchain, command, return code, output, and semantic-review state. If a solver
returns unknown or a compiler is missing, retain that outcome without upgrading
candidate validity.

## Experimental groups

| Group | Controlled change |
| --- | --- |
| A: baseline | Structured generation without barrier context. |
| B: barrier context | Same budget and output schema plus qualified barrier summaries. |
| Feedback | A or B plus counterexamples and a fixed maximum revision count. |
| Formal follow-up | Same feedback procedure plus supported Lean templates. |

Compare multiple model seeds where a provider supports them. Keep a development
benchmark separate from held-out statements and larger-n checks. Do not give
one group extra revisions, verifier time, or favorable filters. Report when
formalization coverage differs: a small template library is a selection effect.

## Metrics and denominators

Let T be the number of recorded candidate versions, P the number parsed,
F the number falsified, E empirically survived, V formally verified, R versions
with a parent, and S surviving revised versions (empirical or formal). Publish
raw counts alongside rates and treat a zero denominator as a reported zero
with its denominator shown, not positive evidence.

| Metric | Reporting definition |
| --- | --- |
| total_candidates | T, including parse failures and revisions. |
| parse_success_rate | P / T. |
| falsification_rate | F / T; optionally also F / attempted checks, explicitly named. |
| empirical_survival_rate | E / T, with exact finite coverage. |
| formal_verification_rate | V / T; also report supported formal-template coverage. |
| revision_survival_rate | S / R, distinguishing empirical from formal survival. |
| average_revisions | Total revision versions / root candidate count. |
| barrier_flag_rate | Candidates with substantive heuristic barrier flags / T; mandatory manual-review labels alone do not count. |
| duplicate_or_known_result_rate | Union of identified duplicates and evidenced known-result records / T, without double-counting. |

Group summaries must use the same definitions. Status snapshots can hide prior
finite survival after formal checking; keep the full history and identify which
snapshot is summarized. Counts of inherited revisions are not independent
observations. Report family-level outcomes in addition to candidate-level rates
before claiming statistical improvement.

## Revision and negative-result review

Recheck revised statements from scratch. Add held-out witnesses or sizes to
reduce counterexample overfitting. Mark tautologies, weakened goals, narrowed
domains, circular dependencies, and known-result rediscoveries in review notes.
False candidates and unsuccessful repairs are publishable research data, not
records to omit from quality metrics. No finite rate measures progress toward
settling P versus NP by itself.
