---
id: retrybudget-inter-01
title: Cap retries with a budget, not one per failure — a widespread outage turns per-failure retries into a self-inflicted storm
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: Retrying a failed request is usually right — most failures are transient blips, and a single retry recovers them for almost nothing — but a retry is extra load, and the assumption that failures are rare (which makes retrying cheap) is exactly the assumption that breaks during an incident. When a dependency degrades and most requests start failing, retrying every failure roughly doubles the load on the struggling dependency at the worst possible moment, driving it further down and keeping it there: a retry storm, one of the classic ways a recoverable blip becomes a sustained, self-inflicted outage. Jitter helps by spreading retries out in time, and retrying at only one layer stops them multiplying across layers, but neither bounds the total volume — with per-failure retries, jittered and single-layer, an outage where 80% of requests fail still offers nearly 1.8× the load, because every failure still gets its retry. A retry budget bounds the volume directly: treat retries as a scarce resource, allow them only up to a small fraction of the request rate (a token bucket refilled at, say, 10% of requests), and once the budget is spent, fail fast instead of retrying. The elegance is that the budget is invisible in normal operation — transient failures are far under it, so every one still gets retried and recovery is unaffected — and only engages during a broad outage, capping the amplification. On a fixture with a 10%-of-requests retry budget, a healthy period (5 of 100 failing) retries all 5 under both policies (the budget is transparent), while an outage (80 failing) pushes per-failure retries to 1.8× load and the budget caps it at 1.1×.
eli5: If you knock on a door and no one answers, knocking once more is sensible — usually they were just busy for a second. But imagine the person inside is overwhelmed and can't get to any door, and a hundred people are all knocking twice as hard because no one answered the first time. Now the poor person is buried under twice as much knocking exactly when they can least handle it, and they'll never recover. A retry budget is a rule: as a group, we're only allowed a small number of second-knocks per minute. When almost everyone gets an answer, that limit never matters — the few who need to knock again still can. But when the whole house is overwhelmed, the limit stops the pile-on so the person inside gets a chance to catch up.
---

## Why this module

Retries are the most natural resilience mechanism there is, and the most dangerous when they are unbounded. The logic that justifies a retry — "failures are rare, so a retry is cheap insurance" — is a statement about the healthy state, and it silently inverts during an incident. The moment failures stop being rare, every retry is no longer cheap insurance but added load on a system that is failing precisely because it is overloaded or degraded. The mechanism meant to improve reliability becomes the thing preventing recovery.

This is a retry storm, and it is a specific, well-documented failure mode: a dependency has a transient degradation, its clients all retry, the extra load pushes it further past its capacity, more requests fail, they retry too, and the system settles into a stable-but-broken state that persists long after the original trigger is gone (a metastable failure). The insidious part is that each individual client is behaving reasonably — one retry per failure, maybe even with backoff and jitter — yet the aggregate is a self-sustaining overload.

Jitter and single-layer retries address the shape and multiplication of retries but not their sheer volume. This module isolates the volume problem and the fix that bounds it: a retry budget, shown across a healthy period and an outage.

**Per-failure retries are cheap insurance only while failures are rare; when a widespread outage makes most requests fail, retrying every one amplifies the load on the failing dependency — a retry budget bounds the total retry volume so the amplification is capped.**

## Concepts

The fixture is a request count, a budget expressed as a fraction of requests, and two scenarios: a healthy period with few failures and an outage with many.

```json filename=modules/ship-and-operate/code/retrybudget-inter-01/retrybudget.json:3-8 COMPLETE
  "requests": 100,
  "budget_fraction": 0.1,
  "scenarios": [
    {"name": "healthy", "failures": 5},
    {"name": "outage", "failures": 80}
  ]
```

The budget is a fraction of the request rate. The no-budget policy retries every failure; the budgeted policy retries up to the budget, then fails fast. Amplification is the total offered load — original requests plus retries — divided by the requests.

```python filename=modules/ship-and-operate/code/retrybudget-inter-01/retrybudget.py:33-48 COMPLETE
def budget(requests, fraction):
    return math.ceil(fraction * requests)


def retries_no_budget(failures):
    """Retry every failure."""
    return failures


def retries_with_budget(failures, requests, fraction):
    """Retry up to the budget, then fail fast."""
    return min(failures, budget(requests, fraction))


def amplification(requests, retries):
    return (requests + retries) / requests
```

The whole difference is the `min` with the budget: when failures are below the budget it is a no-op, and when they exceed it, it clamps the retries — so the policy changes behavior only when it needs to.

<svg role="img" aria-label="Retries versus failure rate: the no-budget line rises with every failure, the budgeted line rises with it until it hits the budget cap and then stays flat" viewBox="0 0 320 130">
  <line x1="35" y1="20" x2="35" y2="100" stroke="var(--line)" stroke-width="1"/>
  <line x1="35" y1="100" x2="300" y2="100" stroke="var(--line)" stroke-width="1"/>
  <text x="0" y="26" font-size="7.5" fill="var(--muted)">retries</text>
  <text x="230" y="116" font-size="7.5" fill="var(--muted)">failures →</text>
  <line x1="35" y1="100" x2="285" y2="24" stroke="var(--s2)" stroke-width="2"/>
  <text x="238" y="34" font-size="7" fill="var(--s2)">no budget</text>
  <line x1="35" y1="100" x2="95" y2="82" stroke="var(--s1)" stroke-width="2"/>
  <line x1="95" y1="82" x2="285" y2="82" stroke="var(--s1)" stroke-width="2"/>
  <line x1="95" y1="78" x2="95" y2="100" stroke="var(--ink)" stroke-dasharray="2 2"/>
  <text x="70" y="112" font-size="7" fill="var(--ink)">budget</text>
  <text x="210" y="78" font-size="7" fill="var(--s1)">budgeted (capped)</text>
  <text x="35" y="14" font-size="7.5" fill="var(--muted)">below the budget the two agree; above it the budget flattens</text>
</svg>
^ Below the budget the two policies issue identical retries — the budget is transparent. Once failures exceed the budget, the no-budget line keeps climbing with the failure rate while the budgeted line flattens at the cap. The budget engages exactly and only when retries would otherwise run away.

**Retries equal failures until they hit the budget, then the budget clamps them — so the cap is a no-op in normal operation and only bites when the failure rate would produce a storm.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the retry policy of a client calling a dependency, reduced to a 100-request window so every count is checkable by hand.

Run `--scenarios` to see retries and total load in each period.

```text filename=retrybudget.py --scenarios
  period    failures   no-budget retries/load   budget retries/load
  healthy   5          5   / 105                5   / 105
  outage    80         80  / 180                10  / 110
```

In the healthy period, 5 of 100 requests fail. Both policies retry all 5 — the budget is 10, and 5 is under it — so both offer 105 total requests. The budget did nothing, which is the point: it does not interfere with recovering ordinary transient failures. In the outage, 80 of 100 fail. The no-budget policy retries all 80, offering 180 total — 1.8× the load on a dependency that is already failing 80% of what it receives. The budgeted policy retries only 10 (the budget) and fails the other 70 fast, offering 110 total. Same outage, and one policy nearly doubles the load while the other adds a tenth.

Now `--amplify` states it as a multiplier — the offered load over the request count, each policy.

```python filename=modules/ship-and-operate/code/retrybudget-inter-01/retrybudget.py:74-75 COMPLETE
        nb = amplification(requests, retries_no_budget(f))
        bg = amplification(requests, retries_with_budget(f, requests, frac))
```

The two multipliers diverge only under load.

```text filename=retrybudget.py --amplify
  healthy   no-budget 1.05x   budget 1.05x
  outage    no-budget 1.80x   budget 1.10x
```

In the healthy period both policies sit at 1.05× — identical, negligible. In the outage they split: no-budget 1.80×, budget 1.10×. The budgeted amplification is bounded at 1 + the budget fraction (1.10×) no matter how bad the failure rate gets, because retries can never exceed the budget; the no-budget amplification rises without limit toward 2× as the failure rate approaches 100%. The retry storm is precisely the difference between those two curves, and it appears only under the load conditions where amplifying is most harmful.

<svg role="img" aria-label="Load amplification bars: healthy period both policies at 1.05x, outage no-budget at 1.80x versus budget at 1.10x" viewBox="0 0 320 120">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">offered-load multiplier (1.0x = no added load)</text>
  <text x="10" y="36" font-size="8" fill="var(--muted)">healthy</text>
  <rect x="70" y="28" width="12" height="12" fill="var(--s1)"/><text x="86" y="38" font-size="7.5" fill="var(--ink)">both 1.05x</text>
  <text x="10" y="66" font-size="8" fill="var(--muted)">outage</text>
  <rect x="70" y="58" width="14" height="12" fill="var(--s1)"/><text x="88" y="68" font-size="7.5" fill="var(--s1)">budget 1.10x</text>
  <rect x="70" y="76" width="112" height="12" fill="var(--s2)"/><text x="186" y="86" font-size="7.5" fill="var(--s2)">no-budget 1.80x</text>
  <text x="10" y="110" font-size="7.5" fill="var(--muted)">the budget bounds the outage multiplier at 1 + fraction; no-budget climbs toward 2x</text>
</svg>
^ Healthy, both policies add a negligible 5%. In the outage, the no-budget policy offers 1.80× load — the retry storm — while the budgeted policy stays at 1.10×. The budget's ceiling is 1 + the budget fraction regardless of how high the failure rate climbs.

**Both policies add a negligible 1.05× when failures are rare; in the outage per-failure retries reach 1.80× while the budget holds at 1.10× — the storm is exactly the gap, and only the budget bounds it.**

## Build

The self-test asserts transparency and the cap: when failures are rare the budget retries every one, per-failure retries amplify the outage, and the budget caps the outage retries.

```python filename=modules/ship-and-operate/code/retrybudget-inter-01/retrybudget.py:91-97 COMPLETE
    budget_transparent_when_healthy = retries_with_budget(hf, requests, frac) == retries_no_budget(hf)
    print("  when failures are rare the budget retries every one (transparent) = %s (%d == %d)"
          % (budget_transparent_when_healthy, retries_with_budget(hf, requests, frac), retries_no_budget(hf)))

    no_budget_amplifies_outage = amplification(requests, retries_no_budget(of)) >= 1.5
    print("  per-failure retries amplify load in the outage = %s (%.2fx)"
          % (no_budget_amplifies_outage, amplification(requests, retries_no_budget(of))))
```

Then the bound: the budgeted outage load is capped at 1 + the fraction, and the outage's failures do exceed the budget so the cap actually engages.

```python filename=modules/ship-and-operate/code/retrybudget-inter-01/retrybudget.py:99-105 COMPLETE
    budget_caps_outage_retries = retries_with_budget(of, requests, frac) < retries_no_budget(of)
    print("  the budget caps retries in the outage = %s (%d < %d)"
          % (budget_caps_outage_retries, retries_with_budget(of, requests, frac), retries_no_budget(of)))

    budget_bounds_amplification = amplification(requests, retries_with_budget(of, requests, frac)) <= 1 + frac + 1e-9
    print("  the budget bounds outage amplification at 1+fraction = %s (%.2fx <= %.2fx)"
          % (budget_bounds_amplification, amplification(requests, retries_with_budget(of, requests, frac)), 1 + frac))
```

Running the check confirms every clause.

```text filename=retrybudget.py --check
  when failures are rare the budget retries every one (transparent) = True (5 == 5)
  per-failure retries amplify load in the outage = True (1.80x)
  the budget caps retries in the outage = True (10 < 80)
  the budget bounds outage amplification at 1+fraction = True (1.10x <= 1.10x)
  the outage's failures exceed the budget (so the cap engages) = True (80 > 10)
```

**The check shows the budget doing nothing when failures are rare and clamping the amplification to 1 + the fraction when they spike — the fix engages only in the outage, exactly where per-failure retries turn into a storm.**

## Definition of done

Done means the budget is transparent in the healthy period and caps the outage amplification at 1 + the budget fraction, with the outage's failure count proven to exceed the budget so the cap genuinely engages. That transparency clause is what makes a retry budget safe to deploy: it never sacrifices the recovery of ordinary transient failures, so there is no tradeoff to tune away — it is pure downside protection that activates only under storm conditions.

Two clarifications make it real. First, the budget is normally implemented as a token bucket, not a per-window counter: each request adds a fraction of a token, each retry costs a token, and retries are allowed only while tokens remain, which gives a smooth rolling cap (like 10% of recent requests) rather than a hard per-window reset. This is exactly how client libraries such as gRPC and the AWS SDKs implement retry throttling, and it composes with — does not replace — backoff and jitter (which space retries in time) and circuit breakers (which stop calling a dependency that is failing outright). A robust client uses all three: jittered backoff for timing, a retry budget for volume, and a breaker for a dead dependency. Second, the budget must live client-side and be measured against that client's own traffic, because the whole point is to bound the load one client (or fleet) adds; a server-side limit is a different tool (load shedding). And the fraction is a real knob — too low and you fail to retry recoverable blips under moderate failure rates, too high and the storm protection weakens — with single-digit-percent budgets being typical, on the logic that if more than a few percent of requests are failing, retrying harder is not the answer.

<svg role="img" aria-label="Three complementary retry controls: jittered backoff for timing, retry budget for volume, circuit breaker for a dead dependency, each addressing a different axis" viewBox="0 0 320 118">
  <rect x="12" y="24" width="96" height="40" fill="none" stroke="var(--s1)"/>
  <text x="20" y="40" font-size="7.5" fill="var(--s1)">backoff + jitter</text>
  <text x="20" y="52" font-size="7" fill="var(--ink)">timing (when)</text>
  <rect x="112" y="24" width="96" height="40" fill="none" stroke="var(--s2)"/>
  <text x="120" y="40" font-size="7.5" fill="var(--s2)">retry budget</text>
  <text x="120" y="52" font-size="7" fill="var(--ink)">volume (how much)</text>
  <rect x="212" y="24" width="96" height="40" fill="none" stroke="var(--ink)"/>
  <text x="220" y="40" font-size="7.5" fill="var(--ink)">circuit breaker</text>
  <text x="220" y="52" font-size="7" fill="var(--ink)">whether (dead dep)</text>
  <text x="12" y="86" font-size="7.5" fill="var(--muted)">three axes of retry control — a robust client uses all three, not one</text>
  <text x="12" y="102" font-size="7.5" fill="var(--ink)">the budget is the volume axis: a client-side token bucket, single-digit-percent</text>
</svg>
^ Retry control has three independent axes: backoff and jitter fix the timing, a retry budget bounds the volume, and a circuit breaker decides whether to call at all. They compose — the budget is the volume axis this module isolates, typically a client-side token bucket sized at a few percent of requests.

**Done means the budget is transparent when failures are rare and caps outage amplification at 1 + the fraction — implemented as a client-side token bucket that composes with backoff/jitter and circuit breakers, sized at a few percent so it protects against storms without suppressing ordinary retries.**

## Boss fight

A service calls a downstream dependency with jittered exponential backoff, retrying up to three times on failure. During a brief downstream degradation, the dependency went from slow to completely down and stayed down for twenty minutes — far longer than its usual blips — and the on-call found the downstream pinned at several times its normal request rate the entire time, unable to recover even as organic traffic was steady. The retries all had proper backoff and jitter. What happened, and what control is missing?

The retries had correct timing but unbounded volume, so the degradation became a retry storm. Once the dependency started failing most requests, every failure triggered up to three retries; with, say, a 90% failure rate and three retries each, the offered load multiplied several-fold, which is exactly the "several times normal rate" the on-call saw. Backoff and jitter spaced those retries out and kept them from arriving in a synchronized spike, but they did nothing to cap the total number of retry attempts — so the dependency was held down by the retry load itself, a metastable failure that persisted long after the original trigger and could not recover while the extra load continued. The missing control is a retry budget: a client-side cap on retry volume as a fraction of the request rate, implemented as a token bucket (each request adds a fraction of a token, each retry spends one), so retries are allowed while failures are rare and throttled off once the failure rate blows past the budget. With a budget of a few percent, the healthy behavior is unchanged — transient blips still get their retries — but during the twenty-minute outage the client would have retried only a small fraction of failures and failed the rest fast, holding the offered load near 1× instead of several times normal and letting the dependency recover once its underlying problem cleared. Pair it with a circuit breaker so that when the dependency is detected as down, the client stops calling it altogether for a cool-off window rather than sending even the budgeted trickle. The rule the team learned the hard way: backoff controls when you retry, but you also need a budget to control how much, or a long outage will let bounded-per-request retries add up to an unbounded aggregate.

## External resources

The retry-throttling / retry-budget mechanisms in production client libraries (gRPC's retry throttling, the AWS SDKs' retry quota/token-bucket, and Google's SRE-book treatment of retry amplification) — the token-bucket implementation this module abstracts, and the guidance on sizing the budget and combining it with backoff and circuit breakers.

Writing on retry storms and metastable failures in distributed systems (the "metastable failures in distributed systems" paper and postmortems of retry-amplified outages) — why bounded-per-request retries sum to an unbounded aggregate during a broad outage, and how a volume cap breaks the self-sustaining overload.
