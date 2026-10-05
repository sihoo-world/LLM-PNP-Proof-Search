"""Metrics with explicit denominators and duplicate detection, not novelty claims."""

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from pnp_search.models import CandidateLemma, CandidateStatus


def summarize(candidates: list[CandidateLemma]) -> dict[str, Any]:
    """Report final version states; a duplicate is the same executable claim."""
    total = len(candidates)
    counts = Counter(c.status.value for c in candidates)
    revisions = [c for c in candidates if c.parent_candidate_id]
    survivors = {CandidateStatus.empirically_survived, CandidateStatus.formally_verified}
    seen: set[str] = set()
    duplicates_or_known = 0
    for candidate in candidates:
        executable = candidate.bound.model_dump() if candidate.bound else candidate.formalized_statement
        key = json.dumps({"executable": executable, "domain": candidate.domain,
                          "assumptions": candidate.assumptions, "definitions": candidate.definitions},
                         sort_keys=True) if executable is not None else None
        duplicate = key is not None and key in seen
        known = candidate.status == CandidateStatus.known_result or (candidate.classification in {"known_theorem", "rediscovery"} and bool(candidate.classification_evidence))
        duplicates_or_known += int(duplicate or known)
        if key:
            seen.add(key)
    flags = {"likely_relativizing", "possibly_natural", "possible_algebrization_issue"}
    roots = total - len(revisions)
    return {
        "total_candidates": total,
        "status_counts": dict(sorted(counts.items())),
        "parse_success_rate": sum(c.status != CandidateStatus.parse_failed for c in candidates) / total if total else 0,
        "falsification_rate": counts["falsified"] / total if total else 0,
        "empirical_survival_rate": counts["empirically_survived"] / total if total else 0,
        "formal_verification_rate": counts["formally_verified"] / total if total else 0,
        "revision_survival_rate": sum(c.status in survivors for c in revisions) / len(revisions) if revisions else 0,
        "average_revisions": len(revisions) / roots if roots else 0,
        "barrier_flag_rate": sum(bool(flags.intersection(c.barrier_labels)) for c in candidates) / total if total else 0,
        "duplicate_or_known_result_rate": duplicates_or_known / total if total else 0,
        "revision_count": len(revisions), "root_count": roots,
        "duplicate_or_known_count": duplicates_or_known,
        "formal_template_count": sum(c.lean_template is not None for c in candidates),
        "interpretation": "Finite evidence and infrastructure metrics; neither novelty nor a general lower bound is established.",
    }


def export_summary(candidates: list[CandidateLemma], output: Path) -> dict[str, Any]:
    """Export global and matched-group counts in JSON and flat CSV."""
    output.mkdir(parents=True, exist_ok=True)
    summaries = {"all": summarize(candidates)}
    summaries.update({group: summarize([c for c in candidates if c.group == group]) for group in sorted({c.group for c in candidates})})
    (output / "summary.json").write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")
    rows = [{"group": group, **{k: v for k, v in summary.items() if not isinstance(v, dict)}} for group, summary in summaries.items()]
    with (output / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return summaries

