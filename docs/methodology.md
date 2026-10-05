# Methodology and trust boundaries

## Candidate versus evidence

Natural-language text, structured executable claim, proof sketch, verifier
evidence, and human review are distinct artifacts. A parser only checks schema
and grammar. A verifier checks the structured claim in its supported scope; it
does not silently validate every sentence in the source output.

Candidates with assumptions outside the executable grammar must remain
unsupported or unknown. Never discard an assumption and then describe the
resulting computation as a check of the original claim. Record whether a human
has reviewed the correspondence between prose and formalization.

## Exact finite semantics

For n inputs, the truth table has 2^n entries. Index x denotes the assignment
whose coordinate i is bit i of x. Integer bit x stores f(x). All operations are
pointwise, and complements are masked to that finite table width.

The algebraic normal form is over GF(2), with square-free monomials. For the zero
function this project uses degree 0 as an explicit computational convention.
It is not silently interchangeable with the mathematical convention -infinity.
For this convention, deg(f AND g) <= deg(f) + deg(g) is a valid bound: multiply
the GF(2) polynomials and reduce x_i^2 to x_i. Thus this example should survive
finite tests; a fabricated counterexample would be a bug. AND degree bounded by
max(deg(f), deg(g)) is false for two distinct projections.

Sensitivity is the largest number of single-bit flips changing an output.
Influence of coordinate i is that change probability under uniform input;
average sensitivity is the sum of influences. Unless explicitly stated
otherwise, Fourier coefficients use the sign function (-1)^f and uniform
normalization. Record conventions with each measure version.

## Search coverage

There are 2^(2^n) Boolean functions. Binary exhaustive checking requires the
square of that count: at n=3 this is 65,536 ordered pairs; at n=4 it is
4,294,967,296. Enumeration of all 65,536 individual four-input functions is
different from enumeration of all pairs. Apply explicit work limits.

A found witness falsifies the supported quantified claim immediately. No
witness after completed finite enumeration earns only empirically_survived,
with the checked n and scope. A stopped, timed-out, unsupported, or failed run
cannot earn that status. Sampled coverage, if added, must be distinguished from
exhaustive coverage, with a replayable sampling procedure and budget.

## Execution boundary

Measures and right-hand sides use an allowlisted expression language. No eval,
exec, dynamic imports, arbitrary attributes, subprocess calls, or LLM-provided
Python are needed. Reject oversized expressions and invalid arithmetic. Solver
encodings must state supported measures and decode witnesses into the same
Boolean representation so Python can independently recheck them.

Lean execution is restricted to trusted templates for the MVP. Arbitrary Lean
source can contain executable elaborators or IO; a compiler is not a sandbox.
An allowed theorem must actually occur in the checked source, without admitted
proofs or unreviewed added axioms. Compilation success is evidence about the
formal theorem only. It is not evidence of novelty or automatic correspondence
with an unrelated prose claim.

## Revision protocol

A revision is a new immutable candidate with a new identifier, its parent ID,
and incremented revision number. A falsified parent stays falsified. Preserve
the critique and require: failure explanation, precise failed assumption,
replacement claim, nontriviality argument, and remaining lower-bound relevance.
Trivially weakened statements may survive without scientific progress. Keep
this assessment separate from the finite verifier result.
