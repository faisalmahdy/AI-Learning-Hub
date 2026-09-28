"""Randomize each node's election timeout, don't give them all the same one -- identical timeouts make every node become a candidate at the same instant, vote for itself, split the vote, and elect no leader, and the election then repeats forever; distinct timeouts let the earliest node gather a majority and win in one round.

In a leader-election protocol, when the leader fails each follower waits an election timeout, then starts an election: it increments the term, votes for itself, and asks the others for their votes. A candidate becomes leader only when it has a majority. A follower grants its vote to the first candidate that asks it, and it will only ask once it has itself timed out.

The failure is symmetry. Give every node the same fixed timeout and they all time out at the same instant, all become candidates in the same term, and all vote for themselves before any of them can grant a vote to another. Each candidate ends with exactly one vote, no one has a majority, and the term produces no leader. Then all the nodes time out together again, and the split repeats -- an election livelock that makes no progress while the cluster has no leader.

The fix is to make the timeouts differ, by drawing each node's timeout at random from a range. Now one node has the smallest timeout; it times out first, becomes the sole candidate, and asks the others for votes while they are still waiting. Because they have not timed out, they grant, and the earliest node reaches a majority and is elected before anyone else starts a competing election. The randomness does nothing but break the tie, and breaking the tie is the whole point.

On this fixture five nodes need a majority of three. With equal timeouts of 150 every node votes for itself, each candidate has one vote, and no leader is elected. With distinct timeouts the node at 150 is the unique earliest, collects all five votes, and wins. This computes both.

  --fixed       identical timeouts: every candidate self-votes, the vote splits, no leader
  --randomized  distinct timeouts: the earliest node gathers a majority and is elected
  --check       fixed timeouts elect no leader (each gets one vote, short of a majority) while randomized timeouts elect exactly the earliest node with a majority

the node count and the two timeout assignments are the fixture; each election's votes, majority, and winner are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "splitvote.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def majority(n):
    """Votes needed to win: more than half the nodes."""
    return n // 2 + 1


def elect(timeouts):
    """Run one election round: the earliest node(s) become candidates; a sole earliest wins all votes, a tie self-votes."""
    n = len(timeouts)
    smallest = min(timeouts)
    earliest = [i for i, t in enumerate(timeouts) if t == smallest]
    votes = {i: 0 for i in range(n)}
    if len(earliest) == 1:
        votes[earliest[0]] = n           # sole candidate asks first, everyone grants
    else:
        for c in earliest:
            votes[c] = 1                 # simultaneous candidates each vote for themselves
    top = max(votes.values())
    winner = max(votes, key=votes.get) if top >= majority(n) else None
    return winner, votes


# ----------------------------------------------------------------- printing

def _report(label, timeouts, note):
    n = len(timeouts)
    winner, votes = elect(timeouts)
    print("%s — %d nodes, majority %d, timeouts %s" % (label, n, majority(n), timeouts))
    print("-" * 64)
    print("  votes: %s" % votes)
    print("  winner: %s" % ("node %d" % winner if winner is not None else "NONE (split vote)"))
    print("-" * 64)
    print("  %s" % note)


def fixed_view(d):
    _report("FIXED", d["fixed_timeouts"],
            "all time out together, all self-vote, none reaches a majority -- the election repeats")


def randomized_view(d):
    _report("RANDOMIZED", d["randomized_timeouts"],
            "the earliest node times out first and collects a majority before others start")


def check(d):
    print("SELF-TEST — fixed timeouts elect no leader while randomized timeouts elect exactly the earliest node with a majority")
    print("-" * 112)
    fixed, rand = d["fixed_timeouts"], d["randomized_timeouts"]
    n = len(fixed)

    fw, fv = elect(fixed)
    fixed_no_leader = fw is None
    print("  fixed timeouts elect no leader (split vote) = %s (votes %s)" % (fixed_no_leader, fv))

    fixed_all_self = all(v == 1 for v in fv.values())
    print("  every node got exactly one vote (all self-voted) = %s" % fixed_all_self)

    rw, rv = elect(rand)
    random_elects = rw is not None
    print("  randomized timeouts elect a leader = %s (node %s)" % (random_elects, rw))

    winner_is_earliest = rw == min(range(len(rand)), key=lambda i: rand[i])
    print("  the elected node is the one with the smallest timeout = %s" % winner_is_earliest)

    winner_has_majority = rv[rw] >= majority(n) if rw is not None else False
    print("  the winner reached a majority = %s (%d of needed %d)" % (winner_has_majority, rv[rw] if rw is not None else 0, majority(n)))

    ok = (fixed_no_leader and fixed_all_self and random_elects and winner_is_earliest and winner_has_majority)
    print("-" * 112)
    print("SELF-TEST %s  fixed_no_leader=%s  fixed_all_self=%s  random_elects=%s  winner_is_earliest=%s  winner_has_majority=%s"
          % ("PASS" if ok else "FAIL", fixed_no_leader, fixed_all_self, random_elects, winner_is_earliest, winner_has_majority))
    return ok


def main():
    p = argparse.ArgumentParser(description="Randomized election timeout: draw each node's election timeout from a range instead of giving them all the same fixed value, because identical timeouts make every node become a candidate at once, vote for itself, split the vote, and elect no leader -- repeating indefinitely -- while distinct timeouts let the earliest node gather a majority and win in one round; the randomness only breaks the symmetry.")
    p.add_argument("--fixed", action="store_true")
    p.add_argument("--randomized", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("nodes=%d  file=%s" % (len(d["fixed_timeouts"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.fixed:
        fixed_view(d)
    elif args.randomized:
        randomized_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
