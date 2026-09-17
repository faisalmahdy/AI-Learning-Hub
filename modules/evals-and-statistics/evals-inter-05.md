---
id: evals-inter-05
title: LLM-as-judge position bias — judge both orders, or you score the slot not the answer
topic: evals-and-statistics
level: intermediate
status: ready
time: 8-10h
summary: A pairwise LLM judge that favors whichever answer is shown first confounds two things — which answer is better and which got the favored slot — so a verdict from one fixed order credits position, not merit, and on any pair whose quality gap is smaller than the position bias the slot wins. With a bias of 2, the single-order judge crowns A on a true tie and calls a pair wrong where B is better by 1, reporting both with full confidence. Judging both orders and trusting only verdicts that survive the swap fixes it: the two pairs whose winner flips are exactly the ones the judge cannot call, so two-order abstains on them and still matches truth on the clear pairs. The flip is the signal — a pair that changes winner when you swap the order was decided by presentation, not by the answer.
eli5: If a taste-tester always likes whatever they sip first, and you only ever hand them cup A first, they will keep saying A is better even when the cups are identical. The fix is to also hand them B first and see if they change their mind. If their pick flips when you swap the cups, they were judging the order, not the drink — so you should not trust that verdict at all.
---

## Why this module

LLM-as-judge is how most modern evals scale: instead of a human comparing two answers, a model does it, pairwise, at volume. It works well enough to be everywhere, and it carries a bias that quietly corrupts the results — the judge systematically prefers whichever answer occupies a particular slot, usually the first one shown. This module measures that position bias and builds the standard correction, because a pairwise eval run in a single fixed order does not measure answer quality; it measures answer quality plus a constant advantage handed to whoever got the favored position, and on close pairs the advantage decides.

The confound is exact. A single-order verdict combines two signals you cannot separate: is answer A actually better, and did A benefit from being shown first. When the true quality gap between the answers is larger than the position bias, quality wins and the verdict is right. But when the gap is smaller than the bias — a genuine tie, or a close call — the slot wins, and the judge confidently crowns the first answer on the strength of its position alone. You cannot detect this from the single verdict, because it looks identical to a real win. The fix is to judge both orders, A-then-B and B-then-A, and trust a verdict only when it survives the swap. A pair whose winner flips when you swap the presentation was decided by position, not merit, and the honest response is to abstain — record no winner — rather than to report a result the judge cannot actually stand behind.

You need the eval-measurement instinct from the earlier evals modules and nothing more. Everything runs offline against a pair fixture — four answer pairs with known true qualities and a modeled position bias — stdlib Python 3, `$0.00`. The judge here is a deterministic scoring rule standing in for a real model call, so the bias is exact and its effect checkable. The instinct to unlearn is that a judge's verdict is about the answers. A single-order verdict is about the answers and their slots together, and only swapping the order tells you which one you measured.

Here is the single-order judge, confidently wrong:

```
# modules/evals-and-statistics/code/evals-inter-05/ — COMPLETE, run from that directory
$ python3 judge.py --single

SINGLE — one order (A first); verdict vs truth (position bias = 2.0)
------------------------------------------------------------------
  p1  A_q=8 B_q=3  verdict=A  ok
  p2  A_q=5 B_q=5  verdict=A  <-- WRONG (truth tie)
  p3  A_q=5 B_q=6  verdict=A  <-- WRONG (truth B)
  p4  A_q=2 B_q=9  verdict=B  ok
```

run: 2026-08-26 · deterministic; qualities are a fixture · position bias 2.0 · `python3 judge.py --single`

Four pairs, and the single-order judge gets two wrong — a true tie it calls for A, and a pair where B is better it also calls for A — both because A was shown first. This module is why those two errors happen and how swapping the order catches them.

## Concepts

Named here so you can find them again; each is built below.

- **Pairwise judging** — asking a judge which of two answers is better; the scalable eval protocol.
- **Position bias** — a systematic preference for the answer in a particular slot (here, first).
- **The confound** — a single-order verdict mixes answer quality with the slot advantage.
- **Order swap** — judging both A-first and B-first to separate merit from position.
- **Flip** — a verdict that changes when the order is swapped; the mark of a bias-decided pair.
- **Abstain** — recording no winner when the verdict does not survive the swap.

## Worked example

Source: the position-bias problem documented in LLM-as-judge research (the "swap and average" or consistency protocols used to debias pairwise judging, as in MT-Bench and related work); the qualities and bias here stand in for a real judge so the flips and errors are exact and checkable.

Script and fixture: `modules/evals-and-statistics/code/evals-inter-05/` — `judge.py`, and `pairs.json`, four pairs with true qualities and a position bias of 2.0. Every command runs from there.

### The biased judge

The judge is a scoring rule with the bias baked in: it favors the first-presented answer by a fixed margin.

```
# judge.py:38-50 — COMPLETE (the judge favors the first slot; verdict as A or B)
def judge_once(first_q, second_q, bias):
    """The judge favors the FIRST-presented answer by `bias`. Returns 'first' or 'second'."""
    return "first" if first_q + bias >= second_q else "second"


def verdict_order(pair, bias, a_first):
    """Judge the pair in one order; return the winner as 'A' or 'B'."""
    if a_first:
        w = judge_once(pair["a_quality"], pair["b_quality"], bias)
        return "A" if w == "first" else "B"
    else:
        w = judge_once(pair["b_quality"], pair["a_quality"], bias)
        return "B" if w == "first" else "A"
```

The `first_q + bias >= second_q` is the whole bias: the first answer only has to come within `bias` of the second to win. With bias 2.0, the first answer wins whenever its quality is no more than 2 below the second's. `verdict_order` wraps this to track which answer, A or B, occupied the first slot. A real judge's bias is not this clean, but the structure is identical — a thumb on the scale for one position — and the clean version makes the consequence exact.

### Single order: the confound in action

The naive protocol judges once, with A always first.

```
# judge.py:55-57 — COMPLETE (the naive single-order protocol)
def single_order(pair, bias):
    """Judge once, A presented first (the naive protocol)."""
    return verdict_order(pair, bias, a_first=True)
```

Walk the four pairs from the cold open. Pair p1 (A 8, B 3): A is better by 5, well over the bias, so A wins honestly. Pair p4 (A 2, B 9): B is better by 7, so even with A first, B wins — quality overcomes the bias. Those two are correct. But p2 (A 5, B 5) is a true tie, and A wins only because `5 + 2 >= 5` — the slot decided it. And p3 (A 5, B 6): B is genuinely better, but `5 + 2 >= 6`, so the bias flips it to A — a real quality difference overturned by position. The single-order judge reports A for both p2 and p3 with no indication that anything is wrong, because a bias-driven verdict is indistinguishable from a merit-driven one when you only look once.

<svg viewBox="0 0 700 190" role="img" aria-label="Four pairs on a quality-gap axis. A vertical band of width equal to the position bias (2) around zero marks the danger zone. p1 (gap +5 for A) and p4 (gap -7, B) fall outside the band and are judged correctly. p2 (gap 0) and p3 (gap -1, B) fall inside the band and are decided by position, wrongly favoring A.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">true quality gap (A minus B); inside ±bias, the slot decides</text>
    <line x1="60" y1="110" x2="650" y2="110" stroke="var(--grid)"></line>
    <line x1="355" y1="40" x2="355" y2="130" stroke="var(--muted)"></line><text x="355" y="150" text-anchor="middle" fill="var(--muted)" font-size="8">0</text>
    <rect x="315" y="50" width="80" height="70" fill="var(--s2)" opacity="0.15"></rect>
    <text x="355" y="46" text-anchor="middle" fill="var(--s2)" font-size="8">±bias danger zone</text>
    <circle cx="560" cy="110" r="5" fill="var(--s1)"></circle><text x="560" y="98" text-anchor="middle" fill="var(--s1)" font-size="8">p1 (+5) ok</text>
    <circle cx="355" cy="110" r="5" fill="var(--s2)"></circle><text x="330" y="98" fill="var(--s2)" font-size="8">p2 (0)</text>
    <circle cx="335" cy="110" r="5" fill="var(--s2)"></circle><text x="300" y="128" fill="var(--s2)" font-size="8">p3 (-1)</text>
    <circle cx="150" cy="110" r="5" fill="var(--s1)"></circle><text x="150" y="98" text-anchor="middle" fill="var(--s1)" font-size="8">p4 (-7) ok</text>
    <text x="120" y="170" fill="var(--muted)" font-size="8">gaps bigger than the bias are safe; gaps inside it are decided by presentation order</text>
  </g>
</svg>
^ Pairs whose true quality gap exceeds the position bias (p1, p4) are judged on merit. Pairs inside the ±bias band (p2, p3) are decided by the slot — and a single-order protocol cannot tell you which band a pair is in.

### Two orders: the swap that reveals it

The fix judges both orders and trusts a verdict only if it survives the swap.

```
# judge.py:60-64 — COMPLETE (two-order: a winner must survive the swap, else abstain)
def two_order(pair, bias):
    """Judge both orders; a winner only counts if it survives the swap, else abstain."""
    ab = verdict_order(pair, bias, a_first=True)
    ba = verdict_order(pair, bias, a_first=False)
    return ab if ab == ba else "abstain"
```

Run it and the flips surface exactly where the danger zone predicted:

```
# $ python3 judge.py --swap
#   p1  A-first=A  B-first=A  holds            two-order=A
#   p2  A-first=A  B-first=B  FLIPS -> abstain two-order=abstain
#   p3  A-first=A  B-first=B  FLIPS -> abstain two-order=abstain
#   p4  A-first=B  B-first=B  holds            two-order=B
```

run: 2026-08-26 · deterministic · `python3 judge.py --swap`

<svg viewBox="0 0 700 190" role="img" aria-label="A 4x3 table. Rows p1..p4. Columns A-first, B-first, two-order. p1: A, A, A (green). p4: B, B, B (green). p2: A, B, abstain (the A and B differ, abstain highlighted). p3: A, B, abstain. The flip rows are marked.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">verdict by order; a row where A-first and B-first differ flips -> abstain</text>
    <g fill="var(--ink)"><text x="150" y="42">A-first</text><text x="270" y="42">B-first</text><text x="400" y="42">two-order</text></g>
    <g fill="var(--muted)"><text x="60" y="66">p1</text><text x="60" y="94">p4</text><text x="60" y="126">p2</text><text x="60" y="154">p3</text></g>
    <g fill="var(--s1)"><text x="165" y="66">A</text><text x="285" y="66">A</text><text x="425" y="66">A ✓</text><text x="165" y="94">B</text><text x="285" y="94">B</text><text x="425" y="94">B ✓</text></g>
    <g><text x="165" y="126" fill="var(--s1)">A</text><text x="285" y="126" fill="var(--s2)">B</text><text x="420" y="126" fill="var(--s2)">abstain</text>
       <text x="165" y="154" fill="var(--s1)">A</text><text x="285" y="154" fill="var(--s2)">B</text><text x="420" y="154" fill="var(--s2)">abstain</text></g>
    <line x1="50" y1="106" x2="500" y2="106" stroke="var(--grid)"></line>
    <text x="520" y="66" fill="var(--muted)" font-size="8">holds</text><text x="520" y="94" fill="var(--muted)" font-size="8">holds</text>
    <text x="520" y="126" fill="var(--s2)" font-size="8">FLIP</text><text x="520" y="154" fill="var(--s2)" font-size="8">FLIP</text>
  </g>
</svg>
^ The top two rows agree across orders and hold; the bottom two disagree — A when A is first, B when B is first — and two-order abstains. The flip is visible only because both orders were run.

For p1, A wins in both orders — the quality gap is real, so the verdict holds, and two-order reports A. For p4, B wins both ways, reported B. But p2 and p3 flip: A wins when shown first, B wins when shown first, because in each order the first slot's bias carries it. That flip is the judge telling you it cannot call the pair — the winner is whoever got the favored slot. Two-order abstains on both, which is the honest outcome: p2 really is a tie, and p3 is close enough that this judge cannot reliably rank it. The single-order protocol reported confident winners for both; the swap reveals those winners were artifacts of order.

**A single-order pairwise verdict confounds answer quality with the position bias, so on any pair whose quality gap is smaller than the bias the slot decides — judge both orders and trust only verdicts that survive the swap, because a flip marks a pair the judge cannot call and the honest verdict there is to abstain.**

### The self-test

The `--check` mode asserts the confound and the fix: single-order crowns the first slot on a tie and errs on a close pair, while two-order abstains on both and still matches truth on the clear pairs.

```
# $ python3 judge.py --check
#   single-order declares a winner on a TRUE TIE = True (p2 -> A)
#   two-order ABSTAINS on the tie = True (p2 -> abstain)
#   single-order gets a close pair WRONG (position beats a small quality gap) = True (p3 -> A, truth B)
#   two-order abstains on that close pair instead of erring = True (p3 -> abstain)
#   two-order matches truth on the CLEAR pairs = True (p1->A, p4->B)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 judge.py --check`

The most damaging assertion is the close pair, where the bias overturns a real quality difference:

```
# judge.py:113-119 — COMPLETE (single-order errs on a close pair; two-order abstains)
    close = pairs["p3"]
    single_close = single_order(close, bias)
    single_wrong = single_close != close["truly_better"]

    two_close = two_order(close, bias)
    two_abstains_close = two_close == "abstain"
```

`single_wrong` requires the single-order verdict on p3 to disagree with the truth (B), and `two_abstains_close` requires two-order to abstain there instead — an error converted into an honest non-answer.

The `crowns_first` line is the demonstration that the bias is real and directional: on a genuine tie, the single-order judge does not flip a coin, it reliably names the first slot. The `single_wrong` line shows the bias overturning an actual quality difference, the most damaging case. And the `clear_ok` line is the correctness anchor for the fix — two-order must still get the easy pairs right, so the swap protocol buys honesty on close pairs without sacrificing accuracy on clear ones; it abstains precisely and only where it should.

### The running tally

| pair | true gap | single-order | two-order | what decided it |
|---|---|---|---|---|
| p1 (8 vs 3) | +5 | A ✓ | A ✓ | merit |
| p4 (2 vs 9) | −7 | B ✓ | B ✓ | merit |
| p2 (5 vs 5) | 0 | A ✗ | abstain | position |
| p3 (5 vs 6) | −1 | A ✗ | abstain | position |

<svg viewBox="0 0 700 160" role="img" aria-label="Two summary bars over the four pairs. Single-order: 2 correct, 2 wrong (both wrong from position bias). Two-order: 2 correct, 2 abstained, 0 wrong. The two-order bar has no wrong segment.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">outcomes over the 4 pairs: correct / wrong / abstained</text>
    <text x="20" y="54" fill="var(--ink)">single-order</text>
    <rect x="150" y="42" width="220" height="18" fill="var(--s1)"></rect><text x="260" y="55" text-anchor="middle" fill="var(--panel)" font-size="8">2 correct</text>
    <rect x="370" y="42" width="220" height="18" fill="var(--s2)"></rect><text x="480" y="55" text-anchor="middle" fill="var(--panel)" font-size="8">2 WRONG</text>
    <text x="20" y="98" fill="var(--ink)">two-order</text>
    <rect x="150" y="86" width="220" height="18" fill="var(--s1)"></rect><text x="260" y="99" text-anchor="middle" fill="var(--panel)" font-size="8">2 correct</text>
    <rect x="370" y="86" width="220" height="18" fill="var(--muted)"></rect><text x="480" y="99" text-anchor="middle" fill="var(--panel)" font-size="8">2 abstained</text>
    <text x="150" y="130" fill="var(--muted)" font-size="8">the swap converts 2 confident errors into 2 honest abstentions — 0 wrong</text>
  </g>
</svg>
^ Single-order gets two right and two wrong; two-order gets the same two right and, instead of erring on the other two, abstains. The trade is confident wrongness for honest uncertainty — always the right trade in an eval.

Split the table at the bias. The top two pairs have gaps larger than the bias of 2, and both protocols agree with truth — the bias was there but harmless, overwhelmed by real quality. The bottom two have gaps inside the bias, and there single-order reports confident winners that are wrong or meaningless while two-order abstains. The whole value of the swap is on those bottom rows: it converts a false, confident verdict into an honest abstention, which is exactly the pairs where a single-order eval would silently mislead you about which answer is better.

### What we did not settle

Swapping is the minimum debiasing, not the maximum. A common protocol averages the two orders' scores rather than requiring agreement, which yields a graded result instead of an abstention and can be more powerful when you must rank everything. Position is not the only judge bias: verbosity bias (preferring longer answers), self-preference (a judge favoring its own model's style), and formatting bias all confound verdicts and need their own controls. The abstention rate itself is a useful diagnostic — a judge that flips on most pairs is too biased or too weak to use for that eval. And the whole approach assumes the true quality exists to be measured; calibrating the judge against human labels is the prior step. The rule here — judge both orders, trust only what survives the swap — is the floor every debiased judging protocol builds on.

## Build

The practice in one paragraph: never run a pairwise LLM judge in a single fixed order; judge every pair both ways and trust a verdict only if it survives the swap, abstaining when it flips; report the flip rate as a diagnostic of how biased the judge is on your task; and check for the other biases — verbosity, self-preference, formatting — with analogous controls. Calibrate the judge against human labels before trusting its verdicts at all, and treat a high abstention rate as a signal the judge is unfit for that comparison.

We opened on the single-order errors. The number that exposes them is the flip:

```
# modules/evals-and-statistics/code/evals-inter-05/ — COMPLETE, run from that directory
$ python3 judge.py --swap
  p2  A-first=A  B-first=B  FLIPS -> abstain two-order=abstain
  p3  A-first=A  B-first=B  FLIPS -> abstain two-order=abstain
```

Now run it on your own judge. Take a real pairwise LLM judge and a set of answer pairs, and judge each pair in both orders. Your number to beat is not the win rate; it is **the flip rate — the fraction of pairs whose winner changes when you swap the order — and whether your reported winners survive the swap**. Abstain on the flips and re-check your leaderboard. Bring back the flip rate and how many verdicts changed. Good luck.

## Definition of done

- [ ] A pairwise judging protocol run in both orders (A-first and B-first)
- [ ] Verdicts that survive the swap kept; flips converted to abstentions
- [ ] The flip rate reported as a measure of the judge's position bias
- [ ] Confirmation that single-order errs on close pairs (position beats a small quality gap)
- [ ] Confirmation that two-order abstains on the flips and still matches truth on clear pairs
- [ ] `python3 judge.py --check` printing SELF-TEST PASS: crowns-first, abstains-on-tie, single-wrong, two-abstains, clear-ok
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. What two signals does a single-order pairwise verdict confound, and why can you not separate them from one verdict?
2. On which pairs does the position bias decide the winner, and what determines whether a pair is in that danger zone?
3. What does a flip (a verdict that changes when you swap the order) tell you about a pair, and why is abstaining the honest response?
4. Two-order abstained on the tie and the close pair but still called the clear pairs. Why is that the desired behavior, not a loss of power?
5. Your own judge was run both orders. What was the flip rate, and how many of your reported winners did not survive the swap?

## External resources

- Zheng et al., *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena* (2023) — https://arxiv.org/abs/2306.05685 — my summary: the paper documenting position bias (and verbosity and self-enhancement bias) in LLM judges and the swap-based controls; read it for the measured magnitude of these biases and the protocols to counter them.
- Anthropic / general LLM-as-judge guidance on debiasing pairwise evals — my summary: practical protocols for order randomization, averaging both orders, and calibrating against human labels; read it for how debiased judging is run at scale.
- This hub, *evals-inter-01* — modules/evals-and-statistics/evals-inter-01.md — my summary: an earlier evals module on measuring judge quality; read it for the calibration step that must precede trusting any judge, biased or not.
