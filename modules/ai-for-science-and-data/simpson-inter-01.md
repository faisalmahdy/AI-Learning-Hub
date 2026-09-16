---
id: simpson-inter-01
title: A treatment can win every subgroup and lose the total — Simpson's paradox is an allocation artifact, not a contradiction
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 16 min
summary: A rate is a fraction — recoveries over patients — and when you pool two subgroups the pooled rate is not the average of the subgroup rates but their count-weighted average, so it leans toward whichever subgroup contributed more patients. That is the entire mechanism of Simpson's paradox: if the subgroup where a treatment does worse is also where most of its patients are, the pooled rate is dragged down toward that worse subgroup even while the treatment beats its rival in every subgroup taken alone. The cause is a confounder — a variable associated with both the treatment assignment and the outcome. On the real Charig 1986 kidney-stone data, treatment A recovers 93.1% of small stones and 73.0% of large ones versus B's 86.7% and 68.8% — A wins both subgroups — but A was given 263 large stones (the hard cases) to B's 80, so A's overall rate is 78.0% against B's 82.6% and B wins the pooled comparison, reversing every subgroup. The fix is to compare like with like: look within subgroups, or standardize both treatments to one common case-mix, which puts A back on top at 83.3% versus 77.9%.
eli5: Imagine two doctors. One doctor mostly treats very sick patients; the other mostly treats mildly sick patients. Even if the first doctor is better with every kind of patient, their overall recovery rate can look worse — because they took on the hard cases, and hard cases recover less no matter who treats them. If you just compare the two doctors' overall numbers, you're really comparing who got the easier patients, not who's the better doctor. To compare them fairly you have to look at how each did on the SAME kind of patient — and then the better doctor shows up as better, just like they were within each group all along.
---

## Why this module

Pooling two groups feels like it should only add information, so a total that disagrees with every part reads as a paradox or an error. It is neither: the total is a different, confounded question, and reporting it as if it summarized the parts is one of the most common ways real data is read exactly backwards.

A rate is a fraction: recoveries over patients. When you pool two subgroups, the pooled rate is not the average of the two subgroup rates — it is their count-weighted average, so the pooled number leans toward whichever subgroup contributed more patients. That is the whole mechanism behind Simpson's paradox. If the subgroup where a treatment does worse also happens to be the subgroup where most of its patients are, the pooled rate is dragged down toward that worse subgroup, even while the treatment beats its rival in every subgroup taken alone. Two treatments can each be pooled toward different subgroups, and the pooled comparison then points the opposite way from every subgroup comparison. Nothing is inconsistent — the pooled rates answer a different question than the subgroup rates, because the two treatments were not given to comparable patients.

The cause is a confounder: a variable associated with both the treatment assignment and the outcome. Here stone size is the confounder — large stones recover less often (they affect the outcome), and treatment A was given mostly to large-stone patients while B went mostly to small-stone patients (it is associated with the assignment). So A's overall rate is a report on a harder population, and comparing A's overall rate to B's compares treatment tangled with case-mix. The fix is to compare like with like: look within each subgroup, or standardize — apply each treatment's per-subgroup rates to one common population mix, holding the confounder fixed. This module runs the real kidney-stone numbers and shows the reversal and its repair.

**A pooled rate is the count-weighted average of its subgroup rates, so when a confounder is allocated unevenly a treatment can win every subgroup and still lose the total — and the total is then a fact about case-mix, not about the treatment, until you standardize or compare within subgroups.**

## Concepts

**The pooled rate** sums recoveries and patients across subgroups, so a subgroup with more patients pulls the total toward its own rate. It is not the mean of the subgroup rates.

```python filename=modules/ai-for-science-and-data/code/simpson-inter-01/simpson.py:51-55 COMPLETE
def overall(treatment):
    """Pooled recovery rate: total recoveries over total patients -- the count-weighted mix of the subgroup rates."""
    rec = sum(treatment[g]["recovered"] for g in SUBGROUPS)
    tot = sum(treatment[g]["total"] for g in SUBGROUPS)
    return rec / tot
```

**Standardizing** removes the confounder's effect by force: take each treatment's per-subgroup rates and apply them to one shared case-mix, so both treatments are scored as if they had treated the same population. Whatever difference remains is the treatment, not the allocation.

```python filename=modules/ai-for-science-and-data/code/simpson-inter-01/simpson.py:63-66 COMPLETE
def standardized(treatment, mix):
    """Apply this treatment's per-subgroup rates to a common population mix -- holds the confounder fixed."""
    total = sum(mix.values())
    return sum(rate(treatment[g]) * mix[g] for g in SUBGROUPS) / total
```

<svg role="img" aria-label="Grouped recovery rates: treatment A above B in the small subgroup and in the large subgroup, but A below B in the overall pooled bar" viewBox="0 0 300 128" width="300" height="128">
  <text x="6" y="12" fill="var(--muted)" font-size="8">A is higher in each subgroup, lower in the pooled total</text>
  <line x1="30" y1="104" x2="290" y2="104" stroke="var(--line)"/>
  <text x="24" y="34" fill="var(--muted)" font-size="7" text-anchor="end">100%</text>
  <line x1="30" y1="32" x2="290" y2="32" stroke="var(--grid)" stroke-dasharray="2 2"/>
  <g transform="translate(60,0)">
  <rect x="0" y="38" width="18" height="66" fill="var(--s1)"/><rect x="20" y="47" width="18" height="57" fill="var(--s2)"/>
  <text x="0" y="116" fill="var(--muted)" font-size="7">small</text><text x="0" y="34" fill="var(--muted)" font-size="6">93 / 87</text>
  </g>
  <g transform="translate(140,0)">
  <rect x="0" y="53" width="18" height="51" fill="var(--s1)"/><rect x="20" y="56" width="18" height="48" fill="var(--s2)"/>
  <text x="0" y="116" fill="var(--muted)" font-size="7">large</text><text x="0" y="49" fill="var(--muted)" font-size="6">73 / 69</text>
  </g>
  <g transform="translate(226,0)">
  <rect x="0" y="49" width="18" height="55" fill="var(--s1)"/><rect x="20" y="46" width="18" height="58" fill="var(--s2)"/>
  <text x="-4" y="116" fill="var(--muted)" font-size="7">overall</text><text x="-2" y="42" fill="var(--muted)" font-size="6">78 / 83</text>
  </g>
  <text x="60" y="128" fill="var(--s1)" font-size="7">■ A</text><text x="90" y="128" fill="var(--s2)" font-size="7">■ B</text>
</svg>
^ In both the small and large subgroups treatment A's bar (left) stands above B's, yet in the pooled overall bars the order flips and B stands above A — the reversal Simpson's paradox names.

**Pool by summing counts and the bigger subgroup wins the average; standardize to a common mix and the confounder is held fixed — the two operations answer different questions, and only the second compares the treatments rather than their patient populations.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/simpson-inter-01/simpson.py

The fixture is the real Charig 1986 kidney-stone counts: recoveries over patients, per treatment, split by stone size.

```json filename=modules/ai-for-science-and-data/code/simpson-inter-01/simpson.json:4-7 COMPLETE
    "A": {
      "small": {"recovered": 81, "total": 87},
      "large": {"recovered": 192, "total": 263}
    },
```

Run `--rates` for the per-subgroup and pooled rates.

```text filename=--rates
RATES — per-subgroup and overall recovery
------------------------------------------------------------
  treatment   small           large           overall
  A            81/87  (93.1%)  192/263 (73.0%)  273/350 (78.0%)
  B           234/270 (86.7%)   55/80  (68.8%)  289/350 (82.6%)
------------------------------------------------------------
  A wins small (93.1 > 86.7) and large (73.0 > 68.8), but B wins overall (82.6 > 78.0).
```

Read the two subgroup columns first: A recovers 93.1% of small stones to B's 86.7%, and 73.0% of large stones to B's 68.8%. A is better on every kind of patient. Now read the overall column: A 78.0%, B 82.6% — B is better. Both statements are true of the same table. The reversal is not a rounding artifact or a trick of small numbers; it is 350 patients per arm, and the gap flips by more than four points. What changed between the columns is not the treatments' effectiveness but the denominators: A's overall 78.0% is dominated by its 263 large-stone patients, whose 73.0% drags the pooled number down, while B's overall 82.6% is dominated by its 270 small-stone patients at 86.7%. The pooled rates are each leaning toward a different subgroup, so they compare two different populations wearing the treatments' names.

<svg role="img" aria-label="Patient composition of each treatment: treatment A is mostly large-stone patients, treatment B is mostly small-stone patients, so their pooled rates lean toward opposite subgroups" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">each arm has 350 patients but opposite case-mix</text>
  <g transform="translate(40,24)">
  <text x="-30" y="14" fill="var(--muted)" font-size="8">A</text>
  <rect x="0" y="2" width="55" height="16" fill="var(--s1)"/><rect x="55" y="2" width="165" height="16" fill="var(--s2)"/>
  <text x="8" y="14" fill="var(--panel)" font-size="7">87 small</text><text x="105" y="14" fill="var(--panel)" font-size="7">263 large (hard)</text>
  </g>
  <g transform="translate(40,52)">
  <text x="-30" y="14" fill="var(--muted)" font-size="8">B</text>
  <rect x="0" y="2" width="170" height="16" fill="var(--s1)"/><rect x="170" y="2" width="50" height="16" fill="var(--s2)"/>
  <text x="45" y="14" fill="var(--panel)" font-size="7">270 small (easy)</text><text x="176" y="14" fill="var(--panel)" font-size="7">80 large</text>
  </g>
  <text x="40" y="92" fill="var(--s1)" font-size="7">■ small stones</text><text x="150" y="92" fill="var(--s2)" font-size="7">■ large stones</text>
</svg>
^ Both treatments have 350 patients, but A's are three-quarters large (hard) stones and B's are three-quarters small (easy) stones, so each treatment's pooled rate is pulled toward a different subgroup — the uneven case-mix that drives the reversal.

## Build

The reversal is caused entirely by the allocation, and naming that confounder is what lets you undo it. Run `--confound`.

```text filename=--confound
CONFOUND — the allocation that flips the total, and standardizing that undoes it
------------------------------------------------------------------
  large-stone (hard cases) share of each treatment's patients:
    A    263 of 350 = 75% large stones
    B     80 of 350 = 23% large stones
  common case-mix (both treatments): small=357, large=343
------------------------------------------------------------------
  standardized to that mix:  A = 83.3%   B = 77.9%   -> A wins, agreeing with the subgroups.
```

Here is the whole cause in one line: 75% of A's patients had large stones versus 23% of B's. A was handed the hard cases. Because large stones recover less often no matter the treatment, A's population was set up to post a lower overall number before any treatment was given — that is exactly what "confounded" means, a variable (stone size) that steers both who gets which treatment and who recovers. Standardizing dissolves it: take the combined case-mix (357 small, 343 large patients across both arms) and score each treatment as if it had treated that same mix, using its own per-subgroup rates. Now A is 83.3% and B is 77.9% — A wins, back in agreement with both subgroups, because the comparison finally holds stone size fixed. The common mix is just the per-subgroup patient totals summed across treatments.

```python filename=modules/ai-for-science-and-data/code/simpson-inter-01/simpson.py:58-60 COMPLETE
def combined_mix(treatments):
    """The shared case-mix: total patients per subgroup across both treatments."""
    return {g: sum(treatments[t][g]["total"] for t in treatments) for g in SUBGROUPS}
```

<svg role="img" aria-label="A confounder diagram: stone size points to both treatment assignment and recovery outcome, so the treatment-outcome comparison is confounded by stone size" viewBox="0 0 300 120" width="300" height="120">
  <text x="6" y="12" fill="var(--muted)" font-size="8">stone size steers BOTH assignment and outcome — a confounder</text>
  <rect x="110" y="24" width="80" height="20" fill="none" stroke="var(--s2)"/><text x="122" y="38" fill="var(--muted)" font-size="8">stone size</text>
  <rect x="20" y="82" width="90" height="20" fill="none" stroke="var(--line)"/><text x="30" y="96" fill="var(--muted)" font-size="8">treatment A/B</text>
  <rect x="190" y="82" width="90" height="20" fill="none" stroke="var(--line)"/><text x="205" y="96" fill="var(--muted)" font-size="8">recovery</text>
  <line x1="130" y1="44" x2="80" y2="82" stroke="var(--s2)"/><text x="86" y="66" fill="var(--muted)" font-size="6">allocated by</text>
  <line x1="170" y1="44" x2="220" y2="82" stroke="var(--s2)"/><text x="196" y="66" fill="var(--muted)" font-size="6">affects</text>
  <line x1="110" y1="92" x2="190" y2="92" stroke="var(--ink)" stroke-dasharray="3 2"/><text x="120" y="88" fill="var(--muted)" font-size="6">apparent effect (confounded)</text>
</svg>
^ Stone size is associated with both the treatment a patient received (A got the large stones) and whether they recovered (large stones recover less), so the raw treatment-to-recovery comparison mixes the treatment's effect with the case-mix until stone size is held fixed.

## Definition of done

The self-test pins the full paradox: A wins both subgroups, B wins the pool, the allocation is the confounder, and standardizing restores A.

```python filename=modules/ai-for-science-and-data/code/simpson-inter-01/simpson.py:109-121 COMPLETE
    a_wins_small = rate(t["A"]["small"]) > rate(t["B"]["small"])
    print("  A beats B on small stones = %s (%.1f%% vs %.1f%%)" % (a_wins_small, rate(t["A"]["small"]) * 100, rate(t["B"]["small"]) * 100))

    a_wins_large = rate(t["A"]["large"]) > rate(t["B"]["large"])
    print("  A beats B on large stones = %s (%.1f%% vs %.1f%%)" % (a_wins_large, rate(t["A"]["large"]) * 100, rate(t["B"]["large"]) * 100))

    b_wins_overall = overall(t["B"]) > overall(t["A"])
    print("  yet B beats A overall (the reversal) = %s (%.1f%% vs %.1f%%)" % (b_wins_overall, overall(t["B"]) * 100, overall(t["A"]) * 100))

    a_large_share = t["A"]["large"]["total"] / sum(t["A"][g]["total"] for g in SUBGROUPS)
    b_large_share = t["B"]["large"]["total"] / sum(t["B"][g]["total"] for g in SUBGROUPS)
    allocation_confounded = a_large_share > b_large_share
    print("  A was given far more hard (large-stone) cases = %s (%.0f%% vs %.0f%%)" % (allocation_confounded, a_large_share * 100, b_large_share * 100))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — treatment A wins each subgroup but loses overall; the allocation is confounded; standardizing restores A
--------------------------------------------------------------------------------------------------------------------
  A beats B on small stones = True (93.1% vs 86.7%)
  A beats B on large stones = True (73.0% vs 68.8%)
  yet B beats A overall (the reversal) = True (82.6% vs 78.0%)
  A was given far more hard (large-stone) cases = True (75% vs 23%)
  standardizing to a common case-mix restores A on top = True (83.3% vs 77.9%)
```

**Done means the reversal and its repair are both proven on the real counts: A beats B at 93.1% vs 86.7% (small) and 73.0% vs 68.8% (large) yet loses 78.0% vs 82.6% overall, the cause is that A treated 75% large stones to B's 23%, and standardizing to the combined case-mix returns A to the top at 83.3% vs 77.9% — so the pooled loss was case-mix, not treatment.**

## Boss fight

Predict the hard part, which is not spotting the paradox once the subgroups are in front of you — it is knowing whether to trust the subgroups or the total, because the arithmetic alone cannot tell you.

The first trap is that stratifying is not automatically the right answer; it depends on the causal role of the splitting variable. Here stone size is a confounder — it exists before treatment and influences assignment — so conditioning on it removes bias and the subgroup comparison is the honest one. But if the variable you split on is a *mediator*, something on the causal path from treatment to outcome (a drug lowers blood pressure, and you split on blood pressure), then conditioning on it removes part of the treatment's real effect, and the stratified comparison is the misleading one while the pooled comparison is closer to the truth. Simpson's paradox is the same table either way; which number to believe is decided by a causal question — is the splitter a common cause or an effect? — that lives outside the data. This is why "always look at subgroups" and "always look at the total" are both wrong as blanket rules.

The second trap is that this is the engine behind a whole family of aggregation mistakes, and it does not require a tidy two-by-two table. Any time you compare pooled rates across groups with different compositions — click-through rates across two weeks with different traffic mixes, model accuracy across two datasets with different class balances, pass rates across cohorts with different difficulty — the pooled comparison can reverse the within-group truth, and averaging pre-computed per-group rates (an unweighted mean of the subgroup rates) is yet a third number that matches neither pool nor the correct standardized comparison. The defenses are structural: never compare pooled rates across populations without checking whether their case-mix differs, report standardized or within-stratum comparisons when it does, and treat any headline rate as a weighted average whose weights you must see before you trust the direction. The paradox is not exotic; it is what count-weighting does whenever the weights differ and nobody looked.

**Whether the subgroup or the pooled comparison is correct is a causal question the numbers cannot answer — condition on a confounder (a pre-treatment common cause) but not on a mediator (an effect on the causal path) — and because any cross-population comparison of count-weighted rates can reverse under differing case-mix, the durable defense is to check composition, standardize to a common mix, and always read a headline rate as a weighted average whose weights you have actually inspected.**

## External resources

Any statistics or causal-inference text on Simpson's paradox and confounding — the kidney-stone data used here (Charig et al. 1986) and the Berkeley admissions example are the standard cases, alongside the confounder-versus-mediator distinction that decides which comparison to trust.

Judea Pearl's writing on the causal resolution of Simpson's paradox — why the choice between the aggregated and stratified table cannot be made from the data alone and requires a causal model of how the splitting variable relates to treatment and outcome.

The companion base-rate and probability-fallacy modules in this topic — like them, Simpson's paradox is a case where an intuitive read of the numbers is confidently wrong, here because a pooled rate hides the weights that produced it.
