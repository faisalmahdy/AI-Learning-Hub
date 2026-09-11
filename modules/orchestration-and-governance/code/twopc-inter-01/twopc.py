"""Two-phase commit makes a distributed transaction atomic -- and blocks when the coordinator dies mid-decision. Know both.

A transaction that touches several independent databases has to be all-or-nothing: either every participant commits or none does, because a half-committed transaction (money debited from one account, never credited to the other) is corruption. But each database can only commit its own part, and any of them can fail at any moment, so you need a protocol that reaches a single agreed outcome across all of them. Two-phase commit (2PC) is the classic answer, and understanding it means understanding exactly one guarantee it provides and exactly one weakness it cannot escape.

The protocol has two phases run by a coordinator. In PREPARE, the coordinator asks every participant 'can you commit?' Each participant does all the work up to the final commit, and if it can, it votes yes and LOCKS its resources, promising it will be able to commit if told to; otherwise it votes no. In COMMIT/ABORT, the coordinator collects the votes and decides: commit only if every vote was yes, abort if any single vote was no -- then it broadcasts the decision and every participant carries it out. That decision rule is the atomicity guarantee: one no forces everyone to abort, including participants that voted yes, so the participants never diverge. All commit or all abort, never a mix.

The weakness is in the gap between the two phases. A participant that has voted yes has locked its resources and promised to commit -- it is now in DOUBT, waiting for the decision, and it cannot resolve on its own: it may not commit (the coordinator might decide abort because someone else voted no) and it may not abort (the coordinator might decide commit). If the coordinator crashes in that window, after the votes are in but before the decision is delivered, every yes-voter is stuck: blocked, holding its locks, unable to make progress until the coordinator recovers and tells it the outcome. This is the blocking problem, and it is fundamental to 2PC -- the price of its atomicity is that a coordinator failure at the wrong moment freezes the participants.

The rule: two-phase commit guarantees atomicity -- a prepare phase where each participant votes and locks, then a decision that commits only if all voted yes and otherwise aborts, applied uniformly -- but it blocks: a participant that has voted yes is in doubt and cannot decide alone, so a coordinator crash after the vote leaves the prepared participants stuck holding locks until it recovers.

On this fixture, when all three participants vote yes the decision is commit; when one votes no the decision is abort for everyone, including the yes-voters. And if the coordinator crashes after the votes but before the decision, the participants that voted yes are in doubt and blocked. This computes both.

  --decide    each scenario's votes and the atomic decision (commit only if unanimous), applied to every participant
  --block     the coordinator-crash case: which participants are in doubt and blocked, holding their locks
  --check     a single no forces a uniform abort (atomicity); a coordinator crash after the vote blocks the yes-voters

scenarios are the fixture; the decision, its uniformity, and the in-doubt set on crash are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "twopc.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def decide(votes):
    """Commit only if every participant voted yes; otherwise abort."""
    return "commit" if all(v == "yes" for v in votes.values()) else "abort"


def outcome_per_participant(votes):
    """The decision applied uniformly to every participant."""
    d = decide(votes)
    return {p: d for p in votes}


def in_doubt_on_crash(votes):
    """If the coordinator crashes after votes but before the decision, the yes-voters are in doubt (blocked)."""
    return [p for p, v in votes.items() if v == "yes"]


# ----------------------------------------------------------------- printing

def decide_view(data):
    print("DECIDE — votes and the atomic decision per scenario")
    print("-" * 60)
    for name, sc in data["scenarios"].items():
        votes = sc["votes"]
        d = decide(votes)
        print("  %-14s votes=%s -> %s" % (name, votes, d.upper()))
        print("                 per participant: %s" % outcome_per_participant(votes))
    print("-" * 60)
    print("  commit requires ALL yes; a single no aborts everyone (atomicity)")


def block_view(data):
    print("BLOCK — coordinator crashes after the vote, before the decision")
    print("-" * 64)
    votes = data["scenarios"]["all_prepared"]["votes"]
    doubt = in_doubt_on_crash(votes)
    print("  all participants voted: %s" % votes)
    print("  coordinator crashes before broadcasting the decision")
    print("  in doubt (voted yes, locked, awaiting decision): %s" % doubt)
    print("-" * 64)
    print("  these %d participants are BLOCKED -- they cannot commit or abort alone, and hold their locks" % len(doubt))


def check(data):
    print("SELF-TEST — a single no forces a uniform abort (atomicity); a coordinator crash after the vote blocks the yes-voters")
    print("-" * 120)
    allp = data["scenarios"]["all_prepared"]["votes"]
    onen = data["scenarios"]["one_aborts"]["votes"]

    all_yes_commits = decide(allp) == "commit"
    print("  unanimous yes -> commit = %s (%s)" % (all_yes_commits, decide(allp)))

    any_no_aborts = decide(onen) == "abort"
    print("  any no -> abort = %s (%s, votes %s)" % (any_no_aborts, decide(onen), onen))

    decision_uniform = len(set(outcome_per_participant(onen).values())) == 1
    print("  the decision is uniform across all participants = %s (%s)" % (decision_uniform, outcome_per_participant(onen)))

    yes_voters_overridden = decide(onen) == "abort" and any(v == "yes" for v in onen.values())
    print("  yes-voters are overridden by the single no (all-or-nothing) = %s (A,C voted yes, still abort)" % yes_voters_overridden)

    doubt = in_doubt_on_crash(allp)
    coordinator_crash_blocks = len(doubt) > 0
    print("  a coordinator crash after the vote leaves participants in doubt = %s (%s blocked)" % (coordinator_crash_blocks, doubt))

    all_yes_voters_blocked = set(doubt) == {p for p, v in allp.items() if v == "yes"}
    print("  every yes-voter is blocked holding locks until the coordinator recovers = %s" % all_yes_voters_blocked)

    ok = all_yes_commits and any_no_aborts and decision_uniform and yes_voters_overridden and coordinator_crash_blocks and all_yes_voters_blocked
    print("-" * 120)
    print("SELF-TEST %s  all_yes_commits=%s  any_no_aborts=%s  decision_uniform=%s  yes_voters_overridden=%s  coordinator_crash_blocks=%s  all_yes_voters_blocked=%s"
          % ("PASS" if ok else "FAIL", all_yes_commits, any_no_aborts, decision_uniform, yes_voters_overridden, coordinator_crash_blocks, all_yes_voters_blocked))
    return ok


def main():
    p = argparse.ArgumentParser(description="Two-phase commit: 2PC guarantees atomicity -- a prepare phase where each participant votes and locks, then a decision that commits only if all voted yes and otherwise aborts, applied uniformly -- but it blocks: a participant that has voted yes is in doubt and cannot decide alone, so a coordinator crash after the vote leaves the prepared participants stuck holding locks until it recovers.")
    p.add_argument("--decide", action="store_true")
    p.add_argument("--block", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("scenarios=%s  file=%s  (the participant vote sets are a fixture)"
          % (list(data["scenarios"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.decide:
        decide_view(data)
    elif args.block:
        block_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
