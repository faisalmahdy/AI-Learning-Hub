#!/usr/bin/env python3
"""Require a quorum before trusting a vote -- 100% of the two who answered is not consensus.

A governed system asks a panel to approve a consequential action -- promote an agent, ship a
change, execute an irreversible step -- and acts on the vote. The tempting rule is to go with
the majority of whoever answered. That rule breaks the moment some voters are slow or down:
if three of five time out and the two who replied both say yes, the majority-of-responders
rule reports 100% approval and acts, on the word of two voters out of five. A decision made by
a non-representative minority is not consensus; it is a coincidence of who happened to be
reachable.

A quorum rule fixes it: before counting the vote at all, require that enough voters actually
responded. Below the quorum, the round is inconclusive -- withhold the action and escalate,
rather than let two votes stand in for five. Above it, count the majority as usual. This
builds both rules and runs them on a degraded round (only two of five reply) and a healthy
round (four reply): the naive rule approves the degraded round on two votes while the quorum
rule withholds it, and both approve the well-supported healthy round. The quorum blocks
exactly the under-supported decision and nothing else.

  --rounds    each voting round, who responded, and the naive vs quorum decision
  --tally     the approval math: responders, yes/no, and why each rule decided as it did
  --check     naive approves the degraded round; the quorum rule withholds it; both pass the healthy one

The rounds and the quorum size are the fixture; every count and decision is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "rounds.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- counting a round

def responders(votes):
    """Voters who actually replied (not 'timeout')."""
    return [v for v in votes if v != "timeout"]


def tally(votes):
    r = responders(votes)
    return {"total": len(votes), "responded": len(r),
            "yes": r.count("yes"), "no": r.count("no")}


# ------------------------------------------------------------- the two decision rules

def decide_naive(votes):
    """The bug: majority of whoever answered, ignoring how many stayed silent."""
    t = tally(votes)
    if t["responded"] == 0:
        return "withhold"
    return "approve" if t["yes"] > t["no"] else "withhold"


def decide_quorum(votes, quorum):
    """The fix: require `quorum` responses first; below it the round is inconclusive."""
    t = tally(votes)
    if t["responded"] < quorum:
        return "no-quorum"              # not enough voters to trust the result -- escalate
    return "approve" if t["yes"] > t["no"] else "withhold"


def acts(decision):
    """Only a clean 'approve' authorizes the action; withhold and no-quorum do not."""
    return decision == "approve"


# ----------------------------------------------------------------- printing

def rounds_view(data):
    q = data["quorum"]
    print("ROUNDS — %d voters per round, quorum %d required to trust the vote" % (data["voters"], q))
    print("-" * 68)
    print("  round        votes                          naive     quorum")
    for rd in data["rounds"]:
        v = rd["votes"]
        print("  %-12s %-30s %-9s %s"
              % (rd["name"], ",".join(v), decide_naive(v), decide_quorum(v, q)))
    print("-" * 68)
    print("  naive acts on the majority of responders; the quorum rule needs enough responders first.")


def tally_view(data):
    q = data["quorum"]
    print("TALLY — the approval math behind each decision")
    print("-" * 68)
    for rd in data["rounds"]:
        v = rd["votes"]
        t = tally(v)
        rate = (t["yes"] / t["responded"]) if t["responded"] else 0.0
        print("  %-12s responded %d/%d  yes=%d no=%d  approval-of-responders=%.0f%%"
              % (rd["name"], t["responded"], t["total"], t["yes"], t["no"], 100 * rate))
        print("     naive=%s  quorum=%s" % (decide_naive(v), decide_quorum(v, q)))
    print("-" * 68)
    print("  100% approval of 2 responders is not the same evidence as 60% of 5.")


def check(data):
    print("SELF-TEST — naive approves the degraded round; quorum withholds it; both pass the healthy one")
    print("-" * 68)
    q = data["quorum"]
    by = {rd["name"]: rd["votes"] for rd in data["rounds"]}
    degraded, healthy = by["degraded"], by["healthy"]

    naive_acts_degraded = acts(decide_naive(degraded))
    print("  naive ACTS on the degraded round (2 of 5 replied) = %s (%s)"
          % (naive_acts_degraded, decide_naive(degraded)))

    quorum_blocks_degraded = not acts(decide_quorum(degraded, q))
    print("  the quorum rule does NOT act on the degraded round = %s (%s)"
          % (quorum_blocks_degraded, decide_quorum(degraded, q)))

    both_act_healthy = acts(decide_naive(healthy)) and acts(decide_quorum(healthy, q))
    print("  both rules act on the healthy round (4 of 5 replied) = %s (naive=%s, quorum=%s)"
          % (both_act_healthy, decide_naive(healthy), decide_quorum(healthy, q)))

    # the quorum rule withholds exactly when too few responded
    quorum_gates_on_responses = all(
        (decide_quorum(rd["votes"], q) == "no-quorum") == (tally(rd["votes"])["responded"] < q)
        for rd in data["rounds"])
    print("  the quorum rule returns no-quorum exactly when responders < quorum = %s" % quorum_gates_on_responses)

    ok = naive_acts_degraded and quorum_blocks_degraded and both_act_healthy and quorum_gates_on_responses
    print("-" * 68)
    print("SELF-TEST %s  naive_acts_degraded=%s  quorum_blocks=%s  both_act_healthy=%s  gates_on_responses=%s"
          % ("PASS" if ok else "FAIL", naive_acts_degraded, quorum_blocks_degraded,
             both_act_healthy, quorum_gates_on_responses))
    return ok


def main():
    p = argparse.ArgumentParser(description="Require a quorum before trusting a vote.")
    p.add_argument("--rounds", action="store_true")
    p.add_argument("--tally", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("voters=%d  quorum=%d  rounds=%d  file=%s  (the rounds are a fixture)"
          % (data["voters"], data["quorum"], len(data["rounds"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.rounds:
        rounds_view(data)
    elif args.tally:
        tally_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
