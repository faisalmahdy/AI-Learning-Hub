---
id: teach-inter-10
title: Target the edge of ability — items too easy or too hard teach almost nothing, and by the same amount
topic: teaching-and-portability
level: intermediate
status: ready
time: 22 min
summary: The learning signal from a problem is largest where the outcome is uncertain — near even odds — and vanishes when the problem is trivial or hopeless. Over 30 items a policy that targets the learner's current skill reaches skill 3.000, while too-easy and too-hard policies both stall at 0.841 — the same value, because p(1−p) is symmetric.
eli5: If you only practice things you can already do, you don't get better — you just prove you can do them. If you only try things way too hard, you fail and learn nothing from the failure. You improve fastest on things you get right about half the time: hard enough to be worth it, easy enough to have a shot.
---

## Why this module

A tutor's most important decision is how hard the next problem should be, and both easy and hard are wrong in the same way.

The instinct is to make problems easy — students succeed, feel good, stay motivated. But a problem you were always going to get right teaches you nothing: the success confirms a skill you already had and moves you nowhere. The opposite instinct, to push with hard problems, fails for the mirror reason: a problem far beyond your reach produces a failure you cannot learn from, because you had no foothold to begin with. Both extremes feel like practice and neither is. The session goes by, the learner is either bored or frustrated, and the skill needle barely moves.

The signal in a problem — the amount it can teach — is largest exactly where the outcome is in doubt. When you have roughly even odds, the result actually resolves something: it tells you which way a genuinely uncertain skill fell, and that is what drives improvement. This is the same principle that makes an experiment informative only when its outcome is uncertain, and it is why "desirable difficulty" is desirable. The best next problem is the one at the edge of your ability, where you might get it and might not.

We will model a learner and run three difficulty policies over thirty problems: one that stays well below the learner's skill, one well above, and one that tracks it exactly. The targeted policy will climb to skill 3.000. The too-easy and too-hard policies will both stall at 0.841 — and the fact that they stall at the *same* number, not just similar ones, is the lesson: a problem you were 92% going to solve and one you were 8% going to solve carry identical, tiny amounts of learning.

**The learning in a problem peaks where the outcome is uncertain and vanishes at both extremes, so easy and hard waste the item equally — the edge of ability is where practice pays.**

## Concepts

Model a learner with a single skill number and each problem with a difficulty number. The probability the learner solves the problem is the logistic function of the difference: skill minus difficulty. When skill far exceeds difficulty, that probability is near one; when difficulty far exceeds skill, near zero; when they match, one half. This is the standard item-response shape, and it captures the intuition that you usually beat easy problems and usually lose to hard ones.

The load-bearing assumption is what an item teaches. The learning gain is proportional to p·(1−p), where p is the success probability. That expression is the variance of the outcome — the uncertainty of a coin with bias p — and it is maximal at p = 0.5, where it equals 0.25, and falls to zero as p approaches either 0 or 1. It encodes the principle directly: the more certain the outcome, the less the item teaches. A 0.95-probability item teaches 0.95 × 0.05 = 0.0475 worth; a 0.05-probability item teaches 0.05 × 0.95 = 0.0475 — identical. Their symmetry is not a coincidence; p(1−p) is symmetric about 0.5, so equally-certain outcomes on either side are equally uninformative.

That symmetry is the surprising part and worth sitting with. It says an item you would almost certainly get right and one you would almost certainly get wrong are equally worthless for learning — the easy problem and the impossible problem are the same mistake. Intuition treats easy problems as at least a little useful ("review!") and hard problems as ambitious ("stretch!"), but under this model both are near-zero, and the review problem is exactly as wasteful as the impossible one. The only useful region is the middle.

A policy that targets difficulty to the learner's current skill keeps every item near p = 0.5, harvesting the maximum 0.25-per-item signal every time, and — crucially — it keeps doing so as the learner improves, because it re-aims at the new, higher skill each step. Fixed-difficulty policies drift out of the useful zone: hold difficulty constant and as the learner grows, once-hard problems become easy and stop teaching. Adaptive targeting is what keeps the learner perpetually at their own edge.

**Learning gain is p(1−p), the outcome's uncertainty, maximal at even odds and symmetric about it — so the useful problems are the middling ones, and a good policy re-aims at the learner's rising skill.**

## Worked example

The fixture is the simulation's parameters — the three policies as difficulty offsets from the learner's current skill.

```json filename=modules/teaching-and-portability/code/teach-inter-10/learning.json:7-13 COMPLETE
  "start_skill": 0.0,
  "items": 30,
  "learning_rate": 0.4,
  "policies": {
    "too_easy": -2.5,
    "targeted": 0.0,
    "too_hard": 2.5
```

Skill starts at 0, thirty items, learning rate 0.4. The too-easy policy sets each problem 2.5 below the learner's skill; too-hard sets it 2.5 above; targeted sets it exactly at skill.

```text filename=modules/teaching-and-portability/code/teach-inter-10/difficulty.py --policies
POLICIES — difficulty each sets, relative to the learner's current skill
--------------------------------------------------------
  too_easy   offset -2.5   -> 2.5 below skill
  targeted   offset +0.0   -> at skill (even odds)
  too_hard   offset +2.5   -> 2.5 above skill
--------------------------------------------------------
  start skill=0.0, 30 items, learning rate=0.4.
```

The success probability is the logistic of skill minus difficulty.

```python filename=modules/teaching-and-portability/code/teach-inter-10/difficulty.py:40-41 COMPLETE
def sigmoid(x):
    return 1 / (1 + math.exp(-x))
```

The simulation applies a policy for thirty items: each step, set the difficulty, compute the success probability, gain p(1−p) worth of skill, and move on.

```python filename=modules/teaching-and-portability/code/teach-inter-10/difficulty.py:46-56 COMPLETE
def simulate(offset, start_skill, items, lr):
    """Run `items` steps of a policy that sets difficulty = current skill + offset. Returns (final, trace)."""
    skill = start_skill
    trace = []
    for _ in range(items):
        difficulty = skill + offset
        p = sigmoid(skill - difficulty)   # success probability on this item
        gain = lr * p * (1 - p)           # learning signal, maximal at p = 0.5
        skill += gain
        trace.append((p, gain, skill))
    return skill, trace
```

Predict before running. Targeted keeps difficulty at skill, so p = 0.5 every item, gain 0.4 × 0.25 = 0.1 per item, thirty items, final skill 3.0. Too-easy sits 2.5 below skill, so p = sigmoid(2.5) ≈ 0.924, gain 0.4 × 0.924 × 0.076 ≈ 0.028 per item, final ≈ 0.84. Too-hard is the mirror: p ≈ 0.076, same gain, same final. Run it.

```text filename=modules/teaching-and-portability/code/teach-inter-10/difficulty.py --run
RUN — skill gained over 30 items, per policy
--------------------------------------------------------------
  policy      final skill   mean success   mean gain/item
  too_easy      0.841         0.924         0.0280
  targeted      3.000         0.500         0.1000
  too_hard      0.841         0.076         0.0280
--------------------------------------------------------------
  targeted keeps success near 0.5 and learns most; the extremes stall together.
```

Targeted reaches 3.000 at a mean success rate of exactly 0.500 — even odds, maximum signal, 0.1 skill per item. Too-easy reaches 0.841 at a 92.4% success rate; too-hard reaches 0.841 at a 7.6% success rate. The two extremes learned the same 0.028 per item and stalled at the identical 0.841, one from winning almost always and one from losing almost always. Targeting more than tripled the skill of either, and the whole difference is where on the p(1−p) curve each policy lived.

<svg role="img" aria-label="Final skill after 30 items: too-easy 0.84, too-hard 0.84, targeted 3.00" viewBox="0 0 460 160" width="460" height="160">
  <rect x="0" y="0" width="460" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">final skill after 30 items</text>
  <line x1="60" y1="130" x2="440" y2="130" stroke="var(--line)"/>
  <rect x="90" y="107" width="70" height="23" fill="var(--s2)" stroke="var(--line)"/><text x="112" y="101" font-family="var(--mono)" font-size="10" fill="var(--ink)">0.84</text><text x="92" y="146" font-family="var(--mono)" font-size="9" fill="var(--muted)">too-easy</text>
  <rect x="200" y="43" width="70" height="87" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="220" y="37" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">3.00</text><text x="205" y="146" font-family="var(--mono)" font-size="9" fill="var(--muted)">targeted</text>
  <rect x="310" y="107" width="70" height="23" fill="var(--s2)" stroke="var(--line)"/><text x="332" y="101" font-family="var(--mono)" font-size="10" fill="var(--ink)">0.84</text><text x="312" y="146" font-family="var(--mono)" font-size="9" fill="var(--muted)">too-hard</text>
</svg>
^ Targeting builds more than triple the skill of either extreme, and the two extremes are exactly level — easy and hard fail identically.

<svg role="img" aria-label="The learning-gain curve p times one-minus-p versus success probability: a hump peaking at 0.5, near zero at 0 and 1, with too-easy at 0.92, targeted at 0.5, too-hard at 0.08 marked" viewBox="0 0 460 190" width="460" height="190">
  <rect x="0" y="0" width="460" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">learning gain p(1−p) vs success probability p</text>
  <line x1="40" y1="150" x2="440" y2="150" stroke="var(--line)"/>
  <line x1="40" y1="150" x2="40" y2="40" stroke="var(--line)"/>
  <path d="M40 150 Q240 -10 440 150" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <text x="34" y="166" font-family="var(--mono)" font-size="9" fill="var(--muted)">p=0</text><text x="230" y="166" font-family="var(--mono)" font-size="9" fill="var(--muted)">0.5</text><text x="420" y="166" font-family="var(--mono)" font-size="9" fill="var(--muted)">1.0</text>
  <line x1="240" y1="50" x2="240" y2="150" stroke="var(--acc-ink)" stroke-dasharray="3 2"/><circle cx="240" cy="50" r="4" fill="var(--acc-line)"/><text x="248" y="52" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">targeted 0.25</text>
  <circle cx="70" cy="135" r="4" fill="var(--s2)"/><text x="40" y="128" font-family="var(--mono)" font-size="8" fill="var(--s2)">too-hard 0.08</text>
  <circle cx="410" cy="135" r="4" fill="var(--s2)"/><text x="356" y="128" font-family="var(--mono)" font-size="8" fill="var(--s2)">too-easy 0.92</text>
  <text x="120" y="100" font-family="var(--mono)" font-size="9" fill="var(--muted)">both extremes sit at the same low height</text>
</svg>
^ The learning-gain curve is a symmetric hump: targeted sits at the peak, and too-easy and too-hard sit at the same low height on opposite sides.

The mean success rate is just the average p over the run — the readout of where a policy lived on the curve.

```python filename=modules/teaching-and-portability/code/teach-inter-10/difficulty.py:59-60 COMPLETE
def mean_success(trace):
    return sum(step[0] for step in trace) / len(trace)
```

<svg role="img" aria-label="Skill trajectories over 30 items: targeted climbs in a straight line to 3.0, while too-easy and too-hard trace the same low curve to 0.84" viewBox="0 0 460 190" width="460" height="190">
  <rect x="0" y="0" width="460" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">skill vs items (30 items)</text>
  <line x1="50" y1="160" x2="440" y2="160" stroke="var(--line)"/>
  <line x1="50" y1="160" x2="50" y2="35" stroke="var(--line)"/>
  <text x="24" y="45" font-family="var(--mono)" font-size="9" fill="var(--muted)">3.0</text><text x="30" y="164" font-family="var(--mono)" font-size="9" fill="var(--muted)">0</text>
  <line x1="50" y1="160" x2="420" y2="45" stroke="var(--acc-ink)" stroke-width="2"/><circle cx="420" cy="45" r="4" fill="var(--acc-line)"/><text x="330" y="42" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">targeted 3.00</text>
  <path d="M50 160 Q230 130 420 128" fill="none" stroke="var(--s2)" stroke-width="2"/><circle cx="420" cy="128" r="4" fill="var(--s2)"/><text x="300" y="145" font-family="var(--mono)" font-size="9" fill="var(--s2)">easy & hard 0.84</text>
</svg>
^ Targeting climbs steadily because it stays at even odds every step; the extremes flatten almost immediately and both trace the same stalled curve.

## Build

Reproduce the trajectories. Pure standard library, deterministic, so 3.000, 0.841, 0.841 come out exactly.

Run `--policies` for the setup, `--run` for the three trajectories, `--check` for the gate. The self-test pins the whole story: targeted wins, the two extremes stall at the identical value, targeted holds even odds, and the margin is large.

```python filename=modules/teaching-and-portability/code/teach-inter-10/difficulty.py:98-107 COMPLETE
    easy, _ = simulate(pol["too_easy"], s0, n, lr)
    targ, targ_trace = simulate(pol["targeted"], s0, n, lr)
    hard, _ = simulate(pol["too_hard"], s0, n, lr)

    targeted_wins = targ > easy and targ > hard
    print("  the targeted policy gains the most skill = %s (targeted %.3f vs easy %.3f, hard %.3f)"
          % (targeted_wins, targ, easy, hard))

    extremes_equal = abs(easy - hard) < 1e-9
    print("  too-easy and too-hard stall at the SAME skill = %s (%.3f = %.3f)" % (extremes_equal, easy, hard))
```

The `extremes_equal` check — `abs(easy - hard) < 1e-9` — is the one that proves the model's claim rather than just illustrating it. It demands the too-easy and too-hard final skills be equal to nine decimals, not merely close. That exact equality is the signature of the p(1−p) symmetry: a 92% item and an 8% item are equidistant from even odds, so they carry identical learning. If the two extremes stalled at different values, the symmetry story would be wrong. Here is the full gate.

```text filename=modules/teaching-and-portability/code/teach-inter-10/difficulty.py --check
SELF-TEST — targeted beats both extremes; too-easy and too-hard waste the item equally
------------------------------------------------------------------------------------
  the targeted policy gains the most skill = True (targeted 3.000 vs easy 0.841, hard 0.841)
  too-easy and too-hard stall at the SAME skill = True (0.841 = 0.841)
  the targeted policy keeps success at even odds = True (mean p 0.500)
  targeting more than doubles the skill of either extreme = True (3.000 vs 0.841)
------------------------------------------------------------------------------------
SELF-TEST PASS  targeted_wins=True  extremes_equal=True  targeted_even_odds=True  big_margin=True
```

Four True flags. Targeted_wins: targeting gains the most skill. Extremes_equal: too-easy and too-hard stall at the identical 0.841. Targeted_even_odds: the targeted policy holds a 0.500 success rate. Big_margin: targeting more than doubles either extreme — here more than triples it. The equal-extremes flag is the counterintuitive heart of it: easy and hard are not "less good and worse," they are exactly equally wasteful.

**The self-test demands the two extremes be equal to nine decimals, because that exact symmetry — not just their both being low — is what the p(1−p) model predicts.**

## Definition of done

You are done when you reproduce the trajectories and can explain the symmetry.

Concretely: `--run` shows targeted reaching 3.000 at 0.500 success while both extremes stall at 0.841; `--check` prints PASS with four True flags. You can state the learning-gain model — proportional to p(1−p), the outcome's uncertainty — and explain why it is maximal at even odds and zero at the extremes. You can explain why too-easy and too-hard stall at the *same* skill (symmetry of p(1−p) about 0.5), which is the non-obvious prediction. And you can say why a targeting policy keeps winning as the learner improves: it re-aims at the rising skill, so every item stays at the edge.

The habit to carry: when choosing the next problem, aim for the one the learner has roughly even odds on, and re-aim as they improve. Treat a stream of easy wins and a stream of crushing failures as the same failure mode — both are off the useful part of the curve.

## Boss fight

The instructive failure is a course that feels great and teaches little.

A learning app optimizes for engagement, and easy problems are engaging — students get them right, streaks build, retention numbers look good. The app serves problems well within each student's ability, everyone feels smart, and skill growth is a fraction of what it could be, because almost every item is on the flat right end of the p(1−p) curve. The mirror failure is a hardcore course that serves brutal problems to signal rigor; students fail most of them, learn little from failures they can't act on, and drop out. Both courses mistake a feeling — comfort or challenge — for learning, and both leave the same amount of skill on the table. The fix is to measure success rate and steer it toward the middle, not toward comfort or toward difficulty.

Your turn, two moves. First, find the exact break-even for the extremes. The too-easy policy at offset −2.5 and too-hard at +2.5 stall identically; predict what happens at offset −1.0 versus −4.0 and confirm the pattern: the closer the offset is to 0, the higher the final skill, and any offset and its negation give the identical result. Plot final skill against offset and you get the p(1−p) hump reflected. Second, test the real-world refinement. This model peaks at p = 0.5, but the well-known "85% rule" for certain error-correcting learners puts the optimum at about 0.85 success, not 0.50 — because their learning signal is not p(1−p) but something skewed toward more success. Change the gain function to peak at 0.85 (weight it toward higher p) and predict how the targeted offset would shift: the tutor should aim slightly easier than even odds, serving problems the learner gets right most but not all of the time. Sit with why the exact optimum depends on the learner's update rule, while the shape of the lesson — a peak in the middle, waste at both ends — does not.

## External resources

Wilson, Shenhav, Straccia, and Cohen, "The Eighty Five Percent Rule for optimal learning" (2019), derives the optimal training difficulty for gradient-descent learners and lands on ~85% success — the skewed refinement of the even-odds intuition this module builds.

The "desirable difficulties" literature from Robert and Elizabeth Bjork makes the same case for human learners: conditions that feel harder and slower during practice, including appropriately difficult items, produce better long-term learning than easy, fluent practice.

For the item-response and adaptive-testing view, any treatment of Item Response Theory and computerized adaptive testing covers selecting items near a test-taker's ability to maximize information — the same p(1−p)-style information function, applied to measuring rather than teaching.
