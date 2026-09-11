---
id: ship-inter-03
title: Rate-limit with a token bucket — and cap it, or a burst floods after idle
topic: ship-and-operate
level: intermediate
status: ready
time: 8-10h
summary: A token bucket bounds request rate: capacity is the burst size, the refill rate is the sustained throughput, and each request spends a token or is denied — a correct limiter with capacity 3 lets 8 of 11 requests through and never allows more than 3 at any one instant. The whole guarantee rests on one clamp: after refilling, cap the bucket at capacity. Drop it and tokens pile up without bound through an idle gap, so a bucket sitting quiet for ten seconds holds far more than capacity and the next burst of five sails straight through — the buggy limiter allows 10 and lets a burst of 5 past a capacity-3 limit. It looks correct under steady load and fails exactly when a burst follows a lull, the one traffic shape that overloads a service.
eli5: A bucket fills with drips and each request scoops one cup; no cup, no entry. The bucket has a rim so it can only hold so much — that rim is what stops a flood. If you forget the rim, then while nobody is drawing water the bucket keeps filling past the top, and when a crowd finally arrives they all get a cup at once. The rim is the entire point of the bucket.
---

## Why this module

Every service that talks to a rate-limited dependency, or protects itself from overload, needs to bound how fast requests flow — "100 per second", "10 per user per minute". The token bucket is the primitive that does it, and it is worth building from scratch because its correctness hinges on a single line that is trivially easy to omit, and omitting it produces a limiter that passes every casual test and then fails in production under the exact traffic it exists to stop. This module builds the bucket, plants that omission, and measures the flood it causes.

The mechanism is small. A bucket holds up to `capacity` tokens and gains `refill_per_sec` tokens per second of elapsed time; each arriving request spends one token if one is there, otherwise it is denied. Capacity is the burst allowance — the most requests that can pass back-to-back — and the refill rate is the sustained throughput once the burst is spent. The one subtlety is what happens to refilled tokens when no requests come: they must be clamped at capacity, because a bucket is a bucket, with a rim. Forget the clamp and idle time accumulates tokens without limit, so after a quiet stretch the bucket holds far more than capacity and the next burst passes unthrottled — the limiter's guarantee silently void. That clamp is the module's planted bug, and it is invisible under steady load because steady load never lets the bucket overfill.

You need no prior module, only the idea of requests arriving over time. Everything runs offline against a traffic fixture — a burst, an idle gap, a bigger burst — stdlib Python 3, `$0.00`. Time is the request timestamps, not a wall clock, so the run is deterministic. The instinct to unlearn is that a rate limiter that works under load is correct. A limiter can pass every steady-load test and still have no rim, and the burst-after-idle is the traffic that finds out.

Here is the correct limiter policing the stream:

```
# modules/ship-and-operate/code/ship-inter-03/ — COMPLETE, run from that directory
$ python3 ratelimit.py --run

RUN — correct limiter (capacity=3, refill=1/s)
------------------------------------------------------------------
  t=0    allow
  t=0    allow
  t=0    allow
  t=0    DENY
  t=10   allow
  t=10   allow
  t=10   allow
  t=10   DENY
  t=10   DENY
  t=11   allow
  t=12   allow
```

run: 2026-08-26 · deterministic; arrival times are a fixture · 11 requests · `python3 ratelimit.py --run`

<svg viewBox="0 0 700 140" role="img" aria-label="A timeline of eleven request decisions. At t=0, four requests: three green allow, one red deny. A gap. At t=10, five requests: three green allow, two red deny. Then single allows at t=11 and t=12.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">decisions over time — each burst capped at capacity=3</text>
    <line x1="40" y1="70" x2="660" y2="70" stroke="var(--grid)"></line>
    <g fill="var(--s1)"><circle cx="70" cy="70" r="7"></circle><circle cx="88" cy="70" r="7"></circle><circle cx="106" cy="70" r="7"></circle></g>
    <circle cx="124" cy="70" r="7" fill="var(--s2)"></circle>
    <text x="97" y="96" text-anchor="middle" fill="var(--muted)" font-size="8">t=0: allow 3, deny 1</text>
    <text x="300" y="74" fill="var(--muted)" font-size="8">— idle 10s —</text>
    <g fill="var(--s1)"><circle cx="430" cy="70" r="7"></circle><circle cx="448" cy="70" r="7"></circle><circle cx="466" cy="70" r="7"></circle></g>
    <g fill="var(--s2)"><circle cx="484" cy="70" r="7"></circle><circle cx="502" cy="70" r="7"></circle></g>
    <text x="466" y="96" text-anchor="middle" fill="var(--muted)" font-size="8">t=10: allow 3, deny 2</text>
    <circle cx="580" cy="70" r="7" fill="var(--s1)"></circle><circle cx="610" cy="70" r="7" fill="var(--s1)"></circle>
    <text x="595" y="96" text-anchor="middle" fill="var(--muted)" font-size="8">t=11,12: allow</text>
    <rect x="40" y="112" width="10" height="10" fill="var(--s1)"></rect><text x="54" y="121" fill="var(--muted)" font-size="8">allow</text>
    <rect x="110" y="112" width="10" height="10" fill="var(--s2)"></rect><text x="124" y="121" fill="var(--muted)" font-size="8">deny</text>
  </g>
</svg>
^ Both bursts are clipped to three allows; the idle refill lets the second burst pass three again, and the trailing singles at t=11 and t=12 ride the steady refill. Every instant is held at or below capacity.

Two bursts of many simultaneous requests, and each is capped at three — capacity — with the rest denied, even though ten seconds of idle sat between them. That capping after idle is the whole property, and this module is the one line that provides it.

## Concepts

Named here so you can find them again; each is built below.

- **Token bucket** — a bucket of up to `capacity` tokens; a request spends one or is denied.
- **Capacity** — the maximum burst: how many requests can pass back-to-back.
- **Refill rate** — tokens added per second; the sustained throughput once the burst is spent.
- **The clamp** — cap the bucket at capacity after refilling; the rim that bounds a burst.
- **Idle accumulation** — the bug where, without the clamp, tokens pile up during quiet periods.
- **Instant burst** — requests allowed at a single timestamp; must never exceed capacity.

## Worked example

Source: the token-bucket algorithm behind essentially every production rate limiter (API gateways, Stripe, cloud load balancers, the `nginx` limit modules), reduced to its arithmetic; the arrival times here stand in for a real request stream so the allow/deny decisions and the post-idle burst are exact and checkable.

Script and fixture: `modules/ship-and-operate/code/ship-inter-03/` — `ratelimit.py`, and `traffic.json`, capacity 3, refill 1/second, eleven arrival times shaped as burst–idle–burst. Every command runs from there.

### The bucket, and the one clamp

The whole limiter is a dozen lines. Refill for the elapsed time, clamp, then spend or deny.

```
# ratelimit.py:39-57 — COMPLETE (the token bucket; cap_bucket=False is the bug)
def run_limiter(capacity, refill, requests, cap_bucket=True):
    """Token bucket. cap_bucket=False is the BUG: refilled tokens are never clamped."""
    tokens = float(capacity)  # start full
    last = requests[0] if requests else 0
    decisions = []
    for t in requests:
        tokens += (t - last) * refill  # refill for elapsed time
        if cap_bucket:
            tokens = min(tokens, capacity)  # THE CLAMP: never hold more than capacity
        last = t
        if tokens >= 1.0:
            tokens -= 1.0
            decisions.append((t, True))
        else:
            decisions.append((t, False))
    return decisions
```

Everything except one line is uncontroversial: start full, add `(t - last) * refill` tokens per request, spend one if available. The load-bearing line is `tokens = min(tokens, capacity)`. It is the rim. With it, the bucket can never hold more than three tokens no matter how long it sits idle, so a burst can never exceed capacity. Without it — `cap_bucket=False` — the refill keeps adding through the idle gap and the bucket overflows unbounded.

### Tracing the idle gap

Follow the tokens through the fixture under each version. Both start with three tokens and handle the first burst identically: at t=0 the bucket has 3, allows three requests, denies the fourth. The divergence is the idle gap from t=0 to t=10.

<svg viewBox="0 0 700 200" role="img" aria-label="Token count over time under two limiters. Both start at 3 and drop to 0 during the first burst at t=0. During the idle gap to t=10 the correct limiter's tokens refill and flatten at the capacity ceiling of 3, while the buggy limiter's tokens climb past 3 up to 10, uncapped. At t=10 the correct bucket has 3 and allows 3; the buggy bucket has 10 and allows all 5 requests.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">tokens in the bucket through the idle gap (capacity=3)</text>
    <line x1="60" y1="160" x2="650" y2="160" stroke="var(--grid)"></line>
    <line x1="60" y1="30" x2="60" y2="160" stroke="var(--grid)"></line>
    <line x1="60" y1="118" x2="650" y2="118" stroke="var(--acc)" stroke-dasharray="4 3"></line>
    <text x="500" y="114" fill="var(--acc-ink)" font-size="8">capacity ceiling = 3</text>
    <polyline points="90,118 90,160 300,118 320,118" fill="none" stroke="var(--s1)" stroke-width="2.2"></polyline>
    <text x="330" y="120" fill="var(--s1)" font-size="8">correct: refills, flattens at 3</text>
    <polyline points="90,118 90,160 300,20 320,20" fill="none" stroke="var(--s2)" stroke-width="2.2" stroke-dasharray="5 3"></polyline>
    <text x="330" y="26" fill="var(--s2)" font-size="8">buggy: climbs uncapped to 10</text>
    <g fill="var(--muted)" text-anchor="middle"><text x="90" y="176">t=0 burst</text><text x="310" y="176">t=10 burst</text></g>
    <g fill="var(--muted)" text-anchor="end"><text x="54" y="160">0</text><text x="54" y="118">3</text><text x="54" y="24">10</text></g>
  </g>
</svg>
^ Through the idle gap the correct bucket refills and then flattens against the capacity ceiling; the buggy bucket keeps climbing to ten tokens. When the second burst hits at t=10, the correct bucket has three tokens and the buggy one has ten — and that difference is the flood.

### The flood: burst after idle

The total allowed is a simple tally over the decisions:

```
# ratelimit.py:60-61 — COMPLETE (how many requests got through)
def allowed_count(decisions):
    return sum(1 for _, a in decisions if a)
```

But the total is not the number that catches this bug — a limiter can allow a sensible total while still letting a single burst through too large. What matters is how many were allowed at once, the most requests sharing one timestamp. Measure the largest burst each limiter lets through at a single instant.

```
# ratelimit.py:64-68 — COMPLETE (most requests allowed at one timestamp)
def max_instant_burst(decisions):
    """Most requests ALLOWED sharing a single timestamp -- the true burst let through."""
    per_time = {}
    for t, a in decisions:
        if a:
            per_time[t] = per_time.get(t, 0) + 1
    return max(per_time.values()) if per_time else 0
```

Run both limiters over the same stream:

```
# $ python3 ratelimit.py --burst
#   correct (capped) limiter: allowed=8  max instant burst=3
#   buggy (uncapped) limiter: allowed=10  max instant burst=5
```

run: 2026-08-26 · deterministic · `python3 ratelimit.py --burst`

<svg viewBox="0 0 700 150" role="img" aria-label="Two horizontal bars of the maximum instant burst let through, against a dashed capacity line at 3. Correct limiter: bar at 3, exactly on the line. Buggy limiter: bar at 5, overshooting the line by two.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="18" fill="var(--muted)">largest burst let through at one instant (capacity=3)</text>
    <line x1="360" y1="28" x2="360" y2="130" stroke="var(--acc)" stroke-dasharray="4 3"></line>
    <text x="360" y="144" text-anchor="middle" fill="var(--acc-ink)" font-size="8">capacity 3</text>
    <text x="20" y="52" fill="var(--ink)">correct</text><rect x="160" y="40" width="200" height="18" fill="var(--s1)"></rect><text x="368" y="54" fill="var(--s1)" font-size="9">3 (on the limit)</text>
    <text x="20" y="92" fill="var(--ink)">buggy</text><rect x="160" y="80" width="334" height="18" fill="var(--s2)"></rect><text x="502" y="94" fill="var(--s2)" font-size="9">5 (flood)</text>
  </g>
</svg>
^ The correct limiter's burst lands exactly on the capacity line; the buggy one overshoots to five. Two extra simultaneous requests reaching a service it was told to shield — delivered right after the quietest stretch.

The correct limiter caps the t=10 burst at three, the capacity — exactly its job. The buggy limiter, holding ten saved-up tokens, allows all five requests at t=10, a burst of five past a capacity-three limit, and lets ten of eleven requests through overall. A downstream service protected by the buggy limiter would see, after ten quiet seconds, a sudden spike of five simultaneous requests it was promised would be at most three. The bug does not leak a little; it voids the guarantee precisely when the traffic is burstiest.

**A token bucket's rate guarantee is the clamp that caps it at capacity: without that one line, idle time accumulates tokens without bound and a burst after a lull floods straight through — the limiter looks correct under steady load and fails on the exact traffic shape it exists to stop.**

### The self-test

The `--check` mode asserts both the property and the bug: the correct limiter never allows more than capacity at an instant, and the buggy one does.

```
# $ python3 ratelimit.py --check
#   correct: no instant burst exceeds capacity = True (3 <= 3)
#   buggy: an instant burst exceeds capacity = True (5 > 3)
#   correct limiter denies the over-limit requests = True (3 denied)
#   buggy limiter allows more than the correct one = True (10 > 8)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 ratelimit.py --check`

The two decisive assertions put the capped and uncapped limiters head to head on the same stream:

```
# ratelimit.py:108-114 — COMPLETE (the property, and the bug, as assertions)
    burst_bounded = max_instant_burst(good) <= cap
    print("  correct: no instant burst exceeds capacity = %s (%d <= %d)"
          % (burst_bounded, max_instant_burst(good), cap))

    bug_floods = max_instant_burst(bug) > cap
    print("  buggy: an instant burst exceeds capacity = %s (%d > %d)"
          % (bug_floods, max_instant_burst(bug), cap))
```

The `burst_bounded` line is the correctness anchor: no timestamp may allow more than capacity requests, and if a refactor dropped the clamp that assertion would fail first. The `bug_floods` line encodes the failure as a guardrail — it requires that the uncapped version actually exceeds capacity on this stream, so the test proves the clamp is what matters rather than merely asserting the happy path. A limiter tested only under steady load would show neither.

### The running tally

| limiter | requests allowed | max instant burst | guarantee held |
|---|---|---|---|
| correct (capped) | 8 of 11 | 3 | yes — burst ≤ capacity |
| buggy (uncapped) | 10 of 11 | 5 | no — flooded after idle |

The buggy limiter looks more permissive — ten allowed versus eight — and a naive reading might even call that better throughput. It is not; it is the guarantee breaking. The two extra requests it allowed are exactly the over-capacity burst the limiter was supposed to reject, delivered to a service at the worst possible moment. Allowing more is the symptom, not a feature; the number that matters is the instant burst, and only the capped limiter holds it at capacity.

### What we did not settle

The token bucket is one of several limiter shapes. A leaky bucket smooths output to a constant rate rather than allowing bursts up to capacity; fixed and sliding window counters are simpler but have their own edge — the fixed window allows a double burst across a boundary. Distributed rate limiting is harder: the bucket state must be shared and updated atomically across servers, or each replica enforces its own limit and the aggregate is N times too loose — the same consistency problem idempotency faced. And a real limiter reads a monotonic clock, not request timestamps, so clock skew and pauses matter. The arithmetic here — refill, clamp, spend — is the core every one of those refines.

## Build

The practice in one paragraph: bound request rate with a token bucket sized by capacity (the burst you tolerate) and refill rate (the sustained throughput you allow); on each request, add tokens for the elapsed time, clamp the total at capacity, then spend one or deny; and test the clamp with a burst-after-idle stream, asserting that no instant exceeds capacity, because steady-load tests never exercise the overflow. Use a monotonic clock in production and share state atomically if the limit spans servers.

We opened on the correct run. The number that proves the limiter holds is the instant burst:

```
# modules/ship-and-operate/code/ship-inter-03/ — COMPLETE, run from that directory
$ python3 ratelimit.py --burst
  correct (capped) limiter: allowed=8  max instant burst=3
  buggy (uncapped) limiter: allowed=10  max instant burst=5
```

Now build it yourself. Implement a token bucket, then feed it a burst, a long idle gap, and a bigger burst. Your number to beat is not the count allowed; it is **the maximum instant burst, which must never exceed capacity** — then remove the clamp and watch the post-idle burst blow past it, so you have seen the failure. Bring back both max-instant-burst numbers, capped and uncapped. Good luck.

## Definition of done

- [ ] A token bucket with capacity and refill rate, spending one token per request
- [ ] Refilled tokens clamped at capacity after each refill
- [ ] A burst–idle–burst request stream that exercises the overflow
- [ ] Allow/deny decisions and the max instant burst measured under the correct limiter
- [ ] The uncapped version run on the same stream, flooding after the idle gap
- [ ] Confirmation the correct limiter never allows more than capacity at one instant
- [ ] `python3 ratelimit.py --check` printing SELF-TEST PASS: burst-bounded, bug-floods, correct-denies, buggy-allows-more
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. What do capacity and refill rate each control in a token bucket, and how do they map to "burst" and "sustained rate"?
2. The whole guarantee rests on one line. Which one, and what exactly goes wrong without it?
3. Why does the bug stay invisible under steady load and appear only after an idle gap?
4. The buggy limiter allowed more requests than the correct one. Why is "allowed more" the symptom of a failure, not a feature?
5. Your own bucket was fed a burst–idle–burst stream. What was the max instant burst with the clamp and without it, and how did each compare to capacity?

## External resources

- Wikipedia / standard references, *Token bucket* algorithm — my summary: the canonical description of capacity, refill, and the burst-versus-rate distinction this module implements; read it for the leaky-bucket contrast and where each shape fits.
- Stripe engineering, *Scaling your API with rate limiters* — my summary: a production account of token-bucket limiters, per-key buckets, and why bursts are allowed up to a cap; read it for how the primitive here is deployed at scale and the operational knobs around it.
- This hub, *ship-inter-02* — modules/ship-and-operate/ship-inter-02.md — my summary: the other ship-and-operate module where a correct-looking mechanism fails under a specific condition (a retry without a stable idempotency key); read it for the shared lesson — test the failure condition, not the happy path, and for the distributed-state consistency problem both share.
