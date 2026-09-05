---
id: ship-inter-04
title: A circuit breaker trips on consecutive failures — reset on success, or it false-trips
topic: ship-and-operate
level: intermediate
status: ready
time: 8-10h
summary: A circuit breaker opens after enough failures to stop hammering a dying dependency, and the whole question is what "enough" means — a run of consecutive failures signals a real outage, and the correct breaker trips at the third consecutive fail while staying closed on a healthy service whose worst failure run is one. The bug is counting total failures and never resetting on success: on a genuine outage it behaves identically, but on a basically-healthy service with four scattered blips it creeps to the threshold and false-trips at step 7, taking down a working dependency because unrelated hiccups accumulated forever. The fix is one line — reset the failure count to zero on every success — and the tell that the bug is subtle is that both breakers agree on the real outage and differ only where it matters.
eli5: Imagine a fuse that cuts the power if something keeps going wrong. A good fuse trips when the failures come in a row — that means something is really broken. A bad fuse just keeps a running tally of every hiccup ever and eventually trips even though the appliance is fine, because it never forgives the old, unrelated glitches. The fix is to reset the count to zero every time things work.
---

## Why this module

When a downstream dependency starts failing, the worst thing a client can do is keep calling it: retries pile load onto a service that is already struggling, turning a partial failure into a full outage and often taking the caller down with it. The circuit breaker is the pattern that prevents this — after enough failures it opens, failing fast without attempting the call, so the dependency gets room to recover. This module builds the breaker and the one design decision that separates a breaker that protects you from one that manufactures outages: what counts as "enough failures".

The right definition is consecutive failures. A run of failures in a row is evidence the dependency is actually down, and that is when you want to stop calling it. A scattered failure here and there among successes is normal — networks blip, a request times out, a node restarts — and a healthy service should not be cut off because of them. The tempting bug is to count total failures and never reset the counter, which feels equivalent and is not. On a real outage the two behave identically, so testing on an outage never reveals the difference. On a healthy-but-flaky service, the total-failure counter creeps upward over minutes or hours and eventually crosses the threshold, tripping the breaker on a dependency that was fine — a self-inflicted outage caused by a few unrelated hiccups. The fix is a single line: reset the failure count to zero on every success, so only a genuine run trips the breaker.

You need no prior module, only the idea of a client calling a dependency that sometimes fails. Everything runs offline against a call fixture — two sequences of successes and failures, a real outage and a flaky-but-healthy service — stdlib Python 3, `$0.00`. The instinct to unlearn is that a failure counter should count failures. It should count consecutive failures, and the reset on success is what makes it a breaker rather than a slow-motion outage generator.

Here is the correct breaker on a real outage:

```
# modules/ship-and-operate/code/ship-inter-04/ — COMPLETE, run from that directory
$ python3 breaker.py --trace outage

TRACE — correct breaker on 'outage' (threshold=3 consecutive failures)
------------------------------------------------------------------
  step:     0  1  2  3  4  5  6  7  8  9
  outcome:  1  1  0  0  0  0  0  1  1  1
  state:   cl cl cl cl Op Op Op Op Op Op
```

run: 2026-08-26 · deterministic; call outcomes are a fixture · threshold 3 · `python3 breaker.py --trace outage`

Two good calls, then a run of failures, and at the third consecutive failure — step 4 — the breaker opens and stops attempting the call. That is exactly right. This module is what happens when that same logic meets a service that is not actually down.

## Concepts

Named here so you can find them again; each is built below.

- **Circuit breaker** — a guard that opens after enough failures, failing fast instead of calling a dying dependency.
- **Closed / open** — closed lets calls through; open fails them fast to relieve the dependency.
- **Consecutive failures** — failures in an unbroken run; the correct trip signal.
- **The reset** — clearing the failure count to zero on any success; what makes the count consecutive.
- **Total-failure counting** — the bug: summing all failures ever, never resetting.
- **False trip** — opening on a healthy service because scattered blips accumulated.

## Worked example

Source: the circuit-breaker pattern from resilience libraries (Hystrix, resilience4j, Polly) and Nygard's *Release It!*, reduced to its trip logic; the call sequences here stand in for a real dependency's outcomes so the trip decisions are exact and checkable.

Script and fixture: `modules/ship-and-operate/code/ship-inter-04/` — `breaker.py`, and `calls.json`, a threshold of 3 and two scenarios: `outage` (a run of failures) and `flaky` (scattered blips on a healthy service). Every command runs from there.

### The breaker, and the one reset

The breaker is a counter and a threshold. The whole correctness question is a single branch.

```
# breaker.py:39-62 — COMPLETE (trip on the counter; reset_on_success=False is the bug)
def run_breaker(outcomes, threshold, reset_on_success=True):
    """Trip when the failure counter reaches threshold. Returns (opened, trip_index, states)."""
    failures = 0
    opened = False
    trip_index = None
    states = []
    for i, ok in enumerate(outcomes):
        if opened:
            states.append("OPEN")  # fail fast: not even attempted
            continue
        if ok:
            if reset_on_success:
                failures = 0  # THE RESET: a success clears the consecutive count
        else:
            failures += 1
        if failures >= threshold:
            opened = True
            trip_index = i
        states.append("OPEN" if opened else "closed")
    return opened, trip_index, states
```

<svg viewBox="0 0 700 150" role="img" aria-label="A two-state machine. A closed state and an open state. An arrow from closed to open labelled 'failure count reaches threshold'. A self-loop on closed labelled 'success resets count to 0'. A self-loop on closed labelled 'failure: count += 1'. The open state has a note: fail fast, do not call.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the breaker's two states (recovery/half-open omitted)</text>
    <circle cx="170" cy="85" r="42" fill="var(--acc-soft)" stroke="var(--acc-line)"></circle><text x="170" y="88" text-anchor="middle" fill="var(--acc-ink)">closed</text><text x="170" y="102" text-anchor="middle" fill="var(--acc-ink)" font-size="7">calls pass</text>
    <circle cx="520" cy="85" r="42" fill="var(--panel)" stroke="var(--s2)"></circle><text x="520" y="88" text-anchor="middle" fill="var(--s2)">open</text><text x="520" y="102" text-anchor="middle" fill="var(--s2)" font-size="7">fail fast</text>
    <line x1="212" y1="85" x2="478" y2="85" stroke="var(--s2)" stroke-width="1.5"></line>
    <text x="345" y="78" text-anchor="middle" fill="var(--s2)" font-size="8">count reaches threshold</text>
    <path d="M 150 47 A 30 30 0 1 1 190 47" fill="none" stroke="var(--s1)"></path>
    <text x="170" y="30" text-anchor="middle" fill="var(--s1)" font-size="8">success -> count = 0</text>
    <text x="170" y="140" text-anchor="middle" fill="var(--muted)" font-size="8">failure -> count += 1 (stays closed until the run reaches the threshold)</text>
  </g>
</svg>
^ Closed lets calls through, counting failures; a success resets the count to zero; the count reaching the threshold flips it to open, where calls fail fast. The reset loop on the closed state is the whole difference between consecutive and total counting.

Everything is uncontroversial except the `if reset_on_success: failures = 0` line. With it, a success wipes the failure count, so `failures` is the length of the current unbroken run — it only reaches the threshold if that many failures happen in a row. Without it, `failures` is every failure that has ever occurred, and it only ever grows. On an outage — a run of failures with no successes between them — the two are identical, because there is no success to reset on. The difference lives entirely on services that do recover between failures.

### The healthy service the bug takes down

The flaky scenario is a healthy service: four failures scattered among successes, and crucially, never two failures in a row.

```
# breaker.py:65-70 — COMPLETE (longest run of failures in a sequence)
def max_consecutive_failures(outcomes):
    run = best = 0
    for ok in outcomes:
        run = 0 if ok else run + 1
        best = max(best, run)
    return best
```

Its longest failure run is 1, well under the threshold of 3, so a correct breaker should never open on it. Trace it and the correct breaker stays closed the whole way:

```
# $ python3 breaker.py --trace flaky
#   step:     0  1  2  3  4  5  6  7  8  9 10 11
#   outcome:  1  0  1  1  0  1  1  0  1  0  1  1
#   state:   cl cl cl cl cl cl cl cl cl cl cl cl
#   stayed CLOSED: longest failure run was 1 (< 3).
```

run: 2026-08-26 · deterministic · `python3 breaker.py --trace flaky`

Every failure is immediately followed by a success that resets the counter, so `failures` never climbs past 1. The breaker correctly reads this as a working service having normal hiccups, and leaves the circuit closed.

<svg viewBox="0 0 700 190" role="img" aria-label="The flaky sequence shown as a rising staircase for the buggy total-failure counter versus a flat-near-zero line for the correct consecutive counter. The buggy counter steps up at each of the four failures: 1, 2, 3, 4, crossing the threshold line at 3 on the fourth-scattered failure at step 7. The correct counter spikes to 1 at each failure and immediately drops back to 0.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">failure counter on the FLAKY (healthy) service — same blips, two counters</text>
    <line x1="50" y1="150" x2="650" y2="150" stroke="var(--grid)"></line>
    <line x1="50" y1="30" x2="50" y2="150" stroke="var(--grid)"></line>
    <line x1="50" y1="78" x2="650" y2="78" stroke="var(--acc)" stroke-dasharray="4 3"></line>
    <text x="540" y="74" fill="var(--acc-ink)" font-size="8">threshold 3 = trip</text>
    <polyline points="95,150 145,126 195,126 245,126 295,102 345,102 395,102 445,78 495,78 545,78 595,78 640,78" fill="none" stroke="var(--s2)" stroke-width="2"></polyline>
    <text x="455" y="70" fill="var(--s2)" font-size="8">buggy: total, never resets -> trips at step 7</text>
    <polyline points="95,150 145,126 195,150 245,150 295,126 345,150 395,150 445,126 495,150 545,126 595,150 640,150" fill="none" stroke="var(--s1)" stroke-width="1.6"></polyline>
    <text x="380" y="164" fill="var(--s1)" font-size="8">correct: consecutive, resets to 0 each success -> never trips</text>
    <g fill="var(--muted)" text-anchor="end"><text x="44" y="150">0</text><text x="44" y="78">3</text></g>
  </g>
</svg>
^ The correct counter spikes to 1 at each blip and falls back to 0 on the next success; the buggy counter only climbs, crossing the threshold at the fourth scattered failure. Same healthy service, and only the resetting counter reads it correctly.

### The false trip

Now run the buggy breaker — total failures, no reset — on that same healthy service.

```
# $ python3 breaker.py --compare
#   outcomes: [1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1]   (4 scattered failures, longest run 1)
#   correct (reset on success): opened=False
#   buggy (counts all failures): opened=True  at step 7
```

run: 2026-08-26 · deterministic · `python3 breaker.py --compare`

The buggy breaker opens at step 7, on the third scattered failure, and from then on fails every call to a dependency that is working fine. Four unrelated blips over a dozen calls — the kind every healthy service produces — accumulated into a trip, because the counter never forgave the earlier ones. This is a self-inflicted outage: the breaker, meant to protect against a failing dependency, has taken down a healthy one. And it would pass any test written against an outage scenario, because on a real outage it opens correctly.

**A circuit breaker must trip on consecutive failures, not total ones, so a success has to reset the count to zero — without that reset a healthy service's scattered blips accumulate forever and the breaker false-trips, manufacturing the outage it exists to prevent.**

### The self-test

The `--check` mode asserts the full picture: the correct breaker opens on the outage and holds on the flaky service, the buggy one false-trips on the flaky service, and both agree on the outage so the bug is specific to scattered failures.

```
# $ python3 breaker.py --check
#   correct breaker OPENS on the real outage = True
#   correct breaker STAYS CLOSED on the flaky service = True (longest run 1 < 3)
#   buggy breaker FALSE-TRIPS on the flaky service = True (opened at step 7)
#   both breakers open on the outage (bug is flaky-only) = True
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 breaker.py --check`

The two decisive assertions run the same flaky sequence through both breakers:

```
# breaker.py:117-125 — COMPLETE (correct holds; buggy false-trips, on the same sequence)
    correct_flaky, _, _ = run_breaker(flaky, thr, reset_on_success=True)
    holds_on_flaky = not correct_flaky

    buggy_flaky, bug_i, _ = run_breaker(flaky, thr, reset_on_success=False)
    buggy_false_trips = buggy_flaky
```

The `holds_on_flaky` line is the correctness anchor: a breaker whose threshold is 3 must stay closed when the longest failure run is 1, and if a refactor broke the reset that assertion would fail first. The `agree_on_outage` line is what makes the module honest about why the bug is dangerous — it requires both breakers to open on the real outage, proving the bug is invisible to outage tests and shows only on the healthy-service case that a naive test suite omits.

### The running tally

| scenario | longest failure run | correct breaker | buggy breaker |
|---|---|---|---|
| outage (a real run of failures) | 5 | opens at step 4 | opens (same) |
| flaky (healthy, scattered blips) | 1 | stays closed | false-trips at step 7 |

<svg viewBox="0 0 700 150" role="img" aria-label="A two-by-two grid. Rows: outage, flaky. Columns: correct breaker, buggy breaker. Outage/correct: opens. Outage/buggy: opens. Flaky/correct: closed (good). Flaky/buggy: false-trips (bad, highlighted).">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">where the two breakers agree, and where they don't</text>
    <text x="200" y="42" text-anchor="middle" fill="var(--ink)">correct</text><text x="360" y="42" text-anchor="middle" fill="var(--ink)">buggy</text>
    <text x="90" y="72" fill="var(--ink)">outage</text>
    <rect x="150" y="56" width="100" height="24" fill="var(--panel)" stroke="var(--line)"></rect><text x="200" y="72" text-anchor="middle" fill="var(--s2)" font-size="8">opens</text>
    <rect x="310" y="56" width="100" height="24" fill="var(--panel)" stroke="var(--line)"></rect><text x="360" y="72" text-anchor="middle" fill="var(--s2)" font-size="8">opens</text>
    <text x="440" y="72" fill="var(--muted)" font-size="8">agree — the test everyone writes</text>
    <text x="90" y="110" fill="var(--ink)">flaky</text>
    <rect x="150" y="94" width="100" height="24" fill="var(--panel)" stroke="var(--s1)"></rect><text x="200" y="110" text-anchor="middle" fill="var(--s1)" font-size="8">closed (good)</text>
    <rect x="310" y="94" width="100" height="24" fill="var(--acc-soft)" stroke="var(--s2)"></rect><text x="360" y="110" text-anchor="middle" fill="var(--s2)" font-size="8">FALSE-TRIP</text>
    <text x="440" y="110" fill="var(--s2)" font-size="8">differ — the test that matters</text>
  </g>
</svg>
^ Three of the four cells look fine; only the flaky/buggy cell is the disaster, and it is the one an outage-only test never reaches. The bug hides in the single cell nobody checks.

The first row is where the two agree, and it is the row every test writer reaches for — an obvious outage, both breakers open, ship it. The second row is where they differ, and it is the row that decides whether your breaker protects you or attacks you. A breaker validated only on the outage row passes while carrying a bug that will, on some ordinary flaky afternoon, cut off a working dependency. Test the healthy-but-flaky case, because that is the only place the reset matters.

### What we did not settle

A real breaker has a third state and a recovery path we skipped: after opening, it waits a cooldown, then goes half-open and allows one probe call — if it succeeds the breaker closes, if it fails it reopens — so the circuit recovers automatically instead of staying open forever as ours does. Thresholds are often rate-based, not count-based: open if more than X% of calls in a rolling window fail, which handles high-volume services better than a fixed consecutive count. The window itself needs sizing against traffic. And breakers are usually paired with timeouts and fallbacks, so an open circuit returns a cached or degraded response rather than a hard error. The trip logic here — consecutive failures with a reset on success — is the heart; half-open recovery and rate windows are the next layer.

## Build

The practice in one paragraph: guard every call to a fallible dependency with a circuit breaker; trip it on consecutive failures, resetting the count to zero on every success, so only a genuine run opens it; add a cooldown and a half-open probe so it recovers on its own; and test it on a healthy-but-flaky sequence, not just an outage, because the outage case hides the reset bug entirely. Pair it with timeouts and a fallback so an open circuit degrades gracefully.

We opened on the outage. The number that proves the breaker is safe is what it does to a healthy service:

```
# modules/ship-and-operate/code/ship-inter-04/ — COMPLETE, run from that directory
$ python3 breaker.py --compare
  correct (reset on success): opened=False
  buggy (counts all failures): opened=True  at step 7
```

Now build it yourself. Implement a breaker, then run it on two sequences: a real outage (a run of failures) and a healthy service (scattered failures, none consecutive past the threshold). Your number to beat is not that it opens on the outage — both versions do that; it is **that it stays closed on the healthy-but-flaky sequence**, which only the reset-on-success version achieves. Then remove the reset and watch it false-trip. Bring back both breakers' decisions on the flaky sequence. Good luck.

## Definition of done

- [ ] A breaker that opens when the failure count reaches a threshold and fails fast while open
- [ ] The failure count reset to zero on every success (consecutive, not total)
- [ ] An outage sequence (a run of failures) and a healthy-but-flaky sequence (scattered failures)
- [ ] Confirmation the breaker opens on the outage and stays closed on the flaky service
- [ ] The no-reset version run on the flaky sequence, false-tripping
- [ ] Verification that both versions agree on the outage, so the bug is flaky-only
- [ ] `python3 breaker.py --check` printing SELF-TEST PASS: opens-on-outage, holds-on-flaky, buggy-false-trips, agree-on-outage
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why is retrying a failing dependency harmful, and what does opening the circuit accomplish?
2. What is the difference between counting consecutive failures and counting total failures, and which is correct for a breaker?
3. The bug is one missing line. Which one, and why does it make no difference on a real outage?
4. Explain how a healthy service ends up tripping the buggy breaker, and why that is a self-inflicted outage.
5. Your own breaker was run on an outage and a flaky sequence. What did each version do on the flaky one, and why did the outage case fail to reveal the bug?

## External resources

- Michael Nygard, *Release It!* (the Circuit Breaker pattern) — my summary: the origin of the pattern, with the closed/open/half-open states and why failing fast protects both caller and dependency; read it for the full state machine this module cores down to its trip logic.
- resilience4j / Hystrix circuit-breaker documentation — my summary: production breakers with rate-based windows, half-open probes, and fallbacks; read it for the recovery path and the rolling-window trip condition beyond the consecutive count here.
- This hub, *ship-inter-03* — modules/ship-and-operate/ship-inter-03.md — my summary: the token-bucket rate limiter, another resilience primitive whose correctness hinges on one line and hides its bug under ordinary load; read it for the shared lesson — test the adversarial traffic shape, not the happy path.
