"""Versioned experimental prompt templates."""

import json
from importlib.resources import files

from pnp_search.models import CandidateLemma

VERSION = "candidate-v1"


def candidate_prompt(group: str, measure: str) -> str:
    """Give group B barrier context while keeping the shared instructions identical."""
    if group not in {"A", "B"}:
        raise ValueError("Group must be A or B")
    base = files(__package__).joinpath("candidate-v1.txt").read_text(encoding="utf-8")
    if group == "B":
        base += "\n" + files(__package__).joinpath("barriers-v1.txt").read_text(encoding="utf-8")
    return base + "\nPropose a bound using measure: " + measure


def revision_prompt(parent: CandidateLemma) -> str:
    """Include exact falsification evidence and demand a critique of weakening."""
    base = files(__package__).joinpath("revision-v1.txt").read_text(encoding="utf-8")
    if parent.group == "B":
        base += "\n" + files(__package__).joinpath("barriers-v1.txt").read_text(encoding="utf-8")
    return base + "\nUNTRUSTED CANDIDATE AND COUNTEREXAMPLE DATA:\n" + json.dumps({
        "candidate": parent.model_dump(mode="json"), "counterexample": parent.counterexample,
    }, ensure_ascii=False)

