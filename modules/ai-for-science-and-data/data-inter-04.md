---
id: data-inter-04
title: Test twenty hypotheses at p<0.05 and a false discovery is more likely than not
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 8-10h
summary: A p-value below 0.05 allows a 5% false-positive rate per test, so across 20 tests where every hypothesis is null you expect one spurious "significant" result by chance — and here two of twenty null p-values fall below 0.05, exactly what noise produces. The probability of at least one false positive across 20 independent null tests is 1 minus 0.95 to the 20th, which is 64%, more likely than not, and climbs to 92% at 50 tests. Bonferroni correction divides alpha by the number of tests, dropping the threshold to 0.0025, which the smallest p-value of 0.030 does not clear, so the corrected analysis makes zero discoveries — the right answer, because there was nothing to find. A significant result selected from many tests is not evidence until you correct for how many you ran.
eli5: If you flip twenty coins and one lands on its edge, that is not a miracle — with enough coins something odd is bound to happen. Running lots of experiments and reporting the one that looked significant is the same trick: with twenty tries, one will look special by pure luck even if nothing real is going on. The honest fix is to demand much stronger evidence the more things you test.
---

## Why this module

You generated real datasets, and the temptation with real data is to ask it many questions: does the effect show up by cohort, by day, by segment, by feature. Every one of those questions is a hypothesis test, and every test has a false-positive rate. Ask enough questions and one will answer "yes" by chance alone, even when the true answer to all of them is "no". This module measures that failure directly — twenty tests of hypotheses that are all null — and builds the correction that keeps a multi-test analysis honest. It is the statistical mistake most likely to turn your own data science into confident nonsense.

The mechanism is just arithmetic on the significance threshold. A p-value below 0.05 means data this extreme occurs less than 5% of the time under the null, so a single test at 0.05 has a 5% false-positive rate. Run twenty independent tests and you expect 5% of twenty — one — to cross the line by chance. The probability of getting at least one false positive is worse than the expectation suggests: 1 minus 0.95 to the twentieth power, which is 64%, so a spurious "significant" result is more likely than not. Reporting the one test that crossed 0.05, out of many you ran, is p-hacking, whether you did it deliberately or just by exploring. The fix is to make the threshold stricter as the number of tests grows: Bonferroni divides alpha by the number of tests, so the family-wise error rate — the chance of any false positive across the whole family — stays at your intended alpha instead of ballooning to 64%.

You need no prior module, only that a p-value is a false-positive rate under the null. Everything runs offline against a p-value fixture — twenty tests, every hypothesis null — stdlib Python 3, `$0.00`. Because the truth here is that nothing is real, every "discovery" the naive analysis makes is by construction a false one, which is what makes the correction's job checkable. The instinct to unlearn is that a p below 0.05 is a discovery. It is a discovery per test; across many tests it is an expectation, and the count of them matches pure chance.

Here are the naive "discoveries" from twenty null tests:

```
# modules/ai-for-science-and-data/code/data-inter-04/ — COMPLETE, run from that directory
$ python3 phack.py --naive

NAIVE — 'significant' at p < 0.05, across 20 all-null tests
------------------------------------------------------------------
  test  0: p = 0.030  <-- called significant
  test  1: p = 0.048  <-- called significant
  found 2 'discoveries'; chance alone predicts 1.0 false positive(s).
  every hypothesis here is null -- these are noise.
```

run: 2026-08-26 · deterministic; p-values are a fixture · 20 tests · `python3 phack.py --naive`

<svg viewBox="0 0 700 150" role="img" aria-label="Twenty p-values plotted as dots along a 0 to 1 axis, roughly evenly spread. A dashed vertical line at 0.05 near the left edge. Two dots, at 0.030 and 0.048, fall to the left of the line and are highlighted as false discoveries; the other eighteen are spread across the rest of the axis.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">20 null p-values spread across [0,1]; two land left of 0.05 by chance</text>
    <line x1="60" y1="90" x2="650" y2="90" stroke="var(--grid)"></line>
    <line x1="90" y1="60" x2="90" y2="120" stroke="var(--s2)" stroke-dasharray="3 3"></line>
    <text x="95" y="56" fill="var(--s2)" font-size="8">p=0.05</text>
    <g fill="var(--s2)"><circle cx="78" cy="90" r="4"></circle><circle cx="88" cy="90" r="4"></circle></g>
    <g fill="var(--s1)"><circle cx="125" cy="90" r="3"></circle><circle cx="172" cy="90" r="3"></circle><circle cx="196" cy="90" r="3"></circle><circle cx="243" cy="90" r="3"></circle><circle cx="278" cy="90" r="3"></circle><circle cx="308" cy="90" r="3"></circle><circle cx="355" cy="90" r="3"></circle><circle cx="384" cy="90" r="3"></circle><circle cx="419" cy="90" r="3"></circle><circle cx="454" cy="90" r="3"></circle><circle cx="484" cy="90" r="3"></circle><circle cx="507" cy="90" r="3"></circle><circle cx="537" cy="90" r="3"></circle><circle cx="560" cy="90" r="3"></circle><circle cx="584" cy="90" r="3"></circle><circle cx="607" cy="90" r="3"></circle><circle cx="631" cy="90" r="3"></circle><circle cx="643" cy="90" r="3"></circle></g>
    <g fill="var(--muted)" text-anchor="middle"><text x="60" y="112">0</text><text x="640" y="112">1</text></g>
    <text x="80" y="132" fill="var(--s2)" font-size="8">these two "discoveries" are the left tail of pure noise</text>
  </g>
</svg>
^ Twenty p-values from nothing-is-real spread evenly across the range, because a null p-value is uniform. Two happen to fall below 0.05 — the expected left-tail of the family, not a signal.

Two significant results, from twenty tests of hypotheses that are all false. Chance predicted one; two is well within the noise. This module is why those two are nothing, and what threshold would have said so.

## Concepts

Named here so you can find them again; each is built below.

- **P-value** — the probability of data this extreme under the null; a per-test false-positive rate at its threshold.
- **Multiple comparisons** — running many tests, so false positives accumulate across the family.
- **Expected false positives** — number of tests times alpha; what chance produces under all-null.
- **Family-wise error rate (FWER)** — the probability of at least one false positive across the family.
- **P-hacking** — reporting the significant test out of many, without correcting for the many.
- **Bonferroni correction** — divide alpha by the number of tests to hold the FWER at alpha.

## Worked example

Source: the multiple-comparisons problem that governs any exploratory analysis (and the reproducibility crisis it drives), with the Bonferroni correction as the simplest fix; the p-values here stand in for twenty real tests so the false-discovery count and the correction are exact and checkable.

Script and fixture: `modules/ai-for-science-and-data/code/data-inter-04/` — `phack.py`, and `pvalues.json`, twenty p-values from all-null tests, two below 0.05 by chance. Every command runs from there.

### What chance produces: expected false positives

The naive analysis counts p-values below alpha. Under all-null, how many should it find?

```
# phack.py:41-48 — COMPLETE (discoveries at a threshold; the count chance predicts)
def discoveries(pvalues, threshold):
    """Indices of tests that clear a significance threshold."""
    return [i for i, p in enumerate(pvalues) if p < threshold]


def expected_false_positives(n, alpha):
    """Under all-null, the number of tests expected to cross alpha by chance."""
    return n * alpha
```

With twenty tests at alpha 0.05, the expected number of false positives is `20 × 0.05 = 1`. The naive analysis found two, which is not alarming — it is one above the expectation, well inside the spread of a count that averages one. The key realization is that finding "a significant result" here is not surprising and not evidence; it is the null hypothesis behaving exactly as advertised. A per-test 5% error rate, applied twenty times, is designed to produce about one false alarm.

### The probability of being fooled: FWER

Expectation understates the danger. The quantity that matters is the probability of at least one false positive.

```
# phack.py:51-53 — COMPLETE (family-wise error: P at least one false positive)
def family_wise_error(n, alpha):
    """P(at least one false positive) across n independent null tests."""
    return 1 - (1 - alpha) ** n
```

Each test independently avoids a false positive with probability 0.95, so the whole family avoids one with probability 0.95 to the n — and the chance of at least one is one minus that. Watch it grow:

```
# $ python3 phack.py --fwer
#   tests   P(>= 1 false positive)
#   1       5%
#   5       23%
#   10      40%
#   20      64%
#   50      92%
```

run: 2026-08-26 · deterministic · `python3 phack.py --fwer`

At one test the false-positive risk is the 5% you signed up for. At twenty it is 64% — you are more likely than not to find a spurious "significant" result. At fifty it is 92%, nearly guaranteed. This is why exploratory analysis over a real dataset, poking at cohort after cohort, will hand you a significant finding whether or not anything is real: with enough looks, noise clears the bar.

<svg viewBox="0 0 700 180" role="img" aria-label="A rising curve of the probability of at least one false positive against the number of tests. At 1 test it is 5%, at 5 it is 23%, at 10 it is 40%, at 20 it is 64% crossing a dashed 50% line, at 50 it is 92%. The curve rises steeply and approaches 100%.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">P(at least one false positive) vs number of tests, alpha=0.05</text>
    <line x1="60" y1="150" x2="650" y2="150" stroke="var(--grid)"></line>
    <line x1="60" y1="30" x2="60" y2="150" stroke="var(--grid)"></line>
    <line x1="60" y1="90" x2="650" y2="90" stroke="var(--acc)" stroke-dasharray="4 3"></line>
    <text x="560" y="86" fill="var(--acc-ink)" font-size="8">50% — coin flip</text>
    <polyline points="80,144 190,115 320,78 450,49 640,40" fill="none" stroke="var(--s2)" stroke-width="2.5"></polyline>
    <circle cx="80" cy="144" r="3" fill="var(--s2)"></circle><circle cx="190" cy="115" r="3" fill="var(--s2)"></circle><circle cx="320" cy="78" r="3" fill="var(--s2)"></circle><circle cx="450" cy="49" r="3" fill="var(--s2)"></circle><circle cx="640" cy="40" r="3" fill="var(--s2)"></circle>
    <g fill="var(--muted)" font-size="8"><text x="74" y="164">1</text><text x="184" y="164">5</text><text x="314" y="164">10</text><text x="444" y="164">20</text><text x="632" y="164">50</text></g>
    <g fill="var(--muted)" font-size="8"><text x="88" y="142">5%</text><text x="330" y="74">40%</text><text x="450" y="45">64%</text><text x="612" y="36">92%</text></g>
  </g>
</svg>
^ The false-positive probability crosses 50% before twenty tests: past that point a "significant" result from an uncorrected family is more likely noise than signal. The 5% you intended holds only at a single test.

### The fix: correct the threshold

Bonferroni holds the family-wise error at alpha by dividing the per-test threshold by the number of tests.

```
# phack.py:56-58 — COMPLETE (Bonferroni: shrink the threshold by the number of tests)
def bonferroni_threshold(n, alpha):
    """Divide alpha by the number of tests so the family-wise error stays at alpha."""
    return alpha / n
```

For twenty tests the corrected threshold is `0.05 / 20 = 0.0025`, and nothing in the family clears it:

```
# $ python3 phack.py --correct
#   naive threshold      = 0.0500  -> 2 'discoveries' [0, 1]
#   Bonferroni threshold = 0.0025  -> 0 discoveries []
#   smallest p-value is 0.030, still above 0.0025
```

run: 2026-08-26 · deterministic · `python3 phack.py --correct`

<svg viewBox="0 0 700 140" role="img" aria-label="A zoomed axis from 0 to 0.06. The naive threshold at 0.05 is far right; the Bonferroni threshold at 0.0025 is a tiny sliver near zero. The two smallest p-values, 0.030 and 0.048, sit between the two thresholds — inside the naive bar, outside the corrected one.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">zoom on [0, 0.06]: the two thresholds and the two smallest p-values</text>
    <line x1="60" y1="90" x2="650" y2="90" stroke="var(--grid)"></line>
    <line x1="90" y1="60" x2="90" y2="110" stroke="var(--s1)" stroke-dasharray="3 3"></line>
    <text x="60" y="52" fill="var(--s1)" font-size="8">Bonferroni 0.0025</text>
    <line x1="550" y1="60" x2="550" y2="110" stroke="var(--s2)" stroke-dasharray="3 3"></line>
    <text x="500" y="52" fill="var(--s2)" font-size="8">naive 0.05</text>
    <circle cx="382" cy="90" r="4" fill="var(--ink)"></circle><text x="382" y="80" text-anchor="middle" fill="var(--ink)" font-size="8">0.030</text>
    <circle cx="538" cy="90" r="4" fill="var(--ink)"></circle><text x="538" y="80" text-anchor="middle" fill="var(--ink)" font-size="8">0.048</text>
    <g fill="var(--muted)" text-anchor="middle"><text x="60" y="112">0</text><text x="640" y="112">0.06</text></g>
    <text x="200" y="130" fill="var(--muted)" font-size="8">both p-values sit right of the corrected threshold -> 0 discoveries after correction</text>
  </g>
</svg>
^ Correcting for twenty tests slides the bar from 0.05 all the way left to 0.0025, and both "significant" p-values are now well to the right of it. Nothing survives, which is correct — nothing was real.

The smallest p-value, 0.030, looked significant at 0.05 and is nowhere near 0.0025. The correction makes zero discoveries, which is the correct answer, because every hypothesis was null. The logic is exact: requiring each of twenty tests to clear alpha-over-twenty means the probability that any of them crosses by chance is back down to roughly alpha, restoring the 5% guarantee you thought you had. You pay in power — a real effect now needs a much smaller p to be believed — but you stop reporting noise.

**A p-value is a per-test false-positive rate, so across many tests false positives accumulate — 20 tests give a 64% chance of a spurious "significant" result — and a finding selected from many tests is not evidence until the threshold is corrected for the number of tests, which Bonferroni does by dividing alpha by that number.**

### The self-test

The `--check` mode asserts the whole chain: the naive analysis finds discoveries, the count matches chance, the family-wise error exceeds 50%, and the correction rejects everything.

```
# $ python3 phack.py --check
#   naive p<0.05 finds 'significant' results = True (2 of 20)
#   the count matches chance (expected 1.0 false positives) = True
#   P(>=1 false positive) exceeds 50% = True (64%)
#   Bonferroni correction rejects every discovery = True (threshold 0.0025)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 phack.py --check`

The `correction_rejects` line is the correctness anchor: since every hypothesis is null, a correct multiple-comparisons procedure must make zero discoveries, and if the threshold arithmetic were wrong that assertion would fail first. The `consistent_with_noise` line is the honest framing of the naive result — it asserts the discovery count is within chance of the expected false positives, so the module cannot pretend the naive finding was surprising; it was exactly what noise produces.

### The running tally

| threshold | value | discoveries | correct, given all-null? |
|---|---|---|---|
| naive per-test | 0.0500 | 2 (tests 0, 1) | no — noise called signal |
| Bonferroni (÷20) | 0.0025 | 0 | yes — nothing was real |

The two rows use the identical twenty p-values and differ only in where the line is drawn. The naive line, correct for a single test, is wrong for a family of twenty and manufactures two discoveries from noise. The corrected line restores the guarantee and finds nothing, which is the truth. The number of tests you ran is part of the analysis, not a detail — a p-value means nothing until you know how many you looked at to find it.

### What we did not settle

Bonferroni is the strictest, simplest correction and it trades away power: with many tests it can miss real effects because the bar is so high. The Benjamini-Hochberg procedure controls the false discovery rate — the expected fraction of discoveries that are false — instead of the family-wise error, which is far more powerful when you expect some real effects among many tests, and is the standard in fields like genomics that run thousands of tests. Independence matters too: correlated tests make Bonferroni conservative. And the deeper fix is pre-registration — deciding which hypotheses to test before seeing the data, so you cannot select the significant one after the fact. The rule here — correct for the number of tests — is the floor; which correction depends on how many real effects you expect.

## Build

The practice in one paragraph: count every test you run against a dataset, including the exploratory ones you did not report; never call a result significant at a per-test threshold when it was selected from many tests; correct the threshold for the number of comparisons — Bonferroni for few tests or when any false positive is costly, Benjamini-Hochberg for many tests where some real effects are expected; and pre-register your hypotheses when you can, so the count of tests is fixed before the data is seen. Report how many tests you ran alongside every p-value.

We opened on the naive discoveries. The number that shows they are noise is the family-wise error rate:

```
# modules/ai-for-science-and-data/code/data-inter-04/ — COMPLETE, run from that directory
$ python3 phack.py --fwer
  20      64%
```

Now do it to your own analysis. Count every hypothesis test you ran over a dataset, compute the family-wise error rate at your alpha, and apply a Bonferroni (or Benjamini-Hochberg) correction to your p-values. Your number to beat is not a single p-value; it is **the family-wise error rate of your whole analysis, and how many of your "significant" findings survive correction** — if the FWER is above 50% and a finding does not survive, it was likely noise. Bring back the FWER and the corrected discovery count. Good luck.

## Definition of done

- [ ] Every hypothesis test in an analysis counted, exploratory ones included
- [ ] The expected number of false positives (n × alpha) computed
- [ ] The family-wise error rate computed and shown to grow with the number of tests
- [ ] A Bonferroni-corrected threshold applied to the p-values
- [ ] Confirmation that correction rejects the chance-level discoveries
- [ ] `python3 phack.py --check` printing SELF-TEST PASS: finds-by-chance, consistent-with-noise, fwer-high, correction-rejects
- [ ] A statement of how many tests you ran, reported next to every p-value
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. A p-value below 0.05 is a per-test guarantee. What happens to the guarantee across twenty tests, and by how much?
2. Two of twenty null tests were "significant". Why is that not surprising, and what number predicted it?
3. What is the family-wise error rate, and why does it reach 64% at twenty tests?
4. How does Bonferroni correction restore the intended error rate, and what does it cost you?
5. Your own multi-test analysis was corrected. What was its family-wise error rate, and how many findings survived correction?

## External resources

- Benjamini & Hochberg, *Controlling the False Discovery Rate* (1995) — my summary: the more powerful alternative to Bonferroni that controls the fraction of discoveries that are false rather than any false positive; read it for what to use when you run many tests and expect some real effects.
- Simmons, Nelson & Simonsohn, *False-Positive Psychology* (2011) — my summary: how researcher degrees of freedom and undisclosed multiple comparisons manufacture significant results, and why pre-registration helps; read it for how p-hacking happens in practice, often without intent.
- This hub, *data-inter-03* — modules/ai-for-science-and-data/data-inter-03.md — my summary: the base-rate module, another place a per-item rate misleads at the population scale (precision under low prevalence); read it for the shared discipline — a rate that is fine in isolation lies once you account for how many cases it is applied to.
