---
id: data-inter-08
title: Real data's leading digits follow Benford's law — fabricated numbers don't, and that flags them
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 5-8h
summary: Count the first digit of every number in a large real-world dataset and the digits are not uniform — the digit 1 leads about 30% of the time and 9 barely 5%, following Benford's law, where the probability that the first digit is d is log10(1 + 1/d). It arises whenever data spans several orders of magnitude, because what is uniform is the exponent, not the value, so numbers spend more of their range with a small leading digit. This makes a fraud detector: a person inventing numbers to look random spreads the first digits evenly, because uniform feels random, but real data is Benford not uniform, so the fabricated set's flat distribution stands out. A genuine multi-scale dataset here matches Benford with a total deviation of 0.024, while a fabricated dataset of hand-picked "random" values deviates 0.47 — twenty times as far — so a deviation threshold of 0.10 sits cleanly between them and flags the fake while clearing the real. The lesson is that authentic quantitative data carries a statistical fingerprint most people do not know to forge, and comparing leading digits to Benford is a cheap first screen for made-up or manipulated numbers.
eli5: If you look at the first digit of lots of real numbers — house prices, river lengths, bank balances — the number 1 shows up as the first digit way more often than 9, about six times as often. It sounds impossible, but it's true whenever numbers come in wildly different sizes. Someone making up numbers usually sprinkles the digits evenly because that feels random, and that evenness is the tell: real data leans hard on 1, fakes don't, so counting first digits catches a lot of made-up data.
---

## Why this module

Here is a fact that sounds wrong the first time you hear it: in a large collection of real-world numbers, the leading digit is far more likely to be 1 than 9 — not a little more likely, about six times more. Across street addresses, populations, physical constants, stock prices, invoice amounts, the first digit is 1 roughly 30% of the time and 9 only about 5%. This is Benford's law, and the exact probabilities are given by a short formula: the chance the first digit is d is log10(1 + 1/d).

The reason is scale. Benford's law holds for data that spans several orders of magnitude, and the key insight is that in such data it is the exponent that is roughly uniform, not the value. Think of a quantity growing at a steady percentage rate: it takes as long to go from 100 to 200 (doubling) as from 200 to 400, but the first of those journeys sits entirely on leading digit 1 while the second passes through 2 and 3. So a number spends more of its life with a small leading digit than a large one, and integrated over many decades that produces exactly the logarithmic distribution. Uniform first digits are what you would get if numbers had no scale — and real, multi-scale data always has scale.

That gap between what real data does and what people expect is a fraud detector. Someone fabricating numbers — padding an expense report, inventing survey responses, faking measurements — tends to make the first digits roughly uniform, because "spread them out evenly" is what random feels like. But real data is not uniform, it is Benford, so the fabricated set's flat leading-digit distribution is a fingerprint of invention. This module generates a genuine multi-scale dataset and a fabricated one, tallies their leading digits, compares each to Benford's expected distribution, and shows the fake caught by its deviation. Everything runs offline, stdlib Python 3, `$0.00`, with the numbers and digits generated and the deviations computed. The instinct to unlearn is that random-looking numbers are uniform. Authentic quantitative data is Benford-distributed, and evenly-spread leading digits are a sign not of randomness but of a human hand.

## Concepts

Named here so you can find them again; each is built below.

- **Leading digit** — the first significant digit of a number; scale-invariant.
- **Benford's law** — P(first digit = d) = log10(1 + 1/d); 1 leads ~30%, 9 ~5%.
- **Scale span** — data covering several orders of magnitude, the condition Benford needs.
- **Observed distribution** — the actual leading-digit frequencies of a dataset.
- **Deviation** — total distance between the observed distribution and Benford's expected one.
- **Fabrication fingerprint** — a flat (uniform) leading-digit distribution, the mark of invented numbers.

## Worked example

Source: a data-integrity screen — the leading-digit check an auditor or scientist runs on a dataset to flag possible fabrication. The two datasets stand in for genuine multi-scale data and hand-invented numbers; both are generated so the leading digits and deviations are real, not asserted.

Script and fixture: `modules/ai-for-science-and-data/code/data-inter-08/` — `benford.py`, and `config.json`. Every command runs from there.

### Benford's expected distribution

The law is one line, and the leading-digit extractor is scale-invariant.

```
# benford.py:42-58 — COMPLETE (Benford's formula and the scale-invariant leading digit)
def benford_expected():
    """P(first digit = d) = log10(1 + 1/d), for d in 1..9."""
    return {d: math.log10(1 + 1 / d) for d in range(1, 10)}


def first_digit(x):
    """The leading significant digit of x (scale-invariant)."""
    x = abs(x)
    if x == 0:
        return 0
    while x >= 10:
        x /= 10
    while x < 1:
        x *= 10
    return int(x)
```

`first_digit` divides or multiplies by 10 until the number is in [1, 10), then takes the integer part — so 42, 4200, and 0.042 all return 4, because the leading digit does not depend on the units or scale. Look at the expected distribution:

```
# $ python3 benford.py --benford
#   digit 1: 0.301  ##############################
#   digit 2: 0.176  ##################
#   digit 3: 0.125  ############
#   digit 5: 0.079  ########
#   digit 9: 0.046  #####
```

run: 2026-08-27 · deterministic · `python3 benford.py --benford`

The distribution falls off steeply and smoothly: 1 at 0.301, 2 at 0.176, down to 9 at 0.046. It is monotonic and heavily front-loaded, nothing like the flat 1/9 ≈ 0.111 you would guess. That specific curved shape is what real data matches and fabricated data does not.

<svg viewBox="0 0 700 190" role="img" aria-label="Benford's distribution as bars: digit 1 tallest at 0.30, falling smoothly to digit 9 at 0.05. A dashed line at 0.111 marks the uniform distribution a naive person expects. The Benford bars are far above uniform at digit 1 and below it at digits 5 through 9.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">Benford's law: leading digit 1 dominates, not uniform 1/9</text>
    <line x1="50" y1="160" x2="660" y2="160" stroke="var(--line)"></line>
    <line x1="50" y1="105" x2="660" y2="105" stroke="var(--s2)" stroke-dasharray="4 3"></line><text x="664" y="108" fill="var(--s2)" font-size="7">uniform .111</text>
    <g fill="var(--s1)">
      <rect x="70" y="40" width="50" height="120"></rect><rect x="135" y="90" width="50" height="70"></rect><rect x="200" y="110" width="50" height="50"></rect><rect x="265" y="121" width="50" height="39"></rect><rect x="330" y="128" width="50" height="32"></rect><rect x="395" y="133" width="50" height="27"></rect><rect x="460" y="137" width="50" height="23"></rect><rect x="525" y="140" width="50" height="20"></rect><rect x="590" y="142" width="50" height="18"></rect>
    </g>
    <text x="95" y="34" text-anchor="middle" fill="var(--s1)" font-size="7">.30</text><text x="615" y="136" text-anchor="middle" fill="var(--s1)" font-size="7">.05</text>
    <text x="95" y="174" text-anchor="middle" fill="var(--muted)" font-size="7">1</text><text x="615" y="174" text-anchor="middle" fill="var(--muted)" font-size="7">9</text>
    <text x="355" y="174" text-anchor="middle" fill="var(--muted)" font-size="7">leading digit</text>
  </g>
</svg>
^ Benford's bars tower over the uniform line at digit 1 and sink below it from 5 on — a smooth logarithmic fall. Real data traces this curve; fabricated data hugs the flat uniform line.

### Two datasets, tallied

One dataset is genuine multi-scale data; the other is fabricated to look random.

```
# benford.py:61-68 — COMPLETE (real data spans orders of magnitude; fabricated spreads digits evenly)
def real_dataset(n):
    """Genuine multi-scale data: values spanning many orders of magnitude (log-uniform)."""
    return [10 ** (k / 120) for k in range(n)]


def fabricated_dataset(n):
    """Made-up 'random' numbers: a person spreading first digits evenly (uniform), which real data never is."""
    return [((k % 9) + 1) * 10 ** (k % 4) + (k % 7) for k in range(n)]
```

The real dataset is values spread uniformly in the exponent — 10 to a smoothly increasing power — which is the mathematical signature of data spanning many decades, and it is Benford by construction of the real world, not by fiat. The fabricated dataset is what invention looks like: leading digits cycled evenly through 1–9, the "even spread" a person reaches for. Tally both:

```
# $ python3 benford.py --data
#   digit  benford  real data  fabricated
#   1      0.301    0.308      0.178
#   2      0.176    0.175      0.092
#   5      0.079    0.083      0.104
#   9      0.046    0.042      0.110
#   real deviation: 0.0237    fabricated deviation: 0.4708
```

run: 2026-08-27 · deterministic; sizes are a fixture, numbers generated · `python3 benford.py --data`

The real-data column tracks Benford almost exactly — 0.308 against 0.301 for digit 1, 0.175 against 0.176 for digit 2, all the way down — for a total deviation of 0.0237. The fabricated column is nearly flat: every digit near 0.10 to 0.11, with digit 1 at only 0.178 instead of 0.30 and digit 9 at 0.110 instead of 0.046. Its total deviation is 0.4708, twenty times the real data's. The fabricator's numbers pass a casual glance — they look like a jumble of plausible values — but their leading digits carry the unmistakable flatness of a distribution a human made even.

<svg viewBox="0 0 700 200" role="img" aria-label="Leading-digit distributions overlaid. Benford is a falling curve. The real dataset traces it closely. The fabricated dataset is nearly flat near 0.1 across all digits, far from Benford at digit 1 (0.18 vs 0.30) and digit 9 (0.11 vs 0.05).">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">real data traces Benford; fabricated data is flat (deviation 0.024 vs 0.47)</text>
    <line x1="50" y1="170" x2="660" y2="170" stroke="var(--line)"></line>
    <polyline points="70,44 138,92 206,112 274,123 342,130 410,135 478,139 546,142 614,144" fill="none" stroke="var(--s1)"></polyline><text x="120" y="40" fill="var(--s1)" font-size="8">Benford + real</text>
    <polyline points="70,120 138,155 206,153 274,150 342,148 410,148 478,147 546,147 614,146" fill="none" stroke="var(--s2)" stroke-dasharray="4 3"></polyline><text x="470" y="135" fill="var(--s2)" font-size="8">fabricated (flat)</text>
    <g fill="var(--s1)"><circle cx="70" cy="44" r="3"></circle><circle cx="138" cy="92" r="3"></circle><circle cx="614" cy="144" r="3"></circle></g>
    <g fill="var(--s2)"><circle cx="70" cy="120" r="3"></circle><circle cx="614" cy="146" r="3"></circle></g>
    <text x="70" y="186" text-anchor="middle" fill="var(--muted)" font-size="7">1</text><text x="614" y="186" text-anchor="middle" fill="var(--muted)" font-size="7">9</text>
    <text x="355" y="186" text-anchor="middle" fill="var(--muted)" font-size="7">leading digit</text>
  </g>
</svg>
^ The real dataset lies right on the Benford curve; the fabricated one is nearly flat, missing digit 1's dominance and overshooting the high digits. The vertical gap between the two lines is the deviation the detector measures.

### Deviation and the flag

The deviation is the total distance from Benford; a threshold turns it into a flag.

```
# benford.py:79-83 — COMPLETE (total absolute distance from Benford's expected distribution)
def deviation(dataset):
    """Total absolute distance between the observed and Benford's expected first-digit distribution."""
    obs, exp = observed(dataset), benford_expected()
    return sum(abs(obs[d] - exp[d]) for d in range(1, 10))
```

<svg viewBox="0 0 700 150" role="img" aria-label="Two deviation bars against a threshold line at 0.10. The real dataset's deviation is 0.024, a tiny bar well below the threshold. The fabricated dataset's deviation is 0.47, a tall bar well above it. The threshold sits cleanly in the wide gap between them.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">deviation from Benford vs the 0.10 flag threshold</text>
    <line x1="60" y1="120" x2="660" y2="120" stroke="var(--line)"></line>
    <line x1="60" y1="96" x2="660" y2="96" stroke="var(--s2)" stroke-dasharray="5 3"></line><text x="664" y="99" fill="var(--s2)" font-size="7">threshold 0.10</text>
    <rect x="150" y="114" width="120" height="6" fill="var(--s1)"></rect><text x="210" y="108" text-anchor="middle" fill="var(--s1)" font-size="8">real 0.024</text><text x="210" y="136" text-anchor="middle" fill="var(--muted)" font-size="7">cleared</text>
    <rect x="430" y="32" width="120" height="88" fill="var(--s2)"></rect><text x="490" y="26" text-anchor="middle" fill="var(--s2)" font-size="8">fabricated 0.47</text><text x="490" y="136" text-anchor="middle" fill="var(--s2)" font-size="7">FLAGGED</text>
    <text x="60" y="146" fill="var(--muted)" font-size="8">a 20x gap with the threshold sitting cleanly in the middle — not a close call</text>
  </g>
</svg>
^ The real data's deviation barely registers below the threshold; the fabricated data's towers far above it. The threshold sits in a wide empty gap, so the flag is decisive rather than marginal.

The real data's deviation, 0.0237, sits far below the threshold of 0.10; the fabricated data's, 0.4708, sits far above it. The threshold has clean separation to work with — a factor of twenty between conforming and fabricated — so the flag is not a close call. This is why leading-digit analysis is a standard first screen in forensic accounting and scientific-data auditing: it is cheap, it needs no knowledge of what the numbers mean, and it catches a fabrication mode people fall into without realizing.

**Real multi-scale data follows Benford's law — leading digit d with probability log10(1 + 1/d), so 1 leads ~30% and 9 ~5% — while fabricated numbers spread their leading digits uniformly; the genuine dataset deviates 0.024 from Benford and the fabricated one 0.47, twenty times as far, so a deviation threshold flags invented data by a fingerprint most forgers do not know to reproduce.**

### The self-test

The `--check` mode confirms Benford is a proper distribution, the real data conforms, the fabricated data deviates, and the fabricated deviation dwarfs the real one.

```
# $ python3 benford.py --check
#   Benford's expected distribution sums to 1 and peaks at digit 1 = True
#   the real dataset conforms to Benford (deviation below threshold) = True (0.0237 < 0.10)
#   the fabricated dataset deviates from Benford = True (0.4708 > 0.10)
#   the fabricated deviation is many times the real one = True (0.4708 vs 0.0237, 19.9x)
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 benford.py --check`

The `real_conforms` and `fake_deviates` lines are the detector working in both directions — it must clear genuine data as well as catch fabricated data, or it would be a smoke alarm that goes off at every meal. The clean 0.024-versus-0.47 split, with the threshold between them, is what makes it a usable screen rather than a coin flip.

```
# benford.py:123-128 — COMPLETE (the real dataset conforms; the fabricated one is flagged)
    real_conforms = d_real < thr
    print("  the real dataset conforms to Benford (deviation below threshold) = %s (%.4f < %.2f)"
          % (real_conforms, d_real, thr))

    fake_deviates = d_fake > thr
    print("  the fabricated dataset deviates from Benford = %s (%.4f > %.2f)" % (fake_deviates, d_fake, thr))
```

### The running tally

| dataset | digit-1 share | digit-9 share | deviation | flagged? |
|---|---|---|---|---|
| Benford (expected) | 0.301 | 0.046 | 0 | — |
| real (multi-scale) | 0.308 | 0.042 | 0.0237 | no (< 0.10) |
| fabricated (uniform) | 0.178 | 0.110 | 0.4708 | yes (> 0.10) |

Read the digit-1 and digit-9 columns: the real data leans on 1 (0.308) and neglects 9 (0.042) just as Benford predicts, while the fabricated data flattens both toward 0.1, under-representing 1 and over-representing 9. That flattening is the whole tell — a fabricator makes the rare high digits too common and the dominant digit 1 too rare, because their mental model of "random" is uniform. The deviation column turns that visual into one number, and the threshold turns the number into a decision. It is a screen, not a proof — conforming data is not guaranteed genuine, and some real data legitimately fails Benford — but a large deviation is a cheap, meaningful reason to look harder.

### What we did not settle

This is the first-digit test; the technique has more to it. A proper test uses a statistic with a sampling distribution — a chi-square or the specialized MAD (mean absolute deviation) cutoffs Nigrini published for accounting data — rather than an eyeballed threshold, so you can attach a significance to the flag. Benford's law also constrains the second digit, and the first-two-digits test is more powerful for spotting narrow anomalies (a cluster of invented values just below an approval limit). The law needs the right kind of data: it fails for numbers with a built-in scale (heights in cm, phone numbers, assigned IDs) or a narrow range, so a non-conforming dataset can be perfectly honest — the test screens, it does not convict. And a sophisticated fabricator who knows Benford can defeat the first-digit test, which is why auditors combine it with other checks. The invariant: authentic multi-scale data has a leading-digit fingerprint, and its absence is a reason to investigate.

## Build

The build in one paragraph: to screen a dataset for fabrication, extract the scale-invariant leading digit of every value, tally the nine frequencies, and compare them to Benford's expected distribution (log10(1 + 1/d)) with a deviation measure; a distribution that is suspiciously flat — under-weighting digit 1, over-weighting the high digits — deviates far from Benford and warrants a closer look. Use a principled cutoff (chi-square or Nigrini's MAD thresholds) rather than an eyeballed one, add the first-two-digits test for narrow anomalies, apply it only to data that spans scales and lacks a built-in range, and treat a flag as a reason to investigate, never as proof.

We opened on the expected distribution. The number that proves the screen is the two datasets' deviations:

```
# modules/ai-for-science-and-data/code/data-inter-08/ — COMPLETE, run from that directory
$ python3 benford.py --check
  the real dataset conforms to Benford (deviation below threshold) = True (0.0237 < 0.10)
  the fabricated dataset deviates from Benford = True (0.4708 > 0.10)
```

Now build your own. Take a real multi-scale dataset (transaction amounts, city populations, file sizes) and a set of numbers you invent to "look random," and run the leading-digit test on both. Your number to beat is not the size of the data; it is **the deviation from Benford, real versus fabricated** — the real data should hug the Benford curve while your invented numbers spread flat and deviate far. Confirm the threshold clears one and flags the other. Bring back both deviations. Good luck.

## Definition of done

- [ ] Benford's expected distribution and a scale-invariant leading-digit function
- [ ] A genuine multi-scale dataset and a fabricated (uniform-digit) one
- [ ] Observed leading-digit distributions for both
- [ ] A deviation measure from Benford, and a flag threshold
- [ ] Confirmation the real dataset conforms (deviation below threshold)
- [ ] Confirmation the fabricated dataset deviates far above the threshold
- [ ] `python3 benford.py --check` printing SELF-TEST PASS: benford_sums, real_conforms, fake_deviates, fake_far_worse
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. State Benford's law. Roughly how often does 1 lead, versus 9?
2. Why does multi-scale data follow it? What is uniform — the value or the exponent?
3. What does a fabricated dataset's leading-digit distribution look like, and why do people produce that shape?
4. Why is a Benford flag a screen and not a proof? Name a kind of honest data that fails the test.
5. Your own real and fabricated datasets were tested. What deviation did each show, and did the threshold separate them?

## External resources

- Nigrini, *Benford's Law: Applications for Forensic Accounting, Auditing, and Fraud Detection* — my summary: the practical playbook, including the MAD cutoffs and first-two-digits test this module simplifies; read it for turning a deviation into a defensible flag.
- Hill, *A Statistical Derivation of the Significant-Digit Law* — my summary: why scale-invariance (and mixtures of distributions) forces the logarithmic law; read it for the theory behind why real data is Benford.
- This hub, *data-inter-02* (the mean describes no typical request) — read it for the heavy-tailed, multi-scale data that is exactly the kind Benford's law governs.
