---
id: teach-adv-01
title: The adaptive tutor — compose the frontier, calibration, and scaffolding into one decision
topic: teaching-and-portability
level: advanced
status: ready
time: 12-16h
summary: A good "what should this learner do next" decision has to satisfy three constraints at once — the concept must be unlocked (its prerequisites mastered), it must be one the learner actually failed on their last from-memory recall rather than one that merely feels weak, and it must be delivered at scaffolding faded to the learner's competence. Composing the teaching track's frontier, calibration, and expertise-reversal signals, the tutor recommends vectors at full scaffolding and calculus at none — both unlocked and failed, 2 of 2 good picks — while a naive tutor that sorts by self-rated confidence, ignores prerequisites, and gives everyone full scaffolding recommends a locked concept the learner bounces off and one they already recall, 0 of 2 good, and misses the overconfident-but-failed concept that is the real gap. Adaptive teaching is not any one signal; it is the conjunction, and dropping any of the three produces a confident, wrong recommendation.
eli5: Picking the next thing to teach is like picking the next rung on a ladder. It has to be a rung you can actually reach (you've mastered what's below it), a rung you haven't already climbed (you keep slipping on it, not just feel nervous about it), and you hand over exactly as much help as this climber still needs — a lot for a beginner, none for an expert. Get any of those wrong and you send someone at a rung they'll fall off, or one they're already standing on.
---

## Why this module

The teaching track built each signal an adaptive tutor needs, one module at a time: the prerequisite frontier decides what a learner can absorb, calibration decides what they should study (what they failed, not what feels weak), and the expertise-reversal effect decides how much scaffolding to give. This module composes all three into a single next-step decision and measures it against the naive tutor, because a recommendation is only good if it satisfies every constraint simultaneously — and a tutor that gets two of three right still confidently teaches the wrong thing.

The composition is a conjunction, and each clause rules out a distinct failure. A concept must be unlocked — its prerequisites mastered — or the learner bounces off material that assumes knowledge they lack, the wasted-effort failure from the frontier module. It must be one they actually failed on their last from-memory recall, not one they merely rated low confidence on, because confidence and competence diverge: the calibration module showed learners are overconfident on some failed concepts and underconfident on some passed ones, so studying by feeling both wastes time on the known and skips the overconfident gaps. And it must be delivered at scaffolding faded to competence — full worked examples for a novice, none for an expert — or the expertise-reversal effect turns a correct concept into a mistaught one. The naive tutor violates all three at once: it sorts by self-rated confidence, ignores prerequisites, and gives everyone full scaffolding, so it recommends locked concepts, wastes slots on already-mastered material, and mis-scaffolds even its accidental good picks.

You need the whole teaching track: `teach-inter-05` (the frontier), `teach-inter-03` (calibration), and `teach-inter-06` (faded scaffolding). Everything runs offline against a learner-state fixture — six concepts with mastery, prerequisites, last-recall result, confidence, and competence — stdlib Python 3, `$0.00`. The instinct to unlearn is that a tutor needs a good signal. It needs the conjunction of three signals, and any one of them alone, or even any two, produces a recommendation that looks reasonable and is wrong.

Here is the learner's state, with all three signals resolved per concept:

```
# modules/teaching-and-portability/code/teach-adv-01/ — COMPLETE, run from that directory
$ python3 tutor.py --state

STATE — each concept's signals (reversal competence 0.56)
------------------------------------------------------------------
  concept    mastered unlocked failed conf  comp  scaffold
  vectors    False    True     True   0.30  0.20  1
  attention  False    False    True   0.15  0.30  -
  calculus   False    True     True   0.85  0.70  0
  retrieval  False    True     False  0.25  0.50  1
```

run: 2026-08-26 · deterministic; learner state is a fixture · 6 concepts · `python3 tutor.py --state`

Four non-mastered concepts, each a different combination: vectors (unlocked, failed, novice), attention (locked, failed), calculus (unlocked, failed, but high-confidence and expert-level), retrieval (unlocked but already recalled). This module is which two a good tutor picks and why the naive one picks the other two.

## Concepts

Named here so you can find them again; each is built below.

- **Frontier (unlocked)** — prerequisites mastered and the concept not yet mastered; what the learner can absorb.
- **Calibration (failed)** — study what the last recall failed, not what confidence feels weak.
- **Faded scaffolding** — full support below the reversal competence, none above.
- **Good recommendation** — the conjunction: unlocked and failed, at the faded scaffold level.
- **The bounce** — recommending a locked concept the learner cannot yet absorb.
- **The waste** — recommending a concept the learner already recalls.

## Worked example

Source: the composition of the teaching track's own results into an adaptive-tutor decision — the kind of next-step logic an intelligent tutoring system runs; the learner state here stands in for a real recall ledger plus competence estimates so the recommendations are exact and checkable.

Script and fixture: `modules/teaching-and-portability/code/teach-adv-01/` — `tutor.py`, and `state.json`, one learner across six concepts. Every command runs from there.

### The three signals, each a function

The tutor reads three signals off each concept. Each is one small function, and each is the core idea of a prior module.

```
# tutor.py:45-59 — COMPLETE (the three signals: frontier, calibration, scaffolding)
def unlocked(concept_id, concepts):
    """Frontier: prerequisites all mastered, and not itself mastered."""
    s = concepts[concept_id]
    mastered = mastered_set(concepts)
    return (not s["mastered"]) and all(p in mastered for p in s["prereqs"])


def needs_study(concept_id, concepts):
    """Calibration: study what the last RECALL failed -- not what confidence feels weak."""
    return concepts[concept_id]["recalled"] == 0


def faded_scaffold(concept_id, concepts, reversal):
    """Expertise reversal: full scaffolding below the reversal competence, none above."""
    return 1.0 if concepts[concept_id]["competence"] < reversal else 0.0
```

`unlocked` is the frontier from `teach-inter-05` — prerequisites mastered, concept not. `needs_study` is the calibration lesson from `teach-inter-03` — it reads the recall result, never the confidence, because confidence lies. `faded_scaffold` is the expertise-reversal rule from `teach-inter-06` — full below the reversal competence, none above. Three independent signals, each already validated in its own module; the tutor's job is to combine them correctly.

The frontier signal needs the set of mastered concepts, which the other functions read too, so it is factored out once:

```
# tutor.py:41-42 — COMPLETE (the mastered set, read by the frontier signal)
def mastered_set(concepts):
    return {c for c, s in concepts.items() if s["mastered"]}
```

The point to hold onto is that these three signals answer three different questions — *can* the learner take this on, *do* they need it, and *how* should it be delivered — and the answers do not correlate. A concept can be reachable but already known (retrieval), needed but unreachable (attention), or needed and reachable but at a competence that inverts the right scaffolding (calculus). Because the questions are orthogonal, no single signal is a proxy for the others, and that is the whole reason the composition cannot collapse into one heuristic.

<svg viewBox="0 0 700 190" role="img" aria-label="Three orthogonal signals feed an AND gate. Frontier asks can-absorb (unlocked). Calibration asks needs-study (recall failed). Scaffolding asks how-delivered (faded to competence). The first two are ANDed into eligibility; the third sets the delivery level. A concept passes only if unlocked AND failed, then is delivered at its faded scaffold.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">three orthogonal questions → one recommendation</text>
    <rect x="20" y="34" width="150" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="95" y="50" text-anchor="middle" fill="var(--acc-ink)" font-size="8">FRONTIER</text><text x="95" y="62" text-anchor="middle" fill="var(--acc-ink)" font-size="8">can absorb? (unlocked)</text>
    <rect x="20" y="78" width="150" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="95" y="94" text-anchor="middle" fill="var(--acc-ink)" font-size="8">CALIBRATION</text><text x="95" y="106" text-anchor="middle" fill="var(--acc-ink)" font-size="8">needs it? (recall failed)</text>
    <rect x="20" y="122" width="150" height="34" fill="var(--panel)" stroke="var(--line)"></rect><text x="95" y="138" text-anchor="middle" fill="var(--ink)" font-size="8">SCAFFOLDING</text><text x="95" y="150" text-anchor="middle" fill="var(--ink)" font-size="8">how? (faded to comp.)</text>
    <line x1="170" y1="51" x2="300" y2="70" stroke="var(--acc-line)"></line>
    <line x1="170" y1="95" x2="300" y2="76" stroke="var(--acc-line)"></line>
    <rect x="300" y="56" width="90" height="34" fill="var(--s1)"></rect><text x="345" y="77" text-anchor="middle" fill="var(--panel)" font-size="9">AND</text>
    <line x1="390" y1="73" x2="470" y2="73" stroke="var(--ink)"></line>
    <rect x="470" y="56" width="120" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="530" y="72" text-anchor="middle" fill="var(--acc-ink)" font-size="8">ELIGIBLE</text><text x="530" y="84" text-anchor="middle" fill="var(--acc-ink)" font-size="8">unlocked & failed</text>
    <line x1="170" y1="139" x2="530" y2="139" stroke="var(--line)"></line><line x1="530" y1="139" x2="530" y2="90" stroke="var(--line)"></line>
    <text x="600" y="76" fill="var(--muted)" font-size="8">→ pick</text>
    <text x="360" y="176" fill="var(--muted)" font-size="8">eligibility is the AND of the first two; the third sets delivery, not eligibility</text>
  </g>
</svg>
^ The frontier and calibration signals are ANDed into eligibility — a concept is worth teaching only if it is both reachable and unrecalled — and the scaffolding signal sets how the eligible concept is delivered. Drop any input and the wrong concept, or the right concept wrongly delivered, gets through.

### A good recommendation is the conjunction

The composition is an AND, not a menu. A recommendation is good only if the concept is both unlocked and failed.

```
# tutor.py:64-66 — COMPLETE (a recommendation is good only if unlocked AND failed)
def is_good(concept_id, concepts):
    """A recommendation is good only if the concept is unlocked AND actually failed."""
    return unlocked(concept_id, concepts) and needs_study(concept_id, concepts)
```

This is the crux. Each clause rules out one failure mode: drop `unlocked` and you recommend a locked concept the learner bounces off; drop `needs_study` and you recommend something they already know. The scaffolding is a third dimension layered on top — a good concept at the wrong scaffold is still mistaught — but the eligibility itself is the conjunction of frontier and calibration. Look at the four candidates against it: vectors (unlocked ✓, failed ✓ → good), attention (locked ✗ → bounce), calculus (unlocked ✓, failed ✓ → good), retrieval (unlocked ✓, but recalled → waste). Only two survive, and they are not the two the naive tutor will pick.

<svg viewBox="0 0 700 220" role="img" aria-label="A 2x2 grid on axes unlocked (yes/no) and failed (yes/no). vectors and calculus are in the unlocked-and-failed cell (good). attention is in the locked-and-failed cell (bounce). retrieval is in the unlocked-and-recalled cell (waste). The mastered concepts sit outside. Only the unlocked-and-failed cell is a good recommendation.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">a good pick is the conjunction: unlocked AND failed</text>
    <text x="250" y="42" text-anchor="middle" fill="var(--ink)">failed (recall=0)</text>
    <text x="470" y="42" text-anchor="middle" fill="var(--ink)">recalled (recall=1)</text>
    <text x="70" y="90" fill="var(--ink)">unlocked</text>
    <rect x="160" y="56" width="200" height="60" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="260" y="82" text-anchor="middle" fill="var(--acc-ink)">vectors, calculus</text><text x="260" y="98" text-anchor="middle" fill="var(--acc-ink)" font-size="8">GOOD — teach these</text>
    <rect x="380" y="56" width="200" height="60" fill="var(--panel)" stroke="var(--s2)"></rect><text x="480" y="82" text-anchor="middle" fill="var(--s2)">retrieval</text><text x="480" y="98" text-anchor="middle" fill="var(--s2)" font-size="8">WASTE — already known</text>
    <text x="70" y="160" fill="var(--ink)">locked</text>
    <rect x="160" y="126" width="200" height="60" fill="var(--panel)" stroke="var(--s2)"></rect><text x="260" y="152" text-anchor="middle" fill="var(--s2)">attention</text><text x="260" y="168" text-anchor="middle" fill="var(--s2)" font-size="8">BOUNCE — prereqs unmet</text>
    <rect x="380" y="126" width="200" height="60" fill="var(--panel)" stroke="var(--line)"></rect><text x="480" y="156" text-anchor="middle" fill="var(--muted)" font-size="8">(nothing to teach)</text>
    <text x="160" y="208" fill="var(--muted)" font-size="8">only the top-left cell is a good recommendation — both clauses must hold</text>
  </g>
</svg>
^ The four candidates fall in three different cells; only the unlocked-and-failed cell is a good pick. Attention is failed but locked (a bounce), retrieval is unlocked but recalled (a waste), and only vectors and calculus satisfy both clauses.

### The composed tutor

The composed tutor selects the good concepts and attaches the faded scaffold to each.

```
# tutor.py:71-75 — COMPLETE (unlocked AND failed, each at faded scaffolding)
def recommend_composed(concepts, reversal, budget):
    """Unlocked AND failed, each at scaffolding faded to competence."""
    picks = [c for c in concepts if unlocked(c, concepts) and needs_study(c, concepts)]
    picks.sort()
    return [(c, faded_scaffold(c, concepts, reversal)) for c in picks[:budget]]
```

It picks vectors and calculus, and — the third signal — scaffolds each to its competence: vectors at competence 0.20 gets full scaffolding, calculus at competence 0.70 gets none. That last part matters as much as the selection: calculus is a failed concept the learner needs, but they are expert-level at it (they failed the recall for another reason, perhaps staleness), so full worked examples would trigger the expertise reversal and teach less. The composed tutor gives calculus a bare problem and vectors a full walkthrough — same recommendation list, different delivery, each matched to the learner.

The fixture makes each candidate's signals exact, so the picks and the mistakes are not accidents of tuning but hand-authored to be checkable:

```
# state.json — COMPLETE (the four non-mastered concepts; reversal 0.56, budget 2)
"vectors":   {"mastered": false, "prereqs": ["basics"],  "recalled": 0, "confidence": 0.30, "competence": 0.20},
"attention": {"mastered": false, "prereqs": ["vectors"], "recalled": 0, "confidence": 0.15, "competence": 0.30},
"calculus":  {"mastered": false, "prereqs": [],          "recalled": 0, "confidence": 0.85, "competence": 0.70},
"retrieval": {"mastered": false, "prereqs": ["basics"],  "recalled": 1, "confidence": 0.25, "competence": 0.50}
```

Read the competence column against the reversal threshold of 0.56 to see the scaffold decision: vectors (0.20) and attention (0.30) sit below it and get full support, calculus (0.70) and retrieval (0.50) sit above and below it respectively. The fade is a step at the reversal point — full to the left, none to the right — and only the eligible concepts ever reach it.

<svg viewBox="0 0 700 170" role="img" aria-label="A competence axis from 0 to 1 with a reversal threshold at 0.56. Scaffolding is a step: full to the left of the threshold, none to the right. vectors at 0.20 and attention at 0.30 are in the full-scaffold region. retrieval at 0.50 is just below the threshold; calculus at 0.70 is above it in the no-scaffold region. Only eligible concepts vectors and calculus are marked as delivered.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">scaffolding fades at the reversal competence (0.56)</text>
    <line x1="60" y1="120" x2="620" y2="120" stroke="var(--line)"></line>
    <text x="60" y="138" text-anchor="middle" fill="var(--muted)" font-size="8">comp 0.0</text>
    <text x="620" y="138" text-anchor="middle" fill="var(--muted)" font-size="8">1.0</text>
    <rect x="60" y="60" width="373" height="60" fill="var(--acc-soft)"></rect><text x="240" y="50" text-anchor="middle" fill="var(--acc-ink)" font-size="8">full scaffolding</text>
    <rect x="433" y="90" width="187" height="30" fill="var(--panel)" stroke="var(--line)"></rect><text x="526" y="50" text-anchor="middle" fill="var(--muted)" font-size="8">no scaffolding</text>
    <line x1="433" y1="40" x2="433" y2="120" stroke="var(--s2)"></line><text x="433" y="34" text-anchor="middle" fill="var(--s2)" font-size="8">reversal 0.56</text>
    <circle cx="172" cy="120" r="4" fill="var(--s1)"></circle><text x="172" y="152" text-anchor="middle" fill="var(--ink)" font-size="8">vectors ✓</text>
    <circle cx="228" cy="120" r="4" fill="var(--muted)"></circle><text x="228" y="152" text-anchor="middle" fill="var(--muted)" font-size="8">attention</text>
    <circle cx="340" cy="120" r="4" fill="var(--muted)"></circle><text x="340" y="152" text-anchor="middle" fill="var(--muted)" font-size="8">retrieval</text>
    <circle cx="452" cy="120" r="4" fill="var(--s1)"></circle><text x="452" y="152" text-anchor="middle" fill="var(--ink)" font-size="8">calculus ✓</text>
  </g>
</svg>
^ The scaffold is a step at the reversal competence: vectors (0.20) lands in the full-support region, calculus (0.70) in the no-support region. Only the eligible picks (marked ✓) are delivered; attention and retrieval are shown for position but never recommended.

### The naive tutor: three mistakes at once

The naive tutor sorts by confidence, ignores prerequisites, and fixes scaffolding at full.

```
# tutor.py:78-81 — COMPLETE (the bug: sort by confidence, ignore prereqs, full scaffold)
def recommend_naive(concepts, reversal, budget):
    """The bug: lowest self-rated confidence first, ignore prereqs, full scaffolding for all."""
    cand = sorted((c for c in concepts if not concepts[c]["mastered"]),
                  key=lambda c: (concepts[c]["confidence"], c))
    return [(c, 1.0) for c in cand[:budget]]
```

Sorting the non-mastered concepts by confidence puts attention (0.15) and retrieval (0.25) first — the two the learner feels least sure about. The diagnosis of why each naive pick is bad is itself the conjunction read backwards — a pick fails either the frontier clause or the calibration clause:

```
# tutor.py:110-113 — COMPLETE (diagnosing each naive pick: bounce, waste, or ok)
    print("  naive:    %s" % [c for c, _ in nai])
    for c, _ in nai:
        why = "LOCKED (bounce)" if not unlocked(c, cs) else ("already recalled (waste)" if not needs_study(c, cs) else "ok")
        print("     %-10s %s" % (c, why))
```

A pick is a bounce if it fails `unlocked`, a waste if it fails `needs_study`, and only "ok" if it passes both — the same two clauses `is_good` ANDs together, here separated so the failure mode is named. Run both tutors:

```
# $ python3 tutor.py --recommend
#   composed: [('calculus', 'none'), ('vectors', 'full')]
#      calculus   unlocked=True failed=True  -> good
#      vectors    unlocked=True failed=True  -> good
#   naive:    ['attention', 'retrieval']
#      attention  LOCKED (bounce)
#      retrieval  already recalled (waste)
```

run: 2026-08-26 · deterministic · `python3 tutor.py --recommend`

The naive tutor's two picks are both bad, for different reasons. Attention has the lowest confidence, so it is picked first — but its prerequisite (vectors) is unmastered, so it is locked, and the learner sent there will bounce off material they cannot follow. Retrieval has low confidence too, but the learner actually recalled it on their last attempt — they are underconfident, so studying it is wasted time on something already known. And the naive tutor misses both good concepts entirely: vectors (confidence 0.30, just outside the budget) and calculus (confidence 0.85, felt strong, so never considered) — calculus being the exact overconfident-but-failed gap the calibration module warned about. Three signals, three mistakes, zero good recommendations.

<svg viewBox="0 0 700 180" role="img" aria-label="Two tutors' picks scored. Composed: vectors (good) and calculus (good), 2 of 2. Naive: attention (bounce) and retrieval (waste), 0 of 2. Below, the two concepts naive missed: vectors and calculus, both good, one of them the overconfident-failed gap.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">good recommendations (unlocked AND failed) per tutor</text>
    <text x="20" y="48" fill="var(--ink)">composed</text>
    <rect x="140" y="36" width="130" height="18" fill="var(--s1)"></rect><text x="205" y="49" text-anchor="middle" fill="var(--panel)" font-size="8">vectors ✓</text>
    <rect x="278" y="36" width="130" height="18" fill="var(--s1)"></rect><text x="343" y="49" text-anchor="middle" fill="var(--panel)" font-size="8">calculus ✓</text>
    <text x="420" y="49" fill="var(--s1)" font-size="8">2 / 2 good</text>
    <text x="20" y="88" fill="var(--ink)">naive</text>
    <rect x="140" y="76" width="130" height="18" fill="var(--s2)"></rect><text x="205" y="89" text-anchor="middle" fill="var(--panel)" font-size="8">attention (bounce)</text>
    <rect x="278" y="76" width="130" height="18" fill="var(--s2)"></rect><text x="343" y="89" text-anchor="middle" fill="var(--panel)" font-size="8">retrieval (waste)</text>
    <text x="420" y="89" fill="var(--s2)" font-size="8">0 / 2 good</text>
    <text x="140" y="128" fill="var(--muted)" font-size="8">naive missed: vectors (just outside budget) and calculus (felt strong, so never considered)</text>
    <text x="140" y="146" fill="var(--s2)" font-size="8">calculus is the overconfident-but-failed gap — invisible to a confidence-sorted tutor</text>
  </g>
</svg>
^ The composed tutor's two picks are both good; the naive tutor's are a bounce and a waste, and it never even considers the overconfident-failed calculus. Sorting by feeling routes the learner exactly wrong.

**A good next-step recommendation is the conjunction of three signals — unlocked (frontier), failed on recall not weak on confidence (calibration), and scaffolded to competence (expertise reversal) — so a tutor that drops any one of them recommends a locked concept, a known concept, or a mis-scaffolded one; adaptive teaching is the composition, not any single signal.**

### The self-test

The `--check` mode asserts the composition: every composed pick is unlocked and failed, the scaffolding is faded, and the naive tutor commits both the bounce and the waste while making fewer good picks.

```
# $ python3 tutor.py --check
#   every composed recommendation is unlocked AND failed = True (['calculus', 'vectors'])
#   scaffolding is faded to competence = True (vectors full, calculus none)
#   naive recommends a LOCKED concept (a bounce) = True (['attention'])
#   naive recommends an already-recalled concept (a waste) = True (['retrieval'])
#   composed makes more good recommendations = True (2 vs 0)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 tutor.py --check`

The single line that welds the whole test together is the final AND — the module only passes if all five properties hold at once, which is the same conjunction discipline the tutor itself enforces:

```
# tutor.py:140-145 — COMPLETE (the payoff assertion and the combined gate)
    comp_n = sum(is_good(c, cs) for c, _ in comp)
    naive_n = sum(is_good(c, cs) for c, _ in nai)
    composed_wins = comp_n > naive_n
    print("  composed makes more good recommendations = %s (%d vs %d)" % (composed_wins, comp_n, naive_n))

    ok = comp_good and scaffold_faded and naive_locked and naive_waste and composed_wins
```

The `comp_good` line is the composition's correctness anchor: every recommendation must satisfy the full conjunction, and if the tutor dropped either clause a bad pick would slip through. The `naive_locked` and `naive_waste` lines prove the two failure modes are real and distinct — a confidence-sorted tutor commits both on this learner — and `composed_wins` confirms the payoff: the composition makes strictly more good recommendations than any single-signal shortcut. The `scaffold_faded` line guards the third dimension, so even the right concepts are delivered right.

### The running tally

| concept | unlocked | failed | naive picks it? | composed picks it? | verdict |
|---|---|---|---|---|---|
| vectors | yes | yes | no (outside budget) | yes (full scaffold) | good — missed by naive |
| calculus | yes | yes | no (felt strong) | yes (no scaffold) | good — the overconfident gap |
| attention | no | yes | yes (lowest conf) | no | naive bounce |
| retrieval | yes | no | yes (low conf) | no | naive waste |

Read the naive column against the verdict column: it picks exactly the two bad concepts and misses exactly the two good ones, a perfect inversion, because confidence is uncorrelated with the two things that actually matter — readiness and true recall. The composed tutor's column is the mirror image. This is why adaptive teaching cannot be a single heuristic: readiness, need, and delivery are three orthogonal questions, and a good recommendation is the point where all three answers align. Optimize any one alone and you land in the wrong cell.

### What we did not settle

This composes three signals into a per-concept decision; a full tutoring system does more. The mastery and competence estimates feeding the signals are themselves derived from performance and carry uncertainty, so the tutor should propagate that — the readiness-honesty module's discipline applies to its own inputs. Ordering within the good set matters when the budget is tight: shortest path to a goal concept, or spacing across topics for retention (the spaced-repetition module), should break ties. The scaffolding fade should be gradual (faded worked examples), not the bang-bang here. And the whole loop is closed over time — each recommendation produces a new recall result that updates the state for the next decision, which is the actual adaptive loop this single step lives inside. The invariant is the conjunction: ready, needed, and well-delivered, together.

## Build

The build in one paragraph: compute three signals per concept — unlocked (prerequisites mastered), needs-study (last recall failed, read from the ledger not from confidence), and faded scaffolding (by competence past the reversal point); recommend only concepts that satisfy the frontier-and-calibration conjunction, each at its faded scaffold level; and verify every recommendation is both reachable and needed, never trusting a single signal like confidence that is uncorrelated with both. Derive the input estimates honestly, order the good set by goal and spacing, and close the loop by feeding each new recall result back into the state.

We opened on the state. The number that proves the composition works is the good-recommendation count:

```
# modules/teaching-and-portability/code/teach-adv-01/ — COMPLETE, run from that directory
$ python3 tutor.py --check
  composed makes more good recommendations = True (2 vs 0)
```

Now build your own. Take a real learner state — a recall ledger, a prerequisite graph, competence estimates — and compose the three signals into a next-step recommendation. Your number to beat is not the number of recommendations; it is **how many satisfy the full conjunction (unlocked AND failed, correctly scaffolded), against a confidence-sorted baseline** — the composed tutor should dominate it. Then check the baseline for bounces and wastes. Bring back both tutors' good-recommendation counts. Good luck.

## Definition of done

- [ ] Three per-concept signals: unlocked (frontier), needs-study (recall-based), faded scaffolding
- [ ] A composed recommender selecting concepts that are unlocked AND failed, at faded scaffolding
- [ ] A naive confidence-sorted recommender for contrast
- [ ] Confirmation every composed pick is reachable and needed
- [ ] Confirmation the naive picks include a locked concept (bounce) and an already-recalled one (waste)
- [ ] Confirmation the composed tutor makes strictly more good recommendations
- [ ] `python3 tutor.py --check` printing SELF-TEST PASS: comp-good, scaffold-faded, naive-locked, naive-waste, composed-wins
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. What three signals must a good next-step recommendation satisfy, and which prior module is each from?
2. Why is a good recommendation the conjunction of the signals rather than any one of them?
3. The naive tutor recommended attention and retrieval. Explain why each is a bad pick, and name the failure mode.
4. The naive tutor missed calculus entirely. Why, and what does that reveal about sorting by confidence?
5. Your own learner state was run through both tutors. How many good recommendations did each make, and did the naive one bounce or waste?

## External resources

- Intelligent tutoring systems literature (knowledge tracing + mastery learning) — my summary: how adaptive tutors estimate mastery and select the next skill, the real systems this composition abstracts; read it for how the signals are estimated and the loop is closed over time.
- Corbett & Anderson, *Knowledge Tracing* — my summary: the model behind estimating whether a skill is mastered from performance, which feeds the frontier and calibration signals here; read it for where the mastery and recall estimates come from.
- This hub, *teach-inter-03*, *teach-inter-05*, *teach-inter-06* — the calibration, prerequisite-frontier, and expertise-reversal modules this capstone composes; read them for each signal in isolation before seeing them combined into one decision.
