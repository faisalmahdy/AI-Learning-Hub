---
id: teach-inter-09
title: Correct the score for guessing before you call it mastery — raw accuracy promotes a coin-flipper
topic: teaching-and-portability
level: intermediate
status: ready
time: 22 min
summary: On a multiple-choice quiz, blind guessing scores 1/g for free, so raw accuracy counts luck as knowledge. The correction-for-guessing formula docks the expected lucky hits back out. A learner who truly knows 60% scores 70% raw and clears a 65% bar; corrected, they score exactly 60% and are held.
eli5: On a four-answer quiz you get a quarter of the answers right just by closing your eyes and picking. So a score of 70% isn't 70% knowing — some of it is lucky picks. If you subtract out the lucky ones, you find out how much this person actually knows before you decide they're ready to move on.
---

## Why this module

Every advancement decision you make from a multiple-choice score is reading luck as if it were knowledge, and the fewer choices the item has, the more luck you are misreading.

The arithmetic is unavoidable. A four-choice item hands out the correct answer to one in four blind guesses. Close your eyes and mark the whole quiz at random and you expect 25% correct while knowing nothing at all. So a raw score is never a measure of knowledge — it is knowledge plus a guessing floor, and the floor does not go away just because the learner also knew some real answers. A learner who genuinely knows 60% of the material and guesses the rest will, on average, convert a chunk of those guesses into correct answers and post a raw score well above 60%. If your advancement bar sits in the gap between what they know and what they scored, you promote someone who is not ready, and you do it on data that looks perfectly solid.

This is not an exotic failure. It is the default behavior of grading by percent-correct, which is how almost every quiz is graded. The fix is nearly as old as standardized testing — a one-line correction that estimates how many of the correct answers were probably lucky and subtracts them back out. It is called the correction for guessing, or formula scoring, and it turns a raw score into an estimate of actual knowledge.

We will build a record where the ground truth is known: a learner who truly knew twelve of twenty items. They guessed the other eight, two came up lucky, and they posted a raw 70% against a 65% bar — advance. Then we apply the correction, watch the score fall to exactly 60%, and watch the decision flip to hold — which is the decision the ground truth agrees with.

**A multiple-choice score is knowledge plus a guessing floor; deciding mastery on the raw number advances learners whose margin over the bar is made of luck.**

## Concepts

Start with the guessing floor. With g choices, a blind guess is correct with probability 1/g: one-half for true/false, one-quarter for four-choice, one-fifth for five-choice. That floor is the score of pure ignorance, and any sensible measure of knowledge has to be calibrated so that pure ignorance reads as zero, not as 1/g.

The correction for guessing does exactly that calibration. The formula is `score = R - W/(g-1)`, where R is the number right, W the number wrong, and g the number of choices. The reasoning is a small piece of bookkeeping about guesses. Assume every wrong answer was a guess — you knew it, you would have gotten it right. For a learner who guesses, wrong guesses and lucky-right guesses come in a fixed ratio: with g choices, each correct guess is accompanied by about g−1 wrong ones, because one of every g guesses lands and g−1 miss. So the number of lucky-right guesses is about W/(g−1), and subtracting that from R removes the luck, leaving an estimate of how many items the learner actually knew.

Watch what the correction does to the two extremes, because that is how you know it is calibrated right. A learner who knows everything gets all items right, W = 0, and the correction subtracts nothing — a perfect score stays perfect. A learner who knows nothing and guesses everything gets, in expectation, N/g right and the rest wrong; plug those into `R - W/(g-1)` and it comes out to zero. Ignorance reads as zero, mastery reads as full, and everyone in between is placed on that honest scale instead of the inflated raw one.

<svg role="img" aria-label="Two scales compared: on the raw scale pure guessing reads at the 0.25 floor, on the corrected scale it reads at zero, while full mastery reads 1.0 on both" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="24" font-family="var(--mono)" font-size="11" fill="var(--muted)">raw scale</text>
  <line x1="120" y1="40" x2="420" y2="40" stroke="var(--line)"/>
  <line x1="120" y1="34" x2="120" y2="46" stroke="var(--grid)"/><text x="112" y="62" font-family="var(--mono)" font-size="10" fill="var(--muted)">0</text>
  <line x1="420" y1="34" x2="420" y2="46" stroke="var(--grid)"/><text x="414" y="62" font-family="var(--mono)" font-size="10" fill="var(--muted)">1</text>
  <circle cx="195" cy="40" r="5" fill="var(--s2)" stroke="var(--ink)"/><text x="150" y="30" font-family="var(--mono)" font-size="10" fill="var(--ink)">guessing 0.25</text>
  <circle cx="420" cy="40" r="5" fill="var(--acc-line)" stroke="var(--acc-ink)"/>
  <text x="16" y="104" font-family="var(--mono)" font-size="11" fill="var(--muted)">corrected scale</text>
  <line x1="120" y1="120" x2="420" y2="120" stroke="var(--line)"/>
  <line x1="120" y1="114" x2="120" y2="126" stroke="var(--grid)"/><text x="112" y="142" font-family="var(--mono)" font-size="10" fill="var(--muted)">0</text>
  <line x1="420" y1="114" x2="420" y2="126" stroke="var(--grid)"/><text x="414" y="142" font-family="var(--mono)" font-size="10" fill="var(--muted)">1</text>
  <circle cx="120" cy="120" r="5" fill="var(--s2)" stroke="var(--ink)"/><text x="126" y="110" font-family="var(--mono)" font-size="10" fill="var(--ink)">guessing 0</text>
  <circle cx="420" cy="120" r="5" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="330" y="110" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">mastery 1.0</text>
</svg>
^ The correction slides pure guessing from the 0.25 floor down to zero while leaving full mastery at 1.0 — it re-zeros the scale so ignorance reads as knowing nothing.

The trap is that the raw score feels like the real thing. It is a count of correct answers, concrete and defensible — "they got 70% right, that's a fact." And it is a fact; it is just not a fact about knowledge. The gap between raw and corrected is widest exactly where it matters most: near the passing bar, where borderline learners cluster, and where a few points of luck decide whether someone advances before they are ready.

**Raw accuracy measures answers; the correction measures knowledge, and the two diverge most for the borderline learners whose advancement you most need to get right.**

## Worked example

The fixture is a response record with the ground truth attached — for each item, whether the learner actually knew it, and whether they got it right.

```json filename=modules/teaching-and-portability/code/teach-inter-09/responses.json:7-15 COMPLETE
  "choices": 4,
  "advance_threshold": 0.65,
  "items": [
    {
      "item": "q01",
      "known": true,
      "correct": true
    },
```

Four choices per item, a 0.65 bar to advance. The `known` flag is ground truth we get to see because this is a fixture — in a real quiz you never observe it, which is the whole reason you need the correction. The lucky guesses are the interesting rows.

```json filename=modules/teaching-and-portability/code/teach-inter-09/responses.json:70-74 COMPLETE
    {
      "item": "q13",
      "known": false,
      "correct": true
    },
```

Item q13: `known` is false, `correct` is true. The learner did not know it and got it right anyway — a lucky guess, exactly the kind of answer that inflates the raw score. There are two such rows, q13 and q14, and they are the difference between what the learner knows and what they scored. Print the full record.

```text filename=modules/teaching-and-portability/code/teach-inter-09/guessing.py --responses
  item   knew   correct   how
  q01   yes    yes       knew it
  ...
  q12   yes    yes       knew it
  q13   no     yes       lucky guess
  q14   no     yes       lucky guess
  q15   no     no        wrong guess
  q16   no     no        wrong guess
  q17   no     no        wrong guess
  q18   no     no        wrong guess
  q19   no     no        wrong guess
  q20   no     no        wrong guess
----------------------------------------------
  14 right, 6 wrong; 12 truly known, 8 guessed.
```

Twelve known, eight guessed; of the eight guesses, two lucky and six wrong. That two-of-eight is not arbitrary — it is one in four, the four-choice guessing rate, which is what makes the correction land exactly on the truth rather than approximately. Fourteen right total, so the raw score is 14/20 = 0.70.

<svg role="img" aria-label="A stacked bar: 12 known answers plus 2 lucky guesses make the raw score of 14, sitting above the advance bar; the known portion alone sits below it" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="24" font-family="var(--mono)" font-size="11" fill="var(--muted)">raw score = known + lucky guesses</text>
  <rect x="40" y="40" width="240" height="30" fill="var(--acc-line)" stroke="var(--acc-ink)"/>
  <text x="120" y="60" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">12 known</text>
  <rect x="280" y="40" width="40" height="30" fill="var(--s2)" stroke="var(--line)"/>
  <text x="326" y="60" font-family="var(--mono)" font-size="11" fill="var(--ink)">+2 luck</text>
  <text x="330" y="34" font-family="var(--mono)" font-size="10" fill="var(--ink)">raw 0.70</text>
  <line x1="260" y1="30" x2="260" y2="150" stroke="var(--ink)" stroke-dasharray="4 3"/>
  <text x="200" y="120" font-family="var(--mono)" font-size="11" fill="var(--ink)">bar 0.65</text>
  <text x="40" y="100" font-family="var(--mono)" font-size="11" fill="var(--muted)">known alone (0.60) falls left of the bar;</text>
  <text x="40" y="116" font-family="var(--mono)" font-size="11" fill="var(--muted)">the two lucky guesses carry the score over it.</text>
</svg>
^ The advance bar cuts between real knowledge (0.60) and the luck-inflated raw score (0.70); the two lucky guesses are the entire margin.

Raw accuracy just counts correct answers.

```python filename=modules/teaching-and-portability/code/teach-inter-09/guessing.py:38-40 COMPLETE
def raw_accuracy(items):
    """Fraction correct -- counts a lucky guess as if it were knowledge."""
    return round(sum(1 for it in items if it["correct"]) / len(items), 4)
```

The correction subtracts the estimated lucky hits — `W/(g-1)` of them — before dividing.

```python filename=modules/teaching-and-portability/code/teach-inter-09/guessing.py:43-48 COMPLETE
def corrected_score(items, choices):
    """Correction for guessing: (R - W/(g-1)) / N -- docks the expected lucky hits back out."""
    right = sum(1 for it in items if it["correct"])
    wrong = len(items) - right
    corrected_right = right - wrong / (choices - 1)
    return round(corrected_right / len(items), 4)
```

With R = 14, W = 6, g = 4, the correction removes 6/3 = 2 lucky hits, leaving 12 — the exact number the learner knew. And the ground truth is right there in the fixture to check against.

```python filename=modules/teaching-and-portability/code/teach-inter-09/guessing.py:51-53 COMPLETE
def true_known(items):
    """Ground truth: the fraction the learner actually knew (fixture flag, not computed from answers)."""
    return round(sum(1 for it in items if it["known"]) / len(items), 4)
```

Now score it both ways and read the decisions.

```text filename=modules/teaching-and-portability/code/teach-inter-09/guessing.py --score
SCORE — raw accuracy vs guessing-corrected, advance at 0.65
--------------------------------------------------------
  raw accuracy:        0.70  -> ADVANCE
  corrected for guess: 0.60  -> HOLD
--------------------------------------------------------
  raw counts 2 lucky guesses as knowledge and clears the bar; corrected does not.
```

Raw 0.70 clears the 0.65 bar and advances the learner. Corrected 0.60 falls below it and holds them. Same twenty answers, opposite decisions, and the corrected 0.60 is not a conservative fudge — it is exactly the fraction the learner actually knew. The correction did not lower the score to be safe; it lowered it to be accurate.

<svg role="img" aria-label="Two scores against the advance bar: raw 0.70 clears it and advances, corrected 0.60 falls short and holds, with true knowledge also at 0.60" viewBox="0 0 460 160" width="460" height="160">
  <rect x="0" y="0" width="460" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <line x1="300" y1="20" x2="300" y2="140" stroke="var(--ink)" stroke-dasharray="4 3"/>
  <text x="306" y="34" font-family="var(--mono)" font-size="11" fill="var(--ink)">bar 0.65</text>
  <text x="16" y="56" font-family="var(--mono)" font-size="11" fill="var(--ink)">raw 0.70</text>
  <rect x="90" y="44" width="240" height="22" fill="var(--s2)" stroke="var(--line)"/>
  <text x="336" y="60" font-family="var(--mono)" font-size="11" fill="var(--ink)">ADVANCE</text>
  <text x="16" y="96" font-family="var(--mono)" font-size="11" fill="var(--ink)">corrected 0.60</text>
  <rect x="130" y="84" width="150" height="22" fill="var(--acc-line)" stroke="var(--acc-ink)"/>
  <text x="286" y="100" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">HOLD</text>
  <text x="16" y="132" font-family="var(--mono)" font-size="11" fill="var(--muted)">true known 0.60 — agrees with corrected, not raw</text>
</svg>
^ The bar falls between the corrected score and the raw score, so the two graders make opposite calls; ground truth sits on the corrected side.

## Build

Reproduce both scores and both decisions. Pure arithmetic, no dependencies — 0.70 and 0.60 must come out exactly.

Run `--responses` for the record, `--score` for the two graders, `--check` for the gate. The self-test does more than check the corrected score is lower — it checks the correction is *right*, by comparing it to the ground-truth known fraction the fixture carries.

```python filename=modules/teaching-and-portability/code/teach-inter-09/guessing.py:95-103 COMPLETE
    raw_overstates = raw > truth
    print("  raw accuracy overstates what the learner knows = %s (raw %.2f vs true %.2f)" % (raw_overstates, raw, truth))

    corrected_recovers = abs(cor - truth) < 1e-9
    print("  the correction recovers the true known fraction = %s (corrected %.2f, true %.2f)" % (corrected_recovers, cor, truth))

    raw_advances = raw >= thr
    corrected_holds = cor < thr
    decisions_disagree = raw_advances and corrected_holds
    print("  raw advances but corrected holds (opposite calls) = %s (bar %.2f)" % (decisions_disagree, thr))
```

The load-bearing predicate is `corrected_recovers`: `abs(cor - truth) < 1e-9` demands the corrected score equal the true known fraction to nine decimals, not merely come close. That is what elevates the module from "the correction is more cautious" to "the correction is accurate." If someone perturbs the lucky-guess count off the one-in-four rate, the correction will only approximate the truth and this line fails — the fixture is pinned to the exact case where the formula's assumption holds. Here is the full gate.

```text filename=modules/teaching-and-portability/code/teach-inter-09/guessing.py --check
SELF-TEST — raw accuracy overstates mastery and advances; correcting recovers the true known fraction
------------------------------------------------------------------------------------
  raw accuracy overstates what the learner knows = True (raw 0.70 vs true 0.60)
  the correction recovers the true known fraction = True (corrected 0.60, true 0.60)
  raw advances but corrected holds (opposite calls) = True (bar 0.65)
  the corrected decision matches ground truth = True (true mastery 0.60 < 0.65)
------------------------------------------------------------------------------------
SELF-TEST PASS  raw_overstates=True  corrected_recovers=True  decisions_disagree=True  corrected_is_right=True
```

Four True flags, and together they tell the whole story. Raw_overstates: the naive score is too high. Corrected_recovers: the fix lands on the truth exactly. Decisions_disagree: the two graders make opposite advancement calls. Corrected_is_right: the corrected call is the one ground truth agrees with. The last flag is the point — the correction is not just different from raw, it is correct where raw is wrong.

**The self-test pins the corrected score to the true known fraction, so the claim is not "safer" but "accurate" — the correction recovers exactly what the learner knew.**

## Definition of done

You are done when you reproduce 0.70 and 0.60 and can explain why the second number is the honest one.

Concretely: `--score` prints raw 0.70 → ADVANCE and corrected 0.60 → HOLD; `--check` prints PASS with four True flags. You can state the guessing floor for any g — 1/g — and why a knowledge measure must read pure guessing as zero. You can write `R - W/(g-1)` and explain the `W/(g-1)` term as the estimated lucky hits, and you can check the formula at both extremes: full knowledge is unchanged, full ignorance corrects to zero. And you can name where the raw-versus-corrected gap does the most damage: at the passing bar, where borderline learners live.

The habit to carry: before advancing anyone on a multiple-choice score, ask what the guessing floor is and whether their margin over the bar is bigger than the luck the format hands out for free. If it is not, correct the score before you trust it.

## Boss fight

The expensive version of this is a curriculum that advances learners on raw quiz scores and then wonders why they collapse two units later.

A learner squeaks over every bar on the strength of a few lucky guesses per quiz. Each quiz, their real knowledge is a little below where the system thinks it is, and the gap compounds: unit three assumes mastery of unit two that was never there, unit four assumes three, and by unit five the learner is lost in material that depends on foundations they were credited with but never had. The quizzes all said "ready." No single decision looked wrong. The failure was systematic — a grader that counted luck as knowledge, applied twenty times, until the debt came due. Correcting for guessing at every gate would have held the learner at unit two until the knowledge was real.

Your turn, two moves. First, change the format and watch the floor move. Set choices to 2 — a true/false quiz — and predict before you run: the guessing floor jumps to one-half, so the correction gets far more aggressive (`W/(g-1)` becomes just `W`), and a raw 0.70 corrects to something much lower. Re-derive what raw score a true/false quiz needs just to clear a corrected 0.65, and notice how brutal binary-choice formats are to guessers. Second, break the clean recovery on purpose: change one wrong guess (say q15) to a lucky guess, so now three of eight guesses landed instead of two — above the one-in-four rate. Predict: the raw score rises, but the correction now *under*-counts the luck (it only expected two lucky hits, not three), so the corrected score will sit slightly above the true 0.60, and `corrected_recovers` will fail. That failure is the formula being honest about its own assumption: the correction is exact only in expectation, and a learner who guesses luckier than average will still be overrated. Sit with that limit — the correction fixes the average case, not every case.

## External resources

The correction for guessing is standard psychometrics; any measurement text (Crocker and Algina, "Introduction to Classical and Modern Test Theory") derives `R - W/(g-1)` and discusses when formula scoring helps and when it just adds noise.

The Wikipedia article "Multiple choice" has a clear section on negative marking and correction for guessing, including the argument that it mainly matters when omitting is allowed and guessing is discouraged.

For the modern, model-based version of the same idea, look at Item Response Theory's three-parameter model, where the "guessing parameter" c is a per-item lower asymptote — the same guessing floor, estimated from data rather than assumed uniform at 1/g.
