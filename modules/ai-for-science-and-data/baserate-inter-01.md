---
id: baserate-inter-01
title: A 99% test for a 1% disease is right about a positive only half the time — the base rate, not the accuracy, decides
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 16 min
summary: Ask most people — a test is 99% accurate, you test positive for a disease, how likely is it that you have it? — and they answer 99%. For a disease that 1% of people have, the correct answer is 50%, and the gap is the most consequential mistake in reading any classifier for a rare event. The intuition confuses P(positive | disease), the sensitivity, with P(disease | positive), the thing you want, and those are only equal when the disease is as common as its absence; when the event is rare they diverge, because the answer depends on the base rate the intuition leaves out. Count people: in 100,000 with a 1% disease, 1,000 are sick and 99,000 healthy; a 99%-sensitivity test flags 990 of the sick (true positives), and a 99%-specificity test's 1% false-positive rate flags 990 of the 99,000 healthy (false positives) — so 1,980 positives, exactly half real. The healthy group is ninety-nine times larger, so even a tiny error rate on it produces as many positives as the accurate test does on the few who are sick. Sweeping the base rate with the same 99%/99% test shows it driving the answer: PPV is 9% at 0.1% prevalence, 50% at 1%, and 92% at 10%. The fixes are to reason in natural frequencies (990 vs 990), apply Bayes, and confirm rare-event positives with a second independent test.
eli5: Imagine a huge stadium of 100,000 people, and 1,000 of them secretly have a rare cold. You have a pretty good cold-detector that's right 99 times out of 100. It correctly beeps at almost all 1,000 sick people — but it also mistakenly beeps at 1 out of every 100 healthy people, and there are 99,000 healthy people, so that's about 990 false beeps too. Now the detector beeps at YOU. Are you sick? There are about 990 real cases and 990 false alarms beeping, so it's a coin flip — even though the detector is "99% accurate." When the thing you're hunting for is rare, most of the alarms come from the enormous crowd that doesn't have it.
---

## Why this module

Test accuracy is quoted as a single impressive number, and everyone reads a positive result as if that number were the answer. It is not. For anything rare — a disease, fraud, a defect, a flagged account — a positive from a 99% test can be a coin flip, because the population that does *not* have the condition is so much larger that its rare mistakes flood the results. Getting this backwards is how confident, accurate-sounding tests produce mostly false alarms.

Ask most people: a test is 99% accurate, you test positive for a disease, how likely is it that you have it? The intuitive answer is 99%. The correct answer, for a disease that 1% of people have, is 50% — and the gap between those two numbers is the single most consequential mistake in reading a diagnostic test, a spam filter, a fraud flag, or any classifier for a rare event. The intuition confuses P(positive | disease), the test's sensitivity, with P(disease | positive), the thing you actually want to know, and those are only equal when the disease is as common as its absence. When the event is rare they diverge sharply, because the answer depends on the base rate — how common the disease is before any test — and the intuition simply leaves the base rate out.

Count actual people and it becomes obvious. Take 100,000 people with a 1% disease: 1,000 are sick and 99,000 are healthy. A test with 99% sensitivity flags 990 of the 1,000 sick people (true positives). The same test with 99% specificity has a 1% false-positive rate, and 1% of the 99,000 healthy people is 990 people flagged in error (false positives). So a positive comes from a sick person 990 times and a healthy person 990 times: 1,980 positives, of which exactly half are real. The false positives come from a group ninety-nine times larger than the sick group, so even a tiny false-positive rate on that huge group produces as many positives as the accurate test does on the few who are sick. This module counts the positives and sweeps the base rate.

**For a rare condition, P(disease | positive) depends on the base rate, not just the test accuracy, so a 99%-accurate test for a 1%-prevalence disease has a positive predictive value of only 50% — the huge healthy group's false positives match the sick group's true positives — and the answer is only trustworthy once the base rate is counted in.**

## Concepts

**The confusion counts** are Bayes as a headcount: split the population into sick and healthy, apply the sensitivity to the sick and the false-positive rate to the healthy, and you have the four cells in whole people.

```python filename=modules/ai-for-science-and-data/code/baserate-inter-01/baserate.py:49-57 COMPLETE
def confusion(population, prevalence, sensitivity, specificity):
    """Count true/false positives and negatives over a whole population -- Bayes as headcount."""
    sick = round(population * prevalence)
    healthy = population - sick
    tp = round(sick * sensitivity)
    fn = sick - tp
    fp = round(healthy * (1 - specificity))
    tn = healthy - fp
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn}
```

**The positive predictive value** is the answer to the real question — of everyone who tested positive, what fraction is actually sick — which is just the true positives over all positives.

```python filename=modules/ai-for-science-and-data/code/baserate-inter-01/baserate.py:60-63 COMPLETE
def ppv(c):
    """Positive predictive value: P(disease | positive) = true positives / all positives."""
    positives = c["tp"] + c["fp"]
    return c["tp"] / positives if positives else 0.0
```

<svg role="img" aria-label="A population of 100,000 with a 1% disease: a tiny sick group produces 990 true positives, and the vast healthy group's 1% error produces 990 false positives, so the positives are half real and half false" viewBox="0 0 300 122" width="300" height="122">
  <text x="6" y="12" fill="var(--muted)" font-size="8">1,000 sick vs 99,000 healthy — but equal positives</text>
  <rect x="10" y="22" width="10" height="10" fill="var(--s2)"/><text x="24" y="30" fill="var(--muted)" font-size="7">1,000 sick</text>
  <g transform="translate(90,22)">
  <rect x="0" y="0" width="190" height="10" fill="var(--s1)"/>
  <text x="0" y="-2" fill="var(--muted)" font-size="7">99,000 healthy (99x larger)</text>
  </g>
  <text x="10" y="60" fill="var(--muted)" font-size="7">positives:</text>
  <rect x="70" y="52" width="90" height="14" fill="var(--s2)"/><text x="74" y="62" fill="var(--panel)" font-size="7">990 true (sick)</text>
  <rect x="162" y="52" width="90" height="14" fill="var(--s1)"/><text x="166" y="62" fill="var(--panel)" font-size="7">990 false (healthy)</text>
  <text x="10" y="90" fill="var(--muted)" font-size="8">a positive is real 990 / (990 + 990) = 50% of the time</text>
  <text x="10" y="108" fill="var(--muted)" font-size="7">1% of the enormous healthy group = as many alarms as the whole sick group</text>
</svg>
^ The sick group is a sliver of the population, but the healthy group is so large that its 1% false-positive rate produces 990 false alarms — matching the 990 true positives — so half of all positives are false.

**PPV = true positives / all positives, and because the healthy group is far larger than the sick group, its false positives can equal or outnumber the true positives — so the base rate, through those counts, sets the answer, not the test's accuracy alone.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/baserate-inter-01/baserate.py

The fixture is a 99%/99% test on a 1% disease, counted over 100,000 people.

```json filename=modules/ai-for-science-and-data/code/baserate-inter-01/baserate.json:3-7 COMPLETE
  "population": 100000,
  "prevalence": 0.01,
  "sensitivity": 0.99,
  "specificity": 0.99,
  "prevalence_sweep": [0.001, 0.01, 0.1]
```

Run `--posterior` to count the positives.

```text filename=--posterior
POSTERIOR — P(disease | positive) for a 99% test on a 1% disease
------------------------------------------------------------------
  population 100000: 1000 sick, 99000 healthy
  true positives  (sick, test +)    = 990
  false positives (healthy, test +) = 990
  total positives                   = 1980
------------------------------------------------------------------
  naive answer (the sensitivity)      = 0.99
  true PPV = 990 / 1980                = 0.50  <- a positive is real only half the time
```

The two positive counts are equal — 990 true, 990 false — so a positive test is real exactly half the time, and the naive 99% answer is off by a factor of two. Trace where each 990 comes from. The 990 true positives are 99% of the 1,000 sick people: the test is genuinely accurate on the sick. The 990 false positives are 1% of the 99,000 healthy people: a small error rate, but applied to a group ninety-nine times larger. That size ratio is the whole story — 1% × 99,000 happens to equal 99% × 1,000, so the two sources of positives are balanced, and the positive tells you nothing beyond a coin flip. The number people quote, 0.99, is the test's accuracy on people whose status you already know; the number you need, 0.50, is the probability of disease given only the positive, and it can only be computed with the base rate in hand. This is not a knock on the test — 99%/99% is a very good test — it is what rarity does to any test.

<svg role="img" aria-label="A 2x2 confusion matrix for the 1% disease: 990 true positives and 10 false negatives among the sick, 990 false positives and 98010 true negatives among the healthy; the positive column is 990 plus 990" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the 2×2 counts: the positive column is half true, half false</text>
  <text x="70" y="28" fill="var(--muted)" font-size="7">test +</text><text x="170" y="28" fill="var(--muted)" font-size="7">test −</text>
  <text x="8" y="52" fill="var(--muted)" font-size="7">sick</text>
  <rect x="50" y="34" width="90" height="28" fill="var(--s2)"/><text x="66" y="52" fill="var(--panel)" font-size="8">990 TP</text>
  <rect x="146" y="34" width="120" height="28" fill="none" stroke="var(--line)"/><text x="162" y="52" fill="var(--muted)" font-size="8">10 FN</text>
  <text x="8" y="86" fill="var(--muted)" font-size="7">healthy</text>
  <rect x="50" y="68" width="90" height="28" fill="var(--s1)"/><text x="62" y="86" fill="var(--panel)" font-size="8">990 FP</text>
  <rect x="146" y="68" width="120" height="28" fill="none" stroke="var(--line)"/><text x="162" y="86" fill="var(--muted)" font-size="8">98,010 TN</text>
  <text x="50" y="112" fill="var(--muted)" font-size="7">positive column = 990 + 990 → PPV 990/1980 = 0.50</text>
</svg>
^ In the positive column the 990 true positives (sick) and 990 false positives (healthy) are equal, so PPV is 0.50; the vast 98,010 true negatives are what a high specificity buys but are irrelevant to what a positive means.

## Build

The base rate is not a footnote; it is the dominant term. Run `--prevalence` to hold the test fixed and vary only how common the disease is.

```text filename=--prevalence
PREVALENCE — the same 99%/99% test across base rates
------------------------------------------------------------
  prevalence   true pos   false pos   PPV
  0.1%         99         999         0.0902
  1.0%         990        990         0.5000
  10.0%        9900       900         0.9167
```

Same test, three diseases of different rarity, three completely different meanings for a positive. At 0.1% prevalence a positive is only 9% likely to be real — the 999 false positives swamp the 99 true ones, so ninety-one of every hundred alarms are false. At 1% it is a coin flip. At 10% it is 92% — now the sick group is large enough that its true positives dominate. The test's accuracy never changed; the only thing that moved was the base rate, and it moved the answer across almost the entire range from 0 to 1. This is why a screening test that is excellent for a common condition can be nearly useless for a rare one, and why "how accurate is the test" is the wrong first question — the right first question is "how common is what we're testing for."

```python filename=modules/ai-for-science-and-data/code/baserate-inter-01/baserate.py:114-116 COMPLETE
    ppvs = [ppv(confusion(pop, p, sens, spec)) for p in data["prevalence_sweep"]]
    ppv_rises = all(ppvs[i] < ppvs[i + 1] for i in range(len(ppvs) - 1))
    print("  PPV rises strictly with prevalence = %s (%s)" % (ppv_rises, [round(x, 3) for x in ppvs]))
```

<svg role="img" aria-label="Positive predictive value rising with prevalence: about 9% at 0.1% prevalence, 50% at 1%, and 92% at 10%, for the same 99% test" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">same 99% test — PPV climbs with the base rate</text>
  <line x1="34" y1="98" x2="290" y2="98" stroke="var(--line)"/>
  <line x1="34" y1="20" x2="34" y2="98" stroke="var(--line)"/>
  <text x="28" y="24" fill="var(--muted)" font-size="7" text-anchor="end">100%</text>
  <text x="28" y="62" fill="var(--muted)" font-size="7" text-anchor="end">50%</text>
  <text x="28" y="98" fill="var(--muted)" font-size="7" text-anchor="end">0</text>
  <g transform="translate(0,0)">
  <rect x="70" y="91" width="30" height="7" fill="var(--s2)"/><text x="66" y="110" fill="var(--muted)" font-size="7">0.1%</text><text x="72" y="88" fill="var(--muted)" font-size="6">9%</text>
  <rect x="150" y="59" width="30" height="39" fill="var(--s1)"/><text x="150" y="110" fill="var(--muted)" font-size="7">1%</text><text x="152" y="56" fill="var(--muted)" font-size="6">50%</text>
  <rect x="230" y="26" width="30" height="72" fill="var(--s1)"/><text x="226" y="110" fill="var(--muted)" font-size="7">10%</text><text x="230" y="23" fill="var(--muted)" font-size="6">92%</text>
  </g>
</svg>
^ Holding the 99%/99% test fixed and raising only the prevalence lifts the positive predictive value from 9% to 50% to 92% — the base rate, not the accuracy, is what a positive result's meaning tracks.

## Definition of done

The self-test pins the equal counts, the 0.50 PPV, the overstated naive answer, and the base-rate dependence.

```python filename=modules/ai-for-science-and-data/code/baserate-inter-01/baserate.py:104-112 COMPLETE
    fp_equals_tp = c["fp"] == c["tp"]
    print("  at 1%% prevalence the false positives equal the true positives = %s (%d == %d)" % (fp_equals_tp, c["fp"], c["tp"]))

    ppv_is_half = abs(ppv(c) - 0.5) < 1e-9
    print("  so PPV = P(disease | positive) is 0.50 = %s (%.4f)" % (ppv_is_half, ppv(c)))

    naive_overstates = sens - ppv(c) > 0.4
    print("  the naive answer (the %.2f sensitivity) overstates PPV by far = %s (%.2f vs %.2f)"
          % (sens, naive_overstates, sens, ppv(c)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — false positives equal true positives at 1% prevalence, so PPV is 0.50 not 0.99; PPV rises with prevalence
------------------------------------------------------------------------------------------------------------------------
  at 1% prevalence the false positives equal the true positives = True (990 == 990)
  so PPV = P(disease | positive) is 0.50 = True (0.5000)
  the naive answer (the 0.99 sensitivity) overstates PPV by far = True (0.99 vs 0.50)
  PPV rises strictly with prevalence = True ([0.09, 0.5, 0.917])
  the four cells sum to the whole population = True (100000)
```

**Done means the base-rate effect is proven on real counts: at 1% prevalence the 99%/99% test produces 990 true and 990 false positives, so PPV is exactly 0.50 (not the 0.99 sensitivity), and holding the test fixed while raising prevalence lifts PPV strictly from 0.09 to 0.50 to 0.92 — with the four confusion cells summing to the whole population — so a positive's meaning is set by the base rate, not the accuracy.**

## Boss fight

Predict two ways this is even sharper than the single number suggests, because the base rate hides in more places than a disease's prevalence.

The first trap is that the "base rate" is whatever the true prior is for the specific case in front of you, and using the wrong reference class silently corrupts the answer. Population prevalence is the right prior for random screening, but the moment you test a *selected* group — people with symptoms, a transaction already flagged by a rule, a subpopulation with higher risk — the relevant base rate is that group's rate, which can be far higher, so the same test is far more predictive there than in the general population. This is exactly why doctors test based on symptoms rather than screening everyone: the pre-test probability from symptoms raises the base rate, which raises the PPV. The same logic runs in reverse for automated screening that casts a wide net — a fraud model run on all transactions faces the population base rate (mostly legitimate), so it drowns in false positives, while the same model run only on already-suspicious transactions performs far better. Choosing the base rate is choosing the reference class, and the reference class is a modeling decision, not a given.

The second trap is that the costs of the two errors are usually asymmetric, so the "best" operating point is not the one that maximizes accuracy, and the base rate interacts with that too. A false negative on a serious disease (missing it) and a false positive (a scare and a follow-up test) are not equally bad, so you tune the threshold to trade sensitivity against specificity deliberately — and at a low base rate, buying more sensitivity is cheap in true positives and expensive in false positives, because every point of false-positive rate is multiplied by the huge healthy group. This is why rare-event screening is designed as a *pipeline*: a cheap, high-sensitivity first test that accepts many false positives to miss few true cases, followed by a more specific (often more expensive) confirmatory test applied only to the positives — where the base rate is now much higher, because the first test raised it, so the second test's PPV is high. One test cannot beat a bad base rate, but each test updates the base rate for the next, which is Bayes applied twice. And the deepest point is that accuracy alone is never a sufficient description of a classifier for a rare event: you must report the base rate, the two error rates separately, and the resulting predictive values, because a single "99% accurate" can hide a coin-flip PPV or a flood of false alarms.

**The relevant base rate is the prior for the specific case, so testing a selected, higher-risk group (symptoms, a prior flag) is far more predictive than population screening — the reference class is a modeling choice — and because the two errors are usually asymmetric and false positives are multiplied by the large negative group, rare-event detection is built as a pipeline of tests, each raising the base rate for the next (Bayes applied repeatedly); accuracy alone never describes such a classifier, so always report the base rate, both error rates, and the predictive values.**

## External resources

Any introduction to Bayes' theorem and diagnostic testing — the confusion matrix, sensitivity/specificity versus positive/negative predictive value, and the natural-frequency framing (counting people) that makes base-rate reasoning intuitive.

Gerd Gigerenzer's work on risk communication and "Calculated Risks" — why natural frequencies beat conditional probabilities for teaching base-rate reasoning, and how doctors and patients routinely misread test results.

The companion conjunction-fallacy and Simpson's-paradox modules in this topic — all three are cases where an intuitive read of probabilities is confidently wrong, here because the base rate that dominates the answer is the term the intuition omits.
