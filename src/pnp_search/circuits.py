"""Finite Boolean circuits represented by validated topologically ordered gates."""

from dataclasses import dataclass

from .boolean import BooleanFunction


@dataclass(frozen=True)
class Gate:
    """A gate whose inputs refer to primary variables or earlier gates."""

    operation: str
    inputs: tuple[int, ...]

    def __post_init__(self) -> None:
        """Freeze any supplied iterable to prevent later reference mutations."""
        object.__setattr__(self, "inputs", tuple(self.inputs))


@dataclass(frozen=True)
class BooleanCircuit:
    """A circuit with inputs numbered 0..n-1 and gate k numbered n+k.

    Supported basis is AND/OR/XOR/NOT plus zero-input constants ZERO/ONE.
    Size counts every listed gate, including constants and unused gates.
    This representation alone does not establish minimum circuit size.
    """

    n: int
    gates: tuple[Gate, ...]
    output: int

    def __post_init__(self) -> None:
        """Validate arities and reject cycles or out-of-range references."""
        BooleanFunction(self.n, 0)
        object.__setattr__(self, "gates", tuple(self.gates))
        arities = {"AND": 2, "OR": 2, "XOR": 2, "NOT": 1, "ZERO": 0, "ONE": 0}
        for index, gate in enumerate(self.gates):
            if gate.operation not in arities or len(gate.inputs) != arities[gate.operation]:
                raise ValueError("unsupported operation or incorrect gate arity")
            if any(type(i) is not int or not 0 <= i < self.n + index for i in gate.inputs):
                raise ValueError("gate inputs must reference primary inputs or earlier gates")
        if type(self.output) is not int or not 0 <= self.output < self.n + len(self.gates):
            raise ValueError("circuit output out of range")

    @property
    def size(self) -> int:
        """Return listed gate count, without any minimality claim."""
        return len(self.gates)

    def to_function(self) -> BooleanFunction:
        """Evaluate each gate pointwise to obtain the exact truth table."""
        values = [BooleanFunction.variable(self.n, j) for j in range(self.n)]
        for gate in self.gates:
            arguments = [values[j] for j in gate.inputs]
            if gate.operation == "AND":
                value = arguments[0] & arguments[1]
            elif gate.operation == "OR":
                value = arguments[0] | arguments[1]
            elif gate.operation == "XOR":
                value = arguments[0] ^ arguments[1]
            elif gate.operation == "NOT":
                value = ~arguments[0]
            else:
                value = BooleanFunction.constant(self.n, gate.operation == "ONE")
            values.append(value)
        return values[self.output]
