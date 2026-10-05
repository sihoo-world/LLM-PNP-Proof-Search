"""Validated, JSON-serializable research records with explicit evidence states."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CandidateStatus(StrEnum):
    """Evidence labels; finite survival is never a general proof."""

    generated = "generated"
    parse_failed = "parse_failed"
    pending_verification = "pending_verification"
    falsified = "falsified"
    empirically_survived = "empirically_survived"
    formally_verified = "formally_verified"
    known_result = "known_result"
    circular = "circular"
    barrier_violation = "barrier_violation"
    unsupported = "unsupported"
    unknown = "unknown"


class UniversalBinaryOperationBound(BaseModel):
    """Executable finite test schema, separate from free-form mathematical prose."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    operation: Literal["AND", "OR", "XOR", "NOT"]
    measure: str
    relation: Literal["<="] = "<="
    rhs: str = Field(max_length=256)

    @field_validator("measure", mode="before")
    @classmethod
    def measure_name(cls, value: Any) -> str:
        """Allow primitive measure instances while persisting only declarative names."""
        if isinstance(value, str):
            return value
        if isinstance(getattr(value, "name", None), str):
            return value.name
        raise ValueError("Measure must be a declarative string or named measure instance")


class VerificationResult(BaseModel):
    """Verifier evidence and coverage, never an implicit claim about all arities."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    status: CandidateStatus
    verification_method: str
    verified_for_n: int | None = None
    counterexample_found: bool = False
    counterexample: dict[str, Any] | None = None
    cases_checked: int = Field(default=0, ge=0)
    complete: bool = False
    notes: list[str] = Field(default_factory=list)
    duration_seconds: float | None = None
    error: str | None = None
    formalization_review_required: bool = True

    @model_validator(mode="after")
    def consistent_evidence(self) -> "VerificationResult":
        """Prevent contradictory or unjustified status records."""
        if self.counterexample_found != (self.counterexample is not None):
            raise ValueError("Counterexample flag and payload must agree")
        if self.counterexample_found != (self.status == CandidateStatus.falsified):
            raise ValueError("A concrete counterexample requires falsified status")
        if self.status == CandidateStatus.empirically_survived and not self.complete:
            raise ValueError("Incomplete search cannot establish finite survival")
        if self.status == CandidateStatus.formally_verified:
            if self.verification_method != "lean" or not self.complete:
                raise ValueError("Formal verification requires completed Lean verification")
        return self


class CandidateLemma(BaseModel):
    """Versioned candidate plus provenance, executable interpretation, and audit trail."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    candidate_id: str = Field(default_factory=lambda: "C" + uuid4().hex)
    experiment_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model: str
    prompt_version: str = "candidate-v1"
    domain: str = "boolean_circuit_complexity"
    title: str
    natural_language_statement: str
    formalized_statement: str | None = None
    definitions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    claimed_implication: str = ""
    proof_sketch: str = ""
    source_output: str
    status: CandidateStatus = CandidateStatus.generated
    verification_method: str | None = None
    counterexample: dict[str, Any] | None = None
    notes: list[str] = Field(default_factory=list)
    parent_candidate_id: str | None = None
    revision_number: int = Field(default=0, ge=0)
    group: str = "A"
    bound: UniversalBinaryOperationBound | None = None
    lean_template: Literal["bool_and_commutative"] | None = None
    barrier_labels: list[str] = Field(default_factory=list)
    classification: Literal["unknown", "known_theorem", "rediscovery", "false_claim", "circular_reasoning", "barrier_violation"] = "unknown"
    classification_evidence: str | None = None
    formalization_review_required: bool = True
    revision_analysis: dict[str, str] = Field(default_factory=dict)
    verification_history: list[VerificationResult] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent_revision(self) -> "CandidateLemma":
        """Each noninitial revision must reference its distinct predecessor."""
        if (self.revision_number > 0) != (self.parent_candidate_id is not None):
            raise ValueError("Revision number and parent must be specified together")
        if self.parent_candidate_id == self.candidate_id:
            raise ValueError("A revision cannot be its own parent")
        if self.status == CandidateStatus.formally_verified:
            if not self.verification_history:
                raise ValueError("Formal candidate status requires recorded Lean evidence")
            latest = self.verification_history[-1]
            if latest.status != CandidateStatus.formally_verified or latest.verification_method != "lean" or not latest.complete:
                raise ValueError("Formal candidate status requires the latest completed Lean result")
            if any(result.status == CandidateStatus.falsified for result in self.verification_history):
                raise ValueError("A falsified candidate must be revised, not promoted")
        return self

    def mark_pending(self) -> None:
        """Start verification of a newly generated candidate only."""
        if self.status != CandidateStatus.generated:
            raise ValueError("Create a revision to retry a terminal candidate")
        self.status = CandidateStatus.pending_verification

    def apply_verification(self, result: VerificationResult) -> None:
        """Keep falsification sticky; record every attempt without erasing failures."""
        result = VerificationResult.model_validate(result.model_dump(mode="json"))
        if self.status == CandidateStatus.parse_failed:
            raise ValueError("A parse failure cannot be verified")
        # Validate the complete transition atomically: appending a nonformal result
        # before changing an existing formal status would temporarily contradict it.
        values = self.model_dump(mode="json")
        values["verification_history"].append(result.model_dump(mode="json"))
        if self.status != CandidateStatus.falsified:
            values.update(verification_method=result.verification_method, counterexample=result.counterexample,
                          status=result.status, formalization_review_required=result.formalization_review_required)
            if result.status == CandidateStatus.falsified:
                values["classification"] = "false_claim"
        validated = type(self).model_validate(values)
        object.__setattr__(self, "__dict__", validated.__dict__)
        object.__setattr__(self, "__pydantic_fields_set__", validated.__pydantic_fields_set__)


__all__ = ["CandidateLemma", "CandidateStatus", "UniversalBinaryOperationBound", "VerificationResult"]
