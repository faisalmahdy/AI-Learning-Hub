"""Replicate with a chain -- writes head-to-tail, reads and acknowledgements at the tail -- so a read never returns a value that is not on every replica, unlike naive acknowledge-early / read-any replication.

Chain replication orders the replicas in a line: head, middle(s), tail. A write is applied at the head and passed down the chain one hop at a time, and it is committed -- acknowledged to the client -- only when it reaches the tail. Reads are always served by the tail. That arrangement buys strong consistency almost for free, and the reason is a structural invariant: because propagation is strictly head-to-tail, the replicas that hold the new value are always a prefix of the chain, so if the tail holds the new value, every replica ahead of it does too. The tail is the last to know, which is exactly why trusting it is safe -- anything the tail has, everyone has.

So a read at the tail returns a value that is guaranteed present on every replica, and an acknowledged write (one that reached the tail) is visible to every subsequent tail read. Reads are linearizable and never stale relative to an acknowledged write, and two reads at the same instant cannot disagree, because they all go to the one tail.

Naive replication breaks both halves of this. It acknowledges the write as soon as the first replica -- say the head -- has applied it, before the others catch up, and it lets a read hit any replica. Now a read to a replica that has not yet received the write returns the old value even after the write was acknowledged: a stale read of committed data. And two reads at the same moment to different replicas can return different values, because the replicas are at different points in receiving the write. The client has no single place whose answer is trustworthy.

The rule: replicate with a chain -- propagate writes head-to-tail and take reads and acknowledgements at the tail -- because the tail is the last replica to receive a write, so a value present at the tail is present everywhere; naive replication that acknowledges at the first replica and reads from any replica returns stale, divergent reads.

On this fixture a new write flows through three replicas. At every step, whenever the tail holds the new value the whole chain does (the chain invariant); a naive scheme that acknowledges once the head has the write and then reads the tail returns the stale old value. This computes both.

  --propagate   the value of each replica ([head, middle, tail]) at each step of replication
  --read        the chain (tail) read vs a naive read-from-any at each step, flagging stale/divergent reads
  --check       chain reads are always fully-replicated; naive acknowledge-early read-any reads go stale

propagation and tail_index are the fixture; the invariant and the read outcomes are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "chainrep.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def tail_read(state, tail_index):
    return state[tail_index]


def tail_committed_implies_all(state, tail_index, new="new"):
    """Chain invariant: if the tail holds the new value, every replica does."""
    if state[tail_index] == new:
        return all(v == new for v in state)
    return True


def diverges(state):
    """Do the replicas disagree at this instant (a read-from-any hazard)?"""
    return len(set(state)) > 1


# ----------------------------------------------------------------- printing

def propagate_view(data):
    prop, tail = data["propagation"], data["tail_index"]
    print("PROPAGATE — replica values [head, middle, tail] as the write flows down")
    print("-" * 56)
    print("  step   head   middle  tail")
    for i, s in enumerate(prop):
        print("  %-5d  %-5s  %-6s  %s" % (i, s[0], s[1], s[tail]))
    print("-" * 56)
    print("  the new value is always a prefix ending no later than the tail")


def read_view(data):
    prop, tail = data["propagation"], data["tail_index"]
    print("READ — chain (tail) read vs naive read-from-any, per step")
    print("-" * 62)
    print("  step   chain(tail)   naive replicas   divergent?")
    for i, s in enumerate(prop):
        print("  %-5d  %-11s   %-15s  %s" % (i, tail_read(s, tail), s, diverges(s)))
    print("-" * 62)
    print("  a chain read only ever returns a value all replicas hold; read-any can disagree")


def check(data):
    print("SELF-TEST — chain reads are always fully-replicated; naive acknowledge-early read-any reads go stale")
    print("-" * 124)
    prop, tail = data["propagation"], data["tail_index"]

    chain_invariant_holds = all(tail_committed_implies_all(s, tail) for s in prop)
    print("  chain invariant holds at every step (tail=new => all=new) = %s" % chain_invariant_holds)

    tail_read_always_replicated = all(
        (tail_read(s, tail) != "new") or all(v == "new" for v in s) for s in prop)
    print("  every tail read returns a value present on all replicas = %s" % tail_read_always_replicated)

    # naive: acknowledge as soon as the head has the write
    head_ack_step = next(i for i, s in enumerate(prop) if s[0] == "new")
    naive_ack_then_tail_stale = prop[head_ack_step][tail] != "new"
    print("  naive: after head-acknowledges (step %d), a tail read is stale = %s (%s)"
          % (head_ack_step, naive_ack_then_tail_stale, prop[head_ack_step][tail]))

    naive_reads_can_diverge = any(diverges(s) for s in prop)
    print("  naive read-from-any can return divergent values across replicas = %s" % naive_reads_can_diverge)

    commit_step = next(i for i, s in enumerate(prop) if s[tail] == "new")
    chain_committed_everywhere = all(v == "new" for v in prop[commit_step])
    print("  when the chain commits (tail=new at step %d) the write is on every replica = %s" % (commit_step, chain_committed_everywhere))

    ok = (chain_invariant_holds and tail_read_always_replicated and naive_ack_then_tail_stale
          and naive_reads_can_diverge and chain_committed_everywhere)
    print("-" * 124)
    print("SELF-TEST %s  chain_invariant_holds=%s  tail_read_always_replicated=%s  naive_ack_then_tail_stale=%s  naive_reads_can_diverge=%s  chain_committed_everywhere=%s"
          % ("PASS" if ok else "FAIL", chain_invariant_holds, tail_read_always_replicated, naive_ack_then_tail_stale, naive_reads_can_diverge, chain_committed_everywhere))
    return ok


def main():
    p = argparse.ArgumentParser(description="Chain replication: replicate with a chain -- propagate writes head-to-tail and take reads and acknowledgements at the tail -- because the tail is the last replica to receive a write, so a value present at the tail is present everywhere; naive replication that acknowledges at the first replica and reads from any replica returns stale, divergent reads.")
    p.add_argument("--propagate", action="store_true")
    p.add_argument("--read", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("replicas=%d  tail_index=%d  steps=%d  file=%s  (the propagation is a fixture)"
          % (len(data["propagation"][0]), data["tail_index"], len(data["propagation"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.propagate:
        propagate_view(data)
    elif args.read:
        read_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
