# Proof barriers and conservative triage

These barriers constrain specified proof methods and target statements. They
are not tests that disprove every small lemma used in a lower-bound program.

## Relativization

Baker, Gill, and Solovay construct oracle settings in which P and NP coincide
and others in which they differ. Consequently a proof settling the unrelativized
question cannot remain valid uniformly under arbitrary oracle access. This
does not invalidate a finite Boolean identity or rule out every use of
diagonalization. See the original
[Relativizations of the P = ? NP Question (1975)](https://doi.org/10.1137/0204037).

Triage may flag arguments claiming to work unchanged for every oracle. Review
must identify the relativizing steps, oracle model, and claimed consequence.
The word "oracle" alone is insufficient for a mathematical conclusion.

## Natural Proofs

Razborov and Rudich analyze properties of truth tables that are constructive
(efficient in truth-table length), large (hold for a sufficiently large fraction
of all Boolean functions), and useful against a target small-circuit class.
Their obstruction to strong general circuit lower bounds is conditional on
appropriate pseudorandomness hardness. It is not an unconditional assertion
that all combinatorial measures fail. The circuit class and quantitative
parameters of usefulness, density, constructivity, and hardness matter. See
[Natural Proofs (1997)](https://doi.org/10.1006/jcss.1997.1494).

A search proposing an efficiently decidable property satisfied by many
functions is a reason for manual analysis, not proof that the barrier applies.
Testing small tables establishes none of the asymptotic conditions. Review
also needs the explicit hard family and the claimed target circuit class.

## Algebrization

Aaronson and Wigderson extend oracle-based analysis by providing access to
low-degree algebraic extensions. They show limitations of this framework for
central complexity separations, even though arithmetization can overcome
ordinary relativization. A polynomial expression or an algebraic-degree
inequality is not automatically an algebrizing proof. The oracle-access model
and the direction of the inclusion or separation must be analyzed. See
[Algebrization: A New Barrier in Complexity Theory](https://www.scottaaronson.com/papers/alg.pdf).

## Classifier policy

The MVP classifier is heuristic triage. Preserve triggering text or rules and
always keep a manual-review requirement. Do not change a candidate to
`barrier_violation` merely because a cue is present. Do not infer "barrier-free"
from `no_obvious_barrier_detected` or attach an invented calibrated probability.

Human review should record: target statement, model, exact barrier hypotheses,
which proof steps meet them, uncertainty, references, and reviewer. A barrier
flag can coexist with a correct finite lemma; relevance to a future asymptotic
argument remains a separate question.

Group B prompts should summarize these qualified statements. Group A omits
that context. Compare group outcomes under equal generation and checking
budgets; a rule that merely recognizes copied barrier words can bias flag-rate
comparisons and must not be treated as a quality score.
