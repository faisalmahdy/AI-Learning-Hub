---
id: govern-inter-18
title: Order events by a logical clock — or a skewed wall clock puts a message's receipt before its send
topic: orchestration-and-governance
level: intermediate
status: ready
time: 20 min
summary: Across machines, wall clocks disagree — each is set from its own source and drifts, so two clocks can be seconds apart. That is harmless until you use timestamps to order events from different machines. If the receiver's clock runs behind the sender's, a message can be stamped received at 95 when it was sent at 101: sort by wall clock and the receive precedes the send, an effect before its cause, and any logic that trusts the order is built on a lie. A Lamport logical clock fixes it without trusting wall time — each process increments a counter on every event, stamps outgoing messages with it, and on receive sets its counter to max(own, message) + 1 — guaranteeing a send always has a smaller stamp than its receive. On a two-process log where p2's clock is behind, wall-clock order puts recv m1 (95) before send m1 (101); Lamport order gives send m1 (2) before recv m1 (3).
eli5: Two friends with wrongly-set watches can't figure out who did what first by comparing watch times — one watch might say a reply came before the message it answers. Instead they use a rule: every time you do something, count up by one, and when you get a message, jump your count above the number on the message. Now the reply always has a bigger number than the message, so the order always makes sense, even though nobody's watch was right.
---

## Why this module

Using timestamps to order events across machines feels obvious and is quietly broken, because the clocks producing those timestamps do not agree.

Every machine keeps its own clock, set from its own source and drifting between syncs, so two machines' readings can differ by seconds or more. That skew is invisible while each machine only timestamps its own local events. It becomes a bug the moment you merge events from several machines and sort by timestamp. If the receiver's clock lags the sender's, a message is stamped as received at a wall time earlier than it was sent — and sorted output shows the receive before the send. That is causally impossible, an effect before its cause, and every downstream decision that trusts the order — last-writer-wins, what-happened-first, which update supersedes which — inherits the error. Tightening clock sync narrows the window but never closes it, because clocks can always skew between syncs.

**Wall-clock time answers "what time was it on that machine," which is not the same question as "what happened before what" — and only the second one is what ordering needs.**

A Lamport logical clock answers the second question directly. Each process keeps a counter, bumps it on every event, stamps outgoing messages, and on receipt jumps its counter past the message's — guaranteeing send-before-receive. This module orders one skewed event log both ways and shows the wall-clock ordering violate causality while the logical one preserves it.

## Concepts

A **wall clock** is a machine's real-time-of-day reading. Across machines these are unsynchronized to within their skew, so comparing them across machines is unsafe.

A **Lamport clock** is a per-process integer counter. The rules are three: increment on every local event; attach the counter's value to every message sent; on receiving a message, set the counter to max(local counter, message's stamp) + 1, then that value stamps the receive.

The **guarantee** those rules buy is the clock condition: if event A causally precedes event B, then Lamport(A) < Lamport(B). The critical case is a message — the receive's max-plus-one step forces its stamp strictly above the send's, so a send always precedes its receive in Lamport order. Causality is never inverted.

What a Lamport clock does not give is the converse: two events with Lamport(A) < Lamport(B) are not necessarily causally related — they may be concurrent, on different processes, and the counters merely happened to land that way. Lamport order is a valid total order consistent with causality, not a detector of causality; vector clocks are needed for that.

**A logical clock tracks "happened-before," not "what time it was" — it sacrifices real time to guarantee the one property ordering actually requires.**

The whole guarantee lives in one step: on receive, jump the counter past the message's stamp, so the receive can never tie or trail its send.

<svg role="img" aria-label="A receiver's counter at 0 jumps to max(0, incoming stamp 2) plus 1 equals 3, above the send's stamp of 2" viewBox="0 0 300 110" width="300" height="110">
  <rect x="20" y="35" width="60" height="24" fill="none" stroke="var(--line)" stroke-width="1"/>
  <text x="30" y="51" fill="var(--muted)" font-size="9">local: 0</text>
  <text x="95" y="30" fill="var(--s1)" font-size="8">message stamp 2</text>
  <line x1="90" y1="47" x2="150" y2="47" stroke="var(--s1)" stroke-width="1.5"/>
  <rect x="155" y="35" width="120" height="24" fill="none" stroke="var(--ink)" stroke-width="1"/>
  <text x="162" y="51" fill="var(--ink)" font-size="9">max(0,2)+1 = 3</text>
  <text x="20" y="85" fill="var(--muted)" font-size="8">3 &gt; 2, so the receive always outranks the send</text>
</svg>
^ The receive rule sets the counter to one more than the larger of its own value and the message's stamp, forcing the receive strictly above the send that produced the message.

The trap is reaching for the timestamp you already have. Wall time is right there on every event, and for a single machine it orders things fine. Across machines it is a plausible-looking number that can lie about causality, and the lie is worst exactly when clocks are most skewed.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/govern-inter-18/lamport.py

The fixture is a five-event log from two processes, in true causal order; p2's clock runs behind p1's.

```json filename=modules/orchestration-and-governance/code/govern-inter-18/events.json:1-10 COMPLETE
{
  "_meta": "An event log from two processes (p1, p2) whose wall clocks are skewed: p2's clock runs behind p1's. Events are listed in TRUE causal order. kind is local, send, or recv; msg links a send to the recv that receives it. wall is the local clock reading when the event happened. The question: can you recover the causal order from the wall-clock readings, or do you need logical clocks?",
  "events": [
    {"id": "e1", "proc": "p1", "wall": 100, "kind": "local"},
    {"id": "e2", "proc": "p1", "wall": 101, "kind": "send", "msg": "m1"},
    {"id": "e3", "proc": "p2", "wall": 95,  "kind": "recv", "msg": "m1"},
    {"id": "e4", "proc": "p2", "wall": 96,  "kind": "send", "msg": "m2"},
    {"id": "e5", "proc": "p1", "wall": 110, "kind": "recv", "msg": "m2"}
  ]
}
```

The Lamport rules are one pass over the log: on a receive, jump past the send's stamp; otherwise just increment; a send records its stamp for the matching receive to read.

```python filename=modules/orchestration-and-governance/code/govern-inter-18/lamport.py:41-55 COMPLETE
def lamport_stamps(events):
    """Assign a Lamport timestamp to each event, processing the log in causal order."""
    counter = {}                       # per-process counter
    sent = {}                          # msg -> lamport ts of its send
    stamp = {}                         # event id -> lamport ts
    for e in events:
        p = e["proc"]
        if e["kind"] == "recv":
            counter[p] = max(counter.get(p, 0), sent[e["msg"]]) + 1
        else:
            counter[p] = counter.get(p, 0) + 1
        stamp[e["id"]] = counter[p]
        if e["kind"] == "send":
            sent[e["msg"]] = counter[p]
    return stamp
```

To check the causal invariant we pair each send with its matching receive by message id.

```python filename=modules/orchestration-and-governance/code/govern-inter-18/lamport.py:58-64 COMPLETE
def pairs(events):
    """(send event, recv event) for each message."""
    by_msg = {}
    for e in events:
        if e["kind"] in ("send", "recv"):
            by_msg.setdefault(e["msg"], {})[e["kind"]] = e
    return [(v["send"], v["recv"]) for v in by_msg.values() if "send" in v and "recv" in v]
```

Run `--wall` and sort the log by wall clock.

```text filename=--wall
WALL — events ordered by wall clock
----------------------------------------------------------
  wall  95  e3   p2    recv  msg=m1
  wall  96  e4   p2    send  msg=m2
  wall 100  e1   p1    local
  wall 101  e2   p1    send  msg=m1
  wall 110  e5   p1    recv  msg=m2
----------------------------------------------------------
  VIOLATION: m1 received (wall 95) before it was sent (wall 101)
  a clock behind on the receiver makes a receive look earlier than its send.
```

The receive of m1 sits at the top with wall 95, six ticks before its own send at wall 101. Read this order literally and p2 received a message that p1 had not yet sent — impossible, and yet it is exactly what the timestamps say.

<svg role="img" aria-label="Two wall-clock timelines: p2 behind p1, so the arrow from send m1 to recv m1 points backward in wall time" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="25" fill="var(--muted)" font-size="9">p1</text>
  <line x1="40" y1="30" x2="285" y2="30" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="230" cy="30" r="4" fill="var(--s1)"/>
  <text x="215" y="20" fill="var(--s1)" font-size="8">send m1 (101)</text>
  <text x="10" y="85" fill="var(--muted)" font-size="9">p2</text>
  <line x1="40" y1="90" x2="285" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="120" cy="90" r="4" fill="var(--s2)"/>
  <text x="90" y="105" fill="var(--s2)" font-size="8">recv m1 (95)</text>
  <line x1="230" y1="30" x2="120" y2="90" stroke="var(--ink)" stroke-width="1.5"/>
  <text x="150" y="55" fill="var(--muted)" font-size="8">arrow points back in wall time!</text>
</svg>
^ The message arrow slopes backward in wall time because the receiver's clock is behind — sorting by wall clock reports the receive before the send.

## Build

Now run `--lamport` and order the same log by logical time.

```text filename=--lamport
LAMPORT — logical timestamp per event, then the causal order
----------------------------------------------------------
  L1   e1   p1    local
  L2   e2   p1    send   msg=m1
  L3   e3   p2    recv   msg=m1
  L4   e4   p2    send   msg=m2
  L5   e5   p1    recv   msg=m2
----------------------------------------------------------
  every send has a smaller Lamport stamp than its receive.
```

The order is repaired. Send m1 is L2, its receive is L3; send m2 is L4, its receive L5. The max-plus-one rule forced each receive above its send regardless of what the wall clocks read, and the log's causal order is recovered exactly. The logical clock never knew the time of day and did not need to.

<svg role="img" aria-label="The message arrow from send m1 (L2) to recv m1 (L3) points forward in Lamport time" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="25" fill="var(--muted)" font-size="9">p1</text>
  <line x1="40" y1="30" x2="285" y2="30" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="100" cy="30" r="4" fill="var(--s1)"/>
  <text x="80" y="20" fill="var(--s1)" font-size="8">send m1 (L2)</text>
  <text x="10" y="85" fill="var(--muted)" font-size="9">p2</text>
  <line x1="40" y1="90" x2="285" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="160" cy="90" r="4" fill="var(--s2)"/>
  <text x="140" y="105" fill="var(--s2)" font-size="8">recv m1 (L3)</text>
  <line x1="100" y1="30" x2="160" y2="90" stroke="var(--ink)" stroke-width="1.5"/>
  <text x="165" y="55" fill="var(--muted)" font-size="8">arrow points forward: L2 &lt; L3</text>
</svg>
^ In Lamport time the same message arrow points forward — the receive stamp (L3) is forced above the send stamp (L2), so causality holds.

## Definition of done

The self-test pins the contrast: the wall order violates causality, every send has a smaller Lamport stamp than its receive, the wall order differs from the causal order, the Lamport order matches it, and Lamport stamps strictly increase along the log.

```python filename=modules/orchestration-and-governance/code/govern-inter-18/lamport.py:102-123 COMPLETE
    wall_violates = any(r["wall"] < s["wall"] for s, r in ps)
    print("  some message is received (by wall clock) before it was sent = %s" % wall_violates)
    for s, r in ps:
        if r["wall"] < s["wall"]:
            print("    %s: send wall %d, recv wall %d" % (s["msg"], s["wall"], r["wall"]))

    lamport_respects = all(stamp[s["id"]] < stamp[r["id"]] for s, r in ps)
    print("  every send has a smaller Lamport stamp than its receive = %s" % lamport_respects)
    for s, r in ps:
        print("    %s: send L%d < recv L%d = %s" % (s["msg"], stamp[s["id"]], stamp[r["id"]], stamp[s["id"]] < stamp[r["id"]]))

    wall_order = [e["id"] for e in sorted(events, key=lambda e: e["wall"])]
    lamport_order = [e["id"] for e in sorted(events, key=lambda e: stamp[e["id"]])]
    causal_order = [e["id"] for e in events]

    wall_reorders = wall_order != causal_order
    print("  wall-clock order differs from the true causal order = %s (%s)" % (wall_reorders, wall_order))

    lamport_matches_causal = lamport_order == causal_order
    print("  Lamport order matches the true causal order = %s (%s)" % (lamport_matches_causal, lamport_order))

    stamps_strictly_increase = all(stamp[events[i]["id"]] < stamp[events[i + 1]["id"]] for i in range(len(events) - 1))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — wall-clock order violates causality; the Lamport order puts every send before its receive
--------------------------------------------------------------------------------------------------------
  some message is received (by wall clock) before it was sent = True
    m1: send wall 101, recv wall 95
  every send has a smaller Lamport stamp than its receive = True
    m1: send L2 < recv L3 = True
    m2: send L4 < recv L5 = True
  wall-clock order differs from the true causal order = True (['e3', 'e4', 'e1', 'e2', 'e5'])
  Lamport order matches the true causal order = True (['e1', 'e2', 'e3', 'e4', 'e5'])
  Lamport stamps strictly increase along the causal log = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  wall_violates=True  lamport_respects=True  wall_reorders=True  lamport_matches_causal=True  stamps_strictly_increase=True
```

**Done means the fix is proven on the causal invariant, not on wall time: send m1 (L2) precedes recv m1 (L3) while the wall clocks claimed the reverse, so the logical order restored a causality the timestamps had inverted.**

## Boss fight

Lamport order put everything right here. Predict whether Lamport(A) < Lamport(B) lets you conclude that A caused B. It is tempting to read the total order that way — it worked for the messages.

It does not, and this is the limit that sends people to vector clocks. Lamport clocks guarantee only one direction: if A happened-before B, then Lamport(A) < Lamport(B). The converse fails. Two events on different processes that never exchanged a message are concurrent — neither caused the other — yet their Lamport stamps are still comparable, and one will be smaller purely by how the counters advanced. So a smaller stamp can mean "earlier in causal order" or "concurrent and it just landed lower." To actually detect concurrency versus causal dependence you need a vector clock, which keeps a counter per process and can tell "before," "after," and "concurrent" apart.

The mirror-image mistake is thinking better clock synchronization removes the need for logical clocks. Even with tight sync (NTP, or bounded-uncertainty clocks like Google's TrueTime) there is a residual uncertainty window, and within it wall-clock ordering can still invert causality. Systems that need real timestamps handle this by waiting out the uncertainty; systems that only need ordering use logical clocks and skip the problem entirely.

```python filename=modules/orchestration-and-governance/code/govern-inter-18/lamport.py:41-49 COMPLETE
def lamport_stamps(events):
    """Assign a Lamport timestamp to each event, processing the log in causal order."""
    counter = {}                       # per-process counter
    sent = {}                          # msg -> lamport ts of its send
    stamp = {}                         # event id -> lamport ts
    for e in events:
        p = e["proc"]
        if e["kind"] == "recv":
            counter[p] = max(counter.get(p, 0), sent[e["msg"]]) + 1
        else:
            counter[p] = counter.get(p, 0) + 1
```

**Order distributed events by a logical clock, not a wall clock: Lamport stamps guarantee a send precedes its receive, but only a vector clock can tell causal dependence from concurrency.**

## External resources

Leslie Lamport, "Time, Clocks, and the Ordering of Events in a Distributed System" (1978) — the original paper defining the happened-before relation and the logical clock this module builds.

Fidge and Mattern on vector clocks — the extension that detects concurrency, the exact gap named in the boss fight.

The "Designing Data-Intensive Applications" (Kleppmann) chapter on ordering and clocks — why wall-clock timestamps are unsafe for ordering, TrueTime's uncertainty window, and where logical clocks fit.
