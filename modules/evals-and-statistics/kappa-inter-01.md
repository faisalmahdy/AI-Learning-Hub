---
id: kappa-inter-01
title: Report Cohen's kappa, not raw agreement — two raters who both say "no" agree 82% of the time by chance alone
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: When two raters label the same items — two annotators, an LLM judge against a gold label, two judges to compare — the natural quality measure is how often they agree, but raw agreement is inflated whenever the labels are imbalanced, because agreement can happen by accident. If 90% of items are really "no", two raters who each say "no" most of the time land on "no" together most of the time without any shared judgment, so their agreement is mostly the arithmetic of both usually guessing the common class. Cohen's kappa corrects for chance: it computes observed agreement p_o and the agreement expected if the raters' labels were independent given their yes-rates p_e, and reports kappa = (p_o − p_e)/(1 − p_e) — the agreement above chance over the room there was to beat chance — so kappa = 0 means chance-level (no real signal), 1 means perfect, and the rescaling makes it comparable across class balances that raw agreement is not. On a fixture, a "chance" pair whose yes-labels are independent on an imbalanced set has raw agreement 0.82 but chance agreement also 0.82, so kappa is 0 — no real agreement at all — while a "real" pair has raw agreement 0.94 and kappa 0.79; raw agreement cannot tell them apart, kappa can.
eli5: If two people are asked yes/no questions where the answer is almost always "no," and they both just tend to say "no," they'll match most of the time — but that's not teamwork, it's both leaning the same easy way. To measure real agreement you first figure out how often they'd match just by both guessing "no" a lot, then check how much they beat that. Two graders can both look 90% in-agreement while one pair genuinely sees eye to eye and the other is only riding the fact that "no" is usually right. The corrected score tells them apart; the raw percentage doesn't.
---

## Why this module

Inter-rater agreement is the headline number behind every claim that a labeling process is trustworthy — an annotation guideline is clear, an LLM judge matches humans, two graders are consistent. Reported as a raw percentage on skewed labels, that number is systematically too high, because it counts the agreements that both raters would have reached by simply favoring the common answer. A labeling scheme that looks 82% reliable can have no real reliability at all.

When two raters label the same items — two human annotators, an LLM judge against a gold label, two judges to be compared — the natural quality measure is how often they agree. But raw agreement (the fraction of items labeled the same) is inflated whenever the labels are imbalanced, because agreement can happen by accident. If 90% of items are really "no", two raters who each say "no" most of the time will land on "no" together most of the time without any shared judgment — their agreement is mostly the arithmetic of both usually guessing the common class. So a headline like "82% agreement" can describe raters who are, in the part that matters, no better than two independent coin-weightings.

Cohen's kappa corrects for chance agreement. It computes the observed agreement p_o (the raw fraction) and the expected agreement p_e — how often the two would agree if their labels were independent given their individual yes-rates — and reports kappa = (p_o − p_e)/(1 − p_e). The numerator is the agreement above chance; the denominator is the room above chance there was to agree. So kappa = 0 means agreement exactly at the chance level, kappa = 1 means perfect, and negative means worse than chance, and the rescaling by (1 − p_e) makes kappa comparable across datasets with different class balances — which raw agreement is not. This module scores two rater-pairs that both hit high raw agreement and shows kappa separate them.

**Raw inter-rater agreement is inflated on imbalanced labels because two raters who both favor the common class agree by chance, so report Cohen's kappa = (observed − chance)/(1 − chance), which is 0 at chance-level agreement and comparable across class balances.**

## Concepts

**Observed agreement** is the raw fraction of items the two raters labeled the same — the number that looks reassuring and hides the chance component.

```python filename=modules/evals-and-statistics/code/kappa-inter-01/kappa.py:50-52 COMPLETE
def observed_agreement(c):
    """p_o: the fraction of items the two raters labeled the same."""
    return (c["both_yes"] + c["both_no"]) / total(c)
```

**Chance agreement** is how often the two would coincide if their labels were independent, given each rater's own yes-rate — high exactly when the labels are imbalanced.

```python filename=modules/evals-and-statistics/code/kappa-inter-01/kappa.py:55-60 COMPLETE
def chance_agreement(c):
    """p_e: agreement expected if the two raters' labels were independent given their yes-rates."""
    n = total(c)
    r1_yes = (c["both_yes"] + c["r1_yes_r2_no"]) / n
    r2_yes = (c["both_yes"] + c["r1_no_r2_yes"]) / n
    return r1_yes * r2_yes + (1 - r1_yes) * (1 - r2_yes)
```

**Kappa** subtracts the chance agreement from the observed and rescales by the room above chance, so it reports only the agreement that is not explained by both raters leaning the same way.

```python filename=modules/evals-and-statistics/code/kappa-inter-01/kappa.py:63-67 COMPLETE
def kappa(c):
    """Cohen's kappa: (observed - chance) / (1 - chance)."""
    po, pe = observed_agreement(c), chance_agreement(c)
    k = (po - pe) / (1 - pe)
    return 0.0 if abs(k) < 1e-9 else k
```

<svg role="img" aria-label="A bar of observed agreement, a bar of chance agreement, and kappa as the gap between them rescaled by the room above chance" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">kappa = (observed − chance) / (1 − chance)</text>
  <line x1="30" y1="96" x2="30" y2="24" stroke="var(--line)"/><line x1="30" y1="96" x2="290" y2="96" stroke="var(--line)"/>
  <text x="24" y="28" fill="var(--muted)" font-size="7" text-anchor="end">1.0</text>
  <text x="150" y="30" fill="var(--muted)" font-size="7">real-agreement scenario</text>
  <rect x="60" y="28" width="40" height="68" fill="var(--s1)"/><text x="58" y="108" fill="var(--muted)" font-size="7">observed .94</text>
  <rect x="120" y="47" width="40" height="49" fill="var(--muted)"/><text x="120" y="108" fill="var(--muted)" font-size="7">chance .72</text>
  <line x1="180" y1="28" x2="180" y2="47" stroke="var(--s2)"/><line x1="176" y1="28" x2="184" y2="28" stroke="var(--s2)"/><line x1="176" y1="47" x2="184" y2="47" stroke="var(--s2)"/>
  <text x="188" y="34" fill="var(--muted)" font-size="6">above chance</text>
  <line x1="200" y1="28" x2="200" y2="96" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="204" y="60" fill="var(--muted)" font-size="6">room above</text><text x="204" y="70" fill="var(--muted)" font-size="6">chance (1−.72)</text>
  <text x="60" y="120" fill="var(--muted)" font-size="7"></text>
</svg>
^ Kappa is the height of "observed above chance" divided by the room there was above chance (1 − chance): only the part of the agreement that exceeds what both raters would reach by chance counts, and it is normalized so different class balances are comparable.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/kappa-inter-01/kappa.py

The fixture is two rater-pairs, each a 2×2 confusion of 100 items.

```json filename=modules/evals-and-statistics/code/kappa-inter-01/kappa.json:3-6 COMPLETE
  "scenarios": {
    "chance_agreement": {"both_yes": 1, "r1_yes_r2_no": 9, "r1_no_r2_yes": 9, "both_no": 81},
    "real_agreement":   {"both_yes": 14, "r1_yes_r2_no": 3, "r1_no_r2_yes": 3, "both_no": 80}
  }
```

Run `--agreement` to score both.

```text filename=--agreement
AGREEMENT — raw agreement vs Cohen's kappa, per scenario
------------------------------------------------------------------
  scenario           raw agreement   chance agreement   kappa
  chance_agreement   0.82            0.82               0.00
  real_agreement     0.94            0.72               0.79
------------------------------------------------------------------
  both scenarios have high raw agreement; only kappa separates real from chance.
```

By raw agreement both pairs look good: 0.82 and 0.94, the kind of numbers a report would call "high inter-rater agreement." Kappa tells them apart completely. The chance pair's kappa is 0.00: its observed agreement (0.82) exactly equals its chance agreement (0.82), so *none* of the agreement is above what two raters who each say "no" 90% of the time would produce by luck — there is no real shared judgment at all. The real pair's kappa is 0.79: its observed 0.94 sits well above its chance 0.72, so most of the agreement is genuine. A raw-agreement report would rank these two labeling processes as roughly comparable (0.82 vs 0.94, both "high"); kappa reveals one is worthless and the other is strong. This is exactly the situation in LLM evaluation when a judge is scored against gold on a skewed label — a high match rate can be almost entirely the base rate.

<svg role="img" aria-label="As the common class grows from balanced to very imbalanced, the chance agreement floor rises toward 1, so more and more raw agreement is free" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the more imbalanced the labels, the higher the chance floor</text>
  <line x1="34" y1="90" x2="290" y2="90" stroke="var(--line)"/>
  <line x1="34" y1="24" x2="34" y2="90" stroke="var(--line)"/>
  <text x="28" y="28" fill="var(--muted)" font-size="7" text-anchor="end">1.0</text>
  <text x="28" y="60" fill="var(--muted)" font-size="7" text-anchor="end">.5</text>
  <text x="40" y="102" fill="var(--muted)" font-size="7">50/50</text><text x="240" y="102" fill="var(--muted)" font-size="7">95/5</text>
  <path d="M40,57 Q150,40 270,27" fill="none" stroke="var(--s2)"/>
  <text x="150" y="44" fill="var(--muted)" font-size="7">chance agreement floor</text>
  <circle cx="230" cy="30" r="3" fill="var(--s2)"/><text x="180" y="24" fill="var(--muted)" font-size="6">90/10 → .82 free</text>
  <text x="40" y="82" fill="var(--muted)" font-size="7">raw agreement above this line is the only part that counts</text>
</svg>
^ At balanced labels chance agreement is around 0.5, but as the common class dominates the chance floor climbs toward 1 (0.82 at a 90/10 split), so on skewed data most of any raw agreement is free and only the sliver above the floor reflects real judgment.

## Build

The chance pair's zero kappa is not a quirk; it is arithmetic you can trace. Run `--explain`.

```text filename=--explain
EXPLAIN — why the chance scenario's 0.82 agreement is all chance
--------------------------------------------------------------
  rater 1 says 'yes' 10% of the time, 'no' 90%
  rater 2 says 'yes' 10% of the time, 'no' 90%
  so by chance they both say 'no' 90% x 90% = 81% of the time,
  plus both 'yes' 10% x 10% = 1% -> chance agreement 0.82
--------------------------------------------------------------
  observed agreement (0.82) equals chance agreement (0.82), so kappa = 0.
```

Both raters say "no" 90% of the time. If their answers were completely independent — no shared understanding whatsoever — they would still both say "no" on 0.90 × 0.90 = 81% of items, and both say "yes" on 0.10 × 0.10 = 1%, for 82% agreement by chance alone. The pair's actual agreement is also 82%, so they are agreeing at exactly the rate two independent "no"-leaning raters would, and kappa correctly reports 0: the 82% is entirely the base rate leaking through, not a signal that the raters understand the task the same way. This is why raw agreement is dangerous on skewed data — the more imbalanced the labels, the higher the chance floor, so the more raw agreement you get for free and the more it overstates reliability. Kappa measures the distance above that floor.

```python filename=modules/evals-and-statistics/code/kappa-inter-01/kappa.py:104-111 COMPLETE
    both_raw_high = observed_agreement(ch) >= 0.8 and observed_agreement(re) >= 0.8
    print("  both scenarios have raw agreement >= 0.80 = %s (%.2f, %.2f)" % (both_raw_high, observed_agreement(ch), observed_agreement(re)))

    chance_kappa_zero = abs(kappa(ch)) < 1e-9
    print("  the chance scenario's kappa is 0 = %s (%.2f)" % (chance_kappa_zero, kappa(ch)))

    real_kappa_high = kappa(re) > 0.7
    print("  the real scenario's kappa is high = %s (%.2f)" % (real_kappa_high, kappa(re)))
```

<svg role="img" aria-label="Two scenarios: both have high raw agreement bars (0.82 and 0.94) but the chance scenario's kappa bar is 0 while the real scenario's kappa bar is 0.79" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">same-ish raw agreement, opposite kappa</text>
  <line x1="34" y1="96" x2="290" y2="96" stroke="var(--line)"/>
  <text x="28" y="30" fill="var(--muted)" font-size="7" text-anchor="end">1.0</text>
  <g transform="translate(60,0)">
  <text x="0" y="108" fill="var(--muted)" font-size="7">chance</text>
  <rect x="0" y="34" width="26" height="62" fill="var(--s1)"/><text x="0" y="30" fill="var(--muted)" font-size="6">raw .82</text>
  <rect x="30" y="96" width="26" height="0.6" fill="var(--s2)"/><text x="30" y="92" fill="var(--muted)" font-size="6">kappa 0</text>
  </g>
  <g transform="translate(180,0)">
  <text x="0" y="108" fill="var(--muted)" font-size="7">real</text>
  <rect x="0" y="25" width="26" height="71" fill="var(--s1)"/><text x="0" y="21" fill="var(--muted)" font-size="6">raw .94</text>
  <rect x="30" y="36" width="26" height="60" fill="var(--s2)"/><text x="30" y="32" fill="var(--muted)" font-size="6">kappa .79</text>
  </g>
</svg>
^ Both scenarios show a tall raw-agreement bar, but the chance scenario's kappa is flat at 0 while the real scenario's kappa stands at 0.79 — the chance-correction is what exposes that one pair's agreement is entirely the base rate.

## Definition of done

The self-test pins the high raw agreement in both, the zero kappa for chance, the high kappa for real, and the formula. Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — raw agreement is high in both scenarios; the chance scenario's kappa is ~0 while the real one's is high; kappa = (po-pe)/(1-pe)
------------------------------------------------------------------------------------------------------------------------------------
  both scenarios have raw agreement >= 0.80 = True (0.82, 0.94)
  the chance scenario's kappa is 0 = True (0.00)
  the real scenario's kappa is high = True (0.79)
  raw agreement separates them less than kappa does = True (raw gap 0.12 vs kappa gap 0.79)
  kappa equals (observed - chance) / (1 - chance) = True
```

**Done means the chance-inflation and its correction are proven on real counts: both rater-pairs reach high raw agreement (0.82 and 0.94), yet the chance pair's kappa is 0.00 (observed equals chance) while the real pair's is 0.79, and the raw-agreement gap (0.12) is far smaller than the kappa gap (0.79) — so kappa, not raw agreement, is the metric that reveals whether agreement is real or just the base rate.**

## Boss fight

Predict two ways kappa is subtler than "always report kappa," because kappa has its own pathologies and the right agreement metric depends on the labels.

The first trap is that kappa itself is distorted by prevalence and by rater bias — the "kappa paradoxes" — so a low kappa does not always mean poor raters. When one class is extremely rare, kappa can be low even when raw agreement is very high and the raters are genuinely careful, simply because there is almost no room above the sky-high chance floor (the prevalence problem); and when the two raters have very different overall yes-rates, kappa can be artificially depressed (the bias problem). So a kappa of 0.4 on a 99%-negative dataset may reflect an unavoidably high chance baseline rather than sloppy labeling, and comparing kappa across datasets with very different prevalence can mislead in the other direction from raw agreement. The practical response is to report kappa alongside the raw agreement and the marginal rates (so a reader can see the prevalence and bias), and to consider prevalence-adjusted variants (PABAK) or to recognize that on extremely skewed labels the informative metric may be per-class (precision/recall on the rare class, from the class-imbalance module) rather than a single agreement number.

The second trap is that Cohen's kappa is specifically two raters and nominal (unordered) categories, and using it outside those bounds is a modeling error. For ordinal labels (a 1–5 quality rating) plain kappa treats a 1-vs-2 disagreement as exactly as bad as a 1-vs-5 disagreement, which throws away the ordering — weighted kappa, which penalizes far-apart disagreements more, is the right tool. For more than two raters, or raters who did not all label every item, Cohen's kappa does not apply and you need Fleiss's kappa or Krippendorff's alpha (which also handles missing data and multiple scales). And for an LLM-judge evaluation specifically, agreement with a single human gold is only as good as that gold: if the humans themselves disagree (a low human-human kappa), then a judge's agreement with one human is capped by the task's inherent ambiguity, so you should measure human-human kappa first to establish the ceiling, then measure judge-human kappa against it — a judge that matches humans as well as humans match each other is as good as the label allows, and asking for more is asking to overfit noise. The metric must match the number of raters, the label type, and the reliability of the reference itself.

**Kappa fixes raw agreement's chance inflation but has its own prevalence and bias paradoxes (report it with raw agreement and marginals, and consider per-class metrics on very skewed labels), and it is only for two raters on nominal labels — use weighted kappa for ordinal scales, Fleiss's kappa or Krippendorff's alpha for many raters, and establish the human-human agreement ceiling before judging an LLM judge's agreement against a single gold.**

## External resources

Any measurement or annotation-reliability reference on Cohen's kappa — the (p_o − p_e)/(1 − p_e) formula, the prevalence and bias paradoxes, and weighted kappa / Fleiss's kappa / Krippendorff's alpha for ordinal labels and multiple raters.

Writing on LLM-as-judge evaluation and inter-annotator agreement — why raw match rate against gold overstates reliability on skewed labels, and why the human-human agreement ceiling bounds how good a judge can look.

The companion judge-noise and class-imbalance modules in this topic — kappa measures agreement corrected for chance, judge-noise measures the variance of a single judge, and on very skewed labels per-class precision/recall is often more informative than any single agreement number.
