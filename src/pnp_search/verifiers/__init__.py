"""Finite verifier interfaces, with strict separation from formal proof."""

from typing import Protocol

from pnp_search.models import CandidateLemma, UniversalBinaryOperationBound, VerificationResult
from pnp_search.verifiers.exhaustive import ExhaustiveVerifier
from pnp_search.verifiers.smt import SATVerifier, SMTVerifier
from pnp_search.verifiers.lean import LeanVerifier


class Verifier(Protocol):
    """A verifier produces explicit evidence for an executable interpretation."""

    def verify(self, candidate: CandidateLemma | UniversalBinaryOperationBound) -> VerificationResult:
        """Return evidence including scope, coverage, and any concrete witness."""
        ...


__all__ = ["Verifier", "ExhaustiveVerifier", "SMTVerifier", "SATVerifier", "LeanVerifier"]
