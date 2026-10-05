"""Provider-independent candidate generation without executable model output."""

import json
import os
import urllib.request
from typing import Any, Protocol


class LLMBackend(Protocol):
    """Backends return untrusted text, never trusted mathematical facts."""

    name: str

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a candidate from a fully persisted prompt."""
        ...


class MockBackend:
    """Deterministic fixtures exercising both survival and counterexamples."""

    name = "deterministic-mock-v1"

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Emit a known false weight bound or elementary finite-test examples."""
        measure = kwargs.get("measure", "truth_table_weight")
        revision = kwargs.get("revision", False)
        operation = "XOR" if measure == "truth_table_weight" else "AND"
        rhs = "M(f)" if measure == "truth_table_weight" and not revision else "M(f) + M(g)"
        result = {
            "title": f"{measure} under {operation}",
            "domain": "boolean_circuit_complexity",
            "definitions": [f"M is {measure} on Boolean functions of the same arity."],
            "assumptions": [],
            "lemma": f"For all same-arity Boolean f,g, M(f {operation} g) <= {rhs}.",
            "motivation": "Test an operation bound as a possible ingredient; no lower bound follows alone.",
            "proof_sketch": "Candidate only. For sum bounds, analyze the output pointwise or in GF(2).",
            "expected_implication": "No circuit lower bound is established by this local inequality alone.",
            "possible_failure_modes": ["The proposed bound may omit the contribution of g."],
            "bound": {"operation": operation, "measure": measure, "relation": "<=", "rhs": rhs},
        }
        if revision:
            result["revision_analysis"] = {
                "failure_explanation": "XOR can be nonzero where f is zero because of g.",
                "broken_assumption": "The earlier bound implicitly ignored the support of g.",
                "revised_statement": result["lemma"],
                "nontriviality": "The union-of-support bound is elementary; novelty is not claimed.",
                "lower_bound_relevance": "A gate inequality is only an ingredient; no separating measure growth is supplied.",
            }
        return json.dumps(result, ensure_ascii=False)


class HTTPBackend:
    """Optional chat-completions-compatible transport configured only by environment."""

    def __init__(self) -> None:
        """Read credentials at runtime and fail closed on missing configuration."""
        self.key = os.environ.get("PNP_LLM_API_KEY", "")
        self.base_url = os.environ.get("PNP_LLM_BASE_URL", "")
        self.name = os.environ.get("PNP_LLM_MODEL", "")
        if not all((self.key, self.base_url, self.name)):
            raise ValueError("Set PNP_LLM_API_KEY, PNP_LLM_BASE_URL and PNP_LLM_MODEL")
        if not self.base_url.startswith("https://"):
            raise ValueError("HTTP backend requires HTTPS to protect credentials")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Return text; never persist the request headers or authentication secret."""
        payload = json.dumps({"model": self.name, "messages": [{"role": "user", "content": prompt}], "temperature": 0}).encode()
        request = urllib.request.Request(self.base_url.rstrip("/") + "/chat/completions", data=payload,
                                         headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json"})
        # Redirects could send Authorization to another host. Reject all redirects.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            """Prevent authenticated requests from following provider redirects."""

            def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
                return None

        with urllib.request.build_opener(NoRedirect).open(request, timeout=60) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Provider response exceeds 2 MB")
        return str(json.loads(raw)["choices"][0]["message"]["content"])

