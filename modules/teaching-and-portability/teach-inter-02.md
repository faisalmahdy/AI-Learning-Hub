---
id: teach-inter-02
title: Schedule reviews by whether you recalled — not by how many times you looked
topic: teaching-and-portability
level: intermediate
status: ready
time: 8-10h
summary: A spaced-repetition scheduler reads a recall ledger and doubles a concept's review interval when you pass and resets it to one day when you fail, so a concept failed four times running stays at interval 1 and comes due immediately while a mastered concept reaches interval 16. The seductive bug is to grow the interval on every review regardless of result: it feels like progress and empties the queue, but it pushes a chronically-failed concept out to interval 16 exactly like a mastered one, and today it buries bpe-tokens and kv-cache — the two concepts you are actively failing — from the due queue entirely. The fix is one branch: read the result of each review instead of merely counting that it happened.
eli5: Studying with flashcards works best when the cards you keep getting wrong come back often and the ones you know well come back rarely. A broken shuffler that just shows every card less and less often, whether or not you got it right, feels efficient because the pile shrinks — but it hides exactly the cards you keep failing. Show the ones you miss more, not less.
---

## Why this module

The hub's whole learning loop rests on the boss-fight recall ledger: after each module you attempt a from-memory recall, pass or fail, and log it. That ledger is only worth keeping if something reads it and tells you what to review next. This module builds that reader — a spaced-repetition scheduler — and the specific bug that makes it feel like it is working while it quietly hides the material you most need. The bug matters because it is the natural first implementation, it passes casual inspection, and it fails in the one direction that hurts learning: it stops surfacing what you do not know.

Spaced repetition is a simple, well-evidenced idea: expand the gap between reviews of a concept you keep recalling, and shrink it hard for a concept you blank on, so your limited review time flows to your weak spots. Encoded honestly, that is two rules — double the interval on a pass, reset it on a fail — and the reset is the load-bearing one. The seductive mistake is to grow the interval on every review, counting that a review happened rather than reading whether it succeeded. That version empties your queue and feels like mastery, but it treats a concept you have failed four times in a row exactly like one you have aced, pushing both far into the future. The concept you cannot recall stops appearing, which is the precise opposite of what a study scheduler is for.

You need no prior module, only the idea of a dated pass/fail log. Everything runs offline against a review fixture — five concepts with hand-authored histories, some mastered, some chronically failed — stdlib Python 3, `$0.00`. The instinct to unlearn is that a shrinking review queue means you are learning. A queue can shrink because you have mastered the material or because your scheduler has stopped showing you your failures, and only reading the results tells the two apart.

Here is what the bug hides from today's review queue:

```
# modules/teaching-and-portability/code/teach-inter-02/ — COMPLETE, run from that directory
$ python3 spaced.py --due

DUE — what each scheduler surfaces today (today=40)
------------------------------------------------------------------
  correct scheduler due: ['attention', 'bpe-tokens', 'kv-cache', 'quantization', 'retrieval-recall']
  naive scheduler due:   ['attention', 'quantization', 'retrieval-recall']
  hidden by the bug:     ['bpe-tokens', 'kv-cache']
```

run: 2026-08-26 · deterministic; review histories are a fixture · 5 concepts · `python3 spaced.py --due`

The correct scheduler surfaces all five, including the two concepts you are actively failing. The naive one surfaces three — and buries `bpe-tokens` and `kv-cache`, the two you cannot recall. This module is why those two lines differ.

<svg viewBox="0 0 700 170" role="img" aria-label="Today's due queue under each scheduler. Correct scheduler: five concept chips, all shown. Naive scheduler: three chips shown, and two chips (bpe-tokens, kv-cache) greyed out and marked hidden.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="18" fill="var(--muted)">due today (today=40): what each scheduler shows you</text>
    <text x="20" y="52" fill="var(--ink)" font-size="9">correct</text>
    <g fill="var(--acc-soft)" stroke="var(--acc-line)"><rect x="120" y="40" width="90" height="20" rx="10"></rect><rect x="216" y="40" width="90" height="20" rx="10"></rect><rect x="312" y="40" width="80" height="20" rx="10"></rect><rect x="398" y="40" width="90" height="20" rx="10"></rect><rect x="494" y="40" width="110" height="20" rx="10"></rect></g>
    <g fill="var(--acc-ink)" text-anchor="middle"><text x="165" y="54">attention</text><text x="261" y="54">bpe-tokens</text><text x="352" y="54">kv-cache</text><text x="443" y="54">quantization</text><text x="549" y="54">retrieval-recall</text></g>
    <text x="20" y="112" fill="var(--ink)" font-size="9">naive</text>
    <g fill="var(--panel)" stroke="var(--line)"><rect x="120" y="100" width="90" height="20" rx="10"></rect><rect x="398" y="100" width="90" height="20" rx="10"></rect><rect x="494" y="100" width="110" height="20" rx="10"></rect></g>
    <g fill="var(--ink)" text-anchor="middle"><text x="165" y="114">attention</text><text x="443" y="114">quantization</text><text x="549" y="114">retrieval-recall</text></g>
    <g fill="none" stroke="var(--muted)" stroke-dasharray="3 2"><rect x="216" y="100" width="90" height="20" rx="10"></rect><rect x="312" y="100" width="80" height="20" rx="10"></rect></g>
    <g fill="var(--muted)" text-anchor="middle"><text x="261" y="114">bpe-tokens</text><text x="352" y="114">kv-cache</text></g>
    <text x="120" y="140" fill="var(--s2)" font-size="8">dashed = hidden by the bug — the two concepts you are failing</text>
  </g>
</svg>
^ Same day, same ledger. The correct scheduler shows all five; the naive one drops the two dashed chips — precisely the concepts with recent fails. A shrinking queue looks like progress and is actually blindness.

## Concepts

Named here so you can find them again; each is built below.

- **Recall ledger** — the dated pass/fail log of boss-fight attempts per concept.
- **Review interval** — the current gap, in days, before a concept is shown again.
- **Expand on pass** — double the interval when you recall the concept; you need it less often.
- **Reset on fail** — collapse the interval to one day when you blank; you need it soon.
- **Next-due day** — last review day plus interval; a concept is due when that is today or earlier.
- **The grow-always bug** — expanding the interval on every review, ignoring the result.

## Worked example

Source: the SM-2 spaced-repetition family (Anki, SuperMemo) that schedules by recall success, reduced to its core interval rule; the review histories here stand in for a real boss-fight ledger so the intervals and due dates are exact and checkable. This is the reader for the ledger built in `teach-basic-01`.

Script and fixture: `modules/teaching-and-portability/code/teach-inter-02/` — `spaced.py`, and `reviews.json`, five concepts with ordered pass/fail histories and a fixed `today`. Every command runs from there.

### The correct scheduler: expand on pass, reset on fail

The interval starts at one day. Each review either doubles it or collapses it, depending on the result.

```
# spaced.py:40-51 — COMPLETE (double on pass; reset to 1 on fail)
def interval_correct(history):
    """Double the interval on a pass; RESET to 1 on a fail. Returns (interval, last_day)."""
    interval = 1
    last_day = 0
    for review in history:
        if review["result"] == "pass":
            interval *= 2
        else:
            interval = 1  # blanked -> bring it back tomorrow
        last_day = review["day"]
    return interval, last_day
```

A concept is due when its last review day plus its interval has arrived:

```
# spaced.py:63-69 — COMPLETE (next-due day, and whether it is due today)
def next_due(interval_fn, history):
    interval, last_day = interval_fn(history)
    return last_day + interval


def is_due(interval_fn, concept, today):
    return next_due(interval_fn, concept["history"]) <= today
```

Both schedulers share this due logic; they differ only in the interval they feed it, which is the entire point — the same due rule surfaces or hides a concept purely on the interval the scheduler assigned. Run the schedule and the intervals sort the concepts by how well you know them:

```
# $ python3 spaced.py --schedule
#   attention          interval=16  last=day15  due=day31   DUE
#   bpe-tokens         interval=1   last=day30  due=day31   DUE  (failing)
#   kv-cache           interval=1   last=day33  due=day34   DUE  (failing)
#   quantization       interval=8   last=day20  due=day28   DUE
#   retrieval-recall   interval=1   last=day22  due=day23   DUE  (failing)
```

run: 2026-08-26 · deterministic · `python3 spaced.py --schedule`

`attention`, recalled four times running, has climbed to interval 16 — a fortnight between reviews. `bpe-tokens`, failed four times, sits at interval 1, due the day after each attempt. The reset is doing the work: every fail drops the concept straight back to the front, no matter how long its history. That is the behaviour you want — the scheduler chases your weaknesses.

### The bug: grow the interval on every review

Here is the version that looks right and is not. It expands the interval on every review and never reads the result.

```
# spaced.py:53-61 — COMPLETE (the bug: grow always, never read the result)
def interval_naive(history):
    """The bug: grow the interval on EVERY review, ignoring pass/fail."""
    interval = 1
    last_day = 0
    for review in history:
        interval *= 2  # never reads review["result"] -- failures pushed out like passes
        last_day = review["day"]
    return interval, last_day
```

The only difference from the correct scheduler is the missing branch: `interval_correct` collapses on a fail, `interval_naive` doubles regardless. It feels like progress — every review pushes the concept further out, the due queue drains — but the interval now encodes only how many times you have looked at a concept, not whether you know it.

<svg viewBox="0 0 700 200" role="img" aria-label="Two interval trajectories for bpe-tokens over four failed reviews. Under the correct scheduler the interval stays flat at 1 across all four fails. Under the naive scheduler it doubles each time: 2, 4, 8, 16, climbing steeply, even though every review was a fail.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">bpe-tokens: interval after each review — every one a FAIL</text>
    <line x1="60" y1="160" x2="640" y2="160" stroke="var(--grid)"></line>
    <line x1="60" y1="30" x2="60" y2="160" stroke="var(--grid)"></line>
    <polyline points="120,156 260,156 400,156 560,156" fill="none" stroke="var(--s1)" stroke-width="2.5"></polyline>
    <text x="420" y="150" fill="var(--s1)" font-size="8">correct: stays at 1 (chases the failure)</text>
    <polyline points="120,150 260,138 400,110 560,52" fill="none" stroke="var(--s2)" stroke-width="2.5"></polyline>
    <text x="430" y="60" fill="var(--s2)" font-size="8">naive: 2, 4, 8, 16 (buries the failure)</text>
    <g fill="var(--muted)" text-anchor="middle"><text x="120" y="176">fail 1</text><text x="260" y="176">fail 2</text><text x="400" y="176">fail 3</text><text x="560" y="176">fail 4</text></g>
    <g fill="var(--muted)" text-anchor="end"><text x="54" y="160">1</text><text x="54" y="52">16</text></g>
  </g>
</svg>
^ Four failures in a row. The correct scheduler holds the interval at 1 so the concept keeps coming back; the naive one doubles it to 16, pushing a concept you have never once recalled two weeks into the future. The trajectories diverge precisely because one reads the result and the other counts the review.

### The two side by side

Put the intervals next to the trailing-fail count and the bug is unmistakable.

```
# $ python3 spaced.py --compare
#   concept            trailing-fails  correct-interval  naive-interval
#   attention          0               16                16
#   bpe-tokens         4               1                 16
#   kv-cache           2               1                 32
#   quantization       0               8                 8
#   retrieval-recall   1               1                 8
```

run: 2026-08-26 · deterministic · `python3 spaced.py --compare`

Where the trailing-fail count is 0 — `attention`, `quantization` — the two schedulers agree, because a history of pure passes doubles identically either way. The disagreement is entirely on the concepts with recent fails, and there the naive interval is wildly too large: `kv-cache`, failed twice recently, gets interval 32, larger than mastered `attention`. The naive scheduler has ranked a concept you cannot recall as more mastered than one you have aced, purely because it was reviewed more times. Interval under the bug measures exposure, not knowledge.

**A review scheduler must read the result of each review, not count that one happened: expand the interval on a pass and reset it on a fail, or a concept you keep failing is pushed out exactly like one you have mastered and vanishes from the queue that exists to resurface it.**

### The self-test

The `--check` mode asserts both behaviours: the correct scheduler keeps failed concepts short and lets mastered ones grow, and the naive scheduler commits the bug of pushing a failed concept far out and hiding it.

```
# $ python3 spaced.py --check
#   correct: a repeatedly-failed concept stays at interval 1 = True (bpe-tokens=1)
#   naive: the same failed concept is pushed far out = True (bpe-tokens=16)
#   correct: an all-pass concept reaches a long interval = True (attention=16)
#   the naive scheduler hides a failing concept that the correct one shows = True
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 spaced.py --check`

The `failed_stays_short` line is the correctness anchor: a concept whose last review was a fail must have interval 1, always, and if a refactor dropped the reset that assertion would fail first. The `bug_hides` line encodes the lesson as a guardrail — it confirms the naive scheduler actually removes a failing concept from today's due set that the correct scheduler surfaces, so the difference is not academic but a concept you would never see.

### The running tally

| concept | trailing fails | correct interval | naive interval | who is right |
|---|---|---|---|---|
| attention | 0 | 16 | 16 | agree — mastered |
| quantization | 0 | 8 | 8 | agree — progressing |
| bpe-tokens | 4 | 1 | 16 | correct — failing, show it |
| kv-cache | 2 | 1 | 32 | correct — failing, show it |

<svg viewBox="0 0 700 190" role="img" aria-label="Paired interval bars per concept, correct vs naive. attention: both 16. quantization: both 8. bpe-tokens: correct 1 (tiny), naive 16 (long). kv-cache: correct 1 (tiny), naive 32 (longest). The failing concepts show a huge gap between correct and naive.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">interval by concept: correct (chases fails) vs naive (buries them)</text>
    <line x1="60" y1="160" x2="660" y2="160" stroke="var(--grid)"></line>
    <g><rect x="80" y="80" width="20" height="80" fill="var(--s1)"></rect><rect x="102" y="80" width="20" height="80" fill="var(--s2)"></rect><text x="101" y="174" text-anchor="middle" fill="var(--muted)">attention</text><text x="101" y="74" text-anchor="middle" fill="var(--muted)">16/16</text></g>
    <g><rect x="200" y="120" width="20" height="40" fill="var(--s1)"></rect><rect x="222" y="120" width="20" height="40" fill="var(--s2)"></rect><text x="221" y="174" text-anchor="middle" fill="var(--muted)">quant</text><text x="221" y="114" text-anchor="middle" fill="var(--muted)">8/8</text></g>
    <g><rect x="330" y="155" width="20" height="5" fill="var(--s1)"></rect><rect x="352" y="80" width="20" height="80" fill="var(--s2)"></rect><text x="351" y="174" text-anchor="middle" fill="var(--muted)">bpe(fail x4)</text><text x="351" y="74" text-anchor="middle" fill="var(--s2)">1 / 16</text></g>
    <g><rect x="470" y="155" width="20" height="5" fill="var(--s1)"></rect><rect x="492" y="40" width="20" height="120" fill="var(--s2)"></rect><text x="491" y="174" text-anchor="middle" fill="var(--muted)">kv(fail x2)</text><text x="491" y="34" text-anchor="middle" fill="var(--s2)">1 / 32</text></g>
    <rect x="580" y="40" width="10" height="10" fill="var(--s1)"></rect><text x="594" y="49" fill="var(--muted)">correct</text>
    <rect x="580" y="56" width="10" height="10" fill="var(--s2)"></rect><text x="594" y="65" fill="var(--muted)">naive</text>
  </g>
</svg>
^ On the all-pass concepts the bars are equal; on the failing concepts the correct interval is a sliver and the naive one towers — largest of all for kv-cache, a concept you cannot recall. The gap is the bug, and it lives only where it hurts.

The top two rows are where the schedulers agree, and they lull you: on the material you know, the bug is invisible. The bottom two rows are where it counts, and there the naive interval is 16 and 32 — a fortnight or a month — for concepts you cannot recall at all. A scheduler that is correct exactly when it does not matter and wrong exactly when it does is worse than no scheduler, because it comes with false confidence. Judge it only on the failing rows.

### What we did not settle

Real spaced repetition is richer than double-or-reset. SM-2 grades recall on a scale, not pass/fail, and scales an ease factor per concept so a hard-but-known item grows more slowly than an easy one; a partial reset (back to a few days, not one) often beats a full reset for a concept you nearly had. Intervals also want a cap and a daily review budget, so a backlog after time away does not dump everything at once — which is the real version of the "today=40, everything due" pileup here. And the ledger this reads must itself be honest: a recall you graded a pass because you almost remembered poisons the schedule, which is why the hub's boss-fight rule is from-memory, module-closed. The rule here — read the result, reset on fail — is the floor every richer scheme is built on.

## Build

The practice in one paragraph: keep an honest per-concept recall ledger; schedule the next review by reading each result — expand the interval on a pass, reset it on a fail — never by counting reviews; compute due = last-review + interval and surface everything due, weakest first; and judge your scheduler only on the concepts you are failing, because that is the sole place a broken one differs from a good one. Cap intervals and bound the daily queue so time away does not bury you.

We opened on the due queue. The number that proves the scheduler works is what it refuses to hide:

```
# modules/teaching-and-portability/code/teach-inter-02/ — COMPLETE, run from that directory
$ python3 spaced.py --due
  hidden by the bug:     ['bpe-tokens', 'kv-cache']
```

Now run it on your own ledger. Take your real boss-fight passes and fails, schedule with expand-on-pass / reset-on-fail, and list what is due. Your number to beat is not the size of the due queue; it is **the set of currently-failing concepts, every one of which must be due** — if any concept whose last attempt was a fail is not in your due list, your scheduler has a grow-always bug somewhere. Then implement the naive version and confirm it hides some of them. Bring back both due lists. Good luck.

## Definition of done

- [ ] A scheduler that reads a pass/fail ledger and expands on pass, resets on fail
- [ ] Per-concept interval and next-due day computed from the history
- [ ] A due-today list that surfaces every concept whose last attempt was a fail
- [ ] The naive grow-always scheduler implemented for contrast
- [ ] Confirmation the naive scheduler pushes failed concepts out and hides them
- [ ] `python3 spaced.py --check` printing SELF-TEST PASS: failed-short, naive-pushes, mastered-grows, bug-hides
- [ ] Your own ledger scheduled both ways, with the concepts the bug hides recorded
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. State the two interval rules of the correct scheduler and explain which one is load-bearing and why.
2. The naive scheduler drops one branch. Which one, and what does the interval come to measure once it is gone?
3. A colleague says their review queue is nearly empty, so they must have learned the material. What alternative explanation must you rule out, and how?
4. Why do the correct and naive schedulers agree on all-pass concepts, and why does that agreement make the bug dangerous?
5. Your own ledger was scheduled both ways. Which failing concepts did the naive scheduler hide, and what interval did it assign them?

## External resources

- Piotr Wozniak, *The SM-2 algorithm* (SuperMemo) — https://super-memory.com/english/ol/sm2.htm — my summary: the graded-recall scheduler this module simplifies, with an ease factor per item and interval growth tied to recall quality; read it for the richer version of expand-on-pass and why a full reset is sometimes too harsh.
- Cepeda et al., *Distributed practice in verbal recall tasks* (2006) — my summary: the meta-analysis establishing that spaced review beats massed review across a wide range of intervals; read it for the evidence that the shape this scheduler enforces is worth enforcing.
- This hub, *teach-basic-01* — modules/teaching-and-portability/teach-basic-01.md — my summary: the recall ledger this scheduler reads, and the reader-derived-versus-emitter-claimed discipline behind it; read it for where the pass/fail data comes from and why it must be honest for this schedule to mean anything.
