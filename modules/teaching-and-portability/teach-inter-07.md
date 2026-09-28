---
id: teach-inter-07
title: Interleave practice types, don't block them — blocking wins the practice, interleaving the test
topic: teaching-and-portability
level: intermediate
status: ready
time: 5-8h
summary: Two learners practice the same three problem types the same number of times, differing only in order — one blocks (AAABBBCCC), one interleaves (ABCABCABC) — and blocking both feels better and scores better during practice because within a block every problem is the same type, so you are cued and fluent, while interleaving forces a which-method-is-this decision on every trial. But the delayed test is mixed and uncued, exactly like the real world, and it is a discrimination task, so the interleaved learner wins it decisively: on the stylized model the blocked schedule scores 0.825 in practice but only 0.427 on the test, while interleaved scores 0.600 in practice and 0.900 on the test — a clean reversal, the practice-best schedule being the test-worst. The whole gap traces to one countable thing, the number of type-switches (2 for blocked, 8 for interleaved), which is exactly how much discrimination each schedule practiced, and the trap is selecting the schedule by practice accuracy, a proxy that points the wrong way.
eli5: Imagine practicing three kinds of shots in a sport. If you take fifty of the same shot in a row, you get into a groove and look great in practice — but in a real game the shots come mixed and unannounced, and you freeze because you never practiced picking the right shot on the fly. If instead you mix the shots in practice, you look clumsy that day, but you get good at the real skill: deciding which shot the moment needs. Looking good in practice and being good in the game are not the same thing, and mixing it up trades the first for the second.
---

## Why this module

Learning has a metric problem that looks a lot like every other metric problem in this hub: the number you can see during practice is not the number you actually care about. What you care about is durable, transferable skill — can the learner solve a problem weeks later, mixed in with everything else, with no cue about which method applies. What you can see is how well practice is going right now. And those two numbers do not just differ in magnitude; on the choice of practice schedule they point in opposite directions.

The classic demonstration is blocking versus interleaving. Blocked practice groups all of one type together: all the type-A problems, then all the type-B, then all the type-C. Interleaved practice mixes them: A, B, C, A, B, C. Give a learner blocked practice and they look great — within a block every problem is the same kind, so after the first one or two they are primed and fluent, and their practice accuracy climbs. Give a learner interleaved practice and they struggle — every single problem is a switch, and before they can even apply a method they have to work out which method this problem needs. Blocking feels like mastery; interleaving feels like floundering.

Then the test comes, and it is nothing like blocked practice. Real problems arrive mixed and uncued, so the test is fundamentally a discrimination task: step one is recognizing which kind of problem you are looking at. Blocking never practiced that step — inside a block, you always knew the type for free. Interleaving practiced it on every trial.

<svg viewBox="0 0 700 160" role="img" aria-label="Two problems compared. Inside a block, the problem arrives with its type known, so the learner skips straight to executing the method. On the test, the problem arrives with no cue, so the learner must first decide which method applies, then execute. Blocking skips the decide step that the test requires.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">inside a block the type is free; on the test you must decide it first</text>
    <rect x="40" y="34" width="130" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="105" y="53" text-anchor="middle" fill="var(--acc-ink)" font-size="8">block: "type A" known</text>
    <text x="178" y="53" fill="var(--muted)">→</text>
    <rect x="200" y="34" width="120" height="30" fill="var(--panel)" stroke="var(--line)"></rect><text x="260" y="53" text-anchor="middle" fill="var(--muted)" font-size="8">skip deciding</text>
    <text x="328" y="53" fill="var(--muted)">→</text>
    <rect x="350" y="34" width="130" height="30" fill="var(--s1)"></rect><text x="415" y="53" text-anchor="middle" fill="var(--panel)" font-size="8">execute method</text>
    <rect x="40" y="98" width="130" height="30" fill="var(--panel)" stroke="var(--s2)"></rect><text x="105" y="117" text-anchor="middle" fill="var(--s2)" font-size="8">test: no cue</text>
    <text x="178" y="117" fill="var(--muted)">→</text>
    <rect x="200" y="98" width="120" height="30" fill="var(--s2)"></rect><text x="260" y="117" text-anchor="middle" fill="var(--panel)" font-size="8">DECIDE which method</text>
    <text x="328" y="117" fill="var(--muted)">→</text>
    <rect x="350" y="98" width="130" height="30" fill="var(--s1)"></rect><text x="415" y="117" text-anchor="middle" fill="var(--panel)" font-size="8">execute method</text>
    <text x="500" y="117" fill="var(--s2)" font-size="8">← the step blocking skipped</text>
    <text x="40" y="150" fill="var(--muted)" font-size="8">interleaving reps the DECIDE step every trial; blocking never does</text>
  </g>
</svg>
^ A blocked-practice problem lets the learner skip straight to executing the known method; a test problem forces the decide-which-method step first. That skipped step is exactly what interleaving trains and blocking omits. So the interleaved learner, who looked worse all through practice, wins the test decisively. This module makes the reversal concrete: two schedules, the same problems, the same number of reps, and it computes both the practice score and the delayed-test score from the one thing that separates the schedules — how many type-switches they contain. Everything runs offline against a schedule fixture, stdlib Python 3, `$0.00`. The instinct to unlearn is that practice performance measures learning. It measures practice; the switches you avoided to make practice smooth are the discrimination you failed to learn.

This is a stylized model of a robust, replicated finding, not a claim about exact effect sizes — but the mechanism it computes, discrimination from type-switches, is the real one.

## Concepts

Named here so you can find them again; each is built below.

- **Blocked practice** — group all reps of one type together (AAABBBCCC); cued, fluent, few switches.
- **Interleaved practice** — mix the types (ABCABCABC); every trial a switch, feels harder.
- **Type-switch** — a trial whose type differs from the one before; a rep at discrimination.
- **Discrimination** — recognizing which method a problem needs; the delayed test's real task.
- **Practice accuracy** — the score during practice; a proxy that favors blocking.
- **Delayed-test accuracy** — the uncued mixed test; the target that favors interleaving.

## Worked example

Source: the choice of how to sequence practice — the decision a curriculum, a spaced-review tool, or a tutor makes every time it orders problems. The schedules stand in for real practice sessions, and the stylized model turns the well-documented mechanism (discrimination is practiced by switches) into checkable numbers.

Script and fixture: `modules/teaching-and-portability/code/teach-inter-07/` — `interleave.py`, and `practice.json`, two schedules over three types. Every command runs from there.

### The mechanism: type-switches

The one thing that separates the two schedules is how often the problem type changes from trial to trial, and that count is the discrimination practiced.

```
# interleave.py:42-51 — COMPLETE (type-switches, and the discrimination they imply)
def switches(seq):
    """How many trials differ in type from the trial before -- each is a discrimination rep."""
    return sum(1 for i in range(1, len(seq)) if seq[i] != seq[i - 1])


def discrimination(seq):
    """Fraction of transitions that were switches: how much discrimination this schedule practiced."""
    return switches(seq) / (len(seq) - 1)
```

A switch is a trial where you cannot coast on the previous problem's type — you have to decide afresh what you are looking at. That decision is the exact skill the mixed test demands, so counting switches is counting reps at the test's real task. Look at the two schedules:

```
# $ python3 interleave.py --schedules
#   blocked      AAABBBCCC
#      type-switches: 2 of 8 transitions   discrimination practiced: 0.25
#   interleaved  ABCABCABC
#      type-switches: 8 of 8 transitions   discrimination practiced: 1.00
```

run: 2026-08-27 · deterministic; schedules and model constants are a fixture · 2 schedules · `python3 interleave.py --schedules`

Same nine problems, same three reps of each type — the only difference is the order, and the order produces wildly different switch counts. Blocked has 2 switches out of 8 transitions (only at the A→B and B→C block boundaries); interleaved has 8 out of 8 (every transition). The blocked learner practiced discrimination at a rate of 0.25; the interleaved learner at 1.00, four times as much, for the identical problems.

<svg viewBox="0 0 700 170" role="img" aria-label="Two practice sequences of nine problems. Blocked: A A A B B B C C C, with switch markers only at the two block boundaries. Interleaved: A B C A B C A B C, with a switch marker at every gap. Interleaved has eight switches, blocked has two.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">same problems, different order → very different switch counts</text>
    <text x="30" y="52" fill="var(--muted)" font-size="8">blocked</text>
    <g font-size="10">
      <text x="110" y="52" fill="var(--s2)">A</text><text x="140" y="52" fill="var(--s2)">A</text><text x="170" y="52" fill="var(--s2)">A</text><text x="205" y="52" fill="var(--s1)">B</text><text x="235" y="52" fill="var(--s1)">B</text><text x="265" y="52" fill="var(--s1)">B</text><text x="300" y="52" fill="var(--muted)">C</text><text x="330" y="52" fill="var(--muted)">C</text><text x="360" y="52" fill="var(--muted)">C</text>
    </g>
    <text x="188" y="40" fill="var(--ink)" font-size="11">|</text><text x="283" y="40" fill="var(--ink)" font-size="11">|</text>
    <text x="420" y="52" fill="var(--s2)" font-size="8">2 switches → discrimination 0.25</text>
    <text x="30" y="112" fill="var(--muted)" font-size="8">interleaved</text>
    <g font-size="10">
      <text x="110" y="112" fill="var(--s2)">A</text><text x="140" y="112" fill="var(--s1)">B</text><text x="170" y="112" fill="var(--muted)">C</text><text x="205" y="112" fill="var(--s2)">A</text><text x="235" y="112" fill="var(--s1)">B</text><text x="265" y="112" fill="var(--muted)">C</text><text x="300" y="112" fill="var(--s2)">A</text><text x="330" y="112" fill="var(--s1)">B</text><text x="360" y="112" fill="var(--muted)">C</text>
    </g>
    <g fill="var(--ink)" font-size="11"><text x="128" y="100">|</text><text x="158" y="100">|</text><text x="190" y="100">|</text><text x="220" y="100">|</text><text x="250" y="100">|</text><text x="285" y="100">|</text><text x="315" y="100">|</text><text x="345" y="100">|</text></g>
    <text x="420" y="112" fill="var(--s1)" font-size="8">8 switches → discrimination 1.00</text>
    <text x="30" y="150" fill="var(--muted)" font-size="8">each | is a switch: a rep at deciding which method the next problem needs</text>
  </g>
</svg>
^ Blocking clusters each type, so switches happen only at the two block seams; interleaving switches on every trial. The switch count is the discrimination each schedule trains — and the test is a discrimination task.

### The two outcomes

Practice accuracy and delayed-test accuracy are computed from that discrimination, in opposite directions.

```
# interleave.py:54-61 — COMPLETE (practice punishes switches; the test rewards discrimination)
def practice_accuracy(seq, m):
    """During practice: execution minus a cost for every switch (interleaving feels harder)."""
    return m["exec_max"] - m["practice_switch_cost"] * discrimination(seq)


def test_accuracy(seq, m):
    """Delayed mixed test: execution times how well discrimination was practiced (the test needs it)."""
    return m["exec_max"] * (m["test_floor"] + (1 - m["test_floor"]) * discrimination(seq))
```

The model says two honest things. Practice accuracy starts from execution skill (equal for both, since both did the same reps) and subtracts a cost for switching — so more switches means lower practice accuracy, which is why interleaving feels worse. Test accuracy starts from that same execution skill but scales it by how much discrimination was practiced — because on a mixed uncued test, executing a method you cannot select is worth little. Run the scores:

```
# $ python3 interleave.py --scores
#   schedule     practice   delayed-test
#   blocked      0.825      0.427
#   interleaved  0.600      0.900
```

run: 2026-08-27 · deterministic · `python3 interleave.py --scores`

There is the reversal in four numbers. Blocking scores 0.825 in practice — the visibly better session — but only 0.427 on the test. Interleaving scores 0.600 in practice — it looked like the worse session, and a learner would swear it was — but 0.900 on the test. The schedule that wins the number you watch loses the number you want, by a lot, and it loses it precisely because the thing that made practice feel smooth (never switching) is the thing the test requires.

<svg viewBox="0 0 700 190" role="img" aria-label="Grouped bars for two schedules on two metrics. Blocked: practice 0.825 tall, delayed-test 0.427 short. Interleaved: practice 0.600 medium, delayed-test 0.900 tall. The tallest practice bar (blocked) sits above the shortest test bar; the tallest test bar (interleaved) sits above a shorter practice bar. The metrics cross.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">practice score (proxy) vs delayed-test score (target) — the two cross</text>
    <line x1="60" y1="160" x2="660" y2="160" stroke="var(--line)"></line>
    <text x="200" y="178" text-anchor="middle" fill="var(--muted)" font-size="8">BLOCKED</text>
    <rect x="110" y="45" width="60" height="115" fill="var(--muted)"></rect><text x="140" y="39" text-anchor="middle" fill="var(--muted)" font-size="8">.825</text><text x="140" y="172" text-anchor="middle" fill="var(--muted)" font-size="7">practice</text>
    <rect x="230" y="100" width="60" height="60" fill="var(--s2)"></rect><text x="260" y="94" text-anchor="middle" fill="var(--s2)" font-size="8">.427</text><text x="260" y="172" text-anchor="middle" fill="var(--s2)" font-size="7">test</text>
    <text x="500" y="178" text-anchor="middle" fill="var(--muted)" font-size="8">INTERLEAVED</text>
    <rect x="410" y="76" width="60" height="84" fill="var(--muted)"></rect><text x="440" y="70" text-anchor="middle" fill="var(--muted)" font-size="8">.600</text><text x="440" y="172" text-anchor="middle" fill="var(--muted)" font-size="7">practice</text>
    <rect x="530" y="34" width="60" height="126" fill="var(--s1)"></rect><text x="560" y="28" text-anchor="middle" fill="var(--s1)" font-size="8">.900</text><text x="560" y="172" text-anchor="middle" fill="var(--s1)" font-size="7">test</text>
  </g>
</svg>
^ Blocking's practice bar is the tallest of the four but its test bar is the shortest; interleaving's test bar is the tallest but its practice bar is lower. Whichever metric you optimize, you get the opposite of the other — and only one of them is the real world.

**A mixed, uncued test is a discrimination task, and discrimination is practiced by type-switches — so interleaving (many switches) scores worse during practice but far better on the delayed test, while blocking (few switches) does the reverse; selecting a practice schedule by practice accuracy optimizes the proxy and ships the schedule that tests worst.**

### The self-test

The `--check` mode plants the bug — trusting practice accuracy — and proves the reversal: interleaving has more switches, blocking wins practice, interleaving wins the test, and so the practice-best schedule is not the test-best.

```
# $ python3 interleave.py --check
#   interleaving has more type-switches (more discrimination) = True (8 vs 2)
#   blocking wins the PRACTICE score = True (0.825 vs 0.600)
#   interleaving wins the delayed TEST = True (0.900 vs 0.427)
#   the practice-best schedule is NOT the test-best = True (practice:blocked, test:interleaved)
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 interleave.py --check`

The two middle lines are the reversal's halves, each read straight off the scores:

```
# interleave.py:102-108 — COMPLETE (blocking wins practice, interleaving wins the test)
    blocking_wins_practice = practice_accuracy(blk, m) > practice_accuracy(inter, m)
    print("  blocking wins the PRACTICE score = %s (%.3f vs %.3f)"
          % (blocking_wins_practice, practice_accuracy(blk, m), practice_accuracy(inter, m)))

    interleaving_wins_test = test_accuracy(inter, m) > test_accuracy(blk, m)
    print("  interleaving wins the delayed TEST = %s (%.3f vs %.3f)"
          % (interleaving_wins_test, test_accuracy(inter, m), test_accuracy(blk, m)))
```

The `reversal` line is the one that makes the practice number dangerous rather than merely imperfect. If practice accuracy were just a noisy version of test accuracy, optimizing it would at least point roughly the right way. Instead the schedule that maximizes practice accuracy is the one that minimizes test accuracy, so following the visible number does not just fail to help — it actively selects the worse curriculum.

```
# interleave.py:110-113 — COMPLETE (the reversal: practice-best and test-best are different schedules)
    practice_best = max(data["schedules"], key=lambda s: practice_accuracy(s["seq"], m))["name"]
    test_best = max(data["schedules"], key=lambda s: test_accuracy(s["seq"], m))["name"]
    reversal = practice_best != test_best
```

### The running tally

| schedule | switches | discrimination | practice | delayed test |
|---|---|---|---|---|
| blocked | 2 | 0.25 | 0.825 | 0.427 |
| interleaved | 8 | 1.00 | 0.600 | 0.900 |

Read the discrimination column against the last two: it is inversely related to practice accuracy and directly related to test accuracy. That single column drives both outcomes in opposite directions, which is why no amount of watching the practice score can reveal the right schedule — the practice score is highest exactly where the discrimination, and therefore the test score, is lowest. The lesson is the same shape as the Goodhart module in evals: the measure you optimize (practice accuracy) is not the measure you want (delayed transfer), and here optimizing it is not merely useless but backwards.

### What we did not settle

This is one mechanism — discrimination from switches — and learning has neighbors that interact with it. Interleaving works best when the types are confusable enough that discrimination is the hard part; if the types are obviously different, the benefit shrinks, and if switching is so costly that execution never consolidates, blocking a little first can help. Interleaving pairs with spacing (`teach-inter-02`): mixing types naturally spaces each type's reps apart, so the two desirable difficulties reinforce each other, and both trade practice-time smoothness for retention. The model here scores a schedule once; a real curriculum would also adapt the mix to the learner's frontier (`teach-inter-05`). And the constants are stylized — the direction of the reversal is the robust finding, not the exact 0.427. The invariant to carry: judge a practice schedule by a delayed, mixed, uncued test, never by how practice felt or scored.

## Build

The build in one paragraph: sequence practice by interleaving the problem types rather than blocking them, so every trial is a type-switch that reps the discrimination a real test demands; expect and accept that interleaving lowers practice-time accuracy — that discomfort is the desirable difficulty, not a failure — and judge the schedule only by a delayed, mixed, uncued test. Count the type-switches as a cheap proxy for the discrimination a schedule trains, pair interleaving with spacing, and back off toward some early blocking only when the types are so confusable that execution never consolidates.

We opened on the switch counts. The number that proves the point is the reversal between practice and test:

```
# modules/teaching-and-portability/code/teach-inter-07/ — COMPLETE, run from that directory
$ python3 interleave.py --scores
  blocked      0.825      0.427
  interleaved  0.600      0.900
```

Now build your own. Take real practice material with distinct problem types, sequence it both blocked and interleaved, and — crucially — measure not the practice session but a delayed mixed test. Your number to beat is not how practice felt; it is **the delayed-test accuracy, blocked versus interleaved** — interleaving should win the test even though it lost the practice. Count the switches in each schedule as the mechanism. Bring back both test scores. Good luck.

## Definition of done

- [ ] Two schedules over the same types with equal reps: blocked and interleaved
- [ ] A type-switch count and the discrimination it implies
- [ ] A practice-accuracy score that decreases with switches
- [ ] A delayed-test-accuracy score that increases with discrimination
- [ ] Confirmation blocking wins practice and interleaving wins the delayed test
- [ ] Confirmation the practice-best schedule is not the test-best (a reversal)
- [ ] `python3 interleave.py --check` printing SELF-TEST PASS: more_switches, blocking_wins_practice, interleaving_wins_test, reversal
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why does blocked practice score higher during practice, and why is that score misleading?
2. What makes a delayed mixed test a "discrimination task," and which schedule practices discrimination?
3. What is a type-switch, and why is counting switches a good proxy for what a schedule teaches?
4. Explain the reversal: why does optimizing practice accuracy select the worse curriculum?
5. Your own material was practiced both ways. What was the delayed-test score under each, and did interleaving win despite losing practice?

## External resources

- Rohrer & Taylor, *The shuffling of mathematics problems improves learning* — my summary: the study showing interleaved math practice crushes blocked on a delayed test despite worse practice performance; read it for the empirical reversal this module models.
- Bjork & Bjork, *Making Things Hard on Yourself, But in a Good Way: Creating Desirable Difficulties* — my summary: the framework tying interleaving, spacing, and testing together as difficulties that depress performance and improve learning; read it for why the practice-time discomfort is the point.
- This hub, *teach-inter-02* (spaced review) and the evals Goodhart module — read them for the spacing that interleaving reinforces and the general shape of optimizing a proxy that points away from the target.
