---
id: data-adv-01
title: The honest-effect gauntlet — a claim must survive every pitfall guard at once
topic: ai-for-science-and-data
level: advanced
status: ready
time: 12-16h
summary: A reported effect can be wrong in three unrelated ways, and catching one does nothing for the other two — a Simpson reversal (a positive aggregate that is negative in every segment), a regression-to-the-mean artifact (a treated group that improved no more than an untreated control selected the same way), and a multiple-comparisons fluke (a raw p below 0.05 cherry-picked from twenty tests). Composing the AI-for-science track's three guards into one gauntlet, an honest analyst ships a claim only if it is consistent across the confounder's segments AND beats its control AND clears the Bonferroni threshold, so of four claims it ships exactly the one real effect and zero false ones — while a naive analyst who ships anything with a positive aggregate and raw p below 0.05 ships all four, three of them false, each false one a different classic pitfall. The job of an honest analysis is not to find effects but to not report the ones that are not there, and that is the conjunction of every guard, because each pitfall walks straight through the guards built for the others.
eli5: Imagine four people claim they found treasure. One measured the whole beach and says there's gold, but every individual spot he checked was empty — his average lied. One says his lucky charm made him richer, but his friend with no charm got just as rich that week. One tried twenty different spots and got excited about the one that beeped, which is just what random noise does. And one actually dug up a coin in every spot he checked. A careless judge believes all four. A careful judge makes each claim pass every test — same result everywhere, better than plain luck, and not just the best of many tries — and only the real treasure gets through.
---

## Why this module

The AI-for-science track built each statistical pitfall one module at a time, and each was a distinct way a real, correctly-computed number lies. Simpson's paradox (`data-basic-01`) reversed an aggregate that pooled over a confounder — a treatment better on every case but worse overall because it took the harder cases. Regression to the mean (`data-inter-01`) manufactured an improvement out of thin air by selecting the worst group and measuring again, with no intervention at all. Multiple comparisons (`data-inter-04`) turned pure noise into a "significant" finding by running enough tests that one crossed p below 0.05 by chance. Each pitfall has a guard — segment before you aggregate, compare against a control selected the same way, correct the threshold for how many tests you ran — and this module composes the three guards into one gauntlet a claim must pass before it ships.

The composition matters because the pitfalls are orthogonal, and a guard against one is blind to the other two. Segment your data to defeat Simpson and a regression-to-the-mean artifact still sails through, because it is consistent across segments — it is just not real. Run a controlled study to defeat regression and a cherry-picked metric still ships, because it beat its control — it was one of twenty tries. Correct your p-value to defeat multiple comparisons and a Simpson reversal still ships, because its single p-value is tiny — the aggregate is just pointing the wrong way. An analyst who has internalized one pitfall and not the others reports false discoveries with total statistical rigor. Only the conjunction of all three guards keeps every false claim out.

You need the whole track: `data-basic-01` (Simpson), `data-inter-01` (regression to the mean), and `data-inter-04` (multiple comparisons). Everything runs offline against a findings fixture — four claimed effects, each carrying the raw signal all three guards read, and a ground-truth flag so the false- and true-discovery counts are exact — stdlib Python 3, `$0.00`. The instinct to unlearn is that a rigorous analysis is one that applies the right test. It is one that applies every test, because the claim in front of you does not tell you which way it is lying, and the whole discipline of honest analysis is refusing to report an effect until it has survived all the ways it could be an artifact.

Here are the four claims and the raw signal each guard reads:

```
# modules/ai-for-science-and-data/code/data-adv-01/ — COMPLETE, run from that directory
$ python3 gauntlet.py --findings

FINDINGS — four claimed effects and the raw signal each guard reads
--------------------------------------------------------------------------
  id          agg     segments        treated/control   p       n_tests  real
  coaching    +8.500  [7.9, 9.1]      +8.50 / +9.20     0.001   1       False
  new_model   +0.050  [-0.06, -0.04]  +0.05 / +0.00     0.002   1       False
  metric_7    +0.030  [0.02, 0.04]    +0.03 / +0.00     0.03    20      False
  real_fix    +0.060  [0.05, 0.07]    +0.06 / +0.01     0.0004  3       True
```

run: 2026-08-27 · deterministic; claims and the ground-truth 'real' flag are a fixture · 4 findings · `python3 gauntlet.py --findings`

Every one of these has a positive aggregate and, except metric_7, a tiny p-value — they all look shippable. Three are artifacts. This module is which guard catches each, and why you need all three running at once.

## Concepts

Named here so you can find them again; each guard is the core of a prior module.

- **The segments guard** — the effect must hold within every segment of the confounder, not only in the pool (Simpson).
- **The control guard** — the treated change must exceed a control selected the same way, or the "effect" is regression to the mean.
- **The correction guard** — the p-value must clear the Bonferroni threshold alpha/n_tests, not the raw alpha (multiple comparisons).
- **The gauntlet** — ship only if a claim passes all three guards; the conjunction, not any one.
- **A false discovery** — a claim that ships but is not real; the thing an honest analysis exists to prevent.
- **Orthogonality** — each pitfall passes cleanly through the guards built for the other two.

## Worked example

Source: the composition of the AI-for-science track's own guards into one analysis gate — the checklist a careful data scientist runs before reporting an effect from an experiment. The four findings stand in for real claimed results, with a ground-truth flag so the discovery counts are exact and checkable.

Script and fixture: `modules/ai-for-science-and-data/code/data-adv-01/` — `gauntlet.py`, and `findings.json`, four claims. Every command runs from there.

### Guard one: segments (Simpson)

The first guard rejects a claim whose aggregate points one way while every segment points the other — a confounder reversal.

```
# gauntlet.py:45-55 — COMPLETE (the effect must hold within every segment, not just the pool)
def consistent_across_segments(f):
    """Simpson (data-basic-01): the effect holds within every segment, not just in aggregate.

    A positive aggregate whose segments are all negative is a confounder reversal -- the
    aggregate is an artifact of an uneven mix, not a real within-group effect.
    """
    agg = f["aggregate_effect"]
    if agg == 0:
        return False
    return all((seg > 0) == (agg > 0) for seg in f["segments"])
```

Look at `new_model`: aggregate +0.05, segments [-0.06, -0.04]. The new model is worse on the small-stone cases and worse on the large-stone cases, and only wins the pool because of how the cases were distributed between the arms — exactly `data-basic-01`. Its aggregate is real arithmetic and a false picture. The guard checks that every segment agrees in sign with the aggregate; new_model fails, because a claim that reverses inside the confounder is not an effect, it is a mixing artifact.

<svg viewBox="0 0 700 190" role="img" aria-label="A bar chart for new_model. The aggregate bar points up to plus 0.05, labeled apparent win. The two segment bars, small and large, both point down below zero to minus 0.06 and minus 0.04, labeled loses in every segment. The aggregate points opposite to both segments — the Simpson reversal.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">new_model: the aggregate points up, every segment points down</text>
    <line x1="40" y1="100" x2="660" y2="100" stroke="var(--line)"></line>
    <text x="30" y="104" text-anchor="end" fill="var(--muted)" font-size="7">0</text>
    <rect x="120" y="60" width="90" height="40" fill="var(--s1)"></rect><text x="165" y="52" text-anchor="middle" fill="var(--s1)" font-size="8">agg +0.05</text><text x="165" y="128" text-anchor="middle" fill="var(--muted)" font-size="7">aggregate</text>
    <rect x="320" y="100" width="90" height="48" fill="var(--s2)"></rect><text x="365" y="162" text-anchor="middle" fill="var(--s2)" font-size="8">small −0.06</text>
    <rect x="470" y="100" width="90" height="32" fill="var(--s2)"></rect><text x="515" y="162" text-anchor="middle" fill="var(--s2)" font-size="8">large −0.04</text>
    <text x="440" y="180" text-anchor="middle" fill="var(--muted)" font-size="7">every segment: the new model loses</text>
  </g>
</svg>
^ The aggregate rises above zero while both segments fall below it — the classic Simpson reversal. The new model is worse on every fairly-compared case and wins the pool only through an uneven mix, so the segments guard rejects it.

### Guard two: control (regression to the mean)

The second guard rejects a claim whose treated group improved no more than an untreated control selected the same way.

```
# gauntlet.py:57-61 — COMPLETE (the treated change must beat a control selected the same way)
def beats_control(f):
    """Regression to the mean (data-inter-01): the treated change must exceed a control
    selected the same way. If an untreated control moved as much, the 'effect' is regression."""
    return (f["treated_change"] - f["control_change"]) > 0.005
```

Look at `coaching`: treated change +8.50, control change +9.20. The bottom cohort was selected because it scored worst, then measured again, and it rose 8.5 points — but a control group selected the same way and left alone rose 9.2, because a low score is partly bad luck that does not repeat. This is `data-inter-01` exactly: the improvement is regression to the mean, and the control that moved as much is the proof. The guard subtracts the control from the treated change; coaching comes out negative and fails. Note that coaching passes the segments guard cleanly — its effect is consistent across segments — which is precisely why segmenting alone would ship it.

### Guard three: correction (multiple comparisons)

The third guard rejects a claim whose p-value clears the raw 0.05 but not the Bonferroni threshold for how many tests were run.

```
# gauntlet.py:63-66 — COMPLETE (the p-value must clear alpha/n_tests, not the raw alpha)
def survives_correction(f):
    """Multiple comparisons (data-inter-04): the p-value must clear the Bonferroni threshold
    alpha/n_tests, not the raw alpha, or a finding picked from many tests is just noise."""
    return f["p_value"] < ALPHA / f["n_tests"]
```

Look at `metric_7`: p=0.03, n_tests=20. A raw p of 0.03 is "significant" — but it was the best of twenty metrics tested, and across 20 null tests you expect one to cross 0.05 by chance, as `data-inter-04` showed. The Bonferroni threshold is 0.05/20 = 0.0025, and 0.03 does not clear it. The guard fails metric_7. And again note it passes the other two guards — consistent across segments, and there is no control confound — so only the correction guard stands between this noise and a shipped finding.

<svg viewBox="0 0 700 210" role="img" aria-label="Three guards in a row, each a gate. The segments guard catches new_model (Simpson reversal). The control guard catches coaching (regression to the mean). The correction guard catches metric_7 (multiple comparisons). real_fix passes all three gates and ships. Arrows show each false claim dropping out at a different gate, and real_fix flowing all the way through.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">three guards, three different pitfalls — a claim must pass every gate</text>
    <rect x="60" y="80" width="120" height="44" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="120" y="98" text-anchor="middle" fill="var(--acc-ink)" font-size="8">SEGMENTS</text><text x="120" y="112" text-anchor="middle" fill="var(--acc-ink)" font-size="7">Simpson</text>
    <rect x="270" y="80" width="120" height="44" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="330" y="98" text-anchor="middle" fill="var(--acc-ink)" font-size="8">CONTROL</text><text x="330" y="112" text-anchor="middle" fill="var(--acc-ink)" font-size="7">regression to mean</text>
    <rect x="480" y="80" width="120" height="44" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="540" y="98" text-anchor="middle" fill="var(--acc-ink)" font-size="8">CORRECTION</text><text x="540" y="112" text-anchor="middle" fill="var(--acc-ink)" font-size="7">multiple comparisons</text>
    <line x1="30" y1="102" x2="60" y2="102" stroke="var(--ink)"></line><text x="20" y="76" fill="var(--muted)" font-size="7">4 claims</text>
    <line x1="180" y1="102" x2="270" y2="102" stroke="var(--ink)"></line>
    <line x1="390" y1="102" x2="480" y2="102" stroke="var(--ink)"></line>
    <line x1="600" y1="102" x2="640" y2="102" stroke="var(--s1)"></line><text x="655" y="105" fill="var(--s1)" font-size="8">SHIP</text>
    <text x="120" y="150" text-anchor="middle" fill="var(--s2)" font-size="7">✗ new_model</text><line x1="120" y1="124" x2="120" y2="140" stroke="var(--s2)"></line>
    <text x="330" y="150" text-anchor="middle" fill="var(--s2)" font-size="7">✗ coaching</text><line x1="330" y1="124" x2="330" y2="140" stroke="var(--s2)"></line>
    <text x="540" y="150" text-anchor="middle" fill="var(--s2)" font-size="7">✗ metric_7</text><line x1="540" y1="124" x2="540" y2="140" stroke="var(--s2)"></line>
    <text x="655" y="120" fill="var(--s1)" font-size="7">real_fix</text>
    <text x="60" y="184" fill="var(--muted)" font-size="8">each false claim drops out at a different gate — real_fix is the only one through all three</text>
  </g>
</svg>
^ The four claims enter the gauntlet; new_model fails the segments gate, coaching the control gate, metric_7 the correction gate, and only real_fix passes all three. Because the pitfalls are orthogonal, removing any one gate would let its false claim through.

### The gauntlet is the conjunction

The honest analyst ships a claim only if it passes every guard; the naive one ships on a positive aggregate and a raw p below 0.05.

```
# gauntlet.py:69-85 — COMPLETE (the three guards, and the two analysts)
GUARDS = [
    ("segments", consistent_across_segments),   # Simpson
    ("control", beats_control),                 # regression to the mean
    ("correction", survives_correction),        # multiple comparisons
]


def honest_ships(f):
    """Ship only if the claim passes every guard -- the conjunction of all three."""
    return all(g(f) for _, g in GUARDS)


def naive_ships(f):
    """The bug: a positive aggregate and a raw p below 0.05 is enough to ship."""
    return f["aggregate_effect"] > 0 and f["p_value"] < ALPHA
```

`honest_ships` is `all(...)` over the guards — one failure drops the claim. `naive_ships` reads only the aggregate's sign and the raw p-value, the two numbers that every one of these artifacts satisfies. Run both:

```
# $ python3 gauntlet.py --honest
#   id          segments  control  correction  -> verdict (failed pitfall)
#   coaching    True      False    True        -> drop  (control)
#   new_model   False     True     True        -> drop  (segments)
#   metric_7    True      True     False       -> drop  (correction)
#   real_fix    True      True     True        -> SHIP
#   shipped: ['real_fix']   false discoveries: []
```

run: 2026-08-27 · deterministic · `python3 gauntlet.py --honest`

Read the three dropped rows. Each has exactly one `False`, and it is a different column every time: coaching fails control, new_model fails segments, metric_7 fails correction. Three false claims, three distinct pitfalls, each invisible to two of the three guards. real_fix is the only row that is True across the board, and it is the only real effect — it is consistent across segments (0.05, 0.07), beats its control (0.06 vs 0.01), and clears its Bonferroni threshold (0.0004 < 0.05/3). The gauntlet ships it and nothing else.

The false-discovery count is just the shipped claims whose ground-truth flag is false — the analyst shipped them, but they were never real:

```
# gauntlet.py:121-123 — COMPLETE (a false discovery: shipped by the analyst, but not real)
    false_disc = [f["id"] for f in fs if naive_ships(f) and not f["real"]]
    print("-" * 74)
    print("  shipped: %s   of which FALSE discoveries: %s" % (shipped, false_disc))
```

Now the naive analyst on the same four claims:

```
# $ python3 gauntlet.py --naive
#   coaching    agg+8.500  p=0.001   -> SHIP
#   new_model   agg+0.050  p=0.002   -> SHIP
#   metric_7    agg+0.030  p=0.03    -> SHIP
#   real_fix    agg+0.060  p=0.0004  -> SHIP
#   shipped: ['coaching', 'new_model', 'metric_7', 'real_fix']   of which FALSE discoveries: ['coaching', 'new_model', 'metric_7']
```

run: 2026-08-27 · deterministic · `python3 gauntlet.py --naive`

The naive analyst ships all four, three of them false. It is not sloppy — every claim it ships has a positive effect and a small p-value, which is the bar most reported results actually clear. It is exactly the analyst who never learned to look past the headline number, and on this set it is wrong three times out of four.

<svg viewBox="0 0 700 170" role="img" aria-label="Two stacked bars comparing shipped claims. The naive bar has four segments: coaching, new_model, metric_7 all marked false, and real_fix marked real. The honest bar has one segment: real_fix marked real. A label reads naive ships 3 false plus 1 real, honest ships 0 false plus 1 real.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">what each analyst ships from the same four claims</text>
    <text x="20" y="52" fill="var(--s2)">naive</text>
    <rect x="110" y="38" width="120" height="20" fill="var(--s2)"></rect><text x="170" y="52" text-anchor="middle" fill="var(--panel)" font-size="7">coaching ✗</text>
    <rect x="234" y="38" width="120" height="20" fill="var(--s2)"></rect><text x="294" y="52" text-anchor="middle" fill="var(--panel)" font-size="7">new_model ✗</text>
    <rect x="358" y="38" width="120" height="20" fill="var(--s2)"></rect><text x="418" y="52" text-anchor="middle" fill="var(--panel)" font-size="7">metric_7 ✗</text>
    <rect x="482" y="38" width="120" height="20" fill="var(--s1)"></rect><text x="542" y="52" text-anchor="middle" fill="var(--panel)" font-size="7">real_fix ✓</text>
    <text x="612" y="52" fill="var(--s2)" font-size="8">3 false + 1 real</text>
    <text x="20" y="102" fill="var(--s1)">honest</text>
    <rect x="110" y="88" width="120" height="20" fill="var(--s1)"></rect><text x="170" y="102" text-anchor="middle" fill="var(--panel)" font-size="7">real_fix ✓</text>
    <text x="242" y="102" fill="var(--s1)" font-size="8">0 false + 1 real</text>
    <text x="110" y="140" fill="var(--muted)" font-size="8">the gauntlet ships one claim; the naive analyst ships four, three of them artifacts</text>
  </g>
</svg>
^ The naive analyst ships all four claims, three of them false discoveries; the honest gauntlet ships only real_fix. Same evidence, opposite output — the difference is three guards run in conjunction.

**An honest analysis is the conjunction of every pitfall guard — consistent across segments, better than a same-way control, and surviving correction for how many tests were run — because a claim can be a Simpson reversal, a regression artifact, or a multiple-comparisons fluke, and each of those walks cleanly through the two guards built for the others; catching one pitfall is not rigor, it is false confidence.**

### The self-test

The `--check` mode asserts the composition: the gauntlet makes zero false discoveries and keeps the one real effect, the naive analyst makes at least three false discoveries, and — the composition's signature — the three false claims each fail a different guard.

```
# $ python3 gauntlet.py --check
#   honest gauntlet makes zero false discoveries = True ([])
#   honest gauntlet keeps every real effect = True (1 of 1)
#   naive analyst makes >=3 false discoveries = True (['coaching', 'new_model', 'metric_7'])
#   the three false claims each fail a different guard = True (['control', 'correction', 'segments'])
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 gauntlet.py --check`

The `three_distinct` line is the one that proves this is a composition and not a single test in disguise. If all three false claims failed the same guard, you would only need that guard — the other two would be decoration. Instead each false claim fails a different one, so dropping any single guard ships exactly one more false discovery. That is what it means for the guards to be orthogonal, and why the honest verdict is the AND of all of them.

Which guard a claim fails is read off directly — the first guard it does not pass names the pitfall that would have fooled a naive analyst:

```
# gauntlet.py:88-93 — COMPLETE (the failed guard names the pitfall)
def failed_guard(f):
    """Which guard (if any) a finding fails -- the pitfall that would have fooled a naive analyst."""
    for name, g in GUARDS:
        if not g(f):
            return name
    return None
```

<svg viewBox="0 0 700 200" role="img" aria-label="A matrix with three false claims as rows and three guards as columns. coaching passes segments, fails control, passes correction. new_model fails segments, passes control and correction. metric_7 passes segments and control, fails correction. The three FAIL cells form a diagonal, showing each claim fails a different guard.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">each false claim fails a different guard — the FAILs form a diagonal</text>
    <text x="200" y="44" text-anchor="middle" fill="var(--ink)" font-size="8">segments</text>
    <text x="340" y="44" text-anchor="middle" fill="var(--ink)" font-size="8">control</text>
    <text x="480" y="44" text-anchor="middle" fill="var(--ink)" font-size="8">correction</text>
    <text x="30" y="80" fill="var(--ink)" font-size="8">coaching</text>
    <rect x="150" y="64" width="100" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="200" y="80" text-anchor="middle" fill="var(--acc-ink)" font-size="7">pass</text>
    <rect x="290" y="64" width="100" height="24" fill="var(--s2)"></rect><text x="340" y="80" text-anchor="middle" fill="var(--panel)" font-size="7">FAIL</text>
    <rect x="430" y="64" width="100" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="480" y="80" text-anchor="middle" fill="var(--acc-ink)" font-size="7">pass</text>
    <text x="30" y="116" fill="var(--ink)" font-size="8">new_model</text>
    <rect x="150" y="100" width="100" height="24" fill="var(--s2)"></rect><text x="200" y="116" text-anchor="middle" fill="var(--panel)" font-size="7">FAIL</text>
    <rect x="290" y="100" width="100" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="340" y="116" text-anchor="middle" fill="var(--acc-ink)" font-size="7">pass</text>
    <rect x="430" y="100" width="100" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="480" y="116" text-anchor="middle" fill="var(--acc-ink)" font-size="7">pass</text>
    <text x="30" y="152" fill="var(--ink)" font-size="8">metric_7</text>
    <rect x="150" y="136" width="100" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="200" y="152" text-anchor="middle" fill="var(--acc-ink)" font-size="7">pass</text>
    <rect x="290" y="136" width="100" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="340" y="152" text-anchor="middle" fill="var(--acc-ink)" font-size="7">pass</text>
    <rect x="430" y="136" width="100" height="24" fill="var(--s2)"></rect><text x="480" y="152" text-anchor="middle" fill="var(--panel)" font-size="7">FAIL</text>
    <text x="30" y="188" fill="var(--muted)" font-size="8">one FAIL per row, a different column each time — remove any column and one row ships</text>
  </g>
</svg>
^ The three false claims against the three guards: each row has exactly one FAIL, and the FAILs run down the diagonal. Because no two false claims fail the same guard, every guard is load-bearing — remove one column and exactly one false claim ships.

```
# gauntlet.py:164-165 — COMPLETE (the signature check: the false claims fail three different guards)
    fails = sorted({failed_guard(f) for f in fs if not f["real"]})
    three_distinct = fails == ["control", "correction", "segments"]
```

### The running tally

| finding | segments | control | correction | honest | naive | truth |
|---|---|---|---|---|---|---|
| coaching | pass | FAIL | pass | drop | ship | false (regression) |
| new_model | FAIL | pass | pass | drop | ship | false (Simpson) |
| metric_7 | pass | pass | FAIL | drop | ship | false (multiple tests) |
| real_fix | pass | pass | pass | ship | ship | real |

Read the three guard columns for the false rows: the single FAIL slides diagonally down — control, then segments, then correction — one pitfall per row, never the same guard twice. Read the honest and naive columns: honest ships one, naive ships four. The gap between them is not carefulness in general; it is three specific guards, and removing any one of them closes the gap by exactly the one false discovery that guard alone catches. This is why an honest analysis cannot be a single habit like "always segment" or "always correct" — the claim in front of you is silent about which way it lies, so you run every guard, every time.

### What we did not settle

This composes three guards into a per-claim gate; a full analysis pipeline has more, and each earlier module named one. Survivorship bias (`data-inter-05`) is a fourth pitfall — a claim computed over survivors, with the failures silently absent — and it needs its own guard (account for the dropouts), which slots into the same gauntlet. The base-rate fallacy (`data-inter-03`) means a "significant" detector can still be mostly wrong when it fires, so precision must be read against prevalence, not in isolation. Anscombe's quartet (`data-inter-06`) is the reminder that even a claim passing every numeric guard should be looked at — the shape can still betray a fit the summary statistics bless. And the guards here are thresholded hard; a real pipeline reports effect sizes with confidence intervals (`evals-inter`) rather than a binary ship. The invariant survives all of it: an effect is worth reporting only when it has outlived every way it could be an artifact.

## Build

The build in one paragraph: for each claimed effect, read the raw signal three ways — its per-segment effects against the aggregate (Simpson), its treated change against a same-way-selected control (regression to the mean), and its p-value against the Bonferroni threshold alpha over the number of tests run (multiple comparisons) — and ship the claim only if it passes all three guards. Add the survivorship guard (account for dropouts), read precision against the base rate rather than alone, and look at the shape of anything that clears the numbers, because a claim is silent about which way it lies and rigor is running every guard, not the one you happen to favor.

We opened on the four findings. The number that proves the composition works is the false-discovery count:

```
# modules/ai-for-science-and-data/code/data-adv-01/ — COMPLETE, run from that directory
$ python3 gauntlet.py --check
  honest gauntlet makes zero false discoveries = True ([])
  naive analyst makes >=3 false discoveries = True (['coaching', 'new_model', 'metric_7'])
```

Now build your own. Take a set of real claimed effects — from your own experiments or a paper's table — and run each through the three guards. Your number to beat is not how many effects you find; it is **how many false discoveries you ship against a naive positive-aggregate-and-raw-p baseline** — the honest gauntlet should ship zero while keeping the real ones. Then knock out one guard and watch exactly one false claim reappear. Bring back both false-discovery counts. Good luck.

## Definition of done

- [ ] A segments guard rejecting a claim whose aggregate reverses inside the confounder
- [ ] A control guard rejecting a claim whose treated change does not beat a same-way control
- [ ] A correction guard rejecting a claim whose p-value clears raw alpha but not alpha/n_tests
- [ ] A gauntlet shipping a claim only if it passes all three guards
- [ ] A naive baseline shipping on positive aggregate and raw p below 0.05
- [ ] Confirmation the gauntlet makes zero false discoveries and keeps every real effect
- [ ] Confirmation the false claims each fail a different guard (the pitfalls are orthogonal)
- [ ] `python3 gauntlet.py --check` printing SELF-TEST PASS: honest_no_false, honest_keeps_real, naive_leaks, three_distinct
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Name the three guards and the pitfall each defeats. Which prior module is each from?
2. Why is an honest analysis the conjunction of the guards rather than any one? What does "orthogonal pitfalls" mean here?
3. coaching passed the segments guard but was still false. Which guard caught it, and what was the tell in the numbers?
4. metric_7 had a raw p of 0.03, normally "significant." Why did the gauntlet drop it, and what threshold did it fail?
5. Your own claims were run through the gauntlet and a naive baseline. How many false discoveries did each ship, and did knocking out one guard bring exactly one back?

## External resources

- Ioannidis, *Why Most Published Research Findings Are False* — my summary: the paper on how multiple testing, small effects, and flexible analysis inflate false discoveries across a literature; read it for why the guards here are not paranoia but the base rate of published claims.
- Reinhart, *Statistics Done Wrong* — my summary: a working catalog of exactly these pitfalls with worked cases; read it for the confounding, regression, and multiple-comparison chapters that each guard here operationalizes.
- This hub, *data-basic-01*, *data-inter-01*, *data-inter-04* — the Simpson's paradox, regression-to-the-mean, and multiple-comparisons modules this gauntlet composes; read each for one pitfall in full before seeing all three guards run at once.
