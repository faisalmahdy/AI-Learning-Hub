---
id: percentile-inter-01
title: Compute the fleet p99 from the merged samples — averaging per-host p99s is not a percentile and hides the tail
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: A percentile is a rank statistic — the p99 is the value 99% of requests came in under — and that definition is about one pooled set of measurements, not a partition of it. Means distribute over groups (the mean of two groups is the weighted average of their means), but percentiles do not: the p99 of two hosts is not the average of their p99s and is generally not any simple function of them. So a dashboard that averages each host's reported p99 to get "the fleet p99" answers a question nobody asked and under-reports the real tail, because a slow host's slow requests get diluted by the fast hosts' low cutoffs instead of counted. The fix is to aggregate the distributions first — merge every host's samples, or equivalently sum their histograms bucket by bucket — and take the percentile of the pool. On a fixture where two hosts serve 100 requests at 10ms and a third serves 90 at 10ms and 10 at 1000ms, the mean of the per-host p99s is 340ms while the true fleet p99 from all 300 requests is 1000ms — averaging hid 660ms of tail, 2.9× — and the fleet median stays 10ms, so a median-only view shows nothing wrong.
eli5: Say three checkout lines each timed their customers. Two lines were fast; one line had a few people who waited a really long time. If you ask each line "what was your slowest-typical wait?" and then average those three answers, the one bad line's long waits get washed out by the two good lines, and you conclude things were fine. But a real customer doesn't experience the average of the lines — they're one specific person in one specific line. To know how bad the slow experiences really were, you have to throw everyone's wait times into one big pile and find the slow cutoff of the whole pile. Averaging the per-line summaries lies; pooling the raw times tells the truth.
---

## Why this module

Every latency dashboard shows a p99, and almost every one that spans more than one host computes it wrong — by averaging the hosts' p99s. The number looks reasonable, the graph is smooth, and it under-reports the exact thing a p99 exists to catch.

A percentile is a rank statistic. The p99 of a set of latencies is the value at the 99th-of-100 position when you sort them — the number that 99% of requests came in under. That definition is about one pooled set of measurements. It does not distribute over a partition of the data, because rank is not linear. The mean does distribute: the mean of two groups is the weighted average of their means, so you can average per-group means and get the right grouped mean. The p99 does not: the p99 of two hosts' requests is not the average of the two hosts' p99s, and generally is not any simple function of them at all. So when a service runs on many hosts and each reports its own p99, averaging those numbers computes "the average of our hosts' tail cutoffs" — a quantity with no operational meaning — and it silently under-reports the real fleet tail, because a slow host's slow requests get diluted by the fast hosts' low p99s instead of counted as the slow requests they are.

The correct fleet percentile comes from the pooled requests: merge every host's samples into one set and take the percentile of that. Equivalently and cheaply, sum the hosts' histograms bucket by bucket and read the percentile off the combined histogram — histograms are mergeable because bucket counts add, which is exactly why real metrics systems ship per-host histograms or mergeable sketches (t-digest, HDR histogram) and combine *those*, never per-host percentiles. The rule is one line: aggregate the distributions, then take the percentile; never take the percentiles, then aggregate. This module runs both aggregations on three hosts and shows the gap.

**A percentile is a rank over one pooled sample and does not average across groups, so the fleet p99 must be computed from the merged samples (or summed histograms) — averaging per-host p99s dilutes a slow host's tail and reports a latency the fleet never had.**

## Concepts

**The percentile** is nearest-rank: sort the values, and the pXX is the value at rank `ceil(XX/100 × n)`. Reading it off a `{latency: count}` histogram just walks the buckets in order until the cumulative count reaches that rank.

```python filename=modules/ship-and-operate/code/percentile-inter-01/percentile.py:44-54 COMPLETE
def hist_percentile(hist, q):
    """Nearest-rank percentile of a {latency_ms: count} histogram: the value at rank ceil(q/100 * total)."""
    values = sorted(int(v) for v in hist)
    total = sum(hist.values())
    rank = max(1, math.ceil(q / 100 * total))
    cum = 0
    for v in values:
        cum += hist[str(v)]
        if cum >= rank:
            return v
    return values[-1]
```

**Merging** is the only correct way to combine hosts: sum the histograms bucket by bucket. Counts are additive — three requests at 10ms here plus five there are eight requests at 10ms — so the merged histogram is the true pooled distribution, and its percentile is the true fleet percentile. Percentiles are not additive, which is why you merge the distributions and never the percentiles.

```python filename=modules/ship-and-operate/code/percentile-inter-01/percentile.py:57-63 COMPLETE
def merge_hists(hosts):
    """Sum the per-host histograms bucket by bucket -- the correct way to combine, because counts are additive."""
    merged = {}
    for h in hosts:
        for bucket, count in h["hist"].items():
            merged[bucket] = merged.get(bucket, 0) + count
    return merged
```

<svg role="img" aria-label="A sorted row of 100 request latencies with the p99 marked at the 99th position, illustrating that a percentile is a rank over one pooled set" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">a percentile is a rank over ONE pooled, sorted sample</text>
  <g transform="translate(20,28)">
  <rect x="0" y="0" width="230" height="16" fill="var(--panel)" stroke="var(--line)"/>
  <text x="4" y="12" fill="var(--muted)" font-size="7">sorted requests: fast ————————————————→ slow</text>
  <line x1="228" y1="-4" x2="228" y2="20" stroke="var(--s2)"/>
  <text x="196" y="-8" fill="var(--muted)" font-size="7">p99 cutoff</text>
  <rect x="228" y="0" width="2" height="16" fill="var(--s2)"/>
  </g>
  <text x="20" y="66" fill="var(--muted)" font-size="8">means average across groups; ranks do not —</text>
  <text x="20" y="80" fill="var(--muted)" font-size="8">so you pool the samples, THEN take the rank</text>
</svg>
^ The p99 is the value at the 99% rank of one sorted, pooled sample; because rank does not distribute over a partition, you must pool every host's requests before ranking, not rank each host and average.

**Merge the histograms first because counts add, then take the percentile of the pool — the reverse order, percentile-then-average, computes a number the fleet never experienced.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/percentile-inter-01/percentile.py

The fixture is three hosts, each 100 requests, as histograms. Two are healthy at 10ms; the third has a slow tenth at 1000ms.

```json filename=modules/ship-and-operate/code/percentile-inter-01/percentile.json:3-7 COMPLETE
  "hosts": [
    {"name": "web-1", "hist": {"10": 100}},
    {"name": "web-2", "hist": {"10": 100}},
    {"name": "web-3", "hist": {"10": 90, "1000": 10}}
  ]
```

Run `--aggregate` to compute both the averaged and the merged p99.

```text filename=--aggregate
AGGREGATE — per-host p99, averaged vs merged
------------------------------------------------------------
  host      requests   p99 (ms)
  web-1     100        10
  web-2     100        10
  web-3     100        1000
------------------------------------------------------------
  mean of the per-host p99s (WRONG) = 340.0 ms
  p99 of the merged samples  (RIGHT) = 1000 ms
  averaging hid 660.0 ms of tail -- it under-reports by 2.9x
```

The two healthy hosts have p99 = 10ms and the degraded host has p99 = 1000ms. Average those three numbers and you get 340ms — a tail that looks merely elevated, the kind of number you might not page on. But the true fleet p99, computed from all 300 requests pooled, is 1000ms: one request in a hundred across the whole service really waits a full second. Averaging did not approximate that badly; it produced a number 2.9× too low, and 340ms is not a rounded-off 1000ms — it is the wrong quantity, the mean of three cutoffs rather than a cutoff of the pool. Notice *why* it under-reports specifically: the slow host's ten 1000ms requests are real and numerous enough to sit above the fleet's 99% rank, but when you first reduce that host to a single p99 number and then average, those ten requests stop being counted as slow requests and become one-third of a vote for "1000", outvoted by two votes for "10".

## Build

Pooling the requests shows both the true tail and why one common defense — watching the median — misses it entirely. Run `--merge`.

```text filename=--merge
MERGE — sum the histograms, then read percentiles off the pool
------------------------------------------------------------
  merged histogram (latency ms -> requests): {10: 290, 1000: 10}
  total requests = 300
------------------------------------------------------------
  fleet p50 = 10 ms
  fleet p90 = 10 ms
  fleet p99 = 1000 ms
  the median is 10 ms -- a median-only dashboard shows nothing wrong, but 1% of requests wait 1000 ms.
```

Summed bucket by bucket, the fleet is 290 requests at 10ms and 10 at 1000ms. Its p50 and p90 are both 10ms — the median is perfectly healthy, because 99% of requests *are* fast — and only the p99 exposes the 10 slow ones. This is the second lesson riding along with the first: not only does averaging per-host p99s understate the tail, but any central-tendency view (mean, median) hides a tail that is small in count and large in magnitude. The slow requests are 3.3% of traffic here yet invisible below p90, which is why tail percentiles exist and why they must be computed correctly — a wrong p99 and a healthy-looking median together would let this degradation ship unnoticed. The wrong aggregation is just the same percentile function applied at the wrong level: per host, then averaged.

```python filename=modules/ship-and-operate/code/percentile-inter-01/percentile.py:66-69 COMPLETE
def mean_of_host_percentiles(hosts, q):
    """The WRONG aggregation: take each host's percentile, then average those numbers."""
    ps = [hist_percentile(h["hist"], q) for h in hosts]
    return sum(ps) / len(ps)
```

<svg role="img" aria-label="The merged fleet histogram: a tall bar of 290 requests at 10ms and a short bar of 10 requests at 1000ms, with p50 and p90 landing in the tall bar and p99 landing in the short slow bar" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">merged fleet: 290 fast, 10 slow — p50/p90 miss the tail, p99 catches it</text>
  <line x1="30" y1="96" x2="290" y2="96" stroke="var(--line)"/>
  <rect x="60" y="26" width="50" height="70" fill="var(--s1)"/><text x="58" y="108" fill="var(--muted)" font-size="7">10 ms (290)</text>
  <rect x="200" y="88" width="50" height="8" fill="var(--s2)"/><text x="190" y="108" fill="var(--muted)" font-size="7">1000 ms (10)</text>
  <line x1="70" y1="20" x2="70" y2="96" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="60" y="24" fill="var(--muted)" font-size="7">p50</text>
  <line x1="95" y1="20" x2="95" y2="96" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="88" y="24" fill="var(--muted)" font-size="7">p90</text>
  <line x1="225" y1="20" x2="225" y2="88" stroke="var(--s2)"/><text x="216" y="24" fill="var(--muted)" font-size="7">p99</text>
</svg>
^ In the pooled histogram 99% of requests fall in the 10ms bar, so p50 and p90 sit inside it and read healthy; only p99 reaches the 1000ms bar, which is why the tail percentile is the one that must be computed from the pool.

<svg role="img" aria-label="Two bars: the averaged per-host p99 at 340ms and the true merged fleet p99 at 1000ms, with the fleet median marked far below at 10ms" viewBox="0 0 300 120" width="300" height="120">
  <text x="6" y="12" fill="var(--muted)" font-size="8">averaging (340) vs the true pooled p99 (1000)</text>
  <line x1="60" y1="100" x2="290" y2="100" stroke="var(--line)"/>
  <line x1="60" y1="24" x2="290" y2="24" stroke="var(--grid)" stroke-dasharray="2 2"/>
  <text x="54" y="28" fill="var(--muted)" font-size="7" text-anchor="end">1000</text>
  <text x="54" y="78" fill="var(--muted)" font-size="7" text-anchor="end">340</text>
  <text x="54" y="99" fill="var(--muted)" font-size="7" text-anchor="end">10</text>
  <rect x="90" y="74" width="40" height="26" fill="var(--s2)"/><text x="82" y="112" fill="var(--muted)" font-size="7">mean of p99s</text>
  <rect x="200" y="24" width="40" height="76" fill="var(--s1)"/><text x="196" y="112" fill="var(--muted)" font-size="7">merged p99</text>
  <line x1="60" y1="98" x2="290" y2="98" stroke="var(--ink)" stroke-dasharray="3 2"/>
  <text x="250" y="94" fill="var(--muted)" font-size="7">median=10</text>
</svg>
^ Averaging the per-host p99s reports 340ms; the p99 of the pooled 300 requests is 1000ms, nearly 3× higher, while the fleet median sits at 10ms — the tail is both under-reported by averaging and invisible to the median.

## Definition of done

The self-test pins the structural facts and the two failure modes: averaging understates, the merge recovers the truth, and the median hides it.

```python filename=modules/ship-and-operate/code/percentile-inter-01/percentile.py:113-123 COMPLETE
    host_p99s = [hist_percentile(h["hist"], 99) for h in hosts]
    host_p99s_are = host_p99s == [10, 10, 1000]
    print("  the per-host p99s are two fast and one slow = %s (%s)" % (host_p99s_are, host_p99s))

    avg = mean_of_host_percentiles(hosts, 99)
    true = fleet_percentile(hosts, 99)
    avg_understates = avg < true
    print("  the mean of per-host p99s is below the true fleet p99 = %s (%.1f < %d)" % (avg_understates, avg, true))

    merged_recovers_true = fleet_percentile(hosts, 99) == 1000
    print("  the merged histogram gives the true fleet p99 = %s (%d ms)" % (merged_recovers_true, true))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — averaging per-host p99s understates the true fleet p99, which the merged histogram recovers; median hides it
------------------------------------------------------------------------------------------------------------------------
  the per-host p99s are two fast and one slow = True ([10, 10, 1000])
  the mean of per-host p99s is below the true fleet p99 = True (340.0 < 1000)
  the merged histogram gives the true fleet p99 = True (1000 ms)
  averaging under-reports the tail by more than 2x = True (2.9x)
  the fleet median hides the tail the p99 exposes = True (p50=10, p99=1000)
```

**Done means the two aggregations are shown to disagree on real numbers: the mean of the per-host p99s is 340ms, the p99 of the merged 300 requests is 1000ms (2.9× higher), and the fleet median is 10ms — proving that percentiles must be computed from the pooled distribution, and that a median-only view would miss the tail entirely.**

## Boss fight

Predict two ways this is worse than "just remember to merge," because the merge itself has to be built to be mergeable, and the direction of the error is not always down.

The first trap is that you often *cannot* merge after the fact, because the per-host p99 is all you kept. If each host computes and ships only its p99 every minute, the raw samples are gone and no correct fleet p99 can ever be reconstructed — averaging is not a mistake you can fix downstream, it is a loss of information upstream. That is why metrics systems export a *histogram* or a *mergeable sketch* per host, not a percentile: bucketed counts (Prometheus histograms) and sketches like t-digest and HDR histogram are designed so that summing or merging them across hosts, and then reading a percentile, is correct to a bounded error. The cost is that percentiles are approximate (bucket boundaries or sketch compression introduce error), but an approximate percentile of the true pooled distribution beats an exact percentile of the wrong quantity. The design rule: emit distributions, aggregate distributions, take percentiles last — and if a system only lets you emit pre-computed percentiles, its cross-host "p99" is decorative.

The second trap is assuming averaging always understates, so a high averaged number is at least safe. It is not — the fleet p99 can also be *higher* than every single host's p99, which no average could ever produce. Imagine many hosts that each keep their slow requests just under their own 99% rank: each host's p99 looks fine, but pooled, all those individually-sub-threshold slow requests stack up past the fleet's 99% rank, so the fleet p99 exceeds the maximum per-host p99. Averaging cannot report a value above the max of its inputs, so in that regime it is not merely low, it is structurally incapable of reaching the right answer. And the same non-linearity defeats the tempting patches: a traffic-weighted average of per-host p99s is still not the pooled percentile, and taking the max of per-host p99s is a conservative bound only sometimes, not a correct fleet p99. There is exactly one general method — pool the distributions and rank — and every shortcut that stays in percentile-space is wrong in a direction that depends on the data.

**Percentiles do not average, so a correct fleet p99 requires keeping mergeable per-host distributions (histograms or sketches like t-digest / HDR) and ranking the pooled result — pre-computed per-host percentiles cannot be combined at all, and no percentile-space shortcut (mean, traffic-weighted mean, or max) is a general substitute, because the pooled p99 can even exceed every host's p99.**

## External resources

Documentation for any histogram-based metrics system — Prometheus histograms, HDR Histogram, or t-digest — on why per-host histograms/sketches are exported and merged and percentiles are read last, and what error the bucketing or compression introduces.

Gil Tene's talks on latency measurement ("How NOT to Measure Latency") — the companion point to this module: percentiles are easy to compute wrong, both by averaging across hosts and by the coordinated-omission effect that hides the tail during stalls.

The companion coordinated-omission module in this topic — another way a tail percentile is silently under-reported, there by the measurement loop stalling rather than by aggregating percentiles, so together they cover the two most common ways a p99 lies.
