---
id: evals-inter-16
title: Blind the LLM judge to provenance — or self-preference bias crowns its own family's answer
topic: evals-and-statistics
level: intermediate
status: ready
time: 21 min
summary: An LLM judge that can see which model wrote each answer scores its own family's higher — self-preference bias — so on close comparisons the bias flips the verdict toward its own, and the eval reports a win a neutral grader would call a loss. The damage is concentrated on close cases (where the true gap is smaller than the bias) and always points the same way. On 5 cases with a +2 self-preference bonus, the biased judge is right 3 of 5 (wrongly favoring its own on the two close cases) while the blinded judge is right on all 5.
eli5: If a judge in a contest can see that one entry is from their own team, they tend to score it a little higher — not on purpose, just bias. On close calls that tips the win to their team even when the other entry was better. The fix is to hide the names, so the judge scores the work, not the team.
---

## Why this module

An LLM judge that knows which model produced each answer is not a neutral referee, and the direction of its thumb on the scale is toward itself.

Using an LLM to judge model outputs is standard — cheaper and faster than human raters, and good enough for many comparisons. But a judge is itself a model, and judges exhibit self-preference bias: they systematically score answers from their own model family higher than a fair grader would. When you use a judge to compare its own family's output against a competitor's — which is exactly what you do when you evaluate your model with a judge from the same family — the judge tips the scale toward its own answer. It is not lying; it genuinely rates its own family's style higher, the way a person unconsciously favors work that resembles their own.

The bias changes outcomes precisely on the comparisons that matter. A competitor answer that is far better still wins despite the bias — the true quality gap swamps the bonus. But a competitor answer that is only slightly better loses to the bias: the judge adds its self-preference bonus to its own answer, and that is enough to flip a close verdict. So the errors are concentrated on the close cases, which are the ones an eval most needs to get right, because those are where the models are actually competitive and where the eval's conclusion is in doubt. On the blowouts the eval was never going to be wrong; on the toss-ups, the bias decides.

Worse, every error points the same way — toward the judge's own family. It is not random noise that averages out over many cases; it is a systematic, one-directional tilt, so it biases the aggregate result, not just individual verdicts. Run enough close comparisons and your model's measured win rate is inflated by however often the bias flipped a toss-up. The fix is to blind the judge to provenance: strip which model produced each answer before the judge sees them, so it grades on content alone. With provenance hidden the self-preference bonus has nothing to attach to, and the judge scores by true quality.

On the fixture, a biased judge (a +2 bonus to its own answer) gets 3 of 5 verdicts right, wrongly favoring its own on the two close cases; the blinded judge gets all 5 right.

**An LLM judge scores its own family's answers higher (self-preference bias), so on close comparisons — where the true gap is smaller than the bias — it flips the verdict toward itself, and because every such error points the same way it inflates the aggregate result; blinding the judge to provenance removes the bonus and restores judgment by content.**

## Concepts

Self-preference bias is a threshold effect, which is why it targets close cases. The judge decides by comparing scores, and the bias adds a fixed bonus to its own answer's score. That bonus changes the decision only when it is large enough to reverse the comparison — that is, when the competitor's true advantage is smaller than the bonus. Above that margin, the competitor wins anyway; below it, the bias flips the result. So the set of affected cases is exactly the band where the two answers are within the bias of each other, and everything outside that band is judged correctly. The narrower the true quality gap, the more the bias matters — and eval sets are often deliberately full of close comparisons, because those are the informative ones.

<svg role="img" aria-label="Random errors scatter both ways and cancel in the aggregate; self-preference errors all point one way and add up" viewBox="0 0 470 170" width="470" height="170">
  <rect x="0" y="0" width="470" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">random noise cancels; a one-directional bias accumulates</text>
  <line x1="235" y1="44" x2="235" y2="150" stroke="var(--line)"/>
  <text x="30" y="46" font-family="var(--mono)" font-size="8" fill="var(--muted)">random errors</text>
  <g fill="var(--muted)"><circle cx="180" cy="62" r="4"/><circle cx="290" cy="62" r="4"/><circle cx="200" cy="76" r="4"/><circle cx="270" cy="76" r="4"/></g>
  <text x="120" y="66" font-family="var(--mono)" font-size="7" fill="var(--muted)">↔ cancel</text>
  <text x="300" y="66" font-family="var(--mono)" font-size="7" fill="var(--muted)">→ ~0 net</text>
  <text x="30" y="112" font-family="var(--mono)" font-size="8" fill="var(--s2)">self-preference</text>
  <g fill="var(--s2)"><circle cx="290" cy="122" r="4"/><circle cx="320" cy="122" r="4"/><circle cx="350" cy="122" r="4"/><circle cx="380" cy="122" r="4"/></g>
  <text x="250" y="112" font-family="var(--mono)" font-size="7" fill="var(--s2)">all toward own →</text>
  <text x="250" y="140" font-family="var(--mono)" font-size="7" fill="var(--s2)">net shift, inflates the aggregate</text>
</svg>
^ Random judging errors land on both sides of the truth and average out, but every self-preference error lands on the same side, so they sum into a net shift of the reported result.

The one-directional nature is what makes it a bias rather than noise, and it is the more dangerous property. Random judging errors scatter in both directions and partly cancel when you aggregate: a model wrongly favored on one case is wrongly penalized on another, and the average is roughly right. Self-preference errors all favor the same side, so they add up — the judge's own family's measured win rate is systematically inflated by the fraction of close cases the bias flipped. A metric can be precise (low variance across runs) and still badly biased; self-preference attacks accuracy, not precision, and you cannot fix it by running more cases, because more cases just accumulate more same-direction errors.

Blinding works because the bias needs provenance to attach to. The self-preference bonus is applied to "my family's answer," so the judge must know which answer is its family's to apply it. Remove that information — present the two answers unlabeled, in a way that does not reveal the source — and there is nothing for the bonus to key on, so the judge scores both by content. This is the same logic as blind review in academia and blind auditions in orchestras: hide the identity that triggers the bias, and the evaluation is made on the work. It is a clean fix precisely because the bias is provenance-triggered, not a general inability to judge quality.

Self-preference is one of a family of LLM-judge biases, and blinding is one of a family of debiasing moves. Position bias (favoring the first- or last-presented answer) is fixed by judging both orders and averaging; verbosity bias (favoring longer answers) by controlling for length; self-preference by blinding provenance. The cautions: blinding provenance is not always sufficient (a judge may still recognize its own family's style even unlabeled, so a genuinely independent judge, or a human, is the stronger control for high-stakes comparisons), and you should measure the bias, not just assume it — compare the judge's verdicts to a neutral grader on a calibration set. But the default hygiene is clear: never let a judge see which model it is scoring when one of them is its own family, and prefer a judge from a different family (or a panel) for comparisons that decide anything.

**The bias is a threshold effect that flips only close cases and always in its own favor, so it damages accuracy (not precision) and cannot be averaged away; blinding removes it because the self-preference bonus needs provenance to attach to — with independent judges or humans as the stronger control when style leaks through.**

## Worked example

The fixture is a set of head-to-head cases and the self-preference bonus.

```json filename=modules/evals-and-statistics/code/evals-inter-16/cases.json:3-10 COMPLETE
  "bias": 2,
  "cases": [
    {"q_own": 5, "q_other": 8},
    {"q_own": 5, "q_other": 6},
    {"q_own": 7, "q_other": 4},
    {"q_own": 6, "q_other": 7},
    {"q_own": 3, "q_other": 9}
  ]
```

Each case has the true quality of the judge's own answer and the competitor's, from a neutral grader. The truly better answer is the higher quality; the judge picks the higher score, and a biased judge adds the bias to its own answer's score.

```python filename=modules/evals-and-statistics/code/evals-inter-16/selfpref.py:42-49 COMPLETE
def true_better(case):
    """The genuinely better answer by quality (ties go to 'other', the neutral choice)."""
    return "own" if case["q_own"] > case["q_other"] else "other"


def judge_pick(case, bias):
    """The judge picks the higher-scoring answer; a biased judge adds `bias` to its own answer's score."""
    return "own" if case["q_own"] + bias > case["q_other"] else "other"
```

Accuracy is the fraction of cases where the judge's pick matches the truly better answer.

```python filename=modules/evals-and-statistics/code/evals-inter-16/selfpref.py:52-53 COMPLETE
def accuracy(cases, bias):
    return round(sum(judge_pick(c, bias) == true_better(c) for c in cases) / len(cases), 3)
```

The blinded judge is just the same function with bias 0. Predict: the biased judge flips the close cases (where the competitor leads by less than 2) to its own, and is right on the blowouts; the blinded judge is right on all. Look at the verdicts.

```text filename=modules/evals-and-statistics/code/evals-inter-16/selfpref.py --verdicts
VERDICTS — true-better vs biased judge (+2 to own) vs blinded judge
--------------------------------------------------------------
  case  q_own  q_other  truth   biased   blinded
  1     5      8        other   other    other
  2     5      6        other   own      other  <- biased wrong
  3     7      4        own     own      own
  4     6      7        other   own      other  <- biased wrong
  5     3      9        other   other    other
--------------------------------------------------------------
  the bias flips the close cases toward 'own'.
```

Cases 1 and 5 are blowouts — the competitor leads by 3 and 6, more than the bias of 2 — so the biased judge still (correctly) picks the competitor. Case 3 the own answer is genuinely better, so both judges pick it. Cases 2 and 4 are the close ones: the competitor leads by just 1, less than the bias, so the biased judge adds 2 to its own score (5→7 beats 6; 6→8 beats 7) and wrongly picks its own answer, while the blinded judge correctly picks the competitor. The two errors are exactly the two close cases, and both favor the judge's own family. Now the accuracy.

```text filename=modules/evals-and-statistics/code/evals-inter-16/selfpref.py --accuracy
ACCURACY — judge accuracy and how often it picks its own answer
----------------------------------------------------------
  biased judge:   accuracy 0.600   picks own 0.600
  blinded judge:  accuracy 1.000   picks own 0.200
  ground truth:                    own is better 0.200 of the time
----------------------------------------------------------
  the biased judge picks own more than the truth warrants.
```

The biased judge is right on 3 of 5 (0.600) and the blinded judge on all 5 (1.000). The tell is in the "picks own" column: the truth is that the own answer is better only 20% of the time (1 of 5), and the blinded judge picks own exactly that often (0.200) — but the biased judge picks own 60% of the time (0.600), three times what the quality warrants. The bias inflated the own-answer win rate from a true 20% to a reported 60%, entirely by flipping the close cases. An eval run through this judge would report the own model winning most comparisons when it deserves to win one in five.

<svg role="img" aria-label="Five cases on a quality-gap axis; the two cases where the competitor leads by less than the bias are flipped to own by the biased judge, the blowouts are not" viewBox="0 0 470 180" width="470" height="180">
  <rect x="0" y="0" width="470" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">competitor's true lead per case vs the bias band (±2)</text>
  <line x1="45" y1="110" x2="450" y2="110" stroke="var(--line)"/>
  <rect x="45" y="60" width="130" height="100" fill="var(--s2)" opacity="0.18"/>
  <text x="52" y="74" font-family="var(--mono)" font-size="7" fill="var(--s2)">bias band: lead ≤ 2 → flipped to own</text>
  <line x1="175" y1="55" x2="175" y2="160" stroke="var(--s2)" stroke-dasharray="3 2"/>
  <g font-family="var(--mono)" font-size="8">
    <circle cx="130" cy="110" r="6" fill="var(--s2)"/><text x="120" y="135" fill="var(--s2)">c2 (+1)</text>
    <circle cx="145" cy="90" r="6" fill="var(--s2)"/><text x="140" y="52" fill="var(--s2)">c4 (+1)</text>
    <circle cx="255" cy="110" r="6" fill="var(--acc-line)"/><text x="243" y="135" fill="var(--acc-ink)">c1 (+3)</text>
    <circle cx="360" cy="110" r="6" fill="var(--acc-line)"/><text x="348" y="135" fill="var(--acc-ink)">c5 (+6)</text>
  </g>
  <text x="200" y="170" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">outside the band: competitor wins despite the bias</text>
</svg>
^ Cases 2 and 4, where the competitor leads by less than the bias, fall inside the bias band and are flipped to the judge's own answer; the blowouts (c1, c5) lie outside it and are judged correctly.

## Build

Reproduce the verdicts. Pure standard library, deterministic, so the biased 0.600 accuracy and the blinded 1.000 come out exactly.

Run `--verdicts` for the per-case picks, `--accuracy` for the summary, `--check` for the gate. The own-pick rate — how often the judge chose its own answer — is what exposes the inflation against the true 20%.

```python filename=modules/evals-and-statistics/code/evals-inter-16/selfpref.py:56-57 COMPLETE
def own_pick_rate(cases, bias):
    return round(sum(judge_pick(c, bias) == "own" for c in cases) / len(cases), 3)
```

<svg role="img" aria-label="Bars: biased judge accuracy 0.6 and own-pick 0.6; blinded accuracy 1.0 and own-pick 0.2 matching the true 0.2" viewBox="0 0 470 165" width="470" height="165">
  <rect x="0" y="0" width="470" height="165" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">accuracy and own-pick rate (truth: own better 0.20)</text>
  <line x1="45" y1="130" x2="450" y2="130" stroke="var(--line)"/>
  <line x1="45" y1="45" x2="450" y2="45" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="360" y="41" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">1.0</text>
  <text x="70" y="40" font-family="var(--mono)" font-size="8" fill="var(--s2)">biased</text>
  <rect x="70" y="79" width="45" height="51" fill="var(--s2)"/>
  <text x="66" y="145" font-family="var(--mono)" font-size="7" fill="var(--muted)">acc .60</text>
  <rect x="125" y="79" width="45" height="51" fill="var(--s1)"/>
  <text x="121" y="145" font-family="var(--mono)" font-size="7" fill="var(--muted)">own .60</text>
  <text x="280" y="40" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">blinded</text>
  <rect x="280" y="45" width="45" height="85" fill="var(--acc-line)"/>
  <text x="276" y="145" font-family="var(--mono)" font-size="7" fill="var(--muted)">acc 1.0</text>
  <rect x="335" y="113" width="45" height="17" fill="var(--acc-line)"/>
  <text x="331" y="145" font-family="var(--mono)" font-size="7" fill="var(--muted)">own .20</text>
</svg>
^ The biased judge's own-pick rate (0.60) is triple the true rate (0.20) that the blinded judge matches, and its accuracy (0.60) is well below the blinded 1.00 — the inflation and the accuracy loss are the same bias seen two ways.

The self-test pins that the blinded judge is perfect, the biased judge is worse, its errors all favor its own, and they are exactly the close cases.

```python filename=modules/evals-and-statistics/code/evals-inter-16/selfpref.py:93-96 COMPLETE
    blinded_perfect = accuracy(cases, 0) == 1.0
    print("  the blinded judge matches the true-better answer every time = %s (%.3f)" % (blinded_perfect, accuracy(cases, 0)))

    biased_less_accurate = accuracy(cases, bias) < accuracy(cases, 0)
    print("  the biased judge is less accurate than the blinded one = %s (%.3f vs %.3f)"
          % (biased_less_accurate, accuracy(cases, bias), accuracy(cases, 0)))
```

```text filename=modules/evals-and-statistics/code/evals-inter-16/selfpref.py --check
SELF-TEST — the biased judge favors its own on close cases and is less accurate; blinding fixes it
----------------------------------------------------------------------------------------------------
  the blinded judge matches the true-better answer every time = True (1.000)
  the biased judge is less accurate than the blinded one = True (0.600 vs 1.000)
  every biased error wrongly favors the judge's own answer = True (cases [2, 4])
  the flipped cases are exactly those where own trailed by <= the bias = True
  the biased judge picks its own answer more often than blinded = True (0.600 vs 0.200)
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  blinded_perfect=True  biased_less_accurate=True  errors_favor_own=True  flips_are_close=True  own_rate_inflated=True
```

Five True flags. Blinded_perfect: blinding gives 1.000 accuracy. Biased_less_accurate: the biased judge drops to 0.600. Errors_favor_own: both of its errors (cases 2 and 4) wrongly picked its own answer — the one-directional tilt. Flips_are_close: those cases are exactly the ones where the competitor led by no more than the bias. Own_rate_inflated: the biased judge picks its own answer 0.600 of the time versus the blinded 0.200. The errors-favor-own flag is the signature of a bias rather than noise — the mistakes are not scattered, they all lean the same way, which is what makes them accumulate in the aggregate.

**The errors-favor-own flag is what makes this a bias and not noise — every mistake tilts toward the judge's own family, so the errors add up across cases and inflate the aggregate win rate instead of canceling out.**

## Definition of done

You are done when you reproduce the flipped close cases and the blinding fix, and can explain why the bias attacks accuracy.

Concretely: `--verdicts` shows the biased judge flipping cases 2 and 4 to its own while the blinded judge is correct; `--accuracy` shows biased 0.600 / blinded 1.000, with the biased "picks own" at 0.600 versus a true 0.200; `--check` prints PASS with five True flags. You can explain that self-preference is a threshold effect that flips only cases within the bias of a tie and always toward the judge's own family, that this is a systematic bias (not noise) so it inflates the aggregate and cannot be averaged away, and that blinding removes it because the bonus needs provenance to attach to. You can name the sibling biases (position, verbosity) and their fixes, and the caveat that style may leak through blinding.

The habit to carry: never let an LLM judge see which model produced each answer when one of them is from the judge's own family — blind the provenance, and for comparisons that decide anything, prefer a judge from a different family, a panel, or human raters. When your model's judged win rate is suspiciously high, especially on close comparisons, check whether the judge shares its family and whether it could see provenance; measure the bias against a neutral grader on a calibration set rather than assuming it away.

## Boss fight

The instructive failure is a leaderboard that ranks a lab's own model first because the lab's own model is the judge.

A team evaluates several models with an LLM judge, and the judge happens to be from the same family as one of the contestants. That contestant tops the leaderboard, and the result is used to claim state-of-the-art. But many of its wins are close comparisons the judge flipped in its own family's favor; a neutral judge (or blinded provenance) ranks it lower. The leaderboard measured the judge's self-preference as much as the model's quality. The fix is to use an independent judge (from a different family) or a panel of judges, blind the answers' provenance, and calibrate the judge against human labels on a sample — after which the inflated model settles to its true rank. The tell is a judge and a top contestant sharing a model family.

Your turn, two moves. First, size the bias against the quality spread: shrink all the true quality gaps (make every case a near-tie) and confirm the biased judge's accuracy collapses toward picking its own every time, while the blinded judge stays accurate — because the closer the field, the more of it falls inside the bias band, which is why competitive evals are the most corrupted. Second, model the aggregate inflation: run many close cases where own is truly better half the time, and confirm the biased judge reports a win rate well above 50% while the blinded judge reports about 50% — showing the one-directional bias shifts the headline number, not just individual verdicts.

## External resources

Research on self-preference in LLM judges (e.g. Panickssery et al., "LLM Evaluators Recognize and Favor Their Own Generations," 2024) documents that models rate their own outputs higher and connects it to self-recognition, motivating provenance blinding and independent judges.

The broader LLM-as-judge bias literature (Zheng et al.'s "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena," and surveys of position, verbosity, and self-enhancement biases) catalogs the biases and their mitigations, of which blinding and swapping are the standard ones.

Work on blind review and blind auditions (the Goldin and Rouse orchestra study) is the general evidence that hiding identity removes identity-triggered bias, which is exactly the mechanism blinding a judge relies on.
