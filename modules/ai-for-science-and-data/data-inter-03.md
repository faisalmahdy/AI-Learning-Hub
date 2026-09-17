---
id: data-inter-03
title: A 99% detector that is mostly wrong when it fires — the base-rate fallacy
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 8-10h
summary: A detector that is 99% sensitive and 95% specific sounds excellent, but on a population where the target is 1% prevalent it flags 5940 people of whom only 990 are real — precision 16.7%, because 5% of the huge negative population (4950 false alarms) dwarfs 99% of the tiny positive one. Precision is not a property of the detector; it is a property of the detector and the prevalence together, and the same detector climbs from 1.9% precision at 0.1% prevalence to 95% at 50%. Alongside sits the accuracy trap: at 1% prevalence a model that flags nothing scores 99% accuracy, beating the real detector's 95%, because accuracy rewards predicting the majority class — so on rare events accuracy actively prefers a useless model.
eli5: Imagine a rare disease that one in a hundred people have, and a very good test that is right 95 to 99 percent of the time. If you test everyone, most of the people the test says are sick are actually fine — because there are so many healthy people that even a small mistake rate produces more false alarms than there are truly sick people. And a lazy test that just says "healthy" to everyone looks 99 percent accurate while helping nobody. Rare things break your intuition about good tests.
---

## Why this module

Most of the events an AI system is asked to detect are rare: fraud in a stream of legitimate transactions, a defect on a line of good parts, abuse in a feed of normal posts, a disease in a screened population. Rarity changes the arithmetic of a classifier so profoundly that the metrics practitioners reach for by reflex — sensitivity, specificity, accuracy — give a dangerously wrong picture of how the detector performs in the wild. This module builds a detector everyone would sign off on, points it at a rare event, and measures the two ways the intuition fails: the false alarms swamp the true ones, and the headline accuracy metric rewards a model that does nothing.

The first failure is the base-rate fallacy. Sensitivity and specificity are properties of the detector alone — they do not depend on how common the target is. Precision, the fraction of flags that are real, is not: it depends on the base rate. When positives are 1% of a population, a 95% specificity means 5% of the other 99% get falsely flagged, and 5% of a large number is far more than 99% of a small one, so most flags are false. No improvement to the detector's own quality escapes this; only the prevalence changes it. The second failure is the accuracy trap. On rare events, always predicting the majority class — flag nothing — scores an accuracy equal to one minus the prevalence, which is high, often higher than a real detector that pays false positives to catch the rare true ones. Accuracy prefers the useless model, so it is the wrong metric to optimize or report.

You need no prior module, only what a false positive and a false negative are. Everything runs offline against a screening fixture — a population, a prevalence, a detector's sensitivity and specificity — stdlib Python 3, `$0.00`. The instinct to unlearn is that a high-sensitivity, high-specificity detector is a high-precision detector. Precision is set by the detector and the base rate together, and on a rare event the base rate wins.

Here is the excellent detector on a rare event:

```
# modules/ai-for-science-and-data/code/data-inter-03/ — COMPLETE, run from that directory
$ python3 baserate.py --matrix

MATRIX — 100000 people, 1% prevalence, 99% sensitive, 95% specific
------------------------------------------------------------------
  true positives  (real, flagged)   =    990
  false negatives (real, missed)    =     10
  false positives (fine, flagged)   =   4950
  true negatives  (fine, cleared)   =  94050
  precision (PPV) = 16.7%  <- of everything flagged, this fraction is real
  recall          = 99.0%   accuracy = 95.0%
```

run: 2026-08-26 · deterministic; rates are a fixture · 100000 people · `python3 baserate.py --matrix`

Ninety-nine percent sensitive, ninety-five percent specific — and yet only 16.7% of the people it flags are real, because 4950 false positives bury 990 true ones. This module is where that 16.7% comes from and why the detector's quality cannot fix it.

## Concepts

Named here so you can find them again; each is built below.

- **Prevalence (base rate)** — how common the target is in the population.
- **Sensitivity** — of the true positives, the fraction the detector flags; a detector property.
- **Specificity** — of the true negatives, the fraction the detector clears; a detector property.
- **Precision (PPV)** — of everything flagged, the fraction that is real; depends on the base rate.
- **The base-rate fallacy** — assuming high sensitivity/specificity means high precision; it does not.
- **The accuracy trap** — on rare events, flag-nothing scores high accuracy while finding nothing.

## Worked example

Source: the base-rate reasoning behind every rare-event screening system (medical testing, fraud detection, content moderation, anomaly detection), worked through a confusion matrix; the population and rates here stand in for a real deployment so the counts and precision are exact and checkable.

Script and fixture: `modules/ai-for-science-and-data/code/data-inter-03/` — `baserate.py`, and `screen.json`, a population of 100000, 1% prevalence, a 99%/95% detector. Every command runs from there.

### The confusion matrix: where the flags come from

Everything follows from four counts. Split the population into positives and negatives by prevalence, then apply the detector's rates to each.

```
# baserate.py:42-50 — COMPLETE (the four cells of the confusion matrix)
def confusion(population, prevalence, sensitivity, specificity):
    """Return TP, FN, FP, TN for a detector on this population and prevalence."""
    positives = population * prevalence
    negatives = population - positives
    tp = positives * sensitivity
    fn = positives - tp
    tn = negatives * specificity
    fp = negatives - tn
    return tp, fn, fp, tn
```

With 100000 people at 1% prevalence there are 1000 positives and 99000 negatives. The detector catches 99% of the 1000 — 990 true positives, 10 missed. It clears 95% of the 99000 — but the other 5% is 4950 false positives. That asymmetry is the whole story: 5% of 99000 is 4950, five times the 990 real cases, because the negative pool is a hundred times larger than the positive one. The false-positive count is driven by the size of the negative population, which prevalence makes enormous.

<svg viewBox="0 0 700 200" role="img" aria-label="A confusion matrix as areas. A huge block of 99000 negatives dominates the picture; 5% of it (4950) is shaded as false positives. A tiny block of 1000 positives sits beside it; 990 of it is true positives. The false-positive shaded area is visibly five times the true-positive area.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">1000 positives vs 99000 negatives — 5% of the big block swamps the small one</text>
    <rect x="40" y="40" width="70" height="120" fill="var(--panel)" stroke="var(--line)"></rect>
    <rect x="40" y="40" width="70" height="119" fill="var(--s1)"></rect>
    <text x="75" y="175" text-anchor="middle" fill="var(--s1)" font-size="8">990 TP</text>
    <text x="75" y="35" text-anchor="middle" fill="var(--muted)" font-size="8">1000 positive</text>
    <rect x="180" y="40" width="470" height="120" fill="var(--panel)" stroke="var(--line)"></rect>
    <rect x="180" y="40" width="470" height="114" fill="none"></rect>
    <rect x="180" y="148" width="470" height="12" fill="var(--s2)"></rect>
    <text x="415" y="100" text-anchor="middle" fill="var(--muted)" font-size="8">94050 TN (95% of negatives)</text>
    <text x="415" y="175" text-anchor="middle" fill="var(--s2)" font-size="8">4950 FP (5% of negatives) — five times the TP block</text>
    <text x="415" y="35" text-anchor="middle" fill="var(--muted)" font-size="8">99000 negative</text>
  </g>
</svg>
^ The flags are the true-positive sliver plus the false-positive strip, and the strip is five times the sliver because it is 5% of a population a hundred times larger. Precision is the sliver over sliver-plus-strip — 990 of 5940.

### Precision: a property of the detector and the base rate

Precision is the fraction of flags that are real — true positives over everything flagged.

```
# baserate.py:53-55 — COMPLETE (precision / positive predictive value)
def precision(tp, fp):
    """PPV: of everything flagged, the fraction that is truly positive."""
    return tp / (tp + fp) if (tp + fp) else 0.0
```

Here that is 990 / (990 + 4950) = 16.7%. Notice what precision does not mention: sensitivity and specificity went into the counts, but the number that matters to a person who receives a flag — "is this real?" — is 16.7%, not 99% and not 95%. Sweep the prevalence and watch precision move while the detector stays frozen:

```
# $ python3 baserate.py --sweep
#   prevalence   flagged   true   false   precision
#   0.1%            5094     99    4995   1.9%
#   1.0%            5940    990    4950   16.7%
#   5.0%            9700   4950    4750   51.0%
#   10.0%          14400   9900    4500   68.8%
#   50.0%          52000  49500    2500   95.2%
```

run: 2026-08-26 · deterministic · `python3 baserate.py --sweep`

The detector is byte-for-byte identical at every row — 99% sensitive, 95% specific throughout. Precision alone swings from 1.9% to 95.2% purely because the base rate moved. At 0.1% prevalence, 98 of every 100 flags are false; at 50%, 95 of 100 are real. This is the proof that precision is not a detector property: nothing about the detector changed across those rows, and precision changed by a factor of fifty.

<svg viewBox="0 0 700 180" role="img" aria-label="A rising curve of precision against prevalence. At 0.1% prevalence precision is near 2%, at 1% it is 17%, at 5% it is 51%, at 10% it is 69%, at 50% it is 95%. The curve rises steeply from near zero and flattens high.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">precision vs prevalence — same detector, base rate alone moves it</text>
    <line x1="60" y1="150" x2="650" y2="150" stroke="var(--grid)"></line>
    <line x1="60" y1="30" x2="60" y2="150" stroke="var(--grid)"></line>
    <polyline points="70,147 130,122 250,76 370,53 640,43" fill="none" stroke="var(--s1)" stroke-width="2.5"></polyline>
    <circle cx="70" cy="147" r="3" fill="var(--s1)"></circle><circle cx="130" cy="122" r="3" fill="var(--s1)"></circle><circle cx="250" cy="76" r="3" fill="var(--s1)"></circle><circle cx="370" cy="53" r="3" fill="var(--s1)"></circle><circle cx="640" cy="43" r="3" fill="var(--s1)"></circle>
    <g fill="var(--muted)" font-size="8"><text x="66" y="163">0.1%</text><text x="120" y="163">1%</text><text x="240" y="163">5%</text><text x="360" y="163">10%</text><text x="628" y="163">50%</text></g>
    <g fill="var(--muted)" font-size="8"><text x="80" y="147">1.9%</text><text x="140" y="120">17%</text><text x="260" y="74">51%</text><text x="380" y="51">69%</text><text x="600" y="40">95%</text></g>
  </g>
</svg>
^ The detector is fixed; the curve is entirely the base rate's doing. A rare-event deployment lives at the steep left end, where precision is low no matter how good the detector is.

### The accuracy trap: rewarding the model that does nothing

Accuracy and recall are the other two rates off the same four counts:

```
# baserate.py:58-63 — COMPLETE (recall and accuracy from the confusion matrix)
def recall(tp, fn):
    return tp / (tp + fn) if (tp + fn) else 0.0


def accuracy(tp, fn, fp, tn):
    return (tp + tn) / (tp + fn + fp + tn)
```

Recall asks "of the real positives, how many did we catch"; accuracy asks "of everyone, how many did we call correctly". On a rare event those two questions pull apart hard. Compare the real detector to a model that flags nothing at all.

```
# $ python3 baserate.py --accuracy
#   real detector:  accuracy = 95.04%   recall = 99%   found 990 of 1000
#   flag nothing:   accuracy = 99.00%   recall = 0%   found 0 of 1000
```

run: 2026-08-26 · deterministic · `python3 baserate.py --accuracy`

<svg viewBox="0 0 700 175" role="img" aria-label="Two models compared on two metrics. By accuracy: flag-nothing scores 99%, higher than the real detector's 95%. By recall: the real detector scores 99%, the flag-nothing model scores 0%. Accuracy ranks them backwards; recall ranks them right.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">two models, two metrics — accuracy ranks them backwards</text>
    <text x="60" y="44" fill="var(--ink)">by accuracy</text>
    <text x="60" y="64" fill="var(--muted)" font-size="8">detector</text><rect x="150" y="56" width="380" height="12" fill="var(--s1)"></rect><text x="536" y="66" fill="var(--s1)" font-size="8">95%</text>
    <text x="60" y="82" fill="var(--muted)" font-size="8">flag-nothing</text><rect x="150" y="74" width="396" height="12" fill="var(--s2)"></rect><text x="552" y="84" fill="var(--s2)" font-size="8">99% wins</text>
    <text x="60" y="118" fill="var(--ink)">by recall</text>
    <text x="60" y="138" fill="var(--muted)" font-size="8">detector</text><rect x="150" y="130" width="396" height="12" fill="var(--s1)"></rect><text x="552" y="140" fill="var(--s1)" font-size="8">99% wins</text>
    <text x="60" y="156" fill="var(--muted)" font-size="8">flag-nothing</text><rect x="150" y="148" width="2" height="12" fill="var(--s2)"></rect><text x="160" y="158" fill="var(--s2)" font-size="8">0%</text>
  </g>
</svg>
^ By accuracy the flag-nothing model edges ahead; by recall it collapses to zero while the detector holds at 99%. The metric you pick decides which model you ship, and only one of these metrics is honest about a detector that finds nothing.

The flag-nothing model is 99% accurate — higher than the real detector's 95% — because it correctly clears all 99000 negatives and simply pays for the 1000 positives it misses, and at 1% prevalence that is a cheap price by accuracy. The real detector scores lower on accuracy precisely because it accepts 4950 false positives to catch 990 true ones. If you ranked these two models by accuracy, you would pick the one that finds nothing. Accuracy on a rare event is not merely uninformative; it is inverted, preferring the useless model, which is why precision and recall — not accuracy — are the metrics for imbalanced problems.

**Precision is a property of the detector and the base rate together, not the detector alone, so a 99%/95% detector flags mostly false positives on a rare event — and accuracy compounds the trap by scoring a flag-nothing model above a real one, because it rewards predicting the majority class.**

### The self-test

The `--check` mode asserts both failures: precision is low and far below sensitivity, and the flag-nothing baseline beats the detector on accuracy while finding nothing.

```
# $ python3 baserate.py --check
#   precision is low at 1% prevalence = True (16.7% flagged are real)
#   precision << sensitivity = True (16.7% vs 99%)
#   flag-nothing accuracy beats the detector = True (99.00% > 95.04%)
#   ...but flag-nothing has 0% recall (finds nothing) = True
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 baserate.py --check`

The `base_rate_dominates` line is the anchor: it requires precision to sit far below sensitivity, encoding the fact that the base rate, not the detector, set the precision. The `accuracy_trap` line turns the second failure into a guardrail — it asserts the flag-nothing model actually out-scores the detector on accuracy, so anyone tempted to optimize accuracy on this problem is confronted with the model it would choose.

### The running tally

| model / setting | precision | recall | accuracy |
|---|---|---|---|
| detector @ 1% prevalence | 16.7% | 99% | 95.0% |
| detector @ 50% prevalence | 95.2% | 99% | — |
| flag nothing @ 1% | undefined (0 flags) | 0% | 99.0% |

The first two rows are the same detector at two base rates, and precision alone separates them — the base-rate fallacy in one comparison. The first and third rows are two models at the same base rate, and accuracy ranks them backwards while recall and precision rank them right — the accuracy trap in one comparison. Report precision and recall on rare events; accuracy will lie to you, and the base rate will make a great detector look like a false-alarm machine unless you state the prevalence alongside it.

### What we did not settle

The confusion matrix is the start of imbalanced-classification practice, not the end. The precision-recall tradeoff is tunable: moving the decision threshold trades false positives against false negatives, and the PR curve (not the ROC curve, which looks deceptively good under imbalance) is how you choose. F-scores combine precision and recall into one number when you must rank. The cost of a false positive versus a false negative is usually asymmetric — a missed fraud versus an annoyed customer — and the right operating point weights them, which is decision theory, not just statistics. And prevalence is often estimated, so precision inherits that uncertainty. The base-rate reasoning here is the floor beneath all of it: know the prevalence, and never read precision off the detector's specs.

## Build

The practice in one paragraph: before trusting any detector, find the base rate of what it detects; compute the full confusion matrix at that prevalence, not on a balanced test set; report precision and recall, never accuracy, on imbalanced problems; and always compare against the flag-nothing (and flag-everything) baselines, so the accuracy trap is visible. State the prevalence next to every precision number, because the same detector has a different precision at every base rate.

We opened on the matrix. The number that tells a flagged person what to believe is precision:

```
# modules/ai-for-science-and-data/code/data-inter-03/ — COMPLETE, run from that directory
$ python3 baserate.py --sweep
  0.1%   ... precision 1.9%
  50.0%  ... precision 95.2%
```

Now do it to your own detector. Take a real classifier and the true prevalence of its target, build the confusion matrix at that prevalence, and compute precision, recall, and accuracy. Your number to beat is not accuracy; it is **precision at the true base rate, next to the flag-nothing accuracy baseline** — if flag-nothing's accuracy beats your model's, you have proven why accuracy is the wrong metric here. Sweep the prevalence and watch precision move with the detector frozen. Bring back precision at the real base rate and the two accuracies. Good luck.

## Definition of done

- [ ] The true prevalence of the target established, not assumed balanced
- [ ] A full confusion matrix computed at that prevalence from the detector's rates
- [ ] Precision, recall, and accuracy all reported
- [ ] A prevalence sweep showing precision move while the detector is fixed
- [ ] The flag-nothing baseline computed, with its accuracy compared to the detector's
- [ ] Confirmation that precision is far below sensitivity and that accuracy prefers the useless model
- [ ] `python3 baserate.py --check` printing SELF-TEST PASS: ppv-low, base-rate-dominates, accuracy-trap, nothing-useless
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. A detector is 99% sensitive and 95% specific. Why can its precision still be 17%, and which quantity outside the detector sets that?
2. Sensitivity and specificity did not change across the prevalence sweep, but precision swung from 2% to 95%. Explain why precision is not a detector property.
3. At 1% prevalence a model that flags nothing is 99% accurate. Explain the accuracy trap and why accuracy is the wrong metric on rare events.
4. Which metrics should you report instead on an imbalanced problem, and why do they rank the flag-nothing model correctly?
5. Your own detector was evaluated at its true base rate. What was its precision, and did the flag-nothing baseline beat it on accuracy?

## External resources

- Wikipedia / standard references, *Base rate fallacy* and *Positive predictive value* — my summary: the formal statement that PPV depends on prevalence, with the classic medical-screening worked example this module mirrors; read it for the Bayesian derivation of precision from sensitivity, specificity, and base rate.
- *The Relationship Between Precision-Recall and ROC Curves* (Davis & Goadrich, 2006) — https://www.biostat.wisc.edu/~page/rocpr.pdf — my summary: why ROC/AUC looks good under class imbalance while PR curves tell the truth; read it for the next step past a single operating point — choosing a threshold on a rare-event problem.
- This hub, *data-inter-02* — modules/ai-for-science-and-data/data-inter-02.md — my summary: the other data module where a single reflexive summary statistic (the mean) misleads on a skewed distribution; read it for the shared discipline — match the metric to the question, and never trust a headline number that hides the structure beneath it.
