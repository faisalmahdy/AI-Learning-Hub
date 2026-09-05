---
id: ship-inter-05
title: Propagate the remaining deadline to each hop, or a slow chain overruns its SLA
topic: ship-and-operate
level: intermediate
status: ready
time: 8-10h
summary: A request that promises a 100ms deadline and fans out to a chain of calls must hand each hop the time that is left, not the full timeout — propagate the remaining budget and a 30-40-50ms chain is bounded, failing fast on the third hop at exactly 100ms rather than running to 120. The bug is giving each hop the original 100ms timeout, so no hop knows the global deadline and every one of them "succeeds" while the request overruns to 120ms and misses its SLA, the caller having already given up. The overrun is invisible on a fast chain that fits inside one hop's timeout and appears only when the chain is slow, which is exactly when the deadline matters — so budget propagation, not per-call timeouts, is what actually enforces a deadline.
eli5: If you have one hour to run three errands, you do not give each errand a full hour — you give the second errand however much time is left after the first, and the third whatever remains. If instead every errand thinks it has the whole hour, you will happily finish the last one long after your hour is up. The clock that matters is the shared one, and every stop has to look at it.
---

## Why this module

A deadline is a promise: respond within this much time, whatever happens downstream. Keeping that promise across a chain of calls is harder than it looks, because the obvious implementation — give each downstream call a timeout — enforces a per-call limit, not the end-to-end deadline the caller actually cares about. This module builds the correct mechanism, deadline budget propagation, and shows the common bug that passes every test on a fast system and silently blows the SLA on a slow one, which is the only time the deadline was ever going to be tested.

The correct idea is that the deadline is a shrinking budget carried through the chain. The request starts with the full budget; each hop is given the time remaining after everything before it, and when it finishes, the budget shrinks by what it took. A hop that would need more than the remaining budget fails fast — it does not run and overrun; it reports deadline-exceeded while the request is still within its promise. The bug is to hand each hop the original timeout instead of the remaining budget. Now every hop measures itself against the full deadline, none of them knows how much time the chain has already spent, and a chain whose durations sum past the deadline runs to completion anyway. The insidious part is that every individual call reports success — each finished inside its own timeout — while the overall request missed its deadline, the caller long gone, the work wasted.

You need no prior module, only the idea of a request that calls other services. Everything runs offline against a chain fixture — a total deadline and per-hop durations — stdlib Python 3, `$0.00`. Time is the fixture's durations, not a wall clock, so the run is deterministic. The instinct to unlearn is that a timeout on each call enforces a deadline. A per-call timeout bounds each call; only propagating the remaining budget bounds the whole.

Here is the correct handling failing fast, on time:

```
# modules/ship-and-operate/code/ship-inter-05/ — COMPLETE, run from that directory
$ python3 deadline.py --trace slow

TRACE — correct budget propagation on 'slow' (deadline=100ms)
------------------------------------------------------------------
  hop 0: took 30ms, 70ms budget remaining
  hop 1: took 40ms, 30ms budget remaining
  hop 2: needs 50ms, only 30ms left -> FAIL FAST (deadline exceeded)
  total elapsed = 100ms (<= deadline 100ms)
```

run: 2026-08-26 · deterministic; durations are a fixture · deadline 100ms · `python3 deadline.py --trace slow`

The budget shrinks 100 → 70 → 30, and the third hop, needing 50ms with only 30 left, fails fast instead of running — total elapsed exactly 100ms, the deadline held. This module is why that fail-fast is correct and what the alternative does.

## Concepts

Named here so you can find them again; each is built below.

- **Deadline** — the total time a request has to respond, promised to the caller.
- **Budget** — the deadline minus time already spent; the time left for the rest of the chain.
- **Budget propagation** — passing each hop the remaining budget as its timeout, not the original.
- **Fail fast** — a hop that would exceed the remaining budget reports deadline-exceeded without running.
- **Per-call timeout** — a limit on one call; bounds the call, not the end-to-end deadline.
- **Silent overrun** — every hop succeeds under its own timeout while the request misses its deadline.

## Worked example

Source: deadline propagation as implemented in RPC frameworks (gRPC deadlines, context.Context in Go, request-scoped timeouts), reduced to a linear call chain; the durations here stand in for real downstream latencies so the elapsed times and the overrun are exact and checkable.

Script and fixture: `modules/ship-and-operate/code/ship-inter-05/` — `deadline.py`, and `chain.json`, a 100ms deadline and two chains: `slow` (30+40+50) and `fast` (20+25+15). Every command runs from there.

### The correct policy: shrink the budget each hop

Carry the remaining budget through the chain. Each hop gets what is left; a hop that needs more fails fast.

```
# deadline.py:39-51 — COMPLETE (propagate the remaining budget; fail fast when it runs out)
def run_with_budget(deadline, durations):
    """Propagate the remaining budget. A hop that exceeds it fails fast at the budget."""
    elapsed = 0
    for d in durations:
        remaining = deadline - elapsed
        if d > remaining:
            elapsed += remaining  # the hop is cut off at the remaining budget
            return elapsed, False  # fail fast: deadline would be exceeded
        elapsed += d
    return elapsed, True
```

<svg viewBox="0 0 700 150" role="img" aria-label="A budget bar shrinking across three hops. Starts full at 100ms. After hop0 (30ms) it is 70. After hop1 (40ms) it is 30. Hop2 needs 50ms but only 30 remains, so the remaining 30 is shaded red as fail-fast and the budget reaches zero at the deadline.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the budget shrinks each hop; hop2 needs more than is left</text>
    <text x="20" y="46" fill="var(--muted)" font-size="8">start</text><rect x="90" y="34" width="500" height="16" fill="var(--s1)"></rect><text x="596" y="46" fill="var(--muted)" font-size="8">100</text>
    <text x="20" y="72" fill="var(--muted)" font-size="8">-hop0 30</text><rect x="90" y="60" width="350" height="16" fill="var(--s1)"></rect><text x="446" y="72" fill="var(--muted)" font-size="8">70 left</text>
    <text x="20" y="98" fill="var(--muted)" font-size="8">-hop1 40</text><rect x="90" y="86" width="150" height="16" fill="var(--s1)"></rect><text x="246" y="98" fill="var(--muted)" font-size="8">30 left</text>
    <text x="20" y="124" fill="var(--muted)" font-size="8">hop2 50?</text><rect x="90" y="112" width="150" height="16" fill="var(--s2)"></rect><text x="246" y="124" fill="var(--s2)" font-size="8">only 30 -> FAIL FAST</text>
  </g>
</svg>
^ Each hop draws down the shared budget; by hop2 only 30ms remain against a 50ms need, so it fails fast rather than borrowing time the request does not have.

The line that enforces the deadline is `remaining = deadline - elapsed`: each hop's real limit is the global deadline minus everything spent so far, not the full deadline. When the third hop of the slow chain asks for 50ms with 30 left, the `d > remaining` check catches it and returns deadline-exceeded at elapsed 100 — bounded. The request fails, but it fails on time, which is the promise. A bounded failure inside the SLA is a correct outcome; an unbounded success past it is not.

### The bug: give every hop the full timeout

The natural wrong implementation gives each hop the original timeout, so no hop sees the shared clock.

```
# deadline.py:54-62 — COMPLETE (the bug: each hop checks the original timeout, not the budget)
def run_full_timeout(deadline, durations):
    """The bug: each hop gets the full timeout, so the chain runs regardless of the deadline."""
    elapsed = 0
    for d in durations:
        if d > deadline:      # each hop only checks against the ORIGINAL timeout
            elapsed += deadline
            return elapsed, False
        elapsed += d          # otherwise it runs fully, ignorant of the global budget
    return elapsed, True
```

The only change is `d > deadline` instead of `d > remaining`. Each hop of the slow chain — 30, 40, 50 — is individually under the 100ms timeout, so each one runs to completion and reports success, and the total climbs to 120ms. No single call did anything wrong by its own measure; the deadline was simply never anyone's job. The chain ran 20ms past the promise, and the function even returns `ok=True`, because from inside, everything worked.

<svg viewBox="0 0 700 200" role="img" aria-label="Two timelines against a 100ms deadline line. Top, budget propagation: hop0 30ms, hop1 40ms, then hop2 fails fast at the 100ms line, total 100ms, bounded. Bottom, full-timeout: hop0 30ms, hop1 40ms, hop2 runs a full 50ms past the deadline line to 120ms, overrunning.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">two policies against the 100ms deadline (each box is a hop, width = ms)</text>
    <line x1="60" y1="30" x2="60" y2="185" stroke="var(--grid)"></line>
    <line x1="560" y1="30" x2="560" y2="185" stroke="var(--acc)" stroke-dasharray="4 3"></line>
    <text x="560" y="28" text-anchor="middle" fill="var(--acc-ink)" font-size="8">deadline 100ms</text>
    <text x="60" y="58" fill="var(--ink)" font-size="8">budget-prop</text>
    <rect x="60" y="64" width="150" height="20" fill="var(--s1)"></rect><text x="135" y="79" text-anchor="middle" fill="var(--panel)" font-size="7">hop0 30</text>
    <rect x="210" y="64" width="200" height="20" fill="var(--s1)"></rect><text x="310" y="79" text-anchor="middle" fill="var(--panel)" font-size="7">hop1 40</text>
    <rect x="410" y="64" width="150" height="20" fill="var(--muted)"></rect><text x="485" y="79" text-anchor="middle" fill="var(--panel)" font-size="7">hop2 fail-fast</text>
    <text x="60" y="118" fill="var(--ink)" font-size="8">full-timeout</text>
    <rect x="60" y="124" width="150" height="20" fill="var(--s2)"></rect><text x="135" y="139" text-anchor="middle" fill="var(--panel)" font-size="7">hop0 30</text>
    <rect x="210" y="124" width="200" height="20" fill="var(--s2)"></rect><text x="310" y="139" text-anchor="middle" fill="var(--panel)" font-size="7">hop1 40</text>
    <rect x="410" y="124" width="250" height="20" fill="var(--s2)"></rect><text x="535" y="139" text-anchor="middle" fill="var(--panel)" font-size="7">hop2 50 (overruns)</text>
    <text x="610" y="139" fill="var(--s2)" font-size="8">120ms</text>
    <text x="60" y="172" fill="var(--muted)" font-size="8">budget-prop stops at the deadline; full-timeout runs 20ms past it, all hops "ok"</text>
  </g>
</svg>
^ Both chains spend the same 30 and 40 on the first two hops. Budget propagation cuts the third off at the deadline line; full-timeout lets it run its full 50ms, crossing the line to 120ms while every hop reports success.

### Both policies side by side

Run both on both chains and the bug's shape is clear.

```
# $ python3 deadline.py --compare
#   chain   sum    budget-prop (elapsed, ok)   full-timeout (elapsed, ok)
#   slow    120    100ms False              120ms True   <-- OVERRUN
#   fast    60      60ms True                60ms True
```

run: 2026-08-26 · deterministic · `python3 deadline.py --compare`

The check also confirms the bug hides on the fast chain, where both policies fit:

```
# deadline.py:119-121 — COMPLETE (on the fast chain both stay within deadline)
    be_fast, _ = run_with_budget(deadline, fast)
    fe_fast, _ = run_full_timeout(deadline, fast)
    both_ok_fast = be_fast <= deadline and fe_fast <= deadline
```

On the fast chain both policies finish at 60ms, both within deadline — the bug is completely invisible, because no hop ever comes close to the limit. On the slow chain they diverge: budget propagation stops at 100ms and reports failure (deadline exceeded, honestly), while full-timeout runs to 120ms and reports success (dishonestly — it missed the SLA). The `ok=True` on that overrun row is the whole danger: a monitoring system watching per-call success would see all green while callers time out, because the failure is in the end-to-end budget that no individual call was tracking.

**A deadline is enforced by propagating the remaining budget to each hop, not by giving each a per-call timeout — the per-call approach bounds each call but lets a slow chain overrun the end-to-end deadline while every hop reports success, and the overrun shows only when the chain is slow, which is exactly when the deadline matters.**

### The self-test

The `--check` mode asserts both behaviours and the bug's hiding place: budget propagation is bounded and fails fast, full-timeout overruns the slow chain, and both fit the fast chain.

```
# $ python3 deadline.py --check
#   budget propagation stays within the deadline on the slow chain = True (100ms <= 100ms)
#   ...and it fails fast rather than overrunning = True (deadline exceeded reported)
#   full-timeout overruns the deadline on the slow chain = True (120ms > 100ms)
#   on the fast chain both stay within deadline (bug hides) = True (60ms, 60ms)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 deadline.py --check`

The two decisive assertions put the policies against the deadline on the slow chain:

```
# deadline.py:105-114 — COMPLETE (budget propagation bounded; full-timeout overruns)
    be_slow, bok_slow = run_with_budget(deadline, slow)
    bounded = be_slow <= deadline

    fe_slow, _ = run_full_timeout(deadline, slow)
    full_overruns = fe_slow > deadline
```

`bounded` requires budget propagation to stay at or under the deadline; `full_overruns` requires the full-timeout policy to exceed it — the deadline kept by one and broken by the other, on the identical chain.

The `bounded` line is the correctness anchor: budget propagation must never exceed the deadline, on any chain, and if the `remaining` computation were wrong that bound would break. The `both_ok_fast` line is what makes the module honest about why the bug survives — it requires the fast chain to pass under both policies, proving the overrun is slow-chain-only and therefore invisible to any test that does not push past the deadline. Test with a chain that exceeds the deadline, or you will never see it.

### The running tally

| chain | sum of hops | budget-prop elapsed | full-timeout elapsed | deadline held? |
|---|---|---|---|---|
| slow | 120ms | 100ms (fail fast) | 120ms (all "ok") | prop yes, full no |
| fast | 60ms | 60ms | 60ms | both yes |

<svg viewBox="0 0 700 150" role="img" aria-label="A 2x2 outcome grid. Rows: slow chain, fast chain. Columns: budget-prop, full-timeout. slow/budget-prop: 100ms, deadline held (fail reported). slow/full-timeout: 120ms OVERRUN, highlighted. fast/budget-prop: 60ms ok. fast/full-timeout: 60ms ok. Only one cell breaks the deadline.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">outcome by chain and policy — one cell overruns</text>
    <text x="230" y="42" text-anchor="middle" fill="var(--ink)">budget-prop</text><text x="440" y="42" text-anchor="middle" fill="var(--ink)">full-timeout</text>
    <text x="80" y="72" fill="var(--ink)">slow</text>
    <rect x="160" y="56" width="140" height="26" fill="var(--panel)" stroke="var(--s1)"></rect><text x="230" y="72" text-anchor="middle" fill="var(--s1)" font-size="8">100ms held</text>
    <rect x="370" y="56" width="140" height="26" fill="var(--acc-soft)" stroke="var(--s2)"></rect><text x="440" y="72" text-anchor="middle" fill="var(--s2)" font-size="8">120ms OVERRUN</text>
    <text x="80" y="112" fill="var(--ink)">fast</text>
    <rect x="160" y="96" width="140" height="26" fill="var(--panel)" stroke="var(--s1)"></rect><text x="230" y="112" text-anchor="middle" fill="var(--s1)" font-size="8">60ms ok</text>
    <rect x="370" y="96" width="140" height="26" fill="var(--panel)" stroke="var(--s1)"></rect><text x="440" y="112" text-anchor="middle" fill="var(--s1)" font-size="8">60ms ok</text>
    <text x="160" y="140" fill="var(--muted)" font-size="8">three cells look fine; the slow/full-timeout cell is the only failure — and the only untested one</text>
  </g>
</svg>
^ Only the slow chain under full-timeout breaks the deadline. The other three cells pass, so a test that omits the slow chain sees nothing wrong — the bug lives in the single cell most test suites skip.

The slow row is the whole lesson. Budget propagation reports a failure but keeps the promise — 100ms, on the deadline; full-timeout reports success but breaks it — 120ms, past the deadline. An honest failure inside the SLA beats a dishonest success outside it, because the caller has already moved on by 120ms and the work is thrown away regardless. The fast row is the trap: identical outcomes, so any test that only runs fast chains certifies the buggy code as correct.

### What we did not settle

Real deadline handling has more edges. The budget must account for the network and queueing time between hops, not just each hop's compute, or the propagated budget is optimistically large. Parallel fan-out changes the arithmetic: sibling calls share the same remaining budget rather than consuming it in sequence, so the deadline is the max of the branches, not the sum. Clock skew across services means the deadline is usually propagated as a duration or an absolute timestamp with care. And a fail-fast on a deadline should still trigger the compensation and cleanup the saga module covered, so a cancelled call does not leave work half-done. The core here — carry the remaining budget, fail fast when it runs out — is the invariant every one of those refines.

## Build

The practice in one paragraph: treat a deadline as a budget that shrinks through the call chain; pass each downstream call the time remaining, not the original timeout; make a hop fail fast when it would exceed the remaining budget, so the request fails on time rather than succeeding late; and test with a chain whose latencies sum past the deadline, because a fast chain certifies the bug as correct. Account for network time between hops, and take the max over parallel branches rather than the sum.

We opened on the fail-fast trace. The number that proves the deadline is enforced is the bounded elapsed on the slow chain:

```
# modules/ship-and-operate/code/ship-inter-05/ — COMPLETE, run from that directory
$ python3 deadline.py --compare
  slow    120    100ms False              120ms True   <-- OVERRUN
```

Now build it yourself. Model a request with a total deadline that calls a chain of downstream services, and propagate the remaining budget to each. Your number to beat is not that the request succeeds; it is **that the total elapsed never exceeds the deadline on a chain whose latencies sum past it**, which only budget propagation guarantees. Then give each hop the full timeout and watch the slow chain overrun while every hop reports success. Bring back the elapsed times under both policies. Good luck.

## Definition of done

- [ ] A request with a total deadline calling a chain of downstream hops
- [ ] The remaining budget propagated to each hop, shrinking by time already spent
- [ ] A hop that would exceed the remaining budget failing fast with deadline-exceeded
- [ ] The full-timeout policy implemented for contrast
- [ ] A slow chain (latencies sum past the deadline) and a fast chain (they do not)
- [ ] Confirmation budget propagation stays within the deadline while full-timeout overruns the slow chain
- [ ] `python3 deadline.py --check` printing SELF-TEST PASS: bounded, fails-fast, full-overruns, both-ok-fast
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why does a per-call timeout on every downstream call fail to enforce an end-to-end deadline?
2. What is the budget, and what is the one line that makes each hop respect the global deadline?
3. On the slow chain, budget propagation reports failure and full-timeout reports success. Explain why the failure is the correct outcome.
4. Why is the bug invisible on a fast chain, and what does that imply about how you must test deadline handling?
5. Your own chain was run under both policies. What were the elapsed times on the slow chain, and which policy kept the deadline?

## External resources

- gRPC / Go context documentation on deadlines and propagation — my summary: how production RPC frameworks carry a request deadline through a call tree and cancel downstream work when it expires; read it for the real API this module models and how cancellation propagates.
- Google SRE Book, chapters on timeouts and cascading failures — my summary: why per-call timeouts without a global budget cause retry storms and cascading overload, and how deadline propagation contains them; read it for the operational stakes of the bug here.
- This hub, *ship-inter-04* — modules/ship-and-operate/ship-inter-04.md — my summary: the circuit-breaker module, another resilience primitive whose bug hides on the easy case (a healthy service) and appears only under stress; read it for the shared discipline — test the adversarial case, because the happy path certifies the bug.
