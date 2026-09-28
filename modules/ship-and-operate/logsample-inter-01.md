---
id: logsample-inter-01
title: Sample logs by outcome, not uniformly at the head — or you throw away almost all of the errors you keep logs for
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: At high volume you cannot store every log line or trace, so you keep a sample. The obvious way is uniform head sampling — for each request, before you know how it turns out, keep it with probability r. That keeps a representative slice, fine for measuring throughput or latency, but a disaster for debugging: the reason you keep logs is the rare bad request, and uniform sampling keeps only r of those too. Errors are a small fraction of traffic, so sampling them at the success rate discards almost all the exact lines an on-call engineer comes looking for. Priority sampling decides after the outcome is known: keep every error unconditionally and only r of the successes, capturing 100% of the failures while still shrinking the flood of routine successes. Because errors are rare, keeping all of them barely moves the total volume. On a fixture of 10000 requests at a 2% error rate keeping 5%, uniform stores 500 lines but only 10 of the 200 errors, while priority stores 690 lines — all 200 errors plus 490 sampled successes — capturing 100% of the errors for 38% more volume.
eli5: Imagine a factory where almost every item is fine and a few are defective, and you can only afford to keep a small pile of items to inspect later. If you grab items at random, your pile is mostly fine items and almost none of the defective ones — which are the only ones you actually wanted to study. Better: always set aside every defective item you spot, and only randomly keep a few of the fine ones. Your pile is barely bigger, but now it has every defect in it.
---

## Why this module

Logs and traces exist for the bad request, and sampling exists because you cannot keep them all — so a sampling rule that treats the rare bad request like every other request keeps the data you don't need and drops the data you do.

Above a certain volume, storing every log line or every distributed trace is too expensive, so you keep a fraction — five percent, one percent, whatever the budget allows. The natural implementation is uniform head sampling: as each request arrives, before it has run, flip a weighted coin and decide whether to keep its logs with probability r. This gives an unbiased slice of traffic, and for aggregate questions — what is the p99 latency, how many requests per second — an unbiased slice is exactly right. But debugging is not an aggregate question. When something breaks, the on-call engineer goes looking for the trace of *the failure*, and failures are rare. Sample them at the same r as everything else and you keep only r of them. At five percent sampling and a two percent error rate, ninety-five percent of your errors were discarded at the coin flip, before anyone knew they were errors. The sample is statistically representative and operationally useless.

**Uniform sampling decides before the outcome is known, so it keeps only the sample rate of the errors — and errors are the rare, precious lines the whole logging pipeline exists to preserve, so a representative sample is the wrong sample for debugging.**

Priority sampling moves the decision to after the outcome. Keep every error unconditionally, and keep only the sample rate of the successes. Now you capture one hundred percent of the failures — every trace an engineer might need — while still collapsing the flood of routine successes down to the budget. The cost is tiny precisely because errors are rare: adding all of them to a sample that was mostly successes anyway barely changes the total volume. This is the principle behind tail-based trace sampling, which buffers a trace until it finishes and then keeps it if it errored or was slow — the keep/drop decision belongs after the outcome, not before it. This module computes the error capture and the volume for both schemes.

## Concepts

**Uniform (head) sampling** keeps a fixed fraction r of every line, deciding at request start before the outcome is known. It captures r of the successes and, unavoidably, only r of the errors.

```python filename=modules/ship-and-operate/code/logsample-inter-01/logsample.py:48-50 COMPLETE
def uniform_sample(errors, successes, rate):
    """Head sampling: keep `rate` of every line, deciding before the outcome is known."""
    return {"errors_kept": round(errors * rate), "success_kept": round(successes * rate)}
```

**Priority (outcome/tail) sampling** keeps every error and only r of the successes, deciding after the outcome is known. It captures 100% of the errors.

```python filename=modules/ship-and-operate/code/logsample-inter-01/logsample.py:53-55 COMPLETE
def priority_sample(errors, successes, rate):
    """Outcome sampling: keep every error, and `rate` of the successes."""
    return {"errors_kept": errors, "success_kept": round(successes * rate)}
```

**Error capture** is the fraction of errors that survive into the stored sample — the metric that matters for debugging, and the one uniform sampling silently tanks.

<svg role="img" aria-label="Uniform sampling keeps 5 percent of both errors and successes; priority sampling keeps all errors and 5 percent of successes" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">of the incoming stream, what each scheme stores</text>
  <text x="6" y="34" fill="var(--muted)" font-size="8">uniform</text>
  <rect x="60" y="24" width="12" height="14" fill="var(--s2)"/><text x="76" y="34" fill="var(--muted)" font-size="7">5% of errors (most lost)</text>
  <rect x="60" y="42" width="180" height="10" fill="var(--s1)" opacity="0.4"/><text x="76" y="50" fill="var(--muted)" font-size="6">5% of successes</text>
  <text x="6" y="76" fill="var(--muted)" font-size="8">priority</text>
  <rect x="60" y="66" width="120" height="14" fill="var(--s2)"/><text x="182" y="76" fill="var(--muted)" font-size="7">ALL errors</text>
  <rect x="60" y="84" width="180" height="10" fill="var(--s1)" opacity="0.4"/><text x="76" y="92" fill="var(--muted)" font-size="6">5% of successes</text>
  <text x="6" y="105" fill="var(--muted)" font-size="8">same success sampling; priority keeps every error, uniform keeps a twentieth of them</text>
</svg>
^ Both schemes sample successes the same way, but uniform keeps only 5% of the errors while priority keeps all of them — the difference is entirely in how the rare error class is treated.

**Decide keep-or-drop after the outcome, not before it: keep every error and only a fraction of the successes, so error capture is 100% instead of the sample rate — the rare class is exactly the one a uniform sample destroys.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/logsample-inter-01/logsample.py

The fixture is 10000 requests at a 2% error rate, with a budget that keeps 5%.

```json filename=modules/ship-and-operate/code/logsample-inter-01/logsample.json:3-5 COMPLETE
  "total_requests": 10000,
  "error_rate": 0.02,
  "sample_rate": 0.05
```

Run `--sample` to store the stream both ways.

```text filename=--sample
SAMPLE — 10000 requests, 200 errors (2%), keeping 5%
--------------------------------------------------------------
  scheme     errors kept       successes kept   total kept
  uniform    10   of 200       490              500
  priority   200  of 200       490              690
```

There are 200 errors in the 10000 requests. Uniform sampling keeps 5% of everything, which means 5% of the errors: 10 of the 200. The other 190 errors are gone — not archived elsewhere, not recoverable, discarded at the coin flip before anyone knew they were failures. When an incident review asks "show me the traces for these errors," 95% of the time there is nothing to show. Priority sampling keeps all 200 errors and the same 490 sampled successes, so every failure is preserved. Both schemes stored roughly the same routine-success volume (490 each); the only difference is that uniform threw away 190 errors to save 190 lines, and priority kept them. Trading away the very data the pipeline exists for, to save a rounding error's worth of storage, is the bad bargain uniform sampling makes silently.

<svg role="img" aria-label="Uniform sampling captures 10 of 200 errors; priority sampling captures all 200" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">errors captured (of 200)</text>
  <line x1="70" y1="20" x2="70" y2="76" stroke="var(--grid)"/>
  <text x="6" y="34" fill="var(--muted)" font-size="8">uniform</text>
  <rect x="70" y="26" width="10" height="14" fill="var(--s2)"/><text x="84" y="37" fill="var(--muted)" font-size="7">10 of 200 (5%) — 190 lost</text>
  <text x="6" y="60" fill="var(--muted)" font-size="8">priority</text>
  <rect x="70" y="52" width="200" height="14" fill="var(--s1)"/><text x="120" y="63" fill="var(--panel)" font-size="7">200 of 200 (100%)</text>
  <text x="6" y="88" fill="var(--muted)" font-size="8">the debugging value of the sample is the error bar, and only priority fills it</text>
</svg>
^ Uniform sampling captures 10 of the 200 errors; priority captures all 200 — the same success sampling, but a twentyfold difference in the data that actually gets used during an incident.

## Build

Is keeping all errors too expensive? Run `--budget`.

```text filename=--budget
BUDGET — volume cost vs error-capture gain
------------------------------------------------------------
  uniform:   500 lines, error capture 5%
  priority:  690 lines, error capture 100%
  extra volume for priority: +190 lines (+38%)
------------------------------------------------------------
  a 38% volume increase buys going from 5% to 100% of the errors captured.
```

Priority sampling stores 690 lines against uniform's 500 — 38% more volume — and in exchange the error capture goes from 5% to 100%. That trade is lopsided in priority's favor, and it gets more lopsided the rarer errors are, which is the regime you are actually in. Errors are a small fraction of traffic by definition (a 2% error rate is already a bad day), so the "keep them all" surcharge is a small fraction of the sample. Halve the error rate to 1% and priority's overhead drops to ~19% for the same 100% capture; at a healthy 0.1% error rate it is ~2%. The math rewards exactly the situation you care about: the rarer and more precious the errors, the cheaper it is to keep every one of them. And if even the 38% is over budget, priority sampling can sample successes *harder* — keep all 200 errors and only 300 successes for a 500-line total that matches uniform's budget exactly, still at 100% error capture. The success rate is the free variable; the errors are non-negotiable.

<svg role="img" aria-label="Uniform stores 500 lines at 5 percent error capture; priority stores 690 lines at 100 percent, a small volume increase for a large capture gain" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">volume (bar) and error capture (label)</text>
  <line x1="70" y1="20" x2="70" y2="80" stroke="var(--grid)"/>
  <text x="6" y="34" fill="var(--muted)" font-size="8">uniform</text>
  <rect x="70" y="26" width="145" height="14" fill="var(--s1)"/><text x="219" y="37" fill="var(--muted)" font-size="7">500 lines · 5% capture</text>
  <text x="6" y="62" fill="var(--muted)" font-size="8">priority</text>
  <rect x="70" y="54" width="200" height="14" fill="var(--s2)"/><text x="120" y="65" fill="var(--panel)" font-size="7">690 lines · 100% capture</text>
  <text x="72" y="84" fill="var(--muted)" font-size="7">+38% volume →</text>
  <text x="6" y="94" fill="var(--muted)" font-size="8">a small bar of extra volume buys the entire error class; rarer errors make it cheaper still</text>
</svg>
^ Priority's bar is 38% longer than uniform's, and that small extra volume buys the jump from 5% to 100% error capture — a gap that widens in priority's favor as errors get rarer.

## Definition of done

The self-test pins the trade: uniform captures about the sample rate of errors and loses most of them, priority captures every error, and its total volume stays within a small factor.

```python filename=modules/ship-and-operate/code/logsample-inter-01/logsample.py:108-121 COMPLETE
    uniform_captures_rate = abs(error_capture(u, errors) - sr) < 0.01
    print("  uniform captures about the sample rate of errors = %s (%.0f%%)" % (uniform_captures_rate, error_capture(u, errors) * 100))

    uniform_loses_most = error_capture(u, errors) < 0.5
    print("  uniform loses most of the errors = %s (%d of %d kept)" % (uniform_loses_most, u["errors_kept"], errors))

    priority_captures_all = error_capture(pr, errors) == 1.0
    print("  priority captures every error = %s (%d of %d)" % (priority_captures_all, pr["errors_kept"], errors))

    small_overhead = total_kept(pr) <= 2 * total_kept(u)
    print("  priority's total volume is within a small factor of uniform's = %s (%d vs %d)" % (small_overhead, total_kept(pr), total_kept(u)))

    priority_beats_uniform = error_capture(pr, errors) > error_capture(u, errors)
    print("  priority captures far more errors than uniform = %s (100%% vs %.0f%%)" % (priority_beats_uniform, error_capture(u, errors) * 100))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — uniform captures only the sample rate of errors; priority captures all errors for a small overhead
--------------------------------------------------------------------------------------------------------------
  uniform captures about the sample rate of errors = True (5%)
  uniform loses most of the errors = True (10 of 200 kept)
  priority captures every error = True (200 of 200)
  priority's total volume is within a small factor of uniform's = True (690 vs 500)
  priority captures far more errors than uniform = True (100% vs 5%)
```

**Done means the sampling choice is proven to decide error visibility: uniform sampling captures only the 5% sample rate of errors (10 of 200, losing 190), while priority sampling captures all 200 for a total volume of 690 against uniform's 500 — a 38% overhead that shrinks as errors get rarer, in exchange for going from 5% to 100% error capture.**

## Boss fight

Predict the two ways priority sampling misleads if you forget what it did to the data. It is tempting to treat the stored sample as representative of production.

The first trap is that priority sampling deliberately biases the sample, so you must not compute rates from it. The stored sample now over-represents errors — it contains 100% of errors but only 5% of successes — so the error rate *within the sample* (200/690 ≈ 29%) is wildly higher than the true 2%. Any dashboard that naively counts "errors ÷ total" over the stored logs will report a catastrophe that isn't happening. The fix is to carry the sampling weight: each retained line records the rate at which its class was kept, so downstream aggregation can reweight (divide error counts by 1.0, success counts by 0.05) to recover unbiased totals. Priority sampling is for *keeping the right traces to read*, not for *measuring rates*; metrics must come from unsampled counters or from properly reweighted samples, never from raw counts over a deliberately skewed store.

```python filename=modules/ship-and-operate/code/logsample-inter-01/logsample.py:63-65 COMPLETE
def error_capture(sample, errors):
    """Fraction of the errors that survived into the stored sample."""
    return sample["errors_kept"] / errors if errors else 0.0
```

The second trap is that "keep every error" assumes you know at decision time what an error is, and the most damaging failures are the ones that don't announce themselves. A request that returns HTTP 200 with a subtly wrong body, a slow-but-successful call, a silent data-corruption — none trip an error flag, so priority sampling drops them at the success rate just like uniform would. This is why real tail sampling keys on more than a status code: latency above a threshold, specific error-prone endpoints, a trace touching a suspect dependency, or a random floor of successes kept precisely so that unknown-unknowns still appear. And tail sampling has an operational cost the head approach avoids: you must buffer every trace until it completes to know its outcome, which for long requests holds memory and adds latency to the decision, so at extreme scale it runs as a separate stage with its own capacity. The rule "keep the interesting ones" is only as good as your definition of interesting, and the definition must include a slice of the boring ones to catch what your error detection misses.

**Sample logs and traces by outcome — keep every error and only a fraction of the successes — so error capture is 100% instead of the sample rate, at a volume overhead that shrinks as errors get rarer; but the resulting store is deliberately biased, so record per-class sampling weights and never compute rates from raw sampled counts, and remember "error" must be defined broadly (latency, suspect dependencies, plus a floor of random successes) because the failures that never set an error flag are the ones this scheme would otherwise drop.**

## External resources

Documentation on tail-based versus head-based sampling in distributed tracing (for example the OpenTelemetry Collector's tail-sampling processor) — the buffering mechanics, the policies for "interesting" traces, and the operational cost of deciding after the trace completes.

Any observability reference on log sampling, sampling weights, and computing unbiased metrics from a biased sample — the reweighting needed to recover true rates from a store that over-keeps errors.

The companion "track the p99, not the mean" and "keep metric labels bounded" modules — all three are about extracting signal from high-volume telemetry without keeping (or paying for) all of it, and about the biases that creep in when you summarize or sample the flood.
