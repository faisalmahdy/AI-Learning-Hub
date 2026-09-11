---
id: govern-inter-13
title: Propagate the deadline down the call chain — a fixed per-hop timeout lets a hop work after the client gave up
topic: orchestration-and-governance
level: intermediate
status: ready
time: 21 min
summary: A request arrives with a total time budget, but a fixed per-hop timeout bounds each hop, not the chain, so four 400 ms hops with 600 ms timeouts run to 1600 ms — 600 ms of it after the client's 1000 ms deadline, on work whose answer is discarded, plus a hop that never had a chance to finish still runs. Propagating the absolute deadline caps the chain at the 1000 ms budget, does zero work past it, and skips the doomed hop.
eli5: Imagine you tell a helper you can only wait 10 minutes, and they pass the job through four friends, each allowed 6 minutes. The friends can take 24 minutes total — you left long ago, so most of their work is wasted. Instead, pass along the clock: each friend checks how much of your 10 minutes is left, and if there's none, they don't even start.
---

## Why this module

Every downstream call in a request chain should know when the client stopped caring, and a fixed per-hop timeout never tells it.

A request arrives with a total time budget: the client will wait 1000 ms and then give up. That request fans out into a chain — A calls B calls C calls D — and each hop needs a bound so it cannot hang forever. The obvious bound is a fixed per-hop timeout: give every hop the same generous limit, say 600 ms. That does stop any single hop from hanging. But it bounds each hop in isolation, not the chain as a whole, and the chain is what the client is waiting on.

Here is the arithmetic that bites. Four hops, each allowed up to 600 ms, can run 2400 ms in total. Even at their real 400 ms each, four of them run 1600 ms — and the client left at 1000 ms. Everything computed after 1000 ms is pure waste: when the chain finally returns, the client has already timed out and discarded the answer. Worse, a hop that could not possibly finish before the deadline still starts and runs to completion, burning capacity on work no one will ever read. The per-hop timeout has no idea the deadline exists.

Deadline propagation fixes it by passing the one thing that matters — the absolute deadline — down the chain instead of a per-hop duration. At each hop you compute the remaining budget; if none is left, you do not start the hop at all; otherwise you cap the hop's timeout at what remains. Now the chain is bounded by the budget the client actually set, no hop runs past the deadline, and doomed hops are skipped rather than started. The work stops the instant it can no longer matter.

On the fixture the budget is 1000 ms and four hops each take 400 ms. Fixed 600 ms timeouts run the chain to 1600 ms and do 600 ms of work after the deadline, and the last hop starts with no chance of finishing. Propagating the deadline caps the chain at 1000 ms, wastes nothing, and never starts the doomed hop.

**A fixed per-hop timeout bounds each hop but not the chain, so a call chain can run far past the client's deadline doing discarded work; propagating the absolute deadline caps the whole chain at the budget and skips hops that cannot finish in time.**

## Concepts

The unit that matters is the request's total budget, and a per-hop timeout is the wrong unit. A per-hop timeout answers "how long may this one call take?" in isolation, but the client asked a different question: "how long until I stop waiting for the whole thing?" Those come apart the moment there is more than one hop. With k hops each allowed t, the chain's worst case is k·t, which has nothing to do with the client's budget. Set t generously enough that no healthy hop trips it, and k·t balloons past the budget; set t tight enough to bound the chain and you trip on hops that were merely slow, not stuck.

Everything computed after the deadline is waste, and a per-hop timeout produces it structurally. Once elapsed time crosses the budget, the client has given up and will discard whatever comes back. A hop that starts before the deadline but finishes after it did partly useful work and partly wasted work; a hop that starts entirely after the deadline did nothing but waste. The per-hop timeout cannot tell these apart because it never looks at the clock the client cares about — it only measures its own call's duration from zero.

Deadline propagation changes the currency from duration to a shared absolute time. The client stamps a deadline — "be done by wall-clock T" — and every hop receives T, not a fresh timeout. Each hop's first act is to compute remaining = T − now. That single subtraction does two jobs. If remaining is zero or negative, the hop is already too late, so it is skipped entirely — no doomed work starts. If remaining is positive, the hop caps its own timeout at remaining, so even a hop that would normally take longer is bounded by what the budget actually allows, and it cannot run past T.

<svg role="img" aria-label="A per-hop timeout of t across k hops stacks to k times t, overshooting the client budget, while a propagated deadline holds flat at the budget" viewBox="0 0 470 180" width="470" height="180">
  <rect x="0" y="0" width="470" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">chain bound as hops are added (per-hop t vs propagated deadline)</text>
  <line x1="40" y1="150" x2="450" y2="150" stroke="var(--line)"/>
  <line x1="40" y1="40" x2="40" y2="150" stroke="var(--line)"/>
  <line x1="40" y1="96" x2="450" y2="96" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="360" y="92" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">client budget</text>
  <polyline points="60,138 160,120 260,102 360,84 440,66" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <text x="300" y="70" font-family="var(--mono)" font-size="8" fill="var(--s2)">per-hop: bound = k·t, climbs past budget</text>
  <line x1="60" y1="96" x2="440" y2="96" stroke="var(--acc-line)" stroke-width="2"/>
  <text x="120" y="112" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">propagated: bound stays at the budget</text>
  <text x="56" y="164" font-family="var(--mono)" font-size="8" fill="var(--muted)">1 hop</text>
  <text x="410" y="164" font-family="var(--mono)" font-size="8" fill="var(--muted)">k hops</text>
</svg>
^ A fixed per-hop timeout t makes the chain's bound grow as k·t with each hop added, crossing the client budget; a propagated deadline keeps the bound flat at the budget no matter how many hops.

The result is that the chain inherits exactly one bound — the client's — and it is enforced at every hop for free. No hop needs to know how many hops precede or follow it; each just subtracts its own start time from the shared deadline. This is why deadline propagation is the standard in RPC frameworks and service meshes: gRPC propagates a deadline in call metadata, and each service derives its downstream deadlines from it. The per-hop timeout survives only as a secondary cap for a runaway single call — the primary bound is always the propagated deadline, because the primary thing to protect is the client's budget, not any one hop's.

**A per-hop timeout measures each call from zero and multiplies across the chain; a propagated deadline is a shared absolute time every hop subtracts its start from, so the chain is bounded once by the client's budget and doomed hops are skipped before they start.**

## Worked example

The fixture is a budget, a fixed per-hop timeout, and a chain of hop durations.

```json filename=modules/orchestration-and-governance/code/govern-inter-13/chain.json:3-11 COMPLETE
  "budget_ms": 1000,
  "per_hop_ms": 600,
  "hops": [
    {"hop": "A", "ms": 400},
    {"hop": "B", "ms": 400},
    {"hop": "C", "ms": 400},
    {"hop": "D", "ms": 400}
  ]
```

The client waits 1000 ms. Four hops, each really taking 400 ms, each allowed up to 600 ms by the fixed timeout. The fixed path caps each hop only by its own timeout and starts a hop as soon as the previous one returned.

```python filename=modules/orchestration-and-governance/code/govern-inter-13/deadline.py:44-51 COMPLETE
def run_fixed(hops, per_hop, budget):
    """Each hop gets a fixed timeout; a hop starts as long as the previous one returned."""
    trace, elapsed = [], 0
    for h in hops:
        ran = min(h["ms"], per_hop)              # capped only by the fixed per-hop timeout
        start, elapsed = elapsed, elapsed + ran
        trace.append({"hop": h["hop"], "start": start, "end": elapsed, "started": True})
    return trace
```

The propagated path computes the remaining budget before each hop, skips the hop if none is left, and otherwise caps its timeout at what remains.

```python filename=modules/orchestration-and-governance/code/govern-inter-13/deadline.py:54-66 COMPLETE
def run_propagated(hops, budget):
    """Each hop gets the remaining budget; a hop with no budget left is not started."""
    trace, elapsed = [], 0
    for h in hops:
        remaining = budget - elapsed
        if remaining <= 0:
            trace.append({"hop": h["hop"], "start": elapsed, "end": elapsed, "started": False})
            continue
        ran = min(h["ms"], remaining)            # capped by whatever budget is left
        start, elapsed = elapsed, elapsed + ran
        trace.append({"hop": h["hop"], "start": start, "end": elapsed, "started": True})
    return trace
```

Predict: the fixed chain runs 4 × 400 = 1600 ms, so hops C and D finish past the 1000 ms deadline. The propagated chain should stop at 1000 ms, with the last hop skipped. Walk both.

```text filename=modules/orchestration-and-governance/code/govern-inter-13/deadline.py --run
FIXED per-hop timeout 600 ms   (budget 1000 ms)
----------------------------------------------------------
  A     0.. 400 ms
  B   400.. 800 ms
  C   800..1200 ms  <-- past deadline
  D  1200..1600 ms  <-- past deadline
  total 1600 ms

PROPAGATED deadline   (budget 1000 ms)
----------------------------------------------------------
  A     0.. 400 ms
  B   400.. 800 ms
  C   800..1000 ms
  D  SKIPPED (no budget left)
  total 1000 ms
```

The fixed chain runs to 1600 ms. Hop C runs 800→1200, so 200 ms of it is past the 1000 ms deadline; hop D runs 1200→1600, entirely past it — 400 ms of work that started after the client had already given up. The propagated chain runs A and B identically, then hits C with only 200 ms of budget left, caps C at 1000 ms, and finds no budget left for D, so D is never started. Same four hops, same durations; the difference is entirely in whether each hop knows the deadline.

<svg role="img" aria-label="Two timelines to a 1000 ms deadline: fixed runs four hops to 1600 ms with C and D crossing the deadline; propagated caps C at the deadline and skips D" viewBox="0 0 470 210" width="470" height="210">
  <rect x="0" y="0" width="470" height="210" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">timeline to the 1000 ms deadline (dashed line)</text>
  <line x1="280" y1="34" x2="280" y2="196" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="286" y="46" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">1000 ms</text>
  <text x="30" y="70" font-family="var(--mono)" font-size="9" fill="var(--s2)">fixed</text>
  <g fill="var(--s2)"><rect x="30" y="76" width="90" height="18"/><rect x="122" y="76" width="90" height="18"/></g>
  <rect x="214" y="76" width="90" height="18" fill="var(--s1)"/>
  <rect x="306" y="76" width="90" height="18" fill="var(--s1)"/>
  <text x="60" y="89" font-family="var(--mono)" font-size="8" fill="var(--ink)">A</text>
  <text x="152" y="89" font-family="var(--mono)" font-size="8" fill="var(--ink)">B</text>
  <text x="244" y="89" font-family="var(--mono)" font-size="8" fill="var(--ink)">C</text>
  <text x="336" y="89" font-family="var(--mono)" font-size="8" fill="var(--ink)">D</text>
  <text x="214" y="112" font-family="var(--mono)" font-size="8" fill="var(--s1)">600 ms of work past the deadline is discarded →</text>
  <text x="30" y="150" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">propagated</text>
  <g fill="var(--acc-line)"><rect x="30" y="156" width="90" height="18"/><rect x="122" y="156" width="90" height="18"/><rect x="214" y="156" width="66" height="18"/></g>
  <text x="60" y="169" font-family="var(--mono)" font-size="8" fill="var(--ink)">A</text>
  <text x="152" y="169" font-family="var(--mono)" font-size="8" fill="var(--ink)">B</text>
  <text x="240" y="169" font-family="var(--mono)" font-size="8" fill="var(--ink)">C</text>
  <text x="286" y="169" font-family="var(--mono)" font-size="8" fill="var(--muted)">D skipped — no budget left</text>
</svg>
^ Fixed timeouts let C and D run past the 1000 ms deadline (600 ms of discarded work); propagation caps C at the deadline and never starts D.

## Build

Reproduce the timings. Pure standard library, deterministic, so the 600 ms of fixed-path waste and the propagated path's zero waste come out exactly.

Run `--run` for the two timelines, `--waste` for the discarded work, `--check` for the gate. The waste of a trace is the time any started hop spent past the deadline — the part of its run whose result the client will throw away.

```python filename=modules/orchestration-and-governance/code/govern-inter-13/deadline.py:69-71 COMPLETE
def wasted_after(trace, budget):
    """Total time a hop spent computing past the deadline -- work whose result is discarded."""
    return sum(max(0, t["end"] - max(t["start"], budget)) for t in trace if t["started"])
```

For each started hop this counts only the portion of its run beyond the budget: `end − max(start, budget)`, floored at zero. Hop C contributes 1200 − max(800, 1000) = 200; hop D contributes 1600 − max(1200, 1000) = 400; A and B contribute nothing. That is the 600 ms.

```text filename=modules/orchestration-and-governance/code/govern-inter-13/deadline.py --waste
WASTE — work done after the 1000 ms deadline
----------------------------------------------------------
  fixed:       total 1600 ms   wasted  600 ms
  propagated:  total 1000 ms   wasted    0 ms
----------------------------------------------------------
  propagation skipped the doomed hop(s): ['D']
```

The total time of a trace is just the end of its last hop — which is why the propagated trace tops out at exactly the budget while the fixed one runs long.

```python filename=modules/orchestration-and-governance/code/govern-inter-13/deadline.py:73-74 COMPLETE
def total_time(trace):
    return max((t["end"] for t in trace), default=0)
```

<svg role="img" aria-label="Bar chart of total time and wasted time: fixed reaches 1600 ms with 600 ms wasted, propagated stops at 1000 ms with none wasted" viewBox="0 0 470 180" width="470" height="180">
  <rect x="0" y="0" width="470" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">total time (bar) and the part wasted past the 1000 ms deadline</text>
  <line x1="40" y1="150" x2="450" y2="150" stroke="var(--line)"/>
  <line x1="40" y1="60" x2="450" y2="60" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="380" y="56" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">1000 ms budget</text>
  <text x="70" y="40" font-family="var(--mono)" font-size="9" fill="var(--s2)">fixed</text>
  <rect x="70" y="60" width="120" height="90" fill="var(--s2)"/>
  <rect x="70" y="60" width="120" height="34" fill="var(--s1)"/>
  <text x="76" y="80" font-family="var(--mono)" font-size="8" fill="var(--ink)">600 ms wasted</text>
  <text x="76" y="166" font-family="var(--mono)" font-size="8" fill="var(--s2)">1600 ms total</text>
  <text x="290" y="40" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">propagated</text>
  <rect x="290" y="60" width="120" height="90" fill="var(--acc-line)"/>
  <text x="296" y="166" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">1000 ms total, 0 wasted</text>
</svg>
^ The fixed bar overshoots the budget line with 600 ms of discarded work stacked on top; the propagated bar stops flush at the budget with nothing wasted.

The self-test pins the whole story: fixed timeouts overrun the budget and waste work, propagation caps the chain and wastes none, and the two differ on the doomed hop — fixed starts every hop, propagation skips it.

```text filename=modules/orchestration-and-governance/code/govern-inter-13/deadline.py --check
SELF-TEST — fixed timeouts overrun the budget and waste work; propagation caps and wastes none
--------------------------------------------------------------------------------------------
  fixed timeouts run the chain past the budget = True (1600 ms > 1000 ms)
  fixed timeouts do work after the deadline = True (600 ms wasted)
  propagation caps the chain at the budget = True (1000 ms <= 1000 ms)
  propagation does no work past the deadline = True (0 ms wasted)
  fixed starts every hop but propagation skips the doomed one = True
--------------------------------------------------------------------------------------------
SELF-TEST PASS  fixed_overruns=True  fixed_wastes=True  propagated_caps=True  propagated_no_waste=True  aborts_doomed=True
```

Five True flags. Fixed_overruns and fixed_wastes: the per-hop timeout runs the chain to 1600 ms and does 600 ms of discarded work. Propagated_caps and propagated_no_waste: the propagated deadline holds the chain to the 1000 ms budget and wastes nothing. Aborts_doomed: the fixed path starts all four hops while the propagated path skips D — the concrete difference between bounding each hop and bounding the chain.

**The waste metric counts only the run past the deadline, so it credits nothing to the propagated path — capping the chain at the budget and skipping the doomed hop is what turns 600 ms of discarded work into zero.**

## Definition of done

You are done when you reproduce both timelines and can explain why the per-hop timeout cannot bound the chain.

Concretely: `--run` shows the fixed chain reaching 1600 ms with C and D past the deadline and the propagated chain stopping at 1000 ms with D skipped; `--waste` shows 600 ms wasted versus 0; `--check` prints PASS with five True flags. You can explain that a per-hop timeout of t across k hops bounds the chain only at k·t, which is unrelated to the client's budget, so generous per-hop limits overrun and tight ones trip healthy hops. You can explain that propagating an absolute deadline lets each hop compute its remaining budget, cap its own timeout, and skip itself when nothing is left — bounding the chain once at the client's budget.

The habit to carry: propagate a deadline, not a per-hop timeout, through any call chain, and have each hop refuse to start when the remaining budget is gone. Keep a per-hop timeout only as a secondary guard against a single runaway call. When you see downstream services doing work for requests that have already timed out at the edge, the cause is almost always a missing propagated deadline.

## Boss fight

The instructive failure is a service that stays busy under load serving requests whose clients left long ago.

An API gateway sets a 1 s client timeout and calls a chain of internal services, each configured with its own 800 ms timeout "to be safe." Under load the chain routinely takes 2 s or more, so the gateway times out and returns an error to the client at 1 s — but the internal services keep running, because their 800 ms timeouts have not each individually tripped. The backend spends half its capacity computing answers for requests no one is waiting for, which makes the chain even slower, which makes more requests time out: a congestion collapse driven entirely by wasted post-deadline work. Adding capacity barely helps because the new capacity is also spent on discarded work. The fix is deadline propagation: pass the gateway's 1 s deadline down, and each service abandons a request the moment the budget is exhausted, freeing capacity for requests that can still be answered.

Your turn, two moves. First, make the chain slower than the budget by raising each hop to 500 ms and predict: the fixed path now wastes even more (it runs to 2000 ms, so 1000 ms is past the deadline and two hops are fully doomed), while the propagated path still caps at 1000 ms and simply skips more hops — waste stays zero regardless of how slow the chain gets, which is the whole point. Second, add a small per-hop deadline check cost (say each hop consumes 10 ms of budget just to look at the clock) and confirm propagation still never runs past the deadline; the check overhead shrinks the useful budget slightly but never turns into discarded work, so propagation degrades gracefully where fixed timeouts collapse.

## External resources

The gRPC documentation on deadlines and cancellation is the canonical treatment — it explains why gRPC propagates an absolute deadline in call metadata rather than a per-call timeout, and how each service derives its downstream deadlines from the one it received.

Google's SRE book chapter on handling overload discusses deadline propagation as a defense against congestion collapse, showing how servers that keep working on requests whose deadlines have passed amplify overload rather than shed it.

Any service-mesh timeout guide (Istio, Linkerd) covers the interaction of per-hop timeouts, retries, and propagated deadlines, and warns about the multiplicative blow-up of budgets when timeouts and retries are configured per hop instead of derived from an end-to-end deadline.
