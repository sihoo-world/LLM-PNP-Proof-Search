"""Kernel-check one trusted Boolean template without executing model-written Lean."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from pnp_search.models import CandidateLemma, CandidateStatus, UniversalBinaryOperationBound, VerificationResult

CANONICAL_FORMAL_STATEMENT = "∀ a b : Bool, (a && b) = (b && a)"
CANONICAL_STATEMENT = CANONICAL_FORMAL_STATEMENT
CANONICAL_NATURAL_STATEMENT = "For all Boolean values a and b, a AND b equals b AND a."
THEOREM_NAME = "PNPResearchGenerated.bool_and_comm"
AXIOM_MARKER = f"'{THEOREM_NAME}' does not depend on any axioms"
TRUSTED_SOURCE = '''namespace PNPResearchGenerated

theorem bool_and_comm (a b : Bool) : (a && b) = (b && a) := by
  cases a <;> cases b <;> rfl

end PNPResearchGenerated

#print axioms PNPResearchGenerated.bool_and_comm
'''


class LeanVerifier:
    """Compile a fixed template; arbitrary mathematical prose is not accepted.

    The exact natural and formal statements must match the template. Additional
    assumptions, definitions, or claimed implications require separate review.
    Source and process evidence are retained in unique artifact directories.
    """

    def __init__(
        self,
        lake_path: str | Path | None = None,
        output_dir: str | Path | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        """Select trusted local tooling and a bounded compiler invocation."""
        if timeout_seconds <= 0:
            raise ValueError("Lean timeout must be positive")
        self.repository = Path(__file__).resolve().parents[3]
        self.project_dir = self.repository / "lean"
        self.output_dir = Path(output_dir) if output_dir is not None else self.project_dir / ".lake" / "checks"
        self.timeout_seconds = timeout_seconds
        self.lake_path = str(lake_path) if lake_path is not None else self.discover_lake()

    def discover_lake(self) -> str | None:
        """Prefer the locally pinned portable installation, then PATH."""
        portable = self.repository / ".tools" / "lean-4.24.0-windows" / "bin" / "lake.exe"
        return str(portable) if portable.is_file() else shutil.which("lake")

    def verify(self, candidate: CandidateLemma | UniversalBinaryOperationBound) -> VerificationResult:
        """Return formal evidence only for the complete admitted template claim."""
        started = time.perf_counter()

        def finish(status: CandidateStatus, **kwargs: object) -> VerificationResult:
            result = VerificationResult(
                status=status,
                verification_method="lean",
                duration_seconds=time.perf_counter() - started,
                formalization_review_required=True,
                **kwargs,
            )
            if isinstance(candidate, CandidateLemma) and candidate.status != CandidateStatus.parse_failed:
                candidate.apply_verification(result)
            return result

        if (not isinstance(candidate, CandidateLemma)
                or candidate.status == CandidateStatus.parse_failed
                or not self._supported(candidate)):
            return finish(
                CandidateStatus.unsupported,
                notes=["Only the exact canonical Boolean AND commutativity statements and template are supported; no bound or additional claims."],
            )
        if not self.lake_path:
            return finish(CandidateStatus.unknown, error="Lean Lake executable is unavailable")
        if not (self.project_dir / "lakefile.core.toml").is_file():
            return finish(CandidateStatus.unknown, error="Trusted core Lake configuration is missing")

        evidence: dict[str, object] = {
            "theorem": THEOREM_NAME,
            "formal_statement": CANONICAL_STATEMENT,
            "source_sha256": hashlib.sha256(TRUSTED_SOURCE.encode("utf-8")).hexdigest(),
            "formalization_review_required": True,
            "mathlib_imported": False,
        }
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            directory = Path(tempfile.mkdtemp(prefix="lean-check-", dir=self.output_dir)).resolve()
            source = directory / "Candidate.lean"
            source.write_text(TRUSTED_SOURCE, encoding="utf-8", newline="\n")
            evidence["source_path"] = str(source)
            version = subprocess.run(
                [self.lake_path, "--version"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=self.timeout_seconds,
                cwd=self.project_dir, check=False,
            )
            evidence["tool_version"] = version.stdout.strip()
            evidence["tool_version_returncode"] = version.returncode
            command = [self.lake_path, "-f", "lakefile.core.toml", "env", "lean", str(source)]
            evidence["command"] = command
            completed = subprocess.run(
                command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=self.timeout_seconds, cwd=self.project_dir, check=False,
            )
            evidence.update(returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)
            combined = completed.stdout + completed.stderr
            passed = (
                version.returncode == 0 and completed.returncode == 0
                and AXIOM_MARKER in completed.stdout
                and "sorryAx" not in combined and "declaration uses 'sorry'" not in combined
            )
            evidence_path = directory / "evidence.json"
            evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
            return finish(
                CandidateStatus.formally_verified if passed else CandidateStatus.unknown,
                complete=passed,
                notes=[json.dumps(evidence, ensure_ascii=False), f"Evidence artifact: {evidence_path}",
                       "Only the canonical Boolean identity is checked; this is an established fact, not a circuit lower bound or novelty result."],
                error=None if passed else "Lean failed or the expected theorem's axiom-free audit was absent",
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            evidence["error"] = str(exc)
            if isinstance(exc, subprocess.TimeoutExpired):
                evidence["timeout_seconds"] = self.timeout_seconds
                for name in ("stdout", "stderr"):
                    output = getattr(exc, name)
                    evidence[name] = output.decode("utf-8", errors="replace") if isinstance(output, bytes) else output
            if "source_path" in evidence:
                try:
                    (Path(str(evidence["source_path"])).parent / "evidence.json").write_text(
                        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8",
                    )
                except OSError:
                    pass  # The structured result still preserves failure evidence.
            return finish(CandidateStatus.unknown, error=str(exc), notes=[json.dumps(evidence, ensure_ascii=False)])

    @staticmethod
    def _supported(candidate: CandidateLemma) -> bool:
        """Require exact alignment instead of claiming to understand arbitrary prose."""
        return (
            candidate.lean_template == "bool_and_commutative"
            and candidate.formalized_statement == CANONICAL_STATEMENT
            and candidate.natural_language_statement == CANONICAL_NATURAL_STATEMENT
            and candidate.bound is None
            and not candidate.assumptions and not candidate.definitions
            and not candidate.claimed_implication
        )
