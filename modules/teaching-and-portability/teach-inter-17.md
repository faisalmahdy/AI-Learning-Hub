---
id: teach-inter-17
title: Pretest before you teach — or you skip the failed attempt that makes the studying stick
topic: teaching-and-portability
level: intermediate
status: ready
time: 20 min
summary: The intuitive order is study first, then test. But attempting a test before studying — and getting most of it wrong, because you have not learned the material yet — improves how much you retain from the studying that follows. The failed retrieval attempt activates related knowledge, exposes the exact gap, and generates a question the study answers, so the material encodes more deeply than a plain read. This is the pretesting effect, robust and replicated. The catch is that the pretest itself looks like a disaster — the learner answers almost nothing — so judging it by its in-the-moment score says "this does not work," while the delayed test says the opposite. On a stylized model, study-only reaches 0.55 on the delayed test, pretesting every item reaches 0.75, and half-pretested reaches 0.65 exactly midway — yet the pretest itself scores 0.05.
eli5: Guessing at a quiz before you have learned anything feels pointless — you get almost everything wrong. But the guessing makes your brain hungry for the answers, so when you then study, the right answers stick better than if you had just read them. The guessing looks like failure in the moment and is actually the part that makes the learning work.
---

## Why this module

The version of a lesson that scores best while you are learning is often not the version you remember best later — and pretesting is the sharpest case of that gap.

Attempt a test on material you have not studied and you will fail most of it; that feels like the wrong way round, and the pretest score confirms it — near zero. But the failed attempt is doing hidden work. Trying to retrieve an answer you do not have activates whatever related knowledge you do have, makes the specific gap vivid, and turns the upcoming study from passive reading into answering a question you now care about. When the study follows, it encodes more deeply. On the delayed test — the one that matters — the learner who pretested and failed beats the learner who only studied.

**A pretest scores like failure in the moment and produces the deepest encoding for later; the in-the-moment score points away from the method that wins.**

This is the same reversal the interleaving schedule shows: the metric available during learning misranks the methods. This module builds a stylized model of the replicated pretesting effect and shows the pretest's in-the-moment accuracy reversing against the delayed retention it produces.

## Concepts

The **delayed test** is the outcome that matters — accuracy on the material after a delay, uncued. Studying alone reaches a baseline, `study_gain`.

A **pretest** is an attempt to answer before studying. Because the learner has not studied, the pretest's **in-the-moment accuracy** is very low. That failure is not the point; the point is what it does to the study that follows.

The mechanism is that pretesting adds a **boost** to delayed retention, and the boost scales with how much you pretested: pretest every item and you get the full boost, pretest half and you get half. The boost is the failed-retrieval effect made countable — each pretested item is one attempt that primed its later encoding.

The trap is judging the pretest by its own score. That score is a proxy for learning, and it points the wrong way: 0.05 looks like "this is not working," so a teacher optimizing for in-the-moment performance drops the pretest — and loses the delayed-retention boost. The metric that matters is the delayed test, and it ranks pretesting first.

**The boost scales with how much you pretested, so the pretest's failure is not wasted effort — it is exactly the effort that raises the delayed score.**

The two metrics disagree because they measure different moments: the pretest score is taken before learning, the delayed test after — and only the second is what the lesson is for.

<svg role="img" aria-label="A timeline: pretest scores low before study, then study, then a delayed test that scores high for the pretested learner" viewBox="0 0 300 100" width="300" height="100">
  <line x1="20" y1="55" x2="285" y2="55" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="55" cy="55" r="4" fill="var(--s1)"/>
  <text x="30" y="40" fill="var(--s1)" font-size="8">pretest 0.05</text>
  <text x="35" y="75" fill="var(--muted)" font-size="8">(looks bad)</text>
  <circle cx="150" cy="55" r="4" fill="var(--muted)"/>
  <text x="132" y="40" fill="var(--muted)" font-size="8">study</text>
  <circle cx="255" cy="55" r="4" fill="var(--s2)"/>
  <text x="220" y="40" fill="var(--s2)" font-size="8">delayed 0.75</text>
  <text x="222" y="75" fill="var(--muted)" font-size="8">(what counts)</text>
</svg>
^ The pretest is measured before any learning and the delayed test after all of it; ranking the method by the early point inverts the ranking the late point gives.

Pretesting is distinct from retrieval practice, which tests after learning to strengthen an existing memory. Pretesting tests before learning, when there is no memory yet — its value is in shaping the encoding to come, not in exercising a trace that already exists.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/teach-inter-17/pretest.py

The fixture is three conditions over ten items plus the model constants. The conditions differ only in how many items are pretested first.

```json filename=modules/teaching-and-portability/code/teach-inter-17/pretest.json:14-21 COMPLETE
  "n_items": 10,
  "model": {"study_gain": 0.55, "max_pretest_boost": 0.20, "pretest_immediate_accuracy": 0.05},
  "conditions": [
    {"name": "study_only",   "pretested": 0},
    {"name": "pretest_half", "pretested": 5},
    {"name": "pretest_all",  "pretested": 10}
  ]
}
```

The two outcomes are two functions. Delayed accuracy is the study baseline plus a boost scaled by the pretested fraction; the pretest's own accuracy is the low in-the-moment number, or nothing when there was no pretest.

```python filename=modules/teaching-and-portability/code/teach-inter-17/pretest.py:41-53 COMPLETE
def pretest_fraction(cond, n):
    """How much of the material was attempted as a pretest before studying."""
    return cond["pretested"] / n


def delayed_accuracy(cond, n, m):
    """Delayed-test accuracy: studying gets you study_gain; pretesting adds a boost scaled by how much you pretested."""
    return m["study_gain"] + m["max_pretest_boost"] * pretest_fraction(cond, n)


def immediate_pretest_accuracy(cond, m):
    """How the pretest itself scored -- near zero, because the learner has not studied yet."""
    return m["pretest_immediate_accuracy"] if cond["pretested"] > 0 else None
```

Run `--conditions` — the in-the-moment view, the one a teacher watching the room would see.

```text filename=--conditions
CONDITIONS — how much each learner pretested, and how the pretest itself scored (10 items)
------------------------------------------------------------------
  study_only    pretested  0/10   in-the-moment pretest accuracy   —  (no pretest)
  pretest_half  pretested  5/10   in-the-moment pretest accuracy 0.05
  pretest_all   pretested 10/10   in-the-moment pretest accuracy 0.05
------------------------------------------------------------------
  the pretest is answered at 0.05 -- it looks like failure in the moment.
```

From inside the lesson, pretesting looks like a waste: the learners answer 5% of the pretest, a wall of red. Optimizing for what you can see right now, you cut it.

<svg role="img" aria-label="The pretest in-the-moment accuracy is 0.05, a nearly empty bar, looking like failure" viewBox="0 0 300 90" width="300" height="90">
  <text x="10" y="20" fill="var(--muted)" font-size="9">pretest, in the moment</text>
  <rect x="20" y="30" width="240" height="20" fill="none" stroke="var(--line)" stroke-width="1"/>
  <rect x="20" y="30" width="12" height="20" fill="var(--s1)"/>
  <text x="40" y="45" fill="var(--muted)" font-size="9">0.05 correct</text>
  <text x="20" y="72" fill="var(--muted)" font-size="8">judged here, pretesting looks like pure failure — so it gets cut</text>
</svg>
^ The signal available during learning: the pretest is answered at 0.05, an almost empty bar that reads as "this does not work."

## Build

The retention view computes the delayed score for each condition and reports the boost over the study-only baseline.

```python filename=modules/teaching-and-portability/code/teach-inter-17/pretest.py:72-82 COMPLETE
    print("RETENTION — delayed-test accuracy per condition")
    print("-" * 66)
    base = None
    for c in data["conditions"]:
        d = delayed_accuracy(c, n, m)
        if c["pretested"] == 0:
            base = d
        boost = "" if base is None else "   (+%.2f over study-only)" % (d - base)
        print("  %-13s delayed test %.2f%s" % (c["name"], d, boost if c["pretested"] > 0 else ""))
    print("-" * 66)
    print("  the boost scales with how many items were pretested: half pretested, half the boost.")
```

Now run `--retention` — the delayed test, weeks later, the outcome the lesson was for.

```text filename=--retention
RETENTION — delayed-test accuracy per condition
------------------------------------------------------------------
  study_only    delayed test 0.55
  pretest_half  delayed test 0.65   (+0.10 over study-only)
  pretest_all   delayed test 0.75   (+0.20 over study-only)
------------------------------------------------------------------
  the boost scales with how many items were pretested: half pretested, half the boost.
```

The order reverses. Study-only, which looked fine, lands at 0.55. Pretest-all, which looked like failure, lands at 0.75 — a full 0.20 higher. And pretest-half sits exactly midway at 0.65, because the boost scales with the fraction pretested: half the failed attempts, half the gain. The 0.05 pretest score was never a measure of learning; it was the cost of the mechanism that produced the 0.20 boost.

<svg role="img" aria-label="Delayed-test accuracy rises with pretesting: study_only 0.55, pretest_half 0.65, pretest_all 0.75" viewBox="0 0 300 130" width="300" height="130">
  <line x1="80" y1="15" x2="80" y2="100" stroke="var(--grid)" stroke-width="1"/>
  <line x1="80" y1="100" x2="285" y2="100" stroke="var(--grid)" stroke-width="1"/>
  <rect x="90" y="45" width="110" height="14" fill="var(--s2)"/>
  <text x="10" y="56" fill="var(--muted)" font-size="8">study_only</text>
  <text x="205" y="56" fill="var(--muted)" font-size="8">0.55</text>
  <rect x="90" y="65" width="130" height="14" fill="var(--s1)"/>
  <text x="10" y="76" fill="var(--muted)" font-size="8">pretest_half</text>
  <text x="225" y="76" fill="var(--muted)" font-size="8">0.65</text>
  <rect x="90" y="85" width="150" height="14" fill="var(--s1)"/>
  <text x="10" y="96" fill="var(--muted)" font-size="8">pretest_all</text>
  <text x="245" y="96" fill="var(--muted)" font-size="8">0.75</text>
  <text x="90" y="30" fill="var(--muted)" font-size="8">the boost is linear in the fraction pretested</text>
</svg>
^ The outcome view: pretesting lifts delayed retention in proportion to how much was pretested, exactly reversing the in-the-moment ranking.

## Definition of done

The self-test pins the reversal: study-only is the baseline, pretesting all wins the delayed test, half gives exactly half the boost, the pretest looks like failure in the moment, and the in-the-moment signal reverses against the outcome.

```python filename=modules/teaching-and-portability/code/teach-inter-17/pretest.py:95-108 COMPLETE
    study_only_baseline = abs(study - m["study_gain"]) < 1e-9
    print("  study-only equals the study gain, no boost = %s (%.2f)" % (study_only_baseline, study))

    pretest_wins_delayed = allp > study
    print("  pretesting every item wins the delayed test = %s (%.2f > %.2f)" % (pretest_wins_delayed, allp, study))

    boost_scales_linearly = abs(half - (study + allp) / 2) < 1e-9
    print("  pretesting half gives half the boost (midway) = %s (%.2f vs %.2f)" % (boost_scales_linearly, half, (study + allp) / 2))

    pretest_looks_like_failure = imm < study
    print("  in the moment the pretest looks like failure = %s (pretest %.2f < study-only delayed %.2f)" % (pretest_looks_like_failure, imm, study))

    proxy_reversal = imm < study and allp > study
    print("  the in-the-moment signal reverses against the outcome = %s" % proxy_reversal)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the pretest looks like failure in the moment but wins the delayed test -- a reversal
--------------------------------------------------------------------------------------------------------
  study-only equals the study gain, no boost = True (0.55)
  pretesting every item wins the delayed test = True (0.75 > 0.55)
  pretesting half gives half the boost (midway) = True (0.65 vs 0.65)
  in the moment the pretest looks like failure = True (pretest 0.05 < study-only delayed 0.55)
  the in-the-moment signal reverses against the outcome = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  study_only_baseline=True  pretest_wins_delayed=True  boost_scales_linearly=True  pretest_looks_like_failure=True  proxy_reversal=True
```

**Done means the reversal is provable: the pretest scores 0.05 in the moment yet lifts delayed retention to 0.75 against study-only's 0.55, and the half-condition's exact midpoint shows the boost is the pretesting, not noise.**

## Boss fight

The pretest here scores 0.05 and still helps. Predict whether giving the learner the correct answers immediately after the pretest — so the failure is corrected right away — is necessary for the effect. It is tempting to think the failure alone, uncorrected, would just teach the wrong answer.

Feedback matters, but the striking finding is that the boost survives even when the pretest is unfeedback-ed for a while, because the effect is about the encoding the failed attempt sets up, not about the pretest answer being remembered. The wrong guesses are not learned as facts; they are the search that makes the subsequent study land. That said, the practical design pairs the pretest with study that supplies the answers — which this model assumes — so the learner never leaves with the error uncorrected. The lesson is that the failure is a feature, not that feedback is optional.

The mirror-image mistake is concluding "so make everything a pretest" and skipping the study. The boost is added to `study_gain`, not a replacement for it — a pretest with no study that follows is just failure. Pretesting works because it changes how the study is encoded; remove the study and there is nothing to encode.

```python filename=modules/teaching-and-portability/code/teach-inter-17/pretest.py:46-48 COMPLETE
def delayed_accuracy(cond, n, m):
    """Delayed-test accuracy: studying gets you study_gain; pretesting adds a boost scaled by how much you pretested."""
    return m["study_gain"] + m["max_pretest_boost"] * pretest_fraction(cond, n)
```

**Judge a study method by delayed retention, not by how it scores while learning: a pretest that looks like total failure in the moment is the setup that makes the studying stick.**

## External resources

Richland, Kornell, and Kao, "The pretesting effect" (2009) — the controlled demonstration that an unsuccessful pretest improves later retention over studying alone, the finding this model stylizes.

Bjork and Bjork on "desirable difficulties" — the framework explaining why conditions that depress performance during learning (pretesting, spacing, interleaving) improve durable retention.

Little and Bjork on pretesting with multiple-choice — evidence that even the wrong options in a failed pretest shape what the learner later encodes, directly relevant to the boss-fight question about feedback.
