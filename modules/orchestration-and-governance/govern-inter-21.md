---
id: govern-inter-21
title: Pick the least-loaded of two random workers — one random choice leaves a worker buried under the tail
topic: orchestration-and-governance
level: intermediate
status: ready
time: 19 min
summary: Random dispatch balances load on average but not at the tail: one random choice per task leaves some unlucky worker well above the mean, and that busiest worker sets the queue depth and the tail latency. The power of two choices is a one-line change — sample two random workers and send the task to the less loaded of them — with a wildly disproportionate effect: the expected max load drops from about log n / log log n toward log log n. On 100 tasks over 20 workers (mean 5), averaged across 300 trials, the busiest worker holds 9.62 tasks under one choice and 6.33 under two; a single representative trial shows 9 versus 6. Same tasks, same workers, no global coordination — the only change is sampling two and taking the smaller.
eli5: If everyone in a food court walks up to a random counter, some counter gets a long line just by bad luck. If instead each person glances at two random counters and joins the shorter line, the long lines almost vanish — you barely did more work (you looked at two instead of one) but the worst wait gets much shorter. Servers balance load the same way: checking two and picking the emptier one flattens the busiest one.
---

## Why this module

Balancing load "on average" is easy and almost useless, because the worker that pages you is the busiest one, and uniform random dispatch leaves the busiest one far above the average.

Send each task to a uniformly random worker and every worker gets the same share in expectation — the mean is perfectly balanced. But the mean is not what fills a queue or blows a latency budget; the maximum is. Uniform random has real variance, and with nothing to pull the outliers back, some worker draws more than its share and sits well above the mean. That most-loaded worker is the one whose queue backs up, whose p99 spikes, whose alert fires. You balanced the average and still built a hot spot, because averaging was never the goal.

**Uniform random dispatch balances the mean load but not the maximum, and it is the maximum — the busiest worker — that sets tail latency and queue depth, so "balanced on average" still leaves a hot spot.**

The power of two choices fixes it with almost nothing: instead of picking one worker, sample two at random and send the task to the less loaded of the two. Still no shared counter, no global coordination — two samples and one comparison. But now a task actively avoids the busier of its two options, so a worker that starts running high gets passed over, and the maximum load collapses. This module dispatches the same tasks both ways and measures the busiest worker, averaged over many trials because a single run is noisy.

## Concepts

**Random dispatch (d=1)** sends each task to one uniformly random worker. Zero coordination, perfect mean, but a heavy tail: some worker overshoots.

The **max load** is the metric that matters — the count on the busiest worker. It sets the longest queue and the tail latency, and it is what random dispatch fails to control even while nailing the mean.

**The power of two choices (d=2)** samples two random workers per task and assigns to the less loaded. One extra sample and one comparison; still no global state. The busier of the two is skipped, so hot workers stop attracting tasks.

**The effect is asymmetric to the cost.** Going from one sample to two drops the expected max from roughly `log n / log log n` to `log log n` — an exponential improvement in the tail for a doubling of a tiny per-task cost. Going from two samples to three helps far less; the jump is almost all in the first extra choice.

**A single trial is noise.** With 100 tasks over 20 workers one lucky run of d=1 can beat one unlucky run of d=2, so the claim is about the *expected* max, averaged over many trials — measure one run and you might measure the variance, not the effect.

**Two choices buys tail control, not mean control: the average was already balanced, but sampling two and taking the smaller is what pulls the busiest worker down from ~2x the mean to ~1.3x.**

<svg role="img" aria-label="One choice commits to a random worker even if it is loaded; two choices samples two and skips the busier one" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">a task arrives, workers show their current load</text>
  <text x="8" y="34" fill="var(--s1)" font-size="8">d=1</text>
  <rect x="60" y="24" width="20" height="16" fill="var(--s1)"/><text x="64" y="36" fill="var(--panel)" font-size="8">7</text>
  <text x="85" y="36" fill="var(--muted)" font-size="8">→ picks the one it drew, load 7 (no choice)</text>
  <text x="8" y="76" fill="var(--s2)" font-size="8">d=2</text>
  <rect x="60" y="66" width="20" height="16" fill="var(--s2)"/><text x="64" y="78" fill="var(--panel)" font-size="8">7</text>
  <rect x="86" y="66" width="20" height="16" fill="var(--s2)"/><text x="90" y="78" fill="var(--panel)" font-size="8">2</text>
  <text x="112" y="78" fill="var(--muted)" font-size="8">→ samples two, takes the load-2 worker</text>
  <text x="60" y="106" fill="var(--muted)" font-size="8">the second sample gives the task an option to avoid the busy worker</text>
</svg>
^ One choice must take whatever worker it drew, load and all; two choices draws a second option and sends the task to the emptier one.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/govern-inter-21/twochoices.py

The fixture is a task count, a worker count, and seeds — one for a representative trial, one base for the averaged runs.

```json filename=modules/orchestration-and-governance/code/govern-inter-21/twochoices.json:1-8 COMPLETE
{
  "_meta": "A load-balancing simulation. tasks are dispatched one at a time to workers. Under d=1 (one random choice) each task goes to a uniformly random worker. Under d=2 (power of two choices) each task samples two random workers and goes to the LESS loaded of the two. The MAX load — the busiest worker — sets the tail, so that is what we measure. A single trial is noisy, so --max and --check average the max load over `trials` independent runs (seed = base_seed + trial). --dispatch shows one representative trial (example_seed) so the per-worker loads are concrete. The classic result: going from d=1 to d=2 cuts the expected max from about log n / log log n toward log log n, a large drop for one extra sample.",
  "tasks": 100,
  "workers": 20,
  "base_seed": 1000,
  "trials": 300,
  "example_seed": 1009
}
```

The whole difference is `d`: sample `d` workers and take the least loaded. `d=1` is plain random; `d=2` is the power of two choices.

```python filename=modules/orchestration-and-governance/code/govern-inter-21/twochoices.py:42-51 COMPLETE
def dispatch(tasks, workers, seed, d):
    """Assign each task to a worker. d=1 picks one worker at random; d=2 samples two and takes the less loaded.
    Returns the per-worker load list. rng is seeded so the run is reproducible."""
    rng = random.Random(seed)
    load = [0] * workers
    for _ in range(tasks):
        picks = [rng.randrange(workers) for _ in range(d)]
        chosen = min(picks, key=lambda w: load[w])
        load[chosen] += 1
    return load
```

Run `--dispatch` for one representative trial's per-worker loads.

```text filename=--dispatch
DISPATCH — per-worker load, one representative trial (100 tasks, 20 workers, mean 5.0)
--------------------------------------------------------------------
  one choice (d=1):  [5, 5, 5, 2, 9, 5, 8, 4, 7, 4, 9, 3, 3, 4, 7, 4, 6, 5, 2, 3]   max 9
  two choices (d=2): [5, 5, 6, 5, 4, 4, 5, 6, 4, 6, 4, 5, 5, 5, 5, 6, 6, 5, 4, 5]   max 6
--------------------------------------------------------------------
  one choice leaves a worker well above the mean; two choices flattens the peak.
```

Both dispatch 100 tasks to 20 workers, so both average to 5 per worker. But look at the spread. One choice ranges from 2 to 9 — the busiest worker holds 9, nearly twice the mean, while two workers sit at 2. Two choices ranges from 4 to 6: almost every worker is within one of the mean, and the busiest holds 6. The mean is identical; the tail is transformed.

<svg role="img" aria-label="One choice produces per-worker loads from 2 to 9 with a tall spike; two choices produces loads from 4 to 6, nearly flat" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="12" fill="var(--muted)" font-size="8">per-worker load (representative trial, mean 5)</text>
  <line x1="20" y1="60" x2="290" y2="60" stroke="var(--grid)" stroke-width="1"/><text x="292" y="62" fill="var(--muted)" font-size="7"></text>
  <text x="8" y="30" fill="var(--s1)" font-size="8">d=1</text>
  <rect x="26" y="35" width="8" height="25" fill="var(--s1)"/><rect x="35" y="35" width="8" height="25" fill="var(--s1)"/><rect x="44" y="35" width="8" height="25" fill="var(--s1)"/><rect x="53" y="50" width="8" height="10" fill="var(--s1)"/><rect x="62" y="15" width="8" height="45" fill="var(--s1)"/><rect x="71" y="35" width="8" height="25" fill="var(--s1)"/><rect x="80" y="20" width="8" height="40" fill="var(--s1)"/><rect x="89" y="40" width="8" height="20" fill="var(--s1)"/><rect x="98" y="25" width="8" height="35" fill="var(--s1)"/><rect x="107" y="40" width="8" height="20" fill="var(--s1)"/><rect x="116" y="15" width="8" height="45" fill="var(--s1)"/>
  <text x="120" y="30" fill="var(--s1)" font-size="8">max 9</text>
  <text x="8" y="80" fill="var(--s2)" font-size="8">d=2</text>
  <rect x="26" y="63" width="8" height="25" fill="var(--s2)"/><rect x="35" y="63" width="8" height="25" fill="var(--s2)"/><rect x="44" y="63" width="8" height="30" fill="var(--s2)"/><rect x="53" y="63" width="8" height="25" fill="var(--s2)"/><rect x="62" y="63" width="8" height="20" fill="var(--s2)"/><rect x="71" y="63" width="8" height="20" fill="var(--s2)"/><rect x="80" y="63" width="8" height="25" fill="var(--s2)"/><rect x="89" y="63" width="8" height="30" fill="var(--s2)"/><rect x="98" y="63" width="8" height="20" fill="var(--s2)"/><rect x="107" y="63" width="8" height="30" fill="var(--s2)"/><rect x="116" y="63" width="8" height="20" fill="var(--s2)"/>
  <text x="128" y="80" fill="var(--s2)" font-size="8">max 6</text>
  <text x="20" y="122" fill="var(--muted)" font-size="8">same 100 tasks, same mean — d=1 spikes to 9, d=2 tops out at 6</text>
</svg>
^ One choice leaves one bar towering at 9 while others sit at 2; two choices flattens the whole row so the tallest is 6 — the mean unchanged, the peak halved.

## Build

One trial is noisy, so average the max over many. The view runs the same trials under each strategy and takes the mean of the busiest worker.

```python filename=modules/orchestration-and-governance/code/govern-inter-21/twochoices.py:74-77 COMPLETE
    t, w, bs, tr = data["tasks"], data["workers"], data["base_seed"], data["trials"]
    mean = t / w
    a1 = avg_max(t, w, bs, tr, 1)
    a2 = avg_max(t, w, bs, tr, 2)
```

Run `--max`.

```text filename=--max
MAX — average busiest worker over 300 trials vs the mean
--------------------------------------------------------------
  mean load:          5.0
  one choice avg max: 9.62   (1.9x the mean)
  two choices avg max:6.33   (1.3x the mean)
--------------------------------------------------------------
  the tail worker sets latency; two choices cuts the average peak from 9.62 to 6.33.
```

Across 300 trials the busiest worker averages 9.62 under one choice — nearly double the mean of 5 — and 6.33 under two choices, a third above the mean. The gap to the mean shrinks from 4.62 to 1.33, more than halved, by sampling one extra worker per task. This is why real load balancers (Nginx, HAProxy, and the JSQ(2) literature) use two-choices or least-connections-of-a-sample instead of pure random: the second sample is nearly free and it is the single biggest lever on the tail.

<svg role="img" aria-label="Average max load is 9.62 under one choice and 6.33 under two choices, against a mean of 5" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">average busiest worker over 300 trials (mean = 5)</text>
  <line x1="60" y1="20" x2="60" y2="92" stroke="var(--grid)" stroke-width="1"/>
  <line x1="60" y1="92" x2="285" y2="92" stroke="var(--grid)" stroke-width="1"/>
  <line x1="172" y1="20" x2="172" y2="92" stroke="var(--line)" stroke-width="1" stroke-dasharray="3 3"/><text x="150" y="18" fill="var(--muted)" font-size="7">mean 5</text>
  <rect x="60" y="28" width="215" height="20" fill="var(--s1)"/><text x="200" y="42" fill="var(--panel)" font-size="8">d=1: 9.62 (1.9x)</text>
  <rect x="60" y="58" width="141" height="20" fill="var(--s2)"/><text x="120" y="72" fill="var(--panel)" font-size="8">d=2: 6.33 (1.3x)</text>
  <text x="60" y="108" fill="var(--muted)" font-size="8">the dashed line is the mean; two choices closes most of the gap to it</text>
</svg>
^ The dashed line marks the mean of 5; one choice sits far to its right at 9.62, and two choices pulls most of the way back to 6.33.

## Definition of done

The self-test pins the claims about the averaged max: one choice overshoots the mean, two choices lowers the average max, it more than halves the gap to the mean, load is conserved, and the seeded average is reproducible.

```python filename=modules/orchestration-and-governance/code/govern-inter-21/twochoices.py:95-108 COMPLETE
    one_overshoots = a1 > 1.5 * mean
    print("  one choice's average max is well above the mean = %s (%.2f > %.1f)" % (one_overshoots, a1, 1.5 * mean))

    two_cuts_max = a2 < a1
    print("  two choices lowers the average max = %s (%.2f < %.2f)" % (two_cuts_max, a2, a1))

    two_closer_to_mean = (a2 - mean) < (a1 - mean) / 2
    print("  two choices more than halves the gap to the mean = %s (%.2f < %.2f)" % (two_closer_to_mean, a2 - mean, (a1 - mean) / 2))

    total_conserved = sum(dispatch(t, w, bs, 1)) == sum(dispatch(t, w, bs, 2)) == t
    print("  every trial places all tasks (total load conserved) = %s (%d)" % (total_conserved, t))

    a1_again = avg_max(t, w, bs, tr, 1)
    deterministic = a1 == a1_again
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — one choice overshoots the mean; two choices cuts the average max; the target mean is fixed
--------------------------------------------------------------------------------------------------------
  one choice's average max is well above the mean = True (9.62 > 7.5)
  two choices lowers the average max = True (6.33 < 9.62)
  two choices more than halves the gap to the mean = True (1.33 < 2.31)
  every trial places all tasks (total load conserved) = True (100)
  the seeded average is reproducible = True (9.6233)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  one_overshoots=True  two_cuts_max=True  two_closer_to_mean=True  total_conserved=True  deterministic=True
```

**Done means the tail is provably cut without touching the mean: over 300 trials the busiest worker averages 9.62 (1.9x mean) under one choice and 6.33 (1.3x) under two, both placing all 100 tasks — the gap to the mean more than halved by one extra sample.**

## Boss fight

Two choices nearly flattened the load. Predict what a third or fourth sample buys, and whether "sample all the workers and pick the emptiest" is the right limit. It is tempting to conclude more samples always means better balance, so you should sample as many as you can.

The gain is almost entirely in the first extra choice, and it diminishes fast. Going d=1 to d=2 drops the expected max from `log n / log log n` to `log log n`; going d=2 to d=3 shaves the `log log n` by a constant factor and no more. So the second sample is the bargain and the third is a rounding error, while each extra sample costs another load read on the hot path. Sampling *all* workers (`d = n`, "join the shortest queue") does give the true minimum, but it requires reading every worker's load for every task — the exact global coordination two-choices was designed to avoid — and under stale or delayed load information it can even herd every task onto the one worker that briefly looked emptiest. The sweet spot is two, occasionally three; more samples buy less and cost more.

The subtler trap is stale load information. Two-choices assumes the loads it reads are current; if every dispatcher reads a load snapshot that is a second old, they all see the same "emptiest" worker and pile onto it together — the same worker herd that plagues naive join-shortest-queue. Real systems mitigate this by having each worker report load, adding a little randomness, or decaying old readings, but the lesson stands: the power of two choices is powerful *because* it reads live-enough load, and its guarantee degrades exactly as far as that load is out of date.

```python filename=modules/orchestration-and-governance/code/govern-inter-21/twochoices.py:54-56 COMPLETE
def avg_max(tasks, workers, base_seed, trials, d):
    """Mean of the max load over `trials` independent trials (seed = base_seed + trial)."""
    return sum(max(dispatch(tasks, workers, base_seed + i, d)) for i in range(trials)) / trials
```

**Sample two workers and take the less loaded: the second sample is nearly free and collapses the expected max from log n / log log n toward log log n, but a third sample buys little, sampling all of them reintroduces the global coordination you were avoiding, and the guarantee holds only as far as the load readings are current.**

## External resources

Mitzenmacher's "The Power of Two Choices in Randomized Load Balancing" — the thesis and papers that proved the log n / log log n to log log n result and named the technique.

The Nginx and HAProxy documentation on the "least connections" and "random with two choices" (`random two least_conn`) balancing methods — the production implementations, and their notes on why two beats pure random and full least-connections.

The companion "assign keys with a hash ring" and "fan-out needs a partition contract" modules — hashing places keys deterministically while two-choices balances dynamically; together they cover the two halves of spreading work across a fleet.
