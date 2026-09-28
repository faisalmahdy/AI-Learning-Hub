---
id: teach-inter-13
title: Size the mastery quiz to the decision — a three-item gate misclassifies masters and non-masters alike
topic: teaching-and-portability
level: intermediate
status: ready
time: 21 min
summary: A mastery gate turns a noisy measurement into a yes/no decision, and a short quiz is too noisy to decide reliably. With a non-master at 60% and a master at 90% skill and a 75%-correct gate, a 3-item quiz misclassifies with total error 0.487 — a coin flip — failing the true master 27% of the time. Lengthening the quiz shrinks the noise: total error falls to 0.237 at 10 items, 0.137 at 20, and 0.037 at 40. Quiz length is set by the decision's reliability, not by taste.
eli5: If you flip a slightly-weighted coin only three times, you can't tell it apart from a fair one — you need many flips. A mastery quiz is the same: ask too few questions and you can't tell who really knows the material from who got lucky, so you both promote people too early and hold back people who are ready. More questions, clearer answer.
---

## Why this module

A mastery quiz is a measurement, and a short measurement is a noisy one — so a short quiz makes an unreliable advance-or-hold decision no matter how you set the threshold.

The whole point of a mastery gate is to convert a fuzzy quantity — how much of this does the learner actually know? — into a crisp decision: enough, advance; not enough, hold. But the quiz score you decide from is a sample, and a small sample is noisy. From a noisy score you get an unreliable decision, and unreliable cuts both ways. A non-master catches a lucky run and clears the gate — a false pass, which promotes a learner over a gap that will compound as later material builds on it. A master hits one unlucky item and misses — a false fail, which wastes their time re-studying what they know and teaches them to distrust the tutor.

A three-item "get them all right" gate, which feels strict, is bad at both errors at once. A learner who genuinely knows 60% of the material still answers three-for-three about a fifth of the time, so a fifth of unqualified learners sail through. Meanwhile a learner who knows 90% fails to run the table more than a quarter of the time, so you bounce true masters constantly. The gate feels rigorous because it demands perfection, but demanding perfection on a tiny sample just amplifies the noise — perfection on three items is easy to reach by luck and easy to miss by luck.

The fix is not a cleverer threshold; it is more items. Each item is an independent noisy sample of the same underlying skill, so averaging more of them shrinks the noise around the true score, and a proportion threshold placed between the master and non-master levels separates them cleanly once there are enough items. How many is enough is not a matter of taste — it is set by how reliable the decision has to be, the same way a poll's sample size is set by the margin of error it must beat. A mastery gate is a hypothesis test, and it needs to be powered.

On the fixture a non-master truly knows 60% and a master 90%, and the gate requires 75% correct. At 3 items the total misclassification rate is 0.487 — barely better than a coin flip — with the master failing 27% of the time. Lengthen the quiz and the noise shrinks: total error falls to 0.237 at 10 items, 0.137 at 20, and 0.037 at 40. Same learners, same threshold; only the length changed.

**A mastery gate turns a noisy quiz score into a decision, and a short quiz is too noisy to decide from — a 3-item gate both passes non-masters by luck and fails masters by a slip; lengthening the quiz shrinks the sampling noise, so the number of items is set by the reliability the decision requires.**

## Concepts

The right way to see a mastery quiz is as an estimate of a probability. The learner has some true per-item success probability — 0.6 for the non-master, 0.9 for the master — and the quiz score is an estimate of it from n samples. Like any such estimate, its noise is governed by the sample size: the standard error of a proportion falls like one over the square root of n. So the score from a 3-item quiz scatters wildly around the truth, while the score from a 40-item quiz hugs it. The gate compares that noisy estimate to a threshold, and when the estimate is noisy relative to the gap between master and non-master, the comparison is unreliable.

The two error types trade off against the threshold but cannot both be driven down without more items. Raise the pass fraction and you catch more non-masters (fewer false passes) but bounce more masters (more false fails); lower it and the reverse. On a short quiz the two error curves overlap so much that no threshold makes both small — you are just choosing which mistake to make more of. This is exactly the sensitivity/specificity trade-off of any classifier, and the only way to shrink both errors together is to reduce the noise, which means more items. The threshold chooses the balance; the length chooses the quality.

<svg role="img" aria-label="On a short quiz the master and non-master score distributions overlap heavily; on a long quiz they separate cleanly on either side of the threshold" viewBox="0 0 470 190" width="470" height="190">
  <rect x="0" y="0" width="470" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">score distributions: short quiz (top) vs long quiz (bottom)</text>
  <line x1="235" y1="30" x2="235" y2="96" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="240" y="40" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">gate 75%</text>
  <path d="M40,92 Q130,44 220,92" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <path d="M150,92 Q250,52 350,92" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <text x="60" y="86" font-family="var(--mono)" font-size="8" fill="var(--s2)">non-master</text>
  <text x="300" y="86" font-family="var(--mono)" font-size="8" fill="var(--s1)">master</text>
  <text x="150" y="112" font-family="var(--mono)" font-size="8" fill="var(--muted)">short: wide, overlapping → gate can't separate</text>
  <line x1="235" y1="120" x2="235" y2="180" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <path d="M150,176 Q195,140 240,176" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <path d="M250,176 Q305,132 360,176" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <text x="40" y="150" font-family="var(--mono)" font-size="8" fill="var(--muted)">long: narrow, split → clean decision</text>
</svg>
^ On a short quiz the two learners' score distributions are wide and overlap across the threshold, so the gate misclassifies both ways; more items narrow each distribution onto its own true skill, pulling them to opposite sides of the 75% line.

Placing the threshold between the two skill levels is what lets length work. Put the pass fraction at 0.75, midway between the non-master's 0.6 and the master's 0.9, and as n grows each learner's score concentrates on their own true value — the non-master's near 0.6, the master's near 0.9 — pulling away from the 0.75 line on opposite sides. The gap between 0.6 and 0.9 is the signal; the sampling noise is what blurs it; more items sharpen the signal until the two learners land cleanly on opposite sides of the threshold. If the threshold sat at 0.62 or 0.88, no amount of length would separate them well, because one true level would straddle the line.

This reframes quiz design as a power calculation, and it is the missing piece behind "advance on mastery." Deciding to gate on mastery assumes you can measure mastery, and measuring it to a given reliability takes a computable number of items — more when the master and non-master are close in skill, fewer when they are far apart, more when the cost of a wrong advance is high. Treating three items as sufficient because it is convenient is the same error as running an under-powered experiment and trusting the result: the decision inherits the noise you refused to average out. A mastery gate you have not sized is a decision you have not actually made.

**A quiz score is a proportion estimate whose noise falls like one over the square root of n, so on a short quiz the master and non-master score distributions overlap and no threshold separates them; a threshold placed between the two skill levels separates them only once enough items shrink the noise — quiz length is a power calculation.**

## Worked example

The fixture is two learners' true skills, a pass fraction, and a set of quiz lengths.

```json filename=modules/teaching-and-portability/code/teach-inter-13/quiz.json:3-6 COMPLETE
  "nonmaster_skill": 0.60,
  "master_skill": 0.90,
  "pass_fraction": 0.75,
  "quiz_lengths": [3, 10, 20, 40]
```

The gate requires 75% correct — between the non-master's 0.6 and the master's 0.9. The chance a learner clears the gate is the probability of at least the required number of correct items, computed exactly from the binomial.

```python filename=modules/teaching-and-portability/code/teach-inter-13/reliable.py:42-49 COMPLETE
def p_at_least(k, n, p):
    """Probability of getting at least k of n items right at per-item skill p -- exact binomial."""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def need(n, frac):
    """Items required to pass a length-n quiz at a pass fraction -- rounded up."""
    return math.ceil(frac * n)
```

A false pass is a non-master clearing the gate; a false fail is a master missing it. Both come straight from `p_at_least`.

```python filename=modules/teaching-and-portability/code/teach-inter-13/reliable.py:52-59 COMPLETE
def false_pass(n, frac, nonmaster):
    """A non-master clears the gate by luck."""
    return p_at_least(need(n, frac), n, nonmaster)


def false_fail(n, frac, master):
    """A master misses the gate by an unlucky slip."""
    return 1.0 - p_at_least(need(n, frac), n, master)
```

Predict: at 3 items both errors are large — the non-master passes often and the master fails often — and both shrink as the quiz lengthens, because the scores concentrate on the true skills. Run it.

```text filename=modules/teaching-and-portability/code/teach-inter-13/reliable.py --rates
RATES — misclassification at each quiz length (non-master 60%, master 90%, gate 75%)
------------------------------------------------------------------
  items   need   false pass   false fail   total error
  3       3           0.216        0.271        0.487
  10      8           0.167        0.070        0.237
  20      15          0.126        0.011        0.137
  40      30          0.035        0.001        0.037
------------------------------------------------------------------
  more items shrink the noise, so the total error falls.
```

At 3 items the gate is a coin flip: total error 0.487, with the non-master passing 21.6% of the time and — worse — the master failing 27.1% of the time. That 3-item gate rejects more than a quarter of genuinely ready learners. Lengthen to 10 items and total error more than halves to 0.237; at 20 it is 0.137; at 40 it is 0.037, with the master essentially never wrongly failed (0.001) and the non-master rarely passed (0.035). The same two learners and the same 75% threshold move from indistinguishable to cleanly separated purely by asking more questions.

<svg role="img" aria-label="Total misclassification error falling from 0.487 at 3 items to 0.037 at 40 items, split into false pass and false fail" viewBox="0 0 470 195" width="470" height="195">
  <rect x="0" y="0" width="470" height="195" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">total error (false pass + false fail) by quiz length</text>
  <line x1="45" y1="160" x2="450" y2="160" stroke="var(--line)"/>
  <line x1="45" y1="45" x2="45" y2="160" stroke="var(--line)"/>
  <line x1="45" y1="137" x2="450" y2="137" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="360" y="133" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">coin flip 0.5</text>
  <g><rect x="70" y="48" width="60" height="72" fill="var(--s1)"/><rect x="70" y="120" width="60" height="40" fill="var(--s2)"/></g>
  <g><rect x="170" y="106" width="60" height="16" fill="var(--s1)"/><rect x="170" y="122" width="60" height="38" fill="var(--s2)"/></g>
  <g><rect x="270" y="128" width="60" height="3" fill="var(--s1)"/><rect x="270" y="131" width="60" height="29" fill="var(--s2)"/></g>
  <g><rect x="370" y="152" width="60" height="1" fill="var(--s1)"/><rect x="370" y="153" width="60" height="7" fill="var(--s2)"/></g>
  <text x="78" y="174" font-family="var(--mono)" font-size="8" fill="var(--muted)">3: .487</text>
  <text x="176" y="174" font-family="var(--mono)" font-size="8" fill="var(--muted)">10: .237</text>
  <text x="276" y="174" font-family="var(--mono)" font-size="8" fill="var(--muted)">20: .137</text>
  <text x="376" y="174" font-family="var(--mono)" font-size="8" fill="var(--muted)">40: .037</text>
  <text x="150" y="40" font-family="var(--mono)" font-size="8" fill="var(--s1)">top: false fail (master bounced)</text>
</svg>
^ The total-error bar collapses from a near-coin-flip 0.487 at 3 items to 0.037 at 40; the false-fail slice (bouncing a true master) is what shrinks fastest as items are added.

## Build

Reproduce the rates. Pure standard library — `math.comb` for exact binomial probabilities — so the 0.487 coin-flip at 3 items and the 0.037 at 40 come out exactly.

Run `--rates` for the table, `--gate` for what each length requires and the naive all-correct short gate, `--check` for the gate. The gate view makes the trap concrete: the 3-item 75% gate is literally "all correct," and its false fail is 0.271.

```text filename=modules/teaching-and-portability/code/teach-inter-13/reliable.py --gate
GATE — what each quiz length requires, plus the naive all-correct short gate
------------------------------------------------------------------
   3 items: need 3 correct (75%)
  10 items: need 8 correct (75%)
  20 items: need 15 correct (75%)
  40 items: need 30 correct (75%)
------------------------------------------------------------------
  naive gate — all 3 correct:
    non-master passes 0.216 of the time (false pass)
    master passes only 0.729, so fails 0.271 (false fail)
```

The total error a decision inherits is just the two error rates added — one number that summarizes the gate's unreliability at a given length.

```python filename=modules/teaching-and-portability/code/teach-inter-13/reliable.py:62-63 COMPLETE
def total_error(n, frac, nonmaster, master):
    return false_pass(n, frac, nonmaster) + false_fail(n, frac, master)
```

<svg role="img" aria-label="Both error rates fall as items are added: false fail drops steeply from 0.271 to near zero, false pass falls more slowly from 0.216 to 0.035" viewBox="0 0 470 185" width="470" height="185">
  <rect x="0" y="0" width="470" height="185" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">false-pass and false-fail vs quiz length (3, 10, 20, 40)</text>
  <line x1="45" y1="150" x2="450" y2="150" stroke="var(--line)"/>
  <line x1="45" y1="40" x2="45" y2="150" stroke="var(--line)"/>
  <polyline points="80,90 200,110 320,122 440,143" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <g fill="var(--s2)"><circle cx="80" cy="90" r="3"/><circle cx="200" cy="110" r="3"/><circle cx="320" cy="122" r="3"/><circle cx="440" cy="143" r="3"/></g>
  <text x="230" y="106" font-family="var(--mono)" font-size="8" fill="var(--s2)">false pass: 0.216 → 0.035</text>
  <polyline points="80,68 200,131 320,148 440,150" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <g fill="var(--s1)"><circle cx="80" cy="68" r="3"/><circle cx="200" cy="131" r="3"/><circle cx="320" cy="148" r="3"/><circle cx="440" cy="150" r="3"/></g>
  <text x="90" y="62" font-family="var(--mono)" font-size="8" fill="var(--s1)">false fail: 0.271 → 0.001 (steep)</text>
  <text x="66" y="166" font-family="var(--mono)" font-size="8" fill="var(--muted)">3</text>
  <text x="316" y="166" font-family="var(--mono)" font-size="8" fill="var(--muted)">20</text>
  <text x="432" y="166" font-family="var(--mono)" font-size="8" fill="var(--muted)">40</text>
</svg>
^ Both error rates fall with length, but the false-fail (bouncing a master) collapses fastest — the short quiz's worst failure is the one that most items fix.

The self-test pins the story: the shortest quiz is near a coin flip, it fails a true master too often, the total error falls monotonically as the quiz lengthens, and the longest quiz is reliable.

```python filename=modules/teaching-and-portability/code/teach-inter-13/reliable.py:101-109 COMPLETE
    short_unreliable = errs[0] > 0.4
    print("  the shortest quiz is barely better than a coin flip = %s (total error %.3f at %d items)"
          % (short_unreliable, errs[0], lens[0]))

    short_fails_master = false_fail(lens[0], frac, ms) > 0.2
    print("  the shortest quiz fails a true master too often = %s (false fail %.3f)"
          % (short_fails_master, false_fail(lens[0], frac, ms)))

    error_shrinks = all(errs[i] > errs[i + 1] for i in range(len(errs) - 1))
```

```text filename=modules/teaching-and-portability/code/teach-inter-13/reliable.py --check
SELF-TEST — a short quiz misclassifies both ways; lengthening it drives the total error down
--------------------------------------------------------------------------------------------
  the shortest quiz is barely better than a coin flip = True (total error 0.487 at 3 items)
  the shortest quiz fails a true master too often = True (false fail 0.271)
  total error falls monotonically as the quiz lengthens = True ([0.487, 0.237, 0.137, 0.037])
  the longest quiz is reliable = True (total error 0.037 at 40 items)
--------------------------------------------------------------------------------------------
SELF-TEST PASS  short_unreliable=True  short_fails_master=True  error_shrinks=True  long_reliable=True
```

Four True flags. Short_unreliable: at 3 items the total error is 0.487, a coin flip. Short_fails_master: and 0.271 of that is bouncing true masters, the error that erodes trust fastest. Error_shrinks: 0.487, 0.237, 0.137, 0.037 — each length cuts the error. Long_reliable: at 40 items the total error is 0.037, a decision you can actually stand behind. The monotone sequence is the whole argument: reliability is bought with items, and the price is computable.

**The false-fail flag is the sharp one — a 3-item all-correct gate bounces 27% of genuinely ready learners, so a gate that feels strict is in fact the least reliable, because perfection on a tiny sample is mostly noise.**

## Definition of done

You are done when you reproduce the error curve and can explain why more items, not a better threshold, is the fix.

Concretely: `--rates` shows total error falling 0.487, 0.237, 0.137, 0.037 across lengths 3, 10, 20, 40, with false pass and false fail both shrinking; `--gate` shows the 3-item 75% gate is "all correct" with a 0.271 false-fail; `--check` prints PASS with four True flags. You can explain that a quiz score is a proportion estimate whose noise falls like one over the square root of n, that the two error types trade off against the threshold but only length shrinks both, and that placing the threshold between the two skill levels is what lets length separate them. You can state that sizing a mastery quiz is a power calculation set by the required reliability and the gap between master and non-master.

The habit to carry: size a mastery gate to the decision it makes — more items when the pass/hold cost is high or when learners cluster near the threshold, fewer when the skill gap is wide — and never read a short "all correct" quiz as strong evidence of mastery. When a tutor keeps bouncing learners who clearly know the material, or advancing ones who clearly do not, suspect an under-sized quiz before blaming the threshold. A gate you have not sized is a decision you have not made.

## Boss fight

The instructive failure is an adaptive tutor that thrashes because every mastery check is three items.

A tutor gates each skill on three questions, all correct to advance. Learners complain of two opposite things: some breeze past skills they clearly have not learned (and then drown on the dependent material), while others get stuck re-taking a check on a skill they obviously know, failing on a single careless slip. Both complaints are the same bug — a 3-item gate has a false-pass rate near 0.22 and a false-fail rate near 0.27, so it misclassifies almost half the time. The team's instinct is to raise the bar, but "all correct" is already the strictest a 3-item quiz allows; the bar is not the problem, the sample size is. The fix is to lengthen the check to the reliability the promotion decision needs — often 10 to 20 items — and to set the pass fraction between the mastery and non-mastery levels rather than at 100%.

Your turn, two moves. First, find the length that hits a target reliability. Pick a total-error budget of 0.10 and search quiz lengths to find the smallest that clears it for this 0.6-versus-0.9 gap; then narrow the gap (non-master 0.75, master 0.90) and confirm you need many more items — closer skills demand a longer quiz, which is the power calculation made concrete. Second, hold the length fixed at 10 and sweep the pass fraction from 0.6 to 0.9; confirm no threshold makes both errors small at once (raising it trades false passes for false fails), so the trade-off is real and only length escapes it. That is the difference between choosing the balance of errors and choosing their size.

## External resources

Any introduction to classical test theory or criterion-referenced testing (e.g. the reliability chapters in a psychometrics text) covers exactly this: a mastery decision's reliability depends on test length, and the Spearman-Brown formula predicts how reliability grows as you add items.

Standard treatments of statistical power and sample size (e.g. Cohen) are the general form of the "size the quiz to the decision" argument — the number of observations needed is set by the effect size to detect and the error rates you will tolerate.

The mastery-learning literature (Bloom, and modern competency-based systems) motivates gating on mastery rather than time, and reading it alongside this module shows the gap it leaves: mastery must be measured reliably before it can be gated on, which is a test-length question.
