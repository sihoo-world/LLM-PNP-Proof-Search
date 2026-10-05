# Research plan

## Research question and scope

Can an LLM improve candidate Boolean circuit lower-bound lemmas through repeated
counterexample search, critique, revision, and carefully scoped formal checking?
The deliverable is a reproducible research platform and a corpus of successes,
failures, and unresolved candidates. A generated argument is never mathematical
evidence by itself. This repository makes no claim to settle P versus NP.

The first language expresses bounds on measures under Boolean operations. It is
intentionally narrower than arbitrary mathematical prose. Small-input exact
experiments exercise that language before generalizations are considered.

## Milestones and acceptance criteria

1. Represent Boolean functions exactly; enumerate every function on three inputs
   and every ordered pair when the budget permits. Test independently calculable
   values, including constants, projections, parity, and conjunction.
2. Generate and parse a mock structured candidate; preserve raw output and parse
   failures. Run at least three measures through the same verifier interface.
3. Persist a complete generation-to-counterexample run with the machine-readable
   witness, evaluated inequality, configuration, seed, and software provenance.
4. Revise a falsified candidate using its witness. Preserve both records and the
   parent relationship. Review weakening and relevance separately from survival.
5. Check a trusted small Lean theorem and store the actual compiler evidence.
   Missing tooling or failed compilation is not a successful milestone.
6. Compare real model groups with equal budgets, held-out validation, literature
   review, and transparent failure denominators. Mock outputs test infrastructure;
   they do not measure LLM research ability.

## Mathematical target

A measure's gate inequalities alone do not establish circuit lower bounds.
Further work must specify the circuit basis, fan-in, fan-out, constants, size,
depth, input encoding, and uniformity; establish an induction valid for that
model; and exhibit an explicit function family with the required measure growth.
An induction that duplicates shared subcircuits may give only a formula bound.
Restricted circuit lower bounds do not automatically extend to general circuits.

An NP language outside P/poly would imply P != NP, but this is stronger than the
separation required. Finite truth-table experiments cannot supply such an
asymptotic statement. Keep the claimed implication and every missing bridge as
separate, reviewable fields.

## Reporting

Publish rejected candidates and their witnesses, parsing and resource failures,
known-result rediscoveries, and inconclusive checks. Novelty is a literature
judgment, not absence from a small local benchmark. Report the implementation's
actual supported grammar and verifier coverage, not just planned capabilities.
