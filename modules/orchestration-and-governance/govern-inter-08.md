---
id: govern-inter-08
title: Bound the queue and apply backpressure — an unbounded buffer turns overload into a slow crash
topic: orchestration-and-governance
level: intermediate
status: ready
time: 5-8h
summary: A producer hands work to a slower consumer through a queue, and if the producer outpaces the consumer for any sustained stretch the queue grows — unbounded, it grows without limit, and the failure is quiet: memory climbs until the process is killed, and long before that every item waits behind an ever-longer backlog so latency climbs toward infinity while the system still reports itself up. A bounded queue with backpressure refuses to hide the overload: cap the queue and shed the excess when it is full, so depth never exceeds the cap, latency stays bounded, and memory is flat. You lose the shed work, but that work was never going to be served — the consumer's rate is the hard ceiling on throughput, so the only choice is whether the unservable surplus is dropped now with a bounded queue or buffered forever in an unbounded one until the process dies. Over 20 ticks of 5-per-tick arrivals against a 3-per-tick consumer, the unbounded queue grows to 40 and climbing while the bounded queue holds at 10 and sheds the 33 surplus, and both complete the same 60 items the consumer could actually process — so backpressure changes not what gets done but whether the system survives doing it.
eli5: Imagine a sink filling faster than it drains. If the sink is a magic bottomless one, it never overflows — but the water level rises forever, and anything you drop in takes longer and longer to reach the drain, until the whole thing collapses. A normal sink has a rim: once it is full, extra water spills over the side right away. You lose that spilled water either way — the drain can only take so much — but the normal sink never floods the house. Putting a rim on the queue is backpressure: it spills the extra now instead of hoarding it until everything breaks.
---

## Why this module

Anywhere one component produces work for another to consume, there is a queue between them, and that queue is a bet that the consumer can keep up. Usually it can, and the queue stays near empty. But traffic is bursty and consumers are finite, so sooner or later the producer runs faster than the consumer for a while, and the queue fills. What happens then is decided by one design choice made long before the overload: whether the queue is bounded.

An unbounded queue handles overload by accepting everything, and that is exactly the problem. Every item the consumer cannot yet process is held in memory, so under sustained overload the queue depth rises without limit and takes memory with it, until the process is out of memory and killed.

<svg viewBox="0 0 700 150" role="img" aria-label="A producer emitting 5 items per tick into a queue, which drains to a consumer at 3 per tick. The surplus of 2 per tick accumulates in the queue. An unbounded queue lets the surplus pile up forever; a bounded queue has a rim that spills the surplus.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">producer 5/tick → queue → consumer 3/tick: surplus 2/tick must go somewhere</text>
    <rect x="40" y="55" width="90" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="85" y="76" text-anchor="middle" fill="var(--acc-ink)" font-size="8">producer</text>
    <line x1="130" y1="72" x2="200" y2="72" stroke="var(--s1)"></line><text x="165" y="66" text-anchor="middle" fill="var(--s1)" font-size="8">5/tick</text>
    <rect x="200" y="45" width="150" height="55" fill="var(--panel)" stroke="var(--line)"></rect><text x="275" y="72" text-anchor="middle" fill="var(--ink)" font-size="8">QUEUE</text><text x="275" y="90" text-anchor="middle" fill="var(--muted)" font-size="7">+2 every tick</text>
    <line x1="350" y1="72" x2="420" y2="72" stroke="var(--muted)"></line><text x="385" y="66" text-anchor="middle" fill="var(--muted)" font-size="8">3/tick</text>
    <rect x="420" y="55" width="90" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="465" y="76" text-anchor="middle" fill="var(--acc-ink)" font-size="8">consumer</text>
    <text x="540" y="66" fill="var(--s2)" font-size="8">unbounded: piles up</text>
    <text x="540" y="82" fill="var(--s1)" font-size="8">bounded: spills over</text>
  </g>
</svg>
^ Five arrive, three drain, and two per tick have nowhere to go. The unbounded queue stores that surplus in memory forever; the bounded queue spills it at the rim. The mismatch is the same; only the disposal differs. And the damage arrives before the crash: an item entering a queue of depth D behind a consumer of rate R waits roughly D/R before it is served, so as D climbs, latency climbs with it — the system is technically still processing, still "up," while every request it serves is staler than the last. An unbounded queue does not absorb overload; it converts a throughput mismatch into a memory leak and a latency explosion, and hides both until they are fatal.

The fix is to bound the queue and apply backpressure: give it a maximum depth, and when it is full, refuse new work — shed it, or block the producer. Now the depth cannot exceed the cap, so memory is flat and latency is bounded. The cost is the shed work, and the key realization is that this work was never going to be served regardless: the consumer's rate is a hard ceiling, so under sustained overload some arrivals are unservable no matter what, and the only question is whether you drop them promptly (bounded) or hoard them until the process dies (unbounded). This module simulates both against a steady overload and measures depth, completions, and shed. Everything runs offline against a load fixture, stdlib Python 3, `$0.00`. The instinct to unlearn is that a bigger buffer is safer. An unbounded buffer is the most dangerous kind, because it removes the only signal — a full queue — that would have told you to slow down.

## Concepts

Named here so you can find them again; each is built below.

- **Producer / consumer** — one component makes work, another processes it, at possibly different rates.
- **Queue depth** — how many items are waiting; under overload it either grows or is capped.
- **Unbounded queue** — accepts everything; converts overload into unbounded memory and latency.
- **Bounded queue** — a maximum depth; the precondition for backpressure.
- **Backpressure** — refusing new work when full (shed or block), so overload is signaled not hidden.
- **Shed** — dropping the surplus a bounded queue cannot hold; the unservable work made explicit.

## Worked example

Source: the queue between any fast producer and slower consumer — a task dispatcher feeding workers, an ingestion pipeline, a request buffer. The arrival pattern stands in for sustained overload; the tick is any unit of time in which the consumer does a fixed amount of work.

Script and fixture: `modules/orchestration-and-governance/code/govern-inter-08/` — `backpressure.py`, and `load.json`, 20 ticks of overload. Every command runs from there.

### The unbounded queue

The unbounded queue accepts every arrival and processes what it can each tick.

```
# backpressure.py:42-53 — COMPLETE (accept everything; depth grows under sustained overload)
def run_unbounded(data):
    """No cap: accept every arrival, process consumer_rate per tick. Depth grows without limit."""
    rate = data["consumer_rate"]
    depth, completed = 0, 0
    depths = []
    for a in data["arrivals"]:
        depth += a                       # accept everything -- nothing is ever refused
        served = min(depth, rate)
        depth -= served
        completed += served
        depths.append(depth)
    return {"depths": depths, "final": depth, "completed": completed, "shed": 0}
```

`depth += a` with no check is the whole liability — nothing is ever refused, so with arrivals of 5 and a consumer rate of 3, the depth rises by 2 every tick, forever. The bounded queue differs by exactly the missing check.

### The bounded queue with backpressure

The bounded queue computes the free space, accepts only what fits, and sheds the rest.

```
# backpressure.py:56-70 — COMPLETE (cap the depth; shed the surplus that doesn't fit)
def run_bounded(data):
    """Cap the queue; shed arrivals that don't fit. Depth never exceeds the cap."""
    rate, cap = data["consumer_rate"], data["cap"]
    depth, completed, shed = 0, 0, 0
    depths = []
    for a in data["arrivals"]:
        space = cap - depth
        accepted = min(a, space)
        shed += a - accepted             # backpressure: the surplus is dropped, not buffered
        depth += accepted
        served = min(depth, rate)
        depth -= served
        completed += served
        depths.append(depth)
    return {"depths": depths, "final": depth, "completed": completed, "shed": shed}
```

The two lines `space = cap - depth` and `accepted = min(a, space)` are backpressure: once the queue is full, `space` is zero, `accepted` is zero, and the surplus is shed rather than buffered. Run both queues tick by tick:

```
# $ python3 backpressure.py --run   (abbreviated)
#   tick  unbounded depth       bounded depth
#   0     2                     2
#   4     10                    7
#   9     20                    7
#   14    30                    7
#   19    40                    7
```

run: 2026-08-27 · deterministic; the load pattern is a fixture · 20 ticks · `python3 backpressure.py --run`

The unbounded depth is a straight line climbing 2 per tick — 2, 10, 20, 30, 40 — with no ceiling; extend the run to a thousand ticks and it reaches 2000, limited only by when memory runs out. The bounded depth rises to the cap and then flattens at 7, never higher: once full, each tick it accepts exactly what it serves, so it holds steady. One queue's depth is a function of how long the overload has lasted; the other's is a constant. That is the difference between a memory leak and a stable system.

<svg viewBox="0 0 700 200" role="img" aria-label="Queue depth over 20 ticks. The unbounded queue is a straight line rising from 2 to 40 and an arrow showing it continues off the top. The bounded queue rises to about 7-10 and flattens, staying under the cap line at 10.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">queue depth over time: unbounded climbs forever, bounded holds</text>
    <line x1="60" y1="170" x2="660" y2="170" stroke="var(--line)"></line>
    <line x1="60" y1="30" x2="60" y2="170" stroke="var(--line)"></line>
    <line x1="60" y1="130" x2="660" y2="130" stroke="var(--s2)" stroke-dasharray="4 3"></line><text x="664" y="133" fill="var(--s2)" font-size="7">cap 10</text>
    <line x1="60" y1="168" x2="640" y2="40" stroke="var(--s2)"></line><text x="600" y="44" fill="var(--s2)" font-size="8">unbounded ↗ (→ ∞)</text>
    <polyline points="60,168 90,158 120,148 150,141 640,141" fill="none" stroke="var(--s1)"></polyline><text x="500" y="152" fill="var(--s1)" font-size="8">bounded — flat at the cap</text>
    <text x="60" y="188" fill="var(--muted)" font-size="7">tick 0</text><text x="640" y="188" text-anchor="end" fill="var(--muted)" font-size="7">tick 19</text>
    <text x="120" y="30" fill="var(--muted)" font-size="8">memory and latency both track the unbounded line up</text>
  </g>
</svg>
^ The unbounded queue's depth is a rising line with no ceiling — memory and per-item latency climb with it — while the bounded queue flattens at the cap. Sustained overload makes one a slow crash and leaves the other stable.

### Same work done, opposite survival

The surprise is that shedding costs no real throughput. Compare the totals:

```
# $ python3 backpressure.py --summary
#   after 20 ticks, 100 items arrived
#   unbounded: final depth 40   completed 60   shed 0
#   bounded:   final depth 7    completed 60   shed 33
```

run: 2026-08-27 · deterministic · `python3 backpressure.py --summary`

The summary tallies the disposition of all 100 arrivals for each queue — final depth held, completed, and shed:

```
# backpressure.py:90-97 — COMPLETE (tally final depth, completions, and shed for each queue)
def summary_view(data):
    u = run_unbounded(data)
    b = run_bounded(data)
    total = sum(data["arrivals"])
    print("SUMMARY — after %d ticks, %d items arrived" % (len(data["arrivals"]), total))
    print("-" * 60)
    print("  unbounded: final depth %-4d completed %-4d shed %d" % (u["final"], u["completed"], u["shed"]))
    print("  bounded:   final depth %-4d completed %-4d shed %d" % (b["final"], b["completed"], b["shed"]))
```

<svg viewBox="0 0 700 160" role="img" aria-label="Where the 100 arrivals went for each queue. Unbounded: 60 completed, 40 held in memory (a growing backlog), 0 shed. Bounded: 60 completed, 7 held, 33 shed. Both complete 60; the unbounded queue's extra 40 is buffered forever, the bounded queue's surplus is shed.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">where the 100 arrivals went — completions equal, disposal opposite</text>
    <text x="30" y="52" fill="var(--s2)" font-size="8">unbounded</text>
    <rect x="110" y="38" width="300" height="22" fill="var(--s1)"></rect><text x="260" y="53" text-anchor="middle" fill="var(--panel)" font-size="8">completed 60</text>
    <rect x="410" y="38" width="200" height="22" fill="var(--s2)"></rect><text x="510" y="53" text-anchor="middle" fill="var(--panel)" font-size="8">held in memory 40 (→ growing)</text>
    <text x="30" y="102" fill="var(--s1)" font-size="8">bounded</text>
    <rect x="110" y="88" width="300" height="22" fill="var(--s1)"></rect><text x="260" y="103" text-anchor="middle" fill="var(--panel)" font-size="8">completed 60</text>
    <rect x="410" y="88" width="35" height="22" fill="var(--muted)"></rect><text x="427" y="103" text-anchor="middle" fill="var(--panel)" font-size="7">7</text>
    <rect x="445" y="88" width="165" height="22" fill="var(--panel)" stroke="var(--s2)"></rect><text x="527" y="103" text-anchor="middle" fill="var(--s2)" font-size="8">shed now 33</text>
    <text x="110" y="140" fill="var(--muted)" font-size="8">the completed bar is identical; the unbounded queue just hoards its surplus instead of shedding it</text>
  </g>
</svg>
^ Both queues complete the same 60 items. The unbounded queue's other 40 sit in memory as a backlog it will never clear under continuing overload; the bounded queue sheds its surplus and holds only 7. Hoarding buys no extra completions.

One hundred items arrived; both queues completed exactly 60, because 60 is all the consumer could process in 20 ticks at rate 3 — the throughput ceiling is the consumer, not the queue. The unbounded queue "kept" the other 40 by holding them in memory (a backlog it will never clear while overload continues); the bounded queue shed 33 and holds 7. Neither served more than 60. So the unbounded queue bought nothing for its unbounded memory — the extra items it hoarded are exactly the ones it was never going to get to. Shedding does not lose work that would otherwise have been done; it drops work that was always going to be unservable, and does so before the hoarding kills the process.

**A queue between a fast producer and a slow consumer must be bounded with backpressure, because an unbounded queue converts sustained overload into unbounded memory and latency (depth climbs 2/tick to 40 and beyond) while a bounded queue holds depth at the cap and sheds the surplus — and both complete the same 60 items, since the consumer's rate is the throughput ceiling, so the only choice is dropping the unservable surplus now or hoarding it until the process dies.**

### The self-test

The `--check` mode plants the bug — the unbounded queue — and proves it: the unbounded depth keeps growing, the bounded depth stays under the cap and sheds the surplus, and both complete the same work.

```
# $ python3 backpressure.py --check
#   the unbounded queue depth keeps growing = True (2 -> 22 -> 40)
#   the bounded queue never exceeds the cap = True (max 7 <= 10)
#   the bounded queue sheds the surplus (not buffered) = True (33 shed)
#   both complete the same work (consumer-limited) = True (60 each)
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 backpressure.py --check`

The `same_completed` line is the one that defuses the objection to shedding — that you are "throwing away work." Both queues finish the same 60 items, so the bounded queue threw away nothing the unbounded queue would have completed; it only refused to store what could not be served. Combined with `bounded_capped`, it says the bounded queue is strictly better under overload: same throughput, bounded memory, bounded latency.

```
# backpressure.py:114-118 — COMPLETE (bounded depth stays under the cap and sheds the surplus)
    bounded_capped = max(b["depths"]) <= cap
    print("  the bounded queue never exceeds the cap = %s (max %d <= %d)"
          % (bounded_capped, max(b["depths"]), cap))

    bounded_sheds = b["shed"] > 0
    print("  the bounded queue sheds the surplus (not buffered) = %s (%d shed)" % (bounded_sheds, b["shed"]))
```

### The running tally

| queue | final depth | completed | shed | memory | latency |
|---|---|---|---|---|---|
| unbounded | 40 (→ ∞) | 60 | 0 | grows without limit | grows without limit |
| bounded | 7 (≤ cap 10) | 60 | 33 | flat | bounded |

Read the completed column: it is identical, 60 for both, which is the crux — the queue choice does not change throughput, only what happens to the surplus. Then read every other column: the unbounded queue pays for its zero shed with unbounded memory and latency, ending at depth 40 and rising, while the bounded queue pays a shed count of 33 for flat memory and bounded latency. The unbounded queue's apparent virtue (it never drops anything) is the exact mechanism of its failure, because "never drops anything" under permanent overload means "grows forever." Backpressure trades a visible, bounded loss for an invisible, unbounded one avoided.

### What we did not settle

This is the core of bounded queues; production tunes the details. Shedding is one backpressure policy; blocking the producer (so it slows to the consumer's rate) is another, appropriate when the producer can wait and the work must not be lost — and the two compose across a pipeline, where backpressure propagates upstream stage by stage. What to shed matters: dropping the oldest (which has waited longest and may be stale) often beats dropping the newest, and priority-aware shedding keeps important work. The cap is a real tuning knob — too small wastes consumer capacity on transient bursts a slightly larger buffer would have absorbed, too large reintroduces latency — and is often set from a target maximum latency (cap ≈ rate × acceptable wait). Shed events should be surfaced as a load signal (they are how you learn you are over capacity) and paired with autoscaling the consumer. The invariant: every queue needs a bound, because the alternative to shedding under overload is not keeping the work, it is losing the process.

## Build

The build in one paragraph: give every producer-consumer queue a maximum depth and a backpressure policy — shed the surplus, or block the producer to the consumer's rate — so that under sustained overload the depth stays capped, memory stays flat, and latency stays bounded, accepting that the shed work was unservable anyway because the consumer's rate is the throughput ceiling. Size the cap from a target maximum latency, choose shed-oldest or priority-aware shedding, propagate backpressure upstream across pipeline stages, and treat shed events as a load signal that triggers autoscaling.

We opened on the two queues. The number that proves the point is the depth and completions of each:

```
# modules/orchestration-and-governance/code/govern-inter-08/ — COMPLETE, run from that directory
$ python3 backpressure.py --summary
  unbounded: final depth 40   completed 60   shed 0
  bounded:   final depth 7    completed 60   shed 33
```

Now build your own. Take a real producer-consumer path with a sustained-overload arrival pattern, and run it through an unbounded queue and a bounded one with backpressure. Your number to beat is not completions — they are equal; it is **the peak queue depth (and hence memory and latency), unbounded versus bounded** — the unbounded queue should climb without limit while the bounded one holds at the cap, and both complete the same consumer-limited total. Confirm the shed work was never servable. Bring back both peak depths. Good luck.

## Definition of done

- [ ] An unbounded queue that accepts every arrival and processes a fixed rate per tick
- [ ] A bounded queue with a cap that sheds arrivals that do not fit
- [ ] Per-tick depth tracking for both under sustained overload
- [ ] Confirmation the unbounded depth grows without limit
- [ ] Confirmation the bounded depth never exceeds the cap and sheds the surplus
- [ ] Confirmation both complete the same consumer-limited work
- [ ] `python3 backpressure.py --check` printing SELF-TEST PASS: unbounded_grows, bounded_capped, bounded_sheds, same_completed
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why is an unbounded queue dangerous under sustained overload? What two things grow without limit?
2. What is backpressure, and what are two policies for applying it?
3. Both queues completed 60 items. Why does shedding cost no real throughput?
4. What sets the throughput ceiling — the queue size or the consumer rate?
5. Your own producer-consumer path was run both ways. What peak depth did each reach, and did completions match?

## External resources

- Reactive Streams / backpressure documentation (any framework) — my summary: the contract by which a slow consumer signals a fast producer to slow down, propagated across a pipeline; read it for the block-the-producer policy this module contrasts with shedding.
- Google SRE Book on load shedding and graceful degradation — my summary: why dropping load early beats collapsing under it, and how to shed by priority; read it for the shedding policies and the load-signal use of shed events.
- This hub, *ship-inter-03* (token bucket) and *ship-inter-07* (jitter) — read them for the per-client rate cap and the de-synchronization that reduce the overload a queue must absorb in the first place.
