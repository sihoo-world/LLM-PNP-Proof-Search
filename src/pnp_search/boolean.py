"""Exact Boolean functions; bit i is the value at little-endian assignment i."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
from typing import TYPE_CHECKING, Iterable, Iterator, Sequence

if TYPE_CHECKING:
    from sympy.logic.boolalg import Boolean


@dataclass(frozen=True, slots=True)
class BooleanFunction:
    """An immutable truth table on zero to five labeled Boolean variables.

    Assignment i sets variable j to (i >> j) & 1.  The zero polynomial has
    algebraic degree zero here, a convenient convention for upper bounds.
    """

    n: int
    bits: int

    def __post_init__(self) -> None:
        """Reject malformed or oversized truth tables."""
        if type(self.n) is not int or not 0 <= self.n <= 5:
            raise ValueError("n must be an integer between 0 and 5")
        if type(self.bits) is not int or not 0 <= self.bits < 1 << (1 << self.n):
            raise ValueError("bits must fit the truth table exactly")

    @property
    def truth_table(self) -> tuple[int, ...]:
        """Return entries in assignment-index order."""
        return tuple((self.bits >> i) & 1 for i in range(1 << self.n))

    @classmethod
    def from_truth_table(cls, values: Iterable[int]) -> BooleanFunction:
        """Decode a nonempty power-of-two table of zero/one values."""
        table = tuple(values)
        size = len(table)
        if not size or size & (size - 1) or any(type(v) not in (int, bool) or v not in (0, 1) for v in table):
            raise ValueError("truth table must have power-of-two length and Boolean entries")
        return cls(size.bit_length() - 1, sum(int(v) << i for i, v in enumerate(table)))

    @classmethod
    def variable(cls, n: int, index: int) -> BooleanFunction:
        """Return the coordinate projection x_index."""
        cls(n, 0)
        if type(index) is not int or not 0 <= index < n:
            raise ValueError("variable index out of range")
        return cls(n, sum(((i >> index) & 1) << i for i in range(1 << n)))

    @classmethod
    def constant(cls, n: int, value: int | bool) -> BooleanFunction:
        """Return a constant truth table."""
        cls(n, 0)
        if type(value) not in (int, bool) or value not in (0, 1):
            raise ValueError("constant must be zero or one")
        return cls(n, ((1 << (1 << n)) - 1) if value else 0)

    def __call__(self, assignment: int) -> int:
        """Evaluate an integer-encoded assignment."""
        if type(assignment) is not int or not 0 <= assignment < 1 << self.n:
            raise ValueError("assignment out of range")
        return (self.bits >> assignment) & 1

    def _check_other(self, other: BooleanFunction) -> None:
        """Enforce equal domains before pointwise operations."""
        if not isinstance(other, BooleanFunction) or self.n != other.n:
            raise ValueError("Boolean functions must have equal arity")

    def __and__(self, other: BooleanFunction) -> BooleanFunction:
        """Return pointwise conjunction."""
        self._check_other(other)
        return BooleanFunction(self.n, self.bits & other.bits)

    def __or__(self, other: BooleanFunction) -> BooleanFunction:
        """Return pointwise disjunction."""
        self._check_other(other)
        return BooleanFunction(self.n, self.bits | other.bits)

    def __xor__(self, other: BooleanFunction) -> BooleanFunction:
        """Return pointwise exclusive-or."""
        self._check_other(other)
        return BooleanFunction(self.n, self.bits ^ other.bits)

    def __invert__(self) -> BooleanFunction:
        """Complement precisely the truth-table width."""
        return BooleanFunction(self.n, self.bits ^ ((1 << (1 << self.n)) - 1))

    def compose(self, functions: Sequence[BooleanFunction]) -> BooleanFunction:
        """Substitute same-arity inner functions for this function's variables."""
        if len(functions) != self.n:
            raise ValueError("one inner function is required per outer variable")
        if not functions:
            return self
        n = functions[0].n
        if any(f.n != n for f in functions):
            raise ValueError("inner functions must have equal arity")
        return BooleanFunction.from_truth_table(
            self(sum(f(i) << j for j, f in enumerate(functions))) for i in range(1 << n)
        )

    @property
    def weight(self) -> int:
        """Return the number of satisfying assignments (Hamming weight)."""
        return self.bits.bit_count()

    def local_sensitivity(self, assignment: int) -> int:
        """Count coordinate flips changing the value at one assignment."""
        value = self(assignment)
        return sum(value != self(assignment ^ (1 << j)) for j in range(self.n))

    @property
    def sensitivity(self) -> int:
        """Return maximum local sensitivity."""
        return max(self.local_sensitivity(i) for i in range(1 << self.n))

    def influence(self, index: int) -> Fraction:
        """Return the uniform probability that flipping coordinate index changes f."""
        if type(index) is not int or not 0 <= index < self.n:
            raise ValueError("variable index out of range")
        return Fraction(sum(self(i) != self(i ^ (1 << index)) for i in range(1 << self.n)), 1 << self.n)

    @property
    def average_sensitivity(self) -> Fraction:
        """Return total influence under the uniform distribution."""
        return sum((self.influence(j) for j in range(self.n)), Fraction(0))

    @property
    def anf_coefficients(self) -> tuple[int, ...]:
        """Compute algebraic normal form via the GF(2) subset Mobius transform."""
        coefficients = list(self.truth_table)
        for j in range(self.n):
            for mask in range(1 << self.n):
                if mask & (1 << j):
                    coefficients[mask] ^= coefficients[mask ^ (1 << j)]
        return tuple(coefficients)

    @property
    def algebraic_degree(self) -> int:
        """Return maximum ANF monomial degree; degree(0) is defined as zero."""
        return max((mask.bit_count() for mask, c in enumerate(self.anf_coefficients) if c), default=0)

    @property
    def number_of_monomials(self) -> int:
        """Count nonzero ANF monomials, including the constant monomial."""
        return sum(self.anf_coefficients)

    @property
    def fourier_coefficients(self) -> tuple[Fraction, ...]:
        """Return normalized Walsh coefficients of (-1)^f, indexed by subsets."""
        values = [1 - 2 * value for value in self.truth_table]
        width = 1
        while width < len(values):
            for start in range(0, len(values), 2 * width):
                for i in range(start, start + width):
                    a, b = values[i], values[i + width]
                    values[i], values[i + width] = a + b, a - b
            width *= 2
        return tuple(Fraction(value, len(values)) for value in values)

    @property
    def fourier_l1(self) -> Fraction:
        """Return the exact Fourier L1 norm under the sign convention."""
        return sum(map(abs, self.fourier_coefficients), Fraction(0))

    @property
    def fourier_l2_squared(self) -> Fraction:
        """Return squared Fourier L2 norm (one by Parseval)."""
        return sum((c * c for c in self.fourier_coefficients), Fraction(0))

    @property
    def fourier_l2(self) -> Fraction:
        """Return Fourier L2 norm, exactly one for a Boolean sign function."""
        return Fraction(1)

    @property
    def decision_tree_depth(self) -> int:
        """Find minimum worst-case deterministic decision-tree depth exactly."""
        @lru_cache(maxsize=None)
        def solve(assignments: tuple[int, ...], remaining: tuple[int, ...]) -> int:
            if len({self(i) for i in assignments}) == 1:
                return 0
            return 1 + min(
                max(solve(tuple(i for i in assignments if ((i >> j) & 1) == b), tuple(k for k in remaining if k != j)) for b in (0, 1))
                for j in remaining
            )
        return solve(tuple(range(1 << self.n)), tuple(range(self.n)))

    @property
    def certificate_complexity(self) -> int:
        """Find maximum, over inputs, of the smallest value-forcing certificate."""
        def certificate_size(assignment: int) -> int:
            for size in range(self.n + 1):
                for indices in combinations(range(self.n), size):
                    mask = sum(1 << j for j in indices)
                    if all(self(i) == self(assignment) for i in range(1 << self.n) if (i & mask) == (assignment & mask)):
                        return size
            raise AssertionError("a full assignment is always a certificate")
        return max(certificate_size(i) for i in range(1 << self.n))

    def to_expression(self) -> Boolean:
        """Return a human-readable SymPy sum-of-products expression."""
        from sympy import Symbol, false, true
        from sympy.logic.boolalg import SOPform
        if self.n == 0:
            return true if self.bits else false
        variables = [Symbol(f"x{j}") for j in range(self.n)]
        minterms = [[(i >> j) & 1 for j in range(self.n)] for i in range(1 << self.n) if self(i)]
        return SOPform(variables, minterms)


def enumerate_functions(n: int) -> Iterator[BooleanFunction]:
    """Enumerate all functions at n <= 4; reject infeasible n=5 enumeration."""
    if type(n) is not int or not 0 <= n <= 4:
        raise ValueError("exhaustive function enumeration is limited to 0 <= n <= 4")
    return (BooleanFunction(n, bits) for bits in range(1 << (1 << n)))
