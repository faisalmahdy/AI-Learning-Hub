---
id: evals-inter-03
title: One run crowned the wrong model — pass@k, pass@1, and pass^k
topic: evals-and-statistics
level: intermediate
status: ready
time: 8-10h
summary: Rank three systems on one run each and streaky wins at 1.000; run each five times and the same model passes all five on only 1 of 6 tasks, handing the reliability crown to steady — because a single run answers "can it ever", never "can it be relied on".
eli5: One sunk free throw proves nothing — "worked once" isn't "works every time".
---

## Why this module

evals-inter-01 and inter-02 put intervals on scores and judges, but both graded every system exactly once. The scan found the same reflex everywhere: verdicts from a single run. The author's own bake-off is the clean example — six frontier models on one fixed prompt, scored N=1, with the honest conclusion that none cleared the bar — and the metric that would have changed the reading, pass^k, exists across the labs only as a wiki page. `CURRICULUM.md` names the fix: "Re-run the bake-off at N≥5 per model with agreement stats", so that "the old N=1 verdict is confirmed or overturned, with numbers".

This module overturns one at `intermediate`. Three systems run five times each on six tasks, and you compute the three numbers a single run collapses into one: pass@k (does at least one of k pass?), pass@1 (what fraction of runs pass?), and pass^k (do all k pass?). What it omits: no live model calls — the trials are a fixture — and no per-step credit for partial success, which is its own topic. You need inter-01's bootstrap and `math.comb`. Stdlib Python 3, offline, $0.00, about two seconds a run, one sitting. The hard part is one idea: three of these numbers describe the same system and they disagree by 0.8, so "the score" is a question you have not finished asking.

By the end, one command ranks the systems two ways and shows the winner change. Skipping ahead:

```
# modules/evals-and-statistics/code/evals-inter-03/ — COMPLETE, run from that directory
$ python3 trials.py --scoreboard

systems=3  tasks=6  trials each=5  file=trials.json  (fixture, no model call)

SCOREBOARD — the same three systems, four questions
--------------------------------------------------------------------------
  system      N=1     pass@1   pass@5   pass^5
  steady    0.833    0.733    0.833    0.500
  streaky   1.000    0.800    1.000    0.167
  weak      0.667    0.533    1.000    0.000
--------------------------------------------------------------------------
  ranked by N=1     : streaky > steady > weak
  ranked by pass^5  : steady > streaky > weak
  the N=1 winner (streaky) is the pass^5 loser -- rank 2
```

run: 2026-08-22 · trials are a fixture · n=6 tasks x 5 trials · `python3 trials.py --scoreboard`

Read streaky's row across: it scores 1.000, then 0.800, then 1.000, then 0.167. One system, four questions, answers from a perfect crown to a near-total collapse. The single run picked it as best; the "does it pass all five" column drops it to second and hands the title to steady. This module is about why those columns disagree, and which one you should have been reading.

## Concepts

Named here so you can find them again; each is built and, in one case, broken below.

- **N=1 verdict** — a score from one run per task. What everyone ships and what this module overturns.
- **pass@1** — the average per-trial pass rate; the fraction of all runs that pass. Also written pass^1.
- **pass@k** — the probability at least one of k runs passes. Optimistic; saturates near 1.
- **pass^k** — the probability all k runs pass. The reliability number. #3.
- **The unbiased estimator** — pass^k = C(c,k)/C(n,k) from c passes in n trials. The honest way to compute it.
- **Powering a point estimate** — computing pass^k as p^k from a tiny sample. The planted bug.
- **The ranking flip** — when N=1 and pass^k disagree on the winner.

## Worked example

Source: faisalmahdy/agents-workspace-files — `juanda/canaan-model-eval` (six models on one fixed prompt, scored N=1, none cleared the bar); the bake-off this module re-runs at N=5. De-personalized, described only as far as the curriculum states.

Source: faisalmahdy/ai-engineer-learning — `wiki/` (pass^k documented as prose, never executed), and faisalmahdy/AI-Learning-Hub — `code/evals-inter-01/` (the bootstrap reused for the reliability interval).

Script and fixtures: `modules/evals-and-statistics/code/evals-inter-03/` — `trials.py`, 254 lines, `trials.json`, 3 systems x 6 tasks x 5 trials. Every command runs from there.

### Install the frame: a system is a free-throw shooter

In my opinion, the best way to think of a stochastic system on a task is as a free-throw shooter, not as a fixed thing that either can or cannot sink the shot.

Watch a shooter take one shot and sink it. Can they shoot free throws? You have no idea — you saw one shot. Watch five and count: four in, one out. Now three different questions have three different answers. Will at least one of five go in? Almost certainly. What is their make rate? Four in five. Will all five go in? Not this time — one clanked. A single made shot, the N=1 verdict, cannot tell these apart, and in a clutch situation where you need all five, the make rate flatters a shooter who cannot deliver the streak.

Three jobs, one line each: the make rate says "what fraction of shots fall?", pass@k says "will at least one of k fall?", and pass^k says "will all k fall in a row?"

### Look at the data: three shooters, six tasks, five shots each

Three systems, neutral ids with descriptive names. steady is reliable but not the highest average; streaky has the best make rate but rarely runs the table; weak loses on both. Each ran five times on the same six tasks, and `trials.json` stores the five pass/fail outcomes per task, trial 0 first. The single-run verdict reads only trial 0.

```
# trials.py:45-48 and 53-56 — COMPLETE (count passes for one system-task, and the N=1 read)
def passes(system, task):
    """c, n for one (system, task): passes and total trials."""
    trials = system["trials"][task]
    return sum(1 for t in trials if t), len(trials)

def n1_score(system, tasks):
    """Fraction of tasks passed on trial 0 -- the single-run verdict."""
    hits = sum(1 for t in tasks if system["trials"][t][0])
    return hits / len(tasks)

# $ python3 trials.py --n1
#   streaky   single-run score = 1.000
#   steady    single-run score = 0.833
#   weak      single-run score = 0.667
#   N=1 says the best system is: streaky
```

run: 2026-08-22 · fixture, no model call · n=6 tasks · `python3 trials.py --n1`

Now the prediction — commit before the next section. On one run each, streaky scored a perfect 1.000, steady 0.833, weak 0.667. Which system do you actually want in production? Most people keep streaky; it aced the run and the other two dropped tasks. The answer is at the top of the next section, and it is not streaky.

### The one carried example: streaky on task t1

Hold one shooter and one task for the whole module: streaky on t1, five trials `[pass, pass, pass, fail, pass]` — four passes of five. On trial 0 it passed, so N=1 says "streaky does t1." Whether that is *reliable* is the question, and it has an exact answer we can compute by hand before writing any code.

### Strategy #1 — the make rate. Honest, but not reliability.

Count every trial, not just the first. Streaky passes 24 of its 30 trials, an average pass rate of 0.800.

```
# trials.py:59-67 — COMPLETE (pass^k at k=1 is exactly the average pass rate)
def pass_hat_k(system, tasks, k):
    """pass^k: probability all k trials pass, averaged over tasks. Unbiased
    finite-sample estimator: of the C(n,k) ways to draw k of the n trials,
    the fraction where all k drawn are passes is C(c,k)/C(n,k)."""
    total = 0.0
    for t in tasks:
        c, n = passes(system, t)
        total += comb(c, k) / comb(n, k) if c >= k else 0.0
    return total / len(tasks)

# $ python3 trials.py --scoreboard   (the pass@1 column)
#   steady    pass@1 = 0.733
#   streaky   pass@1 = 0.800
#   weak      pass@1 = 0.533
```

run: 2026-08-22 · fixture, no model call · n=6 tasks x 5 trials · `python3 trials.py --scoreboard`

This is called **pass@1** — the average per-trial pass rate, and it is honest as far as it goes. It is a real improvement on N=1: streaky's single run said 1.000, but across all 30 trials it makes 0.800, so the perfect run was luck the average corrects. What it still hides is the shape. Two shooters can both make 80% of their shots while one sinks them in steady streaks and the other in bursts with clangs between, and pass@1 gives them the same number. The kill: pass@1 answers "how often does one run pass", never "how often do five in a row pass", and an agent that must chain five steps lives on the second question.

### Strategy #2 — pass^k, once you compute it honestly

The answer to the prediction: not streaky. To see why, ask the reliability question — do all k pass? — on the carried example. Streaky/t1 has four passes in five trials. Of every way to pick k of those five trials, in what fraction did you pick k passes? That is one line, and here it is blanked. Fill it in before reading on.

```
# trials.py:59-67 — STUB, the line you write first (committed body above)
def pass_hat_k(system, tasks, k):
    total = 0.0
    for t in tasks:
        c, n = passes(system, t)
        # your turn: the chance that k trials drawn from n are all passes.
        # is it (c/n)**k, or something you can count exactly?
        ...
    return total / len(tasks)
```

Stop here. The tempting answer is `(c/n)**k` — the pass rate, raised to the k. For streaky/t1 that is `0.8**5 = 0.328`, so a 33% chance of passing all five. But the model passed four of five: it never once ran the table. Claiming 33% reliability is inventing a streak the data never showed.

```
# a pass^k sketch — COMPLETE, the wrong answer made concrete
c, n = 4, 5
p = c / n                       # 0.8, the make rate
naive_pass5 = p ** 5            # 0.8**5 = 0.328  <- "a third of the time, all five"
# but c=4: only 4 passes exist, so 'all 5 pass' is impossible from these trials
```

Watch the arithmetic: `0.8**5 = 0.328`, and the shooter has four makes. You cannot draw five makes from four. The honest count uses combinations: of the `C(5,5)=1` way to pick all five trials, `C(4,5)=0` of them are all-passes, so pass^5 is `0/1 = 0`. The `--check` mode runs exactly this assertion:

```
# $ python3 trials.py --check   (the two lines that matter)
#   streaky/t1 pass^5 honest      = 0.0000  (c=4<5, must be 0)
#   streaky/t1 pass^5 naive p**k  = 0.3277  (the bug: claims reliability never seen)
```

run: 2026-08-22 · fixture, no model call · n=5 trials · `python3 trials.py --check`

This is the **powering-a-point-estimate** bug: taking a rate from five trials and raising it to a power, as if five runs pinned the rate exactly and the trials were independent. It hides at k=1, where `(c/n)**1` and the honest estimator agree — both give 0.800 — and the gap only opens as k climbs, so a single-shot eval never exposes it. The one-line assertion that catches it: a task with fewer than k passes must have pass^k exactly 0, because you cannot have observed k passes you do not have. The fix is the combinatorial count — `C(c,k)/C(n,k)` — which never claims a streak it did not see.

<svg viewBox="0 0 680 250" role="img" aria-label="Two decreasing curves over k from 1 to 5 for the streaky-on-t1 example: the honest pass^k estimator falling from 0.8 to 0 at k=5, and the naive p to the k curve falling only to 0.33, with the gap between them widening as k grows">
  <g font-family="var(--mono)">
    <text x="100" y="26" font-size="10.5" fill="var(--muted)">streaky/t1 (4 of 5 passed): pass^k as k grows</text>
    <line x1="100" y1="40" x2="100" y2="210" stroke="var(--grid)"></line>
    <line x1="100" y1="210" x2="620" y2="210" stroke="var(--grid)"></line>
    <g font-size="9" fill="var(--muted)" text-anchor="end"><text x="94" y="44">0.8</text><text x="94" y="124">0.4</text><text x="94" y="213">0.0</text></g>
    <g font-size="9" fill="var(--muted)" text-anchor="middle"><text x="100" y="226">k=1</text><text x="230" y="226">k=2</text><text x="360" y="226">k=3</text><text x="490" y="226">k=4</text><text x="620" y="226">k=5</text></g>
    <polyline points="100,50 230,90 360,130 490,170 620,210" fill="none" stroke="var(--s1)" stroke-width="2"></polyline>
    <g fill="var(--s1)"><circle cx="100" cy="50" r="3.5"></circle><circle cx="230" cy="90" r="3.5"></circle><circle cx="360" cy="130" r="3.5"></circle><circle cx="490" cy="170" r="3.5"></circle><circle cx="620" cy="210" r="3.5"></circle></g>
    <polyline points="100,50 230,72 360,98 490,118 620,134" fill="none" stroke="var(--s2)" stroke-width="2" stroke-dasharray="5 3"></polyline>
    <g fill="var(--s2)"><circle cx="100" cy="50" r="3.5"></circle><circle cx="230" cy="72" r="3.5"></circle><circle cx="360" cy="98" r="3.5"></circle><circle cx="490" cy="118" r="3.5"></circle><circle cx="620" cy="134" r="3.5"></circle></g>
    <text x="600" y="204" font-size="9.5" text-anchor="end" fill="var(--s1)">honest -> 0.000</text>
    <text x="600" y="128" font-size="9.5" text-anchor="end" fill="var(--s2)">naive p**k -> 0.328</text>
    <rect x="360" y="150" width="250" height="20" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="485" y="164" font-size="10" text-anchor="middle" fill="var(--acc-ink)">gap = reliability the bug invents</text>
  </g>
</svg>
^ The same task, two ways to compute pass^k. The curves agree at k=1 and split as k grows; the honest curve reaches 0 because the model never passed all five, the naive curve never admits it.

How to read this: the two lines meeting at k=1 is why the bug survives — single-shot evals see only that point. The failure signature is the dashed line staying up while the solid one falls to the floor.

Now the whole reliability curve, computed the honest way for all three systems:

```
# $ python3 trials.py --curve   (honest estimator, k=1..5)
#   system      k=1     k=2     k=3     k=4     k=5
#   steady    0.733   0.650   0.583   0.533   0.500
#   streaky   0.800   0.617   0.450   0.300   0.167
#   weak      0.533   0.267   0.117   0.033   0.000
```

run: 2026-08-22 · fixture, no model call · n=6 tasks x 5 trials · `python3 trials.py --curve`

This is called **pass^k**. Reading the symbols: `C(c,k)/C(n,k)` looks like notation but it is a fraction of ways to choose — `C(4,2)=6` ways to pick two of streaky/t1's four passes, over `C(5,2)=10` ways to pick any two of its five trials, is 0.600. Watch the two rows cross: at k=1 streaky leads steady 0.800 to 0.733, but by k=5 steady leads 0.500 to 0.167. streaky starts higher and falls faster, exactly the burst-and-clang shooter — the more consecutive passes you demand, the worse it looks against the model that just quietly holds its tasks.

Bracket for the pass^5 numbers: chance and floor is 0 — a system that never passes all five scores 0, which weak does — and the ceiling is 1, all five on every task. Real-world size: this is why agent papers report pass^k at all, because a 90%-per-step agent chained over 10 steps is 0.9^10 = 0.35 reliable end to end. Hold weak's 0.000 as the do-nothing baseline.

**One run answers "can it ever" — never "can it be relied on." Those are different questions with different answers.**

### The optimistic metric, for contrast

There is a fourth number, and it goes the other way. pass@k asks whether *at least one* of k runs passes — the retry-until-it-works question.

```
# trials.py:70-78 — COMPLETE (at least one of k passes; the HumanEval estimator)
def pass_at_k(system, tasks, k):
    """pass@k: probability AT LEAST ONE of k trials passes, averaged over tasks.
    1 - C(n-c,k)/C(n,k) -- the HumanEval estimator."""
    total = 0.0
    for t in tasks:
        c, n = passes(system, t)
        miss = comb(n - c, k) / comb(n, k) if (n - c) >= k else 0.0
        total += 1 - miss
    return total / len(tasks)

# $ python3 trials.py --scoreboard   (the pass@5 column)
#   steady    pass@5 = 0.833
#   streaky   pass@5 = 1.000
#   weak      pass@5 = 1.000
```

run: 2026-08-22 · fixture, no model call · n=6 tasks x 5 trials · `python3 trials.py --scoreboard`

pass@5 rates streaky and weak identical at 1.000 — give either five tries and at least one lands, even weak. It saturates near the top and stops separating systems, which is the whole warning: pass@k flatters everything, and picking it because the numbers look good is picking the metric that cannot tell your systems apart.

*"But hold on,"* you say, *"I retry on failure anyway, so pass@k is my real metric."* Good question. Yes, if you can cheaply tell a pass from a fail at run time and try again — that is the code-with-tests case, where pass@k is exactly right. No, if you cannot verify the output as it streams, which is the usual agent case: you ship the first run, and pass^1 rising to pass^k is the reliability your users actually meet.

### The ranking flip

Put the reliability number beside the single-run number and the winner changes.

```
# $ python3 trials.py --scoreboard   (the ranks)
#   ranked by N=1     : streaky > steady > weak
#   ranked by pass^5  : steady > streaky > weak
#   the N=1 winner (streaky) is the pass^5 loser -- rank 2
```

run: 2026-08-22 · fixture, no model call · n=6 tasks x 5 trials · `python3 trials.py --scoreboard`

<svg viewBox="0 0 680 240" role="img" aria-label="Two ranked columns connected by lines: on the left ranked by one run, streaky first, steady second, weak third; on the right ranked by pass to the five, steady first, streaky second, weak third; the streaky and steady lines cross">
  <g font-family="var(--mono)">
    <text x="180" y="32" font-size="11" font-weight="600" text-anchor="middle" fill="var(--ink)">ranked by N=1</text>
    <text x="500" y="32" font-size="11" font-weight="600" text-anchor="middle" fill="var(--ink)">ranked by pass^5</text>
    <rect x="110" y="56" width="140" height="34" rx="6" fill="var(--s2)" opacity="0.5"></rect>
    <rect x="110" y="102" width="140" height="34" rx="6" fill="var(--s1)" opacity="0.5"></rect>
    <rect x="110" y="148" width="140" height="34" rx="6" fill="var(--grid)"></rect>
    <g font-size="11" fill="var(--ink)" text-anchor="middle"><text x="180" y="78">streaky 1.000</text><text x="180" y="124">steady 0.833</text><text x="180" y="170">weak 0.667</text></g>
    <rect x="430" y="56" width="140" height="34" rx="6" fill="var(--s1)" opacity="0.5"></rect>
    <rect x="430" y="102" width="140" height="34" rx="6" fill="var(--s2)" opacity="0.5"></rect>
    <rect x="430" y="148" width="140" height="34" rx="6" fill="var(--grid)"></rect>
    <g font-size="11" fill="var(--ink)" text-anchor="middle"><text x="500" y="78">steady 0.500</text><text x="500" y="124">streaky 0.167</text><text x="500" y="170">weak 0.000</text></g>
    <line x1="250" y1="73" x2="430" y2="119" stroke="var(--s2)" stroke-width="1.8"></line>
    <line x1="250" y1="119" x2="430" y2="73" stroke="var(--s1)" stroke-width="1.8"></line>
    <line x1="250" y1="165" x2="430" y2="165" stroke="var(--muted)" stroke-width="1.2" stroke-dasharray="4 3"></line>
    <rect x="250" y="200" width="180" height="24" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="340" y="216" font-size="10.5" text-anchor="middle" fill="var(--acc-ink)">the top two swap</text>
  </g>
</svg>
^ The three systems ranked by one run and by all-five reliability. streaky and steady cross; weak stays last either way.

How to read this: follow streaky's line down from first to second — that crossing is the whole module. If the two rankings had matched, N=1 would have been enough; they do not, so it was not.

### The running tally

| read | question it answers | winner | numbers |
|---|---|---|---|
| N=1 | did it pass the one run? | streaky | 1.000 / 0.833 / 0.667 |
| pass@1 | what fraction of runs pass? | streaky | 0.800 / 0.733 / 0.533 |
| pass^5 | do all five runs pass? | steady | 0.500 / 0.167 / 0.000 |

The winner flips at pass^5, and it cost one idea — stop scoring the average and score the streak. And yet — pass^5 is estimated from six tasks, and six tasks carry an interval we have not drawn.

### The reliability numbers have their own intervals

pass^5 is a point over six tasks, so inter-01's bootstrap resamples the tasks and recomputes it.

```
# trials.py:94-102 — COMPLETE (the inter-01 bootstrap, now over tasks, recomputing pass^5)
def bootstrap_pass_hat_k_ci(system, tasks, k, rng):
    """Resample the tasks with replacement, recompute pass^k, 10000 times."""
    m = len(tasks)
    boots = []
    for _ in range(BOOT):
        resample = [tasks[rng.randrange(m)] for _ in range(m)]
        boots.append(pass_hat_k(system, resample, k))
    boots.sort()
    return percentile(boots, 2.5), percentile(boots, 97.5)

# $ python3 trials.py --reliability
#   steady    pass^5 = 0.500   95% CI [0.167, 0.833]
#   streaky   pass^5 = 0.167   95% CI [0.000, 0.500]
#   weak      pass^5 = 0.000   95% CI [0.000, 0.000]
```

run: 2026-08-22 · bootstrap seed=0, B=10000 · n=6 tasks · `python3 trials.py --reliability`

The point estimates flip the ranking, but steady's interval `[0.167, 0.833]` and streaky's `[0.000, 0.500]` overlap heavily. On six tasks the flip is real in the point estimates and not yet significant in the intervals — to *claim* steady is more reliable you would run inter-01's paired difference over many more tasks. Six tasks pinned the ranking's direction, not its certainty, and saying otherwise would repeat inter-01's overlap mistake in reverse.

### Two routes, and the below-k assertion

`--check` computes pass@1 two ways and runs the assertion that catches the bug.

```
# $ python3 trials.py --check
#   streaky pass@1 via estimator  = 0.800000
#   streaky pass@1 via raw counts = 0.800000
#   routes agree                  = True
#   streaky/t1 pass^5 honest      = 0.0000  (c=4<5, must be 0)
#   streaky/t1 pass^5 naive p**k  = 0.3277  (the bug: claims reliability never seen)
#   streaky pass^5 CI run 1       = [0.000, 0.500]
#   streaky pass^5 CI run 2       = [0.000, 0.500]
#   deterministic under seed      = True
# SELF-TEST PASS  routes_agree=True  below_k_zero=True  deterministic=True
```

run: 2026-08-22 · seed=0, B=10000 · n=6 tasks x 5 trials · `python3 trials.py --check`

pass@1 agrees to six places by the estimator and by raw counting, the honest pass^5 is 0 for a task with four passes while the buggy one claims 0.3277, and the CI is identical across two runs at the same seed.

**Raising a pass rate to a power is not measuring reliability; it is assuming it. Measure it by counting the runs that all passed.**

### Bridge to the standard names

Nobody outside this module calls a system a free-throw shooter. **pass@k** is the metric from the Codex/HumanEval paper, and `1 - C(n-c,k)/C(n,k)` is its unbiased estimator; **pass^k** (spoken "pass-hat-k" or "pass to the k") is the all-must-pass analog that agent-reliability work reports. pass@1 is just the mean per-trial success rate. Running N trials to estimate these is a **Monte Carlo** estimate, and the spread you would quote instead of a bootstrap is a **binomial** or **Wilson** interval; the bootstrap here is the same tool inter-01 used, so the track carries one method rather than three.

### What we did not settle

The reliability ranking is directional, not significant — steady's and streaky's pass^5 intervals overlap, so six tasks say "steady looks more reliable" and cannot yet say "steady is more reliable"; that is a paired test over more tasks, straight out of inter-01. The estimator assumes the five trials of a task are exchangeable draws of the same underlying rate, which breaks if the harness has memory across trials or the task drifts. The curriculum asked for two raters and agreement stats; here each trial carries a single gold pass/fail, so a real bake-off runs inter-02's kappa on the two raters *first*, because pass^k is only as trustworthy as the labels feeding it. And n=5 trials is tiny — with n=k=5 each task's pass^5 is all-or-nothing, and the smoothing comes only from averaging the six. If the pass@k-versus-pass^k split still feels slippery, that is the right reaction: it is the one idea the module turns on, and everything else is counting passes.

## Build

The pipeline in one paragraph: run each system K times on every task; store the K pass/fail outcomes per task; compute pass@1 (the average), pass@k (at least one), and pass^k (all k) with the combinatorial estimators; rank by pass^k, not by one run, and put a bootstrap interval on it.

We opened on one command that ranks the systems two ways and shows the winner change. The payoff block (again):

```
# modules/evals-and-statistics/code/evals-inter-03/ — COMPLETE, run from that directory
$ python3 trials.py --scoreboard
...
  ranked by N=1     : streaky > steady > weak
  ranked by pass^5  : steady > streaky > weak
  the N=1 winner (streaky) is the pass^5 loser -- rank 2
```

Now point it at your own bake-off. The one dial is `trials.json`: run each of your systems K times on your tasks — K=5 is the floor, more is better — and store the K pass/fail outcomes per task. Everything in `trials.py` derives from that file. This is a module that costs money to reproduce, K model calls per task, so keep the calls committed and re-run the stats offline.

Your number to beat is not a score — it is a **flip**. Rank your systems by their first run, then by pass^5, and see if the order changes. If it does, N=1 was lying to you and you now know by how much. If it does not, run more tasks until the pass^5 intervals separate, because a stable ranking on six tasks is not a settled one. Bring back both rankings and the pass^5 intervals. Good luck.

### FAQ

**Why not just run it once — models are expensive?** Because one run answers "can it ever", and you are shipping "does it reliably"; here that difference sent the crown to the wrong system. Run five, report pass^k, and you know which question you answered.

**pass@k, pass@1, pass^k — which do I report?** All three, because they are three real questions: pass@k if you retry with a verifier, pass@1 for average throughput, pass^k for the reliability a user meets on a single shot. Reporting one and calling it "the score" is the mistake.

**My pass^5 is 0 everywhere — is my system broken?** Maybe not — pass^5 from five trials is all-or-nothing per task, so a decent system with one clang per task scores 0 on that task. Report the whole pass^k curve, not just k=5, and run more trials so the estimate can land between 0 and 1.

**Why is mine slow?** This script is a fixture and is not; yours calls a model K times per task, so it costs K times a single run. That cost is the price of knowing the variance, and you commit the calls so you pay it once.

### Errata

Version one, dated 2026-08-22. The fixture is built so the ranking flips cleanly and the pass^5 intervals still overlap, which is honest to the real situation but was arranged, not observed; on your own data the flip may be sharper or may not happen. One soft spot left in: pass^k here uses the sampling-without-replacement estimator `C(c,k)/C(n,k)`, which answers "k distinct trials of the n I ran"; if you want "k fresh independent draws" you would model the rate and its uncertainty instead, and the two agree only as n grows well past k.

## Definition of done

- [ ] `trials.json` for your own bake-off: each system run K>=5 times per task, outcomes committed before the first statistic
- [ ] The model calls committed so the numbers reproduce offline
- [ ] pass@1, pass@k, and pass^k all reported, computed with the combinatorial estimators, never p**k
- [ ] Systems ranked by pass^k, and the N=1 ranking shown beside it so any flip is visible
- [ ] A bootstrap CI on pass^k, and a note on whether the ranking's top two intervals separate
- [ ] `python3 trials.py --check` printing SELF-TEST PASS, so pass@1 is derived twice and pass^k is 0 below k passes
- [ ] A run stamp under every published number: date · seed and B · n tasks x trials · the command
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. A system scores 1.000 on one run and 0.167 on pass^5. Explain in one sentence how both are true of the same system.
2. Give the three questions pass@k, pass@1, and pass^k each answer, and say which one an agent that cannot verify its own output at run time actually lives on.
3. A task passed 4 of 5 trials. Give its pass^5 by the honest estimator and by the naive p**k, and say which is right and why the other is impossible.
4. State the one-line assertion that catches the powering-a-point-estimate bug, and the k at which the honest and naive numbers stop agreeing.
5. Your own run printed two pass^5 intervals for the top two systems. Did they overlap, and what does that let you claim about the ranking — and what does it not?

## External resources

- Chen et al., *Evaluating Large Language Models Trained on Code* (2021) — https://arxiv.org/abs/2107.03374 — my summary: the source of the pass@k unbiased estimator this module inverts for pass^k; section 2 is worth reading for why they estimate 1 - C(n-c,k)/C(n,k) instead of the naive rate-to-a-power.
- Li et al., *Competition-Level Code Generation with AlphaCode* (2022) — https://arxiv.org/abs/2203.07814 — my summary: pass@k and n@k reported at scale with explicit sampling budgets; a good second look at why "how many tries" is part of the metric, not a footnote.
- This hub, *evals-inter-01* — modules/evals-and-statistics/evals-inter-01.md — my summary: the resampling used here for the pass^k CI is the same bootstrap built there from scratch; if the interval feels like magic, that module derives it.
