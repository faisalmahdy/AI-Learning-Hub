---
id: loadshed-inter-01
title: Shed low-priority requests first under overload — first-come-first-served spends scarce capacity on best-effort traffic
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: When demand exceeds what a server can handle, some requests will not be served — that is arithmetic. The question the server actually decides is not whether to drop requests but which ones, and the default answer, made by doing nothing special, is to admit in arrival order until capacity is full and turn away the rest. First-come-first-served is indiscriminate under overload: it fills the last scarce slots with whatever arrived early — a prefetch, an analytics beacon, a retry of something already abandoned — while a high-value request that arrived a moment later gets turned away. The server stayed busy; it just spent its scarcest resource on the wrong work. Load shedding makes the choice deliberately: when over capacity, drop low-priority requests first, reserving the limited slots for high-priority ones — a checkout, a payment, a health probe that keeps the instance in the load balancer — while shedding a prefetch or background sync with a fast rejection. Shedding does not create capacity and serves no more requests than first-come-first-served — both serve exactly the capacity — it spends that same capacity on the requests that matter. The rejection must be cheap to be worth it (a quick 503 with Retry-After before expensive work), and priority must reflect real value or you shed the wrong thing, but the core move is the difference between an overload that degrades gracefully and one where important requests are dropped alongside unimportant ones by arrival timing. On a burst of 7 requests for 4 slots (3 high-priority, interleaved), arrival-order admission serves 2 of 3 high-priority and drops one high-priority while serving a low-priority, whereas shedding serves all 3 high-priority plus the earliest low, dropping only low-priority — both serving exactly 4.
eli5: Imagine a small lifeboat that only fits four people, and seven are waiting. Someone has to be left behind — that part cannot be helped. But if you just take the first four who happen to walk up, you might fill the boat with people who were only there to watch, and leave behind someone who really needed a seat, purely because of who showed up first. The better rule is to load the people who most need the boat first, and only fill leftover seats with the others. You are not making the boat bigger — it still holds four — you are just making sure the four seats go to the people who need them, instead of to whoever arrived early.
---

## Why this module

Every server has a capacity, and sooner or later demand exceeds it — a traffic spike, a dependency slowdown that backs work up, a retry storm. When that happens, requests will be dropped; there is no policy that serves more than capacity. What a lot of systems miss is that this is a decision, and if you do not make it deliberately, it gets made for you in the worst possible way: by arrival order. The failure is quiet because the server looks healthy — it is serving requests at full capacity — while the specific requests it drops are chosen by nothing more meaningful than who happened to arrive when the queue filled.

First-come-first-served feels fair, and for uniform traffic it is fine. Under overload with mixed-value traffic it is a liability, because the last few scarce slots go to whatever arrived early, and early does not mean important. A background prefetch that fired at the top of the burst takes a slot; a checkout request that arrived a fraction later is turned away. The system spent its scarcest resource — the ability to serve one more request — on best-effort work and dropped the request a user was actually waiting on. Nothing errored; the capacity was simply misallocated.

Load shedding fixes the allocation by choosing on purpose. This module runs the same overloaded burst through arrival-order admission and priority-based shedding and shows which requests each one saves.

**Under overload, shed low-priority requests first with a cheap rejection, reserving scarce capacity for high-priority requests, rather than admitting in arrival order until full, because first-come-first-served spends the last slots on whatever arrived early — including best-effort traffic — and drops high-value requests that happened to arrive later.**

## Concepts

The fixture is a burst of 7 requests arriving at a server with capacity 4. Priorities are interleaved in arrival order: low, high, low, high, low, high, low. Three requests are high-priority (must-serve — a checkout, a health probe), four are low (best-effort — a prefetch, an analytics ping). Three of the seven must be dropped no matter what; the policy decides which three.

```json filename=modules/ship-and-operate/code/loadshed-inter-01/loadshed.json:12-20 COMPLETE
  "requests": [
    {"id": "r1", "priority": "low"},
    {"id": "r2", "priority": "high"},
    {"id": "r3", "priority": "low"},
    {"id": "r4", "priority": "high"},
    {"id": "r5", "priority": "low"},
    {"id": "r6", "priority": "high"},
    {"id": "r7", "priority": "low"}
  ]
```

Arrival-order admission is the do-nothing policy: take the first `capacity` requests, drop the rest.

```python filename=modules/ship-and-operate/code/loadshed-inter-01/loadshed.py:47-51 COMPLETE
def admit_fifo(requests, capacity):
    """Arrival-order admission: fill the slots with the first `capacity` requests, drop the rest."""
    served = requests[:capacity]
    dropped = requests[capacity:]
    return served, dropped
```

Load shedding orders by priority first, then arrival, and serves the top `capacity`. High-priority requests sort ahead of low regardless of when they arrived, so they claim the scarce slots; low-priority requests fill only what is left.

```python filename=modules/ship-and-operate/code/loadshed-inter-01/loadshed.py:54-61 COMPLETE
def admit_shed(requests, capacity):
    """Load shedding: order by priority (high first), then arrival; serve the top `capacity`, shed the rest."""
    ordered = sorted(enumerate(requests), key=lambda p: (PRIORITY_RANK[p[1]["priority"]], p[0]))
    served_ids = {requests[i]["id"] for i, _ in ordered[:capacity]}
    served = [r for r in requests if r["id"] in served_ids]
    dropped = [r for r in requests if r["id"] not in served_ids]
    return served, dropped
```

<svg role="img" aria-label="Seven requests in arrival order with four capacity slots; FIFO fills slots with the first four, cutting off after r4 and dropping high-priority r6, while shedding pulls the three high requests plus r1 into the slots" viewBox="0 0 320 150">
  <text x="10" y="18" font-size="9" fill="var(--muted)">arrival: r1(l) r2(h) r3(l) r4(h) r5(l) r6(h) r7(l) — capacity 4</text>
  <text x="10" y="42" font-size="8.5" fill="var(--s2)">FIFO</text>
  <rect x="45" y="30" width="30" height="18" fill="var(--muted)"/><text x="52" y="43" font-size="8" fill="var(--panel)">r1 l</text>
  <rect x="77" y="30" width="30" height="18" fill="var(--s1)"/><text x="84" y="43" font-size="8" fill="var(--panel)">r2 h</text>
  <rect x="109" y="30" width="30" height="18" fill="var(--muted)"/><text x="116" y="43" font-size="8" fill="var(--panel)">r3 l</text>
  <rect x="141" y="30" width="30" height="18" fill="var(--s1)"/><text x="148" y="43" font-size="8" fill="var(--panel)">r4 h</text>
  <line x1="173" y1="26" x2="173" y2="52" stroke="var(--ink)" stroke-width="1.5"/>
  <text x="176" y="36" font-size="7.5" fill="var(--muted)">cutoff</text>
  <rect x="177" y="30" width="30" height="18" fill="none" stroke="var(--line)"/><text x="184" y="43" font-size="8" fill="var(--muted)">r5</text>
  <rect x="209" y="30" width="30" height="18" fill="none" stroke="var(--s1)" stroke-dasharray="2 2"/><text x="215" y="43" font-size="8" fill="var(--s2)">r6 h✗</text>
  <rect x="241" y="30" width="30" height="18" fill="none" stroke="var(--line)"/><text x="248" y="43" font-size="8" fill="var(--muted)">r7</text>
  <text x="10" y="92" font-size="8.5" fill="var(--s1)">shed</text>
  <rect x="45" y="80" width="30" height="18" fill="var(--s1)"/><text x="52" y="93" font-size="8" fill="var(--panel)">r2 h</text>
  <rect x="77" y="80" width="30" height="18" fill="var(--s1)"/><text x="84" y="93" font-size="8" fill="var(--panel)">r4 h</text>
  <rect x="109" y="80" width="30" height="18" fill="var(--s1)"/><text x="116" y="93" font-size="8" fill="var(--panel)">r6 h</text>
  <rect x="141" y="80" width="30" height="18" fill="var(--muted)"/><text x="148" y="93" font-size="8" fill="var(--panel)">r1 l</text>
  <text x="178" y="93" font-size="8" fill="var(--muted)">drops r3,r5,r7 (all low)</text>
  <text x="45" y="120" font-size="8.5" fill="var(--s2)">FIFO: 2 of 3 high served, r6 dropped</text>
  <text x="45" y="134" font-size="8.5" fill="var(--s1)">shed: 3 of 3 high served</text>
</svg>
^ FIFO's cutoff falls after r4, so high-priority r6 lands outside it and is dropped while low-priority r3 sits inside. Shedding pulls all three high requests into the four slots and fills the last with the earliest low — same four slots, better occupants.

**Both policies serve exactly four requests; the only difference is whether the four slots are chosen by arrival time or by value, and under overload those pick very different requests.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the admission-control step of an overloaded service, reduced to a seven-request burst so every admission decision is checkable by hand.

Run `--burst` to see the incoming traffic and the shortfall.

```text filename=loadshed.py --burst
  arrival: r1(l) r2(h) r3(l) r4(h) r5(l) r6(h) r7(l)
  demand = 7 requests ; capacity = 4 ; must drop 3
  high-priority in burst = 3 ; low-priority = 4
```

Seven requests, four slots: three must be dropped. There are exactly three high-priority requests — so it is possible to serve all of them and still have a slot to spare, if the policy chooses to. Whether it does is the whole question.

Now `--admit` runs both policies.

```text filename=loadshed.py --admit
  arrival order:  serves ['r1', 'r2', 'r3', 'r4'] (high 2/3)
                  drops  ['r5', 'r6', 'r7']  <- dropped a HIGH-priority request!
  load shedding:  serves ['r1', 'r2', 'r4', 'r6'] (high 3/3)
                  drops  ['r3', 'r5', 'r7'] (all low-priority)
  both serve exactly 4; shedding spends the same capacity on all 3 high-priority requests
```

Arrival order takes r1 through r4 — that is one low, one high, one low, one high — serving 2 of the 3 high-priority requests and dropping r6, a high-priority request, along with the low-priority r5 and r7. It spent a slot on r3 (low) while turning away r6 (high), purely because r3 arrived earlier. Load shedding serves r2, r4, and r6 — all three high-priority — plus r1, the earliest low, and drops only low-priority requests. Both served four requests; shedding just did not waste one of those four on a best-effort request while a critical one waited.

**Arrival order dropped a checkout to serve a prefetch that merely arrived first; shedding served every high-priority request with the same four slots — the capacity was identical, the allocation was not.**

## Build

The self-test asserts the setup and the divergence: that demand genuinely exceeds capacity, that arrival order drops a high-priority request, that shedding serves all of them, and that shedding drops only low-priority requests.

```python filename=modules/ship-and-operate/code/loadshed-inter-01/loadshed.py:96-108 COMPLETE
    demand_exceeds_capacity = len(reqs) > cap
    print("  demand exceeds capacity (some requests must be dropped) = %s (%d > %d)" % (demand_exceeds_capacity, len(reqs), cap))

    naive_drops_high = high_count(fd) > 0
    print("  arrival-order admission drops a high-priority request = %s (dropped high: %s)" % (naive_drops_high, [r["id"] for r in fd if r["priority"] == "high"]))

    shedding_serves_all_high = high_count(ss) == total_high
    print("  load shedding serves ALL high-priority requests = %s (%d/%d)" % (shedding_serves_all_high, high_count(ss), total_high))

    shedding_drops_only_low = high_count(sd) == 0
    print("  load shedding drops only low-priority requests = %s" % shedding_drops_only_low)

    same_total_served = len(fs) == len(ss) == cap
    print("  both admission policies serve exactly the capacity = %s (%d == %d == %d)" % (same_total_served, len(fs), len(ss), cap))
```

<svg role="img" aria-label="Two stacked bars of four served slots: FIFO with 2 high and 2 low, shedding with 3 high and 1 low, both totaling four" viewBox="0 0 320 120">
  <text x="10" y="30" font-size="9" fill="var(--s2)">arrival order</text>
  <rect x="100" y="18" width="45" height="20" fill="var(--s1)"/><rect x="145" y="18" width="45" height="20" fill="var(--s1)"/>
  <rect x="190" y="18" width="45" height="20" fill="var(--muted)"/><rect x="235" y="18" width="45" height="20" fill="var(--muted)"/>
  <text x="112" y="32" font-size="8" fill="var(--panel)">high</text><text x="157" y="32" font-size="8" fill="var(--panel)">high</text>
  <text x="204" y="32" font-size="8" fill="var(--panel)">low</text><text x="249" y="32" font-size="8" fill="var(--panel)">low</text>
  <text x="10" y="76" font-size="9" fill="var(--s1)">load shedding</text>
  <rect x="100" y="64" width="45" height="20" fill="var(--s1)"/><rect x="145" y="64" width="45" height="20" fill="var(--s1)"/>
  <rect x="190" y="64" width="45" height="20" fill="var(--s1)"/><rect x="235" y="64" width="45" height="20" fill="var(--muted)"/>
  <text x="112" y="78" font-size="8" fill="var(--panel)">high</text><text x="157" y="78" font-size="8" fill="var(--panel)">high</text>
  <text x="202" y="78" font-size="8" fill="var(--panel)">high</text><text x="249" y="78" font-size="8" fill="var(--panel)">low</text>
  <text x="100" y="104" font-size="8.5" fill="var(--muted)">same 4 slots — shedding fits all 3 high, arrival order only 2</text>
</svg>
^ The four served slots, both policies: arrival order fills two with high and two with low; shedding fills three with high and one with low. Identical total, one more critical request served.

Running the check confirms every clause, including that shedding preserves more high-priority than arrival order.

```text filename=loadshed.py --check
  demand exceeds capacity (some requests must be dropped) = True (7 > 4)
  arrival-order admission drops a high-priority request = True (dropped high: ['r6'])
  load shedding serves ALL high-priority requests = True (3/3)
  load shedding drops only low-priority requests = True
  both admission policies serve exactly the capacity = True (4 == 4 == 4)
  shedding preserves more high-priority than arrival order = True (3 > 2)
```

**The check pins that shedding serves the same count but a better set — all high-priority preserved, only low dropped — so the win is allocation, proven against a genuine shortfall.**

## Definition of done

Two properties close it, and together they say shedding is a reallocation, not a capacity increase. Both policies serve exactly the capacity — shedding is not magic, it does not squeeze in more — and shedding preserves strictly more high-priority requests, dropping only low-priority ones. The equal-total clause is what keeps the module honest: the benefit is entirely in which requests survive.

```python filename=modules/ship-and-operate/code/loadshed-inter-01/loadshed.py:110-113 COMPLETE
    shedding_preserves_more_high = high_count(ss) > high_count(fs)
    print("  shedding preserves more high-priority than arrival order = %s (%d > %d)" % (shedding_preserves_more_high, high_count(ss), high_count(fs)))

    ok = demand_exceeds_capacity and naive_drops_high and shedding_serves_all_high and shedding_drops_only_low and same_total_served and shedding_preserves_more_high
```

Two conditions make shedding actually pay off, stated so it is not mis-applied. First, the rejection must be cheap: a shed request has to be turned away quickly — a fast 503 with a Retry-After, before it consumes the expensive work (the database query, the model call) — or you have not freed capacity, you have just relabeled a slow failure, and the shed request still competed for the resource. Second, priority must reflect real value and be hard to game: if clients can mark their own traffic high-priority, everything becomes high-priority and shedding degenerates back to first-come-first-served; priority is best assigned by the system from the request's role (health checks and paying-customer paths high, background jobs low), not taken on trust. And shedding is a load-management tool, not a substitute for capacity — if high-priority demand alone exceeds capacity, shedding keeps the system alive but you still need to scale. Within those bounds it is one of the cheapest reliability wins available: the same capacity, spent on the requests that matter.

<svg role="img" aria-label="Two shed paths: a cheap fast 503 rejection that frees the slot, versus an expensive rejection after doing the database work that consumed the slot anyway" viewBox="0 0 320 120">
  <text x="10" y="20" font-size="9" fill="var(--s1)">cheap shed (fast 503)</text>
  <rect x="30" y="28" width="30" height="16" fill="var(--s1)"/><text x="36" y="40" font-size="8" fill="var(--panel)">reject</text>
  <text x="66" y="40" font-size="8.5" fill="var(--muted)">→ slot freed for a high-priority request</text>
  <text x="10" y="76" font-size="9" fill="var(--s2)">expensive shed (reject after work)</text>
  <rect x="30" y="84" width="60" height="16" fill="var(--muted)"/><text x="36" y="96" font-size="8" fill="var(--panel)">DB query</text>
  <rect x="90" y="84" width="30" height="16" fill="var(--s2)"/><text x="96" y="96" font-size="8" fill="var(--panel)">reject</text>
  <text x="124" y="96" font-size="8.5" fill="var(--muted)">→ slot already spent — no capacity freed</text>
</svg>
^ Shedding only frees capacity if the rejection is cheap. A fast 503 before the expensive work releases the slot; rejecting after the database query has already run consumes the slot anyway, turning shedding into a slow failure with extra steps.

**Done means shedding serves the same total but strictly more high-priority requests, dropping only low — a deliberate reallocation of scarce capacity, effective only when the rejection is cheap and the priority is trustworthy.**

## Boss fight

During a traffic spike your service's latency climbs and both critical checkout requests and background recommendation-refresh requests start failing at similar rates. An engineer adds a global rate limiter that rejects any request over a fixed requests-per-second threshold, regardless of type. Latency stabilizes, but checkout success during spikes is still poor. Why did the blunt rate limiter not solve the real problem, and what would?

The blunt rate limiter caps total throughput, which stabilizes latency, but it is priority-blind: when it rejects requests over the threshold, it rejects checkouts and recommendation refreshes indiscriminately, so during a spike a large share of the rejected requests are still the critical ones — exactly the first-come-first-served problem, just enforced by a rate cap instead of a queue. It protected the server from overload but did nothing to protect the important requests within the admitted load. The fix is priority-aware load shedding: classify requests by role — checkout and other revenue or health-critical paths as high priority, recommendation refresh and other best-effort work as low — and when the system is over capacity, shed the low-priority traffic first with a cheap rejection, reserving throughput for the high-priority requests. The recommendation refreshes get fast 503s and back off; the checkouts get served. You can keep the global limiter as a backstop to bound total load, but the admission decision under that limit has to be made by priority, not by arrival or a flat rate, or the requests you most need to serve keep losing their slots to work you could afford to drop.

## External resources

Google's *Site Reliability Engineering*, the "Handling Overload" chapter — the canonical treatment of load shedding and graceful degradation, including criticality-based admission (serving high-criticality requests first) and why a cheap rejection is essential to actually shed load.

The Envoy and Istio documentation on load shedding, priority-based admission, and circuit breaking — production implementations of exactly this pattern at the proxy layer, showing how requests are classified and low-priority traffic is shed under pressure while critical paths are preserved.
