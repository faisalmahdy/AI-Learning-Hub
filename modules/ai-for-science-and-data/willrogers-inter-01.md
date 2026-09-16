---
id: willrogers-inter-01
title: Check the overall average, not just the group averages — reclassifying one borderline case can raise both groups' means
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: Two ranked groups — early-stage and late-stage patients, weak and strong schools, low- and high-risk accounts — and you track the average outcome in each. Then the boundary between the groups moves: a better scanner reclassifies some borderline patients, a new rule shifts schools between tiers, a model re-scores accounts. Afterward both groups show a better average and it is tempting to declare progress — but you can get exactly that result with no one's outcome changing at all, purely by moving a case from one group to the other. This is the Will Rogers phenomenon, named for the quip that when the Okies left Oklahoma for California they raised the average intelligence of both states. The mechanism is a fact about averages: take a case below its current group's average but above the other group's average, remove it from the first (whose average rises, having dropped a below-average member) and add it to the second (whose average also rises, having gained an above-average member) — one move, both means up, the case itself unchanged. In medicine this is stage migration: more sensitive imaging finds tiny metastases in patients who would have been early-stage, so they are relabeled late-stage; the early-stage group loses its sickest and the late-stage group gains its healthiest, both average survivals rise, and not one patient lives a day longer. The tell is the overall ungrouped average, which is unchanged when only labels moved. On a fixture where a borderline patient (survival 5) is reclassified from localized (mean 6) to advanced (mean 2), localized rises to 6.5 and advanced to 2.75 while the overall average stays 4.0.
eli5: Imagine two teams lining up by height — the "tall" team and the "short" team. There is one kid on the tall team who is actually the shortest of the tall kids, but still taller than everyone on the short team. If you move that kid to the short team, something funny happens: the tall team's average height goes up (they lost their shortest member) and the short team's average height also goes up (they gained someone taller than all of them). Both teams got "taller on average" — but nobody grew a single inch, you just moved one kid across. So if someone says both groups improved, first check whether the whole crowd actually improved, or whether somebody just got relabeled.
---

## Why this module

This is the statistical illusion that lets both halves of a population improve while the population does not change at all — and it shows up exactly where people least expect a trick, in before-and-after comparisons that seem airtight because every subgroup moved the right way. If early-stage cancer survival went up and late-stage survival also went up, surely treatment improved? Not necessarily. The comparison can be entirely satisfied by relabeling patients, and the person reading the report has no way to see it from the subgroup numbers alone.

The setup is any two ranked groups where the boundary between them can shift. Better diagnostics are the classic cause: a more sensitive scanner finds disease that older equipment missed, so patients who used to be counted in the healthier group get moved to the sicker group. The moved patients are the sickest of the healthy group and the healthiest of the sick group. Removing them lifts the healthy group's average; adding them lifts the sick group's average. Both subgroup survival curves improve, publications report progress by stage, and the actual population outcome is identical to before — the same patients, the same survival times, different labels.

The defense is one number the subgroup comparison omits. This module reclassifies a single patient and shows both group means rising while the pooled average stays flat.

**When comparing group averages across a change that could move cases between groups (a reclassification, a new threshold, a better test), check the overall ungrouped average too, because moving a case that is below its old group's mean and above its new group's mean raises both group means with no change to any individual — so improved subgroup averages can be pure stage-migration artifact, which the unchanged overall average exposes.**

## Concepts

The fixture is two stages of patients with their survival times. Localized (early stage, better prognosis) has survivals 5, 6, 7 — mean 6. Advanced (late stage, worse prognosis) has 1, 2, 3 — mean 2. The reclassification moves one borderline patient, survival 5, from localized to advanced: a better scanner found micro-metastases that reclassify them, but their survival number does not change.

```json filename=modules/ai-for-science-and-data/code/willrogers-inter-01/willrogers.json:4-8 COMPLETE
  "groups": {
    "localized": [5, 6, 7],
    "advanced": [1, 2, 3]
  },
  "reclassify": {"value": 5, "from": "localized", "to": "advanced"}
```

Applying the move is pure relabeling — the value is removed from one group's list and appended to the other's, unchanged. And the overall mean is the pooled average across everyone, ignoring the grouping entirely.

```python filename=modules/ai-for-science-and-data/code/willrogers-inter-01/willrogers.py:53-69 COMPLETE
def mean(vals):
    return sum(vals) / len(vals)


def apply_move(groups, move):
    """Return new groups with the reclassified value moved from one group to the other (value unchanged)."""
    after = {k: list(v) for k, v in groups.items()}
    after[move["from"]].remove(move["value"])
    after[move["to"]].append(move["value"])
    return after


def overall(groups):
    """The pooled mean across every case, ignoring the grouping."""
    allvals = [v for g in groups.values() for v in g]
    return mean(allvals)
```

The condition that makes both means rise is precise: the moved case must be below its old group's mean (so removing it lifts that mean) and above its new group's mean (so adding it lifts that one). The reasoning view prints exactly that pair of comparisons.

```python filename=modules/ai-for-science-and-data/code/willrogers-inter-01/willrogers.py:73-78 COMPLETE
    print("  moved case: %s = %d, from %s to %s" % (data["metric"], v, move["from"], move["to"]))
    print("  it is BELOW its old group's mean: %d < %.2f (%s)" % (v, mean(groups[move["from"]]), move["from"]))
    print("  it is ABOVE its new group's mean: %d > %.2f (%s)" % (v, mean(groups[move["to"]]), move["to"]))
    print("-" * 60)
    print("  removing a below-average member raises the old group's mean;")
    print("  adding an above-average member raises the new group's mean.")
```

A value of 5 is below localized's 6 and above advanced's 2 — it satisfies both.

<svg role="img" aria-label="A number line with localized cases at 5,6,7 and advanced at 1,2,3; the case at 5 sits below the localized mean of 6 and above the advanced mean of 2, with an arrow moving it from the localized group to the advanced group" viewBox="0 0 320 130">
  <line x1="20" y1="70" x2="300" y2="70" stroke="var(--line)" stroke-width="1"/>
  <text x="16" y="85" font-size="8" fill="var(--muted)">1</text>
  <text x="156" y="85" font-size="8" fill="var(--muted)">4</text>
  <text x="292" y="85" font-size="8" fill="var(--muted)">7</text>
  <circle cx="60" cy="70" r="4" fill="var(--s2)"/><circle cx="100" cy="70" r="4" fill="var(--s2)"/><circle cx="140" cy="70" r="4" fill="var(--s2)"/>
  <text x="52" y="100" font-size="8" fill="var(--s2)">advanced 1,2,3 (mean 2)</text>
  <circle cx="220" cy="70" r="4" fill="var(--s1)"/><circle cx="260" cy="70" r="4" fill="var(--s1)"/>
  <circle cx="180" cy="70" r="5" fill="var(--ink)"/>
  <text x="200" y="100" font-size="8" fill="var(--s1)">localized 5,6,7 (mean 6)</text>
  <text x="150" y="42" font-size="8.5" fill="var(--ink)">move the 5:</text>
  <path d="M 180 62 Q 150 40 120 62" fill="none" stroke="var(--ink)" stroke-width="1.3"/>
  <text x="150" y="26" font-size="8" fill="var(--muted)">below localized mean 6, above advanced mean 2</text>
</svg>
^ The moved case (the dark point at 5) sits between the two group means — below localized's 6, above advanced's 2. That in-between position is exactly what lets its move raise both averages at once.

**Both means rising is not a coincidence of these numbers but a guarantee of the geometry — any case between the two group means lifts both when it crosses the boundary.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the outcome-comparison step of a survival analysis, reduced to six patients so every mean is checkable by hand.

Run `--groups` to see the means before and after the reclassification.

```text filename=willrogers.py --groups
  before: localized mean 6.00 ; advanced mean 2.00 ; OVERALL 4.00
          localized=[5, 6, 7]  advanced=[1, 2, 3]
  after : localized mean 6.50 ; advanced mean 2.75 ; OVERALL 4.00
          localized=[6, 7]  advanced=[1, 2, 3, 5]
  both group means rose; overall mean unchanged (4.00 -> 4.00)
```

Before, localized averages 6 and advanced averages 2. After moving the single survival-5 patient, localized is [6, 7] averaging 6.5 and advanced is [1, 2, 3, 5] averaging 2.75 — both higher. Read as a stage-by-stage report, this looks like unambiguous improvement in both groups. But the overall line is flat: 4.00 before, 4.00 after. Six patients with the same six survival times; the pooled average cannot move, because nothing moved except a label.

Now `--move` shows why the one patient lifts both.

```text filename=willrogers.py --move
  moved case: survival_months = 5, from localized to advanced
  it is BELOW its old group's mean: 5 < 6.00 (localized)
  it is ABOVE its new group's mean: 5 > 2.00 (advanced)
  removing a below-average member raises the old group's mean;
  adding an above-average member raises the new group's mean.
```

The patient was the weakest of the localized group (5, below the group's 6) — so dropping them raises what remains. And they were stronger than anyone in the advanced group (5, above its 2) — so adding them raises that group too. One patient, both directions, no change to the patient. That is the entire trick, and it works for any case caught between the two group means.

**The subgroup report shows both stages improving by half a point or more; the overall average shows the truth — 4.00 unchanged — because reclassification moved a label, not an outcome.**

## Build

The self-test asserts the paradox and its cause: both group means rise, the overall mean does not, and no individual's value changed. The unchanged overall mean paired with unchanged values is what proves the subgroup improvement is an artifact.

```python filename=modules/ai-for-science-and-data/code/willrogers-inter-01/willrogers.py:87-101 COMPLETE
    from_mean_rises = mean(after[fr]) > mean(groups[fr])
    print("  the %s group mean rises = %s (%.2f -> %.2f)" % (fr, from_mean_rises, mean(groups[fr]), mean(after[fr])))

    to_mean_rises = mean(after[to]) > mean(groups[to])
    print("  the %s group mean rises = %s (%.2f -> %.2f)" % (to, to_mean_rises, mean(groups[to]), mean(after[to])))

    overall_unchanged = abs(overall(after) - overall(groups)) < 1e-9
    print("  the overall (ungrouped) mean is unchanged = %s (%.2f == %.2f)" % (overall_unchanged, overall(groups), overall(after)))

    below_old = v < mean(groups[fr])
    print("  the moved case is below its old group's mean = %s (%d < %.2f)" % (below_old, v, mean(groups[fr])))

    above_new = v > mean(groups[to])
    print("  the moved case is above its new group's mean = %s (%d > %.2f)" % (above_new, v, mean(groups[to])))
```

<svg role="img" aria-label="Bars showing localized mean rising from 6 to 6.5 and advanced from 2 to 2.75, with the overall mean flat at 4.0 before and after" viewBox="0 0 320 130">
  <line x1="30" y1="105" x2="310" y2="105" stroke="var(--line)" stroke-width="1"/>
  <text x="40" y="120" font-size="8" fill="var(--muted)">localized</text>
  <rect x="40" y="45" width="20" height="60" fill="var(--s1)" opacity="0.55"/><text x="38" y="41" font-size="7" fill="var(--muted)">6.0</text>
  <rect x="62" y="40" width="20" height="65" fill="var(--s1)"/><text x="62" y="36" font-size="7" fill="var(--muted)">6.5</text>
  <text x="140" y="120" font-size="8" fill="var(--muted)">advanced</text>
  <rect x="140" y="85" width="20" height="20" fill="var(--s2)" opacity="0.55"/><text x="140" y="81" font-size="7" fill="var(--muted)">2.0</text>
  <rect x="162" y="77" width="20" height="28" fill="var(--s2)"/><text x="162" y="73" font-size="7" fill="var(--muted)">2.75</text>
  <text x="245" y="120" font-size="8" fill="var(--muted)">overall</text>
  <rect x="240" y="65" width="20" height="40" fill="var(--ink)" opacity="0.55"/><text x="240" y="61" font-size="7" fill="var(--muted)">4.0</text>
  <rect x="262" y="65" width="20" height="40" fill="var(--ink)"/><text x="262" y="61" font-size="7" fill="var(--muted)">4.0</text>
  <text x="40" y="18" font-size="8.5" fill="var(--muted)">pale = before, solid = after</text>
</svg>
^ Both subgroup bars grow after the move; the overall bar is identical before and after. The flat overall bar is the signature of a Will Rogers artifact — subgroups up, whole unchanged.

Running the check confirms every clause, including that no individual's value changed.

```text filename=willrogers.py --check
  the localized group mean rises = True (6.00 -> 6.50)
  the advanced group mean rises = True (2.00 -> 2.75)
  the overall (ungrouped) mean is unchanged = True (4.00 == 4.00)
  the moved case is below its old group's mean = True (5 < 6.00)
  the moved case is above its new group's mean = True (5 > 2.00)
  no individual's value changed (only the label) = True
```

**The check ties both rising subgroup means to an unchanged overall mean and unchanged values — so the improvement is demonstrably relabeling, and the overall mean is the number that reveals it.**

## Definition of done

Two properties close it. Both group means must rise while the overall mean is unchanged — the paradox itself — and no individual's value may have changed, which is what makes "improvement" indefensible. The unchanged-values clause rules out the innocent explanation (that outcomes genuinely improved and reclassification is incidental); here it is reclassification and nothing else.

```python filename=modules/ai-for-science-and-data/code/willrogers-inter-01/willrogers.py:103-107 COMPLETE
    no_value_changed = sorted(v for g in after.values() for v in g) == sorted(v for g in groups.values() for v in g)
    print("  no individual's value changed (only the label) = %s" % no_value_changed)

    ok = from_mean_rises and to_mean_rises and overall_unchanged and below_old and above_new and no_value_changed
```

Two boundaries keep the tool calibrated. First, the phenomenon requires movement between groups; if the boundary is fixed and outcomes genuinely change, rising subgroup means are real, and the overall mean rises with them — the overall check is precisely what distinguishes the two cases, which is why you compute it rather than banning subgroup comparisons. Second, the direction depends on which cases move: reclassifying cases that are above their old group's mean and below the new group's would lower both means, and the general lesson is that any reclassification perturbs subgroup statistics in ways that have nothing to do with real change. The practical rule for reading any before/after comparison where classification could have shifted — new diagnostic tech, a redrawn risk threshold, a re-scored cohort — is to insist on the pooled, ungrouped outcome. If the subgroups improved but the whole did not, you are looking at migration, not progress; if the whole improved too, the gain is real.

<svg role="img" aria-label="A decision guide: subgroups up and overall up means real progress; subgroups up but overall flat means reclassification artifact" viewBox="0 0 320 120">
  <rect x="10" y="14" width="120" height="20" fill="none" stroke="var(--ink)" stroke-width="1"/>
  <text x="18" y="28" font-size="9" fill="var(--ink)">both subgroups up</text>
  <line x1="130" y1="24" x2="180" y2="24" stroke="var(--line)" stroke-width="1"/>
  <text x="184" y="20" font-size="8.5" fill="var(--muted)">check overall...</text>
  <rect x="150" y="46" width="160" height="22" fill="var(--s1)"/>
  <text x="158" y="61" font-size="8.5" fill="var(--panel)">overall UP → real progress</text>
  <rect x="150" y="80" width="160" height="22" fill="var(--s2)"/>
  <text x="158" y="95" font-size="8.5" fill="var(--panel)">overall FLAT → reclassification</text>
  <line x1="150" y1="34" x2="200" y2="46" stroke="var(--s1)" stroke-width="1"/>
  <line x1="150" y1="34" x2="200" y2="80" stroke="var(--s2)" stroke-width="1"/>
</svg>
^ Both subgroups improving is not the conclusion — it is the prompt to check the overall average. Overall up confirms real progress; overall flat means the subgroup gains were reclassification, the Will Rogers case.

**Done means both subgroup means rise, the overall mean is unchanged, and no value changed — a stage-migration artifact, exposed by the one number (the pooled average) that reclassification cannot move.**

## Boss fight

A hospital publishes that five-year survival improved for both early-stage and late-stage lung cancer after it installed a new high-resolution PET scanner, and cites this as evidence the scanner improves outcomes. Before the hospital scales up the program on that basis, what single statistic would you ask for, and what would each possible answer tell you?

Ask for the overall five-year survival across all lung-cancer patients, ungrouped — the pooled rate, not the by-stage rates. The new scanner is exactly the kind of change that causes stage migration: it detects small metastases the old imaging missed, so some patients previously classified early-stage are now classified late-stage. Those migrated patients are the sickest of the old early-stage group (removing them raises early-stage survival) and the healthiest of the late-stage group (adding them raises late-stage survival), so both by-stage curves can improve with zero change in how long anyone lives. If the overall survival is flat, that is precisely what happened — the improvement is a Will Rogers artifact of reclassification, and scaling the scanner will not extend anyone's life (though better staging may still help treatment decisions, that is a separate claim needing separate evidence). If the overall survival also rose, then the gain is real and not just migration, and the scanner (or accompanying treatment changes) deserves credit. The by-stage numbers alone cannot distinguish these two worlds; the pooled number is the one that can, which is why you ask for it before committing resources.

## External resources

Feinstein, Sosin, and Wells, "The Will Rogers Phenomenon: Stage Migration and New Diagnostic Techniques as a Source of Misleading Statistics for Survival in Cancer" (New England Journal of Medicine, 1985) — the paper that named the effect and documented it in real lung-cancer cohorts, the definitive source for the boss fight.

The Wikipedia article on the Will Rogers phenomenon and standard epidemiology texts' treatment of stage migration — accessible explanations of the mechanism and its appearances beyond medicine, including sports, education tiers, and credit-risk reclassification.
