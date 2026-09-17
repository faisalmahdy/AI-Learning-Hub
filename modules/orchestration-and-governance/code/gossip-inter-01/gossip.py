"""Disseminate an update by gossip -- each informed node tells another each round -- not by a single source broadcasting to everyone, or one node becomes a linear-time bottleneck and a single point of failure.

When one node in a cluster learns something everyone must hear -- a config change, a membership update, a cache invalidation -- the obvious way to spread it is for that node to send it to each of the others. It works, and it has two problems that get worse with cluster size. The origin does all the sending, so it is a bottleneck: N-1 sends stacked on one node, taking N-1 rounds if it sends one at a time. And the origin is a single point of failure: if it dies partway through, the nodes it had not yet reached never hear the update, because no one else is spreading it. The dissemination is only as reliable and as fast as one machine.

Gossip inverts both. In each round, every node that already has the update picks another node that does not and passes it along. Now the number of informed nodes roughly doubles every round -- 1, 2, 4, 8 -- so the whole cluster is covered in about log2(N) rounds instead of N-1. The sends are spread across every informed node rather than piled on the origin, so no node carries more than about log2(N) sends. And because many nodes are spreading at once, the failure of any single node, the origin included, barely dents the process -- the others keep infecting. It is called epidemic dissemination for a reason: like an infection, it grows exponentially and does not depend on any one carrier.

The trade is essentially free. Both strategies deliver the same total number of messages -- N-1, one per node that gets informed -- so gossip is not doing more work; it is doing the same work in parallel and without a coordinator. What you give up is tidy determinism (real gossip picks peers at random and takes a variable number of rounds, and a node may be told something it already knows), and what you gain is logarithmic latency, balanced load, and robustness. For anything from a handful to millions of nodes, that trade is why gossip underlies cluster membership, failure detection, and replicated-state systems.

The rule: disseminate cluster-wide state by gossip -- each informed node forwards to another each round -- rather than a single-source broadcast, because a lone sender is an O(N)-round bottleneck and a single point of failure, while gossip informs everyone in O(log N) rounds with the load spread and no dependence on any one node.

On this fixture an update starts at one of 8 nodes. Gossip informs all 8 in 3 rounds (log2 8) with no node sending more than 3 times; the single-source broadcast takes 7 rounds with all 7 sends on the origin, and if the origin dies after round 1 it strands the rest -- while gossip keeps spreading. This computes both.

  --spread   the count of informed nodes after each round, gossip vs single-source broadcast
  --load     rounds to inform everyone, peak per-node send load, and total messages, each strategy
  --check    the broadcast is linear and bottlenecked on one node that is a single point of failure; gossip is logarithmic, load-balanced, and robust

n and source are the fixture; the rounds, informed counts, per-node loads, and source-failure robustness are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "gossip.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def gossip(n, source):
    """Each round, every informed node forwards to the next uninformed node. Returns (informed-per-round, per-node send counts)."""
    informed = [source]
    loads = {source: 0}
    history = [len(informed)]
    while len(informed) < n:
        newly = []
        for node in list(informed):
            target = next((c for c in range(n) if c not in informed and c not in newly), None)
            if target is not None:
                loads[node] = loads.get(node, 0) + 1
                newly.append(target)
        informed += newly
        history.append(len(informed))
    return history, loads


def broadcast(n, source):
    """The source sends to one other node per round; only the source ever sends."""
    loads = {source: 0}
    history = [1]
    informed = 1
    while informed < n:
        loads[source] += 1
        informed += 1
        history.append(informed)
    return history, loads


def reach_if_source_dies_after_round1(n, source, strategy):
    """How many nodes ever get informed if the source stops sending after round 1."""
    if strategy == "broadcast":
        return 2 if n >= 2 else 1          # source informed exactly one node in round 1, then stops; no one else spreads
    # gossip: after round 1 the source and one peer are informed; remove the source, let the peer keep spreading
    informed = [source, next(c for c in range(n) if c != source)]
    dead = source
    while True:
        newly = []
        for node in list(informed):
            if node == dead:
                continue
            target = next((c for c in range(n) if c not in informed and c not in newly), None)
            if target is not None:
                newly.append(target)
        if not newly:
            break
        informed += newly
    return len(informed)


# ----------------------------------------------------------------- printing

def spread_view(data):
    n, source = data["n"], data["source"]
    g, _ = gossip(n, source)
    b, _ = broadcast(n, source)
    print("SPREAD — informed nodes after each round (n=%d)" % n)
    print("-" * 56)
    rounds = max(len(g), len(b))
    print("  round     gossip   broadcast")
    for r in range(rounds):
        gv = g[r] if r < len(g) else g[-1]
        bv = b[r] if r < len(b) else b[-1]
        print("  %-8d  %-6d   %d" % (r, gv, bv))
    print("-" * 56)
    print("  gossip doubles each round; broadcast crawls up one at a time")


def load_view(data):
    n, source = data["n"], data["source"]
    g, gl = gossip(n, source)
    b, bl = broadcast(n, source)
    print("LOAD — cost to inform all %d nodes, each strategy" % n)
    print("-" * 58)
    print("  gossip:     %d rounds, peak %d sends/node, %d total messages" % (len(g) - 1, max(gl.values()), sum(gl.values())))
    print("  broadcast:  %d rounds, peak %d sends/node, %d total messages" % (len(b) - 1, max(bl.values()), sum(bl.values())))
    print("-" * 58)
    print("  same total messages; gossip finishes in log2(n)=%d rounds and spreads the load" % math.ceil(math.log2(n)))


def check(data):
    print("SELF-TEST — the broadcast is linear and bottlenecked on one node that is a single point of failure; gossip is logarithmic, load-balanced, and robust")
    print("-" * 146)
    n, source = data["n"], data["source"]
    g, gl = gossip(n, source)
    b, bl = broadcast(n, source)
    g_rounds, b_rounds = len(g) - 1, len(b) - 1

    gossip_faster = g_rounds < b_rounds
    print("  gossip informs everyone in fewer rounds = %s (%d < %d)" % (gossip_faster, g_rounds, b_rounds))

    gossip_logarithmic = g_rounds == math.ceil(math.log2(n))
    print("  gossip takes log2(n) rounds = %s (%d == ceil(log2 %d))" % (gossip_logarithmic, g_rounds, n))

    broadcast_linear = b_rounds == n - 1
    print("  broadcast takes n-1 rounds = %s (%d)" % (broadcast_linear, b_rounds))

    gossip_spreads_load = max(gl.values()) < max(bl.values())
    print("  gossip's peak per-node send load is lower = %s (%d < %d)" % (gossip_spreads_load, max(gl.values()), max(bl.values())))

    same_total = sum(gl.values()) == sum(bl.values()) == n - 1
    print("  both deliver the same total messages (n-1) = %s (%d)" % (same_total, sum(gl.values())))

    g_reach = reach_if_source_dies_after_round1(n, source, "gossip")
    b_reach = reach_if_source_dies_after_round1(n, source, "broadcast")
    source_is_spof = b_reach < n and g_reach == n
    print("  if the source dies after round 1: broadcast strands nodes, gossip still reaches all = %s (broadcast %d, gossip %d of %d)"
          % (source_is_spof, b_reach, g_reach, n))

    ok = (gossip_faster and gossip_logarithmic and broadcast_linear and gossip_spreads_load and same_total and source_is_spof)
    print("-" * 146)
    print("SELF-TEST %s  gossip_faster=%s  gossip_logarithmic=%s  broadcast_linear=%s  gossip_spreads_load=%s  same_total=%s  source_is_spof=%s"
          % ("PASS" if ok else "FAIL", gossip_faster, gossip_logarithmic, broadcast_linear, gossip_spreads_load, same_total, source_is_spof))
    return ok


def main():
    p = argparse.ArgumentParser(description="Gossip dissemination: disseminate cluster-wide state by gossip -- each informed node forwards to another each round -- rather than a single-source broadcast, because a lone sender is an O(N)-round bottleneck and a single point of failure, while gossip informs everyone in O(log N) rounds with the load spread and no dependence on any one node.")
    p.add_argument("--spread", action="store_true")
    p.add_argument("--load", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n=%d  source=%d  file=%s  (the cluster size and origin are a fixture)" % (data["n"], data["source"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.spread:
        spread_view(data)
    elif args.load:
        load_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
