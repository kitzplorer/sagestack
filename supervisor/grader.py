"""
grader.py — L1-L5 verdict engine
Determines verification depth and produces a verdict dict.
Zero pip dependencies.
"""
from __future__ import annotations

from typing import Any

# Tier descriptions
TIERS = {
    1: "Declaration  — label exists in source",
    2: "Wiring       — referenced symbol/config exists",
    3: "Behavior     — non-stub implementation confirmed",
    4: "Outcome      — measurable runtime behavior observed",
    5: "Peak Standard— beats named external benchmark",
}

DEFAULT_REQUIRED_TIER = 3


def _score_evidence(evidence: list[dict]) -> tuple[int, list[str], list[str]]:
    """
    Walk evidence list and compute the highest tier fully supported
    plus lists of what passed and what's missing.
    """
    passed = []
    gaps = []
    tier = 0

    # Map collector names → tier they prove
    COLLECTOR_TIER = {
        "file_exists": 1,
        "grep_symbol": 2,
        "grep_dir": 2,
        "function_not_stub": 3,
        "git_log_count": 3,
        "test_pass": 3,
        "playwright": 4,
        "http_probe": 4,
        "benchmark": 5,
    }

    # Track highest confirmed tier
    tier_results: dict[int, list[bool]] = {}
    for ev in evidence:
        collector = ev.get("collector", "unknown")
        ev_tier = COLLECTOR_TIER.get(collector, 2)
        ok = bool(ev.get("pass", False))
        detail = ev.get("detail", "")

        tier_results.setdefault(ev_tier, []).append(ok)
        if ok:
            passed.append(f"[L{ev_tier}] {collector}: {detail}")
        else:
            gaps.append(f"[L{ev_tier}] {collector}: {detail}")

    # Highest tier where ALL results pass
    for t in sorted(tier_results.keys()):
        results = tier_results[t]
        if all(results):
            tier = max(tier, t)
        else:
            # Gap at this tier — stop climbing
            break

    return tier, passed, gaps


def grade(
    claim_text: str,
    evidence: list[dict],
    required_tier: int = DEFAULT_REQUIRED_TIER,
    llm_summary: str | None = None,
) -> dict[str, Any]:
    """
    Grade a claim against evidence.

    Returns:
        {
            "tier": int (1-5, 0 if nothing passed),
            "verdict": "pass" | "fail" | "partial",
            "required_tier": int,
            "evidence": [...],
            "passed": [...],
            "gaps": [...],
            "llm_summary": str | None,
            "tier_label": str,
        }
    """
    tier, passed, gaps = _score_evidence(evidence)

    if tier >= required_tier:
        verdict = "pass"
    elif tier >= 1:
        verdict = "partial"
    else:
        verdict = "fail"

    return {
        "tier": tier,
        "verdict": verdict,
        "required_tier": required_tier,
        "evidence": evidence,
        "passed": passed,
        "gaps": gaps,
        "llm_summary": llm_summary,
        "tier_label": TIERS.get(tier, "Unverified"),
    }


def grade_file_claim(file_path: str, claim_text: str) -> dict[str, Any]:
    """
    Quick grade for a file-existence claim — runs L1 + optional L2 inline.
    Useful for sweep without a full evidence list.
    """
    import collector as col  # relative import within the package dir
    evidence = col.run_all_for_file(file_path)
    return grade(claim_text, evidence)


def summarize_grades(grades: list[dict]) -> dict[str, Any]:
    """Roll up a list of grade results."""
    total = len(grades)
    if total == 0:
        return {"total": 0, "pass": 0, "fail": 0, "partial": 0, "avg_tier": 0.0}
    by_verdict = {"pass": 0, "fail": 0, "partial": 0}
    tier_sum = 0
    for g in grades:
        by_verdict[g.get("verdict", "fail")] = by_verdict.get(g.get("verdict", "fail"), 0) + 1
        tier_sum += g.get("tier", 0)
    return {
        "total": total,
        **by_verdict,
        "avg_tier": round(tier_sum / total, 2),
    }
