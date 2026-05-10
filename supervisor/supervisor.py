#!/usr/bin/env python3
"""
supervisor.py — standalone AI-stack supervisor CLI
~/.aistack/supervisor/supervisor.py

Usage:
    python3 supervisor.py status              # open claims + tier distribution
    python3 supervisor.py sweep              # re-evaluate all open claims
    python3 supervisor.py verify --target path/to/file.py
    python3 supervisor.py blocked            # list blocking claims
    python3 supervisor.py add --text "claim text" [--file path] [--type type]

Zero sagent dependencies.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure this dir is on sys.path so sibling modules import cleanly
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import ledger
import collector
import grader
import llm


# ── ANSI colours (degraded gracefully if not a TTY) ──────────────────────────
def _c(code: str, text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"

RED    = lambda t: _c("31", t)
GREEN  = lambda t: _c("32", t)
YELLOW = lambda t: _c("33", t)
CYAN   = lambda t: _c("36", t)
BOLD   = lambda t: _c("1", t)


# ── helpers ───────────────────────────────────────────────────────────────────
def _verdict_colour(verdict: str) -> str:
    return {"pass": GREEN(verdict), "fail": RED(verdict), "partial": YELLOW(verdict)}.get(verdict, verdict)


def _tier_badge(tier: int) -> str:
    return CYAN(f"L{tier}") if tier else RED("L?")


def _print_claim(c: dict, verbose: bool = False) -> None:
    status = c.get("status", "open")
    ev = {}
    if c.get("evidence_json"):
        try:
            ev = json.loads(c["evidence_json"])
        except (json.JSONDecodeError, TypeError):
            ev = {}
    verdict = ev.get("verdict", status)
    tier = c.get("tier", 0)
    print(
        f"  [{c['id']:>4}] {_tier_badge(tier)} {_verdict_colour(verdict):>10}  "
        f"{c.get('claim_type', 'generic'):<18} {c['claim_text'][:80]}"
    )
    if c.get("file_path"):
        print(f"         file: {c['file_path']}")
    if verbose and ev.get("gaps"):
        for gap in ev["gaps"][:3]:
            print(f"         gap: {RED(gap)}")


# ── subcommands ───────────────────────────────────────────────────────────────
def cmd_status(args: argparse.Namespace) -> int:
    claims = ledger.get_open_claims()
    blocked = ledger.get_blocked_claims()
    counts = ledger.tier_counts()
    llm_tier = llm.available_tier()

    print(BOLD("── Supervisor Status ────────────────────────────────"))
    print(f"  DB       : {ledger.DB_PATH}")
    print(f"  LLM tier : {CYAN(llm_tier)}")
    print(f"  Open     : {len(claims)}")
    print(f"  Blocked  : {len(blocked)}")
    if counts:
        dist = "  ".join(f"L{k}={v}" for k, v in sorted(counts.items()))
        print(f"  Tiers    : {dist}")
    print()

    if claims:
        print(BOLD("Open claims:"))
        for c in claims[:20]:
            _print_claim(c)
    else:
        print(GREEN("  No open claims."))

    if blocked:
        print()
        print(BOLD("Blocked claims:"))
        for c in blocked[:10]:
            _print_claim(c, verbose=True)

    return 0


def cmd_sweep(args: argparse.Namespace) -> int:
    claims = ledger.get_open_claims()
    if not claims:
        print("Nothing to sweep.")
        return 0

    print(f"Sweeping {len(claims)} open claim(s)…")
    graded = 0
    for c in claims:
        file_path = c.get("file_path")
        evidence: list[dict] = []

        if file_path:
            evidence = collector.run_all_for_file(file_path)

        # Optional LLM eval for context
        llm_summary = None
        if args.llm:
            prompt = (
                f"Claim: {c['claim_text']}\n"
                f"Evidence: {json.dumps(evidence)}\n"
                "Rate this claim on L1-L5 and note any gaps. Be terse."
            )
            llm_summary = llm.chat(prompt, task="eval_judge")

        result = grader.grade(c["claim_text"], evidence, llm_summary=llm_summary)
        ledger.update_verdict(c["id"], result["tier"], result["verdict"], result["passed"], result["gaps"])

        verdict_str = result["verdict"]
        print(f"  [{c['id']:>4}] L{result['tier']} {_verdict_colour(verdict_str)}  {c['claim_text'][:60]}")
        graded += 1

    print(f"\nSwept {graded} claim(s).")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    target = args.target
    if not target:
        print("--target required", file=sys.stderr)
        return 1

    claims = ledger.get_by_file(target)
    if not claims:
        print(f"No claims recorded for: {target}")
        # Still run collectors as a one-off check
        evidence = collector.run_all_for_file(target)
        result = grader.grade(f"file check: {target}", evidence)
        print(f"On-the-fly check: L{result['tier']} {_verdict_colour(result['verdict'])}")
        for ev in evidence:
            icon = GREEN("✓") if ev.get("pass") else RED("✗")
            print(f"  {icon} {ev['collector']}: {ev['detail']}")
        return 0

    print(f"Verifying {len(claims)} claim(s) for: {target}")
    evidence = collector.run_all_for_file(target)
    for c in claims:
        result = grader.grade(c["claim_text"], evidence)
        ledger.update_verdict(c["id"], result["tier"], result["verdict"], result["passed"], result["gaps"])
        print(f"  [{c['id']:>4}] L{result['tier']} {_verdict_colour(result['verdict'])}  {c['claim_text'][:70]}")
        for gap in result["gaps"][:2]:
            print(f"         {RED('gap:')} {gap}")
    return 0


def cmd_blocked(args: argparse.Namespace) -> int:
    claims = ledger.get_blocked_claims()
    if not claims:
        print(GREEN("No blocked claims."))
        return 0
    print(BOLD(f"{len(claims)} blocked claim(s):"))
    for c in claims:
        _print_claim(c, verbose=True)
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    if not args.text:
        print("--text required", file=sys.stderr)
        return 1
    cid = ledger.add_claim(
        claim_text=args.text,
        claim_type=args.type or "generic",
        file_path=args.file,
    )
    print(f"Claim #{cid} added.")
    return 0


# ── main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        prog="supervisor",
        description="Standalone AI-stack verification supervisor",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Print open claims and tier distribution")

    sweep_p = sub.add_parser("sweep", help="Re-evaluate all open claims")
    sweep_p.add_argument("--llm", action="store_true", help="Use LLM for eval summaries")

    verify_p = sub.add_parser("verify", help="Verify claims for a specific file")
    verify_p.add_argument("--target", required=True, help="File path to verify")

    sub.add_parser("blocked", help="List blocking claims")

    add_p = sub.add_parser("add", help="Add a claim manually")
    add_p.add_argument("--text", required=True, help="Claim text")
    add_p.add_argument("--file", help="Associated file path")
    add_p.add_argument("--type", default="generic", help="Claim type")

    args = parser.parse_args()

    dispatch = {
        "status":  cmd_status,
        "sweep":   cmd_sweep,
        "verify":  cmd_verify,
        "blocked": cmd_blocked,
        "add":     cmd_add,
    }

    if args.command not in dispatch:
        parser.print_help()
        return 0

    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
