---
id: evals-inter-01
title: Two systems, thirty cases — the interval that decides whether B beat A
topic: evals-and-statistics
level: intermediate
status: ready
time: 8-10h
summary: Two prompts score 0.74 and 0.82 on the same 30 cases; their 95% error bars overlap so the naive read is "no difference" — then the interval on the difference clears zero at p=0.0013, because the cases were paired and the overlap rule threw the pairing away.
---

## Why this module

evals-basic-01 ended on an admission: it printed `clean_rate 0.633` with "the spread across reruns is 0.000 — not because these graders are steady but because nothing in them can be unstable", and then named the missing piece out loud — "Draw a different 30 and 0.633 moves, by an amount nothing here can say — evals-basic-02." This is that module. The scan's verdict on the whole portfolio was the same hole, one level up: it "reports point scores with no variance", and `CURRICULUM.md` puts it first — "Statistical rigor in evaluation (variance, confidence intervals, pass^k, N>1)". The anchor file already has the shape of the bug: a benchmark comparator that prints two mean scores side by side and stops, with no function that says whether the gap is real.

This module supplies the missing test at `intermediate`. Two systems answered the same 30 questions; you get a 95% confidence interval on each mean, a 95% interval on their difference, and two significance tests that agree with each other. What it omits: no t-distribution, no power analysis, no effect-size zoo beyond the raw difference — the bootstrap needs none of them and they obscure the one idea. You need evals-basic-01's rubric and a Python list. Stdlib Python 3, offline, $0.00, about two seconds a run, one sitting. The hard part is not the code; it is seeing why two overlapping error bars do not answer the question you asked.

By the end, one command scores both systems, tests the difference, and prints where the naive read and the honest read disagree. Skipping ahead:

```
# modules/evals-and-statistics/code/evals-inter-01/ — COMPLETE, run from that directory
$ python3 compare.py --all

cases=30  file=runs.json  paired A/B, graded 0..6 by the basic-01 rubric

POINT MEANS (no uncertainty)
----------------------------------------------------------------------
  system A (baseline)          mean = 0.7444
  system B (baseline+grounding) mean = 0.8222
  difference  B - A                  = +0.0778

MARGINAL 95% CIs (bootstrap, B=10000, seed=0)
----------------------------------------------------------------------
  A: 0.7444   95% CI [0.6778, 0.8111]
  B: 0.8222   95% CI [0.7667, 0.8778]
  intervals overlap: True

  VERDICT BY OVERLAP RULE: NOT SIGNIFICANT (the CIs overlap)

PAIRED DIFFERENCE (bootstrap CI + permutation test, seed=0)
----------------------------------------------------------------------
  observed mean(B - A)          = +0.0778
  95% CI on the difference      = [+0.0389, +0.1167]
  CI excludes zero              = True
  permutation p (one-sided)     = 0.0013
  sign test: B wins 16, loses 2, ties 12
  sign-test p (exact binomial)  = 0.0007

  VERDICT BY PAIRED CI: SIGNIFICANT (difference CI clears zero)

THE TWO METHODS DISAGREE
```

run: 2026-08-22 · bootstrap seed=0, B=10000 · n=30 · `python3 compare.py --all`

Two verdicts on one comparison. The overlap rule looks at the two error bars, sees them touch, and says stop — no difference. The paired test looks at the difference itself, finds its interval sits entirely above zero, and says B won at p=0.0013. They cannot both be the right way to read the same 30 numbers. This module is about which one is, and why the other is so seductive.

## Concepts

Named here so you can find them again; each is built and, in one case, broken below.

- **Bootstrap** — resample your cases with replacement, recompute the number, thousands of times; the spread of those numbers is your uncertainty. Built in `bootstrap_mean_ci`.
- **Marginal CI** — a 95% interval for one mean on its own. #2, and the trap.
- **Overlapping-CI fallacy** — concluding "no difference" because two marginal CIs touch. The planted bug.
- **Paired difference** — subtract B − A within each case, then average; the case's difficulty cancels. #3.
- **Paired bootstrap** — resample the case index once and use it for both systems, keeping the pair intact. The right interval.
- **Permutation test** — flip the sign of each per-case difference at random; how often does chance beat what you saw?
- **Sign test** — the exact binomial tail on wins-vs-losses, a check on the permutation p.

## Worked example

Source: faisalmahdy/oh-my-claudecode-fork — `benchmark/` comparator (prints two systems' mean scores with no significance function; this module adds the interval and the test). De-personalized, and the target is described only as far as the curriculum states it.

Source: faisalmahdy/AI-Learning-Hub — `modules/evals-and-statistics/code/evals-basic-01/` (the six-check rubric and the 30-case split this module reuses; the scores here are that rubric's `checks_passed` for two systems).

Script and fixtures: `modules/evals-and-statistics/code/evals-inter-01/` — `compare.py`, 264 lines, `runs.json`, 30 paired cases. Every command runs from there.

### Install the frame: the two-pan balance

In my opinion, the best way to think of a paired A/B eval is as a two-pan balance, not two spring scales.

Weigh bag A on a spring scale: the spring wobbles and the needle drifts, so you read a range, not a point. Weigh bag B: another range. If the springs are shaky enough, the two ranges overlap and you cannot say which bag is heavier — that is the marginal CI, one spring scale per mean. Now put both bags on a two-pan balance and read the *difference* directly. The wobble that was common to both weighings — the same shaky spring — now pushes both pans equally and cancels; the needle settles on B minus A with far less jitter. That is the paired difference, and it is the whole trick.

Three jobs, one line each, in the shape evals-basic-01 used for its graders: the mean says "how good on average?", the marginal CI says "how far would this one mean move on a redraw?", and the paired difference says "how much does B beat A, case by case, once the case's difficulty is subtracted out?"

### Look at the data: thirty cases, weighed twice

The 30 cases are evals-basic-01's, the same ten factual, ten synthesis, ten unanswerable. System A is the baseline Query prompt; system B adds one instruction, "cite a page for every claim or refuse". Each case carries A's rubric score and B's, out of 6, on the identical question — that is what makes them paired.

Before any statistic, count the per-case differences by hand. B beats A on 16 cases by one check, ties on 12, and — kept in on purpose — loses on 2 (F06, S02, where the grounding instruction made B refuse something it could have answered). Sixteen up, two down, twelve level.

<svg viewBox="0 0 740 176" role="img" aria-label="Thirty cells in case order, one per case: sixteen marked as B gains a check, two marked as B loses a check, twelve unmarked ties, grouped into factual, synthesis and unanswerable blocks of ten">
  <g font-family="var(--mono)">
    <text x="44" y="26" font-size="10.5" fill="var(--muted)">one cell per case · up = B gains a check · down = B loses a check · flat = tie</text>
    <g>
      <rect x="44" y="44" width="16" height="16" rx="3" fill="var(--grid)"></rect><rect x="66" y="44" width="16" height="16" rx="3" fill="var(--grid)"></rect><rect x="88" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect><rect x="110" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect><rect x="132" y="44" width="16" height="16" rx="3" fill="var(--grid)"></rect><rect x="154" y="44" width="16" height="16" rx="3" fill="var(--s2)"></rect><rect x="176" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect><rect x="198" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect><rect x="220" y="44" width="16" height="16" rx="3" fill="var(--grid)"></rect><rect x="242" y="44" width="16" height="16" rx="3" fill="var(--grid)"></rect>
      <rect x="278" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect><rect x="300" y="44" width="16" height="16" rx="3" fill="var(--s2)"></rect><rect x="322" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect><rect x="344" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect><rect x="366" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect><rect x="388" y="44" width="16" height="16" rx="3" fill="var(--grid)"></rect><rect x="410" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect><rect x="432" y="44" width="16" height="16" rx="3" fill="var(--grid)"></rect><rect x="454" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect><rect x="476" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect>
      <rect x="512" y="44" width="16" height="16" rx="3" fill="var(--grid)"></rect><rect x="534" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect><rect x="556" y="44" width="16" height="16" rx="3" fill="var(--grid)"></rect><rect x="578" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect><rect x="600" y="44" width="16" height="16" rx="3" fill="var(--grid)"></rect><rect x="622" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect><rect x="644" y="44" width="16" height="16" rx="3" fill="var(--grid)"></rect><rect x="666" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect><rect x="688" y="44" width="16" height="16" rx="3" fill="var(--grid)"></rect><rect x="710" y="44" width="16" height="16" rx="3" fill="var(--s1)"></rect>
    </g>
    <g font-size="10" fill="var(--muted)" text-anchor="middle"><text x="143" y="86">F01-F10 factual</text><text x="377" y="86">S01-S10 synthesis</text><text x="611" y="86">U01-U10 unanswerable</text></g>
    <g font-family="var(--mono)"><rect x="44" y="112" width="16" height="16" rx="3" fill="var(--s1)"></rect><text x="70" y="124" font-size="10.5" fill="var(--muted)">B gains — 16 cases</text><rect x="240" y="112" width="16" height="16" rx="3" fill="var(--s2)"></rect><text x="266" y="124" font-size="10.5" fill="var(--muted)">B loses — 2 (F06, S02)</text><rect x="470" y="112" width="16" height="16" rx="3" fill="var(--grid)"></rect><text x="496" y="124" font-size="10.5" fill="var(--muted)">tie — 12 cases</text></g>
    <rect x="44" y="146" width="240" height="24" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="164" y="162" font-size="10.5" text-anchor="middle" fill="var(--acc-ink)">16 up, 2 down · net +14 checks over 30</text>
  </g>
</svg>
^ The per-case verdict of B against A, in case order. Two systems, same questions, so every cell is a head-to-head, not two separate scores.

How to read this: the pairing is the whole figure — each cell compares B and A on one identical case, so the case's difficulty is already divided out. The failure signature to hunt for later is a method that ignores these cells and reads two separate columns of raw scores instead.

### Base case: one case is one subtraction

Take F04. A scored 4 of 6, B scored 5 of 6. The paired difference on this case is `5/6 − 4/6 = 1/6 = 0.1667`, and that is the entire operation — no statistics in a single case, just a subtraction. The mean over all 30 of these per-case subtractions is the number the whole module puts an interval around.

```
# compare.py:61-63 — COMPLETE (the two point means and their difference)
def means(a, b):
    ma, mb = mean(a), mean(b)
    return ma, mb, mb - ma

# $ python3 compare.py --means
#   system A (baseline)          mean = 0.7444
#   system B (baseline+grounding) mean = 0.8222
#   difference  B - A                  = +0.0778
```

run: 2026-08-22 · deterministic (fixture means, no resampling) · n=30 · `python3 compare.py --means`

Bracket for the headline +0.0778: under the null "B is no better than A" the per-case differences are symmetric around zero, so the expected difference is 0.0000 — that is the chance level, and it is what every test below measures distance from. The floor is −1.0 (B scores 0 everywhere A scores 6), the ceiling +1.0. Real-world size: +0.0778 on a six-check rubric is about half a check per case on average — concretely, 16 of 30 cases gained a check and 2 lost one, net +14 checks over 30. Keep 0.7444 and 0.8222; they are the yardstick both methods start from.

### Strategy #1 — read the two means. Killed by having no ruler.

B is 0.8222, A is 0.7444, so B wins. This is where the anchor comparator stops, and it is not wrong so much as unfinished: it reports the needle position and nothing about how much the needle wobbles. The kill is immediate — is +0.0778 a real gain or the kind of gap you would see between two runs of the *same* system on a different 30 cases? Strategy #1 cannot say, because it never resampled anything. It has no ruler, only a reading.

### Strategy #2 — a CI on each mean, then check overlap. This is the bug.

So give each mean a ruler. Resample the 30 cases with replacement, recompute the mean, ten thousand times; the middle 95% of those recomputed means is a confidence interval for that mean. Do it for A, do it for B, and see whether the intervals overlap.

```
# compare.py:68-77 — COMPLETE (one mean's bootstrap CI; the tokenizer of statistics)
def bootstrap_mean_ci(xs, rng):
    """Resample the cases with replacement, recompute the mean, 10000 times.
    Return the 2.5th and 97.5th percentiles: a 95% CI for THIS mean alone."""
    n = len(xs)
    boots = []
    for _ in range(BOOT):
        resample = [xs[rng.randrange(n)] for _ in range(n)]
        boots.append(mean(resample))
    boots.sort()
    return percentile(boots, 2.5), percentile(boots, 97.5)

# $ python3 compare.py --marginal
#   A: 0.7444   95% CI [0.6778, 0.8111]
#   B: 0.8222   95% CI [0.7667, 0.8778]
#   intervals overlap: True
#   VERDICT BY OVERLAP RULE: NOT SIGNIFICANT (the CIs overlap)
```

run: 2026-08-22 · bootstrap seed=0, B=10000 · n=30 · `python3 compare.py --marginal`

This is called a **bootstrap**, and a per-mean interval is its **marginal CI** — marginal meaning "for one variable, ignoring the other". Reading the machine, not a formula: draw 30 indices at random from the 30 you have, some cases landing twice and some not at all, average that resample, and repeat until the histogram of averages is smooth; the 2.5th and 97.5th percentiles fence off the middle 95%. No distribution assumed, no formula for the standard error — the resampling *is* the standard error.

Now the prediction, and I want you to commit to it before the next section. A reaches up to 0.8111, B reaches down to 0.7667, so the two error bars overlap across the whole 0.767–0.811 band. Overlapping error bars — is the difference between A and B significant? Say it out loud. Most people, looking at two overlapping 95% intervals, say no: if the bars touch, the difference could be zero. The answer is at the top of the next section.

<svg viewBox="0 0 740 250" role="img" aria-label="Two number lines with different axes: the top axis in score units shows the marginal CIs for A and B overlapping, the bottom axis in difference units shows the paired difference interval sitting entirely to the right of zero">
  <g font-family="var(--mono)">
    <text x="44" y="24" font-size="10.5" fill="var(--muted)">TOP AXIS — raw score (what the overlap rule reads)</text>
    <line x1="90" y1="86" x2="620" y2="86" stroke="var(--grid)" stroke-width="1.5"></line>
    <g font-size="9" fill="var(--muted)" text-anchor="middle"><text x="90" y="104">0.60</text><text x="266" y="104">0.70</text><text x="443" y="104">0.80</text><text x="620" y="104">0.90</text></g>
    <rect x="384" y="44" width="79" height="10" rx="3" fill="var(--s1)" opacity="0.35"></rect>
    <text x="360" y="52" font-size="9.5" text-anchor="end" fill="var(--muted)">overlap</text>
    <line x1="228" y1="60" x2="463" y2="60" stroke="var(--s1)" stroke-width="2.5"></line>
    <circle cx="345" cy="60" r="4" fill="var(--s1)"></circle>
    <text x="475" y="63" font-size="9.5" fill="var(--ink)">A  0.744  [0.678, 0.811]</text>
    <line x1="384" y1="74" x2="581" y2="74" stroke="var(--s2)" stroke-width="2.5"></line>
    <circle cx="482" cy="74" r="4" fill="var(--s2)"></circle>
    <text x="592" y="77" font-size="9.5" fill="var(--ink)">B  0.822  [0.767, 0.878]</text>
    <text x="44" y="150" font-size="10.5" fill="var(--muted)">BOTTOM AXIS — difference B - A (what the paired test reads)</text>
    <line x1="90" y1="200" x2="620" y2="200" stroke="var(--grid)" stroke-width="1.5"></line>
    <g font-size="9" fill="var(--muted)" text-anchor="middle"><text x="222" y="218">0.00</text><text x="355" y="218">+0.05</text><text x="487" y="218">+0.10</text><text x="620" y="218">+0.15</text></g>
    <line x1="222" y1="164" x2="222" y2="208" stroke="var(--acc)" stroke-width="1.4" stroke-dasharray="3 3"></line>
    <text x="222" y="176" font-size="9.5" text-anchor="middle" fill="var(--acc-ink)">zero</text>
    <line x1="325" y1="188" x2="532" y2="188" stroke="var(--ink)" stroke-width="2.5"></line>
    <circle cx="429" cy="188" r="4" fill="var(--ink)"></circle>
    <text x="325" y="242" font-size="9.5" fill="var(--ink)">B - A  +0.078  [+0.039, +0.117]  — entirely right of zero</text>
    <rect x="470" y="150" width="150" height="22" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="545" y="165" font-size="10" text-anchor="middle" fill="var(--acc-ink)">gap to zero: +0.039</text>
  </g>
</svg>
^ The same comparison on two axes. The overlap rule reads the top axis and sees the bars touch; the paired test reads the bottom axis, where zero is a landmark and the difference interval never reaches it.

How to read this: two axes, because the two methods measure different things — raw score on top, difference on the bottom. The failure signature of the overlap rule is that it never looks at the bottom axis at all, where the only question that matters (is the difference above zero?) actually lives.

### Why the overlap read is wrong — leave the bug in

Stop here. The overlap rule just returned `NOT SIGNIFICANT`, and it is wrong. Why?

The autopsy: the marginal CI for A and the marginal CI for B are each computed by resampling *independently*, as if the two systems had been measured on two unrelated sets of cases. But they were measured on the **same** cases. When a resample happens to draw the hard cases — U02, U08, S03 — both A's mean and B's mean drop together, because those cases are hard for both systems. The two means move as a pair, and the overlap rule, by resampling them separately, has thrown that pairing in the bin. It is answering "could these two clouds of means have come from one system?" when the question was "is B minus A above zero?"

Here is the minimal reproducer — three cases, an extreme version of the same structure:

```
# a 3-case sketch of the fallacy — COMPLETE, paste into a python prompt
A = [0.10, 0.50, 0.90]          # one easy, one medium, one hard case
B = [0.20, 0.60, 1.00]          # B is +0.10 on every single case
# marginal spread of A is huge (0.10 to 0.90), same for B, so their CIs
# overlap almost completely -> "no difference"
# but B - A = [0.10, 0.10, 0.10] -> the difference has ZERO spread and is
# obviously, unanimously positive
```

B wins every case by exactly 0.10, yet each system's scores swing from 0.10 to 0.90, so the marginal intervals sit almost on top of each other. The overlap rule sees the swing and calls it a tie. The difference sees +0.10 three times and calls it a shutout. This is the **overlapping-CI fallacy**: comparing two marginal intervals instead of putting one interval on the difference. It fools people because "if the error bars overlap it's not significant" is a real rule of thumb — for *independent* groups, where it is merely conservative. On paired data it is not conservative, it is wrong, and it hid a p=0.0013 result behind a shrug.

**Overlapping error bars answer a question you did not ask. The question you asked lives on the difference, and the difference has its own, tighter bar.**

The one-line assertion that would have caught it: the interval you report must be computed on `b[i] - a[i]`, never on `a` and `b` separately. If your CI code never subtracts within a case, you have built the bug.

### Strategy #3 — bootstrap the difference, keep the pair intact

The fix is one change: resample the case *index* once per draw and use it for both systems, so A and B are always weighed on the same resampled cases. Here is the loop with its most important line blanked — fill it in before you read on.

```
# compare.py:86-101 — STUB, the version you write first (committed body below)
def bootstrap_diff_ci(a, b, rng):
    n = len(a)
    boots = []
    for _ in range(BOOT):
        sa = 0.0
        sb = 0.0
        for _ in range(n):
            # your turn: how many indices do you draw here, and for which system?
            ...
        boots.append((sb - sa) / n)
```

You draw one index and use it for both. Draw two independent indices — one for A, one for B — and you have silently rebuilt Strategy #2's unpaired comparison inside a difference, throwing the pairing away exactly where it matters. One index per draw is the two-pan balance; two indices is two spring scales again.

```
# compare.py:86-101 — COMPLETE (the paired bootstrap: one index, both systems)
def bootstrap_diff_ci(a, b, rng):
    """Resample the SAME case index for both systems, so the pair stays intact,
    recompute mean(B) - mean(A). The case's difficulty rides in both terms and
    cancels. Return the 95% percentile CI on the difference."""
    n = len(a)
    boots = []
    for _ in range(BOOT):
        sa = 0.0
        sb = 0.0
        for _ in range(n):
            i = rng.randrange(n)     # one index, used for both A and B
            sa += a[i]
            sb += b[i]
        boots.append((sb - sa) / n)
    boots.sort()
    return percentile(boots, 2.5), percentile(boots, 97.5)

# $ python3 compare.py --paired
#   observed mean(B - A)          = +0.0778
#   95% CI on the difference      = [+0.0389, +0.1167]
#   CI excludes zero              = True
#   permutation p (one-sided)     = 0.0013
#   sign test: B wins 16, loses 2, ties 12
#   sign-test p (exact binomial)  = 0.0007
#   VERDICT BY PAIRED CI: SIGNIFICANT (difference CI clears zero)
```

run: 2026-08-22 · bootstrap seed=0, B=10000, permutation B=10000 · n=30 · `python3 compare.py --paired`

The interval on the difference is `[+0.0389, +0.1167]`, and it never touches zero — the nearest edge, +0.0389, is the balance needle's closest approach to the zero mark. The size of the surprise is the point: the overlap rule did not merely land near the significance line and fall on the wrong side, it returned a shrug where the honest answer is p=0.0013 — a thousand-to-one, hidden entirely by reading the wrong axis.

<svg viewBox="0 0 680 250" role="img" aria-label="Two panels of the two-pan balance metaphor: on the left, systems A and B each on a separate spring scale with wide overlapping wobble ranges; on the right, a two-pan balance weighing B minus A directly with a narrow range sitting above zero">
  <g font-family="var(--mono)">
    <text x="20" y="22" font-size="11" font-weight="600" fill="var(--ink)">TWO SPRING SCALES (marginal)</text>
    <text x="380" y="22" font-size="11" font-weight="600" fill="var(--ink)">ONE TWO-PAN BALANCE (paired)</text>
    <g stroke="var(--line)" fill="none" stroke-width="1.5">
      <path d="M60 60 v70"></path><path d="M40 60 h40"></path><path d="M60 130 m-22 0 a22 10 0 0 0 44 0"></path>
      <path d="M170 60 v70"></path><path d="M150 60 h40"></path><path d="M170 130 m-22 0 a22 10 0 0 0 44 0"></path>
    </g>
    <rect x="42" y="86" width="36" height="26" rx="4" fill="var(--s1)" opacity="0.5"></rect>
    <rect x="152" y="76" width="36" height="26" rx="4" fill="var(--s2)" opacity="0.5"></rect>
    <text x="60" y="150" font-size="10" text-anchor="middle" fill="var(--muted)">A 0.744</text>
    <text x="170" y="150" font-size="10" text-anchor="middle" fill="var(--muted)">B 0.822</text>
    <text x="60" y="102" font-size="8.5" text-anchor="middle" fill="var(--ink)">±.067</text>
    <text x="170" y="92" font-size="8.5" text-anchor="middle" fill="var(--ink)">±.056</text>
    <rect x="30" y="168" width="180" height="24" rx="6" fill="var(--panel)" stroke="var(--grid)"></rect>
    <text x="120" y="184" font-size="9.5" text-anchor="middle" fill="var(--muted)">ranges overlap -> "no difference"</text>
    <line x1="300" y1="40" x2="300" y2="210" stroke="var(--grid)" stroke-dasharray="3 3"></line>
    <g stroke="var(--line)" fill="none" stroke-width="1.5">
      <path d="M500 52 v20"></path>
      <path d="M430 72 h140"></path>
      <path d="M430 72 l-14 26"></path><path d="M416 98 m-24 0 a24 11 0 0 0 48 0"></path>
      <path d="M570 72 l14 26"></path><path d="M584 98 m-24 0 a24 11 0 0 0 48 0"></path>
    </g>
    <rect x="392" y="86" width="48" height="20" rx="4" fill="var(--s2)" opacity="0.5"></rect>
    <rect x="560" y="92" width="48" height="14" rx="4" fill="var(--s1)" opacity="0.5"></rect>
    <text x="416" y="130" font-size="10" text-anchor="middle" fill="var(--muted)">B pan</text>
    <text x="584" y="130" font-size="10" text-anchor="middle" fill="var(--muted)">A pan</text>
    <line x1="360" y1="200" x2="620" y2="200" stroke="var(--grid)" stroke-width="1.5"></line>
    <g font-size="9" fill="var(--muted)" text-anchor="middle"><text x="380" y="216">0</text><text x="500" y="216">+0.08</text><text x="620" y="216">+0.15</text></g>
    <line x1="380" y1="188" x2="380" y2="204" stroke="var(--acc)" stroke-width="1.4" stroke-dasharray="3 3"></line>
    <line x1="446" y1="194" x2="580" y2="194" stroke="var(--ink)" stroke-width="2.5"></line>
    <circle cx="513" cy="194" r="4" fill="var(--ink)"></circle>
    <rect x="452" y="168" width="168" height="20" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="536" y="182" font-size="9.5" text-anchor="middle" fill="var(--acc-ink)">needle at +0.078, ±0.039, clears 0</text>
  </g>
</svg>
^ Left: each system weighed alone, wobble ±0.067 and ±0.056, ranges overlapping. Right: the balance weighs B − A directly, the common wobble cancels, and the needle sits at +0.078 ± 0.039, above zero.

How to read this: the diagnostic is the zero mark on the right panel. If the balance's range straddles zero, you cannot call a winner; here it clears zero by +0.039, so B wins. The left panel is the trap — its ranges overlap for a reason that has nothing to do with whether B beat A.

### Two routes to the same p, printed side by side

A single interval could be a fluke of one resampling scheme, so the difference gets a second, unrelated test. The permutation test asks: if B were truly no better than A, the sign of each per-case difference is a coin flip, so flip all 30 signs at random ten thousand times and see how often chance produces a mean difference at least as big as the +0.0778 we saw.

```
# compare.py:104-116 — COMPLETE (permutation test + the exact sign test as a check)
def permutation_p(a, b, rng):
    d = [b[i] - a[i] for i in range(len(a))]
    observed = mean(d)
    at_least = 0
    for _ in range(PERM):
        flipped = mean([di if rng.random() < 0.5 else -di for di in d])
        if flipped >= observed:
            at_least += 1
    return observed, (at_least + 1) / (PERM + 1)   # +1: the observed arrangement

# permutation p (one-sided)     = 0.0013
# sign test: B wins 16, loses 2, ties 12
# sign-test p (exact binomial)  = 0.0007
```

run: 2026-08-22 · permutation seed=0, B=10000 · n=30 · `python3 compare.py --paired`

Reading the symbols: `(at_least + 1) / (PERM + 1)` looks like notation but it is "what fraction of coin-flip universes matched or beat what we saw", with a `+1` on top and bottom for the one real universe — the arrangement we actually observed always counts, so the p can never come back a dishonest 0.0000. The permutation p is 0.0013. The sign test — an exact binomial tail over the 16 wins and 2 losses, ignoring the 12 ties — is 0.0007, computed by a completely different route with no resampling at all. Two methods, one conclusion: the gap is not noise. Both are far under the conventional 0.05, and they agree to the same order of magnitude, which is the cross-check.

### The bootstrap has its own noise — say so

One more honesty beat before the tally. The bootstrap is itself random; change the seed and the interval shifts. The `--check` mode proves the interval is fixed *under a seed* and moves *across seeds*:

```
# $ python3 compare.py --check
#   route A  mean(B) - mean(A)      = +0.077778
#   route B  mean(B[i] - A[i])      = +0.077778
#   routes agree                   = True
#   paired CI, run 1               = [+0.0389, +0.1167]
#   paired CI, run 2 (same seed)   = [+0.0389, +0.1167]
#   deterministic under seed       = True
#   paired CI, seed=1              = [+0.0389, +0.1111]  (bootstrap noise)
# SELF-TEST PASS  routes_agree=True  deterministic=True
```

run: 2026-08-22 · seeds 0 and 1, B=10000 · n=30 · `python3 compare.py --check`

Route A computes the difference as `mean(B) − mean(A)`; route B as the mean of the per-case differences; they are algebraically identical and print `+0.077778` both ways, which is the dumb cross-check that the headline number is real. Then the interval: identical across two runs at seed 0, and `[+0.0389, +0.1111]` at seed 1 — the upper edge moved by 0.0056 just from changing the random seed. That movement is small here and it never drags the lower edge near zero, so the verdict holds, but it is a real number and it must be reported.

**A confidence interval has its own confidence interval — report the seed, or you are hiding a number that moves.**

### The running tally

| read | what it looks at | verdict | number |
|---|---|---|---|
| #1 point means | two needle positions | B higher | +0.0778, no interval |
| #2 marginal overlap | two spring scales, separately | NOT SIGNIFICANT | CIs [0.678, 0.811] vs [0.767, 0.878], overlap |
| #3 paired difference | the two-pan balance | SIGNIFICANT | diff CI [+0.0389, +0.1167], p=0.0013 |

The only verdict that flipped is #2 → #3, and it flipped on one line of code: resample one index for both systems instead of two indices separately. And yet — a difference can be real and still be too small to ship, which no test on this page has weighed.

### Bridge to the standard names

Nobody outside this module calls it a two-pan balance. The paired bootstrap on the difference is the resampling cousin of the **paired t-test** and the **Wilcoxon signed-rank test**; the sign-flip permutation is a **paired permutation test**; the wins-and-losses tail is the **sign test**, exactly that name. If you reach for a stats library, `scipy.stats.wilcoxon` and `scipy.stats.ttest_rel` are the paired functions — the `_rel` and "signed-rank" are the library telling you it subtracts within a pair. The one to avoid for this data is `ttest_ind`, the independent-samples test, which is the overlap fallacy wearing a formula.

### What we did not settle

Significance is not size. The difference is real at p=0.0013, but +0.0778 on a six-check rubric is about half a check per case, and whether that is worth shipping a prompt change is a product call this module does not make — a large enough N makes a trivial difference significant, and n=30 is small enough that the reverse bit us in evals-basic-01.

Three more open ends. Multiple comparisons: test five prompt variants against the baseline and one will clear p=0.05 by luck alone — nothing here corrects for that. The permutation test's one-sided direction is a choice I made because B was designed to beat A; a two-sided test would double the p to 0.0026, still significant. And the fixture caveat from evals-basic-01 stands — these 30 scores are stored, so this measures the *test* honestly and the two systems only as of the day they were graded. If the paired-versus-marginal distinction still feels slippery, that is the correct reaction; it is the one genuinely counterintuitive idea in the module, and everything else is a loop over 30 numbers.

## Build

The pipeline in one paragraph: grade both systems on the same held-out cases with the basic-01 rubric; store the paired per-case scores; bootstrap a 95% interval on the difference, not on each mean; confirm it with a permutation test and a sign test; report the interval, the p, and the seed.

We opened on one command that prints where the naive read and the honest read disagree. The payoff block (again):

```
# modules/evals-and-statistics/code/evals-inter-01/ — COMPLETE, run from that directory
$ python3 compare.py --all
...
  VERDICT BY OVERLAP RULE: NOT SIGNIFICANT (the CIs overlap)
...
  95% CI on the difference      = [+0.0389, +0.1167]
  permutation p (one-sided)     = 0.0013
  VERDICT BY PAIRED CI: SIGNIFICANT (difference CI clears zero)

THE TWO METHODS DISAGREE
```

Now point it at your own system. The one dial is `runs.json`: grade two of your own systems — two prompts, two models, two retrieval configs — on the identical set of cases, and store each case's score under `a` and `b`. Everything in `compare.py` derives from that file; you change nothing else. Keep the losing cases in. Then run `python3 compare.py --all`.

Your number to beat is not the p-value. It is whether your two methods **agree**. Run `--marginal` and `--paired` and check: does the overlap rule say one thing and the paired CI another? If they agree, your effect is either so large the pairing does not matter or so small nothing saves it. If they disagree — overlap says stop, paired says go — you have caught the exact bug this module is about, on your own data, and the paired CI is the one to trust. Bring back both verdicts and the seed. Good luck.

### FAQ

**Why not just compare the two means?** Because +0.0778 with no interval could be a real gain or the gap between two runs of one system; Strategy #1 cannot tell them apart, and the anchor comparator that stops there cannot either.

**The difference is significant — should I ship system B?** Separate question. Significant means "not noise at n=30"; it does not mean "big enough to matter". Half a check per case, minus the 2 cases B made worse, is the real trade, and no p-value decides it for you.

**Is an LLM-graded difference circular?** The grader is the basic-01 rubric, measured there; here it is held fixed across both systems, so whatever bias it has cancels in the subtraction exactly like case difficulty does. That is a bonus of pairing.

**Why is mine slow?** The bootstrap is 10000 resamples of 30 draws, twice, plus 10000 permutations — a few million operations, about two seconds here. If yours crawls, you are either bootstrapping inside another loop or resampling thousands of cases; drop `BOOT` to 2000 while developing and the CI barely moves.

### Errata

Version one, dated 2026-08-22. The two regressions (F06, S02) were added after the first draft, whose fixtures had B winning or tying every case — that made the sign test a degenerate 18-and-0 and hid the fact that a real prompt change costs you a few cases; the numbers above are from the corrected fixtures. One soft spot left in: the seed=1 interval `[+0.0389, +0.1111]` is quoted from `--check` to make the point that the bootstrap wobbles, but I did not sweep more than two seeds, so "the lower edge never nears zero" is shown for two seeds, not proven for all.

## Definition of done

- [ ] `runs.json` for your own two systems: the same cases graded under `a` and `b`, losing cases kept, committed before the first run
- [ ] The CI is computed on the paired difference `b[i] - a[i]`, never on `a` and `b` separately
- [ ] `compare.py` committed and running against your file with no API key and no network
- [ ] Both a bootstrap difference CI and a second test (permutation or sign) reported, agreeing
- [ ] `python3 compare.py --check` printing SELF-TEST PASS, so the difference is derived twice
- [ ] A run stamp under every published number: date · seed and B · n · the command
- [ ] The `--marginal` and `--paired` verdicts both reported, and whether they agree
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Two systems' 95% marginal CIs overlap. Say why that does not mean the difference is insignificant, and name the one code change that measures the real question.
2. In the paired bootstrap loop, you draw one index per iteration and use it for both systems. What breaks if you draw two independent indices instead, and which earlier strategy does that silently rebuild?
3. The permutation p is `(at_least + 1) / (PERM + 1)`. Explain what the two `+1`s are for and what dishonest number they prevent.
4. Give a three-case A/B example where each system's scores swing widely but B beats A on every case, and say what the overlap rule concludes versus the paired difference.
5. Your own run printed a paired difference CI and its seed. What was the interval, did it clear zero, and by how much did the edge move when you changed the seed?

## External resources

- John Rauser, *Statistics Without the Agonizing Pain* (Strata 2014 talk) — https://www.youtube.com/watch?v=5Dnw46eC-0o — my summary: the case for resampling and permutation over t-tables; if you can write a loop you can test a hypothesis, which is exactly the stance of this module.
- Jacob Cohen, *The Earth Is Round (p < .05)* — https://doi.org/10.1037/0003-066X.49.12.997 — my summary: the classic warning that significance is not size and not truth; read it right after this module's "significance is not size" close.
- scipy.stats paired tests — https://docs.scipy.org/doc/scipy/reference/stats.html — my summary: `ttest_rel` and `wilcoxon` are the library versions of the two-pan balance; `ttest_ind` is the independent-samples test to avoid on paired data, per the corpus-bias rule read against the vendor's own docs.
