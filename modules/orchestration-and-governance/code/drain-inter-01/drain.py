"""Drain on shutdown -- stop accepting new work, then let the in-flight requests finish before exiting -- because a hard kill abandons every request in progress, turning almost-complete work into client errors.

A worker in a fleet is stopped all the time: a deploy rolls it, an autoscaler scales it in, an operator restarts it. And at the instant of shutdown the worker is almost never idle -- it is holding requests that are partway through. What happens to those requests is decided entirely by how the shutdown is done.

A hard stop terminates the process immediately. Every in-flight request is abandoned mid-work: the client that was waiting gets an error or a timeout for work that may have been a millisecond from done, and any partial side effects the request had started are left dangling with no completion and no cleanup. The faster and busier the worker, the more requests a hard stop throws away.

A graceful drain does two things, and the order matters. First it stops accepting NEW requests -- it closes the door, so incoming work is rejected at the threshold and the load balancer routes it to a healthy worker. Crucially this is a rejection, not a silent drop: the caller learns immediately and retries elsewhere, rather than having its request accepted here and then killed. Second, with no new work coming in, the worker processes the requests already in flight through to completion, and only then does the process exit.

The distinction between rejected and lost is the whole point. Drain converts what would have been lost in-flight work into zero loss, and converts new arrivals from 'accepted then abandoned' into 'rejected up front so they can go elsewhere'. A hard stop has no rejection step, so everything it was holding is simply lost.

The rule: drain on shutdown -- first stop accepting new requests (rejecting them so they route to a healthy worker), then finish the in-flight requests before the process exits -- because a hard kill abandons all in-flight work as client-visible errors, while draining loses none.

On this fixture the worker holds three in-flight requests and two new ones arrive during shutdown. A hard stop loses all three in-flight (and drops the new ones too); a drain completes all three in-flight, loses none, and rejects the two new arrivals so they retry elsewhere. This computes both.

  --outcome   under a hard stop vs a graceful drain: what completes, what is lost, what is rejected
  --tally     the loss counts side by side -- the number of abandoned requests each strategy leaves
  --check     a hard stop abandons the in-flight requests; draining finishes them and rejects new arrivals, losing none

inflight and new_arrivals are the fixture; the completed, lost, and rejected sets under each strategy are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "drain.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def hard_stop(inflight, new_arrivals):
    """Terminate immediately: in-flight work is abandoned, and any new arrivals taken on are dropped too."""
    return {"completed": [], "lost": list(inflight) + list(new_arrivals), "rejected": []}


def drain(inflight, new_arrivals):
    """Stop accepting new work (reject it), then finish the in-flight requests before exiting."""
    return {"completed": list(inflight), "lost": [], "rejected": list(new_arrivals)}


# ----------------------------------------------------------------- printing

def outcome_view(data):
    inflight, new = data["inflight"], data["new_arrivals"]
    print("OUTCOME — in-flight=%s  new arrivals during shutdown=%s" % (inflight, new))
    print("-" * 60)
    for name, fn in (("hard stop", hard_stop), ("drain", drain)):
        r = fn(inflight, new)
        print("  %-10s completed=%s  lost=%s  rejected=%s"
              % (name, r["completed"], r["lost"], r["rejected"]))
    print("-" * 60)
    print("  drain turns lost in-flight work into completed, and new work into a clean rejection")


def tally_view(data):
    inflight, new = data["inflight"], data["new_arrivals"]
    print("TALLY — abandoned (lost) requests by shutdown strategy")
    print("-" * 44)
    for name, fn in (("hard stop", hard_stop), ("drain", drain)):
        r = fn(inflight, new)
        print("  %-10s lost = %d   (completed %d, rejected %d)"
              % (name, len(r["lost"]), len(r["completed"]), len(r["rejected"])))
    print("-" * 44)
    print("  a rejected request is not a lost one -- the caller retries on a healthy worker")


def check(data):
    print("SELF-TEST — a hard stop abandons the in-flight requests; draining finishes them and rejects new arrivals, losing none")
    print("-" * 120)
    inflight, new = data["inflight"], data["new_arrivals"]
    h = hard_stop(inflight, new)
    d = drain(inflight, new)

    hard_loses_inflight = all(r in h["lost"] for r in inflight) and len(inflight) > 0
    print("  hard stop: every in-flight request is lost = %s (%s)" % (hard_loses_inflight, h["lost"]))

    hard_completes_nothing = h["completed"] == []
    print("  hard stop: nothing is completed after the signal = %s" % hard_completes_nothing)

    drain_completes_inflight = d["completed"] == list(inflight)
    print("  drain: every in-flight request completes = %s (%s)" % (drain_completes_inflight, d["completed"]))

    drain_loses_nothing = d["lost"] == []
    print("  drain: no request is lost = %s" % drain_loses_nothing)

    drain_rejects_new = d["rejected"] == list(new) and all(n not in d["lost"] for n in new)
    print("  drain: new arrivals are rejected (not accepted-then-lost) = %s (%s)" % (drain_rejects_new, d["rejected"]))

    ok = (hard_loses_inflight and hard_completes_nothing and drain_completes_inflight
          and drain_loses_nothing and drain_rejects_new)
    print("-" * 120)
    print("SELF-TEST %s  hard_loses_inflight=%s  hard_completes_nothing=%s  drain_completes_inflight=%s  drain_loses_nothing=%s  drain_rejects_new=%s"
          % ("PASS" if ok else "FAIL", hard_loses_inflight, hard_completes_nothing,
             drain_completes_inflight, drain_loses_nothing, drain_rejects_new))
    return ok


def main():
    p = argparse.ArgumentParser(description="Graceful drain: drain on shutdown -- first stop accepting new requests (rejecting them so they route to a healthy worker), then finish the in-flight requests before the process exits -- because a hard kill abandons all in-flight work as client-visible errors, while draining loses none.")
    p.add_argument("--outcome", action="store_true")
    p.add_argument("--tally", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("inflight=%d  new_arrivals=%d  file=%s  (the request sets are a fixture)"
          % (len(data["inflight"]), len(data["new_arrivals"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.outcome:
        outcome_view(data)
    elif args.tally:
        tally_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
