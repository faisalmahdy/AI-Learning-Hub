---
id: vectorclock-inter-01
title: Compare writes with vector clocks, not timestamps — last-write-wins silently drops one of two concurrent edits
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: When a value is replicated and two clients update it at nearly the same time on different replicas, you end up with two versions and must decide what happened. The easy rule is last-write-wins — keep the version with the later wall-clock timestamp, discard the other — and it is wrong exactly when it matters: when the two writes were concurrent, neither aware of the other. Those are not a newer-and-older pair but a genuine conflict, two independent edits that both deserve to survive, and a timestamp cannot tell a concurrent conflict from a legitimate overwrite because it only orders events, never says whether one causally depended on the other. So last-write-wins silently drops one edit — a lost update — and reports success. A vector clock carries the missing information: one counter per node, recording how many updates from each node the writer had seen. Comparing two clocks reveals the causal relationship directly — if every component of X is ≤ Y (and one strictly less) then X happened-before Y and Y supersedes it; if the ordering holds in neither direction, each clock ahead of the other on some node, the writes are concurrent, a true conflict. With conflicts detected instead of hidden, the system keeps both siblings and lets the application reconcile them, and a later write that descends from both dominates them, marking the conflict resolved. On a fixture where w1 (A's "apple", clock {A:1,B:0}) and w2 (B's "banana", clock {A:0,B:1}) are concurrent, last-write-wins keeps w2 (later wall time) and drops "apple", while vector clocks flag the conflict, keep both, and recognize w3 ("apple,banana", {A:1,B:1}) as the merge that causally dominates both.
eli5: Imagine you and a friend both have a copy of the same shopping list, and at the same moment — without talking — you add "apples" to yours and your friend adds "bananas" to theirs. Later you try to combine the lists. If your rule is "whoever wrote most recently wins," you keep only one list and throw the other away, so one of the two items just vanishes even though you both clearly meant to add something. The smarter way is to have each list remember what it had seen when it was written. Then you can tell that neither of you saw the other's change — you made your edits independently — so instead of throwing one away, you keep both and merge them into "apples, bananas." And once someone writes a combined list that clearly came after seeing both, everyone knows the disagreement is settled.
---

## Why this module

Replication forces a decision that single-copy systems never face: when the same value has been written in two places, which write is the truth? The tempting answer is the one with the newer timestamp — last-write-wins — because it always yields a single, clean result and requires nothing but a clock. It is also the answer that silently destroys data, and it does so precisely in the case a replicated system exists to handle: two users making genuine, independent edits at the same time.

The failure is a category error hiding inside a timestamp. A wall-clock time tells you which of two writes happened later on the clock, but it tells you nothing about whether the later writer had seen the earlier write. Those are different questions. A legitimate overwrite — someone edits a value they just read — and a concurrent conflict — two people edit the same value without seeing each other — can produce the exact same pair of timestamps. Last-write-wins treats them identically, keeping the later and dropping the earlier, so in the conflict case it throws away an edit that had every right to survive, and reports success while doing it.

A vector clock records the one thing the timestamp omits: causal history. This module compares three writes both ways — by wall-clock resolution and by vector-clock relationship — and shows the conflict last-write-wins hides.

**Compare replicated writes with vector clocks and treat clocks ordered in neither direction as concurrent conflicts to be kept and reconciled, rather than resolving versions by last-write-wins on a wall-clock timestamp, because a timestamp cannot distinguish a concurrent conflict from a causal overwrite, so last-write-wins silently discards one of two independent edits.**

## Concepts

The fixture is three writes to one replicated key across two nodes, A and B. w1 is A adding "apple" — its clock {A:1,B:0} says A had made one update and seen none of B's. w2 is B adding "banana" at the same time, having not seen w1 — clock {A:0,B:1}. w3 is a client that read both and wrote the merge "apple,banana" — clock {A:1,B:1}. Each write also carries a wall-clock time, which is all last-write-wins uses.

```json filename=modules/orchestration-and-governance/code/vectorclock-inter-01/vectorclock.json:14-18 COMPLETE
  "writes": [
    {"id": "w1", "clock": {"A": 1, "B": 0}, "value": "apple", "wall": 100},
    {"id": "w2", "clock": {"A": 0, "B": 1}, "value": "banana", "wall": 105},
    {"id": "w3", "clock": {"A": 1, "B": 1}, "value": "apple,banana", "wall": 110}
  ]
```

The comparison is the whole idea. Two clocks are ordered — one happened-before the other — only if every component obeys the same direction; if each is ahead of the other on some node, they are concurrent.

```python filename=modules/orchestration-and-governance/code/vectorclock-inter-01/vectorclock.py:52-73 COMPLETE
def compare(c1, c2, nodes):
    """Vector-clock relationship: 'before', 'after', 'equal', or 'concurrent'."""
    le = all(c1[n] <= c2[n] for n in nodes)
    ge = all(c1[n] >= c2[n] for n in nodes)
    if le and ge:
        return "equal"
    if le:
        return "before"
    if ge:
        return "after"
    return "concurrent"


def concurrent_pairs(writes, nodes):
    """All pairs of writes whose clocks are ordered in neither direction (true conflicts)."""
    out = []
    for i in range(len(writes)):
        for j in range(i + 1, len(writes)):
            if compare(writes[i]["clock"], writes[j]["clock"], nodes) == "concurrent":
                out.append((writes[i]["id"], writes[j]["id"]))
    return out
```

Last-write-wins is the naive resolver — the single latest wall time. And a dominating write is one whose clock is at least every other clock, meaning it causally follows them all: the resolution of a conflict, when one exists.

```python filename=modules/orchestration-and-governance/code/vectorclock-inter-01/vectorclock.py:76-89 COMPLETE
def lww_winner(writes):
    """Last-write-wins: the single write with the latest wall-clock time."""
    return max(writes, key=lambda w: (w["wall"], w["id"]))


def dominating(writes, nodes):
    """A write whose clock is >= every other write's clock -- a version that supersedes all others, if one exists."""
    for w in writes:
        if all(compare(w["clock"], o["clock"], nodes) in ("after", "equal") for o in writes):
            return w
    return None
```

<svg role="img" aria-label="A diagram: w1 at A:1,B:0 and w2 at A:0,B:1 shown side by side as neither ordering holds, with both arrows converging into w3 at A:1,B:1" viewBox="0 0 320 150">
  <rect x="20" y="20" width="90" height="26" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="28" y="37" font-size="10" fill="var(--ink)">w1 {A:1,B:0}</text>
  <rect x="210" y="20" width="90" height="26" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="218" y="37" font-size="10" fill="var(--ink)">w2 {A:0,B:1}</text>
  <text x="130" y="37" font-size="9" fill="var(--muted)">neither ≤ the other</text>
  <text x="140" y="52" font-size="8.5" fill="var(--ink)">→ concurrent</text>
  <rect x="115" y="100" width="95" height="26" fill="none" stroke="var(--ink)" stroke-width="2"/>
  <text x="123" y="117" font-size="10" fill="var(--ink)">w3 {A:1,B:1}</text>
  <line x1="65" y1="46" x2="140" y2="98" stroke="var(--s1)" stroke-width="1.3"/>
  <line x1="255" y1="46" x2="185" y2="98" stroke="var(--s2)" stroke-width="1.3"/>
  <text x="118" y="140" font-size="8.5" fill="var(--muted)">dominates both → conflict resolved</text>
</svg>
^ w1 and w2 are each ahead of the other on one node, so neither happened-before the other — concurrent. w3's clock is ≥ both on every node, so it causally follows both: the merge that resolves the conflict.

**A vector clock turns "which is newer?" into "did one see the other?" — and only the second question can tell a conflict from an overwrite.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the conflict-resolution step of a replicated store, reduced to three writes so every clock comparison is checkable by hand.

Run `--compare` to see the relationship of every pair.

```text filename=vectorclock.py --compare
  w1 {'A': 1, 'B': 0}  vs  w2 {'A': 0, 'B': 1}   ->  w1 || w2 (CONFLICT)
  w1 {'A': 1, 'B': 0}  vs  w3 {'A': 1, 'B': 1}   ->  w1 -> w3 (causal)
  w2 {'A': 0, 'B': 1}  vs  w3 {'A': 1, 'B': 1}   ->  w2 -> w3 (causal)
  concurrent (conflicting) pairs: [('w1', 'w2')]
```

w1 versus w2: on node A, w1 is ahead (1 vs 0); on node B, w2 is ahead (0 vs 1). Neither dominates, so they are concurrent — the `||` conflict. w1 versus w3: w3 is ≥ w1 on both nodes and strictly greater on B, so w1 happened-before w3 — causal, no conflict. Same for w2 versus w3. Exactly one conflicting pair, w1 and w2, and the comparison correctly declines to flag the two causal pairs.

Now `--resolve` applies both strategies to the concurrent writes.

```text filename=vectorclock.py --resolve
  last-write-wins: keeps w2 ('banana', wall 105), DROPS ['apple'] (lost update)
  vector clocks:   w1 || w2 concurrent -> keep BOTH as siblings for reconciliation
  merge: w3 ('apple,banana', clock {'A': 1, 'B': 1}) dominates w1 and w2 -> conflict resolved
```

Last-write-wins compares wall times — 105 beats 100 — keeps "banana", and drops "apple". The apple edit is gone, silently, and nothing records that a conflict ever happened. Vector clocks see the two clocks are concurrent, keep both as siblings, and hand the application a real conflict to reconcile. And w3, the client that read both siblings and wrote "apple,banana", has clock {A:1,B:1} that dominates both — so vector clocks recognize the merge as the causal successor and the conflict as resolved.

<svg role="img" aria-label="Componentwise comparison of w1 and w2: on node A w1 is greater, on node B w2 is greater, so neither dominates and they are concurrent" viewBox="0 0 320 120">
  <text x="10" y="20" font-size="9" fill="var(--muted)">component-by-component: w1 {A:1,B:0} vs w2 {A:0,B:1}</text>
  <text x="40" y="52" font-size="10" fill="var(--ink)">node A:</text>
  <text x="110" y="52" font-size="10" fill="var(--s1)">w1=1</text>
  <text x="160" y="52" font-size="10" fill="var(--muted)">&gt;</text>
  <text x="180" y="52" font-size="10" fill="var(--s2)">w2=0</text>
  <text x="240" y="52" font-size="8.5" fill="var(--s1)">w1 ahead</text>
  <text x="40" y="80" font-size="10" fill="var(--ink)">node B:</text>
  <text x="110" y="80" font-size="10" fill="var(--s1)">w1=0</text>
  <text x="160" y="80" font-size="10" fill="var(--muted)">&lt;</text>
  <text x="180" y="80" font-size="10" fill="var(--s2)">w2=1</text>
  <text x="240" y="80" font-size="8.5" fill="var(--s2)">w2 ahead</text>
  <text x="40" y="106" font-size="9" fill="var(--ink)">each ahead on one node → neither happened-before → concurrent</text>
</svg>
^ Ordering requires the same direction on every component. Here A favors w1 and B favors w2, so neither clock is ≤ the other — the definition of concurrent, and the exact case a single timestamp collapses into a false winner.

**On the same two writes, last-write-wins destroys the apple edit and reports success, while vector clocks preserve both edits and let the merge into w3 settle it — the timestamp hid a conflict the clocks surfaced.**

## Build

The self-test asserts the conflict, the data loss, and the correct handling: that w1 and w2 are concurrent, that last-write-wins keeps only one and that survivor is missing the other's value, and that vector clocks flag the conflict.

```python filename=modules/orchestration-and-governance/code/vectorclock-inter-01/vectorclock.py:110-124 COMPLETE
    w1_w2_concurrent = compare(w1["clock"], w2["clock"], nodes) == "concurrent"
    print("  w1 and w2 are concurrent (ordered in neither direction) = %s (%s vs %s)" % (w1_w2_concurrent, w1["clock"], w2["clock"]))

    win = lww_winner([w1, w2])
    lww_drops_one = win["id"] in ("w1", "w2") and len([w1, w2]) == 2
    print("  last-write-wins keeps only one of the two edits = %s (keeps %s, drops the other)" % (lww_drops_one, win["id"]))

    lww_loses_data = win["value"] != "apple,banana"
    print("  the last-write-wins survivor is missing the other edit = %s ('%s' has lost the concurrent value)" % (lww_loses_data, win["value"]))

    vclock_flags_conflict = ("w1", "w2") in concurrent_pairs(writes, nodes)
    print("  vector clocks flag w1 || w2 as a conflict (both kept) = %s" % vclock_flags_conflict)

    w3_dominates_both = compare(w1["clock"], w3["clock"], nodes) == "before" and compare(w2["clock"], w3["clock"], nodes) == "before"
    print("  w3 causally dominates both w1 and w2 (the merge) = %s (%s after both)" % (w3_dominates_both, w3["clock"]))
```

<svg role="img" aria-label="Two resolution paths: last-write-wins keeps banana and discards apple, vector clocks keep both apple and banana and then merge to apple-comma-banana" viewBox="0 0 320 130">
  <text x="10" y="20" font-size="9" fill="var(--s2)">last-write-wins</text>
  <rect x="10" y="28" width="70" height="20" fill="var(--muted)"/><text x="20" y="42" font-size="8.5" fill="var(--panel)">apple ✗</text>
  <rect x="88" y="28" width="70" height="20" fill="var(--s2)"/><text x="98" y="42" font-size="8.5" fill="var(--panel)">banana ✓</text>
  <text x="168" y="42" font-size="8" fill="var(--muted)">apple lost</text>
  <text x="10" y="76" font-size="9" fill="var(--s1)">vector clocks</text>
  <rect x="10" y="84" width="70" height="20" fill="var(--s1)"/><text x="24" y="98" font-size="8.5" fill="var(--panel)">apple ✓</text>
  <rect x="88" y="84" width="70" height="20" fill="var(--s1)"/><text x="98" y="98" font-size="8.5" fill="var(--panel)">banana ✓</text>
  <text x="164" y="98" font-size="11" fill="var(--muted)">→</text>
  <rect x="182" y="84" width="100" height="20" fill="var(--ink)"/><text x="190" y="98" font-size="8.5" fill="var(--panel)">apple,banana (w3)</text>
</svg>
^ Last-write-wins keeps one edit and discards the other. Vector clocks keep both siblings, and the merge write w3 — dominating both — combines them, so no edit is lost.

Running the check confirms every clause, including that the causal pairs are not misflagged.

```text filename=vectorclock.py --check
  w1 and w2 are concurrent (ordered in neither direction) = True ({'A': 1, 'B': 0} vs {'A': 0, 'B': 1})
  last-write-wins keeps only one of the two edits = True (keeps w2, drops the other)
  the last-write-wins survivor is missing the other edit = True ('banana' has lost the concurrent value)
  vector clocks flag w1 || w2 as a conflict (both kept) = True
  w3 causally dominates both w1 and w2 (the merge) = True ({'A': 1, 'B': 1} after both)
  vector clocks do NOT flag the causal pairs (w1->w3, w2->w3) as conflicts = True
```

**The check ties the lost update to the concurrency last-write-wins ignores and shows vector clocks both flagging the real conflict and sparing the causal pairs — detection that is neither blind nor trigger-happy.**

## Definition of done

Two properties close it. Vector clocks must flag the genuine conflict (w1 || w2) while not flagging the causal pairs (w1→w3, w2→w3) as conflicts — precision in both directions — and the dominating write w3 must be recognized as causally after both, so a resolved conflict is seen as resolved rather than re-flagged forever.

```python filename=modules/orchestration-and-governance/code/vectorclock-inter-01/vectorclock.py:126-129 COMPLETE
    causal_not_flagged = ("w1", "w3") not in concurrent_pairs(writes, nodes) and ("w2", "w3") not in concurrent_pairs(writes, nodes)
    print("  vector clocks do NOT flag the causal pairs (w1->w3, w2->w3) as conflicts = %s" % causal_not_flagged)

    ok = w1_w2_concurrent and lww_drops_one and lww_loses_data and vclock_flags_conflict and w3_dominates_both and causal_not_flagged
```

Two honest boundaries keep the tool from being oversold. First, vector clocks detect a conflict; they do not resolve it. Deciding what "apple" and "banana" merge to — union, a user prompt, a domain rule — is application logic the clocks cannot supply; their whole contribution is refusing to throw an edit away silently. Second, they cost storage: a vector clock has one entry per node that has ever written, so in a system with many transient clients the clocks grow, and real systems prune them (version vectors keyed on durable replicas rather than clients, or dotted version vectors) to keep them bounded. There is also a legitimate place for last-write-wins: when writes are genuinely idempotent or a deterministic tiebreak is acceptable (and losing one of two truly-simultaneous edits is fine), LWW's simplicity wins — the point is to choose it knowingly, not to reach for a timestamp and not realize it is discarding conflicts.

**Done means vector clocks flag the concurrent conflict, spare the causal pairs, and recognize the dominating merge — surfacing the conflict last-write-wins would have hidden, while leaving its resolution to the application.**

## Boss fight

A shopping-cart service replicated across regions uses last-write-wins to resolve conflicting cart updates. Users occasionally report that an item they added "disappeared," and it correlates with adding items quickly from two devices (a phone and a laptop). Support cannot reproduce it reliably. What is happening, and what change fixes the disappearing items without requiring a single primary region?

The two devices are writing to different replicas at nearly the same time, so their cart updates are concurrent — neither device's write saw the other's. Last-write-wins compares the two writes' timestamps, keeps the one with the later time, and discards the other, which is why an item added on the slower-to-arrive device "disappears": its edit lost a timestamp comparison it should never have been in, because the two edits were not a newer-and-older pair but a genuine concurrent conflict. It is intermittent and hard to reproduce because it only happens when two writes land close enough in time to be concurrent on different replicas. The fix is to stop resolving cart writes by timestamp and start comparing them with vector clocks (or version vectors): when two cart versions are concurrent, keep both as siblings instead of dropping one, and merge them with a cart-appropriate rule — union the items, since adding two different items should never lose either. That preserves both edits without needing a single primary region to serialize all writes, which is the whole reason the cart was replicated across regions in the first place. This is exactly how production carts (famously Dynamo's) handle it: detect concurrency, keep siblings, and merge carts by union so an add never vanishes.

## External resources

DeCandia et al., "Dynamo: Amazon's Highly Available Key-value Store" — the paper that popularized vector clocks (version vectors) for exactly this conflict-detection-and-sibling-reconciliation pattern, including the shopping-cart merge that motivates the boss fight.

Leslie Lamport's happens-before relation and the vector-clock formalization by Fidge and Mattern — the theory behind why a scalar timestamp gives only a total order while a vector clock captures the partial order of causality, and thus can detect concurrency that a timestamp cannot.
