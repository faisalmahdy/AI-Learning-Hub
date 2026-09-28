---
id: teach-inter-15
title: Seed the random generator — or the learner can never reproduce your documented output
topic: teaching-and-portability
level: intermediate
status: ready
time: 21 min
summary: A teaching artifact that uses randomness and documents its output — "you should see a sum of 20" — is unreproducible if the generator is left unseeded, because it draws its start state from the clock and produces a different sequence every run. The learner gets a different number and cannot tell a mistake from expected variation. Seeding makes the run a pure function of the seed. On a five-dice task, two unseeded runs give 17 and 23; seeded with a fixed 42, both give the documented 20.
eli5: If you shuffle a deck and tell a friend "the top card is the seven of hearts," they shuffle their own deck and get something else — your answer was never checkable. But if you both start from the exact same shuffle, you both get the seven of hearts. Seeding a random generator is agreeing on the same shuffle, so everyone can check they got the right answer.
---

## Why this module

A lesson that prints a random result and tells the learner what to expect has quietly made a promise it cannot keep, unless the randomness is anchored.

Plenty of teaching artifacts use randomness — a Monte Carlo simulation, a sampled quiz, a shuffled deck, a randomly initialized model. They run, they print numbers, and the lesson documents those numbers as the expected output: "you should see a sum of 20," "the estimate should be about 3.14." This is exactly the hub's own doctrine — show the real output, let the learner match it. But it only works if running the artifact again produces the same output, and a generator left unseeded does not.

An unseeded pseudo-random generator draws its starting state from the wall clock or system entropy, so it begins in a different place on every run. Different starting state, different sequence, different result. The learner runs your artifact, gets 17 instead of the documented 20, and is stuck: did they make a mistake, is their environment broken, or is the output just supposed to vary? They have no way to know, because the one anchor that would tell them — a reproducible expected value — was never set. "Measure or it didn't happen" collapses into "measure and get something different every time," which teaches nothing.

Seeding fixes it, and the fix rests on a fact about pseudo-random generators: they are deterministic functions of their seed. A PRNG does not produce true randomness; it produces a fixed, reproducible sequence that looks random, and which sequence you get is determined entirely by the seed you start it with. Set the seed to a fixed value at the top of the run and the whole artifact becomes a pure function of that seed — same seed, same sequence, same result, on every run and every machine. The output is still random-looking enough for sampling and shuffling; it is simply pinned, so the documented value is reachable.

On the fixture, a task rolls five dice and sums them with a small deterministic generator. Left unseeded — modeled as starting from a varying clock — two runs give sums of 17 and 23, different and unreproducible. Seeded with a fixed 42, two runs both give 20, matching the documented output.

**A pseudo-random generator is a deterministic function of its seed, so an unseeded artifact starts from the clock and produces a different, unreproducible result each run; setting a fixed seed makes the whole run a pure function of the seed, so the learner reproduces the documented output exactly.**

## Concepts

The core fact is that "random" in computing almost always means pseudo-random: a deterministic recurrence that generates a sequence which passes for random but is fully determined by its initial state. Each step computes the next number from the current one by a fixed formula, so the entire stream is a function of where it started — the seed. This is not a limitation to work around; it is the property that makes reproducibility possible. True randomness (from hardware entropy) could not be reproduced at all; pseudo-randomness can, precisely because it is deterministic underneath.

Whether a run is reproducible therefore comes down to one choice: is the seed fixed or is it taken from the environment? Most generators, if you do not set a seed, seed themselves from something that varies — the current time in nanoseconds, an OS entropy source — specifically so that programs which want unpredictable behavior get it by default. That default is right for a game or a security token and wrong for a teaching artifact, where you want the opposite: a result the reader can reproduce. Setting the seed explicitly overrides the varying default with a constant, converting "different every run" into "same every run."

<svg role="img" aria-label="A generator is a chain where each number is computed from the previous; the seed sets the first, so the whole chain follows from the seed" viewBox="0 0 470 150" width="470" height="150">
  <rect x="0" y="0" width="470" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">each number is x = (a·x + c) mod m — the seed sets x0</text>
  <rect x="30" y="60" width="60" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="44" y="77" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">seed</text>
  <text x="94" y="76" font-family="var(--mono)" font-size="10" fill="var(--muted)">→</text>
  <g fill="var(--panel)" stroke="var(--line)"><rect x="112" y="60" width="50" height="26"/><rect x="182" y="60" width="50" height="26"/><rect x="252" y="60" width="50" height="26"/><rect x="322" y="60" width="50" height="26"/></g>
  <text x="128" y="77" font-family="var(--mono)" font-size="8" fill="var(--ink)">x1</text>
  <text x="198" y="77" font-family="var(--mono)" font-size="8" fill="var(--ink)">x2</text>
  <text x="268" y="77" font-family="var(--mono)" font-size="8" fill="var(--ink)">x3</text>
  <text x="338" y="77" font-family="var(--mono)" font-size="8" fill="var(--ink)">x4</text>
  <text x="166" y="76" font-family="var(--mono)" font-size="10" fill="var(--muted)">→</text>
  <text x="236" y="76" font-family="var(--mono)" font-size="10" fill="var(--muted)">→</text>
  <text x="306" y="76" font-family="var(--mono)" font-size="10" fill="var(--muted)">→</text>
  <text x="30" y="120" font-family="var(--mono)" font-size="8" fill="var(--muted)">fix the seed and the entire chain (and every result) is fixed</text>
</svg>
^ The generator is a deterministic chain — each value computed from the last — so the seed, which sets the first value, determines the whole sequence and everything computed from it.

The consequence is that a seeded run is a pure function of its inputs, and purity is what makes an expected output meaningful. When the run depends only on the seed (and the fixed data), the documented number is a property of the artifact, not an accident of when it happened to run. A learner on a different machine, a different day, gets the same number, so they can compare, debug, and know they succeeded. This is the same reproducibility discipline behind pinning dependency versions, fixing file paths, and committing fixtures — remove the hidden inputs (the clock, the environment, the network) so the output depends only on what is checked in.

Two cautions keep this honest. First, reproducibility can require seeding more than one generator and controlling other sources of nondeterminism — a program might use several libraries' generators, and parallelism, hashing with a random seed, or floating-point summation order can each reintroduce variation even after you seed the obvious generator. Full reproducibility means finding every source of nondeterminism, not just the first. Second, a single fixed seed shows one draw, which can be unrepresentative; for a lesson about a distribution you may want to run many seeds and report the spread, or state the seed so the reader knows the printed numbers are one specific, reproducible sample rather than the whole story. The rule is not "avoid randomness" but "anchor it and disclose it."

**Pseudo-randomness is a deterministic sequence fixed by its seed, so reproducibility hinges on setting the seed instead of taking it from the clock; a seeded run is a pure function of its inputs, making the documented output reproducible — but full reproducibility means seeding every generator and disclosing that one seed shows one sample.**

## Worked example

The fixture is a dice task, a fixed seed, two clock seeds, and the documented answer.

```json filename=modules/teaching-and-portability/code/teach-inter-15/task.json:3-6 COMPLETE
  "n_dice": 5,
  "fixed_seed": 42,
  "clock_seeds": [13, 99],
  "documented_sum": 20
```

Five dice, summed. The fixed seed 42 is the reproducible one; the two clock seeds model an unseeded run starting from a varying clock on two different runs; the documented sum, 20, is what the lesson prints. The generator is a small linear congruential recurrence — a deterministic function of the seed.

```python filename=modules/teaching-and-portability/code/teach-inter-15/seed.py:39-45 COMPLETE
def rolls(seed, n):
    """n dice rolls (1..6) from the LCG started at `seed` -- identical whenever the seed is identical."""
    out, x = [], seed
    for _ in range(n):
        x = (A * x + C) % M
        out.append(x % 6 + 1)
    return out
```

The result of a run is the sum of the rolls from a given seed — nothing but the seed and the count go in.

```python filename=modules/teaching-and-portability/code/teach-inter-15/seed.py:48-49 COMPLETE
def total(seed, n):
    return sum(rolls(seed, n))
```

Predict: the two clock-seeded runs will give different sums (different starting states); the two runs at fixed seed 42 will give the identical sum, which should be the documented 20. Roll them.

```text filename=modules/teaching-and-portability/code/teach-inter-15/seed.py --rolls
ROLLS — five dice and their sum, unseeded (two clocks) vs seeded (fixed 42)
----------------------------------------------------------
  unseeded run 1 (clock 13): [1, 4, 5, 6, 1]  sum 17
  unseeded run 2 (clock 99): [3, 6, 3, 6, 5]  sum 23
  seeded   run 1 (seed  42):   [4, 3, 6, 5, 2]  sum 20
  seeded   run 2 (seed  42):   [4, 3, 6, 5, 2]  sum 20
```

The two unseeded runs produced completely different roll sequences and sums — 17 and 23 — because they started from different clock values. A learner running the unseeded artifact would get one of these (or some third value on their clock) and could never match a documented number. The two seeded runs produced the identical sequence [4, 3, 6, 5, 2] and the identical sum 20, because the same seed forces the same sequence. Now check reproducibility against the documented value.

```text filename=modules/teaching-and-portability/code/teach-inter-15/seed.py --reproduce
REPRODUCE — does each mode match the documented sum of 20?
----------------------------------------------------------
  unseeded: runs give 17 and 23   -> match documented? False
  seeded:   runs give 20 and 20   -> match documented? True
```

The unseeded runs give 17 and 23, neither matching the documented 20 — the lesson's stated answer is unreachable, and worse, unreachable differently each time. The seeded runs both give 20, matching the documentation exactly, so a learner can run it and confirm they got the right answer. The only change between the two modes is whether the seed was fixed or taken from the clock, and that single choice is the entire difference between a reproducible teaching artifact and an unreproducible one.

<svg role="img" aria-label="Unseeded runs branch to different sums 17 and 23 from a clock; seeded runs from a fixed seed both land on the documented 20" viewBox="0 0 470 190" width="470" height="190">
  <rect x="0" y="0" width="470" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">seed source decides reproducibility</text>
  <text x="30" y="52" font-family="var(--mono)" font-size="8" fill="var(--s2)">unseeded (clock)</text>
  <rect x="30" y="60" width="70" height="24" fill="var(--panel)" stroke="var(--s2)"/>
  <text x="40" y="76" font-family="var(--mono)" font-size="8" fill="var(--s2)">clock</text>
  <line x1="100" y1="72" x2="200" y2="55" stroke="var(--s2)"/>
  <line x1="100" y1="72" x2="200" y2="95" stroke="var(--s2)"/>
  <text x="205" y="58" font-family="var(--mono)" font-size="8" fill="var(--s2)">run 1 → 17</text>
  <text x="205" y="98" font-family="var(--mono)" font-size="8" fill="var(--s2)">run 2 → 23</text>
  <text x="300" y="78" font-family="var(--mono)" font-size="8" fill="var(--s2)">≠ doc 20</text>
  <text x="30" y="132" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">seeded (fixed 42)</text>
  <rect x="30" y="140" width="70" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="40" y="156" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">seed 42</text>
  <line x1="100" y1="152" x2="200" y2="152" stroke="var(--acc-line)" stroke-width="2"/>
  <text x="205" y="148" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">run 1 → 20</text>
  <text x="205" y="164" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">run 2 → 20</text>
  <text x="300" y="156" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">= doc 20 ✓</text>
</svg>
^ From the clock, two runs branch to 17 and 23, neither the documented value; from a fixed seed, both runs land on 20, so the documented output is reproducible.

## Build

Reproduce the runs. Pure standard library — a small LCG — so the unseeded 17 and 23 and the seeded 20 come out exactly and identically on any machine.

Run `--rolls` for the sequences, `--reproduce` for the match against the documented value, `--check` for the gate. The seeded-matches-doc check is the reproducibility guarantee in one line — the fixed-seed total equals the documented value.

```python filename=modules/teaching-and-portability/code/teach-inter-15/seed.py:96-97 COMPLETE
    seeded_matches_doc = total(fixed, n) == doc
    print("  the seeded run matches the documented sum = %s (%d)" % (seeded_matches_doc, total(fixed, n)))
```

<svg role="img" aria-label="Bar comparison of run outputs against the documented 20: two unseeded runs at 17 and 23 miss the line, two seeded runs sit exactly on it" viewBox="0 0 470 160" width="470" height="160">
  <rect x="0" y="0" width="470" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">run output vs documented 20 (dashed)</text>
  <line x1="40" y1="130" x2="450" y2="130" stroke="var(--line)"/>
  <line x1="40" y1="60" x2="450" y2="60" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="370" y="56" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">documented 20</text>
  <rect x="70" y="71" width="50" height="59" fill="var(--s2)"/>
  <text x="72" y="145" font-family="var(--mono)" font-size="7" fill="var(--s2)">clock 17</text>
  <rect x="150" y="49" width="50" height="81" fill="var(--s2)"/>
  <text x="152" y="145" font-family="var(--mono)" font-size="7" fill="var(--s2)">clock 23</text>
  <rect x="280" y="60" width="50" height="70" fill="var(--acc-line)"/>
  <text x="282" y="145" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">seed 20</text>
  <rect x="360" y="60" width="50" height="70" fill="var(--acc-line)"/>
  <text x="362" y="145" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">seed 20</text>
</svg>
^ The two clock runs land at 17 and 23, one below and one above the documented line; the two seeded runs sit exactly on it, which is what makes the documented value checkable.

The self-test pins that the unseeded runs disagree and miss the documented value while the seeded runs match it.

```python filename=modules/teaching-and-portability/code/teach-inter-15/seed.py:87-91 COMPLETE
    unseeded_differs = total(c1, n) != total(c2, n)
    print("  two unseeded runs give different sums = %s (%d vs %d)" % (unseeded_differs, total(c1, n), total(c2, n)))

    unseeded_misses_doc = total(c1, n) != doc or total(c2, n) != doc
    print("  the unseeded runs do not match the documented sum = %s (doc %d)" % (unseeded_misses_doc, doc))
```

```text filename=modules/teaching-and-portability/code/teach-inter-15/seed.py --check
SELF-TEST — the unseeded runs disagree and miss the documented value; the seeded runs match it exactly
------------------------------------------------------------------------------------------------
  two unseeded runs give different sums = True (17 vs 23)
  the unseeded runs do not match the documented sum = True (doc 20)
  two seeded runs are byte-for-byte identical = True
  the seeded run matches the documented sum = True (20)
  the sequence is a pure function of the seed = True
------------------------------------------------------------------------------------------------
SELF-TEST PASS  unseeded_differs=True  unseeded_misses_doc=True  seeded_matches_itself=True  seeded_matches_doc=True  pure_function_of_seed=True
```

Five True flags. Unseeded_differs: two unseeded runs give 17 and 23. Unseeded_misses_doc: neither matches the documented 20. Seeded_matches_itself: two seeded runs are byte-for-byte identical. Seeded_matches_doc: the seeded run gives exactly the documented 20. Pure_function_of_seed: same seed yields the same sequence and different seeds yield different ones, confirming the output depends only on the seed. The seeded-matches-doc flag is the payoff — it is what lets a learner check their run against a known answer, which the unseeded artifact makes impossible.

**The seeded-matches-doc flag is the reproducibility guarantee — because the run is a pure function of the fixed seed, the documented 20 is reachable by anyone, which is exactly what an unseeded artifact, drifting with the clock, can never promise.**

## Definition of done

You are done when you reproduce the unseeded drift and the seeded match, and can explain why one is reproducible.

Concretely: `--rolls` shows the two clock runs at 17 and 23 and the two seed-42 runs both at 20; `--reproduce` shows unseeded failing to match the documented 20 and seeded matching it; `--check` prints PASS with five True flags. You can explain that a pseudo-random generator is a deterministic function of its seed, that an unseeded run takes its seed from the varying clock so it is unreproducible while a fixed seed makes the run a pure function of its inputs, and that reproducibility can require seeding every generator and controlling other nondeterminism. You can state the honest caveat: one seed shows one sample, so disclose the seed or run many.

The habit to carry: seed every random generator at the top of any artifact whose output you document or test, and treat an unseeded generator as a reproducibility bug — the same class as a hard-coded absolute path or an unpinned dependency. When a learner reports getting a different number than the lesson shows, or a test passes and fails intermittently, suspect an unseeded generator (or a second one you forgot) before anything subtler. Anchor the randomness, and disclose the seed so the reader knows the printed numbers are one reproducible sample.

## Boss fight

The instructive failure is a tutorial whose "expected output" no one can ever reproduce.

A machine-learning tutorial initializes a model with random weights, trains for a few steps, and documents "you should see a loss around 0.83." Every learner gets a different loss — 0.79, 0.91, 1.02 — because the weights are randomly initialized from an unseeded generator, and the data is shuffled by another unseeded generator. The tutorial's forum fills with "I got a different number, is it broken?" and the author cannot help, because they too get a different number each run. The fix is to seed every source of randomness (the weight initializer, the data shuffler, and the framework's global seed) at the top, so the documented 0.83 is reproducible; the deeper fix is to state the seed and note that other seeds give a range, so learners understand the number is one reproducible sample.

Your turn, two moves. First, model the multi-generator trap: add a second independent draw (a shuffle) seeded from its own clock, and confirm that seeding only the first generator still leaves the run unreproducible — so full reproducibility means finding every source, not just the obvious one. Second, model the disclosure fix: run the task across a range of seeds, report the spread of sums, and confirm that a single seed's 20 is just one point in that spread — showing why a lesson about a distribution should show many seeds or disclose the one it used, rather than presenting a single seeded draw as the whole answer.

## External resources

Any language's random-number documentation (Python's `random.seed`, NumPy's `default_rng`, PyTorch's `manual_seed`) states that the generator is deterministic given a seed and that seeding is how you make results reproducible — the exact mechanism this module demonstrates.

Guides on reproducible research and computational reproducibility (the "Ten Simple Rules for Reproducible Computational Research," and framework "reproducibility" pages) list seeding every generator alongside pinning versions and fixing environments as the standard checklist.

Writing on the difference between pseudo-random and true-random generation (and on cryptographically secure PRNGs) clarifies when determinism is a feature (reproducible experiments) versus a bug (predictable tokens), which is the same seed-source choice viewed from the security side.
