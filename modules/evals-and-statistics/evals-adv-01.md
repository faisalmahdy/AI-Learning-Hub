---
id: evals-adv-01
title: Does the orchestration layer help? The capstone A/B, defended
topic: evals-and-statistics
level: advanced
status: ready
time: 12-16h
summary: Run vanilla against an orchestration layer on a SWE-bench slice and omc resolves 60% vs 40% — a paired +20 points that clears zero at p=0.033 on 15 instances, until you notice a 5-instance slice showed +33 with a bootstrap interval the exact test could never confirm, pass^3 reliability is only 27%, and best-of-3 reporting would have published an 87% resolver.
eli5: Two robot coders, same broken programs — a win is real only with an honest "maybe this much".
---

## Why this module

This is the capstone of Track 1, and it puts the whole track to work on the one job the scan found undone: an A/B benchmark that was built and never run. The author's own harness is the case — a complete SWE-bench A/B rig with an empty `predictions/` directory — and the wiki page that would read it reports resolve rates with no interval. `CURRICULUM.md` sets the bar: "Actually run OMC vs vanilla on a SWE-bench slice, with intervals", done when "results/ is non-empty and there is a defensible claim about whether OMC helps".

This module builds the analysis that turns raw benchmark predictions into that defensible claim, at `advanced`. Two harnesses — vanilla and omc, the orchestration layer — each attempt every instance three times; an attempt resolves the instance when its hidden test suite passes. Then everything the track built lands at once: the paired difference and its interval from evals-inter-01, the pass@k / pass^k views from evals-inter-03, and the deterministic test oracle that lets us skip the judge calibration of evals-inter-02, because on SWE-bench the tests are the gold label. What it omits: no live agent run — the outcomes are a committed fixture — and no multiple-comparison correction, because two systems need none. You need all three earlier modules. Stdlib Python 3, offline, $0.00, about three seconds a run, one long sitting. The hard part is not any single statistic; it is refusing to state the claim more strongly than fifteen instances allow.

By the end, one command produces the claim and the evidence you would defend it with. Skipping ahead:

```
# modules/evals-and-statistics/code/evals-adv-01/ — COMPLETE, run from that directory
$ python3 bench.py --headline

instances=15  attempts each=3  file=results.json  (resolve outcomes are a fixture)

HEADLINE — resolve rate (pass@1) and the paired difference
------------------------------------------------------------------
  vanilla  resolve rate = 0.4000
  omc      resolve rate = 0.6000
  paired difference     = +0.2000
  95% CI (bootstrap)    = [+0.0444, +0.3333]  seed=0, B=10000
  CI clears zero        = True
  sign test: omc wins 9, loses 2, ties 4
  sign-test p (exact)   = 0.0327
------------------------------------------------------------------
  DEFENSIBLE CLAIM: omc resolves 60% vs 40%, +20 points
  on this 15-instance slice the difference clears zero (p=0.033).
  It helps -- but the interval is [4, 33] points wide, so 'how much'
  is far from pinned on 15 instances.
```

run: 2026-08-22 · resolve outcomes are a fixture · bootstrap seed=0, B=10000 · n=15 instances x 3 attempts · `python3 bench.py --headline`

That last paragraph is the deliverable. Not "omc wins" — a claim with a number, an interval, a test, and an honest statement of what fifteen instances cannot buy. By the end you will also know why the same run, read three other ways, says omc is 87%, or 27% reliable, or a coin toss — and which reading you defend.

## Concepts

Named here so you can find them again; each is built, and two are broken, below.

- **The slice** — the set of instances you run; the golden set of basic-01, now SWE-bench issues.
- **Resolve rate** — the fraction of attempts whose patch passes the hidden tests. The pass@1 of this module.
- **The test oracle** — the hidden test suite as the gold label, so no LLM judge is calibrated here.
- **Paired difference** — omc's rate minus vanilla's, per instance; the effect, from inter-01.
- **The defensible claim** — the difference plus its interval plus a test, stated no more strongly than the slice allows.
- **The three views** — pass@1, pass@3, pass^3 on the same run; three questions, from inter-03.
- **Best-of-k as the rate** — scoring an instance by its best attempt and calling it the rate. The planted bug.
- **The slice-size sweep** — the verdict as N grows; where the bootstrap and the exact test disagree.

## Worked example

Source: faisalmahdy/oh-my-claudecode-fork — `benchmark/` (a complete SWE-bench A/B harness with `predictions/` empty); the unrun benchmark whose output this module analyzes. De-personalized, described only as far as the curriculum states.

Source: faisalmahdy/AI-Learning-Hub — `code/evals-inter-01/` (the paired bootstrap and sign test reused here) and `code/evals-inter-03/` (the pass@k / pass^k estimators reused here).

Script and fixtures: `modules/evals-and-statistics/code/evals-adv-01/` — `bench.py`, 295 lines, `results.json`, 15 instances x 3 attempts x 2 systems. **The resolve outcomes are a fixture standing in for one real run** — hand-authored, never a real SWE-bench evaluation of these instances, and the module fences that everywhere it matters. Running the real harness is the hand-off. Every command runs from that directory.

### Install the frame: a paired clinical trial

In my opinion, the best way to think of this A/B is as a paired clinical trial, not a leaderboard.

vanilla is the control arm, omc is the treatment, and the instances are the patients — the *same* patients get both, which is what makes it paired and what makes the comparison sharp: an instance that is hard for vanilla is usually hard for omc too, and that shared difficulty cancels when you subtract within the instance. The endpoint is objective, which is the luxury of this benchmark: the hidden test suite either passes or it does not, so there is no doctor's subjective rating to calibrate — the oracle problem that evals-inter-02 spent a whole module measuring is simply absent here. And the trial's honest output is never "the drug works"; it is an effect size with a confidence interval and a p-value, stated no more strongly than the sample allows.

Three jobs, one line each: the resolve rate says "what fraction of attempts pass?", the paired difference says "how much does omc beat vanilla on the same instance?", and the interval says "how much of that gap could be the luck of which fifteen instances we drew?"

### Look at the data: fifteen instances, weighed both ways

Each instance carries two triples of pass/fail, vanilla and omc, three attempts each, and the per-instance score is its resolve rate — the fraction of its three attempts that passed.

```
# bench.py:49-58 — COMPLETE (count resolves for one instance-system, and its rate)
def resolves(inst, system):
    """c, n for one (instance, system): resolved attempts and total attempts."""
    a = inst[system]
    return sum(1 for x in a if x), len(a)

def rate(inst, system):
    """Resolve rate on one instance: the fraction of its attempts that passed."""
    c, n = resolves(inst, system)
    return c / n

# $ python3 bench.py --slice   (a few rows)
#   django__django-13401                  0.33     1.00    +0.67  omc+
#   matplotlib__matplotlib-23987          0.00     0.00    +0.00
#   psf__requests-2317                    1.00     0.67    -0.33  van+
#   vanilla resolve rate = 0.400    omc resolve rate = 0.600
```

run: 2026-08-22 · fixture · n=15 instances x 3 attempts · `python3 bench.py --slice`

Before any statistic, look at the per-instance differences. omc's rate beats vanilla's on 9 instances, ties on 4, and — kept in on purpose — loses on 2 (`psf__requests-2317` and `pylint-dev__pylint-7080`, where the orchestration made it worse). An honest trial keeps its regressions; hiding them is how you fake an effect.

<svg viewBox="0 0 700 292" role="img" aria-label="Fifteen horizontal lollipops, one per instance, sorted by omc-minus-vanilla resolve-rate difference: two at plus 0.67, seven at plus 0.33, four at zero, and two negative at minus 0.33, with a zero line and the mean at plus 0.20 marked">
  <g font-family="var(--mono)">
    <text x="120" y="24" font-size="10.5" fill="var(--muted)">each row: one instance, omc rate minus vanilla rate (paired)</text>
    <line x1="320" y1="40" x2="320" y2="252" stroke="var(--grid)" stroke-width="1.5"></line>
    <line x1="400" y1="40" x2="400" y2="252" stroke="var(--acc)" stroke-width="1.2" stroke-dasharray="3 3"></line>
    <g font-size="9" fill="var(--muted)" text-anchor="middle"><text x="187" y="270">-0.33</text><text x="320" y="270">0</text><text x="453" y="270">+0.33</text><text x="587" y="270">+0.67</text></g>
    <text x="400" y="52" font-size="9" text-anchor="middle" fill="var(--acc-ink)">mean +0.20</text>
    <g stroke="var(--s1)" stroke-width="2"><line x1="320" y1="62" x2="587" y2="62"></line><line x1="320" y1="76" x2="587" y2="76"></line><line x1="320" y1="90" x2="453" y2="90"></line><line x1="320" y1="104" x2="453" y2="104"></line><line x1="320" y1="118" x2="453" y2="118"></line><line x1="320" y1="132" x2="453" y2="132"></line><line x1="320" y1="146" x2="453" y2="146"></line><line x1="320" y1="160" x2="453" y2="160"></line><line x1="320" y1="174" x2="453" y2="174"></line></g>
    <g fill="var(--s1)"><circle cx="587" cy="62" r="3.5"></circle><circle cx="587" cy="76" r="3.5"></circle><circle cx="453" cy="90" r="3.5"></circle><circle cx="453" cy="104" r="3.5"></circle><circle cx="453" cy="118" r="3.5"></circle><circle cx="453" cy="132" r="3.5"></circle><circle cx="453" cy="146" r="3.5"></circle><circle cx="453" cy="160" r="3.5"></circle><circle cx="453" cy="174" r="3.5"></circle></g>
    <g fill="var(--muted)"><circle cx="320" cy="188" r="3"></circle><circle cx="320" cy="202" r="3"></circle><circle cx="320" cy="216" r="3"></circle><circle cx="320" cy="230" r="3"></circle></g>
    <g stroke="var(--s2)" stroke-width="2"><line x1="320" y1="244" x2="187" y2="244"></line><line x1="320" y1="258" x2="187" y2="258"></line></g>
    <g fill="var(--s2)"><circle cx="187" cy="244" r="3.5"></circle><circle cx="187" cy="258" r="3.5"></circle></g>
    <text x="600" y="90" font-size="9.5" fill="var(--s1)">9 omc+</text>
    <text x="330" y="205" font-size="9.5" fill="var(--muted)">4 tie</text>
    <text x="150" y="255" font-size="9.5" text-anchor="end" fill="var(--s2)">2 van+</text>
  </g>
</svg>
^ The fifteen per-instance effects, sorted. Nine point right (omc resolved more), four sit on zero, two point left (vanilla won). The dashed line is the mean, +0.20.

How to read this: the paired design is the whole picture — every row is one instance compared with itself across arms, so the spread is real per-instance variation, not two clouds of unrelated scores. The failure signature to watch for later is any analysis that forgets these are paired and compares two column totals instead.

### Strategy #1 — the resolve rate and its paired difference

vanilla resolves 0.400 of its attempts, omc 0.600. The gap is the mean of the per-instance differences, which — as inter-01 proved — is exactly the difference of the two rates.

```
# bench.py:67-73 — COMPLETE (the two rates, and the paired difference between them)
def resolve_rate(instances, system):
    return mean([rate(i, system) for i in instances])

def paired_diffs(instances):
    """omc rate minus vanilla rate, per instance. Paired: same instance both."""
    return [rate(i, "omc") - rate(i, "vanilla") for i in instances]

# vanilla resolve rate = 0.4000   omc resolve rate = 0.6000   paired difference = +0.2000
```

run: 2026-08-22 · fixture · n=15 instances · `python3 bench.py --headline`

This is the **resolve rate**, SWE-bench's pass@1: the fraction of attempts that pass the tests. A bare +0.200 is where the unrun harness would stop, and it is not wrong, only undefended. Bracket for +0.200: under the null that omc is no better, the per-instance differences are symmetric about zero, so the chance-level gap is 0.000; the floor is −1.0, the ceiling +1.0. Real-world size: +20 points of resolve rate is enormous for SWE-bench — published jumps between serious systems are often single digits — which is precisely why it needs an interval before anyone believes it.

Now the prediction — commit before the next section. omc is +20 points here on 15 instances. If you had stopped at the first 5 instances, the gap was **+33 points** and its bootstrap interval already cleared zero. Bigger, and apparently significant. So: did running ten more instances make omc look *worse*, and would you have called it at five? Most people would have shipped the +33. The answer is in the sweep, three sections down, and it is no.

### Strategy #2 — the interval, two ways that must agree

A difference with no interval is a rumor. inter-01's paired bootstrap resamples the instances and recomputes the gap; its sign test counts how lopsided the wins are. The capstone runs both, and trusts the gap only when they agree.

```
# bench.py:76-87 — COMPLETE (inter-01's paired bootstrap, resampling instances)
def bootstrap_diff_ci(instances, rng):
    """Resample instances with replacement, recompute the mean paired diff."""
    n = len(instances)
    boots = []
    for _ in range(BOOT):
        s = 0.0
        for _ in range(n):
            i = instances[rng.randrange(n)]
            s += rate(i, "omc") - rate(i, "vanilla")
        boots.append(s / n)
    boots.sort()
    return percentile(boots, 2.5), percentile(boots, 97.5)
```

```
# bench.py:90-97 — COMPLETE (the exact sign test on discordant instances)
def sign_test(instances):
    """Instances where omc's rate beats vanilla's, loses, ties; exact tail."""
    wins = sum(1 for i in instances if rate(i, "omc") > rate(i, "vanilla"))
    losses = sum(1 for i in instances if rate(i, "omc") < rate(i, "vanilla"))
    ties = len(instances) - wins - losses
    n = wins + losses
    tail = sum(comb(n, k) for k in range(wins, n + 1)) / (2 ** n) if n else 1.0
    return wins, losses, ties, tail

# 95% CI (bootstrap) = [+0.0444, +0.3333]   clears zero = True
# sign test: omc wins 9, loses 2, ties 4    sign-test p (exact) = 0.0327
```

run: 2026-08-22 · bootstrap seed=0, B=10000 · n=15 instances · `python3 bench.py --headline`

The bootstrap interval `[+0.0444, +0.3333]` sits entirely above zero, and the sign test — 9 wins, 2 losses, p=0.0327 by the exact binomial tail — is under 0.05 by a different route with no resampling. Two methods, one conclusion: on these 15 instances the effect is real. That is the defensible claim, and it comes with its own honesty: the interval is 29 points wide, so "omc helps" is earned but "omc helps by 20 points" is not — the true effect could be as small as 4 points or as large as 33.

<svg viewBox="0 0 700 150" role="img" aria-label="A number line for the paired difference from minus 0.05 to plus 0.40 with zero marked; the omc-minus-vanilla interval runs from plus 0.044 to plus 0.333 with the point estimate at plus 0.20, sitting entirely to the right of zero">
  <g font-family="var(--mono)">
    <text x="90" y="30" font-size="10.5" fill="var(--muted)">paired difference omc - vanilla (resolve rate)</text>
    <line x1="90" y1="86" x2="620" y2="86" stroke="var(--grid)" stroke-width="1.5"></line>
    <g font-size="9" fill="var(--muted)" text-anchor="middle"><text x="149" y="104">0.00</text><text x="267" y="104">+0.10</text><text x="384" y="104">+0.20</text><text x="502" y="104">+0.30</text><text x="620" y="104">+0.40</text></g>
    <line x1="149" y1="70" x2="149" y2="102" stroke="var(--acc)" stroke-width="1.4" stroke-dasharray="3 3"></line>
    <text x="149" y="66" font-size="9.5" text-anchor="middle" fill="var(--acc-ink)">zero</text>
    <line x1="201" y1="86" x2="541" y2="86" stroke="var(--ink)" stroke-width="2.5"></line>
    <line x1="201" y1="78" x2="201" y2="94" stroke="var(--ink)" stroke-width="2.5"></line>
    <line x1="541" y1="78" x2="541" y2="94" stroke="var(--ink)" stroke-width="2.5"></line>
    <circle cx="384" cy="86" r="4.5" fill="var(--ink)"></circle>
    <text x="384" y="128" font-size="10" text-anchor="middle" fill="var(--ink)">+0.20  [+0.044, +0.333]</text>
    <rect x="420" y="112" width="200" height="20" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="520" y="126" font-size="10" text-anchor="middle" fill="var(--acc-ink)">clears zero · sign p=0.033</text>
  </g>
</svg>
^ The defensible claim as one picture: the effect, its 95% interval, and the fact that the interval never touches zero.

How to read this: the diagnostic is the left end of the bar against the zero line. Here it clears by 0.044 — real, but only just, and the bar's width is the honesty. An interval that kissed zero would be the same point estimate with none of the confidence.

**A benchmark number is a claim, and a claim you cannot state with an interval is a press release.**

### Strategy #3 — three questions the one run answers differently

inter-03's warning lands hard on a benchmark: "resolved" hides which question you asked. The same 15 instances, read three ways:

```
# bench.py:102-118 — COMPLETE (inter-03's estimators: at-least-one, and all-k)
def pass_at_k(instances, system, k):
    """At least one of k attempts resolves, averaged over instances."""
    total = 0.0
    for inst in instances:
        c, n = resolves(inst, system)
        miss = comb(n - c, k) / comb(n, k) if (n - c) >= k else 0.0
        total += 1 - miss
    return total / len(instances)

def pass_hat_k(instances, system, k):
    """All k attempts resolve (reliability), averaged over instances."""
    total = 0.0
    for inst in instances:
        c, n = resolves(inst, system)
        total += comb(c, k) / comb(n, k) if c >= k else 0.0
    return total / len(instances)

# $ python3 bench.py --views
#   metric      question                       vanilla   omc
#   pass@1     avg attempt resolves?          0.400     0.600
#   pass@3     at least one of 3?             0.667     0.867
#   pass^3     all three resolve?             0.200     0.267
#   the omc advantage is +20 pts on pass@1, +20 on pass@3, +7 on pass^3.
```

run: 2026-08-22 · fixture · n=15 instances x 3 attempts · `python3 bench.py --views`

Read the omc column top to bottom: 0.600, 0.867, 0.267. If you retry three times and keep any success, omc clears 0.867 — the number a demo screenshots. If you need it to work every single time, omc is 0.267, and vanilla 0.200, so both are unreliable and the gap shrinks to +7 points. The headline +20 lives at pass@1, the honest average. "omc helps" is true, but it means *more often*, not *reliably* — an agent that resolves 60% of attempts and passes all three on a quarter of instances is a triage tool, not a set-and-forget one, and the three columns say so out loud.

**"It resolved" is one attempt, "it resolves" is a rate, and "you can rely on it" is pass^k — a capstone reports all three or defends none.**

<svg viewBox="0 0 700 220" role="img" aria-label="Grouped bars for three metrics, pass at 1, pass at 3, and pass hat 3, each with a vanilla bar and an omc bar; omc leads on all three but the pass hat 3 bars are both low, near 0.2 and 0.27">
  <g font-family="var(--mono)">
    <text x="80" y="24" font-size="10.5" fill="var(--muted)">three questions, one run — bar height is the score (0 to 1)</text>
    <line x1="80" y1="180" x2="620" y2="180" stroke="var(--grid)"></line>
    <g font-size="9" fill="var(--muted)" text-anchor="end"><text x="74" y="184">0.0</text><text x="74" y="110">0.5</text><text x="74" y="44">1.0</text></g>
    <rect x="130" y="128" width="40" height="52" fill="var(--s1)"></rect>
    <rect x="174" y="102" width="40" height="78" fill="var(--s2)"></rect>
    <text x="172" y="196" font-size="9.5" text-anchor="middle" fill="var(--muted)">pass@1</text>
    <text x="150" y="122" font-size="8.5" text-anchor="middle" fill="var(--ink)">.40</text>
    <text x="194" y="96" font-size="8.5" text-anchor="middle" fill="var(--ink)">.60</text>
    <rect x="310" y="93" width="40" height="87" fill="var(--s1)"></rect>
    <rect x="354" y="67" width="40" height="113" fill="var(--s2)"></rect>
    <text x="352" y="196" font-size="9.5" text-anchor="middle" fill="var(--muted)">pass@3</text>
    <text x="330" y="87" font-size="8.5" text-anchor="middle" fill="var(--ink)">.67</text>
    <text x="374" y="61" font-size="8.5" text-anchor="middle" fill="var(--ink)">.87</text>
    <rect x="490" y="154" width="40" height="26" fill="var(--s1)"></rect>
    <rect x="534" y="145" width="40" height="35" fill="var(--s2)"></rect>
    <text x="532" y="196" font-size="9.5" text-anchor="middle" fill="var(--muted)">pass^3</text>
    <text x="510" y="148" font-size="8.5" text-anchor="middle" fill="var(--ink)">.20</text>
    <text x="554" y="139" font-size="8.5" text-anchor="middle" fill="var(--ink)">.27</text>
    <rect x="130" y="40" width="14" height="14" fill="var(--s1)"></rect><text x="150" y="51" font-size="9.5" fill="var(--muted)">vanilla</text>
    <rect x="220" y="40" width="14" height="14" fill="var(--s2)"></rect><text x="240" y="51" font-size="9.5" fill="var(--muted)">omc</text>
  </g>
</svg>
^ The same A/B under three questions. omc leads all three, but pass^3 — resolve all three attempts — is low for both, and that is the reliability the headline hides.

How to read this: compare the two tall pass@3 bars against the two short pass^3 bars. The drop from "at least one" to "all three" is the stochasticity tax, and it is paid by both systems; a report that shows only pass@3 is selling the retry, not the reliability.

### Break it on purpose: watch the verdict as the slice grows

The prediction is due. Sweep the slice size — the first 5, then 10, then all 15 instances — and read the verdict at each.

```
# $ python3 bench.py --sweep
#   N     omc-vanilla   95% CI               clears 0?   sign p
#   5     +0.333        [+0.067, +0.600]     yes         0.125
#   10    +0.233        [+0.033, +0.400]     yes         0.062
#   15    +0.200        [+0.044, +0.333]     yes         0.033
```

run: 2026-08-22 · bootstrap seed=0, B=10000 · n grows 5 -> 10 -> 15 · `python3 bench.py --sweep`

At N=5 the gap was +0.333 and its bootstrap interval already cleared zero — the answer to the prediction, and it is a trap. The exact sign test at N=5 returns p=0.125, not significance, and it *cannot* do better: only 3 of those 5 instances are discordant, all omc wins, so the smallest p the test can ever report is 0.5³ = 0.125. The bootstrap, resampling continuous rates, will happily hand you an interval above zero on 5 instances; the exact test knows there is not enough evidence there to convict. They agree only at N=15. The +33 headline at N=5 was larger and looked significant and was neither — small slices give loud verdicts, and more data pulled the effect down toward its honest size.

<svg viewBox="0 0 700 190" role="img" aria-label="Three stacked confidence intervals for slice sizes N equals 5, 10 and 15, all clearing zero on a difference axis, annotated with sign-test p values 0.125, 0.062 and 0.033, only the last under 0.05">
  <g font-family="var(--mono)">
    <text x="120" y="24" font-size="10.5" fill="var(--muted)">paired difference as the slice grows — bar is the 95% bootstrap CI</text>
    <line x1="180" y1="44" x2="180" y2="164" stroke="var(--acc)" stroke-width="1.2" stroke-dasharray="3 3"></line>
    <text x="180" y="180" font-size="9" text-anchor="middle" fill="var(--acc-ink)">0</text>
    <g font-size="9" fill="var(--muted)" text-anchor="middle"><text x="320" y="180">+0.20</text><text x="460" y="180">+0.40</text><text x="600" y="180">+0.60</text></g>
    <text x="120" y="70" font-size="10" text-anchor="end" fill="var(--muted)">N=5</text>
    <line x1="227" y1="66" x2="600" y2="66" stroke="var(--s2)" stroke-width="2.5"></line>
    <circle cx="413" cy="66" r="4" fill="var(--s2)"></circle>
    <text x="612" y="70" font-size="9.5" fill="var(--s2)">p=0.125</text>
    <text x="120" y="104" font-size="10" text-anchor="end" fill="var(--muted)">N=10</text>
    <line x1="203" y1="100" x2="460" y2="100" stroke="var(--s1)" stroke-width="2.5"></line>
    <circle cx="343" cy="100" r="4" fill="var(--s1)"></circle>
    <text x="612" y="104" font-size="9.5" fill="var(--muted)">p=0.062</text>
    <text x="120" y="138" font-size="10" text-anchor="end" fill="var(--muted)">N=15</text>
    <line x1="211" y1="134" x2="413" y2="134" stroke="var(--ink)" stroke-width="2.5"></line>
    <circle cx="320" cy="134" r="4" fill="var(--ink)"></circle>
    <text x="612" y="138" font-size="9.5" fill="var(--ink)">p=0.033</text>
    <rect x="360" y="150" width="250" height="20" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="485" y="164" font-size="9.5" text-anchor="middle" fill="var(--acc-ink)">only N=15 clears BOTH tests</text>
  </g>
</svg>
^ The verdict at three slice sizes. Every bootstrap interval clears zero, but the sign-test p only crosses 0.05 at N=15 — the two tests agree only once the slice is big enough.

How to read this: the bar clearing zero is necessary, not sufficient. The diagnostic is the p beside it — a cleared interval with p=0.125 is a slice too small to convict, and reading only the bar is how a five-instance eval gets published as a result.

Here is a symptom table for the failure modes an A/B benchmark actually has, each with the view that catches it:

| injected problem | which view exposes it | signature |
|---|---|---|
| slice too small | sign test p vs bootstrap CI | CI clears zero but exact p stuck ≥ 0.1 |
| single attempt only | pass^k missing | no reliability number; pass@1 sold as "resolves it" |
| best attempt reported | resolve rate vs pass@3 | the "rate" equals pass@k |
| unpaired comparison | paired vs marginal CI | wide overlapping arms hide a real per-instance gap |
| contaminated instance | per-instance outliers | one instance resolves at 3/3 for both, suspiciously easy |

### The planted bug: best-of-three, wearing the resolve rate's name

The commonest SWE-bench reporting error is to score an instance as resolved if *any* attempt passed, then call that the resolve rate. Watch what it does.

```
# bench.py:121-125 — COMPLETE (the bug: any() over attempts, averaged)
def best_of_k_rate(instances, system):
    """THE BUG: score each instance 1 if ANY attempt resolved, then average.
    This is pass@3 wearing the resolve-rate's label; it is >= the real rate and
    equal only when every instance is all-or-nothing."""
    return mean([1.0 if any(inst[system]) else 0.0 for inst in instances])

# $ python3 bench.py --bug
#   vanilla   true resolve rate = 0.400   best-of-3 'rate' = 0.667  (+0.267 inflated)
#   omc       true resolve rate = 0.600   best-of-3 'rate' = 0.867  (+0.267 inflated)
```

run: 2026-08-22 · fixture · n=15 instances x 3 attempts · `python3 bench.py --bug`

Stop here. omc's real resolve rate is 0.600, and best-of-three reports 0.867. Why is that wrong, and not just optimistic? Because `any()` over three attempts is exactly pass@3, a different question — "can it ever, given three tries" — and printing it under the label "resolve rate" answers a question nobody asked with the number everyone reads. It inflates each level by 0.267 here, so a 60% resolver is published as an 87% one. The minimal reproducer:

```
# a best-of-k sketch — COMPLETE, watch the label lie
attempts = [True, False, False]     # one of three passed
rate = sum(attempts) / 3            # 0.333  <- the honest resolve rate
best = 1.0 if any(attempts) else 0  # 1.000  <- 'resolved!' if you keep the best
# report 'best' as the rate and one lucky attempt in three becomes a 100% instance
```

One pass in three becomes a perfect instance the moment you keep the best attempt. It hides at k=1, where `any()` of one attempt equals its rate, so a single-attempt eval never exposes it; the gap only opens once you run repeats — which is the whole point of running repeats. Named: **best-of-k as the rate**. The one-line assertion that catches it: the reported rate must be ≤ pass@k for every k, with equality only when every instance is all-or-nothing, so a "rate" that equals pass@3 has collapsed the attempts. `--check` runs exactly that:

```
# $ python3 bench.py --check
#   diff via rate means     = +0.200000
#   diff via paired diffs   = +0.200000
#   routes agree            = True
#   omc resolve rate        = 0.6000
#   omc pass@3              = 0.8667
#   omc best-of-3           = 0.8667  (== pass@3: True)
#   paired CI run 1         = [+0.0444, +0.3333]
#   paired CI run 2         = [+0.0444, +0.3333]
#   deterministic under seed= True
# SELF-TEST PASS  routes_agree=True  rate<=pass@3=True  deterministic=True
```

run: 2026-08-22 · seed=0, B=10000 · n=15 instances · `python3 bench.py --check`

The difference agrees to six places by two routes, the resolve rate 0.600 sits below pass@3 0.867, and best-of-3 equals pass@3 exactly — the assertion firing on itself. The interval is identical across two seeded runs.

### The running tally

| read | question it answers | verdict | numbers |
|---|---|---|---|
| resolve rate (pass@1) | what fraction of attempts pass? | omc helps | 0.600 vs 0.400, +0.200 [0.044, 0.333], p=0.033 |
| pass^3 | does it pass all three? | both unreliable | 0.267 vs 0.200, gap +0.07 |
| best-of-3 (the bug) | can it ever, in three? | inflated | 0.867 vs 0.667, published as "the rate" |

The defensible verdict is the first row, and it took the whole track to state it that carefully — a paired difference, an interval, an exact test, and three views to keep it honest. And yet — every number here rides on 15 hand-authored fixture instances, and the real claim waits on a real run.

### Bridge to the standard names

Nobody outside this module calls a benchmark a clinical trial. The **resolve rate** is SWE-bench's headline; **pass@k** is from the Codex paper; the paired binary comparison has an exact test of its own, **McNemar's test**, which the sign test here approximates; effect size versus significance is Cohen's old warning, that a big enough slice makes a trivial gap significant and a small one hides a real gap. The real harness reads a `predictions.jsonl`, runs each instance's repository tests inside a Docker image, and writes a `results.json` — the file this module's `results.json` imitates. The "orchestration layer helps" question is exactly the one agent-framework bake-offs ask, and most of them ask it at N=1.

### Real stuff — what changes at benchmark scale

Same components, in the same order, at production scale; none of it alters the analysis you just built. **The slice**: 15 here; SWE-bench Lite is 300 instances and the full set is 2,294, and a real result quotes which. **The attempts**: 3 here as a fixture; real repeats cost real API spend and Docker minutes, which is why people skimp to N=1 and why pass^k goes unreported. **The oracle**: the hidden test suite, which at scale is itself a failure mode — a flaky test resolves an instance by luck, and a contaminated instance whose fix sat in the training data resolves for the wrong reason, so a real report audits its oracle. **The comparison**: two systems here; a real bake-off is six, and comparing six against a baseline needs a multiple-comparison correction this module skipped. **The claim**: the same paired difference, interval, and exact test — that part does not change, and that is the point of building it small first.

### What we did not settle

The largest fence is the biggest one this whole track has carried: the resolve outcomes are a fixture, hand-authored to make the statistics legible, and nothing here is a real evaluation of vanilla or omc on these instances — the module teaches the *method*, and the real run is yours. Beyond that: 15 instances is far too few, and the sweep showed the verdict was not stable until the last few; the oracle is assumed sound, where a real one is flaky and gameable; two systems dodged multiple comparisons; and a slice this small, drawn heavy on django, tells you nothing about per-repository effects. The honest scope of the defensible claim is exactly its interval and no wider. If the pass@1-versus-pass^3-versus-best-of-k distinctions still feel slippery, that is the correct reaction — three of the four numbers on this page are the *same run* read differently, and keeping them straight is the capstone's real skill.

## Build

The pipeline in one paragraph: run vanilla and omc over the same instances K times each; record each attempt's resolve against the hidden tests; compute the resolve rate, the paired difference with a bootstrap interval and an exact test, and the pass@1 / pass@3 / pass^3 views; state a claim no stronger than the interval, and keep the regressions in.

We opened on one command that produces that claim. The payoff block (again):

```
# modules/evals-and-statistics/code/evals-adv-01/ — COMPLETE, run from that directory
$ python3 bench.py --headline
...
  paired difference     = +0.2000
  95% CI (bootstrap)    = [+0.0444, +0.3333]  seed=0, B=10000
  sign-test p (exact)   = 0.0327
  DEFENSIBLE CLAIM: omc resolves 60% vs 40%, +20 points
  It helps -- but the interval is [4, 33] points wide.
```

Now run the real thing. This is the capstone's definition of done, and it is the one module in the track that costs real money and Docker time: check out the harness, generate `predictions.jsonl` for vanilla and for omc on a SWE-bench slice — K≥3 attempts each — score them against the hidden tests, and write the per-instance resolves into `results.json` in this module's shape. Everything in `bench.py` then runs offline on your real numbers. The one dial is `results.json`; nothing else changes.

Your number to beat is not +20 points — it is **agreement between the two tests, and the N at which it arrives**. Run `--headline` and `--sweep`: if your bootstrap interval clears zero but your sign test cannot, your slice is too small and you have no verdict yet, only a rumor. Grow the slice until both agree, report all three views so nobody mistakes pass@3 for reliability, and state the claim at the width of its interval. Bring back the interval, the exact p, and the slice size. Good luck.

### FAQ

**omc resolved 60% and vanilla 40% — isn't that just a win?** It is a defensible win *on 15 instances*, +20 points [4, 33], p=0.033. Drop the interval and the p and you have a leaderboard boast that the next 15 instances might erase.

**Why three attempts instead of one?** Because one attempt is inter-03's coin flip: a single resolve tells you it can, never that it does. Three lets you separate pass@1 from pass^3 and see that omc helps more often without being reliable.

**Do I need an LLM judge for this?** No — that is the gift of SWE-bench. The hidden test suite is the oracle, deterministic and un-gameable in principle, so the judge-calibration of inter-02 is unnecessary here. On a benchmark with no test oracle, you would owe that calibration first.

**Why is mine slow?** This script is a fixture and is instant; yours is slow because it runs an agent K times per instance and executes a test suite in Docker for each. That cost is the price of an interval, and you pay it once and re-run the stats offline.

### Errata

Version one, dated 2026-08-22. The fixture is arranged so the effect is real at N=15 while a 5-instance prefix over-claims — honest to how small slices behave, but arranged, not observed. Two soft spots left in: the sweep uses the *first* N instances rather than random subsamples, so it reads as "if you had stopped early", not "any 5 instances"; and best-of-3 happens to preserve the +0.200 gap here while inflating both levels by 0.267, which is luck — on other data best-of-k distorts the gap too, and the assertion catches the inflated levels regardless.

## Definition of done

- [ ] `results.json` from a real run: vanilla and omc over the same SWE-bench slice, K≥3 attempts, per-instance resolves committed before the first statistic
- [ ] The predictions committed so the numbers reproduce offline
- [ ] Resolve rate reported as the mean over attempts, never best-of-k; pass@1 / pass@3 / pass^3 all shown and labeled
- [ ] The paired difference reported with a bootstrap CI and an exact sign test, and the claim stated no wider than the interval
- [ ] The slice grown until the bootstrap CI and the exact test agree; the N at which they did, recorded
- [ ] `python3 bench.py --check` printing SELF-TEST PASS, so the difference is derived twice and the best-of-k assertion holds
- [ ] A run stamp under every published number: date · seed and B · n instances x attempts · the command
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Two systems are run K times on the same instances. Say why the comparison is paired, and what the pairing cancels that an unpaired one would leave in.
2. At N=5 the bootstrap interval clears zero but the sign test reports p=0.125 and cannot go lower. Explain why 0.125 is the floor, and which test you believe.
3. Give the three numbers pass@1, pass@3, and pass^3 answer, and say which one "omc resolves it" usually means versus which one a user on a single shot actually meets.
4. best-of-3 reports omc at 0.867 when its resolve rate is 0.600. Name the real metric best-of-3 equals, and the one-line assertion that catches the mislabel.
5. Your own run printed a paired CI, an exact p, and a slice size. State the claim you would defend, at exactly the width your interval allows — and the one you would refuse to make.

## External resources

- Jimenez et al., *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* (2023) — https://arxiv.org/abs/2310.06770 — my summary: the benchmark this capstone analyzes; read section 4 for how "resolved" is defined by the hidden test suite, which is why no judge calibration is needed here.
- Chen et al., *Evaluating Large Language Models Trained on Code* (2021) — https://arxiv.org/abs/2107.03374 — my summary: the pass@k estimator reused for the three views; the same combinatorics give the pass^k reliability number this module reports beside the headline.
- This hub, *evals-inter-01* and *evals-inter-03* — modules/evals-and-statistics/ — my summary: the paired bootstrap and sign test, and the pass@k / pass^k estimators, are built from scratch there; this capstone only assembles them, so reach back if either feels like magic.
