---
id: breakdown-inter-01
title: Summarize possibly-contaminated data with the median, not the mean — one bad value drags the mean without bound, but the median needs a majority corrupted to break
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: The breakdown point of an estimator is the fraction of the data you must corrupt to send the estimate arbitrarily far from the truth — a measure of how much bad data the summary can survive. For the mean it is zero: the mean is a sum divided by n, so one term pushed large enough dominates the sum and the mean follows it without bound. A single data-entry typo, a pegged sensor, a field parsed wrong — one bad point — and the mean is wherever that point drags it. The median is built differently: it is the middle value in sorted order, so a corrupted point does not enter an arithmetic total, it only changes which value sits in the middle. Push one point to a billion and the median moves by at most one position; to move it outside the range of the clean data you must corrupt more than half the points, so its breakdown point is one half, the highest possible. This is distinct from the skewed-data question (a companion module): there the tail is real and the mean is the right estimator for a total; here the outlier is an error and the mean is simply wrong, reporting a number no clean point is near. Because almost every real dataset contains at least one error, the practical rule is to reach for a robust summary — the median or a trimmed mean — whenever the data is not verified clean. On a fixture of five clean values around 12, one injected outlier drives the mean to 27, then 177, then 1677 as it grows, while the median stays at 12.5 regardless; corrupting the points one at a time, the mean leaves the clean range at the first, the median only at the third of five.
eli5: Imagine five friends whose ages are all around twelve, and you want one number that describes the group. Add the ages and divide (the average), and now let one age be typed wrong as a thousand: the average leaps to nearly two hundred, a number describing nobody, and the bigger the typo the further it leaps — the average has no defense against a single bad entry. Instead, line the ages up in order and take the middle one: one wrong age just sits at the far end of the line and the middle barely shifts, no matter how huge the typo is. To actually move the middle you would have to mess up more than half the ages. So when your data might have a mistake in it, the middle value is the trustworthy summary and the average is the fragile one.
---

## Why this module

You have a column of numbers and you want one number that stands for them, so you take the average. It is the reflex, and on clean, well-behaved data it is fine. The question this module asks is what happens when the data is not clean — when one of the numbers is wrong, not because the world is skewed but because something upstream made an error.

Real data is full of such errors: a temperature logged as 999 when the sensor failed, a price entered with the decimal point slipped, a duration that recorded a timeout as a huge number, a unit mismatch that multiplied one row by a thousand. These are not signal; they are defects, and they are common enough that you should assume any un-vetted dataset has at least one.

The average has no resistance to them. Because it sums every value and divides, a single value large enough dominates the sum, and the average slides toward it without limit — the worse the error, the worse the average. So the one summary everyone reaches for first is precisely the one that a lone bad point can render meaningless, and it does so quietly: the average is still a real number, still computed correctly, just describing nothing in your actual data.

**The mean is a sum divided by n, so a single erroneous value large enough dominates the sum and drags the mean arbitrarily far — its resistance to even one bad point is zero, which is exactly the situation any un-vetted real dataset presents.**

## Concepts

The formal name for this resistance is the breakdown point: the smallest fraction of the data you must corrupt to push the estimate arbitrarily far from the truth. It turns "how robust is this summary" into a number. The mean's breakdown point is zero — corrupt one point out of any number, make it big enough, and the mean goes wherever you like. One bad value in a million still pulls the mean, just less per point.

The median could not be more different. It is the middle value once the data is sorted, so a corrupted value does not get summed into anything — it just takes a place in the ordering, and the middle position barely notices. Replace one value with a billion and the median moves at most one slot over. To drag the median outside the range of the clean data, you have to supply more corrupted values than clean ones, so its breakdown point is one half — the highest any estimator can have, because past half the corrupted points are the majority and there is no honest signal left to recover.

<svg role="img" aria-label="A number line with five clean data points clustered near 12 and one outlier far to the right. The median marker stays at the cluster near 12; the mean marker is pulled far to the right toward the outlier, away from every clean point." viewBox="0 0 440 120">
<line x1="30" y1="70" x2="410" y2="70" stroke="var(--line)"/>
<circle cx="60" cy="70" r="3" fill="var(--ink)"/><circle cx="72" cy="70" r="3" fill="var(--ink)"/><circle cx="84" cy="70" r="3" fill="var(--ink)"/><circle cx="96" cy="70" r="3" fill="var(--ink)"/><circle cx="108" cy="70" r="3" fill="var(--ink)"/>
<text x="84" y="90" fill="var(--muted)" font-size="8" text-anchor="middle">clean data (~12)</text>
<circle cx="390" cy="70" r="4" fill="var(--s2)"/>
<text x="390" y="90" fill="var(--s2)" font-size="8" text-anchor="middle">outlier</text>
<line x1="84" y1="55" x2="84" y2="45" stroke="var(--s1)"/>
<text x="84" y="40" fill="var(--s1)" font-size="8" text-anchor="middle">median</text>
<line x1="250" y1="55" x2="250" y2="45" stroke="var(--s2)"/>
<text x="250" y="40" fill="var(--s2)" font-size="8" text-anchor="middle">mean (dragged out)</text>
</svg>
^ One outlier pulls the mean far from every clean point while the median stays in the cluster — the mean chases the bad value, the median ignores it.

There is a second, sharper distinction hiding in this: how the two respond to the size of the bad value. The mean is sensitive to magnitude — double the outlier and the mean moves further — so the damage is unbounded in the value, not just in the count. The median is completely insensitive to magnitude — a corrupted point at 100 and the same point at a billion put the median in the identical place, because both are just "the largest value" in the sort. The median cares only how many bad points there are, never how bad they are.

<svg role="img" aria-label="Two horizontal bars showing breakdown points. The mean's bar is filled at the very left edge only, labeled breakdown 0 (one point). The median's bar is filled to the halfway mark, labeled breakdown one half (a majority)." viewBox="0 0 440 110">
<text x="20" y="18" fill="var(--muted)" font-size="9">fraction of data you must corrupt to break the estimate</text>
<text x="70" y="45" fill="var(--ink)" font-size="8" text-anchor="end">mean</text>
<rect x="80" y="35" width="330" height="16" fill="var(--panel)" stroke="var(--line)"/>
<rect x="80" y="35" width="6" height="16" fill="var(--s2)"/>
<text x="150" y="47" fill="var(--s2)" font-size="8">breakdown 0 — one bad point</text>
<text x="70" y="80" fill="var(--ink)" font-size="8" text-anchor="end">median</text>
<rect x="80" y="70" width="330" height="16" fill="var(--panel)" stroke="var(--line)"/>
<rect x="80" y="70" width="165" height="16" fill="var(--s1)"/>
<text x="255" y="82" fill="var(--s1)" font-size="8">breakdown 1/2 — a majority</text>
</svg>
^ The breakdown point: the mean tolerates zero corrupted points, the median tolerates just under half — the difference between a summary a single error destroys and one that survives anything short of a majority.

This is deliberately not the skewed-data question. When a distribution has a real long tail — request costs, incomes, file sizes — the large values are genuine, the mean is the correct estimator for a total (a sum is the mean times the count), and the median describes the typical case; both are right for their jobs. Here the extreme value is a mistake, so there is no job for which the mean is right. The judgment is whether the extreme is real signal or a defect, and when you cannot be sure, the robust estimator is the safe default.

**The mean's breakdown point is zero and it is sensitive to the outlier's magnitude; the median's is one half and it is insensitive to magnitude — so on data that may contain errors, the median (or a trimmed mean) is the trustworthy summary, distinct from the skewed-but-real case where the mean has a job.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/breakdown-inter-01. The fixture is five clean values and a set of outlier magnitudes to inject.

```json filename=modules/ai-for-science-and-data/code/breakdown-inter-01/breakdown.json:3-4 COMPLETE
  "clean": [10, 11, 12, 13, 14],
  "outlier_sizes": [100, 1000, 10000]
```

The mean sums and divides.

```python filename=modules/ai-for-science-and-data/code/breakdown-inter-01/breakdown.py:34-35 COMPLETE
def mean(xs):
    return sum(xs) / len(xs)
```

The median sorts and takes the middle — no value is summed, only ordered.

```python filename=modules/ai-for-science-and-data/code/breakdown-inter-01/breakdown.py:38-44 COMPLETE
def median(xs):
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    if n % 2:
        return float(s[mid])
    return (s[mid - 1] + s[mid]) / 2
```

To test the breakdown point, corrupt the first k values to a huge number.

```python filename=modules/ai-for-science-and-data/code/breakdown-inter-01/breakdown.py:47-49 COMPLETE
def corrupt(clean, k, big=BIG):
    """Replace the first k values with a huge contaminating value."""
    return [big] * k + list(clean[k:])
```

Before running it, predict: the clean data sits at 12, and one outlier that grows from 100 to 10000 should drag the mean further each time while the median stays put. Run `--outlier`:

```text filename=breakdown.py --outlier
OUTLIER — one contaminating point added to clean data [10, 11, 12, 13, 14]
--------------------------------------------------------
  data                       mean        median
  clean                      12.00       12.00
  + outlier 100              26.67       12.50
  + outlier 1000             176.67      12.50
  + outlier 10000            1676.67     12.50
--------------------------------------------------------
  the mean chases the outlier without bound; the median barely moves
```

The prediction holds. On clean data both summaries agree at 12. Add a single outlier and they diverge completely: the mean jumps to 26.67 at an outlier of 100, to 176.67 at 1000, to 1676.67 at 10000 — chasing the bad value without bound, further with every increase. The median reads 12.5 in all three cases, unchanged whether the outlier is 100 or ten thousand, because to the median the outlier is just "the biggest one" no matter how big. One bad point, and the mean is off by a hundredfold while the median is off by half a unit.

Now count how many bad points each can survive. Run `--breakdown`:

```text filename=breakdown.py --breakdown
BREAKDOWN — corrupt k of 5 points to a huge value
--------------------------------------------------------
  k    mean            median        median in clean range?
  0    12.00           12.00         True
  1    200000010.00    13.00         True
  2    400000007.80    14.00         True
  3    600000005.40    1000000000.00 False
  4    800000002.80    1000000000.00 False
  5    1000000000.00   1000000000.00 False
--------------------------------------------------------
  the mean leaves the range at k=1; the median only when k exceeds n/2
```

This is the breakdown point made concrete. At k=1 — one corrupted point of five — the mean is already 200 million, wildly outside the clean range of 10 to 14; a single bad point breaks it, exactly breakdown zero. The median holds inside the clean range through k=1 (13) and k=2 (14), and only at k=3 — three of five, a majority — does it jump to a billion and leave the range. The median survived a minority of corruption and broke only when the bad points outnumbered the good, exactly breakdown one half.

<svg role="img" aria-label="A line chart over corrupted-count k from 0 to 5. The mean line leaves the clean range immediately at k=1 and stays out. The median line stays in the clean range at k=0,1,2 and jumps out at k=3." viewBox="0 0 440 140">
<line x1="45" y1="115" x2="410" y2="115" stroke="var(--line)"/>
<line x1="45" y1="20" x2="45" y2="115" stroke="var(--line)"/>
<rect x="45" y="95" width="365" height="20" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="3 2"/>
<text x="395" y="108" fill="var(--muted)" font-size="7">clean range</text>
<text x="30" y="112" fill="var(--muted)" font-size="8">in</text>
<text x="30" y="30" fill="var(--muted)" font-size="8">out</text>
<path d="M60 105 L 115 30 L 175 30 L 235 30 L 295 30 L 355 30" fill="none" stroke="var(--s2)"/>
<text x="250" y="25" fill="var(--s2)" font-size="8">mean: out at k=1</text>
<path d="M60 105 L 115 103 L 175 100 L 235 30 L 295 30 L 355 30" fill="none" stroke="var(--s1)"/>
<text x="120" y="95" fill="var(--s1)" font-size="8">median: out at k=3</text>
<text x="60" y="127" fill="var(--muted)" font-size="7" text-anchor="middle">k=0</text>
<text x="235" y="127" fill="var(--muted)" font-size="7" text-anchor="middle">k=3</text>
<text x="355" y="127" fill="var(--muted)" font-size="7" text-anchor="middle">k=5</text>
</svg>
^ As corrupted points accumulate, the mean leaves the clean range at the very first one; the median holds until a majority is corrupted — the breakdown points, zero and one half, drawn.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that one outlier pushes the mean out of the clean range, that the median stays in it, that the mean grows without bound as the outlier grows, that the median is unchanged by the outlier's size, and that the median survives a minority of corruption but breaks at a majority.

```python filename=modules/ai-for-science-and-data/code/breakdown-inter-01/breakdown.py:91-108 COMPLETE
    outlier_wrecks_mean = not in_range(mean(with_one), clean)
    print("  one outlier pushes the mean out of the clean range = %s (mean %.2f, range [%d, %d])"
          % (outlier_wrecks_mean, mean(with_one), min(clean), max(clean)))

    outlier_spares_median = in_range(median(with_one), clean)
    print("  the median stays in the clean range with that outlier = %s (median %.2f)" % (outlier_spares_median, median(with_one)))

    means = [mean(clean + [o]) for o in data["outlier_sizes"]]
    mean_tracks_outlier_size = means[0] < means[1] < means[2]
    print("  the mean grows without bound as the outlier grows = %s (%s)" % (mean_tracks_outlier_size, [round(m) for m in means]))

    medians = [median(clean + [o]) for o in data["outlier_sizes"]]
    median_invariant_to_outlier_size = medians[0] == medians[1] == medians[2]
    print("  the median is unchanged by the outlier's size = %s (%.2f)" % (median_invariant_to_outlier_size, medians[0]))

    minority = (n - 1) // 2                       # fewer than half
    majority = n // 2 + 1                         # more than half
    median_needs_majority = in_range(median(corrupt(clean, minority)), clean) and not in_range(median(corrupt(clean, majority)), clean)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if one outlier ever stopped wrecking the mean or the median ever broke on a minority:

```text filename=breakdown.py --check
SELF-TEST — one outlier wrecks the mean but not the median; the median survives a minority of corruption and breaks only at a majority
----------------------------------------------------------------------------------------------------------------
  one outlier pushes the mean out of the clean range = True (mean 176.67, range [10, 14])
  the median stays in the clean range with that outlier = True (median 12.50)
  the mean grows without bound as the outlier grows = True ([27, 177, 1677])
  the median is unchanged by the outlier's size = True (12.50)
  median survives 2 corrupted (minority) but breaks at 3 (majority) = True
```

**The self-test pins both dimensions of robustness: that the median ignores the outlier's magnitude (identical for 100 and 10000) and that it survives a minority but not a majority of corrupted points — so a pass certifies breakdown one half, not merely that the median moved less this once.**

## Definition of done

You can define the breakdown point and state it for the mean (zero) and the median (one half).
You can explain why summing makes the mean sensitive to a single point and to that point's magnitude.
You can explain why the median responds only to the count of bad points, never their size.
You can distinguish this contamination case from a genuinely skewed distribution, where the mean has a legitimate job.
You can state the practical rule — use the median or a trimmed mean on un-vetted data — and name a mean far from the median as a signal to hunt for a bad value.

## Boss fight

Suppose you switch to the median for robustness, but you also need a measure of spread, and you reach for the standard deviation. Reason about whether that is safe. It is not: the standard deviation is built from squared deviations from the mean, so it inherits the mean's breakdown point of zero and is even more sensitive to an outlier because the deviation is squared — one bad point inflates it enormously. The robust counterparts are the interquartile range (the spread of the middle half, breakdown 25%) and the median absolute deviation (the median of the absolute deviations from the median, breakdown 50%). The lesson generalizes past the center: every summary has a breakdown point, and switching to a robust center while keeping a fragile spread leaves you half-protected. Match the robustness of your spread estimator to your center.

Now the trap that makes robust estimators quietly the wrong choice. Robustness discards the influence of extreme points, which is exactly right when they are errors and exactly wrong when they are the signal. If you are monitoring for the rare catastrophic request, the fraud transaction, the equipment about to fail, the outlier is the whole point, and a median that ignores it will report "all normal" while the thing you care about happens in the tail. Robust statistics answer "what is a typical value, ignoring contamination"; they are silent about the tail by design. So the right move is not "always use the median" but a diagnosis: are extremes noise to be resisted or signal to be caught. The mean and standard deviation over-weight the tail, the median and IQR ignore it, and choosing between them is choosing what role the tail plays in your question — which is why serious analysis reports both and reconciles the gap rather than picking one blindly.

**The standard deviation shares the mean's zero breakdown (worse, it squares the outlier), so pair a robust center with a robust spread (IQR, median absolute deviation); and robustness ignores the tail by design, so it is the wrong tool when the outlier is the signal you are hunting rather than an error to resist.**

## External resources

Any robust-statistics reference (Huber; Rousseeuw and Leroy) defines the breakdown point and works through the mean, median, trimmed mean, IQR, and median absolute deviation.
Tukey's writing on exploratory data analysis introduced the practice of leading with resistant summaries (median, hinges, the five-number summary) precisely because real data is contaminated.
The topic's own module on the mean versus the median for skewed distributions covers the neighboring case — where the tail is real and the mean is the correct estimator for a total — which this contamination module is deliberately distinguished from.
