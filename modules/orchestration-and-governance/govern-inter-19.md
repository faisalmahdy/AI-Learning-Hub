---
id: govern-inter-19
title: Send a backup request after a short delay — or one slow replica sets your whole tail latency
topic: orchestration-and-governance
level: intermediate
status: ready
time: 19 min
summary: A request goes to one replica and waits for it. Most replicas are fast, but a few are slow at any moment — a GC pause, a busy disk, a noisy neighbor — and a request that lands on one waits the full straggler time even though nothing is wrong with the request. Across many requests these unlucky ones set the tail: the 99th-percentile latency is dominated by the slowest replica each request happened to hit, and you cannot fix that by making the median faster. Hedged requests attack it directly — wait a short delay, and if the primary hasn't answered, send the same request to a second replica and take whichever returns first. The straggler is rescued for the cost of a few extra requests, only the ones that crossed the delay. On nine ~12ms requests and one 200ms straggler with a 20ms hedge delay, the tail drops from 200ms to 35ms for one extra request.
eli5: If you order food from one kitchen and it is having a bad night, you wait forever even though every other kitchen is fine. Hedging is: if your order isn't ready in a little while, quietly place the same order at a second kitchen and eat whichever comes first. You only double-order the few that are running late, so most nights cost nothing extra, and you are never stuck waiting on the one slow kitchen.
---

## Why this module

The slowest replica a request happens to hit, not the typical one, decides how long that request takes — and across a fleet, those unlucky hits are your tail latency.

Send a request to one replica and you are betting on that replica being fast right now. Usually it is. But replicas have transient slow spells — garbage collection, a busy disk, a neighbor hogging the CPU — and when your request lands during one, it waits the full slow time. Nothing is wrong with the request; it was just unlucky. Multiply across thousands of requests and these unlucky ones form the tail: the 99th percentile is set by whichever replica each request hit on its worst moment. Making the average replica faster does not help, because the tail is about the worst draw, not the mean.

**Tail latency comes from the variance across replicas, not the mean, so a request is only as fast as the replica it happened to land on at that instant.**

Hedged requests cut the tail at its source. Wait a short delay — long enough that a healthy request has usually answered — and if the primary is still silent, send the same request to a second replica and take whichever returns first. A straggler is rescued: instead of waiting out the slow replica, you wait the delay plus a fresh replica's normal time. This module runs a batch both ways and measures the tail drop against the extra-request cost.

## Concepts

The **primary** is the first replica a request goes to; its latency is the request's completion time when there is no hedging. Across the batch, the **tail** is the maximum (here standing in for a high percentile) — the worst completion time.

A **hedge** is a duplicate request sent to a second replica after a **hedge delay**. If the primary answers before the delay, no hedge is sent — the fast majority cost nothing. If the primary is still outstanding at the delay, the backup goes out, and the request completes at whichever finishes first: min(primary, delay + backup).

The mechanism is that stragglers are usually uncorrelated with the request. The same query on a different replica is likely fast, because it was the replica, not the query, that was slow. So the backup almost always beats the lingering primary, turning a 200ms straggler into delay-plus-normal.

The cost is controlled by the delay. Only requests slower than the delay ever hedge, so setting the delay near the 95th percentile means about 5% of requests send a backup — a small, bounded increase in load for a large cut in the tail. Set the delay too low and everything hedges (doubling load); too high and stragglers wait a long time before rescue.

**Hedging trades a small, tunable amount of extra load for a large tail reduction, and the delay is the knob that sets the trade.**

The delay splits requests into two populations: the fast majority that finish before it and cost nothing, and the rare stragglers past it that each earn a backup.

<svg role="img" aria-label="A latency axis with a delay line: most requests fall left of the delay and send no hedge, a few fall right and each trigger a backup" viewBox="0 0 300 100" width="300" height="100">
  <line x1="20" y1="55" x2="285" y2="55" stroke="var(--grid)" stroke-width="1"/>
  <line x1="90" y1="20" x2="90" y2="70" stroke="var(--s1)" stroke-width="1.5" stroke-dasharray="3 2"/>
  <text x="72" y="16" fill="var(--s1)" font-size="8">hedge delay</text>
  <circle cx="35" cy="55" r="3" fill="var(--s2)"/><circle cx="48" cy="55" r="3" fill="var(--s2)"/><circle cx="55" cy="55" r="3" fill="var(--s2)"/><circle cx="62" cy="55" r="3" fill="var(--s2)"/><circle cx="70" cy="55" r="3" fill="var(--s2)"/><circle cx="78" cy="55" r="3" fill="var(--s2)"/>
  <text x="30" y="82" fill="var(--s2)" font-size="7">no hedge (free)</text>
  <circle cx="260" cy="55" r="4" fill="var(--s1)"/>
  <text x="200" y="82" fill="var(--s1)" font-size="7">straggler → backup sent</text>
</svg>
^ The delay line separates the cheap majority (left, primary answers first) from the rare stragglers (right) that each trigger one backup — so the extra load is only the right-hand tail.

The point is that this is cheap precisely because it is selective: the healthy majority never trigger it, and only the rare straggler pays for a second request.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/govern-inter-19/hedge.py

The fixture is ten requests — nine fast, one straggler — plus the hedge delay.

```json filename=modules/orchestration-and-governance/code/govern-inter-19/requests.json:1-6 COMPLETE
{
  "_meta": "A batch of requests, each served by a replica. primary_ms is how long each request's first replica takes; backup_ms is how long a second replica would take if we also asked it. One request (index 4) hits a slow replica -- a straggler at 200ms while the rest are ~12ms. hedge_delay_ms is how long we wait before sending a backup request: if the primary has not answered by then, we ask a second replica and take whichever returns first.",
  "primary_ms": [10, 12, 11, 13, 200, 14, 12, 11, 13, 12],
  "backup_ms":  [15, 15, 15, 15, 15, 15, 15, 15, 15, 15],
  "hedge_delay_ms": 20
}
```

Completion without hedging is just the primary's time. With hedging, a request that beats the delay uses the primary; otherwise it races the primary against a backup sent at the delay.

```python filename=modules/orchestration-and-governance/code/govern-inter-19/hedge.py:40-53 COMPLETE
def no_hedge(primary):
    """Completion time with one replica: just the primary's latency."""
    return primary


def hedged(primary, backup, delay):
    """If the primary answers before the delay, use it; else race it against a backup sent at the delay."""
    if primary <= delay:
        return primary                      # primary already back before we would hedge
    return min(primary, delay + backup)     # backup sent at `delay`, take whichever is first


def hedge_fired(primary, delay):
    return primary > delay
```

Run `--latency` per request.

```text filename=--latency
LATENCY — completion per request, no hedge vs hedge (delay 20ms)
------------------------------------------------------------
  req   primary   no-hedge   hedged   note
   0       10ms      10ms      10ms   
   1       12ms      12ms      12ms   
   2       11ms      11ms      11ms   
   3       13ms      13ms      13ms   
   4      200ms     200ms      35ms   hedged (backup raced)
   5       14ms      14ms      14ms   
   6       12ms      12ms      12ms   
   7       11ms      11ms      11ms   
   8       13ms      13ms      13ms   
   9       12ms      12ms      12ms   
------------------------------------------------------------
  only the straggler crosses the delay and gets a backup.
```

Nine requests are identical in both columns — they answered before the 20ms delay, so no backup was ever sent. Only request 4, the 200ms straggler, crossed the delay: its backup was sent at 20ms, finished at 20 + 15 = 35ms, and beat the still-running primary. One request hedged; the rest were untouched.

<svg role="img" aria-label="Nine requests finish near 12ms; the straggler primary reaches 200ms but its hedged completion is 35ms" viewBox="0 0 300 130" width="300" height="130">
  <line x1="30" y1="15" x2="30" y2="105" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="105" x2="285" y2="105" stroke="var(--grid)" stroke-width="1"/>
  <line x1="52" y1="15" x2="52" y2="105" stroke="var(--grid)" stroke-width="1" stroke-dasharray="2 2"/>
  <text x="40" y="120" fill="var(--muted)" font-size="7">20ms delay</text>
  <rect x="30" y="20" width="12" height="6" fill="var(--s2)"/>
  <rect x="30" y="28" width="14" height="6" fill="var(--s2)"/>
  <rect x="30" y="36" width="13" height="6" fill="var(--s2)"/>
  <text x="60" y="34" fill="var(--muted)" font-size="7">nine fast (~12ms), no hedge</text>
  <rect x="30" y="52" width="240" height="8" fill="var(--s1)"/>
  <text x="150" y="50" fill="var(--s1)" font-size="7">straggler primary 200ms</text>
  <rect x="30" y="66" width="42" height="8" fill="var(--s2)"/>
  <text x="76" y="73" fill="var(--s2)" font-size="7">hedged: 35ms (rescued)</text>
</svg>
^ The nine fast requests never reach the delay line; the straggler's primary runs far off to 200ms, but its hedged completion stops at 35ms — the delay plus a fresh replica.

## Build

The tail view takes the max each way and counts how many requests crossed the delay.

```python filename=modules/orchestration-and-governance/code/govern-inter-19/hedge.py:71-81 COMPLETE
def tail_view(data):
    pr, bk, d = data["primary_ms"], data["backup_ms"], data["hedge_delay_ms"]
    nh = [no_hedge(p) for p in pr]
    hg = [hedged(pr[i], bk[i], d) for i in range(len(pr))]
    extra = sum(1 for p in pr if hedge_fired(p, d))
    print("TAIL — worst-case latency and extra request cost")
    print("-" * 60)
    print("  tail (max) latency:  no-hedge %dms   hedged %dms" % (max(nh), max(hg)))
    print("  extra requests sent: %d of %d (%.0f%%)" % (extra, len(pr), 100 * extra / len(pr)))
    print("-" * 60)
    print("  a %dx tail reduction for %.0f%% more requests." % (max(nh) // max(hg), 100 * extra / len(pr)))
```

Aggregate it with `--tail`.

```text filename=--tail
TAIL — worst-case latency and extra request cost
------------------------------------------------------------
  tail (max) latency:  no-hedge 200ms   hedged 35ms
  extra requests sent: 1 of 10 (10%)
------------------------------------------------------------
  a 5x tail reduction for 10% more requests.
```

The tail falls from 200ms to 35ms — the single straggler that defined the tail is gone — while total load rose by one request in ten. That is the whole bargain: the tail is set by the worst request, so rescuing just the worst requests moves it a lot, and rescuing only them keeps the extra load small. In a real fleet where the delay sits at the 95th percentile, the extra load is nearer 5%, and the tail cut is just as dramatic.

<svg role="img" aria-label="Tail latency drops from 200ms without hedging to 35ms with hedging, at the cost of 10 percent more requests" viewBox="0 0 300 120" width="300" height="120">
  <line x1="70" y1="12" x2="70" y2="85" stroke="var(--grid)" stroke-width="1"/>
  <line x1="70" y1="85" x2="285" y2="85" stroke="var(--grid)" stroke-width="1"/>
  <rect x="70" y="20" width="200" height="16" fill="var(--s1)"/><text x="200" y="32" fill="var(--panel)" font-size="8">no-hedge 200ms</text>
  <rect x="70" y="45" width="35" height="16" fill="var(--s2)"/><text x="110" y="57" fill="var(--muted)" font-size="8">hedged 35ms</text>
  <text x="70" y="103" fill="var(--muted)" font-size="8">tail cut ~5x for +10% requests (near 5% when tuned to p95)</text>
</svg>
^ The tail bar shrinks from 200ms to 35ms while the request count barely moves — the defining trade of hedging.

## Definition of done

The self-test pins the trade: hedging lowers the tail, the straggler is rescued, only a small fraction hedged, fast requests sent no backup, and the hedged time is exactly min(primary, delay+backup).

```python filename=modules/orchestration-and-governance/code/govern-inter-19/hedge.py:93-105 COMPLETE
    hedge_cuts_tail = max(hg) < max(nh)
    print("  hedging lowers the tail latency = %s (%dms -> %dms)" % (hedge_cuts_tail, max(nh), max(hg)))

    straggler_rescued = hg[s] < pr[s]
    print("  the straggler is rescued = %s (req %d: %dms -> %dms)" % (straggler_rescued, s, pr[s], hg[s]))

    few_extra_requests = extra < len(pr) / 2
    print("  only a small fraction hedged = %s (%d of %d)" % (few_extra_requests, extra, len(pr)))

    fast_requests_no_hedge = all(not hedge_fired(p, d) for p in pr if p <= d)
    print("  requests answered before the delay sent no backup = %s" % fast_requests_no_hedge)

    hedge_is_min = hg[s] == min(pr[s], d + bk[s])
    print("  the hedged time is min(primary, delay+backup) = %s (min(%d, %d+%d)=%d)" % (hedge_is_min, pr[s], d, bk[s], hg[s]))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — hedging rescues the straggler and cuts the tail for only a few extra requests
----------------------------------------------------------------------------------------------------
  hedging lowers the tail latency = True (200ms -> 35ms)
  the straggler is rescued = True (req 4: 200ms -> 35ms)
  only a small fraction hedged = True (1 of 10)
  requests answered before the delay sent no backup = True
  the hedged time is min(primary, delay+backup) = True (min(200, 20+15)=35)
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  hedge_cuts_tail=True  straggler_rescued=True  few_extra_requests=True  fast_requests_no_hedge=True  hedge_is_min=True
```

**Done means the trade is quantified, not hoped for: the tail drops from 200ms to 35ms while exactly one of ten requests sent a backup, and the rescued time is the provable min of primary and delay-plus-backup.**

## Boss fight

Hedging cut the tail cheaply here. Predict what happens if you drop the hedge delay to 0 — send both requests immediately, always. It is tempting to think earlier is better.

Zero delay doubles your load, and that is the failure mode. With no delay every request hedges, so you send two requests for all of them, not just the stragglers — the "small fraction" becomes 100%, and a system already near capacity tips over from the doubled traffic. The delay is what makes hedging cheap: it lets the fast majority finish on the primary alone and only spends a backup on the rare slow one. The whole art is picking a delay high enough to spare the healthy requests and low enough to rescue stragglers quickly — typically the 95th or 99th percentile of normal latency.

The mirror-image mistake is hedging a request with side effects. Sending the same write to two replicas means the write can happen twice — a duplicate charge, a double insert. Hedging is safe for idempotent reads, and for anything else it must be paired with the idempotency-key discipline so the duplicate is deduplicated at the destination. And a hedge must cancel the loser: if the primary eventually answers after the backup won, the system should drop it, or slow replicas keep doing work nobody needs.

```python filename=modules/orchestration-and-governance/code/govern-inter-19/hedge.py:45-49 COMPLETE
def hedged(primary, backup, delay):
    """If the primary answers before the delay, use it; else race it against a backup sent at the delay."""
    if primary <= delay:
        return primary                      # primary already back before we would hedge
    return min(primary, delay + backup)     # backup sent at `delay`, take whichever is first
```

**Hedge with a delay near a high percentile so only stragglers trigger a backup — zero delay doubles load, and hedging non-idempotent requests double-applies them unless the duplicate is deduplicated.**

## External resources

Dean and Barroso, "The Tail at Scale" (Communications of the ACM, 2013) — the paper that named hedged and tied requests and showed a small backup rate slashing p99 in Google services.

The gRPC and Envoy documentation on request hedging and retries — how hedging is configured in production RPC systems, including the delay and the cap on extra attempts.

The companion tail-latency module ("track the p99") and the idempotency-key module — hedging is why you measure the tail and why the boss fight insists on idempotent requests.
