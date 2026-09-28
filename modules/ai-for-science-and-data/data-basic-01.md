---
id: data-basic-01
title: Simpson's paradox — the average reversed when you looked inside it
topic: ai-for-science-and-data
level: basic
status: ready
time: 6-8h
summary: Compare two treatments by their overall success rate and B wins, 0.83 to 0.78 — but A wins on small stones (0.93 vs 0.87) and on large stones (0.73 vs 0.69), so A is better on every case it is fairly compared against and only loses the pool because it treated 75% hard cases to B's 23%. The aggregate reversed the honest comparison, and the fix is to segment by the confounder before you believe a single number.
eli5: One doctor takes all the hard cases and another takes the easy ones. Judge them by overall survival and the hard-case doctor looks worse — even if they are better at every kind of case. To compare fairly, compare within the same difficulty.
---

## Why this module

This opens the AI-for-science-and-data track — the quantitative spine — and it starts with the mistake that ruins more analyses than any other: trusting an aggregate. The track's own curriculum frames the goal as knowing "which differences are real," and the first thing that makes a difference *not* real is a confounder hiding inside a pooled number. You will compare two options, watch the overall number crown a clear winner, then segment the data and watch the winner flip in every subgroup. Nothing was miscalculated; the aggregate was answering a different question than you thought.

The phenomenon is Simpson's paradox, and it is not a curiosity — it is the default hazard of comparing rates when the groups differ in composition. If one option was applied mostly to hard cases and the other mostly to easy ones, the pooled rate compares the options *and* their case mix at once, and the case mix can dominate. A treatment that is better on easy cases and better on hard cases can still have a worse overall rate simply because it took more of the hard ones. The pooled number is not wrong arithmetic; it is the wrong comparison.

You need nothing but Python 3 and the standard library. Everything runs offline against the published kidney-stone study, a textbook fixture, `$0.00`, one sitting. The instinct to unlearn is that a single rate is a fair summary. A rate is only fair when the things it pools are alike, and the whole discipline is checking that before you believe it.

Here is the reversal:

```
# modules/ai-for-science-and-data/code/data-basic-01/ — COMPLETE, run from that directory
$ python3 simpson.py --paradox

THE PARADOX — subgroup winner vs overall winner
------------------------------------------------------------
  within small        A=0.93  B=0.87  ->  A wins
  within large        A=0.73  B=0.69  ->  A wins
  ----------------------------------------
  OVERALL          A=0.78  B=0.83  ->  B wins
```

run: 2026-08-25 · deterministic; counts are the published study · 2 treatments, 2 segments · `python3 simpson.py --paradox`

Treatment A wins on small stones and on large stones — every fair, like-for-like comparison — and loses the overall rate to B. If you had read only the overall line you would deploy B, the worse treatment. This module is why the two lines disagree and which one to trust.

## Concepts

Named here so you can find them again; each is built below.

- **Success rate** — successes over cases; the number being compared.
- **Segment** — a subgroup that shares a value of the confounder (here, stone size).
- **Aggregate / pooled rate** — one rate over all cases combined; the misleading summary.
- **Confounder** — a variable that affects the outcome and is unevenly split between the options (here, case difficulty).
- **Simpson's paradox** — the aggregate comparison reverses the within-segment comparison.
- **Segmenting** — comparing within each level of the confounder; the fix.

## Worked example

Source: the track's experiment-design material on uncertainty and confounding, grounded in the classic Charig et al. kidney-stone study — the canonical Simpson's-paradox dataset. The same segmentation applies directly to the labs' own A/B comparisons (model versus model on easy and hard prompts, agent versus agent on simple and complex tasks).

Script and fixture: `modules/ai-for-science-and-data/code/data-basic-01/` — `simpson.py`, and `trials.json`, two treatments scored on small and large stones. Every command runs from there.

### The frame: two doctors and who took the hard cases

Picture two surgeons. One is famous for taking the desperate, high-risk cases nobody else will; the other takes routine ones. Rank them by overall survival rate and the brave surgeon looks worse — not because they are worse, but because "overall survival" silently includes "how hard were your patients." The only fair comparison is within the same difficulty: among the desperate cases, who does better; among the routine cases, who does better. Pool across difficulties and you are no longer comparing surgeons, you are comparing surgeons tangled with their caseloads.

That tangle is the whole module. The pooled rate multiplies each option's per-segment skill by how many of each segment it happened to take, and if the caseloads differ enough, the mix wins. Segmenting untangles them: compare like with like, and the option's real quality shows. The aggregate is the trap; the segment is the truth.

### The rate, and the pool

A rate is successes over cases; the pooled rate sums the numerators and denominators across segments.

```
# simpson.py:34-43 — COMPLETE (a rate, and the naive pooled rate)
def rate(pair):
    num, den = pair
    return num / den if den else 0.0


def aggregate(t):
    """Pooled success rate across all segments -- the naive overall number."""
    num = sum(seg[0] for seg in t.values())
    den = sum(seg[1] for seg in t.values())
    return num / den, num, den
```

Look at the full table — per segment and pooled:

```
# $ python3 simpson.py --table
#   treatment   small          large          overall
#   A           81/87=0.93     192/263=0.73   273/350=0.78
#   B           234/270=0.87   55/80=0.69     289/350=0.83
```

run: 2026-08-25 · fixture · `python3 simpson.py --table`

Every per-segment cell favors A: 0.93 over 0.87 on small, 0.73 over 0.69 on large. Yet A's pooled 0.78 loses to B's 0.83. The pooled numerators and denominators are the same arithmetic as the cells — nothing is fudged — but pooling weights A's rate toward its large-stone performance, because that is where most of A's cases are.

### The winners disagree

Two functions decide the winner two ways: within a segment, and over the pool.

```
# simpson.py:46-55 — COMPLETE (segment winner vs overall winner)
def segment_winner(treatments, seg):
    a = rate(treatments["A"][seg])
    b = rate(treatments["B"][seg])
    return "A" if a > b else ("B" if b > a else "tie"), a, b


def overall_winner(treatments):
    a, _, _ = aggregate(treatments["A"])
    b, _, _ = aggregate(treatments["B"])
    return "A" if a > b else ("B" if b > a else "tie"), a, b
```

The segment winner is A on both stones; the overall winner is B. That is the paradox stated in code, and it is the cold-open result.

<svg viewBox="0 0 700 180" role="img" aria-label="Grouped bars. On small stones A 0.93 beats B 0.87. On large stones A 0.73 beats B 0.69. But overall, B 0.83 beats A 0.78. A is taller in both segments yet shorter overall.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">A (dark) vs B (light): A wins both segments, B wins the pool</text>
    <line x1="50" y1="150" x2="660" y2="150" stroke="var(--grid)"></line>
    <g>
      <text x="90" y="168" fill="var(--ink)">small</text>
      <rect x="70" y="55" width="30" height="95" fill="var(--s1)"></rect><text x="66" y="50" fill="var(--s1)" font-size="8">.93</text>
      <rect x="105" y="63" width="30" height="87" fill="var(--s1)" opacity="0.4"></rect><text x="103" y="58" fill="var(--muted)" font-size="8">.87</text>
    </g>
    <g>
      <text x="290" y="168" fill="var(--ink)">large</text>
      <rect x="270" y="77" width="30" height="73" fill="var(--s1)"></rect><text x="266" y="72" fill="var(--s1)" font-size="8">.73</text>
      <rect x="305" y="81" width="30" height="69" fill="var(--s1)" opacity="0.4"></rect><text x="303" y="76" fill="var(--muted)" font-size="8">.69</text>
    </g>
    <g>
      <text x="500" y="168" fill="var(--s2)">OVERALL</text>
      <rect x="480" y="72" width="30" height="78" fill="var(--s1)"></rect><text x="476" y="67" fill="var(--muted)" font-size="8">.78</text>
      <rect x="515" y="67" width="30" height="83" fill="var(--s1)" opacity="0.4"></rect><text x="513" y="62" fill="var(--s2)" font-size="8">.83</text>
    </g>
    <line x1="430" y1="40" x2="430" y2="160" stroke="var(--grid)" stroke-dasharray="3 3"></line>
  </g>
</svg>
^ A's dark bar is taller in both segments and shorter in the pool. The reversal is real and the arithmetic is honest; the pool just answers a question that includes the caseload.

### The confounder explains it

Why does pooling betray A? Because A and B did not take the same mix of cases. The confounder — case difficulty — is split unevenly.

```
# $ python3 simpson.py --confound
#   A          treated 350 cases, 263 of them large (75% hard)
#   B          treated 350 cases, 80 of them large (23% hard)
```

run: 2026-08-25 · fixture · `python3 simpson.py --confound`

A took 75% hard cases; B took 23%. Large stones have a lower success rate for *both* treatments, so A's pool is dragged down by its heavy load of hard cases — a fact about A's caseload, not A's quality. B's easy caseload flatters its pool. Segmenting removes the caseload from the comparison and A's real superiority shows. The self-test states the whole thing:

```
# $ python3 simpson.py --check
#   A wins within every segment = True ({'small': 'A', 'large': 'A'})
#   B wins the pooled rate = True (A=0.780, B=0.826)
#   the aggregate reverses every subgroup = True
#   A took a higher share of hard cases than B = True (0.75 vs 0.23)
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · `python3 simpson.py --check`

<svg viewBox="0 0 700 140" role="img" aria-label="Case mix. Treatment A's 350 cases are 75% large (hard) and 25% small. Treatment B's 350 cases are 23% large and 77% small. A's bar is mostly hard; B's is mostly easy.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">case mix: dark = large (hard, low success for both), light = small (easy)</text>
    <text x="20" y="52" fill="var(--ink)">A</text>
    <rect x="60" y="40" width="435" height="20" fill="var(--s2)"></rect><text x="60" y="76" fill="var(--s2)" font-size="8">263 large (75%)</text>
    <rect x="495" y="40" width="145" height="20" fill="var(--s1)" opacity="0.4"></rect><text x="500" y="76" fill="var(--muted)" font-size="8">87 small</text>
    <text x="20" y="102" fill="var(--ink)">B</text>
    <rect x="60" y="90" width="132" height="20" fill="var(--s2)"></rect><text x="60" y="126" fill="var(--s2)" font-size="8">80 large (23%)</text>
    <rect x="192" y="90" width="448" height="20" fill="var(--s1)" opacity="0.4"></rect><text x="400" y="126" fill="var(--muted)" font-size="8">270 small (77%)</text>
  </g>
</svg>
^ A's caseload is three-quarters hard; B's is three-quarters easy. Because hard cases have lower success for both treatments, A's pool is weighed down by its mix — the reversal is a fact about the caseloads, not the treatments.

**A pooled rate compares the options tangled with their caseloads; when a confounder is split unevenly the pool can reverse every fair comparison, so segment by the confounder before you trust a single number.**

## Build

The pipeline in one paragraph: before comparing two options by a pooled rate, identify any variable that affects the outcome and might be split unevenly between them; compute the rate *within* each level of that variable, not just overall; and if the within-segment winner disagrees with the pooled winner, trust the segments and report the confounder. Never deploy a decision off an aggregate rate without checking the segments.

We opened on the reversal. The comparison that is fair:

```
# modules/ai-for-science-and-data/code/data-basic-01/ — COMPLETE, run from that directory
$ python3 simpson.py --paradox
  within small: A wins   within large: A wins   OVERALL: B wins
```

Now segment your own comparison. Take an A/B rate from your systems — two models on a mix of easy and hard prompts, two agents on simple and complex tasks — and recompute it within each difficulty. Your check is whether the segment winner matches the pooled winner; when they disagree, you have found a confounder. Construct a case where one option takes mostly hard tasks and confirm the pool reverses its per-segment superiority. Bring back the per-segment table and the caseload split. Good luck.

## Definition of done

- [ ] An A/B success rate computed both pooled and within each level of a confounder
- [ ] The segment winner and the overall winner reported separately
- [ ] Your own `trials.json` (or real data) with a confounder split unevenly between the options
- [ ] The caseload mix shown, so the reversal is explained, not just observed
- [ ] `python3 simpson.py --check` printing SELF-TEST PASS: one option wins every segment, the other wins the pool, the mix explains it
- [ ] A written note of which comparison you trust and the confounder you segmented on
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Treatment A won on small stones and large stones but lost overall. Explain how both facts are true at once without any arithmetic error.
2. Define a confounder, and name the one in this dataset and how it was split between the treatments.
3. You have a pooled rate that says B wins. What is the one check that would reveal a Simpson's reversal, and what do you do if it disagrees?
4. Why does A's heavy share of hard cases drag down its pooled rate but not its per-segment rates?
5. Your own A/B comparison was segmented. Did the segment winner match the pooled winner, and what confounder did you check?

## External resources

- Charig et al., *Comparison of treatment of renal calculi* (1986), via the Simpson's-paradox literature — https://en.wikipedia.org/wiki/Simpson%27s_paradox — my summary: the source of these exact numbers and the canonical worked example; read it for the medical context and for other real reversals (Berkeley admissions, batting averages).
- Pearl, *Causal Inference in Statistics: A Primer* — https://bayes.cs.ucla.edu/PRIMER/ — my summary: why segmenting is not always the right fix — whether to pool or split depends on the causal structure, not just the numbers; read it for when the aggregate is actually the honest one and the segments mislead, the deeper half of this lesson.
- This hub, *evals-inter-01* — modules/evals-and-statistics/evals-inter-01.md — my summary: comparing two systems with an interval and a paired test; read it for how to decide whether a within-segment difference is real once you have segmented, closing the loop from "which comparison" to "is it significant".
