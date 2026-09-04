---
id: data-inter-18
title: Relabel one member across two groups — and both group means can rise, though no value changed
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 19 min
summary: Take two groups, a better-scoring one and a worse-scoring one. Move the weakest member of the better group — a value still above everything in the worse group — into the worse group. No number changed; you only moved a label. Yet the better group's mean rises (you removed its lowest member) and the worse group's mean also rises (you added a member above its old average). Both averages improve while the whole population is identical. This is the Will Rogers phenomenon, and it is how stage migration makes survival statistics improve when a better scanner reclassifies patients without curing anyone. On groups good = 8, 9, 10 (mean 9) and poor = 1, 2, 3 (mean 2), moving the 8 — below 9, above 2 — into poor gives good mean 9.5 and poor mean 3.5, both up, while the pooled mean stays 5.5.
eli5: If the shortest kid on the tall team is still taller than everyone on the short team, moving that kid to the short team makes the tall team's average height go up (its shortest left) AND the short team's average go up (someone taller joined). Nobody grew or shrank. Both teams look taller just because one kid switched shirts. Numbers can improve everywhere by relabeling and nowhere in reality.
---

## Why this module

Two subgroup averages can both improve at the same time without a single measurement changing — just by moving one member's label from one group to the other.

Picture a better-scoring group and a worse-scoring one. Reclassify the weakest member of the better group into the worse group — a member who is nonetheless still stronger than everyone already in the worse group. Removing it from the better group lifts that group's average, because you dropped its lowest value. Adding it to the worse group lifts that group's average too, because it is above that group's old mean. Both subgroup means go up. Nobody's value changed; you only moved a label. The improvement is entirely an accounting artifact.

**Two group means can both rise from a pure relabeling, because the moved value is below one group's mean and above the other's.**

This is the Will Rogers phenomenon, and it is not a curiosity — it is how "stage migration" makes cancer survival statistics improve when a more sensitive scanner reclassifies borderline patients, curing no one. This module reclassifies one value between two groups and shows both means rise while the pooled population is byte-for-byte unchanged.

## Concepts

Each group has a **mean** — its average value. Comparing group means is the natural way to ask "is this group doing better," and across a fixed grouping it is fine.

**Reclassification** moves a member from one group to another without changing its value. The trigger condition is precise: the moved value must lie **below the mean of the group it leaves** and **above the mean of the group it joins**. Any value in that gap lifts both means when moved from the higher group to the lower.

The mechanism is two one-sided facts. Removing a below-average member raises a group's mean — the remaining members average higher. Adding an above-average member raises a group's mean — the newcomer pulls it up. The moved value is below-average for the group it leaves and above-average for the group it joins, so it raises both.

The **pooled mean** — the average over the whole population, ignoring the grouping — cannot change, because the set of values is identical; you only relabeled. That invariant is the tell: if the subgroups all improved but the population did not, no real improvement happened.

**Subgroup means are not comparable across a reclassification, because relabeling alone can lift every subgroup while the population stands still.**

The move does two one-sided things at once: it strips the good group's weakest member and hands the poor group a member stronger than any it had.

<svg role="img" aria-label="The value 8 leaves the good group of 8,9,10 and joins the poor group of 1,2,3, becoming that group's largest member" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="20" fill="var(--s2)" font-size="8">good</text>
  <rect x="45" y="12" width="22" height="16" fill="none" stroke="var(--s1)" stroke-width="1" stroke-dasharray="2 2"/>
  <text x="50" y="24" fill="var(--s1)" font-size="9">8</text>
  <rect x="70" y="12" width="22" height="16" fill="var(--s2)"/><text x="75" y="24" fill="var(--panel)" font-size="9">9</text>
  <rect x="95" y="12" width="22" height="16" fill="var(--s2)"/><text x="98" y="24" fill="var(--panel)" font-size="9">10</text>
  <text x="130" y="24" fill="var(--muted)" font-size="8">its lowest leaves → mean up</text>
  <line x1="56" y1="30" x2="56" y2="72" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="10" y="90" fill="var(--s1)" font-size="8">poor</text>
  <rect x="45" y="82" width="22" height="16" fill="var(--s1)"/><text x="52" y="94" fill="var(--panel)" font-size="9">1</text>
  <rect x="70" y="82" width="22" height="16" fill="var(--s1)"/><text x="77" y="94" fill="var(--panel)" font-size="9">2</text>
  <rect x="95" y="82" width="22" height="16" fill="var(--s1)"/><text x="100" y="94" fill="var(--panel)" font-size="9">3</text>
  <rect x="120" y="82" width="22" height="16" fill="none" stroke="var(--s1)" stroke-width="1" stroke-dasharray="2 2"/><text x="125" y="94" fill="var(--s1)" font-size="9">8</text>
  <text x="150" y="94" fill="var(--muted)" font-size="8">its new highest joins → mean up</text>
</svg>
^ The single value 8 is the good group's minimum and, once moved, the poor group's maximum — so its departure lifts one mean and its arrival lifts the other.

The trap is reading improved subgroup averages as progress when the grouping itself moved between the two measurements. In medicine this is stage migration; in any dataset it is what happens when a reclassification, a new threshold, or a better instrument reshuffles who counts as what.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/data-inter-18/willrogers.py

The fixture is two groups and the value to move.

```json filename=modules/ai-for-science-and-data/code/data-inter-18/groups.json:1-6 COMPLETE
{
  "_meta": "Two groups of measurements: 'good' (the better-scoring group) and 'poor' (the worse-scoring group). A single member is reclassified -- moved from good to poor -- without its value changing at all (think: a better diagnostic tool restages one patient from the healthy group to the sick group). move_value is the value being moved. The question: what happens to each group's mean when the SAME numbers are just relabeled?",
  "good": [8, 9, 10],
  "poor": [1, 2, 3],
  "move_value": 8
}
```

Reclassify is a relabel: remove the value from one group, append it to the other, change nothing else.

```python filename=modules/ai-for-science-and-data/code/data-inter-18/willrogers.py:40-49 COMPLETE
def mean(xs):
    return sum(xs) / len(xs)


def reclassify(good, poor, v):
    """Move value v from good to poor without changing any number."""
    new_good = list(good)
    new_good.remove(v)
    new_poor = poor + [v]
    return new_good, new_poor
```

The means view reclassifies once and prints each group's before/after mean alongside the pooled mean.

```python filename=modules/ai-for-science-and-data/code/data-inter-18/willrogers.py:54-65 COMPLETE
def means_view(data):
    good, poor, v = data["good"], data["poor"], data["move_value"]
    ng, npr = reclassify(good, poor, v)
    pooled = good + poor
    print("MEANS — group means before and after moving %d from good to poor" % v)
    print("-" * 60)
    print("  good:   %s mean %.2f   ->   %s mean %.2f" % (good, mean(good), ng, mean(ng)))
    print("  poor:   %s mean %.2f   ->   %s mean %.2f" % (poor, mean(poor), npr, mean(npr)))
    print("  pooled: mean %.2f (%d values)   ->   mean %.2f (%d values)"
          % (mean(pooled), len(pooled), mean(ng + npr), len(ng + npr)))
    print("-" * 60)
    print("  both group means rise; the pooled mean does not move.")
```

Run `--means`.

```text filename=--means
MEANS — group means before and after moving 8 from good to poor
------------------------------------------------------------
  good:   [8, 9, 10] mean 9.00   ->   [9, 10] mean 9.50
  poor:   [1, 2, 3] mean 2.00   ->   [1, 2, 3, 8] mean 3.50
  pooled: mean 5.50 (6 values)   ->   mean 5.50 (6 values)
------------------------------------------------------------
  both group means rise; the pooled mean does not move.
```

The good group climbs from 9.00 to 9.50; the poor group climbs from 2.00 to 3.50. Both improved — and the pooled mean sits at 5.50 before and after, because the six values are the same six values. A report showing only the two subgroup means would announce improvement in both; the population tells the truth.

<svg role="img" aria-label="Both group means rise after moving the value 8 from good to poor, while the pooled mean stays at 5.5" viewBox="0 0 300 130" width="300" height="130">
  <line x1="30" y1="15" x2="30" y2="105" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="105" x2="285" y2="105" stroke="var(--grid)" stroke-width="1"/>
  <text x="5" y="55" fill="var(--muted)" font-size="8">9.5</text>
  <text x="5" y="97" fill="var(--muted)" font-size="8">2</text>
  <line x1="60" y1="60" x2="120" y2="55" stroke="var(--s2)" stroke-width="2"/>
  <circle cx="60" cy="60" r="3" fill="var(--s2)"/><circle cx="120" cy="55" r="3" fill="var(--s2)"/>
  <text x="122" y="52" fill="var(--s2)" font-size="8">good 9.0→9.5</text>
  <line x1="60" y1="97" x2="120" y2="82" stroke="var(--s1)" stroke-width="2"/>
  <circle cx="60" cy="97" r="3" fill="var(--s1)"/><circle cx="120" cy="82" r="3" fill="var(--s1)"/>
  <text x="122" y="88" fill="var(--s1)" font-size="8">poor 2.0→3.5</text>
  <line x1="60" y1="72" x2="200" y2="72" stroke="var(--ink)" stroke-width="1.5" stroke-dasharray="3 2"/>
  <text x="200" y="70" fill="var(--ink)" font-size="8">pooled 5.5 (flat)</text>
  <text x="55" y="120" fill="var(--muted)" font-size="8">before            after</text>
</svg>
^ Both subgroup lines slope up after the relabel while the pooled line is flat — the improvement lives entirely in the grouping, not the data.

## Build

Why does moving one value lift both means? Run `--condition`.

```text filename=--condition
CONDITION — why both rise: the moved value straddles the two means
------------------------------------------------------------
  moved value 8
  poor mean 2.00  <  moved 8  <  good mean 9.00
  below good's mean -> removing it raises good
  above poor's mean -> adding it raises poor
------------------------------------------------------------
  any value in that gap lifts both groups when moved down.
```

The moved value, 8, sits in the gap between the two group means: above poor's 2.00 and below good's 9.00. That is the entire condition. Below good's mean, so dropping it raises good; above poor's mean, so adding it raises poor. Any value in that interval, moved from the higher group to the lower, produces the same double improvement — and the wider the gap between the groups, the more values qualify.

<svg role="img" aria-label="A number line showing poor mean 2, the moved value 8, and good mean 9, with 8 in the gap between the means" viewBox="0 0 300 90" width="300" height="90">
  <line x1="20" y1="50" x2="285" y2="50" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="55" cy="50" r="4" fill="var(--s1)"/>
  <text x="42" y="40" fill="var(--s1)" font-size="8">poor 2</text>
  <circle cx="245" cy="50" r="4" fill="var(--s2)"/>
  <text x="228" y="40" fill="var(--s2)" font-size="8">good 9</text>
  <rect x="55" y="46" width="190" height="8" fill="var(--acc-soft)"/>
  <circle cx="215" cy="50" r="5" fill="var(--ink)"/>
  <text x="200" y="72" fill="var(--ink)" font-size="8">moved 8 (in the gap)</text>
  <text x="90" y="72" fill="var(--muted)" font-size="8">any value in this band lifts both groups</text>
</svg>
^ The moved value lands in the shaded band between the two means — that is the region where removing it helps the group it leaves and adding it helps the group it joins.

## Definition of done

The self-test pins the paradox: the good mean rises, the poor mean rises, the moved value straddles the two means, no value changed, and the pooled mean is unchanged.

```python filename=modules/ai-for-science-and-data/code/data-inter-18/willrogers.py:86-98 COMPLETE
    good_mean_rises = mean(ng) > mean(good)
    print("  the good group's mean rises = %s (%.2f -> %.2f)" % (good_mean_rises, mean(good), mean(ng)))

    poor_mean_rises = mean(npr) > mean(poor)
    print("  the poor group's mean rises = %s (%.2f -> %.2f)" % (poor_mean_rises, mean(poor), mean(npr)))

    moved_straddles = mean(poor) < v < mean(good)
    print("  the moved value is between the two means = %s (%.2f < %d < %.2f)" % (moved_straddles, mean(poor), v, mean(good)))

    no_value_changed = sorted(good + poor) == sorted(ng + npr)
    print("  the full set of values is unchanged = %s" % no_value_changed)

    pooled_mean_unchanged = abs(mean(good + poor) - mean(ng + npr)) < 1e-9
    print("  the pooled mean is unchanged = %s (%.2f)" % (pooled_mean_unchanged, mean(ng + npr)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — both group means rise while no value changes and the pooled mean is unchanged
----------------------------------------------------------------------------------------------------
  the good group's mean rises = True (9.00 -> 9.50)
  the poor group's mean rises = True (2.00 -> 3.50)
  the moved value is between the two means = True (2.00 < 8 < 9.00)
  the full set of values is unchanged = True
  the pooled mean is unchanged = True (5.50)
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  good_mean_rises=True  poor_mean_rises=True  moved_straddles=True  no_value_changed=True  pooled_mean_unchanged=True
```

**Done means the improvement is exposed as an artifact, not a claim: both subgroup means rose while the value multiset and the pooled mean are provably unchanged, so the gain came from the relabel alone.**

## Boss fight

Both means rose here. Predict what happens to the two group means if you move a value that is above the good group's mean instead of below it — say, the 10. It is tempting to think any downward move helps both groups.

It does not, and the straddle condition is why. Move the 10 (above good's mean of 9): removing it lowers good's mean, because you dropped an above-average member. It still raises poor's mean. So one group falls and one rises — no paradox, just a normal transfer. The double-improvement requires the moved value to be below the source group's mean and above the destination's; outside that band, at least one group moves the expected way. The phenomenon is not "relabeling always helps everyone" — it is specifically the straddling value that fools both averages at once.

The mirror-image mistake is trusting the pooled mean to catch every such artifact. It catches this one because the reclassification is within a closed population. But if the reclassification also changes who is counted at all — dropping the borderline cases from the study rather than moving them — the pooled mean shifts too, and you are in survivorship-bias territory instead. The safe habit is to fix the grouping (and the population) before comparing, so a mean difference reflects data, not bookkeeping.

```python filename=modules/ai-for-science-and-data/code/data-inter-18/willrogers.py:44-49 COMPLETE
def reclassify(good, poor, v):
    """Move value v from good to poor without changing any number."""
    new_good = list(good)
    new_good.remove(v)
    new_poor = poor + [v]
    return new_good, new_poor
```

**When a grouping changes between two measurements, compare the pooled population, not the subgroups: relabeling a straddling value lifts every subgroup mean while the data underneath stands perfectly still.**

## External resources

Feinstein, Sosin, and Wells, "The Will Rogers Phenomenon" (New England Journal of Medicine, 1985) — the paper that named it, showing stage migration inflating stage-specific cancer survival with no change in treatment.

Any epidemiology text's treatment of stage migration and lead-time bias — the clinical settings where reclassification by better diagnostics fakes improvement.

The connection to Simpson's paradox — both are artifacts of how data is grouped; comparing this module with the Simpson's module shows two different ways a grouping choice can invert or invent an effect.
