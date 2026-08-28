---
id: teach-inter-06
title: Fade the scaffolding as competence grows — full worked examples hurt an expert
topic: teaching-and-portability
level: intermediate
status: ready
time: 8-10h
summary: A worked example is scaffolding that helps a novice, who needs the steps, and hurts an expert, whose existing schema competes with the redundant steps — so learning gain rises with scaffolding below a reversal competence of 0.56 and falls above it, and full scaffolding takes the novice from 0.50 to 1.32 while taking the expert from 0.50 down to −0.12. A one-size-fits-all policy of always-full worked examples is optimal for the novice and actively harmful for the expert, scoring the cohort 1.98, while an adaptive policy that fades scaffolding to zero past the reversal point matches every learner and rescues the expert, scoring 2.60 and never underperforming the fixed policy for anyone. The right amount of scaffolding is not a constant; it depends on the learner and must fade as competence grows, which is the expertise-reversal effect.
eli5: Training wheels help someone who cannot ride a bike yet, but if you bolt them onto a pro's bike they just get in the way and slow them down. The help a beginner needs is exactly the thing that hinders an expert. So good teaching takes the training wheels off as the rider gets better, instead of leaving them on for everyone.
---

## Why this module

The hub is a curriculum, and a curriculum makes a choice on every module about how much to spell out — full worked examples with every step, or a bare problem to struggle through. The intuition is that more help is always better, so give everyone the fully worked version. That intuition is wrong in a specific, measurable way: heavy scaffolding that rescues a novice actively harms an expert, and a policy that ignores the difference leaves learning on the table. This module measures the expertise-reversal effect and the adaptive policy that respects it, because "how much to explain" is a decision every teacher and every learning system makes constantly, usually as a fixed default that is wrong for half the learners.

The mechanism is that scaffolding does two opposing things at once. It helps in proportion to what the learner does not yet know — a novice without the steps flounders, so the worked steps are pure gain. And it hurts in proportion to what the learner does know — an expert already has the schema, so processing the redundant steps costs attention that competes with, rather than adds to, their understanding. The net effect of more scaffolding is therefore the help minus the hurt, and that difference flips sign at a reversal competence: below it, more scaffolding raises learning; above it, more scaffolding lowers it. A fixed policy of full scaffolding sits on the right side of that line for experts, dragging them down, while an adaptive policy fades the scaffolding as competence grows — full for novices, none for experts — and matches each learner where they are.

You need the earlier teaching modules' framing of a learner with a measurable state. Everything runs offline against a learner fixture — a cohort at three competence levels and a model of scaffolding's help and harm — stdlib Python 3, `$0.00`. The model is a fixture standing in for the empirical effect, so the reversal and the policy comparison are exact. The instinct to unlearn is that more explanation is always more help. More explanation helps up to a point that depends on the learner, and past that point it is redundant load that subtracts from learning.

Here is the reversal, measured:

```
# modules/teaching-and-portability/code/teach-inter-06/ — COMPLETE, run from that directory
$ python3 scaffold.py --curve

CURVE — learning gain vs scaffolding (reversal at competence 0.56)
------------------------------------------------------------------
  learner   c     s=0.0   s=0.5   s=1.0   more scaffold helps?
  novice   0.10   0.50    0.91    1.32   yes
  middle   0.40   0.50    0.64    0.78   yes
  expert   0.90   0.50    0.19   -0.12   NO -- reversal
```

run: 2026-08-26 · deterministic; model is a fixture · reversal at 0.56 · `python3 scaffold.py --curve`

Full scaffolding lifts the novice from 0.50 to 1.32 and drags the expert from 0.50 to −0.12 — the same intervention, opposite effects, because the expert's competence turned the help into interference. This module is that sign flip and the policy that respects it.

## Concepts

Named here so you can find them again; each is built below.

- **Scaffolding** — support that walks a learner through steps, from a worked example (full) to a bare problem (none).
- **Competence** — how much the learner already knows, from novice (0) to expert (1).
- **Expertise reversal** — scaffolding that helps novices harming experts, because it duplicates their schema.
- **Reversal point** — the competence where more scaffolding stops helping and starts hurting.
- **Fixed-full policy** — always full scaffolding; the one-size-fits-all default.
- **Adaptive fading** — reducing scaffolding as competence grows, matching each learner.

## Worked example

Source: the expertise-reversal effect from cognitive-load theory (Kalyuga, Sweller) and the faded-worked-example research it motivates; the learner competences and the help/harm constants here stand in for the empirical effect so the reversal and the policy comparison are exact and checkable.

Script and fixture: `modules/teaching-and-portability/code/teach-inter-06/` — `scaffold.py`, and `learners.json`, three learners and the model constants. Every command runs from there.

### The model: help minus harm

Learning gain is an intrinsic amount (learning from doing the task at all) plus a scaffolding term that helps by what you do not know and hurts by what you do.

```
# scaffold.py:40-47 — COMPLETE (the gain model and where scaffolding stops helping)
def learning_gain(c, s, cfg):
    """Gain for competence c at scaffolding s: intrinsic + s*((1-c)*help - c*redundancy)."""
    return cfg["intrinsic"] + s * ((1 - c) * cfg["help"] - c * cfg["redundancy"])


def reversal_point(cfg):
    """The competence where more scaffolding stops helping: help / (help + redundancy)."""
    return cfg["help"] / (cfg["help"] + cfg["redundancy"])
```

The scaffolding term is `s * ((1-c)*help - c*redundancy)`. Read the bracket: `(1-c)*help` is the benefit, large when competence `c` is low; `c*redundancy` is the cost, large when `c` is high. Their difference is the coefficient of scaffolding `s`, and it is positive for low competence and negative for high. It crosses zero at `help / (help + redundancy)` — here `1.0 / 1.8 = 0.56` — which is the reversal point. Below competence 0.56, adding scaffolding raises the gain; above it, adding scaffolding lowers the gain. That single threshold is the whole phenomenon.

<svg viewBox="0 0 700 130" role="img" aria-label="A competence axis from 0 (novice) to 1 (expert) with a marked reversal point at 0.56. To the left, a region labelled 'more scaffolding helps'. To the right, a region labelled 'more scaffolding hurts'. The three learners are placed: novice at 0.1 and middle at 0.4 on the left, expert at 0.9 on the right.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">competence axis: the reversal point splits help from harm</text>
    <line x1="50" y1="70" x2="650" y2="70" stroke="var(--grid)"></line>
    <line x1="386" y1="45" x2="386" y2="95" stroke="var(--s2)" stroke-dasharray="4 3"></line><text x="386" y="40" text-anchor="middle" fill="var(--s2)" font-size="8">reversal 0.56</text>
    <rect x="50" y="62" width="336" height="8" fill="var(--s1)" opacity="0.3"></rect><text x="200" y="90" text-anchor="middle" fill="var(--s1)" font-size="8">more scaffolding HELPS</text>
    <rect x="386" y="62" width="264" height="8" fill="var(--s2)" opacity="0.3"></rect><text x="518" y="90" text-anchor="middle" fill="var(--s2)" font-size="8">more scaffolding HURTS</text>
    <circle cx="110" cy="70" r="4" fill="var(--s1)"></circle><text x="110" y="58" text-anchor="middle" fill="var(--s1)" font-size="8">novice .1</text>
    <circle cx="290" cy="70" r="4" fill="var(--s1)"></circle><text x="290" y="58" text-anchor="middle" fill="var(--s1)" font-size="8">middle .4</text>
    <circle cx="590" cy="70" r="4" fill="var(--s2)"></circle><text x="590" y="58" text-anchor="middle" fill="var(--s2)" font-size="8">expert .9</text>
    <g fill="var(--muted)" font-size="8"><text x="50" y="112">0 novice</text><text x="610" y="112">expert 1</text></g>
  </g>
</svg>
^ The novice and middle learner sit left of the reversal point, where scaffolding helps; the expert sits right of it, where it hurts. A fixed policy applies full scaffolding across the whole axis, including the harmful right side.

<svg viewBox="0 0 700 200" role="img" aria-label="Three lines of learning gain versus scaffolding from 0 to 1. The novice line rises steeply from 0.5 to 1.32. The middle line rises gently from 0.5 to 0.78. The expert line falls from 0.5 to -0.12, crossing below the others. A note marks that lines for competence below 0.56 rise and above it fall.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">learning gain vs scaffolding s (0 = bare problem, 1 = full worked example)</text>
    <line x1="60" y1="150" x2="640" y2="150" stroke="var(--grid)"></line>
    <line x1="60" y1="30" x2="60" y2="170" stroke="var(--grid)"></line>
    <line x1="60" y1="110" x2="640" y2="110" stroke="var(--grid)" stroke-dasharray="2 3"></line><text x="20" y="113" fill="var(--muted)" font-size="8">0.5</text>
    <polyline points="60,110 640,42" fill="none" stroke="var(--s1)" stroke-width="2.5"></polyline><text x="600" y="38" fill="var(--s1)" font-size="8">novice (0.1)</text>
    <polyline points="60,110 640,82" fill="none" stroke="var(--acc)" stroke-width="2"></polyline><text x="600" y="78" fill="var(--acc-ink)" font-size="8">middle (0.4)</text>
    <polyline points="60,110 640,164" fill="none" stroke="var(--s2)" stroke-width="2.5"></polyline><text x="600" y="168" fill="var(--s2)" font-size="8">expert (0.9)</text>
    <g fill="var(--muted)" font-size="8"><text x="60" y="185">s=0</text><text x="620" y="185">s=1</text></g>
    <text x="330" y="130" fill="var(--muted)" font-size="8">below reversal competence: rises · above it: falls</text>
  </g>
</svg>
^ All three lines start at the intrinsic 0.5 at zero scaffolding and fan out: the novice and middle lines rise with more scaffolding, the expert line falls below the start. The slope's sign is set entirely by whether competence is under or over the reversal point.

### The reversal in numbers

The curve view already showed it: at full scaffolding the novice gains 1.32, the middle learner 0.78, and the expert −0.12. The expert's negative is the striking part — full scaffolding did not merely help the expert less, it left them worse off than a bare problem would have (0.50 intrinsic). The redundant steps of a worked example are not neutral to an expert; they consume working memory that the expert would otherwise spend on the actual problem, so the fully-explained lesson is a net drain. A teacher who gives everyone the fully worked version is, for the experts in the room, handing them a lesson that teaches less than silence.

### Two policies: fixed versus adaptive

Now the decision. A fixed policy gives everyone full scaffolding; an adaptive policy fades it past the reversal point.

```
# scaffold.py:52-59 — COMPLETE (the one-size-fits-all policy vs adaptive fading)
def fixed_full(c, cfg):
    """One-size-fits-all: always full scaffolding (s = 1)."""
    return 1.0


def adaptive(c, cfg):
    """Fade scaffolding past the reversal point: full below it, none above."""
    return 1.0 if c < reversal_point(cfg) else 0.0
```

A policy's cohort score is just the total gain across learners under whatever scaffolding it assigns each:

```
# scaffold.py:62-63 — COMPLETE (total learning across the cohort under a policy)
def cohort_total(learners, policy, cfg):
    return sum(learning_gain(l["competence"], policy(l["competence"], cfg), cfg) for l in learners)
```

`fixed_full` ignores the learner entirely — scaffolding 1 for all. `adaptive` reads the competence: full scaffolding while it still helps (below 0.56), none once it would hurt (above). Run both over the cohort:

```
# $ python3 scaffold.py --policy
#   novice   c=0.10  fixed(s=1)= 1.32   adaptive(s=1)= 1.32
#   middle   c=0.40  fixed(s=1)= 0.78   adaptive(s=1)= 0.78
#   expert   c=0.90  fixed(s=1)=-0.12   adaptive(s=0)= 0.50
#   fixed total = 1.98   adaptive total = 2.60
```

run: 2026-08-26 · deterministic · `python3 scaffold.py --policy`

The two policies agree on the novice and the middle learner — both below the reversal point, both get full scaffolding, both gain the same. They diverge on the expert: fixed gives full scaffolding and scores −0.12, adaptive gives none and scores 0.50. That one difference moves the cohort total from 1.98 to 2.60. And critically, adaptive never does worse than fixed for anyone — it matches on the novices and beats on the expert — so it is not a trade that helps experts at novices' expense; it is a strict improvement that costs nothing. The fixed policy's only virtue is simplicity, and it pays for that simplicity with every expert it teaches.

<svg viewBox="0 0 700 180" role="img" aria-label="Per-learner gain under two policies. Novice: fixed 1.32, adaptive 1.32 (equal). Middle: fixed 0.78, adaptive 0.78 (equal). Expert: fixed -0.12 (bar below zero line), adaptive 0.50 (bar above). Totals: fixed 1.98, adaptive 2.60.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">gain per learner: fixed-full vs adaptive (zero line marked)</text>
    <line x1="60" y1="110" x2="640" y2="110" stroke="var(--grid)"></line>
    <text x="35" y="113" fill="var(--muted)" font-size="8">0</text>
    <g><rect x="90" y="52" width="24" height="58" fill="var(--s2)"></rect><rect x="116" y="52" width="24" height="58" fill="var(--s1)"></rect><text x="115" y="128" text-anchor="middle" fill="var(--muted)">novice</text></g>
    <g><rect x="250" y="76" width="24" height="34" fill="var(--s2)"></rect><rect x="276" y="76" width="24" height="34" fill="var(--s1)"></rect><text x="275" y="128" text-anchor="middle" fill="var(--muted)">middle</text></g>
    <g><rect x="420" y="110" width="24" height="6" fill="var(--s2)"></rect><rect x="446" y="88" width="24" height="22" fill="var(--s1)"></rect><text x="445" y="140" text-anchor="middle" fill="var(--muted)">expert</text></g>
    <text x="440" y="128" fill="var(--s2)" font-size="7">fixed below 0</text>
    <rect x="560" y="40" width="10" height="10" fill="var(--s2)"></rect><text x="574" y="49" fill="var(--muted)" font-size="8">fixed 1.98</text>
    <rect x="560" y="56" width="10" height="10" fill="var(--s1)"></rect><text x="574" y="65" fill="var(--muted)" font-size="8">adaptive 2.60</text>
  </g>
</svg>
^ The two policies' bars are equal for the novice and middle learner and split only at the expert, where fixed dips below the zero line and adaptive stays positive. Adaptive dominates learner-by-learner and wins the total.

**Scaffolding helps a learner in proportion to what they do not know and hurts in proportion to what they do, so its benefit reverses sign past a competence threshold — a fixed full-scaffolding policy is optimal for novices and harmful for experts, while fading scaffolding as competence grows matches each learner and never underperforms.**

### The self-test

The `--check` mode asserts the reversal and the policy dominance: scaffolding helps the novice and hurts the expert, and adaptive fading beats fixed over the cohort while never underperforming for any learner.

```
# $ python3 scaffold.py --check
#   full scaffolding helps the novice = True (1.32 > 0.50)
#   full scaffolding HURTS the expert (reversal) = True (-0.12 < 0.50)
#   adaptive fading beats fixed-full over the cohort = True (2.60 > 1.98)
#   adaptive never underperforms fixed for any learner = True
#   adaptive gives the expert less scaffolding than fixed = True (0 < 1)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 scaffold.py --check`

The two policy assertions are the win and the dominance:

```
# scaffold.py:115-124 — COMPLETE (adaptive wins the cohort and dominates per learner)
    fixed = cohort_total(data["learners"], fixed_full, cfg)
    adapt = cohort_total(data["learners"], adaptive, cfg)
    adaptive_wins = adapt > fixed

    dominates = all(
        learning_gain(l["competence"], adaptive(l["competence"], cfg), cfg)
        >= learning_gain(l["competence"], fixed_full(l["competence"], cfg), cfg) - 1e-9
        for l in data["learners"])
```

`adaptive_wins` requires the higher cohort total; `dominates` requires adaptive to match or beat fixed for every single learner — a total win that costs no individual anything.

The `expert_hurt` line is the phenomenon's core: full scaffolding must leave the expert worse than no scaffolding, which is what makes this a reversal rather than just diminishing returns. The `dominates` line is what elevates adaptive from "better on average" to "strictly better" — it must match or beat fixed for every single learner, so the improvement is free, taken from no one. Together they show the fixed policy is not a reasonable simplification but a dominated choice.

### The running tally

| learner | competence | fixed-full gain | adaptive gain | who is right |
|---|---|---|---|---|
| novice | 0.10 | 1.32 | 1.32 | tie — both scaffold |
| middle | 0.40 | 0.78 | 0.78 | tie — both scaffold |
| expert | 0.90 | −0.12 | 0.50 | adaptive — fade the scaffold |

The first two rows are ties — below the reversal point, full scaffolding is correct and both policies give it. The whole difference is the expert row, where fixed's insistence on full scaffolding turns a positive lesson negative and adaptive's fade keeps it positive. This is why the expertise-reversal effect matters in practice: the cost of a fixed policy is invisible on the novices it was designed for and lands entirely on the advanced learners, who are precisely the ones a fixed curriculum tends to ignore. Match the support to the learner, and fade it as they grow.

### What we did not settle

The model here is a clean linear stand-in; the real effect is richer. Competence is per-topic, not global — the same person is a novice in one area and an expert in another, so scaffolding must adapt per skill, not per learner. Measuring competence to drive the fading is the hard part; systems estimate it from performance, which ties back to the readiness and calibration modules. Fading has a schedule of its own — completion problems and faded worked examples remove steps gradually rather than all at once, which the bang-bang policy here skips. And scaffolding is more than worked examples: hints, prompts, and templates each have their own reversal. The rule here — scaffolding's value depends on competence and must fade — is the invariant; the schedule and the measurement are the engineering.

## Build

The practice in one paragraph: never fix the amount of scaffolding across learners; estimate each learner's competence per topic and fade the scaffolding as it grows — full worked examples for novices, faded examples and then bare problems for the advanced — because past a reversal point more scaffolding lowers learning, not raises it; and verify the adaptive policy dominates the fixed one learner-by-learner, so the change costs no novice anything. Fade gradually with completion problems, and adapt per skill, not per person.

We opened on the reversal curve. The number that proves a fixed policy is wrong is the expert's negative gain:

```
# modules/teaching-and-portability/code/teach-inter-06/ — COMPLETE, run from that directory
$ python3 scaffold.py --policy
  expert   c=0.90  fixed(s=1)=-0.12   adaptive(s=0)= 0.50
```

Now do it with your own learners. Take a cohort at different competence levels, model scaffolding's help and harm, and compare a fixed-full policy to adaptive fading. Your number to beat is not the average gain; it is **whether any learner is hurt by your fixed scaffolding — an expert whose gain goes negative — and whether adaptive fading dominates it learner-by-learner**. Find your reversal point and fade past it. Bring back both policies' per-learner gains and totals. Good luck.

## Definition of done

- [ ] A model of learning gain as a function of competence and scaffolding
- [ ] The reversal point where more scaffolding stops helping, computed
- [ ] Confirmation scaffolding helps a novice and hurts an expert (net negative)
- [ ] A fixed-full policy and an adaptive fading policy compared over a cohort
- [ ] Confirmation adaptive beats fixed in total and never underperforms per learner
- [ ] `python3 scaffold.py --check` printing SELF-TEST PASS: novice-helped, expert-hurt, adaptive-wins, dominates, expert-gets-less
- [ ] A note on how you would estimate competence to drive the fading
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Scaffolding does two opposing things. What are they, and how does each depend on the learner's competence?
2. What is the reversal point, and what determines where it falls?
3. Full scaffolding gave the expert a negative gain. Why is that a reversal and not just diminishing returns?
4. Adaptive fading beat the fixed policy without helping any novice less. Why does that make the fixed policy a dominated choice, not a reasonable simplification?
5. Your own cohort was scaffolded two ways. Was any learner hurt by fixed scaffolding, and did adaptive dominate it?

## External resources

- Kalyuga, Ayres, Chandler & Sweller, *The Expertise Reversal Effect* (2003) — my summary: the cognitive-load-theory result that instructional support helping novices hinders experts, with the working-memory explanation; read it for the empirical basis of the model here.
- Renkl & Atkinson, *Faded worked examples* — my summary: the schedule for gradually removing worked steps as competence grows, the practical form of adaptive fading; read it for how to fade rather than switch abruptly.
- This hub, *teach-inter-03* — modules/teaching-and-portability/teach-inter-03.md — my summary: the calibration module on measuring what a learner actually knows; read it for the competence estimate that an adaptive fading policy needs as its input.
