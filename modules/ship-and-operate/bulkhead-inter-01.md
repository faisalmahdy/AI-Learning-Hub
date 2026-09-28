---
id: bulkhead-inter-01
title: Partition the pool per dependency — one shared pool of slots lets a slow dependency's saturation starve a healthy one
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: A service that calls several downstream dependencies usually draws its concurrency — threads, connections, in-flight slots — from one shared pool. That is efficient while everything is healthy, but it becomes a fault-propagation path the moment one dependency goes slow. If dependency A starts taking 10x longer, each in-flight call to A holds its slot 10x longer, so a burst of A calls can occupy every slot in the shared pool at once. A call to dependency B — perfectly healthy, would return in a millisecond — then arrives, finds no free slot, and is rejected. A single sick dependency has taken down an unrelated one. A bulkhead fixes this by partitioning the pool: each dependency gets its own capped share of the slots, so it can only exhaust its own partition; the name is from ships, whose hulls are divided into watertight compartments so one breach does not flood the vessel. The trade-off is deliberate — bulkheading caps each dependency below the full pool, trading some peak throughput for containment. On a fixture where four slow A calls (service 10) arrive at once and then three healthy B calls (service 1) arrive one per tick, a shared pool of 4 slots serves all four A calls and rejects all three B calls (B served 0 of 3), while a bulkhead of 2 slots each serves only 2 A calls but all 3 B calls (B served 3 of 3).
eli5: Imagine a call center with 4 phone lines shared by two kinds of callers. One kind (A) gets stuck on hold for ages, and four of them grab all 4 lines and hang on. Now the quick callers (B), who would be done in a second, phone in and get a busy signal — even though they did nothing wrong, the stuck callers used up every line. The fix: reserve 2 lines only for A and 2 only for B. Now when A's callers get stuck, they can only tie up their own 2 lines; B's 2 lines are always free, so quick callers always get through. You give up letting one group borrow all 4 lines, in exchange for one group's problem never blocking the other.
---

## Why this module

Reaching for one shared pool of connections or threads feels like the efficient choice — whichever dependency is busy gets the slots. It is efficient right up to the moment one dependency goes slow, and then the sharing you wanted becomes the path by which a single sick dependency takes down every other one that draws from the same pool. The dangerous part is that nothing in the pool is broken; sharing is working exactly as designed, and that is precisely what lets one failure leak into unrelated, healthy traffic.

A service that calls several downstream dependencies usually draws its concurrency — threads, connections, in-flight slots — from one shared pool. That is efficient when everything is healthy: whichever dependency is busy gets the slots. It becomes a fault-propagation path the moment one dependency goes slow. If dependency A starts taking 10x longer, each in-flight call to A holds its slot 10x longer, so a burst of A calls can occupy every slot in the shared pool at once. Now a call to dependency B — which is perfectly healthy and would return in a millisecond — arrives and finds no free slot, so it is rejected or queued behind A's slow calls. A single sick dependency has taken down an unrelated one, and from B's users' point of view the whole service is broken.

A bulkhead fixes this by *partitioning* the pool: each dependency gets its own capped share of the slots, so a dependency can only ever exhaust its own partition. The name is from ships — a hull is divided into watertight compartments so a breach in one does not flood the whole vessel. Give A a cap of 2 slots and B a cap of 2, and when A saturates it fills its 2 slots while B's 2 slots stay untouched, so B keeps serving. The trade-off is deliberate: bulkheading caps each dependency below the full pool, so you trade some peak throughput for the guarantee that one dependency's failure is contained. This module runs the same request stream through a shared pool and through a bulkhead.

**Drawing concurrency for independent dependencies from one shared pool lets a slow or failing dependency saturate every slot and starve the healthy ones, so partition the pool into per-dependency capped bulkheads — a failure then exhausts only its own share, the isolation a circuit breaker gives in time (stop calling a broken dependency) applied in space (cap the resources it can hold).**

## Concepts

**One admission rule, two pool shapes:** a shared pool admits a call if any slot is free; a bulkhead admits it only if the call's own dependency has room in its partition. That single branch is the whole difference between contagion and containment.

```python filename=modules/ship-and-operate/code/bulkhead-inter-01/bulkhead.py:53-73 COMPLETE
    reqs = sorted(requests, key=lambda r: (r["arrival"], r["id"]))
    in_flight = []  # (dep, release_tick) for each held slot
    outcomes = []
    last_arrival = max(r["arrival"] for r in reqs)
    for tick in range(0, last_arrival + 1):
        in_flight = [(d, rel) for (d, rel) in in_flight if rel > tick]  # free completed slots
        for r in reqs:
            if r["arrival"] != tick:
                continue
            dep = r["dep"]
            if caps is None:
                admit = len(in_flight) < total_slots
            else:
                used_dep = sum(1 for (d, rel) in in_flight if d == dep)
                admit = used_dep < caps[dep]
            if admit:
                in_flight.append((dep, tick + r["service"]))
                outcomes.append({"id": r["id"], "dep": dep, "result": "admit"})
            else:
                outcomes.append({"id": r["id"], "dep": dep, "result": "REJECT"})
    return outcomes
```

**We count served vs rejected per dependency** so the story is a number, not a vibe — a starved dependency is one whose served count is zero.

```python filename=modules/ship-and-operate/code/bulkhead-inter-01/bulkhead.py:76-77 COMPLETE
def counts(outcomes, dep, result):
    return sum(1 for o in outcomes if o["dep"] == dep and o["result"] == result)
```

<svg role="img" aria-label="A shared pool of four slots filled entirely by four slow A calls, so three healthy B calls find no free slot and are rejected; beside it a bulkhead splits the four slots into two for A and two for B, so A fills its two and B's two stay free" viewBox="0 0 300 140" width="300" height="140">
  <text x="6" y="12" fill="var(--muted)" font-size="8">shared pool: A fills all 4 slots — B is turned away</text>
  <rect x="20" y="20" width="24" height="16" fill="var(--s2)"/><text x="26" y="32" fill="var(--panel)" font-size="8">A</text>
  <rect x="48" y="20" width="24" height="16" fill="var(--s2)"/><text x="54" y="32" fill="var(--panel)" font-size="8">A</text>
  <rect x="76" y="20" width="24" height="16" fill="var(--s2)"/><text x="82" y="32" fill="var(--panel)" font-size="8">A</text>
  <rect x="104" y="20" width="24" height="16" fill="var(--s2)"/><text x="110" y="32" fill="var(--panel)" font-size="8">A</text>
  <text x="140" y="32" fill="var(--muted)" font-size="7">B B B → REJECT (pool full)</text>
  <text x="6" y="66" fill="var(--muted)" font-size="8">bulkhead: 2 slots for A, 2 for B — B always has room</text>
  <rect x="20" y="74" width="24" height="16" fill="var(--s2)"/><text x="26" y="86" fill="var(--panel)" font-size="8">A</text>
  <rect x="48" y="74" width="24" height="16" fill="var(--s2)"/><text x="54" y="86" fill="var(--panel)" font-size="8">A</text>
  <rect x="76" y="74" width="24" height="16" fill="none" stroke="var(--s1)"/><text x="82" y="86" fill="var(--s1)" font-size="8">B</text>
  <rect x="104" y="74" width="24" height="16" fill="none" stroke="var(--s1)"/><text x="110" y="86" fill="var(--s1)" font-size="8">B</text>
  <text x="20" y="106" fill="var(--muted)" font-size="7">A's extra calls REJECT in A's partition;</text>
  <text x="20" y="118" fill="var(--muted)" font-size="7">B's 2 slots serve all 3 B calls in turn.</text>
  <line x1="14" y1="44" x2="286" y2="44" stroke="var(--grid)"/>
</svg>
^ A shared pool of 4 slots is filled entirely by the 4 slow A calls, so the healthy B calls are rejected; a bulkhead reserves 2 slots for each dependency, so A can only fill its own 2 and B's 2 slots keep serving.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/bulkhead-inter-01/bulkhead.py

The fixture is seven requests: four slow A calls (service 10) all arriving at tick 0, then three healthy B calls (service 1) arriving one per tick.

```json filename=modules/ship-and-operate/code/bulkhead-inter-01/bulkhead.json:4-12 COMPLETE
  "requests": [
    {"id": 1, "arrival": 0, "dep": "A", "service": 10},
    {"id": 2, "arrival": 0, "dep": "A", "service": 10},
    {"id": 3, "arrival": 0, "dep": "A", "service": 10},
    {"id": 4, "arrival": 0, "dep": "A", "service": 10},
    {"id": 5, "arrival": 1, "dep": "B", "service": 1},
    {"id": 6, "arrival": 2, "dep": "B", "service": 1},
    {"id": 7, "arrival": 3, "dep": "B", "service": 1}
  ]
```

Run `--pool`.

```text filename=--pool
POOL — 4 slow A calls (service 10) then 3 healthy B calls (service 1); pool=4, bulkhead caps={'A': 2, 'B': 2}
--------------------------------------------------------------------------
  id  dep  arrival  shared-pool   bulkhead
  1   A    0        admit         admit
  2   A    0        admit         admit
  3   A    0        admit         REJECT
  4   A    0        admit         REJECT
  5   B    1        REJECT        admit
  6   B    2        REJECT        admit
  7   B    3        REJECT        admit
--------------------------------------------------------------------------
  SHARED POOL: A served 4/4, B served 0/3  <- healthy B starved by A
  BULKHEAD:    A served 2/4, B served 3/3  <- A capped, B fully protected
```

Read the two columns. In the shared pool, the four A calls arrive together and take all four slots, which they hold for ten ticks; every B call that arrives afterward finds the pool full and is rejected, so B — which was never slow, never failing — is served zero of three. The slow dependency's saturation has become the healthy dependency's outage. In the bulkhead, A's partition holds only two slots, so A calls 3 and 4 are rejected the instant A's share is full; but that rejection is A's problem, confined to A's compartment. B's partition is untouched, and because each B call frees its slot after one tick, B's two slots serve all three B calls in turn. Same requests, same total of four slots — the difference is entirely whether the four slots are one shared pool or two capped partitions.

## Build

The tick-by-tick trace of the shared pool shows exactly how B gets starved: A never lets go.

```text filename=--trace
TRACE — shared pool of 4 slots, tick by tick
------------------------------------------------------------------
  tick  free-before  arrivals   decision
  0     4            4 call(s)  A#1 admit; A#2 admit; A#3 admit; A#4 admit
  1     0            1 call(s)  B#5 REJECT (pool full)
  2     0            1 call(s)  B#6 REJECT (pool full)
  3     0            1 call(s)  B#7 REJECT (pool full)
------------------------------------------------------------------
  the 4 A calls hold all 4 slots for 10 ticks, so every B call finds a full pool.
```

At tick 0 the pool is empty, so all four A calls are admitted and the free count drops to zero. Each A call holds its slot until tick 10 (arrival 0 + service 10), so at ticks 1, 2, and 3 — when the B calls arrive — the pool is still completely full, and every B call is rejected. This is the mechanism in one word: *duration*. It is not that A sends more calls; it is that each A call occupies its slot far longer, so a small burst of a slow dependency ties up capacity out of all proportion to its request count. A pool sized for healthy latencies is the wrong size the instant one dependency's latency blows up, and with one shared pool that wrong-sizing hits everyone. The bulkhead's cap is what breaks the coupling — A's slow calls can hold at most A's two slots, no matter how long they take.

<svg role="img" aria-label="A timeline of the shared pool: four A calls occupy all four slots from tick 0 to tick 10, and the three B calls arriving at ticks 1, 2 and 3 fall in the shaded full-pool span and are rejected" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">shared pool held full by A for 10 ticks — B arrives into a full pool</text>
  <rect x="40" y="20" width="180" height="60" fill="var(--grid)" opacity="0.4"/>
  <text x="150" y="18" fill="var(--muted)" font-size="6">pool full (all 4 slots held by A)</text>
  <line x1="40" y1="26" x2="220" y2="26" stroke="var(--s2)"/><text x="224" y="29" fill="var(--muted)" font-size="6">A#1</text>
  <line x1="40" y1="38" x2="220" y2="38" stroke="var(--s2)"/><text x="224" y="41" fill="var(--muted)" font-size="6">A#2</text>
  <line x1="40" y1="50" x2="220" y2="50" stroke="var(--s2)"/><text x="224" y="53" fill="var(--muted)" font-size="6">A#3</text>
  <line x1="40" y1="62" x2="220" y2="62" stroke="var(--s2)"/><text x="224" y="65" fill="var(--muted)" font-size="6">A#4</text>
  <circle cx="58" cy="90" r="3" fill="var(--s1)"/><text x="50" y="104" fill="var(--muted)" font-size="6">B#5</text>
  <circle cx="76" cy="90" r="3" fill="var(--s1)"/><text x="68" y="104" fill="var(--muted)" font-size="6">B#6</text>
  <circle cx="94" cy="90" r="3" fill="var(--s1)"/><text x="86" y="104" fill="var(--muted)" font-size="6">B#7</text>
  <text x="120" y="94" fill="var(--muted)" font-size="6">↑ all three land inside the full span → rejected</text>
  <text x="34" y="112" fill="var(--muted)" font-size="6">tick 0</text><text x="205" y="112" fill="var(--muted)" font-size="6">tick 10</text>
</svg>
^ The four A calls hold all four slots continuously from tick 0 to tick 10; the three B calls arrive at ticks 1–3, squarely inside that full-pool span, so each is rejected — it is the ten-tick duration of A's calls, not their count, that starves B.

```python filename=modules/ship-and-operate/code/bulkhead-inter-01/bulkhead.py:135-143 COMPLETE
    shared_starves_b = counts(shared, "B", "admit") == 0
    print("  shared pool: healthy B calls served = %d of %d -> starved = %s"
          % (counts(shared, "B", "admit"), b_total, shared_starves_b))

    bulkhead_protects_b = counts(bulk, "B", "admit") == b_total and counts(bulk, "B", "REJECT") == 0
    print("  bulkhead: healthy B calls served = %d of %d -> fully protected = %s"
          % (counts(bulk, "B", "admit"), b_total, bulkhead_protects_b))

    bulkhead_caps_a = counts(bulk, "A", "admit") < counts(shared, "A", "admit")
```

## Definition of done

The self-test pins the starvation under the shared pool, the full protection of B under the bulkhead, and the deliberate cap on A that pays for it.

```python filename=modules/ship-and-operate/code/bulkhead-inter-01/bulkhead.py:147-153 COMPLETE
    a_confined_to_partition = counts(bulk, "A", "admit") == data["bulkhead_caps"]["A"]
    print("  A can hold at most its own partition = %s (%d slots)"
          % (a_confined_to_partition, data["bulkhead_caps"]["A"]))

    outcomes_differ = counts(shared, "B", "admit") != counts(bulk, "B", "admit")
    print("  bulkhead changes B's fate (isolation worked) = %s (%d vs %d served)"
          % (outcomes_differ, counts(shared, "B", "admit"), counts(bulk, "B", "admit")))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the shared pool lets slow A starve healthy B; the bulkhead caps A and keeps B serving
------------------------------------------------------------------------------------------------
  shared pool: healthy B calls served = 0 of 3 -> starved = True
  bulkhead: healthy B calls served = 3 of 3 -> fully protected = True
  bulkhead caps A below the whole pool = True (A served 2 vs 4 shared)
  A can hold at most its own partition = True (2 slots)
  bulkhead changes B's fate (isolation worked) = True (0 vs 3 served)
```

<svg role="img" aria-label="Bar chart of B calls served: 0 of 3 under the shared pool, 3 of 3 under the bulkhead; and A calls served: 4 under the shared pool, 2 under the bulkhead" viewBox="0 0 300 120" width="300" height="120">
  <text x="6" y="12" fill="var(--muted)" font-size="8">B served: 0/3 shared vs 3/3 bulkhead (A capped 4→2 to pay for it)</text>
  <text x="10" y="40" fill="var(--muted)" font-size="7">B shared</text>
  <rect x="70" y="32" width="2" height="12" fill="var(--s1)"/><text x="76" y="42" fill="var(--muted)" font-size="7">0 of 3 served</text>
  <text x="10" y="60" fill="var(--muted)" font-size="7">B bulkhead</text>
  <rect x="70" y="52" width="150" height="12" fill="var(--s1)"/><text x="226" y="62" fill="var(--muted)" font-size="7">3 of 3</text>
  <text x="10" y="86" fill="var(--muted)" font-size="7">A shared</text>
  <rect x="70" y="78" width="200" height="12" fill="var(--s2)"/><text x="274" y="88" fill="var(--muted)" font-size="7">4</text>
  <text x="10" y="106" fill="var(--muted)" font-size="7">A bulkhead</text>
  <rect x="70" y="98" width="100" height="12" fill="var(--s2)"/><text x="176" y="108" fill="var(--muted)" font-size="7">2 (capped)</text>
</svg>
^ The bulkhead lifts B from 0 of 3 served to 3 of 3, at the deliberate cost of capping A from 4 served down to 2 — isolation bought with a slice of A's peak throughput.

**Done means the fault propagation and its containment are proven on real outcomes: the shared pool of 4 slots serves all 4 slow A calls and starves healthy B to 0 of 3, while the bulkhead of 2 slots each caps A to 2 and keeps B at a full 3 of 3 — so independent dependencies need separate, capped partitions, because one shared pool lets a slow dependency's duration, not its volume, consume the whole thing.**

## Boss fight

Predict two ways this bulkhead can be sized or scoped wrong, because a partition is only protection if it is drawn around the right thing and left with enough room.

The first trap is that a bulkhead trades utilization for isolation, and if you cap too tight you cause the very rejections you were trying to prevent. In the fixture, the bulkhead rejected two A calls that the shared pool would have served — that is the cost, and it is only worth paying because it buys B's survival. Size each partition too small and a dependency's normal (not failing) bursts start hitting its cap, so you shed healthy load and lower throughput for no reason; size every partition as large as the whole pool and you are back to a shared pool with extra bookkeeping. The right sizing comes from each dependency's own concurrency need under normal load (roughly its request rate times its latency, by Little's law) plus headroom, deliberately *not* the sum across dependencies — the whole point is that the partitions do not add up to a single borrowable pool. So a bulkhead is a capacity-planning decision per dependency, and the isolation it buys is real only if you accept, up front, that you are giving up the ability of one dependency to burst into another's idle slots.

The second trap is choosing the wrong axis to partition on, and forgetting that a bulkhead contains resource exhaustion but does not by itself stop the calls from being slow. Partition by the thing whose failures you want isolated — usually per downstream dependency, but sometimes per tenant, per endpoint, or per priority class — because a bulkhead only isolates along the axis you cut it on; if two dependencies you lumped into one partition can each saturate it, they still take each other down. And even a correctly scoped bulkhead only guarantees that A cannot steal B's slots; A's own callers still wait and time out on A's saturated partition, so the bulkhead is a containment mechanism that pairs with, not replaces, a timeout (so an A call gives its slot back instead of holding it forever) and a circuit breaker (so once A is known-bad you stop spending A's partition on doomed calls at all). Bulkhead, timeout, and breaker are the three-part answer: the timeout bounds how long a slot is held, the breaker stops feeding a broken dependency, and the bulkhead guarantees that whatever goes wrong with one dependency cannot drain the slots another one needs.

**Size each partition from that dependency's own normal concurrency plus headroom — never the sum across dependencies, or you have rebuilt the shared pool — and cut the bulkhead along the axis whose failures you want isolated (per dependency, tenant, or priority); the partition contains resource exhaustion but not slowness itself, so it must be paired with a per-call timeout that returns the slot and a circuit breaker that stops spending the partition on a dependency already known to be down.**

## External resources

Michael Nygard's "Release It!" — the bulkhead and circuit-breaker stability patterns, and why a shared resource pool is a failure-propagation path between otherwise independent dependencies.

Documentation for resilience libraries (Resilience4j's Bulkhead, Polly's Bulkhead Isolation, Envoy/Istio connection-pool and outlier-detection limits) — how per-dependency concurrency caps are configured and combined with timeouts and breakers in practice.

The companion circuit-breaker, retry-amplification, and connection-pool modules in this topic — a bulkhead is the spatial partner to the breaker's temporal isolation, and sizing a partition uses the same Little's-law reasoning as sizing the pool it is carved from.
