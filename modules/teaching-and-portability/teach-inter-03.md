---
id: teach-inter-03
title: Your confidence is not your competence — study by recall, not by feeling
topic: teaching-and-portability
level: intermediate
status: ready
time: 8-10h
summary: Self-rated confidence before a boss fight runs above actual recall — mean confidence 0.59 against a real recall rate of 0.50, a systematic overconfidence gap — because fluency from re-reading feels like mastery. The gap is not uniform: inside the high-confidence group (confidence at least 0.70) the concepts felt 81% known but only 50% were recalled, so the confidence there was unearned. That non-uniformity is the trap, because a study plan that restudies what feels weakest picks sampling, retrieval, dedup, quantization and skips bpe-tokens and kv-cache — two overconfident-wrong concepts that do not feel weak but were failed — while a plan that restudies what an actual recall test failed covers every gap. The fix is to allocate study by a from-memory test, never by a judgment of learning.
eli5: Reading your notes over and over makes them feel familiar, and familiar feels like knowing — but when the test comes you find you cannot actually say the answer. The dangerous cards are the ones that feel easy and you still get wrong, because you would never choose to study them. The only honest way to find them is to close the book and try to recall, then study whatever you actually missed, not whatever felt shaky.
---

## Why this module

The hub's learning loop turns on an uncomfortable claim: what you feel about your knowledge is not evidence about your knowledge, and acting on the feeling wastes your study time on the wrong things. This module measures that claim. It takes the self-assessments you make before a boss fight — how well you think you know each concept — puts them next to what actually happened when you tried to recall, and shows two things: your confidence systematically overshoots your recall, and, worse, the overshoot concentrates exactly where it does the most damage.

The mechanism behind the overshoot is fluency. Re-reading a concept until it flows produces a feeling of ease that the mind reads as mastery, even though ease of recognition and ability to reproduce are different skills. Averaged over concepts, this makes mean confidence sit above the true recall rate — an overconfidence gap. A uniform gap would be a nuisance you could subtract off. But the gap is not uniform: the concepts that hurt are the ones you are confident about and still fail, the overconfident-wrong. They matter because they do not feel weak, so every intuitive study strategy — restudy what feels shaky — skips them, leaving your largest real gaps untouched while you polish things you already know. The only reliable signal for what to restudy is a from-memory recall test, which is exactly why the hub's boss fights are closed-book.

You need the recall-ledger idea from the earlier teaching modules and nothing more. Everything runs offline against a judgments fixture — eight concepts, each with a pre-test confidence and an actual recall result — stdlib Python 3, `$0.00`. The instinct to unlearn is that you know which topics you are weak on. You know which ones feel weak, and the overconfident-wrong concepts prove those are not the same set.

Here is the gap between feeling and fact:

```
# modules/teaching-and-portability/code/teach-inter-03/ — COMPLETE, run from that directory
$ python3 calib.py --gap

GAP — self-rated confidence vs what was actually recalled
------------------------------------------------------------------
  attention        confidence=0.90  recalled=1  ok
  bpe-tokens       confidence=0.85  recalled=0  <-- miscalibrated
  kv-cache         confidence=0.80  recalled=0  <-- miscalibrated
  attention-mask   confidence=0.70  recalled=1  ok
  quantization     confidence=0.60  recalled=1  ok
  dedup            confidence=0.40  recalled=0  ok
  retrieval        confidence=0.30  recalled=1  <-- miscalibrated
  sampling         confidence=0.20  recalled=0  ok
  mean confidence = 0.59   actual recall rate = 0.50   overconfidence gap = 0.09
```

run: 2026-08-26 · deterministic; confidence/recall pairs are a fixture · 8 concepts · `python3 calib.py --gap`

Mean confidence 0.59, actual recall 0.50 — a nine-point overconfidence gap. And two concepts, `bpe-tokens` and `kv-cache`, were rated above 0.8 and then failed. This module is why those two are the ones that matter.

## Concepts

Named here so you can find them again; each is built below.

- **Judgment of learning** — your pre-test confidence in a concept; a feeling, not a measurement.
- **Recall** — whether you actually reproduced the concept from memory; the ground truth.
- **Fluency illusion** — re-reading makes a concept feel known without making it recallable.
- **Overconfidence gap** — mean confidence minus actual recall rate; positive when you overshoot.
- **Overconfident-wrong** — high-confidence concepts you failed; the gaps that do not feel like gaps.
- **Study by recall** — allocating restudy from a recall test, not from what feels weak.

## Worked example

Source: the metacognition research on judgments of learning and the testing effect (Bjork, Roediger, Karpicke), reduced to a calibration comparison; the confidence/recall pairs here stand in for your own boss-fight self-ratings so the overconfidence gap and study coverage are exact and checkable.

Script and fixture: `modules/teaching-and-portability/code/teach-inter-03/` — `calib.py`, and `judgments.json`, eight concepts with a pre-test confidence and a recall result, and a study budget. Every command runs from there.

### The overconfidence gap

Two averages tell the top-line story: how confident you felt, and how much you actually recalled.

```
# calib.py:40-51 — COMPLETE (mean confidence, recall rate, and the gap between them)
def mean_confidence(concepts):
    return sum(c["confidence"] for c in concepts) / len(concepts)


def recall_rate(concepts):
    return sum(c["recalled"] for c in concepts) / len(concepts)


def overconfidence_gap(concepts):
    """How far mean confidence sits above the true recall rate."""
    return mean_confidence(concepts) - recall_rate(concepts)
```

<svg viewBox="0 0 700 150" role="img" aria-label="Two horizontal bars. Mean confidence reaches 0.59; actual recall rate reaches 0.50. The small gap between their ends, 0.09, is shaded and labelled overconfidence gap.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="18" fill="var(--muted)">what you felt vs what you recalled</text>
    <text x="20" y="52" fill="var(--ink)">confidence</text><rect x="150" y="40" width="354" height="16" fill="var(--s2)"></rect><text x="512" y="53" fill="var(--s2)" font-size="9">0.59</text>
    <text x="20" y="90" fill="var(--ink)">actual recall</text><rect x="150" y="78" width="300" height="16" fill="var(--s1)"></rect><text x="458" y="91" fill="var(--s1)" font-size="9">0.50</text>
    <rect x="450" y="40" width="54" height="54" fill="none" stroke="var(--muted)" stroke-dasharray="3 2"></rect>
    <text x="150" y="122" fill="var(--muted)" font-size="8">the dashed box is the overconfidence gap, 0.09 — small on average, and that is the trap</text>
  </g>
</svg>
^ The average gap is only nine points, which is exactly why it feels safe to ignore. The next two views show that the gap is not spread evenly — it is piled onto the concepts you trust most.

Mean confidence is 0.59, recall rate 0.50, gap 0.09 — you predicted you would recall 59% of the material and recalled half. Nine points does not sound alarming, and if the error were spread evenly across concepts it would not be: you could mentally discount every confidence by nine points and be roughly right. The danger is entirely in how that gap is distributed, which the average hides. An average overconfidence is survivable; a concentrated one is not.

### Where the gap lives: the confident group

Split out the concepts you were most sure of and check whether the confidence was earned.

```
# calib.py:53-54 — COMPLETE (the concepts you felt you knew)
def high_confidence(concepts, threshold=0.7):
    return [c for c in concepts if c["confidence"] >= threshold]
```

Inside the high-confidence group the story is far worse than the nine-point average:

```
# $ python3 calib.py --calib
#   attention        confidence=0.90  recalled=1
#   bpe-tokens       confidence=0.85  recalled=0
#   kv-cache         confidence=0.80  recalled=0
#   attention-mask   confidence=0.70  recalled=1
#   4 concepts felt known; only 2 were recalled -> recall rate 50% in the group
#   mean confidence there was 81% -- the confidence was not earned.
```

run: 2026-08-26 · deterministic · `python3 calib.py --calib`

Four concepts you rated 0.70 or higher — an average felt-confidence of 81% — and you recalled two of them. A 50% recall rate in the group you were surest about is a 31-point gap, more than triple the overall figure. The overconfidence is not smeared evenly; it is piled onto the concepts you trust most, which is the worst possible place for it, because trust is what decides where you do not spend study time.

<svg viewBox="0 0 700 200" role="img" aria-label="A scatter of eight concepts, confidence on the x-axis, recall outcome as filled (recalled) or hollow (failed) points. A diagonal calibration line runs from bottom-left to top-right. Two high-confidence points, bpe-tokens at 0.85 and kv-cache at 0.80, are hollow (failed) despite sitting far right, marked as the overconfident-wrong danger zone.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">confidence (x) vs recalled (filled) or failed (hollow)</text>
    <line x1="60" y1="160" x2="650" y2="160" stroke="var(--grid)"></line>
    <line x1="60" y1="30" x2="60" y2="160" stroke="var(--grid)"></line>
    <text x="350" y="178" fill="var(--muted)">confidence -></text>
    <text x="30" y="50" fill="var(--muted)">recalled</text><text x="30" y="155" fill="var(--muted)">failed</text>
    <g fill="var(--s1)"><circle cx="590" cy="50" r="5"></circle><circle cx="470" cy="50" r="5"></circle><circle cx="410" cy="50" r="5"></circle><circle cx="240" cy="50" r="5"></circle></g>
    <g fill="none" stroke="var(--s2)" stroke-width="1.5"><circle cx="560" cy="150" r="5"></circle><circle cx="530" cy="150" r="5"></circle><circle cx="300" cy="150" r="5"></circle><circle cx="180" cy="150" r="5"></circle></g>
    <rect x="500" y="130" width="110" height="42" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"></rect>
    <text x="555" y="192" text-anchor="middle" fill="var(--s2)">overconfident-wrong</text>
    <text x="520" y="145" fill="var(--s2)" font-size="7">bpe .85</text><text x="490" y="128" fill="var(--s2)" font-size="7">kv .80</text>
  </g>
</svg>
^ The two hollow points on the right — high confidence, failed — are the overconfident-wrong concepts. They sit far from where a calibrated learner's failures would be (bottom-left, low confidence), and they are the ones a feeling-based study plan will never pick.

### The consequence: studying by feeling skips your real gaps

You have time to restudy some concepts, not all. The intuitive plan restudies what feels weakest; the honest plan restudies what a recall test actually failed.

```
# calib.py:63-72 — COMPLETE (two study plans: by confidence, by actual recall)
def study_by_confidence(concepts, budget):
    """Restudy what FEELS weakest: the lowest-confidence concepts (the naive plan)."""
    ranked = sorted(concepts, key=lambda c: (c["confidence"], c["name"]))
    return ranked[:budget]


def study_by_recall(concepts, budget):
    """Restudy what you ACTUALLY failed: blanked concepts first (the honest plan)."""
    ranked = sorted(concepts, key=lambda c: (c["recalled"], c["name"]))
    return ranked[:budget]
```

With a budget of four, the two plans diverge exactly where it counts:

```
# $ python3 calib.py --study
#   confidence-based restudies: ['sampling', 'retrieval', 'dedup', 'quantization']
#     failed concepts it SKIPS:  ['bpe-tokens', 'kv-cache']
#   recall-based restudies:     ['bpe-tokens', 'dedup', 'kv-cache', 'sampling']
#     failed concepts it SKIPS:  []
```

run: 2026-08-26 · deterministic · `python3 calib.py --study`

<svg viewBox="0 0 700 175" role="img" aria-label="Four failed concepts as a row: bpe-tokens, kv-cache, dedup, sampling. The confidence-based plan covers dedup and sampling but leaves bpe-tokens and kv-cache uncovered. The recall-based plan covers all four.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the four concepts you actually failed — does each study plan cover it?</text>
    <g fill="var(--ink)" text-anchor="middle" font-size="8"><text x="130" y="44">bpe-tokens</text><text x="270" y="44">kv-cache</text><text x="410" y="44">dedup</text><text x="540" y="44">sampling</text></g>
    <text x="20" y="78" fill="var(--ink)">by feeling</text>
    <g><rect x="90" y="64" width="80" height="20" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"></rect><text x="130" y="78" text-anchor="middle" fill="var(--s2)" font-size="8">SKIPPED</text></g>
    <g><rect x="230" y="64" width="80" height="20" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"></rect><text x="270" y="78" text-anchor="middle" fill="var(--s2)" font-size="8">SKIPPED</text></g>
    <g fill="var(--s1)"><rect x="372" y="64" width="76" height="20"></rect><rect x="502" y="64" width="76" height="20"></rect></g>
    <g fill="var(--panel)" text-anchor="middle" font-size="8"><text x="410" y="78">studied</text><text x="540" y="78">studied</text></g>
    <text x="20" y="128" fill="var(--ink)">by recall</text>
    <g fill="var(--s1)"><rect x="90" y="114" width="80" height="20"></rect><rect x="230" y="114" width="80" height="20"></rect><rect x="372" y="114" width="76" height="20"></rect><rect x="502" y="114" width="76" height="20"></rect></g>
    <g fill="var(--panel)" text-anchor="middle" font-size="8"><text x="130" y="128">studied</text><text x="270" y="128">studied</text><text x="410" y="128">studied</text><text x="540" y="128">studied</text></g>
    <text x="90" y="160" fill="var(--muted)" font-size="8">same budget of 4; feeling leaves your two overconfident-wrong gaps unstudied</text>
  </g>
</svg>
^ Both plans spend four slots and both catch the calibrated failures (`dedup`, `sampling`). Only the recall plan catches `bpe-tokens` and `kv-cache` — the failures that felt like successes.

The confidence-based plan restudies four concepts and skips two you actually failed — `bpe-tokens` and `kv-cache`, the overconfident-wrong pair — because they felt known, so they never made the "weakest" list. It even spends a slot on `quantization`, which you recalled correctly, purely because you felt unsure about it. The recall-based plan skips nothing you failed. Same budget, same concepts, and the only difference is whether you allocated study by a feeling or by a test — and the feeling routed your time away from your two biggest gaps.

**Confidence overshoots recall, and the overshoot concentrates on the concepts you trust most, so a study plan driven by what feels weak skips your overconfident-wrong gaps entirely — allocate restudy from a from-memory recall test, never from a judgment of learning.**

### The self-test

The `--check` mode asserts the whole chain: confidence exceeds recall, the confident group is miscalibrated, and studying by feeling skips real failures while studying by recall covers them.

```
# $ python3 calib.py --check
#   mean confidence exceeds actual recall = True (gap 0.09)
#   the high-confidence group under-recalls its confidence = True (recall 0.50 < conf 0.81)
#   confidence-based study skips real failures = True (['bpe-tokens', 'kv-cache'])
#   recall-based study covers every failure = True (skips [])
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 calib.py --check`

The `feeling_skips` line is the lesson as a guardrail: it requires the confidence-based plan to actually miss at least one failed concept, so the test proves the intuitive strategy is unsafe rather than merely asserting the honest one works. The `recall_covers` line is the correctness anchor — the recall-based plan, given a budget at least as large as the number of failures, must leave no failure unstudied, and if a refactor broke the ranking that assertion would fail first.

### The running tally

| study plan | restudies | failed concepts skipped | covers your gaps |
|---|---|---|---|
| by confidence (feeling) | sampling, retrieval, dedup, quantization | bpe-tokens, kv-cache | no |
| by recall (test) | bpe-tokens, dedup, kv-cache, sampling | — | yes |

The two rows spend the identical budget and share two concepts (`dedup`, `sampling` — the calibrated failures, which both plans catch). They differ entirely on the miscalibrated concepts: the feeling plan wastes a slot on a concept you knew (`quantization`) and misses two you failed (`bpe-tokens`, `kv-cache`), while the test plan spends every slot on a real gap. The wasted slot and the missed gaps are the same error seen twice — trusting confidence — and only a recall test separates the concepts that feel known from the ones that are.

### What we did not settle

Calibration is richer than a single gap. A reliability diagram bins predictions by confidence and plots the actual accuracy per bin, turning "are you calibrated" into a curve rather than one number, and it is the same tool used to judge a model's confidence in the evals track — self-assessment and model confidence are the same calibration problem. Underconfidence is real too (here `retrieval`, rated 0.30 and recalled), and it wastes study the other way, on things you already know. The testing effect goes further than diagnosis: the act of retrieval itself strengthens memory, so a recall test is both the measurement and part of the treatment. And confidence can be recalibrated with feedback over time. The rule here — measure recall, allocate study by it — is the floor beneath all of that.

## Build

The practice in one paragraph: never decide what to restudy from how well a concept feels known; take a from-memory recall test, record pass or fail per concept, and spend your study budget on the failures, hardest-felt or not; watch for the overconfident-wrong concepts, the ones you rated high and still missed, because they are invisible to intuition and are usually your largest real gaps; and track your overconfidence gap over time to recalibrate the feeling itself. The test is both the diagnosis and part of the cure.

We opened on the gap. The number that proves feeling is unsafe to study by is the skipped-failures list:

```
# modules/teaching-and-portability/code/teach-inter-03/ — COMPLETE, run from that directory
$ python3 calib.py --study
  confidence-based restudies: ['sampling', 'retrieval', 'dedup', 'quantization']
    failed concepts it SKIPS:  ['bpe-tokens', 'kv-cache']
```

Now run it on yourself. Before your next batch of boss fights, write down a confidence for each concept; after, record what you actually recalled. Compute your overconfidence gap and the recall rate inside your high-confidence group. Your number to beat is not the gap; it is **the list of overconfident-wrong concepts — rated high, failed — because those are the gaps your instincts hide**. Then build both study plans and confirm the feeling-based one skips some of them. Bring back your gap, your confident-group recall rate, and the skipped list. Good luck.

## Definition of done

- [ ] A pre-test confidence recorded for each concept, before the recall attempt
- [ ] The actual recall result recorded per concept
- [ ] The overconfidence gap (mean confidence minus recall rate) computed
- [ ] The recall rate inside the high-confidence group measured
- [ ] The overconfident-wrong concepts (high confidence, failed) identified
- [ ] A confidence-based and a recall-based study plan compared for failure coverage
- [ ] `python3 calib.py --check` printing SELF-TEST PASS: overconfident, hi-miscalibrated, feeling-skips, recall-covers
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. What is the overconfidence gap, and why is a small average gap not reassuring?
2. Why does re-reading a concept raise confidence more than it raises recall?
3. What are the overconfident-wrong concepts, and why does a study plan based on what feels weak systematically skip them?
4. Why is a from-memory recall test the only reliable input to a study plan, and what second benefit does the test itself provide?
5. You calibrated your own judgments. What was your overconfidence gap, your recall rate in the high-confidence group, and which concepts were overconfident-wrong?

## External resources

- Roediger & Karpicke, *Test-Enhanced Learning* (2006) — my summary: the experiments showing retrieval practice beats re-reading for retention, and that judgments of learning favour the weaker strategy; read it for the evidence that the feeling this module distrusts is systematically wrong.
- Bjork, *Desirable Difficulties* (learning and memory writing) — my summary: why conditions that feel harder during study produce better retention, and why fluency misleads; read it for the theory behind the fluency illusion measured here.
- This hub, *teach-inter-02* — modules/teaching-and-portability/teach-inter-02.md — my summary: the spaced-repetition scheduler that reads the same recall ledger; read it for what to do with the failures this module tells you to find — how soon to resurface each one.
