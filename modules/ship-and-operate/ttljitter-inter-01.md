---
id: ttljitter-inter-01
title: Jitter each cache entry's TTL — entries populated together with one fixed TTL all expire at the same instant and flood the origin
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: A cache entry lives for its time-to-live and then expires, and the next request for it misses and refetches from the origin. In steady state those refetches trickle in, spread across time because entries were created at different moments, and the origin handles them comfortably. The danger is when many entries are created at the same moment — a cache warmed at deploy, a traffic spike that populates the cache in one burst, a batch load. If they all share the same fixed TTL they were born together and they die together: at the instant that shared TTL elapses every one of them expires simultaneously, the next requests all miss at once, and the origin receives the entire set of refetches in a single bucket — a synchronized expiry stampede whose peak is the number of entries, hitting a backend sized for the gentle steady-state trickle. It is a self-inflicted thundering herd on a fixed schedule, and it recurs every TTL because the refetched entries are written back together with the same TTL again. The fix is to stop giving entries identical lifetimes: add a small random jitter to each entry's TTL — base plus a random offset within a window — so entries created together expire scattered across that window instead of at one instant. On a fixture of 12 entries populated at once, a fixed TTL puts all 12 refetches in one bucket (peak 12) while jittering over a 4-bucket window spreads them to 3 per bucket (peak 3), flattening the peak to about the entry count divided by the window.
eli5: Imagine you hand out a big batch of library cards on the same day, and every card is set to expire exactly one year later. That works fine until the year is up — and then everyone shows up to renew on the very same morning, and the one clerk at the desk is buried under the whole crowd at once. Nothing was wrong with any single card; the problem is that they all expire together, so the crowd arrives together. The fix is to not stamp them all with the identical date: give each card a slightly different expiry, scattered across a few weeks, so people trickle back to renew a few at a time and the clerk is never swamped. Caches have the same problem. When a pile of entries are created together and all given the same lifetime, they all expire at the same instant and the whole crowd of refetches hits the origin at once. Sprinkling a little randomness on each entry's lifetime spreads the crowd out.
---

## Why this module

A cache entry has a lifetime. It is written with a time-to-live, it serves reads until that TTL elapses, and then it expires — the next request for it misses, refetches from the origin, and writes a fresh copy. In ordinary running this is invisible: entries were created at all sorts of different moments, so their expirations are scattered across time, and the refetches they trigger reach the origin as a thin steady trickle it was sized to absorb.

The trouble starts when a large set of entries is born at the same moment. A cache warmed in one pass at deploy, a traffic spike that populates the cache in a single burst, a nightly batch load — all of them stamp a pile of entries with the same creation time. If every entry also gets the same fixed TTL, then they do not just share a birthday, they share a death date. The lifetime that felt like a per-entry setting is really a synchronized alarm clock for the whole cohort.

When that shared TTL elapses, every entry in the cohort expires in the same instant. The requests that would have been cheap cache hits all miss together, and the origin receives the entire cohort's worth of refetches at once — a spike whose height is the number of entries, landing on a backend provisioned for the trickle. Worse, it repeats: the refetches rewrite the entries together with the same TTL, so the cohort re-synchronizes and stampedes again one TTL later. This module runs a cohort of entries through a fixed TTL and a jittered TTL and counts the refetches per time bucket.

**A fixed TTL gives every entry in a cohort the same death date, so they expire together and flood the origin with a synchronized refetch wave; jittering each entry's TTL scatters the deaths across a window and flattens the peak.**

## Concepts

A cohort here is a set of entries created at the same moment. The word matters because the failure is not about any one entry — each entry's TTL is perfectly reasonable on its own — it is about correlation. Entries that were created together and given identical TTLs are correlated: their expirations are not independent events spread across time, they are one event that happens to many entries at once.

The peak we care about is the worst-case number of refetches landing in a single time bucket, because that is what the origin has to survive. A backend is sized for its peak load, not its average. Spreading the same total number of refetches over more buckets does not reduce the total work at all — it reduces the peak, and the peak is what fails.

Jitter is the cure, and it is the same cure used for correlated retries: break the synchronization by adding a small random offset to each entry's TTL. Instead of `base_ttl`, each entry lives for `base_ttl` plus a random amount within a window. Entries created at the same instant now have different death dates spread across that window, so their refetches land in different buckets. The peak drops from the whole cohort to roughly the cohort size divided by the window, and because each refetch re-jitters, the cohort stays desynchronized rather than re-clumping.

<svg role="img" aria-label="A timeline showing entries created at one instant; with a fixed TTL their expirations align on one later instant, with jitter their expirations spread across a window" viewBox="0 0 440 150">
<line x1="20" y1="40" x2="420" y2="40" stroke="var(--grid)"/>
<circle cx="60" cy="40" r="4" fill="var(--ink)"/>
<text x="60" y="26" fill="var(--muted)" font-size="9" text-anchor="middle">created</text>
<line x1="20" y1="90" x2="420" y2="90" stroke="var(--grid)"/>
<circle cx="300" cy="90" r="8" fill="var(--s1)"/>
<text x="300" y="115" fill="var(--ink)" font-size="10" text-anchor="middle">fixed: all expire here</text>
<line x1="20" y1="130" x2="420" y2="130" stroke="var(--grid)"/>
<circle cx="270" cy="130" r="4" fill="var(--s2)"/>
<circle cx="300" cy="130" r="4" fill="var(--s2)"/>
<circle cx="330" cy="130" r="4" fill="var(--s2)"/>
<circle cx="360" cy="130" r="4" fill="var(--s2)"/>
<text x="315" y="150" fill="var(--ink)" font-size="10" text-anchor="middle">jittered: spread across window</text>
</svg>
^ One creation instant leads to one shared expiry under a fixed TTL, but a spread of expiries under jitter.

**The disease is correlation — entries expiring together — and jitter is the standard cure: a random offset that turns one synchronized event back into a spread of independent ones.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/ttljitter-inter-01. The fixture is a cohort populated together, with a shared nominal TTL and a jitter window.

```json filename=modules/ship-and-operate/code/ttljitter-inter-01/ttljitter.json:3-5 COMPLETE
  "n_entries": 12,
  "base_ttl": 10,
  "jitter_window": 4
```

A fixed TTL gives every entry the identical lifetime, so every entry lands in the same expiry bucket.

```python filename=modules/ship-and-operate/code/ttljitter-inter-01/ttljitter.py:33-35 COMPLETE
def fixed_expiry(n, base):
    """Every entry gets the same TTL, so every entry expires in the same bucket."""
    return [base for _ in range(n)]
```

Jitter adds a deterministic offset within the window to each entry, so the cohort spreads across the window instead of piling into one instant.

```python filename=modules/ship-and-operate/code/ttljitter-inter-01/ttljitter.py:38-40 COMPLETE
def jittered_expiry(n, base, window):
    """Each entry gets base + a deterministic offset within the window, spreading expiries."""
    return [base + (i % window) for i in range(n)]
```

The peak is the most refetches landing in any single bucket — the height the origin has to survive.

```python filename=modules/ship-and-operate/code/ttljitter-inter-01/ttljitter.py:43-45 COMPLETE
def peak(expiries):
    """The most refetches landing in any single bucket."""
    return max(Counter(expiries).values())
```

Here is the per-bucket count. Before running it, predict: the fixed column should be a single tall bar and everything else zero, and the jittered column should be flat. Run `--expiry`:

```text filename=ttljitter.py --expiry
EXPIRY — refetches per time bucket (12 entries populated together)
--------------------------------------------------------
  bucket   fixed   jittered
  10       12      3
  11       0       3
  12       0       3
  13       0       3
--------------------------------------------------------
  fixed TTL piles every refetch into one bucket; jitter spreads them
```

The prediction holds exactly. The fixed TTL puts all 12 refetches in bucket 10 and nothing anywhere else — one spike. Jitter spreads the same 12 refetches evenly across buckets 10 through 13, three per bucket. The total work is identical — 12 refetches either way — but the shape is completely different.

<svg role="img" aria-label="Bar charts of refetches per bucket: fixed TTL is one bar of height 12 at bucket 10; jittered is four bars of height 3 across buckets 10 to 13" viewBox="0 0 440 200">
<line x1="30" y1="160" x2="200" y2="160" stroke="var(--line)"/>
<line x1="30" y1="40" x2="30" y2="160" stroke="var(--line)"/>
<rect x="45" y="40" width="24" height="120" fill="var(--s1)"/>
<text x="57" y="34" fill="var(--ink)" font-size="11" text-anchor="middle">12</text>
<text x="57" y="174" fill="var(--muted)" font-size="10" text-anchor="middle">10</text>
<text x="93" y="174" fill="var(--muted)" font-size="10" text-anchor="middle">11</text>
<text x="129" y="174" fill="var(--muted)" font-size="10" text-anchor="middle">12</text>
<text x="165" y="174" fill="var(--muted)" font-size="10" text-anchor="middle">13</text>
<text x="115" y="192" fill="var(--ink)" font-size="11" text-anchor="middle">fixed TTL</text>
<line x1="250" y1="160" x2="420" y2="160" stroke="var(--line)"/>
<line x1="250" y1="40" x2="250" y2="160" stroke="var(--line)"/>
<rect x="265" y="130" width="24" height="30" fill="var(--s2)"/>
<rect x="301" y="130" width="24" height="30" fill="var(--s2)"/>
<rect x="337" y="130" width="24" height="30" fill="var(--s2)"/>
<rect x="373" y="130" width="24" height="30" fill="var(--s2)"/>
<text x="277" y="124" fill="var(--ink)" font-size="11" text-anchor="middle">3</text>
<text x="277" y="174" fill="var(--muted)" font-size="10" text-anchor="middle">10</text>
<text x="313" y="174" fill="var(--muted)" font-size="10" text-anchor="middle">11</text>
<text x="349" y="174" fill="var(--muted)" font-size="10" text-anchor="middle">12</text>
<text x="385" y="174" fill="var(--muted)" font-size="10" text-anchor="middle">13</text>
<text x="335" y="192" fill="var(--ink)" font-size="11" text-anchor="middle">jittered TTL</text>
</svg>
^ Same total refetches, different shape: the fixed TTL is one bar of 12; jitter flattens it to four bars of 3.

Now the number the origin actually feels — the peak. Run `--peak`:

```text filename=ttljitter.py --peak
PEAK — worst-case refetches in a single bucket
--------------------------------------------------
  fixed TTL    peak = 12
  jittered TTL peak = 3  (window 4)
--------------------------------------------------
  jitter flattens the peak to about entries / window = 3
```

The fixed peak is 12 — the entire cohort. The jittered peak is 3, which is the cohort size (12) divided by the window (4). That is the whole payoff in one ratio: widen the window and the peak drops proportionally, at no cost in total work.

<svg role="img" aria-label="A cohort of entries created at one time; a fixed TTL routes all of them to one expiry instant while a jittered TTL routes them across a spread of instants" viewBox="0 0 440 170">
<rect x="20" y="70" width="70" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="55" y="89" fill="var(--ink)" font-size="10" text-anchor="middle">cohort of 12</text>
<line x1="90" y1="85" x2="170" y2="45" stroke="var(--s1)"/>
<line x1="90" y1="85" x2="170" y2="85" stroke="var(--s1)"/>
<line x1="90" y1="85" x2="170" y2="125" stroke="var(--s1)"/>
<rect x="170" y="70" width="60" height="30" fill="var(--s1)"/>
<text x="200" y="89" fill="var(--ink)" font-size="10" text-anchor="middle">peak 12</text>
<text x="200" y="118" fill="var(--muted)" font-size="9" text-anchor="middle">one instant</text>
<line x1="250" y1="85" x2="330" y2="45" stroke="var(--s2)"/>
<line x1="250" y1="85" x2="330" y2="72" stroke="var(--s2)"/>
<line x1="250" y1="85" x2="330" y2="98" stroke="var(--s2)"/>
<line x1="250" y1="85" x2="330" y2="125" stroke="var(--s2)"/>
<rect x="330" y="38" width="40" height="14" fill="var(--s2)"/>
<rect x="330" y="64" width="40" height="14" fill="var(--s2)"/>
<rect x="330" y="90" width="40" height="14" fill="var(--s2)"/>
<rect x="330" y="116" width="40" height="14" fill="var(--s2)"/>
<text x="395" y="89" fill="var(--ink)" font-size="10" text-anchor="middle">peak 3</text>
</svg>
^ The same cohort routed two ways: a fixed TTL funnels all 12 into one instant (peak 12); jitter fans them across the window (peak 3).

## Build

The self-test plants the failure and names each claim as a boolean flag. It builds the fixed and jittered expiry lists, computes both peaks, and checks that the fixed TTL synchronizes into one bucket at the full cohort height while jitter spreads across the window and lowers the peak to the expected ratio.

```python filename=modules/ship-and-operate/code/ttljitter-inter-01/ttljitter.py:84-97 COMPLETE
    fixed_synchronized = len(set(fx)) == 1
    print("  fixed TTL: all entries expire in one bucket = %s (%d)" % (fixed_synchronized, fx[0]))

    fixed_peak_is_n = fp == n
    print("  fixed TTL: the peak equals the whole entry count = %s (%d)" % (fixed_peak_is_n, fp))

    jittered_spreads = len(set(jt)) == window
    print("  jittered TTL: expiries spread across the window = %s (%d buckets)" % (jittered_spreads, len(set(jt))))

    jitter_lowers_peak = jp < fp
    print("  jittered TTL: the peak is lower than fixed = %s (%d < %d)" % (jitter_lowers_peak, jp, fp))

    peak_matches_expectation = jp == -(-n // window)
    print("  jittered peak is about entries / window = %s (%d)" % (peak_matches_expectation, jp))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly the moment jitter stops flattening the peak:

```text filename=ttljitter.py --check
SELF-TEST — a fixed TTL synchronizes expiry into one bucket; jitter spreads it and flattens the peak
----------------------------------------------------------------------------------------------------------------
  fixed TTL: all entries expire in one bucket = True (10)
  fixed TTL: the peak equals the whole entry count = True (12)
  jittered TTL: expiries spread across the window = True (4 buckets)
  jittered TTL: the peak is lower than fixed = True (3 < 12)
  jittered peak is about entries / window = True (3)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  fixed_synchronized=True  fixed_peak_is_n=True  jittered_spreads=True  jitter_lowers_peak=True  peak_matches_expectation=True
```

**The self-test asserts the ratio, not just the direction: jitter must drop the peak to the cohort size over the window, so a jitter window that has quietly collapsed to one bucket fails the test instead of passing silently.**

## Definition of done

You can point at the cohort — the set of entries created together — and explain why it, not any single entry, is the unit of the problem.
You can state the peak, not the total, as the number the origin must survive, and explain why spreading refetches over more buckets helps even though it does not reduce total work.
You can compute the jittered peak as roughly cohort size divided by window, and predict how widening the window changes it.
You can explain why the stampede recurs without jitter — refetches rewrite the cohort with the same TTL — and why re-jittering on each write keeps it broken up.
You can name jitter as the same cure used for correlated retry backoff, and say what disease both are treating.

## Boss fight

Change `jitter_window` to `1` in the fixture and rerun `--check`. A window of one collapses jitter back to a fixed TTL, so the cohort re-synchronizes into a single bucket. Watch which flags flip and how the self-test reports the regression.

The `jittered_spreads` flag was `len(set(jt)) == window`. With `window` now 1, the jittered list is all `base + 0` — a single bucket — so `len(set(jt))` is 1, which still equals `window`, and that flag stays true. But `jitter_lowers_peak` was `jp < fp`, and now the jittered peak equals the fixed peak of 12, so `3 < 12` becomes `12 < 12`, false. The self-test fails and exits non-zero.

That is the point of asserting the peak ratio rather than trusting the window setting alone: a jitter window that has been misconfigured, or set to zero by a bad default, produces no spreading at all, and only a test that checks the actual peak catches it. A test that merely confirmed "jitter is enabled" would pass while the origin still stampedes.

**A window of one is not jitter — the flag that survives (spread equals window) is the wrong thing to trust; the flag that catches it (peak actually dropped) is the one worth asserting.**

## External resources

The AWS Architecture Blog's "Exponential Backoff And Jitter" makes the general case that jitter, not just backoff, is what breaks correlation between clients — the same principle applied here to TTLs rather than retries.
Redis's documentation on key expiration and cache stampede protection describes TTL jitter and the related single-flight / request-coalescing techniques for the same class of problem.
The "thundering herd" entry on Wikipedia frames the general pattern of many waiters released at once overwhelming a resource, of which synchronized cache expiry is one instance.
