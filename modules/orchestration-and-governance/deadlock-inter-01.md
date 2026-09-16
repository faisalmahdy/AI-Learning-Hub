---
id: deadlock-inter-01
title: Detect deadlock as a cycle in the wait-for graph and abort the cheapest victim — don't just time out the slow ones
topic: orchestration-and-governance
level: intermediate
status: ready
time: 16 min
summary: When transactions or agents hold resources and block waiting for each other, a deadlock is a precise structure — a cycle in the wait-for graph. If T1 waits for a lock T2 holds, T2 for T3, and T3 for T1, each waits for the next, none can proceed, and none will ever release, so they wait forever. The tempting non-fix is a timeout: kill anything blocked too long. That both over- and under-reacts — it kills transactions that were merely slow (losing their work for nothing) and transactions blocked behind a deadlock but not part of it, when aborting one cycle member would have freed them. Real detection reads the structure: the transactions on a cycle are exactly the deadlocked set, and everything else, including a transaction blocked waiting on a deadlocked one, is not deadlocked, just stuck behind it. To resolve, abort the cycle member that has done the least work — releasing its resources, breaking the cycle, and freeing the rest. On a fixture where T1→T2→T3→T1 is a cycle and T4 waits on T2, detection reports the deadlocked set as exactly {T1, T2, T3}, and aborting the cheapest member T3 (cost 10) clears the deadlock while leaving the innocent T4 untouched.
eli5: Three people are each holding a door shut and waiting for the next person to open theirs first — a stuck loop where nobody moves. A timer that says "if you've waited too long, go home" is clumsy: it sends home people who were just slow, and it doesn't even know which three are in the actual loop. The right move is to look at who's waiting on whom, spot the closed loop, and ask just one of those three — the one who's done the least so far — to let go. The loop breaks, everyone else waiting behind them gets through, and nobody innocent gets sent home.
---

## Why this module

A deadlock is not "something is taking too long" — it is a specific closed loop of mutual waiting, and confusing the symptom (a long wait) with the structure (a cycle) makes you kill the wrong things and miss the right one.

Concurrent systems let a transaction hold a resource while it waits for another, and that waiting forms a graph: an edge from T1 to T2 means T1 is blocked wanting something T2 holds. Most of the time this graph is a harmless set of chains — someone waits, gets the resource, proceeds. A deadlock is the moment the graph contains a cycle. If the waiting loops back on itself — T1 waits for T2, T2 for T3, T3 for T1 — then every transaction in the loop is waiting for another transaction in the loop, so none can make the progress that would let it release its resources, and the wait is not long, it is eternal. No amount of patience resolves it, because the thing each is waiting for will never happen. That is the defining feature: a deadlock is a cycle, and a cycle is forever.

**A deadlock is a cycle in the wait-for graph — a closed loop of mutual waiting that no waiting resolves — so it is a structural property to detect, not a duration to wait out; the transactions on the cycle are exactly the deadlocked ones.**

The lazy substitute is a timeout: declare anything blocked past a threshold dead and abort it. This confuses waiting with deadlock, and it fails on both sides. A transaction that is merely slow — waiting on a busy but progressing resource — gets killed and its work discarded, though it was never stuck. And a transaction blocked *behind* a deadlock, waiting on one of the deadlocked transactions, looks identical to a timeout (it has waited a long time) even though it is not part of the cycle and would come unstuck the instant the real deadlock is broken. The structural approach avoids both errors: build the wait-for graph, find the cycle, and the cycle members are the deadlocked set — no more, no less. Break the cycle by aborting one member, chosen to be the cheapest to roll back, and everything blocked behind it proceeds. This module detects the cycle, names the deadlocked set, and resolves it at its least-cost point.

## Concepts

**The wait-for graph** has an edge from T to U when T is blocked waiting for a resource U holds. `reachable` follows those edges to find everything a transaction is (transitively) waiting on.

```python filename=modules/orchestration-and-governance/code/deadlock-inter-01/deadlock.py:42-50 COMPLETE
def reachable(graph, start):
    """Every node reachable from start following one or more wait-for edges."""
    seen, stack = set(), list(graph.get(start, []))
    while stack:
        n = stack.pop()
        if n not in seen:
            seen.add(n)
            stack.extend(graph.get(n, []))
    return seen
```

**A transaction is deadlocked exactly when it can reach itself** through the wait-for edges — it is on a cycle. That test distinguishes the deadlocked from the merely blocked.

```python filename=modules/orchestration-and-governance/code/deadlock-inter-01/deadlock.py:53-55 COMPLETE
def deadlocked_set(graph):
    """Transactions on a cycle: a node is deadlocked iff it can reach itself through the wait-for edges."""
    return {n for n in graph if n in reachable(graph, n)}
```

**Blocked is not deadlocked.** A transaction waiting on a deadlocked one has waited just as long, but it is not on the cycle, so breaking the cycle frees it — a timeout cannot tell the two apart.

<svg role="img" aria-label="A wait-for graph with a cycle T1 to T2 to T3 back to T1; T4 points into T2 from outside the cycle; T5 stands alone" viewBox="0 0 300 104" width="300" height="104">
  <circle cx="70" cy="30" r="12" fill="var(--s2)"/><text x="63" y="33" fill="var(--panel)" font-size="8">T1</text>
  <circle cx="140" cy="30" r="12" fill="var(--s2)"/><text x="133" y="33" fill="var(--panel)" font-size="8">T2</text>
  <circle cx="105" cy="78" r="12" fill="var(--s2)"/><text x="98" y="81" fill="var(--panel)" font-size="8">T3</text>
  <line x1="82" y1="30" x2="128" y2="30" stroke="var(--s2)"/><polygon points="128,27 134,30 128,33" fill="var(--s2)"/>
  <line x1="136" y1="41" x2="112" y2="67" stroke="var(--s2)"/><polygon points="110,62 108,70 116,66" fill="var(--s2)"/>
  <line x1="98" y1="67" x2="74" y2="41" stroke="var(--s2)"/><polygon points="72,46 70,38 78,42" fill="var(--s2)"/>
  <text x="60" y="16" fill="var(--muted)" font-size="7">cycle = deadlock</text>
  <circle cx="210" cy="30" r="12" fill="none" stroke="var(--line)"/><text x="203" y="33" fill="var(--ink)" font-size="8">T4</text>
  <line x1="198" y1="30" x2="154" y2="30" stroke="var(--muted)" stroke-dasharray="2 2"/><polygon points="156,27 150,30 156,33" fill="var(--muted)"/>
  <text x="196" y="52" fill="var(--muted)" font-size="7">blocked, not in cycle</text>
  <circle cx="270" cy="78" r="12" fill="none" stroke="var(--line)"/><text x="263" y="81" fill="var(--ink)" font-size="8">T5</text>
  <text x="248" y="98" fill="var(--muted)" font-size="7">free</text>
</svg>
^ T1→T2→T3→T1 form a cycle (the deadlock); T4 points into T2 from outside, so it is blocked by the deadlock but not part of it; T5 waits on nothing.

**A deadlock is a cycle, so detect it by testing which transactions can reach themselves in the wait-for graph — those, and only those, are deadlocked, distinct from the transactions merely blocked behind them.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/deadlock-inter-01/deadlock.py

The fixture is a wait-for graph with a three-transaction cycle, a fourth blocked behind it, a fifth free, and a rollback cost per transaction.

```json filename=modules/orchestration-and-governance/code/deadlock-inter-01/deadlock.json:3-10 COMPLETE
  "waits_for": {
    "T1": ["T2"],
    "T2": ["T3"],
    "T3": ["T1"],
    "T4": ["T2"],
    "T5": []
  },
  "cost": {"T1": 50, "T2": 30, "T3": 10, "T4": 40, "T5": 5}
```

Run `--detect` to find the deadlock.

```text filename=--detect
DETECT — the wait-for graph and the cycle in it
--------------------------------------------------------
  T1 waits for ['T2']
  T2 waits for ['T3']
  T3 waits for ['T1']
  T4 waits for ['T2']
  T5 waits for (nothing)
--------------------------------------------------------
  cycle found:       T1 -> T2 -> T3 -> T1
  deadlocked set:    ['T1', 'T2', 'T3']
  blocked but not deadlocked: ['T4']
```

The detector finds the cycle T1 → T2 → T3 → T1 and reports the deadlocked set as exactly {T1, T2, T3}. T4 is listed separately as "blocked but not deadlocked" — it waits on T2, which is deadlocked, so T4 will wait forever *unless* the deadlock is resolved, but T4 itself is not on the cycle. That distinction is the entire value of structural detection. To a timeout, T4 is indistinguishable from T1, T2, and T3 — all four have been waiting a long time — so a timeout policy would be as likely to abort T4 as any real deadlock member, throwing away T4's work to fix a deadlock T4 was not part of. Worse, aborting T4 does nothing to break the cycle: T1, T2, and T3 are still waiting on each other, so the deadlock survives and a second victim must be chosen. The wait-for graph makes the right target unambiguous: the cycle, and nothing outside it.

<svg role="img" aria-label="The deadlocked set T1, T2, T3 is circled together; T4 sits outside it, blocked; a timeout cannot distinguish T4 from the cycle members" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">who is actually deadlocked?</text>
  <rect x="20" y="24" width="150" height="44" rx="8" fill="var(--s2)" opacity="0.18" stroke="var(--s2)"/>
  <text x="30" y="20" fill="var(--s2)" font-size="7">deadlocked (the cycle)</text>
  <circle cx="55" cy="46" r="12" fill="var(--s2)"/><text x="48" y="49" fill="var(--panel)" font-size="8">T1</text>
  <circle cx="95" cy="46" r="12" fill="var(--s2)"/><text x="88" y="49" fill="var(--panel)" font-size="8">T2</text>
  <circle cx="135" cy="46" r="12" fill="var(--s2)"/><text x="128" y="49" fill="var(--panel)" font-size="8">T3</text>
  <circle cx="215" cy="46" r="12" fill="none" stroke="var(--line)"/><text x="208" y="49" fill="var(--ink)" font-size="8">T4</text>
  <text x="196" y="72" fill="var(--muted)" font-size="7">blocked, innocent</text>
  <text x="6" y="94" fill="var(--muted)" font-size="8">a timeout has waited equally long on T4 and the cycle — structure tells them apart</text>
</svg>
^ Structural detection isolates the deadlocked set {T1, T2, T3} and marks T4 as blocked-but-innocent; a timeout, seeing only that all four waited a long time, cannot make that distinction.

## Build

Detection names the cycle; resolution has to break it. Run `--resolve`.

```text filename=--resolve
RESOLVE — abort the cheapest cycle member, then re-check
--------------------------------------------------------
  deadlocked members and cost: {'T1': 50, 'T2': 30, 'T3': 10}
  victim (lowest cost):        T3 (cost 10)
  cycle after aborting T3:      none -- deadlock cleared
  T4 (was blocked) aborted?    False
```

Breaking a cycle needs only one cut: abort any single member and the loop is open. But the members are not equal — each has done some work that an abort discards — so the choice is which one to sacrifice. Aborting the cheapest, T3 at cost 10, throws away a third of the work that aborting T1 (cost 50) would, and it breaks the cycle just as completely. After T3 is aborted, its resources are released, so T2 (which waited on T3) can proceed; the re-check confirms no cycle remains. And T4 — the innocent bystander — was never touched: it is still in the graph, and now that the deadlock is cleared it will get T2's resource in turn and proceed. This is the whole discipline: detect the exact cycle, pick the minimum-damage victim within it, abort only that one, and let everything blocked behind the deadlock recover for free. Victim selection can weigh more than raw cost — how many locks the transaction holds, how many times it has already been chosen as a victim (to avoid starving one transaction with repeated aborts), its priority — but the principle is constant: cut the cycle at its least valuable point, and nowhere else.

<svg role="img" aria-label="Aborting T3 removes it and its edges, so the T1-T2-T3 cycle is broken and no cycle remains, while T4 stays in the graph" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">abort T3 (cheapest) → cycle broken</text>
  <circle cx="60" cy="40" r="12" fill="var(--s2)"/><text x="53" y="43" fill="var(--panel)" font-size="8">T1</text>
  <circle cx="130" cy="40" r="12" fill="var(--s2)"/><text x="123" y="43" fill="var(--panel)" font-size="8">T2</text>
  <circle cx="95" cy="82" r="12" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"/><text x="88" y="85" fill="var(--muted)" font-size="8">T3</text>
  <line x1="80" y1="60" x2="88" y2="72" stroke="var(--s2)" stroke-dasharray="2 2"/><line x1="110" y1="72" x2="124" y2="52" stroke="var(--s2)" stroke-dasharray="2 2"/>
  <text x="80" y="96" fill="var(--muted)" font-size="7">aborted, edges gone</text>
  <line x1="72" y1="40" x2="118" y2="40" stroke="var(--s2)"/><polygon points="118,37 124,40 118,43" fill="var(--s2)"/>
  <circle cx="215" cy="40" r="12" fill="none" stroke="var(--line)"/><text x="208" y="43" fill="var(--ink)" font-size="8">T4</text>
  <text x="196" y="62" fill="var(--muted)" font-size="7">spared, now proceeds</text>
  <text x="6" y="72" fill="var(--muted)" font-size="7">no cycle remains</text>
</svg>
^ Aborting T3 removes it and its edges, opening the loop so no cycle remains and T2 can proceed; T4 stays in the graph untouched and comes unstuck once the deadlock clears.

## Definition of done

The self-test pins detection and resolution: a cycle exists, the deadlocked set is exactly the cycle, the blocked-but-not-cyclic transaction is not deadlocked, the victim is the cheapest cycle member, and aborting it clears the deadlock while sparing the innocent.

```python filename=modules/orchestration-and-governance/code/deadlock-inter-01/deadlock.py:137-149 COMPLETE
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
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — a cycle exists; the deadlocked set is exactly the cycle; a blocked-but-not-cyclic txn is not deadlocked
--------------------------------------------------------------------------------------------------------------------
  the wait-for graph contains a cycle (a deadlock) = True (T1 -> T2 -> T3 -> T1)
  the deadlocked set is exactly {T1,T2,T3} = True (['T1', 'T2', 'T3'])
  T4 is blocked (waits on the deadlock) but not itself deadlocked = True
  the victim is the lowest-cost cycle member = True (T3, cost 10)
  aborting the victim leaves no cycle = True
  the innocent blocked T4 is spared (not aborted) = True
```

**Done means detection and resolution are both proven: the wait-for graph's cycle T1→T2→T3→T1 is found, the deadlocked set is exactly {T1, T2, T3}, T4 is blocked on the deadlock but not part of it, the chosen victim is the cheapest cycle member T3 (cost 10), and aborting it leaves no cycle while sparing the innocent T4 — the structural fix a timeout cannot achieve.**

## Boss fight

Predict the two ways detection-and-abort is harder than one graph makes it look. It is tempting to think "find the cycle, abort the cheapest, done."

The first trap is that in a distributed system there is no single wait-for graph to inspect — the edges are spread across machines, and assembling a consistent global snapshot of them is itself a hard problem. Each node knows only its local waits; a deadlock can span several nodes, and by the time you gather everyone's edges into one place, some may have changed (a lock released, a new wait added), so the graph you analyze may show a *phantom* deadlock that has already resolved, or miss a real one that formed after you sampled. This is why distributed deadlock detection uses careful protocols (edge-chasing, where a probe message follows the wait-for edges and declares deadlock only if it returns to its origin) rather than snapshotting, and why many production databases sidestep detection entirely with *prevention*: order all resources and require locks be acquired in that order, so a cycle is impossible by construction, or use wound-wait / wait-die schemes that abort based on transaction age to guarantee no cycle can form. Detection is one option; on a single node it is clean, but distributed it competes with prevention precisely because the global graph is expensive and stale.

```python filename=modules/orchestration-and-governance/code/deadlock-inter-01/deadlock.py:88-91 COMPLETE
def victim(graph, cost):
    """The lowest-cost transaction in the deadlock -- aborting it loses the least work."""
    dead = deadlocked_set(graph)
    return min(dead, key=lambda t: cost[t]) if dead else None
```

The second trap is that victim selection by cost alone can starve a transaction to death. If you always abort the cheapest member, a transaction that is cheap because it is young — it just started, so it has done little work — gets aborted, restarts, becomes the cheapest again, deadlocks again, and is aborted again, forever making progress and losing it. A live-lock hides inside the "minimize damage" rule: minimizing this abort's cost can maximize the total cost across retries. Real victim selection therefore folds in how many times a transaction has already been chosen (raising its effective priority each time so it eventually survives), its age, and its priority, not just its current rollback cost — the same fairness concern as aging a starved task in a priority queue. And the abort itself must be a clean rollback that releases every lock the victim held, or breaking one cycle can leave partial state that forms another. So "abort the cheapest" is the first approximation; the production rule guards against starving a repeat victim and guarantees the abort fully unwinds.

**Detect deadlock as a cycle in the wait-for graph — the transactions on the cycle are exactly the deadlocked set, distinct from those merely blocked behind it, so a timeout that acts on waiting-duration kills the wrong ones — and break it by aborting a single cycle member chosen to minimize damage; but a global wait-for graph is expensive and stale to assemble in a distributed system (edge-chasing or prevention schemes like lock ordering and wound-wait are the alternatives), and victim selection must weigh a transaction's abort history and age, not only its current cost, or repeatedly aborting the cheapest young transaction starves it in a live-lock.**

## External resources

Any database-systems or operating-systems text on deadlock — the wait-for graph and cycle detection, the Coffman conditions for deadlock, and the prevention/avoidance/detection taxonomy (lock ordering, wound-wait, wait-die, banker's algorithm).

Writing on distributed deadlock detection (edge-chasing / Chandy–Misra–Haas) and on victim selection and starvation — why a consistent global wait-for graph is hard and how production systems choose and bound their victims.

The companion "age waiting tasks up in priority" and "a participant that voted yes but hasn't heard the decision cannot resolve alone (2PC blocking)" modules — the first is the same anti-starvation fairness applied to a queue, and the second is a different forever-wait (a blocked commit protocol) that, unlike a deadlock, has no cycle to detect and abort.
