---
id: data-inter-20
title: Average rates with the harmonic mean — or the arithmetic mean overstates the true average speed
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 19 min
summary: "Average speed" tempts the arithmetic mean — drive 60 mph then 20 mph and average (60+20)/2 = 40. That is wrong, because speed is a rate (distance per time) and the true average is total distance over total time, not the average of the numbers. You spend far more time on the slow segment than the fast one — the same distance at 20 mph takes three times as long as at 60 — so the slow speed dominates the trip and the honest average is pulled toward it. When the segments cover equal distances, the correct average of the speeds is the harmonic mean, n / Σ(1/speed), which equals total-distance-over-total-time exactly and is always ≤ the arithmetic mean. On two equal 60-mile legs at 60 and 20 mph, the arithmetic mean says 40 mph; the true average — 120 miles in 4 hours — is 30 mph, exactly the harmonic mean.
eli5: If you crawl to the store and sprint home, you didn't travel at your "average" of crawl-speed and sprint-speed, because you spent way longer crawling. Most of your trip was slow, so your real average is much closer to the crawl. Adding the two speeds and halving them ignores that you spent more time slow — you have to divide the whole distance by the whole time instead.
---

## Why this module

Averaging speeds by adding them and dividing looks obviously right and is obviously wrong, because it ignores that you spend unequal amounts of time at each speed.

Speed is a rate — distance divided by time — and the average speed of a trip has a definition that is not up for negotiation: total distance over total time. When you drive equal distances at different speeds, you spend more time on the slower legs, because covering the same miles takes longer when you go slower. So the slow speed occupies more of the trip and should count for more, not the same. The arithmetic mean gives every speed equal weight, which silently assumes you spent equal time at each — the opposite of what equal-distance legs actually do. The result is a number that overstates how fast you really went and corresponds to no real trip.

**Speed is a rate, so its true average is total distance over total time; the arithmetic mean of the speeds weights them equally, which is wrong whenever you spent unequal time at each.**

For equal-distance segments, the mean that gets it right is the harmonic mean — the reciprocal of the average of the reciprocals. It equals total-distance-over-total-time exactly and is always at or below the arithmetic mean. This module drives a two-leg trip, computes the true average, and shows which mean matches it.

## Concepts

The **true average speed** is total distance ÷ total time. Time on a leg is its distance ÷ its speed, so a slow leg contributes more time and pulls the average down.

The **arithmetic mean** of the speeds, (Σ speeds)/n, weights each speed equally. It equals the true average only when you spend equal *time* at each speed — not equal distance.

The **harmonic mean**, n ÷ Σ(1/speed), is the arithmetic mean of the reciprocals, inverted. For equal-distance legs it equals total-distance-over-total-time exactly, because each 1/speed is proportional to the time spent per unit distance, and averaging those is what the trip actually does.

The relationship is fixed: the harmonic mean is always ≤ the arithmetic mean, with equality only when all the values are identical. So swapping in the harmonic mean can only lower the estimate, never raise it — the arithmetic mean's error is always an overstatement for rates like speed.

The deeper rule is **the right mean depends on what is held constant**. Equal distances → harmonic mean of speeds. Equal times → arithmetic mean of speeds. Averaging a rate without asking "constant over what?" defaults to the arithmetic mean and often gets the wrong one.

**The harmonic mean is the correct average of equal-distance rates because it weights each rate by the time it consumes, which is exactly how the trip is composed.**

The arithmetic mean assumes each speed gets an equal slice of the trip; the reality is that the slow speed gets a bigger slice, and the harmonic mean is what accounts for it.

<svg role="img" aria-label="Arithmetic assumes equal halves of the trip per speed; the true trip gives the slow speed three-quarters, pulling the average down" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="16" fill="var(--s1)" font-size="8">arithmetic assumes</text>
  <rect x="20" y="22" width="130" height="14" fill="var(--s2)"/><text x="60" y="33" fill="var(--panel)" font-size="7">60 mph</text>
  <rect x="150" y="22" width="130" height="14" fill="var(--s1)"/><text x="195" y="33" fill="var(--panel)" font-size="7">20 mph</text>
  <text x="255" y="20" fill="var(--muted)" font-size="6">equal</text>
  <text x="10" y="60" fill="var(--s2)" font-size="8">the trip actually is</text>
  <rect x="20" y="66" width="65" height="14" fill="var(--s2)"/><text x="35" y="77" fill="var(--panel)" font-size="7">60</text>
  <rect x="85" y="66" width="195" height="14" fill="var(--s1)"/><text x="160" y="77" fill="var(--panel)" font-size="7">20 mph (3/4 of the time)</text>
  <text x="20" y="95" fill="var(--muted)" font-size="8">weighting the slow speed by its real time share gives the harmonic mean</text>
</svg>
^ Equal weighting (top) is the arithmetic mean's hidden assumption; the trip's real time split (bottom) weights the slow leg far more, which is exactly what the harmonic mean does.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/data-inter-20/harmonic.py

The fixture is two equal 60-mile legs at 60 and 20 mph.

```json filename=modules/ai-for-science-and-data/code/data-inter-20/trip.json:1-5 COMPLETE
{
  "_meta": "A trip in segments, each with a distance (miles) and the speed driven on it (mph). The true average speed is total distance divided by total time -- not the average of the segment speeds. When the segments are EQUAL distance, the correct average of the speeds is the harmonic mean, which the arithmetic mean overstates. The question: which mean equals the real total-distance-over-total-time speed?",
  "distances": [60, 60],
  "speeds": [60, 20]
}
```

The true average divides total distance by total time; the two candidate means are one line each.

```python filename=modules/ai-for-science-and-data/code/data-inter-20/harmonic.py:40-52 COMPLETE
def arithmetic_mean(xs):
    return sum(xs) / len(xs)


def harmonic_mean(xs):
    """n divided by the sum of reciprocals -- the correct average of equal-distance rates."""
    return len(xs) / sum(1.0 / x for x in xs)


def true_average_speed(distances, speeds):
    """Total distance over total time -- the definition of average speed."""
    total_time = sum(d / s for d, s in zip(distances, speeds))
    return sum(distances) / total_time
```

Run `--trip` and watch the time pile up on the slow leg.

```text filename=--trip
TRIP — 2 segments, distances [60, 60] mi, speeds [60, 20] mph
--------------------------------------------------------------
  leg 1: 60 mi at 60 mph -> 1.00 h
  leg 2: 60 mi at 20 mph -> 3.00 h
  total: 120 mi in 4.00 h
--------------------------------------------------------------
  arithmetic mean 40.0 mph vs true average 30.0 mph
```

The fast leg takes 1 hour; the slow leg takes 3. So three-quarters of the trip's time is spent at 20 mph, and the true average — 120 miles in 4 hours — is 30 mph, dragged down toward the slow speed. The arithmetic mean's 40 mph implicitly treated the two legs as equal-time, but they are 1 hour and 3 hours; it is 10 mph too fast.

<svg role="img" aria-label="Leg 1 is 1 hour at 60 mph, leg 2 is 3 hours at 20 mph; the trip is mostly the slow leg, so the true average 30 is near 20 not 40" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="16" fill="var(--muted)" font-size="8">time spent (4 hours total)</text>
  <rect x="20" y="22" width="65" height="18" fill="var(--s2)"/><text x="30" y="35" fill="var(--panel)" font-size="7">1h @60</text>
  <rect x="85" y="22" width="195" height="18" fill="var(--s1)"/><text x="150" y="35" fill="var(--panel)" font-size="7">3h @20 (most of the trip)</text>
  <line x1="20" y1="60" x2="280" y2="60" stroke="var(--grid)" stroke-width="1"/>
  <line x1="150" y1="54" x2="150" y2="72" stroke="var(--s1)" stroke-width="2"/><text x="130" y="86" fill="var(--s1)" font-size="7">true 30</text>
  <line x1="215" y1="54" x2="215" y2="72" stroke="var(--muted)" stroke-width="1.5" stroke-dasharray="2 2"/><text x="200" y="98" fill="var(--muted)" font-size="7">arithmetic 40</text>
  <text x="20" y="98" fill="var(--muted)" font-size="7">20</text><text x="270" y="98" fill="var(--muted)" font-size="7">60</text>
</svg>
^ The slow leg fills three of the four hours, so the true average sits near the slow speed at 30 — well below the arithmetic mean's 40, which pretends the legs took equal time.

## Build

The means view prints both candidate averages with their formulas beside the true speed.

```python filename=modules/ai-for-science-and-data/code/data-inter-20/harmonic.py:69-77 COMPLETE
def means_view(data):
    d, s = data["distances"], data["speeds"]
    print("MEANS — arithmetic vs harmonic mean of the speeds")
    print("-" * 62)
    print("  arithmetic: (%s)/%d = %.1f mph" % ("+".join(str(x) for x in s), len(s), arithmetic_mean(s)))
    print("  harmonic:   %d/(%s) = %.1f mph" % (len(s), "+".join("1/%d" % x for x in s), harmonic_mean(s)))
    print("  true speed: %d mi / %.2f h = %.1f mph" % (sum(d), sum(dd / ss for dd, ss in zip(d, s)), true_average_speed(d, s)))
    print("-" * 62)
    print("  the harmonic mean matches the true speed; the arithmetic mean sits above both.")
```

Line the means up with `--means`.

```text filename=--means
MEANS — arithmetic vs harmonic mean of the speeds
--------------------------------------------------------------
  arithmetic: (60+20)/2 = 40.0 mph
  harmonic:   2/(1/60+1/20) = 30.0 mph
  true speed: 120 mi / 4.00 h = 30.0 mph
--------------------------------------------------------------
  the harmonic mean matches the true speed; the arithmetic mean sits above both.
```

The harmonic mean — 2 divided by (1/60 + 1/20) — is 30.0, matching the true 30.0 to the decimal. The arithmetic mean is 40.0, sitting above both. This is not a coincidence of these numbers: for equal-distance legs the harmonic mean is *always* the true average, and it is *always* ≤ the arithmetic mean. The arithmetic mean's error for a rate is a guaranteed overstatement, never an undershoot.

<svg role="img" aria-label="Number line: harmonic mean 30 equals the true speed, arithmetic mean 40 sits above it" viewBox="0 0 300 90" width="300" height="90">
  <line x1="30" y1="50" x2="285" y2="50" stroke="var(--grid)" stroke-width="1"/>
  <text x="20" y="66" fill="var(--muted)" font-size="8">20</text>
  <text x="270" y="66" fill="var(--muted)" font-size="8">60</text>
  <circle cx="130" cy="50" r="5" fill="var(--s2)"/><text x="100" y="40" fill="var(--s2)" font-size="8">harmonic = true 30</text>
  <circle cx="195" cy="50" r="4" fill="var(--s1)"/><text x="178" y="40" fill="var(--s1)" font-size="8">arithmetic 40</text>
  <text x="40" y="82" fill="var(--muted)" font-size="8">harmonic ≤ arithmetic always; here it sits right on the true speed</text>
</svg>
^ On the speed line the harmonic mean lands exactly on the true average while the arithmetic mean floats above it — the fixed ordering harmonic ≤ arithmetic made visible.

## Definition of done

The self-test pins the identity and the inequality: the legs are equal distance, the harmonic mean equals total-distance-over-total-time, the arithmetic mean overstates, harmonic is never larger, and more time is spent on the slow leg.

```python filename=modules/ai-for-science-and-data/code/data-inter-20/harmonic.py:86-98 COMPLETE
    equal_distances = len(set(d)) == 1
    print("  the segments are equal distance (so harmonic applies) = %s (%s)" % (equal_distances, d))

    harmonic_equals_true = abs(hm - true) < 1e-9
    print("  the harmonic mean equals total-distance-over-total-time = %s (%.1f = %.1f)" % (harmonic_equals_true, hm, true))

    arithmetic_overstates = am > true
    print("  the arithmetic mean is above the true average = %s (%.1f > %.1f)" % (arithmetic_overstates, am, true))

    harmonic_le_arithmetic = hm <= am
    print("  the harmonic mean is never larger than the arithmetic = %s (%.1f <= %.1f)" % (harmonic_le_arithmetic, hm, am))

    slow_leg_dominates_time = (d[1] / s[1]) > (d[0] / s[0]) if s[1] < s[0] else (d[0] / s[0]) > (d[1] / s[1])
    print("  more time is spent on the slower leg = %s" % slow_leg_dominates_time)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the arithmetic mean overstates; the harmonic mean equals total distance over total time
----------------------------------------------------------------------------------------------------
  the segments are equal distance (so harmonic applies) = True ([60, 60])
  the harmonic mean equals total-distance-over-total-time = True (30.0 = 30.0)
  the arithmetic mean is above the true average = True (40.0 > 30.0)
  the harmonic mean is never larger than the arithmetic = True (30.0 <= 40.0)
  more time is spent on the slower leg = True
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  equal_distances=True  harmonic_equals_true=True  arithmetic_overstates=True  harmonic_le_arithmetic=True  slow_leg_dominates_time=True
```

**Done means the correct mean is identified by matching the definition: the harmonic mean equals the true 30 mph (120 mi / 4 h) while the arithmetic mean's 40 corresponds to no real trip.**

## Boss fight

The harmonic mean was right here. Predict whether it is always the right mean for averaging speeds. It is tempting to adopt "use harmonic for speeds" as the rule.

It is right only when the *distances* are equal; change what is held constant and the correct mean changes. If instead you drive for equal *times* — one hour at 60, one hour at 20 — the true average is total distance (60 + 20 = 80 miles) over total time (2 hours) = 40 mph, which is the *arithmetic* mean of the speeds. So the same two speeds average to 30 or 40 depending on whether the equal thing is distance or time. The rule is not "speeds use harmonic"; it is "average the rate over whatever is held constant, and that dictates the mean" — harmonic when the denominator's quantity (distance) is fixed, arithmetic when the numerator's (time) is.

The mirror-image mistake is reaching for the harmonic mean for quantities that are not rates. The harmonic mean is for things like speed, price-per-unit, and throughput — ratios where you average over the shared denominator. For plain additive quantities (heights, temperatures, counts) the arithmetic mean is correct, and for multiplicative growth factors the *geometric* mean is correct. Three means for three situations; matching them to the quantity is the skill.

```python filename=modules/ai-for-science-and-data/code/data-inter-20/harmonic.py:44-46 COMPLETE
def harmonic_mean(xs):
    """n divided by the sum of reciprocals -- the correct average of equal-distance rates."""
    return len(xs) / sum(1.0 / x for x in xs)
```

**Average a rate over whatever is held constant: harmonic mean for equal-distance speeds (and per-unit prices, throughputs), arithmetic for equal-time, geometric for growth factors — the quantity picks the mean, not habit.**

## External resources

The Pythagorean means (arithmetic, geometric, harmonic) and the AM ≥ GM ≥ HM inequality — any algebra or statistics reference; the harmonic mean and its ordering below the arithmetic are the core result here.

The classic "average speed" problem in physics texts — total distance over total time as the definition, and why averaging the speeds needs the harmonic mean for equal distances.

The companion geometric-mean module — growth factors use the geometric mean; together the two modules cover when the arithmetic mean is the wrong average and which mean replaces it.
