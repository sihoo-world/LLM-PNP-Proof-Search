"""Circuit evaluation and structural validation."""

import pytest

from pnp_search.boolean import BooleanFunction
from pnp_search.circuits import BooleanCircuit, Gate


def test_circuit_evaluation() -> None:
    """A shared DAG evaluates in the documented gate-index convention."""
    circuit = BooleanCircuit(2, (Gate("AND", (0, 1)), Gate("NOT", (2,))), 3)
    assert circuit.to_function() == ~(BooleanFunction.variable(2, 0) & BooleanFunction.variable(2, 1))
    assert circuit.size == 2
    assert BooleanCircuit(0, (Gate("ONE", ()),), 0).to_function().bits == 1


@pytest.mark.parametrize("gate", [Gate("AND", (0,)), Gate("NOT", (2,)), Gate("EXEC", ())])
def test_circuit_invalid_gate(gate: Gate) -> None:
    """Bad arities and future references are rejected before evaluation."""
    with pytest.raises(ValueError):
        BooleanCircuit(2, (gate,), 2)
