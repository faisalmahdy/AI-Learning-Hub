---
id: teach-inter-12
title: Space the reviews out — massing the same number into one session retains almost nothing by the test
topic: teaching-and-portability
level: intermediate
status: ready
time: 21 min
summary: For a fixed number of reviews, when you do them decides how much sticks. Massed reviews pile onto a memory that never faded, barely growing its durability; spaced reviews each rebuild a partly-faded memory, compounding stability, and leave the last review nearer the test. Three reviews on day 0 retain 0.0025 by day 30; three spread over 20 days retain 0.52 — a 211× gap for the same effort.
eli5: Watering a plant three times in one minute is not the same as watering it three times over three weeks — the first way, most of the water runs off because the soil is already soaked. Studying works the same: spreading your reviews out lets each one soak in, so you remember far more for the same amount of studying.
---

## Why this module

The same amount of studying can leave you remembering almost everything or almost nothing, and the only difference is how you spaced it.

Cramming feels efficient — do all the reviewing in one session, get it done. And it works in the very short term: right after the cram, everything is fresh. But memory fades with time, and a crammed session is a single point far in the past by the time you are tested, so most of it has decayed. Spreading the same reviews across days does something cramming cannot: each spaced review catches the memory partly faded and rebuilds it, and rebuilding a faded memory is what makes it durable. Massing reviews onto a memory that never had time to fade wastes most of them — there was nothing to reconstruct, so little sticks.

This is the spacing effect, one of the most robust findings in the science of learning, and it is counterintuitive precisely because massed practice feels better while you do it. The crammed session produces high performance immediately, which reads as "I know this," so people cram, feel confident, and then forget. The spaced schedule feels harder — each review starts from a partly-forgotten state, which is effortful and feels like failure — but that effort is exactly what builds lasting memory. The feeling of ease during study is anti-correlated with long-term retention.

Two mechanisms both favor spacing, and they compound. First, each spaced review rebuilds a faded memory, which increases its stability — roughly, how long it will last before fading again — far more than a massed review, which rebuilds nothing. Second, spreading reviews out means the last review is closer to the test, so there is less time for the final decay. Massing loses on both counts: low stability, and a long gap from the single early session to the test.

We will study three reviews two ways and test on day 30. Massed — all three on day 0 — ends with low stability and decays for 30 days, retaining 0.0025: essentially nothing. Distributed — days 0, 10, 20 — builds triple the stability and decays only 10 days from the last review, retaining 0.52. Same three reviews, a 211-fold difference in what survives.

**For a fixed number of reviews, spacing them rebuilds a faded memory each time (compounding stability) and leaves the last review near the test, so distributed practice retains far more than massing the same effort into one session.**

## Concepts

Model memory with a stability S — think of it as a decay time, the number of days over which the memory fades. Retention after a gap is exp(−gap/S): right after a review retention is 1, and it falls off faster when S is small. The whole story is what happens to S across reviews and how far the test is from the last one.

A review's effect on S depends on spacing, and this is the crux. A review that comes after a real gap — when the memory has partly faded — is effortful: you have to reconstruct something that was slipping, and that reconstruction strengthens the memory, raising S substantially. A review that comes immediately after another, with no gap, finds the memory still fully fresh; there is nothing to reconstruct, so it adds almost nothing to S. So spaced reviews each ratchet S upward while massed reviews are nearly wasted after the first. In the model, the stability gained from a review scales with how much was forgotten since the last one, which is zero for a massed review and large for a well-spaced one.

<svg role="img" aria-label="Two mechanisms favoring distributed: higher stability (5 vs 15.5) and a shorter decay from the last review to the test (30 days vs 10)" viewBox="0 0 460 150" width="460" height="150">
  <rect x="0" y="0" width="460" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">two mechanisms, both favoring distributed</text>
  <text x="20" y="52" font-family="var(--mono)" font-size="9" fill="var(--ink)">stability S</text>
  <rect x="130" y="42" width="40" height="16" fill="var(--s2)" stroke="var(--line)"/><text x="176" y="55" font-family="var(--mono)" font-size="8" fill="var(--muted)">massed 5</text>
  <rect x="130" y="62" width="124" height="16" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="260" y="75" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">distributed 15.5 (higher = slower decay)</text>
  <text x="20" y="112" font-family="var(--mono)" font-size="9" fill="var(--ink)">decay to test</text>
  <rect x="130" y="102" width="180" height="16" fill="var(--s2)" stroke="var(--line)"/><text x="316" y="115" font-family="var(--mono)" font-size="8" fill="var(--muted)">massed 30 days (last review day 0)</text>
  <rect x="130" y="122" width="60" height="16" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="196" y="135" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">distributed 10 days (last review day 20)</text>
</svg>
^ Distributed wins on both dials: it builds higher stability (slower forgetting) and its last review sits nearer the test (less decay to suffer).

The second mechanism is pure timing. Retention at the test decays from the *last* review, over the gap between it and the test day. Massing puts all reviews early, so the last review is far from the test and the memory decays the whole way. Spacing puts the last review late, so there is little decay left to suffer. Even with equal stability, the schedule whose last review is nearer the test retains more — and spacing gives you both the higher stability and the nearer last review.

Together these make the retention gap between massed and distributed enormous, not marginal, which is why the effect is so practically important. It also explains the "desirable difficulty" framing: the spaced schedule is harder during study because each review starts from a faded state, and that difficulty is not a cost to minimize but the very thing producing the durable memory. A study method that feels easy — massing, rereading, cramming — is often building the weakest memory, and one that feels effortful — spacing, retrieval from a faded state — is building the strongest. Feeling and effectiveness point opposite ways, which is why learners reliably choose the worse method.

**Stability grows most from a review that rebuilds a faded memory, so spaced reviews compound S while massed ones waste it; and retention decays from the last review, which spacing places nearer the test — both effects favoring distribution.**

## Worked example

The fixture is two schedules of three reviews each and a test day.

```json filename=modules/teaching-and-portability/code/teach-inter-12/study.json:7-20 COMPLETE
  "test_day": 30,
  "start_stability": 5.0,
  "schedules": {
    "massed": [
      0,
      0,
      0
    ],
    "distributed": [
      0,
      10,
      20
    ]
  }
```

Both schedules have three reviews and both are tested on day 30; massed does them all on day 0, distributed on days 0, 10, 20.

```text filename=modules/teaching-and-portability/code/teach-inter-12/spacing.py --schedules
SCHEDULES — same number of reviews, tested on day 30
--------------------------------------------------
  massed       reviews on days [0, 0, 0]   (last review day 0)
  distributed  reviews on days [0, 10, 20]   (last review day 20)
--------------------------------------------------
  both do 3 reviews -- the only difference is when.
```

Stability builds across the reviews, and a spaced review adds more than a massed one.

```python filename=modules/teaching-and-portability/code/teach-inter-12/spacing.py:41-51 COMPLETE
def final_stability(schedule, start):
    """Build up memory stability across the reviews; a spaced review adds more than a massed one."""
    S = start
    last = None
    for day in schedule:
        if last is not None:
            gap = day - last
            # a review after a gap comparable to S is effortful and adds stability; gap 0 adds nothing
            S = S + S * (1 - math.exp(-gap / S))
        last = day
    return S
```

Retention at the test decays from the last review over the stability built.

```python filename=modules/teaching-and-portability/code/teach-inter-12/spacing.py:54-58 COMPLETE
def retention(schedule, test_day, start):
    """Retention at the test: decay from the last review, over the stability built."""
    S = final_stability(schedule, start)
    last = schedule[-1]
    return math.exp(-(test_day - last) / S)
```

Predict: massed's day-0-only reviews add no stability (each gap is 0), so S stays 5, and decaying from day 0 to day 30 over S=5 gives exp(−30/5) = exp(−6) ≈ 0.0025. Distributed's spaced reviews raise S well above 5, and it decays only from day 20 to 30. Run it.

```text filename=modules/teaching-and-portability/code/teach-inter-12/spacing.py --retention
RETENTION — final stability and retention at day 30
----------------------------------------------------------
  massed       stability  5.00   last review day  0   retention 0.0025
  distributed  stability 15.46   last review day 20   retention 0.5236
----------------------------------------------------------
  distributed builds more stability and its last review is nearer the test.
```

Massed ends at stability 5.00 — the two extra reviews on day 0 added nothing, because there was no gap and nothing to rebuild — and decaying for the full 30 days it retains 0.0025, essentially forgotten. Distributed ends at stability 15.46, more than triple, because each spaced review caught a faded memory and strengthened it, and it decays only 10 days from its last review, retaining 0.5236. Both mechanisms show in the numbers: the higher stability (15.46 vs 5.00) and the nearer last review (day 20 vs day 0). Same three reviews; 0.25% versus 52%.

<svg role="img" aria-label="Retention at the test: massed near zero, distributed about half" viewBox="0 0 460 140" width="460" height="140">
  <rect x="0" y="0" width="460" height="140" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">retention at day 30 (same 3 reviews)</text>
  <line x1="60" y1="110" x2="440" y2="110" stroke="var(--line)"/>
  <rect x="100" y="108" width="120" height="2" fill="var(--s2)" stroke="var(--line)"/><text x="130" y="102" font-family="var(--mono)" font-size="11" fill="var(--s2)">0.0025</text><text x="120" y="126" font-family="var(--mono)" font-size="9" fill="var(--muted)">massed</text>
  <rect x="280" y="45" width="120" height="65" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="315" y="39" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">0.52</text><text x="278" y="126" font-family="var(--mono)" font-size="9" fill="var(--muted)">distributed</text>
</svg>
^ Massing leaves a sliver by the test; spacing the same three reviews retains about half — a 211× difference from scheduling alone.

<svg role="img" aria-label="Retention over time: the massed curve decays from day 0 to nearly zero by day 30; the distributed curve resets upward at each review on days 0, 10, 20 and stays high at the test" viewBox="0 0 460 200" width="460" height="200">
  <rect x="0" y="0" width="460" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">retention over time (reviews reset it to 1)</text>
  <line x1="40" y1="160" x2="440" y2="160" stroke="var(--line)"/>
  <line x1="40" y1="40" x2="40" y2="160" stroke="var(--line)"/>
  <text x="20" y="45" font-family="var(--mono)" font-size="8" fill="var(--muted)">1</text>
  <line x1="400" y1="35" x2="400" y2="170" stroke="var(--ink)" stroke-dasharray="3 2"/><text x="378" y="184" font-family="var(--mono)" font-size="8" fill="var(--ink)">test day 30</text>
  <path d="M40 40 C 90 120, 200 158, 400 159" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <text x="120" y="150" font-family="var(--mono)" font-size="9" fill="var(--s2)">massed → 0.0025</text>
  <path d="M40 40 C 70 80, 110 100, 160 108 L160 40 C 190 70, 230 82, 280 88 L280 40 C 320 60, 370 66, 400 74" fill="none" stroke="var(--acc-ink)" stroke-width="2"/>
  <circle cx="160" cy="40" r="2.5" fill="var(--acc-ink)"/><circle cx="280" cy="40" r="2.5" fill="var(--acc-ink)"/>
  <text x="300" y="60" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">distributed → 0.52</text>
  <text x="150" y="176" font-family="var(--mono)" font-size="8" fill="var(--muted)">↑ reviews day 10, 20 reset distributed; massed all at day 0</text>
</svg>
^ Massed decays from a single day-0 spike to nearly nothing by the test; distributed resets at each spaced review and each rebuild leaves it more durable, so it is still high at day 30.

## Build

Reproduce the retentions. Pure standard library, deterministic, so 0.0025 and 0.5236 come out exactly.

Run `--schedules` for the setup, `--retention` for the numbers, `--check` for the gate. The self-test pins the whole story: distributed wins, both use the same number of reviews, distributed builds more stability, and the gap is large.

```python filename=modules/teaching-and-portability/code/teach-inter-12/spacing.py:90-96 COMPLETE
    r_massed = retention(massed, t, s0)
    r_dist = retention(distributed, t, s0)

    distributed_wins = r_dist > r_massed
    print("  distributed retains more than massed = %s (%.4f vs %.4f)" % (distributed_wins, r_dist, r_massed))

    same_effort = len(massed) == len(distributed)
    print("  both schedules use the same number of reviews = %s (%d each)" % (same_effort, len(massed)))
```

The `same_effort` check is what makes this a lesson about scheduling rather than about effort. It confirms both schedules use the same number of reviews — three each — so the massive retention difference cannot be attributed to studying more. It is the identical amount of study, arranged two ways, and the arrangement alone produces the 211× gap. Without this check, someone could dismiss the result as "distributed just studied more"; the equal count rules that out.

```python filename=modules/teaching-and-portability/code/teach-inter-12/spacing.py:99-104 COMPLETE
    distributed_more_stable = final_stability(distributed, s0) > final_stability(massed, s0)
    print("  distributed builds more stability = %s (%.2f vs %.2f)"
          % (distributed_more_stable, final_stability(distributed, s0), final_stability(massed, s0)))

    big_gap = r_dist > 10 * r_massed
    print("  the retention gap is large, not marginal = %s (%.0fx)" % (big_gap, r_dist / r_massed))
```

```text filename=modules/teaching-and-portability/code/teach-inter-12/spacing.py --check
SELF-TEST — distributed retains far more than massed for the same number of reviews
----------------------------------------------------------------------------------------
  distributed retains more than massed = True (0.5236 vs 0.0025)
  both schedules use the same number of reviews = True (3 each)
  distributed builds more stability = True (15.46 vs 5.00)
  the retention gap is large, not marginal = True (211x)
----------------------------------------------------------------------------------------
SELF-TEST PASS  distributed_wins=True  same_effort=True  distributed_more_stable=True  big_gap=True
```

Four True flags. Distributed_wins: spacing retains more. Same_effort: with the identical number of reviews. Distributed_more_stable: because each spaced review built more durability. Big_gap: the difference is 211×, not a rounding-level edge. The same_effort flag is the one that makes the result matter — this is not "study more," it is "study the same amount, spread out," which is free.

**The equal-review-count check proves the 211× gap comes from scheduling alone, not from more study — the same effort, arranged differently.**

## Definition of done

You are done when you reproduce the retentions and can explain both mechanisms.

Concretely: `--retention` shows massed at 0.0025 (stability 5, last review day 0) and distributed at 0.52 (stability 15.5, last review day 20); `--check` prints PASS with four True flags. You can explain why a massed review adds little stability (nothing to reconstruct) while a spaced one adds a lot (rebuilding a faded memory), and why the last review's distance from the test also matters. You can state the desirable-difficulty point: spacing feels harder because each review starts from a faded state, and that difficulty is what builds durable memory. And you can name the trap: massing and rereading feel productive while building the weakest memory.

The habit to carry: for anything you need to retain, spread the reviews across days rather than massing them, and expect the spaced schedule to feel harder — that difficulty is the mechanism, not a sign it is not working. When designing a curriculum or a study plan, schedule revisits with growing gaps rather than blocks of repetition.

## Boss fight

The instructive failure is the student who studies hard, feels ready, and fails anyway.

A student has a big exam in a month and does all their reviewing in a marathon session the week before. Coming out of it, they feel they know the material cold — massed practice produces high immediate performance — so they are confident. By exam day, a week of forgetting has erased most of it, and they underperform badly, baffled because they "studied so much." The studying was real; the schedule was wrong. The same hours spread across the month, in short spaced sessions, would have built durable memory and left the last review near the exam. The trap is that cramming feels like the more effective method while you do it, so students choose it, and the feeling of fluency during the cram is exactly the illusion that misleads them.

Your turn, two moves. First, find how much spacing helps by moving the last review. Keep the massed schedule but move it to day 25 instead of day 0 — still three reviews all at once, but late. Predict: stability is still 5 (no spacing), but the decay is now only 5 days, so retention is exp(−5/5) = exp(−1) ≈ 0.37 — much better than 0.0025, purely from the timing mechanism. That isolates the "last review near the test" effect from the stability effect, and shows even massed-but-late beats massed-but-early. Second, push the spacing further. Change distributed to days 0, 14, 28 (test still 30). Predict: the wider gaps build even more stability and the last review is at day 28, only 2 days before the test, so retention climbs above 0.52 toward near-1 — wider spacing, up to a point, keeps helping. The lesson: both mechanisms are dials you control by scheduling, and the worst thing you can do with a fixed amount of study is pile it all in early.

## External resources

The spacing effect is among the most replicated findings in learning science; Cepeda et al.'s meta-analysis "Distributed practice in verbal recall tasks" (2006) quantifies how retention depends on the gap between study sessions and the retention interval.

For the practitioner's synthesis, "Make It Stick" (Brown, Roediger, McDaniel) covers spacing alongside retrieval practice and desirable difficulties, and explains why massed practice feels effective while building weak memory.

For the model, the forgetting-curve and memory-stability framing underlies modern spaced-repetition algorithms (SuperMemo's SM-2, Anki, FSRS); their documentation describes stability growing with each successful spaced review, the mechanism this module computes.
