---
id: ship-inter-19
title: Pool the samples to get a fleet percentile — averaging per-shard p90s reports a number that is nowhere
topic: ship-and-operate
level: intermediate
status: ready
time: 19 min
summary: Dashboards love to compute a percentile per shard or host and then average those into one fleet number. It reads as reasonable — average the p90s to get the overall p90 — and it is wrong, because a percentile is not a mean and does not average. Averaging weights every shard equally, so a tiny overloaded shard serving 10 requests counts as much as a healthy shard serving 90. The averaged value is not the fleet's p90; it is not any percentile of anything. The correct fleet percentile comes from the pooled samples — every request's latency in one set — or, in production, from merged histograms, so each shard is weighted by the requests it actually served. On a small_slow shard (10 requests at 200ms, p90 200) and a big_fast shard (90 at 10ms, p90 10), averaging gives 105ms while the pooled p90 is 10ms, overstating the tail more than tenfold.
eli5: If one small classroom has very tall kids and a big classroom has average kids, you cannot find the school's tallest-tenth height by averaging each room's tallest-tenth. The big room has far more kids, so it should count more. You have to line up every kid in the whole school and then look at the tall end. Percentiles have to be measured on everyone together, not blended from each group.
---

## Why this module

Combining percentiles by averaging them feels like arithmetic and is a category error — a percentile is a position in a distribution, and positions from different distributions do not add up.

The setup is everywhere: each shard, host, or region reports its own p90 latency, and a dashboard averages those p90s into a single fleet p90. The number looks authoritative and is meaningless. Averaging gives every shard an equal vote regardless of how much traffic it served, so a small shard handling a sliver of requests distorts the fleet figure as much as the shard handling almost all of them. The result is not the fleet's p90 — it is not any percentile of any real distribution, just a blend of two positions that happens to land between them.

**A percentile is a rank in a distribution, not a quantity you can mean — averaging per-shard percentiles weights shards, not requests, so the answer is nowhere in the data.**

The fix is to combine the distributions first, then take the percentile: pool every request's latency into one set (or, at scale, sum the shards' histograms) and read the percentile off that. Pooling weights each shard by its actual request count, so a minority shard's tail occupies only its true share. This module computes the averaged figure and the pooled figure and shows how far apart they are.

## Concepts

A **percentile** (p90) is the value below which 90% of the samples fall — a rank-based position in the sorted data, computed here by nearest rank.

**Averaging per-shard percentiles** computes each shard's p90 and takes the mean of those. Its flaw is the equal weighting: two shards contribute equally to the mean even if one served ten requests and the other ninety.

**Pooling** concatenates every shard's samples into one set and takes the percentile of that. Because the pool contains each shard's requests in proportion to how many it served, the percentile is weighted by traffic automatically. In production you cannot ship raw samples around, so the equivalent is to **merge histograms**: each shard reports per-bucket counts, the counts sum, and the percentile is read off the summed histogram — same result, bounded data.

The mechanism of the gap is minority weighting. A shard that serves 10% of traffic, all of it slow, contributes its slow requests to the pool — but they are only 10% of the pool, so they land in the top decile, at or above p90, and do not move p90 itself. Averaging, by contrast, lets that 10%-shard's p90 count for half of the fleet number.

**The right operation is combine-then-percentile; averaging is percentile-then-combine, and swapping the order changes the answer.**

The two orderings are genuinely different operations, and only one of them reconstructs a real distribution to read a rank from.

<svg role="img" aria-label="Two paths: percentile-then-average collapses each shard to a number then blends them; combine-then-percentile merges the samples first then takes one rank" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="16" fill="var(--s1)" font-size="8">wrong: percentile → average</text>
  <rect x="15" y="22" width="30" height="16" fill="none" stroke="var(--line)" stroke-width="1"/><text x="20" y="34" fill="var(--muted)" font-size="7">A</text>
  <rect x="50" y="22" width="30" height="16" fill="none" stroke="var(--line)" stroke-width="1"/><text x="55" y="34" fill="var(--muted)" font-size="7">B</text>
  <text x="90" y="34" fill="var(--muted)" font-size="7">→ p90 each → mean → 105</text>
  <line x1="10" y1="52" x2="290" y2="52" stroke="var(--line)" stroke-width="1"/>
  <text x="10" y="70" fill="var(--s2)" font-size="8">right: combine → percentile</text>
  <rect x="15" y="76" width="30" height="16" fill="var(--s2)" opacity="0.5"/><rect x="50" y="76" width="30" height="16" fill="var(--s2)" opacity="0.5"/>
  <text x="90" y="88" fill="var(--muted)" font-size="7">→ pool all samples → p90 → 10</text>
  <text x="15" y="112" fill="var(--muted)" font-size="8">collapsing first throws away the ranks the percentile needs</text>
</svg>
^ Taking each shard's percentile first discards the sample ranks, leaving only two numbers to blend; pooling keeps every sample so the fleet percentile can be read from the real combined distribution.

The rule is absolute for percentiles: means average, counts add, histograms merge — percentiles do none of those, so you must reconstruct the distribution before taking one.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/ship-inter-19/percentiles.py

The fixture is two shards' latency samples: a small slow one and a big fast one.

```json filename=modules/ship-and-operate/code/ship-inter-19/latencies.json:1-5 COMPLETE
{
  "_meta": "Latency samples (ms) from two shards of a service over one window. 'small_slow' is a small shard (10 requests) whose replica is overloaded -- every request is slow. 'big_fast' is the bulk of traffic (90 requests) and is healthy. percentile is the tail percentile to report (90 = the 90th). The question: can you get the fleet's p90 by taking each shard's p90 and averaging them?",
  "percentile": 90,
  "shards": {
    "small_slow": [200, 200, 200, 200, 200, 200, 200, 200, 200, 200],
```

The next line (elided here for length) is `"big_fast"` with ninety samples of 10ms — the healthy bulk of the traffic.

The percentile is nearest-rank; pooling concatenates the samples; averaging means the per-shard values. Three small functions, two philosophies.

```python filename=modules/ship-and-operate/code/ship-inter-19/percentiles.py:42-57 COMPLETE
def percentile(samples, p):
    """Nearest-rank percentile: the smallest value at or above the p-th position."""
    s = sorted(samples)
    idx = max(0, min(len(s) - 1, math.ceil(p / 100 * len(s)) - 1))
    return s[idx]


def average(xs):
    return sum(xs) / len(xs)


def pooled(shards):
    out = []
    for v in shards.values():
        out += v
    return out
```

The percentiles view computes each shard's p90, means them, and separately pools all samples.

```python filename=modules/ship-and-operate/code/ship-inter-19/percentiles.py:62-72 COMPLETE
def percentiles_view(data):
    p, shards = data["percentile"], data["shards"]
    per_shard = {name: percentile(v, p) for name, v in shards.items()}
    print("PERCENTILES — per-shard p%d, their average, and the pooled p%d" % (p, p))
    print("-" * 62)
    for name, v in shards.items():
        print("  %-11s %3d requests   p%d = %dms" % (name, len(v), p, per_shard[name]))
    print("  -")
    print("  average of the p%ds:  %.0fms   <- the tempting wrong answer" % (p, average(list(per_shard.values()))))
    print("  pooled p%d:           %dms   <- the correct fleet value" % (p, percentile(pooled(shards), p)))
```

Run `--percentiles`.

```text filename=--percentiles
PERCENTILES — per-shard p90, their average, and the pooled p90
--------------------------------------------------------------
  small_slow   10 requests   p90 = 200ms
  big_fast     90 requests   p90 = 10ms
  -
  average of the p90s:  105ms   <- the tempting wrong answer
  pooled p90:           10ms   <- the correct fleet value
--------------------------------------------------------------
  averaging counts the two shards equally; pooling counts requests.
```

The small shard's p90 is 200, the big shard's is 10. Average them and you get 105ms — a fleet p90 that looks alarming. Pool all 100 requests and the p90 is 10ms. The averaged figure is more than ten times the truth, invented entirely by giving a 10-request shard the same weight as a 90-request one.

<svg role="img" aria-label="Per-shard p90s 200 and 10 average to 105, but the pooled p90 is 10 — the average is far above the truth" viewBox="0 0 300 130" width="300" height="130">
  <line x1="55" y1="12" x2="55" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <line x1="55" y1="95" x2="285" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <rect x="55" y="18" width="200" height="12" fill="var(--muted)"/><text x="200" y="28" fill="var(--muted)" font-size="7">small_slow p90 200</text>
  <rect x="55" y="34" width="10" height="12" fill="var(--muted)"/><text x="70" y="44" fill="var(--muted)" font-size="7">big_fast p90 10</text>
  <rect x="55" y="54" width="105" height="12" fill="var(--s1)"/><text x="164" y="64" fill="var(--s1)" font-size="7">average 105 (wrong)</text>
  <rect x="55" y="70" width="10" height="12" fill="var(--s2)"/><text x="70" y="80" fill="var(--s2)" font-size="7">pooled 10 (correct)</text>
  <text x="55" y="112" fill="var(--muted)" font-size="8">the average lands 10x above the real fleet p90</text>
</svg>
^ The averaged bar sits ten times higher than the pooled bar — a number that matches neither shard's reality and overstates the fleet tail by an order of magnitude.

## Build

Why does pooling barely notice the slow shard? Run `--pool`.

```text filename=--pool
POOL — why the slow shard barely moves the pooled p90
--------------------------------------------------------------
  total requests: 100   slow requests: 10 (10% of traffic)
  the slowest 10% of 100 requests start at position 90
  the 10 slow requests sit above p90, so p90 reads the fast value 10ms
--------------------------------------------------------------
  a minority shard's tail lands past p90 and does not set it.
```

The slow shard is exactly 10% of traffic, and p90 is the boundary of the slowest 10%. So the ten slow requests fill positions 91–100 — above p90 — and the value at p90 itself is the fast 10ms. Pooling placed the slow requests at their true rank in the fleet; they are real, but they are the top decile, not the ninetieth percentile. Averaging erased that ranking by collapsing each shard to one number before combining.

<svg role="img" aria-label="100 pooled requests sorted: positions 1 to 90 are fast at 10ms, positions 91 to 100 are the slow shard at 200ms, so p90 sits at the boundary value 10" viewBox="0 0 300 110" width="300" height="110">
  <rect x="20" y="30" width="216" height="20" fill="var(--s2)"/>
  <text x="90" y="44" fill="var(--panel)" font-size="8">90 fast requests (10ms)</text>
  <rect x="236" y="30" width="44" height="20" fill="var(--s1)"/>
  <text x="238" y="44" fill="var(--panel)" font-size="7">10 slow</text>
  <line x1="236" y1="24" x2="236" y2="60" stroke="var(--ink)" stroke-width="1.5"/>
  <text x="205" y="72" fill="var(--ink)" font-size="8">p90 boundary</text>
  <text x="245" y="72" fill="var(--s1)" font-size="7">p91–p100</text>
  <text x="20" y="95" fill="var(--muted)" font-size="8">the slow shard occupies the top decile, so p90 = 10ms</text>
</svg>
^ Sorted across the fleet, the slow shard's ten requests are the last ten — above the p90 line — so the ninetieth percentile reads the fast value and the slow tail shows only at higher percentiles.

## Definition of done

The self-test pins the error: the average differs from the pooled p90, it overstates the tail, the shards are unequal in size, the pooled p90 matches the majority shard, and pooling uses every sample.

```python filename=modules/ship-and-operate/code/ship-inter-19/percentiles.py:97-109 COMPLETE
    average_differs_from_pooled = avg != pool_p
    print("  averaging the p%ds differs from the pooled p%d = %s (%.0f vs %d)" % (p, p, average_differs_from_pooled, avg, pool_p))

    averaging_overstates = avg > pool_p
    print("  the averaged number overstates the tail = %s (%.0f > %d)" % (averaging_overstates, avg, pool_p))

    shards_unequal_size = len(shards["small_slow"]) != len(shards["big_fast"])
    print("  the shards serve different request counts = %s (%d vs %d)" % (shards_unequal_size, len(shards["small_slow"]), len(shards["big_fast"])))

    pooled_matches_majority = pool_p == percentile(shards["big_fast"], p)
    print("  the pooled p%d matches the majority shard's value = %s (%dms)" % (p, pooled_matches_majority, pool_p))

    pooled_uses_all_samples = len(pooled(shards)) == sum(len(v) for v in shards.values())
    print("  pooling uses every request's sample = %s (%d)" % (pooled_uses_all_samples, len(pooled(shards))))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the average of per-shard p90s is not the pooled p90; only pooling is correct
----------------------------------------------------------------------------------------------------
  averaging the p90s differs from the pooled p90 = True (105 vs 10)
  the averaged number overstates the tail = True (105 > 10)
  the shards serve different request counts = True (10 vs 90)
  the pooled p90 matches the majority shard's value = True (10ms)
  pooling uses every request's sample = True (100)
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  average_differs_from_pooled=True  averaging_overstates=True  shards_unequal_size=True  pooled_matches_majority=True  pooled_uses_all_samples=True
```

**Done means the discrepancy is exact, not vague: the averaged 105ms and the pooled 10ms differ tenfold, and the pooled value equals the majority shard's p90 because that shard is 90% of traffic.**

## Boss fight

Here averaging overstated the tail. Predict whether averaging per-shard percentiles always overstates. It is tempting to look for a consistent bias to correct for.

There is none, and that is what makes averaging dangerous rather than merely conservative. Flip the fixture — a big slow shard and a small fast one — and averaging understates the tail, hiding a real problem. Averaging per-shard percentiles has no fixed direction of error; it can be high, low, or accidentally right, depending on the shard sizes and shapes, so you cannot apply a fudge factor. The only correct move is to reconstruct the distribution, which is why every serious metrics system (Prometheus histograms, HDR histograms, t-digests) stores mergeable distributions per shard and computes the percentile after merging.

The mirror-image mistake is to fix the weighting but keep averaging — computing a request-count-weighted average of the per-shard p90s. That is closer, but still wrong, because a percentile of a mixture is not any weighted average of the components' percentiles; the p90 can fall in a region no shard's p90 occupies. Weighting addresses who counts how much, but the fundamental error is combining percentiles at all. Combine the distributions, then take the percentile — never the other way.

```python filename=modules/ship-and-operate/code/ship-inter-19/percentiles.py:53-57 COMPLETE
def pooled(shards):
    out = []
    for v in shards.values():
        out += v
    return out
```

**Get a fleet percentile by pooling the samples or merging the shards' histograms and then taking the percentile — never by averaging per-shard percentiles, which has no fixed error direction and cannot be corrected with a weight.**

## External resources

The Prometheus documentation on histograms and `histogram_quantile` — why you aggregate the bucket counts across instances and then compute the quantile, and why averaging `..._quantile` series is explicitly wrong.

Ted Dunning's t-digest and Gil Tene's HDR Histogram — mergeable data structures built precisely so per-shard distributions can be combined before a percentile is read.

Gil Tene, "How NOT to Measure Latency" — the broader talk on percentile pitfalls, including the averaging error and coordinated omission, for operators reasoning about tails.
