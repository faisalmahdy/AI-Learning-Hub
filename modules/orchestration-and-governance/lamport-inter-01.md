---
id: lamport-inter-01
title: Order distributed events by logical clocks, not wall-clock time — a skewed clock makes a reply look older than the message it answers
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: When events happen on different machines and you need one order for them — to replay a log, break a tie, decide which write is "later" — the obvious key is each event's wall-clock timestamp, and it is wrong because the machines' clocks disagree. An event that genuinely happened later, on a machine whose clock runs behind, carries a lower timestamp than an earlier event on a faster machine, so sorting by wall-clock can place a message's receipt before it was ever sent — causality inverted by nothing but two clocks that do not agree. The fix stops using physical clocks for ordering. A Lamport logical clock is a per-node counter with two rules: increment it on every local event, and on receiving a message advance the counter to max(its own value, the message's stamp) + 1. The receive rule is the trick: the message's stamp is a lower bound the receiver must exceed, so a received event always gets a stamp strictly greater than the send it depends on, whatever the wall clocks say. Sorting by Lamport stamp gives a total order (ties broken by node id) consistent with happens-before — causes always precede effects. On a fixture where A sends m1 (wall 100), a behind-schedule B receives it (wall 95) and replies with m2 (wall 96), and A receives the reply (wall 103), the true order is e1→e2→e3→e4; wall-clock sorting puts e2,e3 before e1 (B receiving m1 before A sent it) for one causality violation, while Lamport stamps come out 1,2,3,4 and reproduce the causal order exactly.
eli5: Imagine two friends writing letters back and forth, each dating their letters by their own wristwatch. One friend's watch is running slow. So when she gets a letter and immediately writes back, her reply is dated EARLIER than the letter she is answering — and if you sort the whole pile of letters by the dates on them, the reply comes out before the question, which makes no sense. The fix is to stop trusting the watches. Instead, everyone keeps a little counter. Every time you do anything, you tick it up by one. And whenever you receive a letter, you look at the number written on it, and set your counter to one more than the bigger of your number and theirs. That way a reply always has a bigger number than the letter it answers, no matter whose watch is slow — and sorting by those numbers always puts the question before the answer.
---

## Why this module

You have events from several machines and you need to put them in one order. Maybe you are merging their logs to debug an incident, or deciding which of two concurrent writes should win, or just presenting a timeline. Every event arrived with a timestamp, so the answer looks like it is already in the data: sort by the timestamp. This is the single most common way distributed systems get ordering wrong, and it is worth seeing the failure concretely, because the timestamp looks authoritative right up until it lies to you.

It lies because the machines' clocks are not the same clock. Physical clocks drift; even with NTP correcting them they disagree by milliseconds, and a misconfigured or overloaded one can be off by seconds or more. So the timestamp does not measure "when, on one universal clock" — it measures "what this particular machine's clock happened to read." An event that truly happened later, on a machine whose clock runs behind, is stamped with a lower number than an earlier event on a machine whose clock runs ahead. Sort by that number and you can order an effect before its cause: a reply before the message it answers, a receipt before the send.

The fix is not to synchronize the clocks better — that is a losing battle you never fully win. It is to stop using physical time for ordering at all, and use a logical clock that is built to respect causality by construction. This module orders the same four events both ways and counts how many times each ordering places a receive before its send.

**Order distributed events by Lamport logical clocks — a per-node counter incremented on each event and advanced to max(local, received stamp) + 1 on every receive — not by wall-clock timestamps, because clock skew lets an event on a slow clock carry a lower timestamp than an earlier event on a fast clock, placing effects before their causes.**

## Concepts

The fixture is one causal chain across two machines. A sends message m1; B receives m1; B replies with m2; A receives m2. Each event carries the wall-clock reading of the machine it happened on. B's clock runs behind A's, so B's readings (95, 96) are lower than A's send (100) even though B's events happened after it. The true happens-before order is fixed and unambiguous — e1 → e2 → e3 → e4 — and it is stored as `causal_order` so the two orderings can be scored against ground truth.

```json filename=modules/orchestration-and-governance/code/lamport-inter-01/lamport.json:12-17 COMPLETE
  "events": [
    {"id": "e1", "node": "A", "op": "send", "msg": "m1", "wall": 100},
    {"id": "e2", "node": "B", "op": "recv", "msg": "m1", "wall": 95},
    {"id": "e3", "node": "B", "op": "send", "msg": "m2", "wall": 96},
    {"id": "e4", "node": "A", "op": "recv", "msg": "m2", "wall": 103}
  ],
```

A Lamport clock is a single integer per node. The rules are small: on any local event, increment the counter; on a send, attach the incremented counter to the message; on a receive, advance the counter to one more than the larger of its own value and the stamp the message carries. That receive rule is the entire mechanism — it forces a received event's stamp above the send it depends on.

```python filename=modules/orchestration-and-governance/code/lamport-inter-01/lamport.py:47-62 COMPLETE
def lamport_stamps(events):
    """Per-node counter: +1 on every event, and on receive advance to max(local, message stamp) + 1."""
    clocks = {}
    sent = {}
    stamps = {}
    for e in events:
        node = e["node"]
        clocks.setdefault(node, 0)
        if e["op"] == "send":
            clocks[node] += 1
            sent[e["msg"]] = clocks[node]
        else:
            clocks[node] = max(clocks[node], sent[e["msg"]]) + 1
        stamps[e["id"]] = clocks[node]
    return stamps
```

Once every event has a stamp, ordering is just a sort — by wall-clock or by Lamport stamp — with a stable tiebreak on node and id so the total order is deterministic. And to score an ordering, we count causality violations: for each message, does its receive land before its send in the order? A single "yes" means an effect was placed before its cause.

```python filename=modules/orchestration-and-governance/code/lamport-inter-01/lamport.py:65-83 COMPLETE
def order_by_wall(events):
    """Total order by wall-clock reading, breaking ties by node then id."""
    return [e["id"] for e in sorted(events, key=lambda e: (e["wall"], e["node"], e["id"]))]


def order_by_lamport(events, stamps):
    """Total order by Lamport stamp, breaking ties by node then id."""
    return [e["id"] for e in sorted(events, key=lambda e: (stamps[e["id"]], e["node"], e["id"]))]


def causality_violations(events, order):
    """Count messages whose recv is placed before its send in this ordering -- an effect before its cause."""
    pos = {eid: i for i, eid in enumerate(order)}
    send_at = {e["msg"]: e["id"] for e in events if e["op"] == "send"}
    recv_at = {e["msg"]: e["id"] for e in events if e["op"] == "recv"}
    violations = []
    for msg in send_at:
        if msg in recv_at and pos[recv_at[msg]] < pos[send_at[msg]]:
            violations.append(msg)
    return violations
```

<svg role="img" aria-label="Timeline of two nodes A and B; B's clock reads lower than A's despite its events happening later, with a message arrow crossing backward in wall-clock time" viewBox="0 0 330 160">
  <line x1="30" y1="45" x2="310" y2="45" stroke="var(--line)" stroke-width="1"/>
  <line x1="30" y1="115" x2="310" y2="115" stroke="var(--line)" stroke-width="1"/>
  <text x="8" y="49" font-size="10" fill="var(--muted)">A</text>
  <text x="8" y="119" font-size="10" fill="var(--muted)">B</text>
  <circle cx="90" cy="45" r="4" fill="var(--s1)"/>
  <text x="72" y="34" font-size="9" fill="var(--ink)">e1 send m1</text>
  <text x="80" y="64" font-size="9" fill="var(--muted)">wall 100</text>
  <circle cx="150" cy="115" r="4" fill="var(--s2)"/>
  <text x="132" y="137" font-size="9" fill="var(--ink)">e2 recv m1</text>
  <text x="140" y="106" font-size="9" fill="var(--muted)">wall 95</text>
  <circle cx="210" cy="115" r="4" fill="var(--s2)"/>
  <text x="192" y="137" font-size="9" fill="var(--ink)">e3 send m2</text>
  <circle cx="270" cy="45" r="4" fill="var(--s1)"/>
  <text x="252" y="34" font-size="9" fill="var(--ink)">e4 recv m2</text>
  <line x1="90" y1="49" x2="150" y2="111" stroke="var(--ink)" stroke-width="1.5" stroke-dasharray="3 2"/>
  <line x1="210" y1="111" x2="270" y2="49" stroke="var(--ink)" stroke-width="1.5" stroke-dasharray="3 2"/>
  <text x="150" y="16" font-size="9" fill="var(--muted)">B reads 95/96, below A's 100 — its clock runs behind</text>
</svg>
^ B's events happen after A's send but its clock reads lower (95, 96 vs 100). The dashed message arrows go forward in real time; the wall-clock numbers along B go backward, which is what breaks a timestamp sort.

**A Lamport stamp is not a clock reading — it is a counter whose receive rule guarantees a received event outranks its send, which is exactly the guarantee a wall-clock timestamp cannot make.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the event-ordering step of an orchestration log merge, reduced to four events on two nodes so every stamp and ordering is checkable by hand.

Run `--order` to see each event's wall-clock reading and computed Lamport stamp, and the two orderings against the truth.

```text filename=lamport.py --order
  event  node  op    msg   wall-clock   Lamport
  e1     A     send  m1    100          1
  e2     B     recv  m1    95           2
  e3     B     send  m2    96           3
  e4     A     recv  m2    103          4
  order by wall-clock: e2 e3 e1 e4
  order by Lamport:    e1 e2 e3 e4
  true causal order:   e1 e2 e3 e4
```

Look at the wall-clock column and the trap is visible: e2 and e3 read 95 and 96, below e1's 100, because B's clock is behind. Sort ascending and B's receive of m1 (e2) and its reply (e3) land ahead of A's send of m1 (e1). The Lamport column tells a different story — e1 gets 1, e2 is forced to max(0, 1)+1 = 2, e3 to 3, e4 to max(1, 3)+1 = 4 — and sorting by it reproduces e1 e2 e3 e4, the true order.

Now `--causal` scores each ordering by the one thing that matters: does any message get received before it is sent?

```text filename=lamport.py --causal
  wall-clock order ['e2', 'e3', 'e1', 'e4'] -> 1 violation(s): ['m1']
  Lamport order    ['e1', 'e2', 'e3', 'e4'] -> 0 violation(s): none
  under wall-clock, e2 (recv m1) is ordered before e1 (send m1) -- a reply before its cause
```

One violation under wall-clock: m1 is received (e2, position 0) before it is sent (e1, position 2). That is not a rounding quirk — it is a receipt ordered before the send, which no valid timeline permits. The Lamport ordering has zero, because the receive rule made e2's stamp strictly larger than e1's regardless of the clocks.

<svg role="img" aria-label="Four steps of the Lamport counter: A ticks to 1, B jumps to 2 on receiving stamp 1, B ticks to 3, A jumps to 4 on receiving stamp 3" viewBox="0 0 330 140">
  <text x="10" y="18" font-size="9" fill="var(--muted)">counter value after each event (receive = max(local, stamp)+1)</text>
  <rect x="20" y="40" width="50" height="26" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="30" y="57" font-size="10" fill="var(--ink)">e1 A:1</text>
  <text x="30" y="82" font-size="8" fill="var(--muted)">0+1</text>
  <rect x="95" y="40" width="50" height="26" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="102" y="57" font-size="10" fill="var(--ink)">e2 B:2</text>
  <text x="98" y="82" font-size="8" fill="var(--muted)">max(0,1)+1</text>
  <rect x="170" y="40" width="50" height="26" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="180" y="57" font-size="10" fill="var(--ink)">e3 B:3</text>
  <text x="182" y="82" font-size="8" fill="var(--muted)">2+1</text>
  <rect x="245" y="40" width="50" height="26" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="253" y="57" font-size="10" fill="var(--ink)">e4 A:4</text>
  <text x="248" y="82" font-size="8" fill="var(--muted)">max(1,3)+1</text>
  <path d="M 70 53 L 93 53" fill="none" stroke="var(--ink)" stroke-width="1"/>
  <path d="M 145 53 L 168 53" fill="none" stroke="var(--ink)" stroke-width="1"/>
  <path d="M 220 53 L 243 53" fill="none" stroke="var(--ink)" stroke-width="1"/>
  <text x="70" y="112" font-size="8.5" fill="var(--s2)">m1 carries stamp 1 → forces e2 above e1</text>
  <text x="70" y="126" font-size="8.5" fill="var(--s1)">m2 carries stamp 3 → forces e4 above e3</text>
</svg>
^ The receive rule is the jump: e2 does not just tick to 1, it takes max(0, m1's stamp 1) + 1 = 2, so it outranks its send e1; e4 takes max(1, m2's stamp 3) + 1 = 4. The message's stamp is a floor the receiver must clear.

**The wall-clock sort does not merely reorder close events — it places a message's receipt two positions ahead of its send, an ordering that asserts B answered a message A had not yet transmitted.**

## Build

The self-test asserts the setup and the failure, not just the fix — a fix is only meaningful if the naive method genuinely breaks on this input. So it first confirms the skew exists and that wall-clock ordering actually violates causality.

```python filename=modules/orchestration-and-governance/code/lamport-inter-01/lamport.py:107-116 COMPLETE
    clock_skew_present = min(e["wall"] for e in events if e["node"] == "B") < max(e["wall"] for e in events if e["node"] == "A")
    print("  a slow clock exists (a B event reads lower than an A event) = %s" % clock_skew_present)

    wall_violations = causality_violations(events, wall)
    wallclock_violates_causality = len(wall_violations) > 0
    print("  wall-clock ordering places a receive before its send = %s (%d violation: %s)"
          % (wallclock_violates_causality, len(wall_violations), wall_violations))

    lamport_violations = causality_violations(events, lam)
    lamport_respects_causality = len(lamport_violations) == 0
```

<svg role="img" aria-label="Two orderings of four events; wall-clock ordering has a backward arrow from send to receive, Lamport ordering has all forward arrows" viewBox="0 0 330 170">
  <text x="10" y="20" font-size="10" fill="var(--muted)">wall-clock order</text>
  <text x="60" y="45" font-size="11" fill="var(--ink)">e2</text>
  <text x="120" y="45" font-size="11" fill="var(--ink)">e3</text>
  <text x="180" y="45" font-size="11" fill="var(--ink)">e1</text>
  <text x="240" y="45" font-size="11" fill="var(--ink)">e4</text>
  <path d="M 185 38 Q 130 18 68 38" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="95" y="66" font-size="8.5" fill="var(--s2)">m1: send e1 AFTER recv e2 — violation</text>
  <text x="10" y="110" font-size="10" fill="var(--muted)">Lamport order</text>
  <text x="60" y="135" font-size="11" fill="var(--ink)">e1</text>
  <text x="120" y="135" font-size="11" fill="var(--ink)">e2</text>
  <text x="180" y="135" font-size="11" fill="var(--ink)">e3</text>
  <text x="240" y="135" font-size="11" fill="var(--ink)">e4</text>
  <path d="M 68 128 Q 95 110 128 128" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <path d="M 188 128 Q 215 110 248 128" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="95" y="156" font-size="8.5" fill="var(--s1)">every send precedes its receive — 0 violations</text>
</svg>
^ Under wall-clock the m1 arrow points backward — the send sits after the receive. Under Lamport every message arrow points forward, which is the definition of an ordering consistent with causality.

Running the check confirms both halves — the naive method fails, the logical clock succeeds.

```text filename=lamport.py --check
  a slow clock exists (a B event reads lower than an A event) = True
  wall-clock ordering places a receive before its send = True (1 violation: ['m1'])
  Lamport ordering has zero causality violations = True (none)
  Lamport order reproduces the true causal order = True (e1 e2 e3 e4)
  Lamport stamp strictly increases along the causal chain = True (1 < 2 < 3 < 4)
```

**The check pins down that the wall-clock ordering breaks on exactly this skew and the Lamport ordering does not — so the module measures a real failure being fixed, not a fix with nothing to fix.**

## Definition of done

Two properties close it. The Lamport ordering must reproduce the true causal order the fixture declares, and the stamp must increase strictly along that causal chain — the latter is the invariant that guarantees the former for any chain, not just this one.

```python filename=modules/orchestration-and-governance/code/lamport-inter-01/lamport.py:118-124 COMPLETE
    lamport_matches_causal = lam == causal
    print("  Lamport order reproduces the true causal order = %s (%s)" % (lamport_matches_causal, " ".join(lam)))

    stamps_strictly_increase = all(stamps[causal[i]] < stamps[causal[i + 1]] for i in range(len(causal) - 1))
    print("  Lamport stamp strictly increases along the causal chain = %s (%s)"
          % (stamps_strictly_increase, " < ".join(str(stamps[e]) for e in causal)))
```

There is a boundary worth stating so the tool is not oversold. Lamport clocks give a total order consistent with causality — if a happened-before b, then Lamport(a) < Lamport(b). The converse does not hold: Lamport(a) < Lamport(b) does not prove a happened-before b, because two genuinely unrelated (concurrent) events still get ordered by their stamps and the tiebreak. Detecting true concurrency needs vector clocks, which carry one counter per node instead of one integer. Lamport gives you the weaker, cheaper guarantee that is nonetheless exactly what wall-clock ordering fails to give: causes never come after their effects.

**Done means the Lamport order equals the declared causal order and its stamps rise strictly along the causal chain — a total order that never contradicts happens-before, which is all a single-integer logical clock promises and all this task needs.**

## Boss fight

Your system resolves conflicting writes with last-write-wins, keyed on each write's wall-clock timestamp: the write with the higher timestamp survives. A user reports that they edited a document, saw the edit, then made a second edit — and the second edit vanished, leaving the first. Both edits came from the same session, one strictly after the other. The two writes were served by different replicas. What happened, and how would switching the tiebreak to a Lamport stamp fix it without your having to synchronize any clocks?

The second edit was served by a replica whose clock runs behind the first replica's. So even though it happened later, it carried a lower wall-clock timestamp, and last-write-wins — comparing those timestamps — kept the first edit and discarded the second. The edit did not vanish; it lost a timestamp comparison to an earlier write on a faster clock. A Lamport stamp fixes it because the second write causally follows the first (the session read the first edit before making the second), and if you propagate the Lamport stamp on the read, the second write's stamp is forced to max(local, first write's stamp) + 1 — strictly greater than the first's, whatever the two replicas' wall clocks read. Last-write-wins on the Lamport stamp then keeps the causally-later edit. You changed the comparison key, not the clocks, and the causally-later write wins by construction.

## External resources

Leslie Lamport, "Time, Clocks, and the Ordering of Events in a Distributed System" (1978) — the original paper that defines the happens-before relation and the logical-clock rules implemented here; short, foundational, and readable.

Martin Kleppmann, *Designing Data-Intensive Applications*, the chapter on ordering and consistency — situates Lamport timestamps against vector clocks and version vectors, and explains why last-write-wins on physical timestamps silently drops writes, which is the boss fight above at production scale.
