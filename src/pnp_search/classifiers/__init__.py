"""Transparent lexical triage; labels are not mathematical barrier judgments."""

from pnp_search.models import CandidateLemma


def classify_barriers(candidate: CandidateLemma) -> list[str]:
    """Flag terms for human review; neither presence nor absence proves applicability."""
    text = " ".join([candidate.natural_language_statement, candidate.proof_sketch, *candidate.assumptions]).lower()
    labels = []
    for needles, label in [(("oracle", "relativiz"), "likely_relativizing"),
                           (("natural proof", "largeness", "constructivity", "pseudorandom"), "possibly_natural"),
                           (("algebriz", "algebraic extension"), "possible_algebrization_issue")]:
        if any(needle in text for needle in needles):
            labels.append(label)
    if not labels:
        labels.append("no_obvious_barrier_detected")
    labels.append("manual_review_required")
    return labels

