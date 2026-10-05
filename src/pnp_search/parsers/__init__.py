"""Strict parsing that never accepts model-provided proof statuses."""

import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pnp_search.models import CandidateLemma, CandidateStatus, UniversalBinaryOperationBound


class CandidateOutput(BaseModel):
    """The provider's limited output contract, independent of trusted provenance."""

    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1)
    domain: str
    definitions: list[str]
    assumptions: list[str] = Field(default_factory=list)
    lemma: str = Field(min_length=1)
    motivation: str
    proof_sketch: str
    expected_implication: str
    possible_failure_modes: list[str]
    bound: UniversalBinaryOperationBound
    revision_analysis: dict[str, str] = Field(default_factory=dict)


def parse_candidate(raw: str, *, experiment_id: str, model: str, candidate_id: str,
                    group: str = "A", parent: CandidateLemma | None = None) -> CandidateLemma:
    """Preserve malformed responses as parse_failed records with their original text."""
    provenance = dict(experiment_id=experiment_id, model=model, candidate_id=candidate_id,
                      group=group, source_output=raw, parent_candidate_id=parent.candidate_id if parent else None,
                      revision_number=parent.revision_number + 1 if parent else 0,
                      prompt_version="revision-v1" if parent else "candidate-v1")
    try:
        if len(raw) > 1_000_000:
            raise ValueError("Candidate output exceeds 1 MB")
        output = CandidateOutput.model_validate_json(raw)
        required = {"failure_explanation", "broken_assumption", "revised_statement", "nontriviality", "lower_bound_relevance"}
        if parent and (set(output.revision_analysis) != required or not all(v.strip() for v in output.revision_analysis.values())):
            raise ValueError("Revision must include all five critique fields")
        return CandidateLemma(**provenance, title=output.title, domain=output.domain,
                              natural_language_statement=output.lemma,
                              formalized_statement=json.dumps(output.bound.model_dump(), sort_keys=True),
                              definitions=output.definitions, assumptions=output.assumptions,
                              claimed_implication=output.expected_implication, proof_sketch=output.proof_sketch,
                              notes=[output.motivation, *output.possible_failure_modes], bound=output.bound,
                              revision_analysis=output.revision_analysis)
    except (ValueError, ValidationError) as exc:
        return CandidateLemma(**provenance, title="Unparsed candidate", natural_language_statement="",
                              status=CandidateStatus.parse_failed, notes=[type(exc).__name__ + ": candidate schema rejected"])

