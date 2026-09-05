---
id: evals-inter-07
title: A null result from a small eval is not "no difference" — compute the detectable effect first
topic: evals-and-statistics
level: intermediate
status: ready
time: 5-8h
summary: You run 20 cases on system A and system B, the difference is not statistically significant, and you conclude the systems are equivalent — but a 20-case eval is nearly blind, because its confidence interval on the difference is so wide that only a huge effect could clear it, and a real, useful improvement sits comfortably inside the noise. The number that decides this is the minimum detectable effect (MDE), the smallest true difference a sample size can distinguish from zero, roughly the half-width of the CI on the difference, and it shrinks with the square root of n. Here two systems truly differ by 6 points; at n=20 the MDE is 27 points, so the real effect is more than four times smaller than anything the eval could see and the null is uninformative, while at n=500 the MDE falls to 5 points, below the true effect, and the same difference becomes detectable. Absence of a significant result is not evidence of no effect until the MDE is below the effect you would care about — so a null is only "these are equal" when the eval was powered, and otherwise it means nothing at all.
eli5: If you weigh two backpacks on a bathroom scale that only reads in whole kilograms, and it shows the same number for both, you have not proved they weigh the same — the scale is just too coarse to see a half-kilo difference. A tiny eval is a coarse scale: when it says "no significant difference," that might mean the systems are equal, or it might mean your scale can't tell them apart. Before you trust a "no difference," you have to ask how fine your scale was — and a 20-question eval is very coarse.
---

## Why this module

Evals produce two kinds of result, and one of them is routinely misread. A significant result — B beat A, the interval clears zero — is usually handled with appropriate care. A null result — no significant difference — is where the mistake lives, because the natural reading, "the systems are equivalent," is only one of two possibilities, and often the wrong one. The other possibility is that there is a real difference and your eval was simply too small to see it. Distinguishing these two is not optional nuance; it is the difference between correctly shipping the better system and wrongly declaring a tie and keeping the worse one.

The tool for the distinction is statistical power, summarized by the minimum detectable effect. Every eval has a resolution: below some effect size, a true difference is indistinguishable from noise given your sample size, exactly as a coarse scale cannot resolve a small weight difference.

<svg viewBox="0 0 700 180" role="img" aria-label="Two confidence intervals on the difference between the systems, both centered near the true 6-point effect. The n=20 interval is very wide, from about minus 21 to plus 33, spanning zero, so it is non-significant and the true 6-point effect is buried inside it. The n=500 interval is narrow, from about plus 0.5 to plus 11, not spanning zero, so it is significant.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the same 6-pt effect inside two intervals: n=20 (wide) vs n=500 (narrow)</text>
    <line x1="90" y1="150" x2="640" y2="150" stroke="var(--line)"></line>
    <line x1="300" y1="40" x2="300" y2="160" stroke="var(--s2)" stroke-dasharray="4 3"></line><text x="300" y="174" text-anchor="middle" fill="var(--s2)" font-size="7">0</text>
    <line x1="360" y1="40" x2="360" y2="160" stroke="var(--s1)" stroke-dasharray="2 2"></line><text x="360" y="174" text-anchor="middle" fill="var(--s1)" font-size="7">+6 true</text>
    <line x1="110" y1="70" x2="610" y2="70" stroke="var(--s2)"></line><line x1="110" y1="62" x2="110" y2="78" stroke="var(--s2)"></line><line x1="610" y1="62" x2="610" y2="78" stroke="var(--s2)"></line><circle cx="360" cy="70" r="3" fill="var(--s2)"></circle><text x="120" y="58" fill="var(--s2)" font-size="8">n=20: [−21, +33] spans 0 → NOT significant (blind)</text>
    <line x1="330" y1="110" x2="392" y2="110" stroke="var(--s1)"></line><line x1="330" y1="102" x2="330" y2="118" stroke="var(--s1)"></line><line x1="392" y1="102" x2="392" y2="118" stroke="var(--s1)"></line><circle cx="360" cy="110" r="3" fill="var(--s1)"></circle><text x="400" y="114" fill="var(--s1)" font-size="8">n=500: [+0.5, +11] excludes 0 → significant</text>
  </g>
</svg>
^ Both intervals sit on the same true +6 effect, but the n=20 interval is so wide it swallows zero — a null — while the n=500 interval is tight enough to exclude zero. The effect never changed; only the width did. That resolution is the MDE — roughly the half-width of the confidence interval on the difference between the two systems — and it depends on the sample size, shrinking with the square root of n. A 20-case eval has a large MDE; a 500-case eval has a small one. If the effect you care about is smaller than your MDE, a null result tells you nothing, because the eval could not have detected that effect even if it were real.

This module makes the point with two systems that genuinely differ by 6 percentage points. It computes the MDE at a range of sample sizes and shows that at n=20 the MDE is 27 points — so the real 6-point effect is more than four times too small to detect, and any non-significant result at that size is pure blindness, not evidence of equivalence. Grow the eval to n=500 and the MDE falls to 5 points, below the true effect, and now a null would actually mean something. Everything runs offline against an eval fixture, stdlib Python 3, `$0.00`, with every standard error computed. The instinct to unlearn is that a non-significant result means no difference. It means no *detectable* difference, and whether that is informative depends entirely on what your eval could have detected — which you must compute, not assume.

## Concepts

Named here so you can find them again; each is built below.

- **Null result** — a non-significant difference; the interval on the difference includes zero.
- **Statistical power** — the chance an eval detects a true effect of a given size.
- **Minimum detectable effect (MDE)** — the smallest true difference a sample size can resolve.
- **Standard error of the difference** — the noise in the measured gap; shrinks with sqrt(n).
- **Underpowered** — an eval whose MDE exceeds the effect you care about; its null means nothing.
- **Absence of evidence** — a null; it is evidence of absence only when the eval was powered.

## Worked example

Source: the interpretation of a head-to-head eval result — the decision of whether "no significant difference" means ship-either or keep-measuring. The true rates stand in for a real quality difference you cannot see directly; the whole point is to reason about detectability before trusting a null.

Script and fixture: `modules/evals-and-statistics/code/evals-inter-07/` — `power.py`, and `eval.json`, two systems and a range of sample sizes. Every command runs from there.

### The minimum detectable effect

The MDE is the confidence-interval half-width on the difference: the standard error of the gap, times the 95% critical value.

```
# power.py:42-53 — COMPLETE (standard error of the difference, the MDE, and the detectability test)
def se_difference(pa, pb, n):
    """Standard error of the difference in two pass rates, each measured on n cases."""
    return math.sqrt(pa * (1 - pa) / n + pb * (1 - pb) / n)


def mde(pa, pb, n, z):
    """Minimum detectable effect: the CI half-width, the smallest difference this n can resolve."""
    return z * se_difference(pa, pb, n)


def can_detect(pa, pb, n, z):
    """Can an eval of this size distinguish the true effect from zero?"""
    return abs(pb - pa) > mde(pa, pb, n, z)
```

The `se_difference` shrinks as n grows — the `/ n` inside the square root means it falls with the square root of the sample size, so quadrupling n halves the noise. The MDE is that noise scaled to a 95% interval, and `can_detect` asks the one question that matters: is the true effect bigger than the interval half-width, or does it hide inside it? Compute the MDE across sample sizes:

```
# $ python3 power.py --power
#   n per system   std error   MDE (pts)   can detect the 6-pt effect?
#   20             0.1401      27.5        NO (underpowered)
#   50             0.0886      17.4        NO (underpowered)
#   100            0.0626      12.3        NO (underpowered)
#   200            0.0443      8.7         NO (underpowered)
#   500            0.0280      5.5         yes
```

run: 2026-08-27 · deterministic; rates and sizes are a fixture · true effect 6 pts · `python3 power.py --power`

The true effect is 6 points, fixed. At n=20 the MDE is 27.5 points — the eval can only resolve differences larger than 27 points, so a real 6-point gap is invisible, and a null result is guaranteed regardless of whether the systems differ. As n grows the MDE falls — 17, 12, 9 — but it stays above 6 until n=500, where it finally drops to 5.5 points, just under the true effect, and the difference becomes detectable. The same real 6-point improvement is undetectable at n=20 and detectable at n=500; nothing about the systems changed, only the resolution of the measurement.

<svg viewBox="0 0 700 210" role="img" aria-label="A chart of minimum detectable effect versus sample size. A falling curve from 27.5 points at n=20 down through 17, 12, 9 to 5.5 at n=500. A horizontal line marks the true effect at 6 points. The MDE curve stays above the 6-point line until n=500, where it dips just below — the point where the effect becomes detectable.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">minimum detectable effect falls with n; the true effect is fixed at 6 pts</text>
    <line x1="60" y1="180" x2="660" y2="180" stroke="var(--line)"></line>
    <line x1="60" y1="30" x2="60" y2="180" stroke="var(--line)"></line>
    <line x1="60" y1="150" x2="660" y2="150" stroke="var(--s1)" stroke-dasharray="5 3"></line><text x="664" y="153" fill="var(--s1)" font-size="7">effect 6</text>
    <polyline points="90,42 210,92 330,116 470,138 620,154" fill="none" stroke="var(--s2)"></polyline>
    <circle cx="90" cy="42" r="4" fill="var(--s2)"></circle><text x="90" y="34" text-anchor="middle" fill="var(--s2)" font-size="7">27</text><text x="90" y="196" text-anchor="middle" fill="var(--muted)" font-size="7">20</text>
    <circle cx="210" cy="92" r="4" fill="var(--s2)"></circle><text x="210" y="84" text-anchor="middle" fill="var(--s2)" font-size="7">17</text><text x="210" y="196" text-anchor="middle" fill="var(--muted)" font-size="7">50</text>
    <circle cx="330" cy="116" r="4" fill="var(--s2)"></circle><text x="330" y="108" text-anchor="middle" fill="var(--s2)" font-size="7">12</text><text x="330" y="196" text-anchor="middle" fill="var(--muted)" font-size="7">100</text>
    <circle cx="470" cy="138" r="4" fill="var(--s2)"></circle><text x="470" y="130" text-anchor="middle" fill="var(--s2)" font-size="7">9</text><text x="470" y="196" text-anchor="middle" fill="var(--muted)" font-size="7">200</text>
    <circle cx="620" cy="154" r="4" fill="var(--s1)"></circle><text x="620" y="168" text-anchor="middle" fill="var(--s1)" font-size="7">5.5</text><text x="620" y="196" text-anchor="middle" fill="var(--muted)" font-size="7">500</text>
    <text x="300" y="60" fill="var(--s2)" font-size="8">MDE above the effect → a null is blind</text>
    <text x="470" y="172" fill="var(--s1)" font-size="7">← detectable</text>
  </g>
</svg>
^ The MDE curve falls with sample size but only crosses below the fixed 6-point effect at n=500. Everywhere above the line, a non-significant result is blindness, not equivalence; only at n=500 does a null become meaningful.

### Reading a null correctly

The `--verdict` view turns each MDE into how a null result should be read at that size.

```
# $ python3 power.py --verdict
#   n=20    MDE=27 pts -> UNDERPOWERED: a null means nothing -- MDE 27 pts > effect 6
#   n=50    MDE=17 pts -> UNDERPOWERED: a null means nothing -- MDE 17 pts > effect 6
#   n=100   MDE=12 pts -> UNDERPOWERED: a null means nothing -- MDE 12 pts > effect 6
#   n=200   MDE=9 pts -> UNDERPOWERED: a null means nothing -- MDE 9 pts > effect 6
#   n=500   MDE=5 pts -> powered: a null would truly mean no meaningful effect
```

run: 2026-08-27 · deterministic · `python3 power.py --verdict`

The verdict is a direct comparison of the MDE to the effect, one branch each way:

```
# power.py:80-84 — COMPLETE (a null is meaningful only once the MDE drops below the effect)
        if can_detect(pa, pb, n, z):
            read = "powered: a null would truly mean no meaningful effect"
        else:
            read = "UNDERPOWERED: a null means nothing -- MDE %.0f pts > effect %.0f" % (100 * m, 100 * effect)
        print("  n=%-5d MDE=%.0f pts -> %s" % (n, 100 * m, read))
```

<svg viewBox="0 0 700 150" role="img" aria-label="A diagram showing the square-root relationship: to halve the minimum detectable effect you must quadruple the sample size. n=20 gives MDE 27, n=80 (4x) gives about 14 (half), n=320 (16x) gives about 7 (quarter). Diminishing returns from more data.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">MDE shrinks with sqrt(n): to halve it, quadruple the cases</text>
    <rect x="70" y="40" width="60" height="70" fill="var(--s2)"></rect><text x="100" y="34" text-anchor="middle" fill="var(--s2)" font-size="8">27</text><text x="100" y="126" text-anchor="middle" fill="var(--muted)" font-size="7">n=20</text>
    <text x="150" y="80" fill="var(--muted)">→</text>
    <rect x="180" y="75" width="60" height="35" fill="var(--muted)"></rect><text x="210" y="69" text-anchor="middle" fill="var(--muted)" font-size="8">~14</text><text x="210" y="126" text-anchor="middle" fill="var(--muted)" font-size="7">n=80 (4x)</text>
    <text x="260" y="80" fill="var(--muted)">→</text>
    <rect x="290" y="92" width="60" height="18" fill="var(--s1)"></rect><text x="320" y="86" text-anchor="middle" fill="var(--s1)" font-size="8">~7</text><text x="320" y="126" text-anchor="middle" fill="var(--muted)" font-size="7">n=320 (16x)</text>
    <text x="400" y="80" fill="var(--muted)" font-size="8">each halving of resolution costs 4x the cases —</text>
    <text x="400" y="94" fill="var(--muted)" font-size="8">power gets expensive fast</text>
  </g>
</svg>
^ Because the MDE falls with the square root of n, halving it takes four times the data and quartering it sixteen times — so buying resolution by adding cases has steep diminishing returns, which is why pairing (which cuts variance for free) matters.

For four of the five sizes, a null result means nothing — the eval could not have detected the effect you care about, so its silence is uninformative. Only at n=500, where the MDE finally drops below the effect, does a null carry the meaning people casually assign to it: that there is no difference worth caring about. The verdict is not about the result you got; it is about what result the eval was capable of producing, which is why you compute the MDE before you run, not after you are disappointed.

**A non-significant eval result means no detectable difference, not no difference — so before reading a null as "equivalent," compute the minimum detectable effect, and a real 6-point gap is invisible at n=20 (MDE 27 pts) yet clear at n=500 (MDE 5 pts); a null is evidence of absence only once the MDE is below the effect you would care about, otherwise it is just a measurement too coarse to see.**

### The self-test

The `--check` mode plants the bug — reading a small-eval null as equivalence — and proves it: the small eval cannot detect the true effect, its MDE dwarfs that effect, a large eval can detect the same effect, and the MDE shrinks with n.

```
# $ python3 power.py --check
#   the small eval (n=20) CANNOT detect the 6-pt effect = True (MDE 27 pts)
#   the small eval's MDE is far larger than the true effect = True (27 vs 6 pts)
#   the large eval (n=500) CAN detect the same effect = True (MDE 5 pts)
#   the MDE strictly shrinks as n grows = True
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 power.py --check`

And the resolution improves monotonically with data — more cases, a finer eval, never coarser:

```
# power.py:110-111 — COMPLETE (the MDE strictly shrinks as n grows)
    mdes = [mde(pa, pb, n, z) for n in sorted(data["sample_sizes"])]
    mde_shrinks = all(mdes[i] > mdes[i + 1] for i in range(len(mdes) - 1))
```

The pairing of `small_blind` and `large_detects` is the whole argument: the same true effect, unchanged, is undetectable at one sample size and detectable at another, so detectability is a property of the eval, not of the systems. Concluding "no difference" from the n=20 eval reports a fact about the sample size and mistakes it for a fact about the systems.

```
# power.py:97-105 — COMPLETE (the same effect: blind at small n, detectable at large n)
    small_blind = not can_detect(pa, pb, small, z)
    print("  the small eval (n=%d) CANNOT detect the %.0f-pt effect = %s (MDE %.0f pts)"
          % (small, 100 * effect, small_blind, 100 * mde(pa, pb, small, z)))

    small_underpowered = mde(pa, pb, small, z) > 2 * effect
    print("  the small eval's MDE is far larger than the true effect = %s (%.0f vs %.0f pts)"
          % (small_underpowered, 100 * mde(pa, pb, small, z), 100 * effect))

    large_detects = can_detect(pa, pb, large, z)
```

### The running tally

| n per system | MDE (pts) | detects 6-pt effect? | a null there means |
|---|---|---|---|
| 20 | 27.5 | no | nothing (blind) |
| 50 | 17.4 | no | nothing (blind) |
| 100 | 12.3 | no | nothing (blind) |
| 200 | 8.7 | no | nothing (blind) |
| 500 | 5.5 | yes | no meaningful effect |

Read the MDE column against the last one: the meaning of a null flips exactly when the MDE crosses below the 6-point effect, between n=200 and n=500. Above that, "no significant difference" is a statement about the eval's blindness; below it, the same words become a statement about the systems. The MDE is the translator, and without it every null is ambiguous — you cannot tell blindness from equivalence by looking at the p-value alone, only by knowing what the eval could have seen.

### What we did not settle

This is the sample-size half of power; a full treatment has more. The MDE here uses a fixed z for the interval; true power also involves the type-II error rate (the chance of missing a real effect even when it exceeds the MDE), so a rigorous power calculation targets, say, 80% power, which pushes the required n a bit higher than the bare CI-crossing used here. Paired evals (the same cases run through both systems, as in `evals-inter-01`) cut the variance and so shrink the MDE for a given n — often dramatically — which is the cheapest way to buy power. The effect size you plug in should be the smallest difference worth acting on, chosen before the eval, not the difference you happened to observe. And a null with a reported MDE ("no difference detected down to 5 points") is far more honest than a bare null. The invariant: never read a null result without its minimum detectable effect.

## Build

The build in one paragraph: before trusting any non-significant eval result, compute the minimum detectable effect for your sample size — roughly the confidence-interval half-width on the difference, which shrinks with the square root of n — and compare it to the smallest difference you would care about; if the MDE is larger, the eval is underpowered and its null means nothing, so either collect more cases or report the null together with its MDE rather than as "equivalent." Decide the effect size worth detecting before running, pair the eval to cut variance and shrink the MDE, target a real power level rather than bare CI-crossing, and never let a bare p-value stand in for detectability.

We opened on the MDE table. The number that proves the point is the same effect being blind at small n and detectable at large:

```
# modules/evals-and-statistics/code/evals-inter-07/ — COMPLETE, run from that directory
$ python3 power.py --check
  the small eval (n=20) CANNOT detect the 6-pt effect = True (MDE 27 pts)
  the large eval (n=500) CAN detect the same effect = True (MDE 5 pts)
```

Now build your own. Take a real head-to-head with a plausible true effect and compute the MDE across the sample sizes you might run. Your number to beat is not the p-value; it is **the minimum detectable effect at your planned n versus the smallest difference you would act on** — if the MDE is larger, your eval cannot support a "no difference" conclusion. Find the n where the MDE drops below your effect. Bring back the MDE at your current size. Good luck.

## Definition of done

- [ ] A standard error of the difference in two rates that shrinks with n
- [ ] A minimum detectable effect (the CI half-width on the difference)
- [ ] A detectability test comparing the true effect to the MDE
- [ ] The MDE computed across a range of sample sizes
- [ ] Confirmation a small eval cannot detect the true effect (its null is uninformative)
- [ ] Confirmation a large eval can detect the same effect, and the MDE shrinks with n
- [ ] `python3 power.py --check` printing SELF-TEST PASS: small_blind, small_underpowered, large_detects, mde_shrinks
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why is "no significant difference" not the same as "no difference"? What is the other explanation for a null?
2. What is the minimum detectable effect, and how does it change as the sample size grows?
3. The true effect was 6 points and unchanged throughout. Why was it undetectable at n=20 but detectable at n=500?
4. Why must you decide the effect size worth detecting before running the eval, not after?
5. Your own head-to-head was analyzed for power. What was the MDE at your planned n, and could it detect the effect you cared about?

## External resources

- Any statistics text's chapter on power analysis and sample-size determination — my summary: how power, effect size, alpha, and n interlock, and why you fix three to solve for the fourth before collecting data; read it for the type-II error rate this module simplifies away.
- Cohen, *Statistical Power Analysis for the Behavioral Sciences* — my summary: the standard reference arguing that most null results in practice are underpowered rather than true nulls; read it for why "absence of evidence" is so often misread.
- This hub, *evals-inter-01* (the interval that decides whether B beat A) — read it for the paired-difference interval that both detects a real effect and, run before the study, gives you the MDE that tells you whether a null is trustworthy.
