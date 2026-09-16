---
id: govern-inter-20
title: Use a vector clock to tell concurrency from causality — a single Lamport number invents an order
topic: orchestration-and-governance
level: intermediate
status: ready
time: 20 min
summary: A Lamport clock gives every event one number and guarantees a send has a smaller number than its receive — enough for a total order that never contradicts causality, but the number throws away information. If event A has a smaller Lamport number than B, you cannot tell whether A really happened-before B or whether the two are concurrent and their numbers merely landed that way. Any logic that reads that order as causation acts on a fiction. A vector clock keeps what Lamport discards — one counter per process. A process increments its own on every event and stamps messages with the whole vector; on receipt it takes the element-wise max, then increments its own. Now A happened-before B exactly when A's vector is ≤ B's, and when neither vector is ≤ the other the events are concurrent. On a two-process log, the vector clock marks the send→receive pair as ordered and a cross-process pair as concurrent, where a Lamport number would falsely sequence them.
eli5: A single tie-breaking number can always put two events in some order, even when they had nothing to do with each other — like alphabetizing two strangers and then claiming one influenced the other. A vector clock instead keeps a little scoreboard with one column per person, so it can say "these two events knew about each other" or "these two happened in totally separate corners and neither caused the other." It can admit that some things are simply unrelated.
---

## Why this module

Squeezing every event onto one number buys a tidy total order at the cost of a distinction you often need: whether two events are causally related or merely unrelated.

A Lamport clock stamps each event with a single integer and guarantees the one property causality demands — a message's send has a smaller stamp than its receive. That gives a consistent total order. But a total order is more than causality actually provides: many events are concurrent, happening on different processes with no message linking them, and there is no true "before" between them. Lamport's single number papers over this. When A's number is below B's, you cannot recover whether A caused B or the two are independent and their numbers just fell in that order. Systems that resolve conflicts by "which happened first" then treat two unrelated writes as ordered, discarding one for no reason.

**A single number can always order two events, so it cannot represent the honest answer that two events are concurrent — that information was thrown away when causality was flattened to an integer.**

A vector clock keeps it. Each process tracks a counter for every process, so an event's stamp records how much it knows of each process's history. Compare two vectors element-wise: one is before the other only if it is ≤ in every component, and if neither dominates, they are concurrent — and the clock says so. This module builds vector clocks on a two-process log and finds the concurrency a Lamport number would hide.

## Concepts

A **vector clock** is a list with one counter per process. Event stamps are compared element-wise, not as single numbers.

The **rules** are three. On any event, a process increments its own component. On sending, it attaches its whole vector to the message. On receiving, it sets each component to the **element-wise maximum** of its own vector and the message's, then increments its own — absorbing everything the sender knew plus this new event.

The **relation** between two vectors is read directly: A **happened-before** B if A ≤ B in every component (and they differ); A is **after** B if the reverse; and if **neither** is ≤ the other, A and B are **concurrent**. This is a partial order — it leaves unrelated events unordered, which is the truth.

The contrast with Lamport is exact. Lamport's single number is consistent with causality (A before B implies Lamport(A) < Lamport(B)) but not equivalent to it — the converse fails, so a smaller number does not mean "before." The vector clock's comparison is equivalent to causality in both directions, which is why it, and only it, detects concurrency.

**A vector clock's element-wise order is causality itself: ≤ in all components means happened-before, incomparable means concurrent — the partial order Lamport's total order flattened away.**

Flattening a vector to one number is a projection that loses a dimension: two points that are incomparable in the plane can collapse to different values on a single line, manufacturing an order that was never there.

<svg role="img" aria-label="Two incomparable points in a 2D plane project onto a single number line at different positions, creating a false order" viewBox="0 0 300 110" width="300" height="110">
  <line x1="30" y1="80" x2="30" y2="15" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="80" x2="160" y2="80" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="120" cy="72" r="4" fill="var(--s2)"/><text x="100" y="66" fill="var(--s2)" font-size="7">e2 [2,0]</text>
  <circle cx="38" cy="30" r="4" fill="var(--s1)"/><text x="44" y="28" fill="var(--s1)" font-size="7">e3 [0,1]</text>
  <text x="35" y="100" fill="var(--muted)" font-size="7">2D: incomparable</text>
  <line x1="185" y1="50" x2="285" y2="50" stroke="var(--ink)" stroke-width="1.5"/>
  <circle cx="215" cy="50" r="4" fill="var(--s1)"/><text x="200" y="42" fill="var(--s1)" font-size="7">e3=1</text>
  <circle cx="245" cy="50" r="4" fill="var(--s2)"/><text x="240" y="42" fill="var(--s2)" font-size="7">e2=2</text>
  <text x="185" y="70" fill="var(--muted)" font-size="7">1D Lamport: false order 1 &lt; 2</text>
</svg>
^ In two dimensions e2 and e3 are incomparable; projecting each to a single Lamport number puts them at 1 and 2, inventing an order the plane never had.

The cost is size: a vector grows with the number of processes, where a Lamport clock is always one number. You pay that space to recover concurrency detection.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/govern-inter-20/vector.py

The fixture is a four-event log: p1 acts then sends, p2 acts independently then receives.

```json filename=modules/orchestration-and-governance/code/govern-inter-20/events.json:1-13 COMPLETE
{
  "_meta": "An event log from two processes (p1, p2), listed in an order consistent with causality. kind is local, send, or recv; msg links a send to the recv that receives it. A vector clock keeps one counter per process: a process increments its own on every event, attaches the whole vector to a message, and on receipt takes the element-wise max with the message's vector then increments its own. Two events are CONCURRENT when neither vector is <= the other. The question: which event pairs are causally ordered, and which only look ordered under a single Lamport number?",
  "procs": ["p1", "p2"],
  "events": [
    {"id": "e1", "proc": "p1", "kind": "local"},
    {"id": "e2", "proc": "p1", "kind": "send", "msg": "m1"},
    {"id": "e3", "proc": "p2", "kind": "local"},
    {"id": "e4", "proc": "p2", "kind": "recv", "msg": "m1"}
  ]
}
```

The clock loop applies the three rules; the relation function compares two vectors element-wise.

```python filename=modules/orchestration-and-governance/code/govern-inter-20/vector.py:47-72 COMPLETE
    for e in events:
        p = e["proc"]
        if e["kind"] == "recv":
            mv, ml = sent[e["msg"]]
            clock[p] = [max(clock[p][i], mv[i]) for i in range(len(procs))]
            lam[p] = max(lam[p], ml)
        clock[p][idx[p]] += 1                      # increment own component
        lam[p] += 1
        stamp[e["id"]] = list(clock[p])
        lamport[e["id"]] = lam[p]
        if e["kind"] == "send":
            sent[e["msg"]] = (list(clock[p]), lam[p])
    return stamp, lamport


def relation(a, b):
    """Causal relation of vectors a and b: 'before', 'after', 'equal', or 'concurrent'."""
    le = all(a[i] <= b[i] for i in range(len(a)))
    ge = all(a[i] >= b[i] for i in range(len(a)))
    if le and ge:
        return "equal"
    if le:
        return "before"
    if ge:
        return "after"
    return "concurrent"
```

The clocks view stamps each event by the rules and prints its vector next to its Lamport number.

```python filename=modules/orchestration-and-governance/code/govern-inter-20/vector.py:77-85 COMPLETE
def clocks_view(data):
    stamp, lam = vector_clocks(data["procs"], data["events"])
    print("CLOCKS — vector clock and Lamport number per event (procs %s)" % data["procs"])
    print("-" * 58)
    for e in data["events"]:
        tag = "  msg=%s" % e["msg"] if "msg" in e else ""
        print("  %-4s %-5s %-5s  vector %s   Lamport %d%s" % (e["id"], e["proc"], e["kind"], stamp[e["id"]], lam[e["id"]], tag))
    print("-" * 58)
    print("  the receive takes the element-wise max, then bumps its own counter.")
```

Run `--clocks` for the stamp on each event.

```text filename=--clocks
CLOCKS — vector clock and Lamport number per event (procs ['p1', 'p2'])
----------------------------------------------------------
  e1   p1    local  vector [1, 0]   Lamport 1
  e2   p1    send   vector [2, 0]   Lamport 2  msg=m1
  e3   p2    local  vector [0, 1]   Lamport 1
  e4   p2    recv   vector [2, 2]   Lamport 3  msg=m1
----------------------------------------------------------
  the receive takes the element-wise max, then bumps its own counter.
```

p1's events carry [1,0] and [2,0] — it has seen two of its own events and none of p2's. p2's local event is [0,1] — one of its own, none of p1's. The receive e4 is [2,2]: it took the max of its own [0,1] and the message's [2,0], giving [2,1], then bumped its own to [2,2]. That [2,0] inside e4's vector is the record that e4 knows about e2.

<svg role="img" aria-label="Two process timelines with vectors: p1 has [1,0] and [2,0], p2 has [0,1] then receives m1 to become [2,2]" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="22" fill="var(--muted)" font-size="9">p1</text>
  <line x1="40" y1="30" x2="285" y2="30" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="90" cy="30" r="3" fill="var(--s2)"/><text x="72" y="22" fill="var(--muted)" font-size="7">e1 [1,0]</text>
  <circle cx="160" cy="30" r="3" fill="var(--s2)"/><text x="145" y="22" fill="var(--s2)" font-size="7">e2 [2,0]</text>
  <text x="10" y="92" fill="var(--muted)" font-size="9">p2</text>
  <line x1="40" y1="100" x2="285" y2="100" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="90" cy="100" r="3" fill="var(--s1)"/><text x="70" y="114" fill="var(--s1)" font-size="7">e3 [0,1]</text>
  <circle cx="240" cy="100" r="3" fill="var(--s2)"/><text x="222" y="114" fill="var(--muted)" font-size="7">e4 [2,2]</text>
  <line x1="160" y1="33" x2="240" y2="97" stroke="var(--ink)" stroke-width="1.5"/><text x="185" y="60" fill="var(--muted)" font-size="7">m1 carries [2,0]</text>
</svg>
^ The message from e2 carries p1's vector into e4, so e4's [2,2] contains p1's count of 2 — a record of causal contact that e3, off to the side, never received.

## Build

Now ask how the pairs relate with `--relate`.

```text filename=--relate
RELATE — causal relation of event pairs (vector) vs their Lamport numbers
----------------------------------------------------------------
  e2 [2, 0] vs e4 [2, 2] -> before      (Lamport 2 vs 3)
  e2 [2, 0] vs e3 [0, 1] -> concurrent  (Lamport 2 vs 1)
  e1 [1, 0] vs e3 [0, 1] -> concurrent  (Lamport 1 vs 1)
----------------------------------------------------------------
  concurrent pairs have incomparable vectors but still differ in Lamport.
```

e2 → e4 is before: [2,0] ≤ [2,2] in both components, the causal send-to-receive link. But e2 vs e3 is concurrent: [2,0] and [0,1] — 2 > 0 in the first slot, 0 < 1 in the second, so neither dominates, and there is genuinely no causal order between them. The Lamport column is the trap: it gives e3 a 1 and e2 a 2, which would order e3 before e2 — a sequencing of two events that never influenced each other. The vector clock refuses to invent that order.

<svg role="img" aria-label="e2 [2,0] and e3 [0,1] are incomparable: each is larger in one coordinate, so neither dominates" viewBox="0 0 300 120" width="300" height="120">
  <line x1="40" y1="100" x2="40" y2="15" stroke="var(--grid)" stroke-width="1"/>
  <line x1="40" y1="100" x2="285" y2="100" stroke="var(--grid)" stroke-width="1"/>
  <text x="10" y="60" fill="var(--muted)" font-size="8">p2</text>
  <text x="150" y="115" fill="var(--muted)" font-size="8">p1 →</text>
  <circle cx="230" cy="100" r="4" fill="var(--s2)"/><text x="200" y="94" fill="var(--s2)" font-size="8">e2 [2,0]</text>
  <circle cx="40" cy="40" r="4" fill="var(--s1)"/><text x="48" y="38" fill="var(--s1)" font-size="8">e3 [0,1]</text>
  <line x1="230" y1="100" x2="40" y2="40" stroke="var(--line)" stroke-width="1" stroke-dasharray="3 2"/>
  <text x="95" y="66" fill="var(--muted)" font-size="7">neither point is up-and-right of the other → concurrent</text>
</svg>
^ Plotted by their two components, e2 and e3 each lead in one axis and trail in the other, so neither dominates — the geometric picture of concurrency a scalar clock cannot express.

## Definition of done

The self-test pins the distinction: the send precedes its receive, e2 and e3 are concurrent, a Lamport number would still order that concurrent pair, the receive vector is the element-wise max plus increment, and another cross-process pair is also concurrent.

```python filename=modules/orchestration-and-governance/code/govern-inter-20/vector.py:105-117 COMPLETE
    send_before_recv = relation(stamp["e2"], stamp["e4"]) == "before"
    print("  the send causally precedes its receive = %s (e2 %s before e4 %s)" % (send_before_recv, stamp["e2"], stamp["e4"]))

    concurrent_pair = relation(stamp["e2"], stamp["e3"]) == "concurrent"
    print("  e2 and e3 are concurrent = %s (%s vs %s, neither <= the other)" % (concurrent_pair, stamp["e2"], stamp["e3"]))

    lamport_would_order_them = lam["e2"] != lam["e3"]
    print("  a single Lamport number would order that concurrent pair = %s (e3 %d < e2 %d implies e3 first)" % (lamport_would_order_them, lam["e3"], lam["e2"]))

    receive_took_max = stamp["e4"] == [max(stamp["e2"][0], stamp["e3"][0]), stamp["e3"][1] + 1]
    print("  the receive vector is the element-wise max plus own increment = %s (%s)" % (receive_took_max, stamp["e4"]))

    another_concurrent = relation(stamp["e1"], stamp["e3"]) == "concurrent"
    print("  e1 and e3 are also concurrent = %s" % another_concurrent)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the vector clock finds a concurrent pair that a single Lamport number would falsely order
--------------------------------------------------------------------------------------------------------
  the send causally precedes its receive = True (e2 [2, 0] before e4 [2, 2])
  e2 and e3 are concurrent = True ([2, 0] vs [0, 1], neither <= the other)
  a single Lamport number would order that concurrent pair = True (e3 1 < e2 2 implies e3 first)
  the receive vector is the element-wise max plus own increment = True ([2, 2])
  e1 and e3 are also concurrent = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  send_before_recv=True  concurrent_pair=True  lamport_would_order_them=True  receive_took_max=True  another_concurrent=True
```

**Done means the concurrency is detected, not assumed: e2's [2,0] and e3's [0,1] are provably incomparable, so the vector clock reports concurrent exactly where the Lamport numbers 2 and 1 would have imposed an order.**

## Boss fight

Vector clocks detect concurrency. Predict whether that makes them the right choice for every distributed system that needs ordering. It is tempting to always reach for the more powerful clock.

The power costs space, and the space grows with the system. A vector clock has one component per process, so in a system with thousands of processes each stamp is a thousand-entry vector attached to every message and stored with every event — versus a Lamport clock's single integer. When you only need a consistent total order and never need to ask "are these concurrent," a Lamport clock is far cheaper and sufficient. Vector clocks earn their size only where concurrency detection matters — conflict resolution in a replicated store, causal consistency, debugging distributed traces — which is why real systems use variants (version vectors, dotted version vectors) that bound or prune the size.

The mirror-image mistake is thinking vector clocks give you a total order for free. They give a partial order, and concurrent events are deliberately unordered — that is the feature. If you then need a single sequence (to write to a log, say), you must break ties among concurrent events with some deterministic rule (process ID, for instance). The vector clock tells you which ties are real concurrency you are free to break arbitrarily, versus which orderings are causal and must be respected — a distinction the tie-break needs and a Lamport number cannot supply.

```python filename=modules/orchestration-and-governance/code/govern-inter-20/vector.py:62-72 COMPLETE
def relation(a, b):
    """Causal relation of vectors a and b: 'before', 'after', 'equal', or 'concurrent'."""
    le = all(a[i] <= b[i] for i in range(len(a)))
    ge = all(a[i] >= b[i] for i in range(len(a)))
    if le and ge:
        return "equal"
    if le:
        return "before"
    if ge:
        return "after"
    return "concurrent"
```

**Use a vector clock when you must distinguish causally-related events from concurrent ones — its element-wise order is causality itself — and accept the per-process size, falling back to a Lamport number when a cheap total order is all you need.**

## External resources

Fidge (1988) and Mattern (1989) — the independent inventions of vector clocks and the happened-before-iff-vector-order result this module computes.

The companion Lamport-clock module — its boss fight names this exact gap (a smaller number does not mean "before"); vector clocks are the answer.

The "Designing Data-Intensive Applications" (Kleppmann) chapter on concurrent writes and version vectors — how vector-clock ideas resolve conflicts in replicated databases, and how their size is kept manageable in practice.
