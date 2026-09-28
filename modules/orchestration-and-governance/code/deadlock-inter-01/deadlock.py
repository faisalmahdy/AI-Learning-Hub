"""Detect deadlock as a cycle in the wait-for graph and abort the cheapest victim -- don't just time out the slow ones.

When transactions or agents hold resources and block waiting for each other, a deadlock is a precise structure: a cycle
in the wait-for graph. If T1 waits for a lock T2 holds, T2 waits for T3, and T3 waits for T1, the three form a closed
loop -- each is waiting for the next, none can proceed, and none will ever release, so they wait forever. The tempting
non-fix is a timeout: assume anything blocked too long is stuck and kill it. That both over- and under-reacts. It kills
transactions that were merely slow, not deadlocked, losing their work for nothing; and it kills transactions that are
blocked BEHIND a deadlock but not part of it, when aborting one member of the actual cycle would have freed them. A
timeout treats a symptom (waiting a while) as if it were the disease (a cycle), and the two are not the same.

The real detection reads the structure. Build the wait-for graph and look for a cycle: the transactions on a cycle are
exactly the deadlocked set, and everything else -- including transactions blocked waiting on a deadlocked one -- is not
deadlocked, just stuck behind it. To resolve, pick a victim from the cycle and abort it, which releases its resources,
breaks the cycle, and lets the rest proceed; the others waiting behind the deadlock come unstuck for free. Choose the
victim to minimize damage: abort the cycle member that has done the least work, so the rollback throws away the fewest
computations. Detect the cycle, break it at its cheapest point, and touch nothing outside it.

On this fixture T1->T2->T3->T1 is a deadlock cycle; T4 waits on T2 (blocked by the deadlock, not in it); T5 waits on
nobody. Cycle detection reports the deadlocked set as exactly {T1, T2, T3}. The cheapest member is T3 (cost 10), so
aborting T3 breaks the cycle, and afterward no cycle remains and T4 is untouched -- where a timeout would have risked
killing the innocent T4 too. This computes both.

  --detect   the wait-for graph, the cycle it contains, and the deadlocked set vs the merely-blocked
  --resolve  the lowest-cost victim in the cycle, and that aborting it leaves no cycle (and spares the blocked T4)
  --check    a cycle exists; the deadlocked set is exactly the cycle; a blocked-but-not-cyclic txn is not deadlocked

The wait-for graph and costs are the fixture; every cycle and victim is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "deadlock.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def reachable(graph, start):
    """Every node reachable from start following one or more wait-for edges."""
    seen, stack = set(), list(graph.get(start, []))
    while stack:
        n = stack.pop()
        if n not in seen:
            seen.add(n)
            stack.extend(graph.get(n, []))
    return seen


def deadlocked_set(graph):
    """Transactions on a cycle: a node is deadlocked iff it can reach itself through the wait-for edges."""
    return {n for n in graph if n in reachable(graph, n)}


def find_cycle(graph):
    """Return one cycle as an ordered list of nodes, or [] if the graph is acyclic."""
    path, on_path = [], set()

    def dfs(node):
        path.append(node)
        on_path.add(node)
        for nxt in graph.get(node, []):
            if nxt in on_path:
                return path[path.index(nxt):] + [nxt]
            if nxt not in visited:
                got = dfs(nxt)
                if got:
                    return got
        path.pop()
        on_path.discard(node)
        return []

    visited = set()
    for start in graph:
        if start not in visited:
            cyc = dfs(start)
            visited.update(path)
            path.clear()
            on_path.clear()
            if cyc:
                return cyc
    return []


def victim(graph, cost):
    """The lowest-cost transaction in the deadlock -- aborting it loses the least work."""
    dead = deadlocked_set(graph)
    return min(dead, key=lambda t: cost[t]) if dead else None


def abort(graph, txn):
    """Return the wait-for graph with `txn` aborted: it releases resources and leaves the graph."""
    return {t: [w for w in waits if w != txn] for t, waits in graph.items() if t != txn}


# ----------------------------------------------------------------- printing

def detect_view(data):
    g = data["waits_for"]
    print("DETECT — the wait-for graph and the cycle in it")
    print("-" * 56)
    for t, waits in g.items():
        print("  %s waits for %s" % (t, waits if waits else "(nothing)"))
    print("-" * 56)
    cyc = find_cycle(g)
    dead = deadlocked_set(g)
    print("  cycle found:       %s" % (" -> ".join(cyc) if cyc else "none (no deadlock)"))
    print("  deadlocked set:    %s" % sorted(dead))
    print("  blocked but not deadlocked: %s" % sorted(t for t in g if t not in dead and g[t]))
    print("-" * 56)
    print("  the deadlocked set is exactly the cycle; T4 waits on the deadlock but is not in it.")


def resolve_view(data):
    g, cost = data["waits_for"], data["cost"]
    v = victim(g, cost)
    after = abort(g, v)
    print("RESOLVE — abort the cheapest cycle member, then re-check")
    print("-" * 56)
    dead = deadlocked_set(g)
    print("  deadlocked members and cost: %s" % {t: cost[t] for t in sorted(dead)})
    print("  victim (lowest cost):        %s (cost %d)" % (v, cost[v]))
    print("  cycle after aborting %s:      %s" % (v, " -> ".join(find_cycle(after)) if find_cycle(after) else "none -- deadlock cleared"))
    print("  T4 (was blocked) aborted?    %s" % ("T4" not in after))
    print("-" * 56)
    print("  breaking the cycle at its cheapest point frees the rest; the innocent blocked txn is untouched.")


def check(data):
    print("SELF-TEST — a cycle exists; the deadlocked set is exactly the cycle; a blocked-but-not-cyclic txn is not deadlocked")
    print("-" * 116)
    g, cost = data["waits_for"], data["cost"]

    has_cycle = len(find_cycle(g)) > 0
    print("  the wait-for graph contains a cycle (a deadlock) = %s (%s)" % (has_cycle, " -> ".join(find_cycle(g))))

    dead = deadlocked_set(g)
    dead_is_cycle = dead == {"T1", "T2", "T3"}
    print("  the deadlocked set is exactly {T1,T2,T3} = %s (%s)" % (dead_is_cycle, sorted(dead)))

    t4_blocked_not_dead = "T4" not in dead and g["T4"]
    print("  T4 is blocked (waits on the deadlock) but not itself deadlocked = %s" % bool(t4_blocked_not_dead))

    v = victim(g, cost)
    victim_is_cheapest = cost[v] == min(cost[t] for t in dead)
    print("  the victim is the lowest-cost cycle member = %s (%s, cost %d)" % (victim_is_cheapest, v, cost[v]))

    after = abort(g, v)
    cleared = len(find_cycle(after)) == 0
    print("  aborting the victim leaves no cycle = %s" % cleared)

    t4_spared = "T4" in after
    print("  the innocent blocked T4 is spared (not aborted) = %s" % t4_spared)

    ok = has_cycle and dead_is_cycle and bool(t4_blocked_not_dead) and victim_is_cheapest and cleared and t4_spared
    print("-" * 116)
    print("SELF-TEST %s  has_cycle=%s  dead_is_cycle=%s  t4_blocked_not_dead=%s  victim_is_cheapest=%s  cleared=%s  t4_spared=%s"
          % ("PASS" if ok else "FAIL", has_cycle, dead_is_cycle, bool(t4_blocked_not_dead), victim_is_cheapest, cleared, t4_spared))
    return ok


def main():
    p = argparse.ArgumentParser(description="Deadlock detection: find a cycle in the wait-for graph (the deadlocked set is exactly the cycle) and abort the lowest-cost member to break it, instead of timing out slow or merely-blocked transactions.")
    p.add_argument("--detect", action="store_true")
    p.add_argument("--resolve", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("transactions=%d  file=%s  (the wait-for graph is a fixture)" % (len(data["waits_for"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.detect:
        detect_view(data)
    elif args.resolve:
        resolve_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
