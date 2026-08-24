#!/usr/bin/env python3
"""What should the agent build next? Rank the field's convergence against its own gaps.

Seven agent harnesses were studied in depth (Claude Code, Hermes, OpenClaw,
NanoClaw, Codex, Cursor, OpenCode). The payoff of a survey is not any one harness
-- it is the CONVERGENCE: when systems of totally different shapes independently
land on the same primitive. This reads the distilled convergence table and turns
it into a build queue for Santara, the labs' own agent.

The trap this exists to show: ranking what to build by raw convergence count alone
tells Santara to build the second-most-agreed-on primitive -- an OS sandbox -- which
it already has, and ahead of the one harness that skipped it. Priority is not
"what does the field agree on"; it is "what does the field agree on that WE still lack."

  --table      the convergence table: each primitive, its count, dissent, Santara status
  --priority   the correct build queue: convergence gated on Santara's gaps
  --rawrank    the trap: rank by raw count, ignoring what Santara already has
  --check      counts match the named harnesses; the raw rank builds a have-already; seeds

Stdlib only. No network, no model calls -- the table is a fixture in convergence.json,
distilled from faisalmahdy/agent/docs deep-dives (each row cites its source line).
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TABLE = HERE / "convergence.json"

STATUS_GAP = {"missing": 2, "partial": 1, "have": 0}   # how much room is left to build


def load():
    data = json.loads(TABLE.read_text(encoding="utf-8"))
    return data["harnesses"], data["primitives"]


def rank_key(item):
    """Deterministic order: convergence desc, then gap severity desc, then name."""
    name, p = item
    return (-p["stated_count"], -STATUS_GAP[p["santara"]], name)


# ------------------------------------------------------------------ the queues

def build_priority(prims):
    """CORRECT: only primitives Santara still lacks (missing/partial), ranked by
    convergence. A primitive Santara already HAS is not a thing to build."""
    gap = [(n, p) for n, p in prims.items() if p["santara"] != "have"]
    return [n for n, _ in sorted(gap, key=rank_key)]


def raw_rank(prims):
    """THE BUG: rank every primitive by raw convergence and call the top of the list
    the build queue -- ignoring that Santara already implemented some of them."""
    return [n for n, _ in sorted(prims.items(), key=rank_key)]


# ------------------------------------------------------------------- printing

STATUS = {"missing": "MISSING", "partial": "partial", "have": "HAVE"}


def table(harnesses, prims):
    print("CONVERGENCE TABLE — seven harnesses, five primitives (the studies' own tallies)")
    print("-" * 74)
    for name, p in sorted(prims.items(), key=rank_key):
        dot = "x" * p["stated_count"] + "." * (7 - p["stated_count"])
        diss = ("  dissent: %s" % p["dissent"]) if p["dissent"] else ""
        print("  %-22s x%d/7  [%s]  Santara: %-7s%s"
              % (name, p["stated_count"], dot, STATUS[p["santara"]], diss))
        print("      %-22s %s (%s)" % ("", p["headline"], p["source"]))
    print("-" * 74)
    print("  counts are the deep-dives' peak tallies, cited; a dissenter means the")
    print("  convergence is not unanimous even where the count is high.")


def priority(prims):
    print("BUILD QUEUE — convergence gated on Santara's gaps (the correct ranking)")
    print("-" * 74)
    q = build_priority(prims)
    for i, name in enumerate(q, 1):
        p = prims[name]
        print("  %d. %-22s x%d/7  (Santara: %s)" % (i, name, p["stated_count"], STATUS[p["santara"]]))
    dropped = [n for n, p in prims.items() if p["santara"] == "have"]
    print("-" * 74)
    print("  dropped (already have): %s" % ", ".join(dropped))
    print("  top of the queue is hooks: the field's most-agreed primitive AND a gap.")


def rawrank(prims):
    print("RAW RANK — order by convergence count alone (the trap)")
    print("-" * 74)
    order = raw_rank(prims)
    for i, name in enumerate(order[:3], 1):
        p = prims[name]
        tag = "  <-- Santara already HAS this" if p["santara"] == "have" else ""
        print("  %d. %-22s x%d/7%s" % (i, name, p["stated_count"], tag))
    print("-" * 74)
    print("  #2 is sandbox: build it! -- except Santara already runs a Landlock/seccomp")
    print("  jail, ahead of the one harness (OpenCode) that skipped an OS sandbox. The")
    print("  raw count is 'what does the field do', not 'what do WE still need'.")


def check(harnesses, prims):
    print("SELF-TEST — counts match the named harnesses; the trap builds a have-already")
    print("-" * 74)

    # data integrity: stated_count equals the number of harnesses named, all known.
    counts_ok = True
    known = set(harnesses)
    for name, p in prims.items():
        named = p["confirmed_in"]
        if len(named) != p["stated_count"] or not set(named) <= known:
            counts_ok = False
        if p["dissent"] and p["dissent"] not in known:
            counts_ok = False
    print("  every stated_count equals its named harnesses, all in the roster = %s" % counts_ok)

    # the bug: the raw-rank build queue contains a primitive Santara already HAS.
    raw_top3 = raw_rank(prims)[:3]
    raw_builds_have = any(prims[n]["santara"] == "have" for n in raw_top3)
    have_names = [n for n in raw_top3 if prims[n]["santara"] == "have"]
    print("  raw-rank top 3 = %s" % raw_top3)
    print("  raw rank tells Santara to build something it HAS (%s) = %s"
          % (", ".join(have_names) or "none", raw_builds_have))

    # the fix: the gated queue never contains a have-already, and leads with hooks.
    q = build_priority(prims)
    gated_clean = all(prims[n]["santara"] != "have" for n in q)
    leads_hooks = q[0] == "hooks"
    print("  gated queue = %s" % q)
    print("  gated queue excludes every have-already = %s, leads with hooks = %s"
          % (gated_clean, leads_hooks))

    # determinism.
    det = raw_rank(prims) == raw_rank(dict(reversed(list(prims.items()))))
    print("  rank is independent of dict order (deterministic) = %s" % det)

    ok = counts_ok and raw_builds_have and gated_clean and leads_hooks and det
    print("-" * 74)
    print("SELF-TEST %s  counts=%s  trap_shows=%s  gated_clean=%s  deterministic=%s"
          % ("PASS" if ok else "FAIL", counts_ok, raw_builds_have, gated_clean, det))
    return ok


def main():
    p = argparse.ArgumentParser(description="Rank harness-convergence against Santara's gaps.")
    for flag in ("table", "priority", "rawrank", "check"):
        p.add_argument("--" + flag, action="store_true")
    args = p.parse_args()

    harnesses, prims = load()
    print("harnesses=%d  primitives=%d  file=%s  (table is a sourced fixture)"
          % (len(harnesses), len(prims), TABLE.name))
    print("")

    if args.check:
        return 0 if check(harnesses, prims) else 1
    if args.table:
        table(harnesses, prims)
    elif args.priority:
        priority(prims)
    elif args.rawrank:
        rawrank(prims)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
