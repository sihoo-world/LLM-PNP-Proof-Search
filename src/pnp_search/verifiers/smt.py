"""An actual finite Z3 encoding for truth-table-weight operation bounds."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from pnp_search.boolean import BooleanFunction
from pnp_search.counterexamples import build_counterexample
from pnp_search.measures import parse_measure
from pnp_search.models import CandidateStatus, VerificationResult
from pnp_search.verifiers.dsl import BoundExpression, UnsupportedBound
from pnp_search.verifiers.exhaustive import (
    BoundInput, apply_operation, exact_measure, finish, get_bound,
)


class SMTVerifier:
    """Solve a fixed-arity weight inequality, with timeout and witness replay.

    UNSAT means no counterexample in this finite encoding; it never assigns
    ``formally_verified``. Non-weight primitives are explicitly unsupported.
    """

    def __init__(self, n: int = 3, timeout_ms: int = 10_000, seed: int = 0) -> None:
        if type(n) is not int or not 0 <= n <= 4:
            raise ValueError("SMT verifier supports integer arities 0 <= n <= 4")
        if type(timeout_ms) is not int or timeout_ms <= 0:
            raise ValueError("timeout_ms must be a positive integer")
        if type(seed) is not int or not 0 <= seed < 2**32:
            raise ValueError("seed must be an unsigned 32-bit integer")
        self.n, self.timeout_ms, self.seed = n, timeout_ms, seed

    def verify(self, candidate: BoundInput) -> VerificationResult:
        """Search a symbolic finite truth table and replay any resulting witness."""
        started = perf_counter()

        def result(status: str, **kwargs: object) -> VerificationResult:
            return finish(candidate, VerificationResult(
                status=CandidateStatus(status), verification_method="smt",
                verified_for_n=self.n, duration_seconds=perf_counter() - started, **kwargs,
            ))

        try:
            bound = get_bound(candidate)
            measure = parse_measure(bound.measure)
            if measure.name != "truth_table_weight":
                raise UnsupportedBound("SMT currently supports only truth_table_weight")
            rhs_expression = BoundExpression(bound.rhs, unary=bound.operation == "NOT")
            import z3
        except ImportError:
            return result("unsupported", error="Install project dependencies (z3-solver) to use SMTVerifier")
        except (UnsupportedBound, ValueError, TypeError) as exc:
            return result("unsupported", error=str(exc))

        count = 1 << self.n
        f_vars = [z3.Bool(f"f_{i}") for i in range(count)]
        g_vars = [z3.Bool(f"g_{i}") for i in range(count)]
        operations = {"AND": z3.And, "OR": z3.Or, "XOR": z3.Xor}
        output_vars = [z3.Not(f) for f in f_vars] if bound.operation == "NOT" else [
            operations[bound.operation](f, g) for f, g in zip(f_vars, g_vars)
        ]

        def weight(variables: list[Any]) -> Any:
            # ToReal is essential: Z3 integer division would change rational DSL semantics.
            return z3.ToReal(z3.Sum([z3.If(item, 1, 0) for item in variables]))

        solver = z3.Solver()
        solver.set(timeout=self.timeout_ms, random_seed=self.seed)
        solver.add(weight(output_vars) > rhs_expression.evaluate(weight(f_vars), weight(g_vars)))
        answer = solver.check()
        if answer == z3.unknown:
            return result("unknown", error=solver.reason_unknown(), notes=["SMT search did not decide the finite encoding."])
        if answer == z3.unsat:
            return result("empirically_survived", complete=True, notes=[
                f"Z3 {z3.get_version_string()} returned UNSAT for the negated weight bound at n={self.n}.",
                "Fixed-arity solver evidence only; this is not an arbitrary-arity theorem or a Lean proof.",
            ])

        model = solver.model()

        def decode(variables: list[Any]) -> BooleanFunction:
            bits = sum(1 << index for index, item in enumerate(variables)
                       if z3.is_true(model.eval(item, model_completion=True)))
            return BooleanFunction(self.n, bits)

        f = decode(f_vars)
        g = None if bound.operation == "NOT" else decode(g_vars)
        output = apply_operation(bound.operation, f, g)
        f_value = exact_measure(measure, f)
        g_value = None if g is None else exact_measure(measure, g)
        lhs = exact_measure(measure, output)
        rhs = rhs_expression.evaluate(f_value, g_value)
        if lhs <= rhs:
            return result("unknown", error="SMT witness failed exact replay")
        witness = build_counterexample(
            f=f, g=g, output=output, operation=bound.operation,
            measure_name=bound.measure, f_value=f_value, g_value=g_value,
            lhs=lhs, rhs=rhs, rhs_source=bound.rhs,
        )
        return result("falsified", complete=True, counterexample_found=True,
                      counterexample=witness, cases_checked=1,
                      notes=[f"Z3 {z3.get_version_string()} witness replayed with exact arithmetic."])


class SATVerifier:
    """Reserved interface: no SAT encoding is claimed to exist yet."""

    def verify(self, candidate: BoundInput) -> VerificationResult:
        """Record unsupported status instead of a fabricated verification result."""
        return finish(candidate, VerificationResult(
            status=CandidateStatus.unsupported, verification_method="sat",
            error="SAT encoding is not implemented; use exhaustive or SMT verification.",
        ))
