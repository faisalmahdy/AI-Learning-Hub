---
id: teach-inter-21
title: Measure an item's discrimination, not just its difficulty — a question that separates nobody counts as good
topic: teaching-and-portability
level: intermediate
status: ready
time: 18 min
summary: A quiz exists to sort learners who have a skill from those who don't, and the natural knob — difficulty, the fraction who pass — is only half the story. An item can sit at a perfect 0.5 pass rate and still measure nothing, because the half who pass are not the half who know: strong and weak students pass it equally. Discrimination is the missing number: rank students by overall score, and take pass_rate(top group) − pass_rate(bottom group). On a fixture of 9 students and 3 items, item A is difficulty 0.44 with discrimination +1.00 (strong pass, weak miss); item B is difficulty 1.00, discrimination 0.00 (everyone passes); item C sits at an ideal difficulty 0.56 yet discrimination 0.00 — the top and bottom thirds pass it equally. Judge by difficulty and C is your best item; judge by discrimination and it is dead weight.
eli5: A good test question is like a sieve that catches the students who studied and lets the others fall through. A question everyone answers right catches nobody. Worse, a question that the top and bottom students get right in equal numbers is a broken sieve — it looks like it is working (half pass, half fail) but it is just sorting people at random. To tell a real question from a broken one, check whether the students who did well on the rest of the test are the ones who got it right.
---

## Why this module

A quiz item's job is to separate the students who have the skill from those who don't, and difficulty — how many pass — cannot tell you whether it does that job or splits the class at random.

The standard advice is to tune an item's difficulty toward the middle, around a 0.5 pass rate, so it is neither trivial nor impossible. That is sound as far as it goes, but it measures the wrong thing on its own. An item can land at a flawless 0.5 pass rate while the half who pass are a random half — some of your strongest students miss it and some of your weakest get it, so it sorts nobody. Difficulty tells you how hard an item is; it is silent on whether the item measures the skill you care about or measures noise. A test built by difficulty alone can be full of items that each look reasonable and collectively rank students by luck.

**Difficulty says how hard an item is; it says nothing about whether the right students pass it, so an item at ideal difficulty can still measure nothing.**

Discrimination is the number difficulty leaves out. Rank the students by their overall score, take the top group and the bottom group, and ask how much more the top group passes the item than the bottom: `discrimination = pass_rate(top) − pass_rate(bottom)`. A good item is one the strong students pass and the weak ones miss — high, positive discrimination. An item everyone passes, or one the top and bottom pass equally, has zero discrimination however good its difficulty looks. This module scores three items on both numbers and shows the one difficulty would crown is the one discrimination throws out.

## Concepts

**Difficulty** is the pass rate: the fraction of all students who got the item right. A difficulty of 0.5 means half passed; the "ideal difficulty" heuristic aims here to maximize how finely an item can rank.

**Discrimination** is `pass_rate(top group) − pass_rate(bottom group)` after ranking students by their total score. It answers the question difficulty ignores: do the students who know the material pass this item more than the students who don't?

**High positive discrimination is the goal.** The strong students pass and the weak ones miss, so the item's result agrees with the rest of the test — it adds signal.

**Zero discrimination is dead weight.** Both an item everyone passes (top and bottom both at 1.0) and an item strong and weak pass equally (both at, say, 0.67) score zero — the item does not distinguish anyone, no matter its difficulty.

**Negative discrimination is an alarm.** If the weak students beat the strong ones, the item is usually mis-keyed or rewards a misconception; it actively subtracts signal and should be fixed or cut, not merely down-weighted.

**Difficulty and discrimination are independent axes: an item at ideal difficulty can have zero discrimination, so you must measure whether the right students pass — not just how many — before you trust an item.**

<svg role="img" aria-label="Difficulty and discrimination are two independent axes; item A sits high on discrimination, items B and C sit at zero discrimination regardless of their difficulty" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="12" fill="var(--muted)" font-size="8">difficulty (x) vs discrimination (y) — the axes are independent</text>
  <line x1="35" y1="105" x2="285" y2="105" stroke="var(--grid)" stroke-width="1"/><text x="250" y="118" fill="var(--muted)" font-size="7">difficulty →</text>
  <line x1="35" y1="20" x2="35" y2="105" stroke="var(--grid)" stroke-width="1"/><text x="8" y="30" fill="var(--muted)" font-size="7">disc ↑</text>
  <line x1="35" y1="95" x2="285" y2="95" stroke="var(--line)" stroke-width="1" stroke-dasharray="2 3"/><text x="240" y="93" fill="var(--muted)" font-size="7">keep bar</text>
  <circle cx="130" cy="25" r="4" fill="var(--s1)"/><text x="120" y="20" fill="var(--s1)" font-size="8">A (.44, 1.0)</text>
  <circle cx="275" cy="105" r="4" fill="var(--s2)"/><text x="228" y="103" fill="var(--s2)" font-size="8">B (1.0, 0)</text>
  <circle cx="160" cy="105" r="4" fill="var(--s2)"/><text x="150" y="122" fill="var(--s2)" font-size="8">C (.56, 0)</text>
  <text x="35" y="128" fill="var(--muted)" font-size="8">C's ideal difficulty puts it mid-x, but its zero discrimination pins it to the floor</text>
</svg>
^ Only vertical position (discrimination) decides whether an item is kept; item C's respectable horizontal position (difficulty) buys it nothing because it sits on the floor.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/teach-inter-21/discrimination.py

The fixture is nine students, each with a total score and a pass/fail on three items.

```json filename=modules/teaching-and-portability/code/teach-inter-21/items.json:3-13 COMPLETE
  "students": [
    {"id": "s1", "total": 9, "A": 1, "B": 1, "C": 1},
    {"id": "s2", "total": 8, "A": 1, "B": 1, "C": 0},
    {"id": "s3", "total": 7, "A": 1, "B": 1, "C": 1},
    {"id": "s4", "total": 6, "A": 1, "B": 1, "C": 0},
    {"id": "s5", "total": 5, "A": 0, "B": 1, "C": 1},
    {"id": "s6", "total": 4, "A": 0, "B": 1, "C": 0},
    {"id": "s7", "total": 3, "A": 0, "B": 1, "C": 1},
    {"id": "s8", "total": 2, "A": 0, "B": 1, "C": 0},
    {"id": "s9", "total": 1, "A": 0, "B": 1, "C": 1}
  ],
```

Difficulty is the pass rate; discrimination splits students by total score and compares the top and bottom groups' pass rates.

```python filename=modules/teaching-and-portability/code/teach-inter-21/discrimination.py:41-58 COMPLETE
def difficulty(students, item):
    """Pass rate: the fraction of students who got the item right."""
    return sum(s[item] for s in students) / len(students)


def groups(students, frac=1 / 3):
    """Split students into the top and bottom `frac` by total score."""
    ranked = sorted(students, key=lambda s: s["total"], reverse=True)
    k = max(1, int(len(ranked) * frac))
    return ranked[:k], ranked[-k:]


def discrimination(students, item):
    """pass_rate(top group) - pass_rate(bottom group): does the item separate strong from weak?"""
    top, bottom = groups(students)
    top_rate = sum(s[item] for s in top) / len(top)
    bottom_rate = sum(s[item] for s in bottom) / len(bottom)
    return top_rate - bottom_rate
```

The items view ranks by discrimination and keeps only items above a bar, ignoring difficulty in the verdict.

```python filename=modules/teaching-and-portability/code/teach-inter-21/discrimination.py:68-71 COMPLETE
    for it in sorted(items, key=lambda i: discrimination(students, i), reverse=True):
        d, disc = difficulty(students, it), discrimination(students, it)
        verdict = "keeps" if disc >= 0.3 else "measures nothing"
        print("  %-4s   %.2f         %+.2f            %s" % (it, d, disc, verdict))
```

Run `--items` for both numbers per item.

```text filename=--items
ITEMS — difficulty (pass rate) and discrimination (top - bottom)
--------------------------------------------------------------
  item   difficulty   discrimination   verdict
  A      0.44         +1.00            keeps
  B      1.00         +0.00            measures nothing
  C      0.56         +0.00            measures nothing
--------------------------------------------------------------
  an ideal 0.5 difficulty does not save an item whose discrimination is 0.
```

Item A has the lowest pass rate, 0.44, and a discrimination of +1.00: in this clean fixture every top-group student passes it and every bottom-group student misses it, so it perfectly agrees with the rest of the test. Item B is passed by all nine — difficulty 1.00, discrimination 0.00 — so it ranks nobody. Item C is the trap: its difficulty is 0.56, squarely in the "ideal" band, and by difficulty alone it looks like the best-tuned item on the test. Its discrimination is 0.00.

<svg role="img" aria-label="Item A has low difficulty and high discrimination; item C has ideal difficulty but zero discrimination; item B is too easy with zero discrimination" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">difficulty (grey) vs discrimination (color) per item</text>
  <line x1="30" y1="95" x2="285" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <text x="8" y="90" fill="var(--muted)" font-size="8">A</text>
  <rect x="40" y="60" width="35" height="35" fill="var(--grid)"/><text x="44" y="55" fill="var(--muted)" font-size="7">diff .44</text>
  <rect x="80" y="15" width="35" height="80" fill="var(--s1)"/><text x="82" y="11" fill="var(--s1)" font-size="7">disc 1.0</text>
  <text x="130" y="90" fill="var(--muted)" font-size="8">B</text>
  <rect x="150" y="15" width="35" height="80" fill="var(--grid)"/><text x="152" y="11" fill="var(--muted)" font-size="7">diff 1.0</text>
  <rect x="190" y="95" width="35" height="0" fill="var(--s2)"/><text x="190" y="107" fill="var(--s2)" font-size="7">disc 0</text>
  <text x="238" y="90" fill="var(--muted)" font-size="8">C</text>
  <rect x="250" y="50" width="16" height="45" fill="var(--grid)"/><text x="244" y="45" fill="var(--muted)" font-size="7">diff .56</text>
  <rect x="267" y="95" width="16" height="0" fill="var(--s2)"/><text x="266" y="107" fill="var(--s2)" font-size="7">disc 0</text>
  <text x="30" y="118" fill="var(--muted)" font-size="8">C's difficulty looks ideal, but its discrimination bar has no height</text>
</svg>
^ Item C's grey difficulty bar sits at an attractive mid-height, but its discrimination bar is flat on the axis — the two numbers disagree, and only discrimination tells the truth.

## Build

Discrimination is just the gap between two groups. Run `--groups` to see it.

```text filename=--groups
GROUPS — top third ['s1', 's2', 's3'] vs bottom third ['s7', 's8', 's9'] (by total score)
--------------------------------------------------------------
  item   top pass   bottom pass   discrimination
  A      1.00       0.00          +1.00
  B      1.00       1.00          +0.00
  C      0.67       0.67          +0.00
```

Now the trap is visible. On item A the top third passes at 1.00 and the bottom third at 0.00 — a clean split, discrimination +1.00. On item C both the top third and the bottom third pass at 0.67: the strong and weak students do equally well, so the item's 0.56 difficulty comes from a coin-flip that ignores ability. Item B is passed by everyone, top and bottom alike at 1.00. Difficulty could never have caught B and C, because difficulty never looks at *who* passes — only discrimination compares the groups, and only the comparison reveals that C separates no one.

<svg role="img" aria-label="For item A the top group passes at 1.0 and bottom at 0.0; for item C both groups pass at 0.67, an equal split that discriminates nothing" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">top-group pass (dark) vs bottom-group pass (light)</text>
  <line x1="30" y1="95" x2="285" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <text x="55" y="110" fill="var(--muted)" font-size="8">item A</text>
  <rect x="45" y="20" width="24" height="75" fill="var(--s1)"/><text x="46" y="16" fill="var(--s1)" font-size="7">top 1.0</text>
  <rect x="72" y="95" width="24" height="0" fill="var(--muted)"/><text x="70" y="107" fill="var(--muted)" font-size="7">bot 0.0</text>
  <text x="185" y="110" fill="var(--muted)" font-size="8">item C</text>
  <rect x="175" y="45" width="24" height="50" fill="var(--s1)"/><text x="176" y="41" fill="var(--s1)" font-size="7">top .67</text>
  <rect x="202" y="45" width="24" height="50" fill="var(--muted)"/><text x="203" y="41" fill="var(--muted)" font-size="7">bot .67</text>
  <text x="30" y="118" fill="var(--muted)" font-size="8">A splits the groups (gap = 1.0); C's bars are equal (gap = 0)</text>
</svg>
^ Item A's two bars are as far apart as possible; item C's are the same height — the discrimination is exactly that gap, and C has none.

## Definition of done

The self-test pins the trap: A discriminates, B and C do not, C's ideal difficulty is no defense, difficulty alone would rank C above A, and only A clears a discrimination bar.

```python filename=modules/teaching-and-portability/code/teach-inter-21/discrimination.py:97-110 COMPLETE
    good_item_discriminates = dA >= 0.5
    print("  item A separates strong from weak students = %s (discrimination %+.2f)" % (good_item_discriminates, dA))

    easy_item_zero_disc = dB == 0.0 and fB == 1.0
    print("  item B is too easy and discriminates nothing = %s (difficulty %.2f, disc %+.2f)" % (easy_item_zero_disc, fB, dB))

    ideal_difficulty_still_useless = 0.4 <= fC <= 0.6 and dC == 0.0
    print("  item C has ideal difficulty but zero discrimination = %s (difficulty %.2f, disc %+.2f)" % (ideal_difficulty_still_useless, fC, dC))

    difficulty_would_mislead = fC > fA and dC < dA
    print("  difficulty alone would rank C above A, discrimination reverses it = %s (C %.2f>%.2f A, but disc %+.2f<%+.2f)" % (difficulty_would_mislead, fC, fA, dC, dA))

    only_A_kept = [i for i in data["items"] if discrimination(students, i) >= 0.3] == ["A"]
    print("  only item A clears a discrimination bar of 0.3 = %s" % only_A_kept)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the easy item and the mid-difficulty item both have zero discrimination; only A separates
--------------------------------------------------------------------------------------------------------
  item A separates strong from weak students = True (discrimination +1.00)
  item B is too easy and discriminates nothing = True (difficulty 1.00, disc +0.00)
  item C has ideal difficulty but zero discrimination = True (difficulty 0.56, disc +0.00)
  difficulty alone would rank C above A, discrimination reverses it = True (C 0.56>0.44 A, but disc +0.00<+1.00)
  only item A clears a discrimination bar of 0.3 = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  good_item_discriminates=True  easy_item_zero_disc=True  ideal_difficulty_still_useless=True  difficulty_would_mislead=True  only_A_kept=True
```

**Done means the two axes are provably independent: item C's difficulty of 0.56 would rank it the best-tuned item, yet its discrimination is 0.00 while item A's is +1.00 — so an item passes only when the right students pass it, not merely enough of them.**

## Boss fight

The fixture used the students' total score to rank them. Predict the flaw in scoring an item's discrimination when the item's own result is part of that total. It is tempting to compute each student's total over the whole quiz, including the item you are evaluating.

Including the item in its own total inflates its discrimination, because the item is then partly correlated with itself. A student who passed the item gets a point toward the total that decides which group they land in, so passers are nudged into the top group and failers into the bottom — the very split the discrimination measures. The fix is the corrected (point-biserial) form: rank each item against the total of the *other* items, so the criterion is independent of the item under test. On a long quiz the inflation is tiny and often ignored, but on a short one it can turn a useless item's discrimination positive; when you can, exclude the item from its own criterion.

The deeper caution is that discrimination is only as trustworthy as the total it ranks against. If the whole quiz measures the wrong thing, an item that "discriminates" merely agrees with a bad ruler — high discrimination against a flawed total is not validity. Discrimination tells you an item is consistent with the rest of the test; it does not tell you the test measures the skill you meant. And a single item's statistics are noisy on a small cohort: a discrimination computed on nine students, like this fixture, is an illustration, not a verdict — real item analysis wants enough students that the top and bottom groups are stable. Use discrimination to flag items for review, not to auto-delete them, and pair it with a human read of what the item actually asks.

```python filename=modules/teaching-and-portability/code/teach-inter-21/discrimination.py:53-58 COMPLETE
def discrimination(students, item):
    """pass_rate(top group) - pass_rate(bottom group): does the item separate strong from weak?"""
    top, bottom = groups(students)
    top_rate = sum(s[item] for s in top) / len(top)
    bottom_rate = sum(s[item] for s in bottom) / len(bottom)
    return top_rate - bottom_rate
```

**Rate an item by discrimination — how much more the strong students pass it than the weak — not by difficulty alone, since an ideal-difficulty item can separate no one; but rank against the other items' total to avoid self-inflation, treat high discrimination as agreement with the test rather than proof the test is valid, and flag rather than auto-cut on small cohorts.**

## External resources

Any classical-test-theory or item-analysis reference — the definitions of item difficulty (p-value), discrimination index, and the point-biserial correlation, with the rule-of-thumb bands for keeping, revising, and discarding items.

The documentation for assessment platforms' item-analysis reports (for example the discrimination index and point-biserial columns in test-scoring tools) — the same two numbers as they appear in practice, with guidance on interpreting negative discrimination.

The companion "size the mastery quiz to the decision" and "correct the score for guessing before you call it mastery" modules — quiz length, guessing, and item discrimination are three facets of making an assessment's number mean what you think it means.
