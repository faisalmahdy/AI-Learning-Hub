---
id: data-inter-09
title: Berkson's paradox — selecting on a common effect fakes a correlation that isn't there
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 24 min
summary: Two traits independent in the whole population can look strongly correlated inside a group that was selected using both of them. Conditioning on a common effect — a collider — opens a spurious path between its causes. Talent and looks are independent (r=0), but among the cast they correlate −0.5.
eli5: Imagine a club that lets you in if you're either really funny or really kind. Being funny and being kind have nothing to do with each other out in the world. But inside the club, the funny people are often not-so-kind and the kind people are often not-so-funny — because anyone who was neither never got in. The club made up a pattern that isn't real.
---

## Why this module

You will constantly be handed a sample that was already filtered before it reached you, and the filter lies to you about what correlates with what.

Patients who made it into the study were sick enough to enroll. Actors in the dataset were famous enough to have a page. Startups in the analysis survived long enough to be measured. Users in the logs were engaged enough to click. In every case someone or something selected the rows, and the selection was not random — it depended on the very variables you are now trying to relate. When that happens, correlations appear inside your sample that exist in no one who was left out. Not weak ones, either: a real, large, statistically significant negative relationship between two things that are, in the full world, completely independent.

This is Berkson's paradox, and it is the twin of the confounding you may already know from Simpson's. Confounding is a shared cause you failed to adjust for, and the fix is to adjust for it. Berkson is a shared effect you did adjust for — by selecting on it — and the adjustment is what created the illusion. The two mistakes point in opposite directions, which is exactly why people who have learned "always control for more variables" walk straight into this one. Sometimes controlling for a variable is the bug.

We will build the smallest population where the trap is exact: two traits, independent by construction, correlation zero to four decimal places. Then we cast the ones who clear a bar that depends on both, look only at them, and watch the correlation come out −0.5000 from nothing.

**A correlation measured inside a selected group can be entirely manufactured by the selection; the honest question is always "who is not in this sample, and why."**

## Concepts

The structure that makes this happen has a name: a collider. Draw the causal arrows. Talent causes casting. Looks causes casting. Both arrows point into "cast" — they collide there. A variable that two others both point into is a collider on the path between them.

The rule from causal graphs is short and worth memorizing. A collider blocks the path between its causes by default: talent and looks are independent precisely because the only thing connecting them is a variable they both feed, and an un-touched collider keeps that path closed. But conditioning on the collider — filtering to cast = yes, or splitting by it, or adjusting for it in a regression — opens the path. Once open, information flows between the two causes and they become correlated in your conditioned sample.

Why negatively, here? Think about what it takes to be cast when the bar is talent + looks ≥ 8. If I tell you an actor was cast and is low on talent, they must be high on looks — that is the only way they cleared the bar. Being cast plus knowing one trait is low forces the other trait high. That forcing is the correlation. It is not a fact about talent and looks; it is a fact about the arithmetic of the bar and the people it excluded. The plain, low-talent-low-looks actors who would break the pattern are exactly the ones the selection removed.

The everyday versions are everywhere once you see the shape. "Why are the nice guys I date always boring and the exciting ones always jerks?" — because your dating pool selects on nice-or-exciting, and the boring jerks never got a date. "Why does hospital data show a protective effect that vanishes in the general population?" — because admission selects on being sick in some way, colliding two diseases. Same graph every time: two causes, one selected effect, condition on it, get a phantom correlation.

**Independence is a property of the population; conditioning on a common effect of two variables induces a correlation between them that no one in the full population has.**

## Worked example

The fixture is a whole population laid out as a grid, chosen so independence is not approximate but exact.

```json filename=modules/ai-for-science-and-data/code/data-inter-09/population.json:7-16 COMPLETE
  "threshold": 8,
  "people": [
    {
      "talent": 1,
      "looks": 1
    },
    {
      "talent": 1,
      "looks": 2
    },
```

Every combination of talent and looks from 1 to 5 appears exactly once — all twenty-five of them. That is the trick that makes the population correlation exactly zero: with one person at every cell of the grid, knowing someone's talent tells you nothing about the distribution of their looks, because all five looks values are present at every talent level. Independence by construction, not by luck.

The casting rule is one number: cast anyone with talent + looks ≥ 8. Print the grid and mark them.

```text filename=modules/ai-for-science-and-data/code/data-inter-09/collider.py --population
POPULATION — the full talent x looks grid; * marks who gets cast (talent+looks >= 8)
------------------------------------------------------
        looks 1   2   3   4   5
  talent 5   .   .   *   *   * 
  talent 4   .   .   .   *   * 
  talent 3   .   .   .   .   * 
  talent 2   .   .   .   .   . 
  talent 1   .   .   .   .   . 
------------------------------------------------------
  everyone: 25 people;  cast: 6 people (19 left out)
```

Look at the shape of the stars. They form a triangle in the top-right corner, and the triangle has a slope: as you go down in talent (5 → 4 → 3) the cast entries start further right (looks 3 → 4 → 5). That downward-right slope is the negative correlation, drawn in asterisks. The nineteen dots are the people who will never appear in the "study of famous actors," and every one of them is a talent-looks pair that would have pulled the correlation back toward zero.

<svg role="img" aria-label="A 5 by 5 grid of talent by looks; the six cast cells form a triangle in the top-right whose downward-right slope is the negative correlation" viewBox="0 0 320 260" width="320" height="260">
  <rect x="0" y="0" width="320" height="260" fill="var(--panel)" stroke="var(--line)"/>
  <text x="120" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">looks →</text>
  <text x="16" y="130" font-family="var(--mono)" font-size="11" fill="var(--muted)">talent</text>
  <g stroke="var(--grid)">
    <line x1="60" y1="30" x2="60" y2="230"/><line x1="100" y1="30" x2="100" y2="230"/><line x1="140" y1="30" x2="140" y2="230"/><line x1="180" y1="30" x2="180" y2="230"/><line x1="220" y1="30" x2="220" y2="230"/><line x1="260" y1="30" x2="260" y2="230"/>
    <line x1="60" y1="30" x2="260" y2="30"/><line x1="60" y1="70" x2="260" y2="70"/><line x1="60" y1="110" x2="260" y2="110"/><line x1="60" y1="150" x2="260" y2="150"/><line x1="60" y1="190" x2="260" y2="190"/><line x1="60" y1="230" x2="260" y2="230"/>
  </g>
  <g fill="var(--acc-line)" stroke="var(--acc-ink)">
    <rect x="140" y="30" width="40" height="40"/><rect x="180" y="30" width="40" height="40"/><rect x="220" y="30" width="40" height="40"/>
    <rect x="180" y="70" width="40" height="40"/><rect x="220" y="70" width="40" height="40"/>
    <rect x="220" y="110" width="40" height="40"/>
  </g>
  <text x="70" y="250" font-family="var(--mono)" font-size="10" fill="var(--muted)">1</text>
  <text x="110" y="250" font-family="var(--mono)" font-size="10" fill="var(--muted)">2</text>
  <text x="150" y="250" font-family="var(--mono)" font-size="10" fill="var(--muted)">3</text>
  <text x="190" y="250" font-family="var(--mono)" font-size="10" fill="var(--muted)">4</text>
  <text x="230" y="250" font-family="var(--mono)" font-size="10" fill="var(--muted)">5</text>
  <text x="44" y="54" font-family="var(--mono)" font-size="10" fill="var(--muted)">5</text>
  <text x="44" y="134" font-family="var(--mono)" font-size="10" fill="var(--muted)">3</text>
  <text x="44" y="214" font-family="var(--mono)" font-size="10" fill="var(--muted)">1</text>
</svg>
^ The six shaded cells are the cast; the empty lower-left is everyone the bar excluded, and their absence is what tilts the surviving cells into a downward slope.

Predict before running the numbers. The whole population: correlation zero, by construction. The six cast members: the slope you can see in the triangle, so negative. Here is the measurement.

```text filename=modules/ai-for-science-and-data/code/data-inter-09/collider.py --corr
CORR — talent-looks correlation over everyone vs over the cast only
------------------------------------------------------------
  whole population (25 people): r = +0.0000
  cast subset      ( 6 people): r = -0.5000
------------------------------------------------------------
  independent in the world; negatively correlated once you condition on being cast.
```

Zero to four decimals over everyone; minus one-half over the cast. Nothing about talent or looks changed between those two lines — same people, same ratings. The only thing that changed is which rows we were allowed to look at. The correlation is a property of the filter, not the traits.

<svg role="img" aria-label="A causal diagram: talent and looks both point into cast, which is a collider; conditioning on cast opens a spurious path between talent and looks" viewBox="0 0 460 190" width="460" height="190">
  <rect x="0" y="0" width="460" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <rect x="30" y="40" width="90" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="52" y="62" font-family="var(--mono)" font-size="12" fill="var(--acc-ink)">talent</text>
  <rect x="30" y="120" width="90" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="56" y="142" font-family="var(--mono)" font-size="12" fill="var(--acc-ink)">looks</text>
  <rect x="320" y="80" width="110" height="34" fill="var(--s2)" stroke="var(--line)"/>
  <text x="342" y="102" font-family="var(--mono)" font-size="12" fill="var(--ink)">cast (selected)</text>
  <line x1="120" y1="57" x2="320" y2="90" stroke="var(--ink)"/>
  <line x1="120" y1="137" x2="320" y2="104" stroke="var(--ink)"/>
  <text x="200" y="66" font-family="var(--mono)" font-size="11" fill="var(--muted)">causes →</text>
  <text x="200" y="130" font-family="var(--mono)" font-size="11" fill="var(--muted)">causes →</text>
  <line x1="75" y1="74" x2="75" y2="120" stroke="var(--acc-ink)" stroke-dasharray="4 3"/>
  <text x="82" y="100" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">spurious path,</text>
  <text x="82" y="114" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">opened by conditioning</text>
</svg>
^ Both traits point into cast, so cast is a collider; independent while it is left alone, the two causes become linked the moment you condition on it.

The measurement itself is the ordinary Pearson correlation — no trick in the statistic, the whole trick is in the rows you feed it.

```python filename=modules/ai-for-science-and-data/code/data-inter-09/collider.py:46-56 COMPLETE
def pearson(pairs):
    """Pearson correlation of a list of (x, y). Returns 0.0 if either trait has no spread."""
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = mean(xs), mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in pairs)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return 0.0
    return round(cov / (vx * vy) ** 0.5, 4)
```

The population is every grid cell once, and the cast is the subset over the bar. These two functions are the entire difference between the +0.0000 line and the −0.5000 line.

```python filename=modules/ai-for-science-and-data/code/data-inter-09/collider.py:61-69 COMPLETE
def population(data):
    """Every (talent, looks) combination once -- independence by construction."""
    return [(p["talent"], p["looks"]) for p in data["people"]]


def cast(data):
    """The selected subset: talent + looks >= threshold. Selection depends on BOTH traits."""
    t = data["threshold"]
    return [(x, y) for x, y in population(data) if x + y >= t]
```

The condition `x + y >= t` is the collider being switched on. Feed `pearson` the output of `population` and you measure the world; feed it the output of `cast` and you measure the filter.

<svg role="img" aria-label="Two correlation values on a number line: population at zero, cast subset at minus one half" viewBox="0 0 460 150" width="460" height="150">
  <rect x="0" y="0" width="460" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <line x1="40" y1="80" x2="420" y2="80" stroke="var(--line)"/>
  <line x1="230" y1="70" x2="230" y2="90" stroke="var(--ink)"/>
  <text x="222" y="108" font-family="var(--mono)" font-size="11" fill="var(--muted)">0</text>
  <line x1="40" y1="72" x2="40" y2="88" stroke="var(--grid)"/>
  <text x="28" y="108" font-family="var(--mono)" font-size="11" fill="var(--muted)">-1</text>
  <line x1="420" y1="72" x2="420" y2="88" stroke="var(--grid)"/>
  <text x="414" y="108" font-family="var(--mono)" font-size="11" fill="var(--muted)">+1</text>
  <circle cx="230" cy="80" r="7" fill="var(--acc-line)" stroke="var(--acc-ink)"/>
  <text x="196" y="56" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">population +0.00</text>
  <circle cx="135" cy="80" r="7" fill="var(--s2)" stroke="var(--ink)"/>
  <text x="96" y="133" font-family="var(--mono)" font-size="11" fill="var(--ink)">cast -0.50</text>
</svg>
^ Same people, same traits; the correlation slides from exactly zero to −0.5 purely by restricting to the selected subset.

## Build

Wire it up and reproduce both numbers. No dependencies, no randomness — the grid is deterministic, so your +0.0000 and −0.5000 must match to the last digit.

Run `--population` to see the triangle, `--corr` for the two correlations, `--check` for the gate. The self-test does not just check the cast correlation is negative; it checks all four facts that together diagnose a collider, so you cannot pass it with a lucky number.

```python filename=modules/ai-for-science-and-data/code/data-inter-09/collider.py:108-114 COMPLETE
    r_all = pearson(everyone)
    independent = abs(r_all) < 1e-9
    print("  talent and looks are independent in the population = %s (r = %+.4f)" % (independent, r_all))

    r_cast = pearson(chosen)
    spurious_negative = r_cast < -0.2
    print("  within the cast they are negatively correlated = %s (r = %+.4f)" % (spurious_negative, r_cast))
```

The first predicate demands the population correlation be zero to nine decimals — `abs(r_all) < 1e-9` — not merely small. That pins the "independent by construction" claim: if someone perturbs the grid so the traits are only approximately independent, this line fails and the whole diagnosis is void, because the paradox is only interesting when the before-correlation is exactly nothing. The second predicate demands the cast correlation clear −0.2, so a barely-negative fluke would not count as the effect.

The third predicate is the one that names the structure rather than the symptom: it checks that the selection actually split the population on both traits, which is what makes cast a collider and not an innocent filter.

```python filename=modules/ai-for-science-and-data/code/data-inter-09/collider.py:117-119 COMPLETE
    t = data["threshold"]
    depends_on_both = any(x + y < t for x, y in everyone) and any(x + y >= t for x, y in everyone)
    print("  casting depends on both traits (a common effect) = %s (threshold %d)" % (depends_on_both, t))
```

Here is the full gate.

```text filename=modules/ai-for-science-and-data/code/data-inter-09/collider.py --check
SELF-TEST — the population correlation is ~0; selecting on the collider makes it negative
--------------------------------------------------------------------------
  talent and looks are independent in the population = True (r = +0.0000)
  within the cast they are negatively correlated = True (r = -0.5000)
  casting depends on both traits (a common effect) = True (threshold 8)
  the correlation appears only after conditioning on the collider = True
--------------------------------------------------------------------------
SELF-TEST PASS  independent=True  spurious_negative=True  depends_on_both=True  illusion_from_selection=True
```

Four claims, and only the conjunction is the diagnosis. Independent establishes the before. Spurious_negative establishes the after. Depends_on_both establishes that selection actually touched both traits — the thing that makes cast a collider rather than an innocent filter. And illusion_from_selection welds the first two together: the correlation was absent, then present, and the only thing that intervened was the conditioning.

**The paradox is only real if the before-correlation is exactly zero; a self-test that lets "approximately independent" slide would let the fixture cheat.**

## Definition of done

You are done when you can reproduce +0.0000 and −0.5000 and explain, without the diagram, why the second number is negative.

Concretely: `--corr` prints those two values; `--check` prints PASS with four True flags. You can state the collider rule — a common effect blocks its causes' path until you condition on it, then opens it — and you can say which real-world selection turned an innocent dataset into a colliding one: any filter that depended on both variables you are now correlating. You can name the opposite error, confounding, and say why "adjust for more variables" is not a universal fix: adjusting for a collider is precisely the mistake here.

The portable test you carry out of this: before trusting any correlation, ask who was filtered out of the sample and whether the filter could have depended on both variables. If it could, the correlation might be an artifact of the filter, and the honest move is to find or reason about the un-selected rows.

## Boss fight

Here is the mistake in its natural habitat, and it is a published-paper-grade mistake, not a toy.

A researcher studies hospitalized patients and finds that, among them, having diabetes is associated with a lower risk of a second condition — it looks protective. They publish "diabetes may protect against X." The effect is entirely Berkson: admission to the hospital is the collider, both diabetes and X push you toward being admitted, and conditioning on admission induces a spurious negative correlation between them. In the general population there is no protection at all. This exact structure produced real confusion in early analyses of COVID hospitalization and smoking — a phantom protective effect that was selection, not biology.

Your turn, two moves. First, predict what happens if you raise the casting bar. Change threshold from 8 to 9 and predict the cast correlation before you run it: fewer people clear the higher bar, the triangle shrinks toward the corner, and the forced tradeoff gets sharper — so the negative correlation should get stronger, not weaker. Run it and check the direction. Second, break the collider on purpose: change the casting rule so it depends on talent only — cast if talent ≥ 3, ignoring looks. Now selection touches one trait, not both, so cast is no longer a collider between them. Predict the cast correlation and run it: it should snap back to zero, because conditioning on a variable that only one cause feeds does not open any path. If either prediction misses, the mechanism in your head is off — find the row and reconcile it against the arithmetic of who cleared the bar.

## External resources

Judea Pearl and Dana Mackenzie's "The Book of Why" gives the causal-graph account of colliders in plain language, with the collider rule stated exactly as the thing that flips your intuition about controlling for variables.

The Wikipedia article "Berkson's paradox" is unusually good and carries the original 1946 hospital example that gave the effect its name, plus the dating-pool version that makes it stick.

For the modern epidemiology framing — where this is called collider-stratification bias and shows up in every discussion of selection bias — see Hernán, Hernández-Díaz, and Robins, "A structural approach to selection bias," which draws the graphs for real study designs.
