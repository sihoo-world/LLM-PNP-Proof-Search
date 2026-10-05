# Terminology and result interpretation

| Term or status | Meaning in this project |
| --- | --- |
| candidate / conjecture | Untrusted proposed mathematical statement. |
| lemma | A role intended for a statement; the word alone does not certify it. |
| generated | Raw model output has been received. |
| parse_failed | Output cannot be converted to the supported claim schema. |
| pending_verification | A supported structured claim awaits checking. |
| falsified / false claim | A validated counterexample violates the structured claim under its assumptions. |
| empirically_survived | No counterexample in the explicitly completed finite scope. Never a universal proof. |
| formally_verified | The allowed formal theorem passed actual Lean checking; scope and semantic correspondence still require review. |
| known_result | A claim has been matched to an identified established result with evidence; this is not a fresh proof by the platform. |
| rediscovery | A generation event reproduced a known result. Track as a novelty annotation, independently of verification. |
| circular | Review identified reliance on the conclusion or an equivalent unresolved premise. Mere keyword matches are insufficient. |
| barrier_violation | Reserved for an evidenced, scoped mathematical review of an argument's incompatible claim; never assigned from a keyword heuristic alone. |
| unsupported | The checker cannot express or handle this claim or measure. |
| unknown | No justified verdict, including interrupted searches or solver unknown. |

Status describes the latest evidence recorded for one candidate version, not
confidence that an asymptotic proof strategy will work. Preserve the verifier
history when later review adds new evidence. Never turn a falsified record into
a revised successful one by editing its statement in place.

Barrier classifier labels are independent annotations:
`likely_relativizing`, `possibly_natural`, `possible_algebrization_issue`,
`no_obvious_barrier_detected`, and `manual_review_required`. They are heuristic
triage labels, not calibrated probabilities or mathematical verdicts.
`no_obvious_barrier_detected` means only that the implemented rules did not fire.

Duplicate means the same structured claim under an explicit normalization,
including measure, operation, relation, right-hand side, assumptions, and scope.
It is not equivalent to known theorem. Text similarity alone proves neither
logical equivalence nor prior publication.

A circuit is a directed acyclic graph of gates with possible sharing; a formula
is a tree. A lower bound for one does not transfer automatically to the other.
A finite property concerns a stated n; an asymptotic claim quantifies over a
family as n grows. These distinctions must remain visible in exports and papers.
