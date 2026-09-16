---
id: lockorder-inter-01
title: Acquire locks in one global order — two transactions that grab the same locks in opposite orders deadlock, and a canonical order makes the wait cycle impossible
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: A deadlock over locks is a precise structure — a cycle in the wait-for graph — and it needs a specific ingredient to form: two transactions that acquire the same locks in opposite relative orders. Transaction t1 takes lock A then B; transaction t2 takes B then A. Interleave them so t1 holds A and t2 holds B, and now t1 waits for B (held by t2) while t2 waits for A (held by t1) — t1 → t2 → t1, a cycle in which neither proceeds and neither releases. Simulating every interleaving of the two, 4 of the 6 deadlock. The usual responses treat the symptom: a timeout kills a victim after the fact, a deadlock detector finds the cycle and aborts someone. The cheaper fix removes the possibility. Impose a canonical global order on the locks — here alphabetical, A before B — and require every transaction to acquire the locks it needs in that order (sort its lock set before locking). Now both transactions request A before B: whoever takes A first gets B unobstructed, and the other simply waits for A and then proceeds. A wait-for cycle would require some transaction to hold a later-ordered lock while waiting for an earlier one, which the discipline forbids, so the graph is always acyclic. Re-running all 6 interleavings under the ordered plans, 0 deadlock. The rule: give every lock a global rank and always acquire in rank order — deadlock is then prevented by construction, not detected and recovered.
eli5: Imagine a narrow hallway with two doors, a red one and a blue one, and two people who each need to go through both. If one person always opens red first and the other always opens blue first, they can get stuck: the first is standing in the red doorway waiting for blue, the second is standing in the blue doorway waiting for red, and neither can move because each is blocking the door the other needs. Now make a rule everybody follows: always go through red before blue. Whoever reaches red first goes red then blue and is through; the other just waits at red for a moment and then follows. They can never trap each other, because they are never standing in the two doorways in the opposite order. Same doors, same people — the only change is that everyone agrees on the order.
---

## Why this module

Deadlock is the classic multi-lock failure, and most teams meet it as a mysterious hang: two operations that each work fine alone, run at the same time, and both stop forever. The instinct is to reach for a cure — a timeout that kills whatever has been stuck too long, or a detector that finds the tangle and aborts a victim. Both work, and both are recovery: they let the deadlock happen and then clean up, at the cost of killed work and lost latency.

There is a cheaper move that most deadlocks never survive to need: prevent the cycle from being able to form. A wait-for cycle is not arbitrary — it requires two transactions to hold locks in opposite orders. Take that ingredient away and no interleaving, however unlucky, can deadlock.

This module builds the smallest deadlock — two transactions, two locks, opposite orders — and simulates every way they can interleave: 4 of 6 deadlock. Then it sorts both transactions' lock requests into one global order and simulates again: 0 of 6. Same locks, same transactions, same scheduler; the only change is that both now acquire in the same order.

**A deadlock is not bad luck to be recovered from but a structure to be forbidden, and the structure needs opposite acquisition orders that a single global order simply removes.**

## Concepts

Hold the definition precisely: a deadlock is a cycle in the wait-for graph, the graph whose nodes are transactions and whose edge t → u means "t is blocked waiting for a lock that u holds." If that graph has a cycle, every transaction on it waits for the next and none can advance — a permanent stall, distinct from mere slowness because no amount of waiting resolves it.

Now ask what it takes to build such a cycle with two transactions and two locks. You need t1 → t2 and t2 → t1 at the same time: t1 waiting on a lock t2 holds, and t2 waiting on a lock t1 holds. That means t1 holds one lock and wants the other, while t2 holds the other and wants the first — which can only happen if the two acquired the shared locks in opposite orders. One went A-then-B, the other B-then-A, and the interleaving let each grab its first lock before either reached its second.

That opposition is the load-bearing condition. If both transactions acquire the locks in the same order — say both A then B — the cycle cannot appear. Whichever transaction takes A first will, when it goes for B, find B either free or held by someone who is itself not waiting on A (because that someone took A before B too, so it does not hold B while waiting for A). The wait-for graph degenerates from a cycle into a simple chain: everyone lines up behind whoever holds A, and a line has an end.

The figure shows the two graphs. Opposite orders close the loop; a shared order leaves a chain with a front of the queue that can always move.

<svg role="img" aria-label="Two wait-for graphs. On the left, t1 and t2 point to each other in a two-node cycle, each labeled as holding one lock and waiting for the other. On the right, t2 points to t1 in a single arrow with no return edge, a chain, and t1 is free to proceed" viewBox="0 0 640 220">
<text x="160" y="30" fill="var(--ink)" font-size="12" text-anchor="middle">opposite orders: a cycle</text>
<circle cx="90" cy="120" r="30" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5"/>
<text x="90" y="124" fill="var(--ink)" font-size="12" text-anchor="middle">t1</text>
<circle cx="250" cy="120" r="30" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5"/>
<text x="250" y="124" fill="var(--ink)" font-size="12" text-anchor="middle">t2</text>
<path d="M 118 108 C 160 90 180 90 222 108" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
<polygon points="222,108 212,104 214,113" fill="var(--s2)"/>
<path d="M 222 132 C 180 150 160 150 118 132" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
<polygon points="118,132 128,136 126,127" fill="var(--s2)"/>
<text x="170" y="80" fill="var(--muted)" font-size="10" text-anchor="middle">waits for B</text>
<text x="170" y="170" fill="var(--muted)" font-size="10" text-anchor="middle">waits for A</text>
<text x="490" y="30" fill="var(--ink)" font-size="12" text-anchor="middle">one order: a chain</text>
<circle cx="420" cy="120" r="30" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5"/>
<text x="420" y="124" fill="var(--ink)" font-size="12" text-anchor="middle">t1</text>
<text x="420" y="168" fill="var(--muted)" font-size="10" text-anchor="middle">holds A,B — free</text>
<circle cx="580" cy="120" r="30" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5"/>
<text x="580" y="124" fill="var(--ink)" font-size="12" text-anchor="middle">t2</text>
<path d="M 550 120 L 452 120" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
<polygon points="452,120 462,115 462,125" fill="var(--s1)"/>
<text x="500" y="110" fill="var(--muted)" font-size="10" text-anchor="middle">waits for A</text>
</svg>
^ A cycle needs each transaction waiting on the other; a shared acquisition order can only make a chain, which always has a movable front.

**A wait-for cycle is impossible unless two transactions hold locks in opposite order, so fixing the order is not a heuristic that reduces deadlock — it removes the only shape a deadlock can take.**

## Worked example

The fixture is two transactions needing the same two locks in opposite orders, plus the canonical order of the locks.

```json filename=modules/orchestration-and-governance/code/lockorder-inter-01/lockorder.json:3-5 COMPLETE
  "locks": ["A", "B"],
  "t1_plan": ["A", "B"],
  "t2_plan": ["B", "A"]
```

To measure deadlock without guessing, the simulator runs a given interleaving of the two transactions' acquisition steps and reports whether both end up blocked on each other.

```python filename=modules/orchestration-and-governance/code/lockorder-inter-01/lockorder.py:36-53 COMPLETE
def simulate(plan1, plan2, schedule):
    """Run one interleaving; return 'deadlock' if both transactions end up blocked waiting on each other."""
    plans = {"t1": plan1, "t2": plan2}
    pos = {"t1": 0, "t2": 0}                 # how many locks each has acquired
    held = {}                                # lock -> owner
    for txn in schedule:
        if pos[txn] >= len(plans[txn]):
            continue                          # this transaction is already finished
        want = plans[txn][pos[txn]]
        owner = held.get(want)
        if owner is None or owner == txn:
            held[want] = txn                  # acquire it (or already own it)
            pos[txn] += 1
            if pos[txn] == len(plans[txn]):   # finished: release everything it held
                held = {lk: o for lk, o in held.items() if o != txn}
        # else: the lock is held by the other transaction -> this step blocks and makes no progress
    blocked = {t: (pos[t] < len(plans[t]) and held.get(plans[t][pos[t]]) not in (None, t)) for t in plans}
    return "deadlock" if blocked["t1"] and blocked["t2"] else "ok"
```

Running one bad interleaving shows the cycle forming, and counting all of them shows how common it is.

```text filename=lockorder.py --race
RACE — the naive plans (t1 wants ['A', 'B'], t2 wants ['B', 'A'])
------------------------------------------------------------
  a deadlocking interleaving: ['t1', 't2', 't1', 't2']
    t1 acquires A, t2 acquires B
    t1 now waits for B (held by t2); t2 waits for A (held by t1)
    wait-for graph: t1 -> t2 -> t1  (a cycle: deadlock)
  deadlocking interleavings: 4 of 6
------------------------------------------------------------
  the two acquire the shared locks in opposite order, so each can hold what the other needs
```

Four of the six possible interleavings deadlock — this is not a rare corner case but the majority outcome. The fix sorts each transaction's requests into the global order before acquiring.

```python filename=modules/orchestration-and-governance/code/lockorder-inter-01/lockorder.py:31-33 COMPLETE
def in_canonical_order(plan, locks):
    """Sort a transaction's lock requests into the global order -- the discipline that prevents deadlock."""
    return sorted(plan, key=lambda lock: locks.index(lock))
```

With both plans sorted, every interleaving completes.

```text filename=lockorder.py --ordered
ORDERED — both plans sorted into the canonical order ['A', 'B']
------------------------------------------------------------
  t1 now acquires ['A', 'B'], t2 now acquires ['A', 'B']  (same order)
  whoever takes A first gets B next unobstructed; the other waits for A, then proceeds
  deadlocking interleavings: 0 of 6
------------------------------------------------------------
  no interleaving deadlocks: a wait-for cycle would need the forbidden reverse order
```

The figure contrasts the two plan sets and their deadlock counts.

<svg role="img" aria-label="Two panels. The naive panel shows t1 acquiring A then B and t2 acquiring B then A, opposite orders, with 4 of 6 interleavings deadlocking. The ordered panel shows both t1 and t2 acquiring A then B, the same order, with 0 of 6 deadlocking" viewBox="0 0 640 220">
<text x="160" y="28" fill="var(--ink)" font-size="12" text-anchor="middle">naive plans</text>
<text x="70" y="70" fill="var(--muted)" font-size="11">t1:</text>
<rect x="100" y="56" width="40" height="24" fill="var(--panel)" stroke="var(--line)" rx="4"/>
<text x="120" y="73" fill="var(--ink)" font-size="11" text-anchor="middle">A</text>
<rect x="150" y="56" width="40" height="24" fill="var(--panel)" stroke="var(--line)" rx="4"/>
<text x="170" y="73" fill="var(--ink)" font-size="11" text-anchor="middle">B</text>
<text x="70" y="110" fill="var(--muted)" font-size="11">t2:</text>
<rect x="100" y="96" width="40" height="24" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="4"/>
<text x="120" y="113" fill="var(--ink)" font-size="11" text-anchor="middle">B</text>
<rect x="150" y="96" width="40" height="24" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="4"/>
<text x="170" y="113" fill="var(--ink)" font-size="11" text-anchor="middle">A</text>
<text x="160" y="160" fill="var(--s2)" font-size="13" text-anchor="middle">4 of 6 deadlock</text>
<text x="490" y="28" fill="var(--ink)" font-size="12" text-anchor="middle">ordered plans</text>
<text x="400" y="70" fill="var(--muted)" font-size="11">t1:</text>
<rect x="430" y="56" width="40" height="24" fill="var(--panel)" stroke="var(--line)" rx="4"/>
<text x="450" y="73" fill="var(--ink)" font-size="11" text-anchor="middle">A</text>
<rect x="480" y="56" width="40" height="24" fill="var(--panel)" stroke="var(--line)" rx="4"/>
<text x="500" y="73" fill="var(--ink)" font-size="11" text-anchor="middle">B</text>
<text x="400" y="110" fill="var(--muted)" font-size="11">t2:</text>
<rect x="430" y="96" width="40" height="24" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="4"/>
<text x="450" y="113" fill="var(--ink)" font-size="11" text-anchor="middle">A</text>
<rect x="480" y="96" width="40" height="24" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="4"/>
<text x="500" y="113" fill="var(--ink)" font-size="11" text-anchor="middle">B</text>
<text x="490" y="160" fill="var(--s1)" font-size="13" text-anchor="middle">0 of 6 deadlock</text>
</svg>
^ Only the second row changed — t2 now acquires A before B like t1 — and the deadlock count falls from four to zero.

**Nothing about the locks, the transactions, or the scheduler changed between 4 of 6 and 0 of 6; the entire difference is that t2 now takes A before B.**

## Build

The self-test ties the outcome to its cause: the naive plans conflict in order and deadlock, sorting makes them agree, and the agreed plans deadlock on none.

```python filename=modules/orchestration-and-governance/code/lockorder-inter-01/lockorder.py:104-113 COMPLETE
    naive_orders_conflict = [locks.index(x) for x in p1] != [locks.index(x) for x in p2]
    print("  the two naive plans acquire the shared locks in opposite order = %s (%s vs %s)" % (naive_orders_conflict, p1, p2))

    naive_can_deadlock = deadlock_count(p1, p2) > 0
    print("  the naive plans deadlock on some interleaving = %s (%d of %d)" % (naive_can_deadlock, deadlock_count(p1, p2), total))

    ordering_makes_plans_agree = o1 == o2
    print("  sorting into the canonical order makes both acquire in the same order = %s (%s == %s)" % (ordering_makes_plans_agree, o1, o2))

    ordered_never_deadlocks = deadlock_count(o1, o2) == 0
    print("  the ordered plans deadlock on no interleaving = %s (%d of %d)" % (ordered_never_deadlocks, deadlock_count(o1, o2), total))
```

Those counts come from `deadlock_count`, which runs the simulator over every interleaving and tallies the deadlocks — so "0 of 6" is exhaustive, not a lucky sample.

```python filename=modules/orchestration-and-governance/code/lockorder-inter-01/lockorder.py:61-63 COMPLETE
def deadlock_count(plan1, plan2):
    """How many of the interleavings deadlock under these two plans."""
    return sum(1 for s in all_interleavings() if simulate(plan1, plan2, s) == "deadlock")
```

Running the check turns all five flags green.

```text filename=lockorder.py --check
SELF-TEST — the naive plans deadlock on some interleavings because the two acquire the shared locks in opposite order, and the ordered plans deadlock on none
----------------------------------------------------------------------------------------------------------------
  the two naive plans acquire the shared locks in opposite order = True (['A', 'B'] vs ['B', 'A'])
  the naive plans deadlock on some interleaving = True (4 of 6)
  sorting into the canonical order makes both acquire in the same order = True (['A', 'B'] == ['A', 'B'])
  the ordered plans deadlock on no interleaving = True (0 of 6)
  imposing the order removed the deadlock entirely rather than recovering from it = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  naive_orders_conflict=True  naive_can_deadlock=True  ordering_makes_plans_agree=True  ordered_never_deadlocks=True  prevention_beats_detection=True
```

**The check enumerates every interleaving rather than trying one, so "0 of 6" is a proof over this fixture's whole schedule space, not an observation that it happened to survive one run.**

## Definition of done

You are done when every code path that holds more than one lock at a time acquires them in a single, globally agreed order — so no two paths can ever request the same locks in opposite orders.

The order itself can be anything total and stable: lock names sorted lexically, object ids sorted numerically, a fixed rank assigned to each lock class. What matters is that it is the same everywhere and applied without exception. In practice you enforce it by sorting the set of locks a transaction needs before it starts acquiring, and by code review or tooling that flags a nested acquisition taken out of rank order. When you genuinely cannot know all the locks up front — you discover the second lock only after inspecting data behind the first — the ordering discipline breaks down, and that is exactly the case where you fall back to a detector or a try-lock-and-back-off protocol.

<svg role="img" aria-label="A number line ranking the locks A at rank 1 and B at rank 2, with a rule that both transactions sort their needed locks into this order before acquiring, producing an acyclic wait-for graph" viewBox="0 0 640 170">
<line x1="80" y1="70" x2="420" y2="70" stroke="var(--line)" stroke-width="1"/>
<circle cx="140" cy="70" r="6" fill="var(--ink)"/>
<text x="140" y="55" fill="var(--ink)" font-size="12" text-anchor="middle">A</text>
<text x="140" y="94" fill="var(--muted)" font-size="10" text-anchor="middle">rank 1</text>
<circle cx="360" cy="70" r="6" fill="var(--ink)"/>
<text x="360" y="55" fill="var(--ink)" font-size="12" text-anchor="middle">B</text>
<text x="360" y="94" fill="var(--muted)" font-size="10" text-anchor="middle">rank 2</text>
<text x="250" y="40" fill="var(--muted)" font-size="11" text-anchor="middle">acquire low rank first &#8594;</text>
<rect x="450" y="45" width="160" height="50" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="530" y="66" fill="var(--ink)" font-size="11" text-anchor="middle">sort locks by rank</text>
<text x="530" y="82" fill="var(--muted)" font-size="10" text-anchor="middle">before acquiring</text>
<text x="250" y="130" fill="var(--muted)" font-size="11" text-anchor="middle">every transaction obeys the same ranking → wait-for graph stays acyclic</text>
</svg>
^ Give each lock a global rank and always acquire low-to-high; because no one ever holds a high-rank lock while waiting for a low-rank one, the graph cannot cycle.

**Detection and timeouts answer "we deadlocked, now what"; a global lock order answers "we cannot deadlock" — and the second is worth reaching for first, because the only cost is agreeing on an order.**

## Boss fight

Your turn: scale the problem and watch the guarantee hold. Add a lock C and a third transaction, and set up three transactions that each grab two of {A, B, C} in a rotation — t1 wants A,B; t2 wants B,C; t3 wants C,A. This is the three-way version of the cycle, and simulating it, some interleavings deadlock with a three-node wait-for cycle t1 → t2 → t3 → t1. Now sort every transaction's pair into the canonical order A, B, C and simulate again: zero deadlocks, because the same argument scales — a cycle would need someone holding a higher-ranked lock while waiting on a lower one, and no one ever does.

Then find where the discipline cannot reach. Suppose a transaction does not know it needs the second lock until it has read the row the first lock protects — hand-over-hand locking down a linked structure, or a lock whose identity depends on data behind another lock. You cannot sort a set you do not yet know, so the global-order rule has nothing to sort. This is the real boundary: lock ordering prevents deadlock exactly when the lock set is known in advance, and when it is not, you are back to detection, a try-lock that backs off and retries on failure, or restructuring the access so the locks can be discovered and sorted up front. Knowing which regime you are in is the actual skill; the ordering rule is only the easy case, but it is the case you should engineer toward.

**Lock ordering is the cheapest deadlock cure precisely because it is preventive, but it buys that cheapness with a precondition — you must know the locks before you take them — so the engineering goal is to arrange your code to meet that precondition rather than to abandon ordering when it is inconvenient.**

## External resources

The dining philosophers problem is the canonical illustration of this exact fix — the standard resource-hierarchy solution has one philosopher pick up the lower-numbered fork first, which is lock ordering under another name.

Coffman, Elphick, and Shoshani's classic statement of the four necessary conditions for deadlock (mutual exclusion, hold-and-wait, no preemption, circular wait) names circular wait as the condition a global lock order removes — a good frame for why prevention targets one condition.

The Linux kernel's lockdep documentation describes a production tool that records lock-acquisition orders at runtime and warns when any two are taken in inconsistent orders, which is the ordering discipline of this module enforced automatically across a very large codebase.
