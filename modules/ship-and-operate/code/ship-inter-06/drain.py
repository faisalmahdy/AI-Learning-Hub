#!/usr/bin/env python3
"""Graceful shutdown drains in-flight requests -- a hard stop drops them all.

Deploys and scale-downs send a shutdown signal to a service that is still working: it has
in-flight requests mid-process and new ones still arriving. What it does next decides
whether those users see a result or an error. A graceful shutdown DRAINS: it stops
accepting new requests (rejecting them cleanly, so the client retries another instance),
lets the in-flight requests finish, and only then exits. A hard shutdown exits immediately
and every in-flight request is dropped -- a connection reset, lost work, an error the user
did nothing to cause.

Draining is bounded by a deadline so shutdown cannot hang on a slow request forever: an
in-flight request still running past the drain deadline is force-terminated. So graceful
shutdown drops only the stragglers that exceed the deadline, while a hard stop drops
everything in flight. This measures both against the in-flight set.

  --drain       graceful: stop new, finish in-flight to the deadline, force only stragglers
  --hard        the bug: exit now -- every in-flight request dropped
  --check       drain completes the in-flight that fit the deadline; hard drops them all

Deterministic: ticks_remaining is the fixture, not a clock. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "shutdown.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the two shutdowns

def graceful_shutdown(data):
    """Stop new requests; finish in-flight up to the drain deadline; force-drop stragglers.

    Returns (completed, force_dropped, new_rejected).
    """
    deadline = data["drain_deadline"]
    completed, force_dropped = [], []
    for req in data["in_flight"]:
        if req["ticks_remaining"] <= deadline:   # finishes within the drain window
            completed.append(req["id"])
        else:                                    # still running at the deadline -> terminated
            force_dropped.append(req["id"])
    new_rejected = data["new_requests"]          # cleanly rejected -> client retries elsewhere
    return completed, force_dropped, new_rejected


def hard_shutdown(data):
    """The bug: exit immediately. Every in-flight request is dropped."""
    dropped = [req["id"] for req in data["in_flight"]]
    new_dropped = data["new_requests"]           # dropped mid-connection, not cleanly rejected
    return dropped, new_dropped


# ----------------------------------------------------------------- printing

def drain_view(data):
    completed, forced, rejected = graceful_shutdown(data)
    print("DRAIN — graceful shutdown (drain deadline = %d ticks)" % data["drain_deadline"])
    print("-" * 66)
    print("  completed (finished before exit): %s" % completed)
    print("  force-dropped (past the deadline): %s" % forced)
    print("  new requests cleanly rejected:     %d  (client retries another instance)" % rejected)
    print("-" * 66)
    print("  in-flight work finishes; only a straggler past the deadline is cut, and it is bounded.")


def hard_view(data):
    dropped, new_dropped = hard_shutdown(data)
    print("HARD — the bug: exit immediately")
    print("-" * 66)
    print("  in-flight DROPPED (connection reset): %s" % dropped)
    print("  new requests dropped mid-connection:  %d" % new_dropped)
    print("-" * 66)
    print("  every in-flight request is lost -- users see errors they did nothing to cause.")


def check(data):
    print("SELF-TEST — drain completes what fits the deadline; hard drops everything in flight")
    print("-" * 66)
    in_flight_ids = [r["id"] for r in data["in_flight"]]
    deadline = data["drain_deadline"]

    completed, forced, rejected = graceful_shutdown(data)

    should_complete = [r["id"] for r in data["in_flight"] if r["ticks_remaining"] <= deadline]
    drain_completes = completed == should_complete and len(completed) > 0
    print("  drain completes the in-flight within the deadline = %s (%s)" % (drain_completes, completed))

    only_stragglers_dropped = all(
        next(r for r in data["in_flight"] if r["id"] == i)["ticks_remaining"] > deadline for i in forced)
    print("  drain force-drops only stragglers past the deadline = %s (%s)" % (only_stragglers_dropped, forced))

    drain_bounded = len(forced) < len(in_flight_ids)
    print("  drain is bounded but does not drop everything = %s (%d of %d dropped)"
          % (drain_bounded, len(forced), len(in_flight_ids)))

    dropped, _ = hard_shutdown(data)
    hard_drops_all = set(dropped) == set(in_flight_ids)
    print("  hard shutdown drops ALL in-flight requests = %s (%d)" % (hard_drops_all, len(dropped)))

    drain_saves_more = len(completed) > len(in_flight_ids) - len(dropped)
    print("  graceful shutdown saves work a hard stop loses = %s (%d completed vs 0)"
          % (drain_saves_more, len(completed)))

    ok = drain_completes and only_stragglers_dropped and drain_bounded and hard_drops_all and drain_saves_more
    print("-" * 66)
    print("SELF-TEST %s  drain_completes=%s  only_stragglers=%s  bounded=%s  hard_drops_all=%s  drain_saves_more=%s"
          % ("PASS" if ok else "FAIL", drain_completes, only_stragglers_dropped, drain_bounded, hard_drops_all, drain_saves_more))
    return ok


def main():
    p = argparse.ArgumentParser(description="Graceful shutdown draining vs a hard stop.")
    p.add_argument("--drain", action="store_true")
    p.add_argument("--hard", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("in_flight=%d  drain_deadline=%d  new_requests=%d  file=%s  (ticks are a fixture)"
          % (len(data["in_flight"]), data["drain_deadline"], data["new_requests"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.drain:
        drain_view(data)
    elif args.hard:
        hard_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
