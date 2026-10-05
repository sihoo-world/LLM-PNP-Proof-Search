"""Deterministic finite-domain counterexample search with explicit coverage."""

from __future__ import annotations

import logging
from fractions import Fraction
from time import perf_counter

from pnp_search.boolean import BooleanFunction
from pnp_search.counterexamples import build_counterexample
from pnp_search.measures import ComplexityMeasure, parse_measure
from pnp_search.models import (
    CandidateLemma, CandidateStatus, UniversalBinaryOperationBound, VerificationResult,
)
from pnp_search.verifiers.dsl import BoundExpression, UnsupportedBound

LOGGER = logging.getLogger(__name__)
BoundInput = UniversalBinaryOperationBound | CandidateLemma


def get_bound(candidate: BoundInput) -> UniversalBinaryOperationBound:
    """Extract the executable interpretation; do not infer it from prose."""
    if isinstance(candidate, UniversalBinaryOperationBound):
        return candidate
    if candidate.status == CandidateStatus.parse_failed:
        raise UnsupportedBound("A parse failure has no executable interpretation")
    if candidate.bound is None:
        raise UnsupportedBound("No executable operation-bound formalization was supplied")
    if candidate.assumptions:
        raise UnsupportedBound("Free-form assumptions cannot be checked by this finite verifier")
    return candidate.bound


def exact_measure(measure: ComplexityMeasure, function: BooleanFunction) -> Fraction:
    """Reject inexact measures rather than silently rounding an inequality."""
    value = measure.evaluate(function)
    if not isinstance(value, (int, Fraction)):
        raise UnsupportedBound("Measures must return exact integers or fractions")
    return Fraction(value)


def apply_operation(operation: str, f: BooleanFunction, g: BooleanFunction | None) -> BooleanFunction:
    """Apply the exact truth-table operation represented by a bound."""
    if operation == "NOT":
        return ~f
    if g is None:
        raise UnsupportedBound("Binary operations require two operands")
    if operation == "AND":
        return f & g
    if operation == "OR":
        return f | g
    if operation == "XOR":
        return f ^ g
    raise UnsupportedBound(f"Unsupported operation: {operation}")


def finish(candidate: BoundInput, result: VerificationResult) -> VerificationResult:
    """Persist a verifier outcome on a candidate while keeping failures sticky."""
    if isinstance(candidate, CandidateLemma) and candidate.status != CandidateStatus.parse_failed:
        candidate.apply_verification(result)
    return result


class ExhaustiveVerifier:
    """Search all Boolean functions at one arity, unless a case budget is reached.

    A found counterexample decides the finite claim immediately. Otherwise only
    complete coverage receives ``empirically_survived``. ``verified_for_n`` names
    the attempted finite arity and does not assert a theorem for arbitrary n.
    """

    def __init__(self, n: int = 3, max_cases: int = 1_000_000) -> None:
        if type(n) is not int or not 0 <= n <= 4:
            raise ValueError("Exhaustive verifier supports integer arities 0 <= n <= 4")
        if type(max_cases) is not int or not 1 <= max_cases <= 100_000_000:
            raise ValueError("max_cases must be an integer between 1 and 100000000")
        self.n = n
        self.max_cases = max_cases

    def verify(self, candidate: BoundInput) -> VerificationResult:
        """Find the first lexicographic witness, or report exact finite coverage."""
        started = perf_counter()
        checked = 0

        def result(status: str, **kwargs: object) -> VerificationResult:
            return finish(candidate, VerificationResult(
                status=CandidateStatus(status), verification_method="exhaustive",
                verified_for_n=self.n, cases_checked=checked,
                duration_seconds=perf_counter() - started, **kwargs,
            ))

        try:
            bound = get_bound(candidate)
            measure = parse_measure(bound.measure)
            rhs_expression = BoundExpression(bound.rhs, unary=bound.operation == "NOT")
        except (UnsupportedBound, ValueError, TypeError) as exc:
            return result("unsupported", error=str(exc))

        function_count = 1 << (1 << self.n)
        total_cases = function_count if bound.operation == "NOT" else function_count ** 2
        values: dict[int, Fraction] = {}

        def measure_value(function: BooleanFunction) -> Fraction:
            if function.bits not in values:
                values[function.bits] = exact_measure(measure, function)
            return values[function.bits]

        try:
            for f_bits in range(function_count):
                f = BooleanFunction(self.n, f_bits)
                f_value = measure_value(f)
                g_range = range(1) if bound.operation == "NOT" else range(function_count)
                for g_bits in g_range:
                    if checked >= self.max_cases:
                        return result("unknown", notes=[
                            f"Case budget exhausted: checked {checked} of {total_cases} cases.",
                            "Incomplete finite search is not empirical survival or a general proof.",
                        ])
                    g = None if bound.operation == "NOT" else BooleanFunction(self.n, g_bits)
                    g_value = None if g is None else measure_value(g)
                    output = apply_operation(bound.operation, f, g)
                    lhs = measure_value(output)
                    rhs = rhs_expression.evaluate(f_value, g_value)
                    checked += 1
                    if lhs > rhs:
                        witness = build_counterexample(
                            f=f, g=g, output=output, operation=bound.operation,
                            measure_name=bound.measure, f_value=f_value, g_value=g_value,
                            lhs=lhs, rhs=rhs, rhs_source=bound.rhs,
                        )
                        LOGGER.info("Found counterexample at n=%s after %s cases", self.n, checked)
                        return result("falsified", complete=True, counterexample_found=True,
                                      counterexample=witness)
        except UnsupportedBound as exc:
            return result("unsupported", error=str(exc))
        except (ValueError, TypeError, ArithmeticError) as exc:
            LOGGER.exception("Finite verification failed")
            return result("unknown", error=str(exc))

        return result("empirically_survived", complete=True, notes=[
            f"All {total_cases} cases at n={self.n} passed the executable bound.",
            "Finite evidence only: no claim for arbitrary arity or circuit lower bounds.",
            "The correspondence between the executable bound and natural-language statement requires review.",
        ])
