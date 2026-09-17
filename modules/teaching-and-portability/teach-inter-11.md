---
id: teach-inter-11
title: Advance on mastery, not the clock — fixed pacing lets prerequisite gaps compound down the chain
topic: teaching-and-portability
level: intermediate
status: ready
time: 21 min
summary: When each topic builds on the last, moving learners on a schedule carries their unfinished gaps forward, and because the next topic rests on this one, the gap compounds. Reaching 80% of each topic before advancing decays to 0.80, 0.64, 0.51, 0.41, 0.33 by the fifth topic; mastery-based advancement holds each topic at full and the chain stays at 1.0.
eli5: If you build a tower and each floor is only 80% finished before you start the next, the wobble adds up — by the fifth floor the whole thing is barely standing. If you finish each floor completely before building on it, the tower stays solid all the way up, even though the early floors took longer.
---

## Why this module

When knowledge is a chain — each topic standing on the one before — the pace you advance learners at decides whether the chain holds or quietly collapses, and a schedule-based pace collapses it.

Consider a sequence where each topic is a genuine prerequisite for the next: you cannot understand ratios without fractions, algebra without ratios, functions without algebra, calculus without functions. Now put a learner through it on a fixed schedule — two weeks per topic, ready or not, because the class moves together. A learner who does not finish a topic in the allotted time advances anyway, carrying a gap. That alone would be bad. But the gap does not sit still: the next topic is built on this one, so a shaky grasp of fractions caps how well ratios can possibly be learned, which caps algebra, and so on. The gaps compound down the chain.

The arithmetic is unforgiving. If a learner reaches only 80% of each topic before being pushed forward, their effective grasp of each topic is 80% of their grasp of the prerequisite — the masteries multiply. Eighty percent, then 64%, then 51%, then 41%, then 33%. By the fifth topic the learner is operating at a third of full mastery, and it looks like they "can't do calculus" when in truth they were set up to fail four topics ago by a policy that never let any floor of the tower finish before building the next.

Mastery-based advancement breaks the compounding by refusing to advance a learner until they have actually mastered the current topic. Every topic then rests on a fully-mastered prerequisite, nothing is carried forward, and the chain stays solid all the way down. It costs more time on the topics a given learner finds hard — the pace is individual, not uniform — but it buys a learner who can actually do the last topic, instead of one who was mathematically doomed by the third.

We will run one learner through a five-topic chain under both policies. Fixed pacing decays them to 0.33 by calculus. Mastery-based holds them at 1.0 the whole way. Same learner, same topics; the only difference is whether the policy let each topic finish.

**When topics form a prerequisite chain, an unfinished topic caps the next, so gaps multiply down the chain — fixed pacing compounds them to a fraction, mastery-based advancement holds the chain at full.**

## Concepts

The load-bearing structure is that mastery of a topic is bounded by mastery of its prerequisite. You cannot understand a topic better than you understand what it is built on; the foundation caps the ceiling. So when you advance a learner who is at 80% of topic i, the best they can reach on topic i+1 is not 80% of full — it is 80% of *their* 80%, because they are building on their own partial understanding, not on the full topic. Each link in the chain multiplies by the fraction achieved, and multiplication of fractions below one is exponential decay. This is the same compounding that makes a chain of sub-one factors vanish anywhere it appears; here the factors are per-topic mastery fractions.

That is why fixed pacing fails specifically on long chains. On a single topic, reaching 80% is a modest, recoverable gap. On a chain of five, 80% per link is 0.8⁵ ≈ 0.33 — the same modest gap, compounded, is now catastrophic. The failure is invisible early (topic one at 80% looks fine) and severe late (topic five at 33% looks like the learner hit a wall), which is exactly the trap: the cause and the symptom are separated by several topics, so the late failure gets blamed on the late topic instead of on the accumulated gaps and the policy that allowed them.

Mastery-based advancement sets the per-link fraction to one. By holding a learner until they reach the target — full mastery — before advancing, every link multiplies by 1.0, and 1.0 to any power is still 1.0. The chain does not decay because there is no shortfall to compound. The cost is time, and specifically variable time: a learner who finds ratios hard spends longer on ratios, so the pace is set by each learner's mastery rather than by the calendar. That variable time is the whole trade — you spend more of it early, on the foundations, to avoid a total collapse late.

This is Bloom's mastery learning, and the reason it produces such large effects — Bloom's famous "2 sigma" result — is precisely this compounding. Fixing the pace fixes the wrong variable: it holds time constant and lets mastery vary, when the thing that must not vary, on a prerequisite chain, is mastery. Hold mastery constant and let time vary, and the chain survives. The policy is not "spend more time" in general; it is "spend the time where the compounding will otherwise eat you," which is on every unfinished prerequisite.

**Mastery of a topic is capped by its prerequisite, so per-topic fractions multiply; fixed pacing holds time constant and lets the fractions compound, mastery-based holds mastery constant and lets time vary.**

## Worked example

The fixture is a prerequisite chain and the two policies' parameters.

```json filename=modules/teaching-and-portability/code/teach-inter-11/chain.json:7-15 COMPLETE
  "topics": [
    "fractions",
    "ratios",
    "algebra",
    "functions",
    "calculus"
  ],
  "fixed_per_topic": 0.8,
  "mastery_target": 1.0
```

Five topics in a chain. Under fixed pacing the learner reaches 80% of each topic before advancing; under mastery-based, they hold until 100%.

```text filename=modules/teaching-and-portability/code/teach-inter-11/mastery.py --chain
CHAIN — 5 topics, each a prerequisite for the next
------------------------------------------------------
  fractions -> ratios -> algebra -> functions -> calculus
------------------------------------------------------
  fixed pace: reach 80% of each topic then advance.
  mastery-based: hold until 100% before advancing.
```

Fixed pacing multiplies each topic's mastery by the previous one's.

```python filename=modules/teaching-and-portability/code/teach-inter-11/mastery.py:38-45 COMPLETE
def masteries_fixed(topics, per_topic):
    """Fixed pace: each topic reaches per_topic of the previous topic's mastery -- the gap compounds."""
    out = []
    m = 1.0
    for _ in topics:
        m *= per_topic
        out.append(round(m, 4))
    return out
```

Mastery-based multiplies by the target, 1.0, so nothing decays.

```python filename=modules/teaching-and-portability/code/teach-inter-11/mastery.py:48-55 COMPLETE
def masteries_mastery(topics, target):
    """Mastery-based: hold until the target before advancing, so every topic rests on a full prerequisite."""
    out = []
    m = 1.0
    for _ in topics:
        m = m * target  # advancing only at mastery = 1.0 leaves m unchanged
        out.append(round(m, 4))
    return out
```

Predict: fixed pacing gives 0.8, 0.8², 0.8³, 0.8⁴, 0.8⁵ — decaying to about a third. Mastery-based gives 1.0 all the way. Run it.

```text filename=modules/teaching-and-portability/code/teach-inter-11/mastery.py --mastery
MASTERY — effective grasp of each topic, fixed pace vs mastery-based
--------------------------------------------------------
  topic          fixed pace    mastery-based
  fractions      0.800          1.000
  ratios         0.640          1.000
  algebra        0.512          1.000
  functions      0.410          1.000
  calculus       0.328          1.000
--------------------------------------------------------
  fixed pace decays down the chain; mastery-based holds at full.
```

The fixed-pace column is a collapse in slow motion. Fractions at 0.800 looks fine — a B, nothing alarming. But it never recovers; it compounds. Ratios at 0.640, algebra at 0.512, functions at 0.410, and calculus at 0.328 — the learner reaches the last topic with a third of full mastery, having lost ground at every single step. The mastery-based column holds at 1.000 throughout, because each topic was finished before the next began. The gap between the two columns starts at 0.20 (fractions) and grows to 0.67 (calculus): the policies diverge more the deeper into the chain you go, which is the compounding made visible.

<svg role="img" aria-label="The policy gap by topic: 0.20 at fractions growing to 0.67 at calculus" viewBox="0 0 460 150" width="460" height="150">
  <rect x="0" y="0" width="460" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">gap between the policies, by topic (widens with depth)</text>
  <line x1="50" y1="120" x2="440" y2="120" stroke="var(--line)"/>
  <rect x="60" y="99" width="50" height="21" fill="var(--s1)" stroke="var(--line)"/><text x="70" y="93" font-family="var(--mono)" font-size="8" fill="var(--ink)">.20</text><text x="66" y="134" font-family="var(--mono)" font-size="7" fill="var(--muted)">frac</text>
  <rect x="135" y="82" width="50" height="38" fill="var(--s1)" stroke="var(--line)"/><text x="145" y="76" font-family="var(--mono)" font-size="8" fill="var(--ink)">.36</text><text x="141" y="134" font-family="var(--mono)" font-size="7" fill="var(--muted)">ratios</text>
  <rect x="210" y="69" width="50" height="51" fill="var(--s1)" stroke="var(--line)"/><text x="220" y="63" font-family="var(--mono)" font-size="8" fill="var(--ink)">.49</text><text x="216" y="134" font-family="var(--mono)" font-size="7" fill="var(--muted)">algebra</text>
  <rect x="285" y="59" width="50" height="61" fill="var(--s1)" stroke="var(--line)"/><text x="295" y="53" font-family="var(--mono)" font-size="8" fill="var(--ink)">.59</text><text x="288" y="134" font-family="var(--mono)" font-size="7" fill="var(--muted)">funcs</text>
  <rect x="360" y="50" width="50" height="70" fill="var(--s2)" stroke="var(--line)"/><text x="370" y="44" font-family="var(--mono)" font-size="8" fill="var(--s2)">.67</text><text x="362" y="134" font-family="var(--mono)" font-size="7" fill="var(--muted)">calc</text>
</svg>
^ The distance between fixed and mastery-based pacing grows at every topic — a flat penalty would stay level, so the growth is the compounding itself.

<svg role="img" aria-label="A chain of five topics with arrows, each a prerequisite for the next" viewBox="0 0 460 90" width="460" height="90">
  <rect x="0" y="0" width="460" height="90" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">each topic is a prerequisite for the next</text>
  <g font-family="var(--mono)" font-size="9">
    <rect x="14" y="35" width="74" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="24" y="54" fill="var(--acc-ink)">fractions</text>
    <rect x="102" y="35" width="66" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="112" y="54" fill="var(--acc-ink)">ratios</text>
    <rect x="182" y="35" width="70" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="192" y="54" fill="var(--acc-ink)">algebra</text>
    <rect x="266" y="35" width="80" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="276" y="54" fill="var(--acc-ink)">functions</text>
    <rect x="360" y="35" width="80" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="370" y="54" fill="var(--acc-ink)">calculus</text>
  </g>
  <g stroke="var(--ink)"><line x1="88" y1="50" x2="102" y2="50"/><line x1="168" y1="50" x2="182" y2="50"/><line x1="252" y1="50" x2="266" y2="50"/><line x1="346" y1="50" x2="360" y2="50"/></g>
  <text x="14" y="82" font-family="var(--mono)" font-size="9" fill="var(--muted)">a gap in any box caps every box to its right</text>
</svg>
^ The topics form a chain, so an unfinished box does not just hurt itself — it caps the mastery of everything downstream of it.

<svg role="img" aria-label="Mastery down the chain: the fixed-pace line decays from 0.8 to 0.33 while the mastery-based line stays flat at 1.0" viewBox="0 0 460 190" width="460" height="190">
  <rect x="0" y="0" width="460" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">effective mastery down the chain</text>
  <line x1="50" y1="160" x2="440" y2="160" stroke="var(--line)"/>
  <line x1="50" y1="40" x2="50" y2="160" stroke="var(--line)"/>
  <text x="24" y="45" font-family="var(--mono)" font-size="9" fill="var(--muted)">1.0</text>
  <g font-family="var(--mono)" font-size="8" fill="var(--muted)"><text x="55" y="176">frac</text><text x="330" y="176">calculus</text></g>
  <line x1="60" y1="52" x2="410" y2="52" stroke="var(--acc-ink)" stroke-width="2"/><circle cx="410" cy="52" r="4" fill="var(--acc-line)"/><text x="300" y="46" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">mastery-based 1.0</text>
  <polyline points="60,76 148,99 235,116 322,130 410,138" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <circle cx="60" cy="76" r="3" fill="var(--s1)"/><circle cx="148" cy="99" r="3" fill="var(--s1)"/><circle cx="235" cy="116" r="3" fill="var(--s1)"/><circle cx="322" cy="130" r="3" fill="var(--s1)"/><circle cx="410" cy="138" r="4" fill="var(--s2)"/>
  <text x="300" y="150" font-family="var(--mono)" font-size="9" fill="var(--s2)">fixed pace → 0.33</text>
</svg>
^ Fixed pacing decays with every prerequisite, ending at a third of full mastery; mastery-based holds the line because no gap is ever carried forward.

## Build

Reproduce the two columns. Pure arithmetic, so 0.800 down to 0.328 and the flat 1.000 come out exactly.

Run `--chain` for the setup, `--mastery` for the columns, `--check` for the gate. The self-test pins the compounding: fixed pacing falls at every step, ends at a fraction, mastery-based holds, and the gap widens with depth.

```python filename=modules/teaching-and-portability/code/teach-inter-11/mastery.py:88-94 COMPLETE
    fx = masteries_fixed(topics, per_topic)
    ms = masteries_mastery(topics, target)

    fixed_decays = all(fx[i] < fx[i - 1] for i in range(1, len(fx)))
    print("  fixed pacing's mastery falls at every step (gaps compound) = %s (%s)" % (fixed_decays, fx))

    fixed_last_is_fraction = fx[-1] < 0.4
    print("  by the last topic the fixed-pace learner is at a fraction = %s (%.3f)" % (fixed_last_is_fraction, fx[-1]))
```

The `gap_widens` check is the one that proves this is compounding and not just a constant handicap. It asserts the gap between the two policies at the *end* of the chain is larger than at the start — 0.67 versus 0.20 — which can only happen if the shortfall grows with each link. A constant per-topic penalty would keep the gap fixed; a compounding one widens it, and the widening is the signature of the multiplication. Here is the full gate.

```python filename=modules/teaching-and-portability/code/teach-inter-11/mastery.py:97-102 COMPLETE
    mastery_holds = all(abs(m - 1.0) < 1e-9 for m in ms)
    print("  mastery-based stays at full mastery down the whole chain = %s (%s)" % (mastery_holds, ms))

    gap_widens = (ms[-1] - fx[-1]) > (ms[0] - fx[0])
    print("  the gap between the policies widens with depth = %s (%.3f at end vs %.3f at start)"
          % (gap_widens, ms[-1] - fx[-1], ms[0] - fx[0]))
```

```text filename=modules/teaching-and-portability/code/teach-inter-11/mastery.py --check
SELF-TEST — fixed pacing compounds the gaps to a fraction; mastery-based holds the chain at full
--------------------------------------------------------------------------------------------
  fixed pacing's mastery falls at every step (gaps compound) = True ([0.8, 0.64, 0.512, 0.4096, 0.3277])
  by the last topic the fixed-pace learner is at a fraction = True (0.328)
  mastery-based stays at full mastery down the whole chain = True ([1.0, 1.0, 1.0, 1.0, 1.0])
  the gap between the policies widens with depth = True (0.672 at end vs 0.200 at start)
--------------------------------------------------------------------------------------------
SELF-TEST PASS  fixed_decays=True  fixed_last_is_fraction=True  mastery_holds=True  gap_widens=True
```

Four True flags. Fixed_decays: fixed pacing loses ground at every topic. Fixed_last_is_fraction: it ends at a third of mastery. Mastery_holds: mastery-based stays at full. Gap_widens: the two policies diverge more the deeper the chain. The last flag is the one that identifies the mechanism — compounding, not a flat penalty — and it is why long prerequisite chains are where fixed pacing does the most damage.

**The widening gap is the fingerprint of compounding: a constant penalty would keep the gap fixed, so a gap that grows with depth proves the fractions are multiplying.**

## Definition of done

You are done when you reproduce the columns and can explain why the gap widens.

Concretely: `--mastery` shows fixed pacing decaying 0.800 → 0.328 while mastery-based holds at 1.000; `--check` prints PASS with four True flags. You can explain why mastery of a topic is capped by its prerequisite and why that makes per-topic fractions multiply. You can state the trade — fixed pacing holds time constant and lets mastery vary; mastery-based holds mastery constant and lets time vary — and say which variable must not vary on a prerequisite chain. And you can explain why the failure is misattributed: cause (early gaps) and symptom (late collapse) are separated by several topics.

The habit to carry: on any genuine prerequisite chain, advance on demonstrated mastery, not on a schedule, and when a learner fails a late topic, look upstream for the unfinished prerequisite before concluding the late topic is too hard. Spend the variable time early, where the compounding would otherwise eat you.

## Boss fight

The instructive failure is a whole cohort that "can't do algebra" because of fractions they never finished.

A math program runs on a fixed calendar: every class moves to the next unit on the same day regardless of who has mastered it. Students who are at 75% of fractions move on to ratios, reach 75% of that, and so on. By the time the cohort hits algebra, a large fraction of students are operating at well under half mastery, and the algebra teacher, seeing the wreckage, concludes "these students aren't ready for algebra" and the curriculum gets watered down. But algebra was never the problem; the problem was three units of unfinished prerequisites compounding, created by a pacing policy that valued keeping the class together over keeping the foundations solid. A mastery-based program — hold each student on a unit until they have it, let the pace vary — produces students who reach algebra able to do it, which is exactly what Bloom measured.

Your turn, two moves. First, find how the chain length changes the stakes. At 80% per topic, compute the mastery after 3 topics (0.51) versus 8 topics (0.17) and see that the same per-topic gap is a minor dent on a short chain and a catastrophe on a long one — so the longer the prerequisite chain, the more mastery-based pacing matters and the more fixed pacing costs. Second, find the per-topic fraction that fixed pacing would need to survive the chain. To end above 0.9 mastery after 5 topics, solve f⁵ ≥ 0.9, giving f ≥ 0.979 — so fixed pacing only works if learners reach 98% of every topic on schedule, which is nearly mastery-based pacing by another name. That is the real conclusion: on a prerequisite chain, "good enough per topic" is not good enough, because good enough compounds into not nearly enough, and the only per-topic bar that survives the chain is mastery.

## External resources

Benjamin Bloom's "The 2 Sigma Problem" (1984) is the origin of mastery learning as a measured intervention; it reports the large effect sizes that this module's compounding argument explains mechanistically.

For the modern implementation, Khan Academy and other competency-based platforms are built on exactly this — hold a learner on a skill until mastery, then unlock the next — and their design write-ups discuss the prerequisite-graph and mastery-threshold machinery.

For the learning-science backing, the literature on prior knowledge and prerequisite skills (for example the "How Learning Works" synthesis by Ambrose and colleagues) documents that new learning is bounded by the relevant prior knowledge, the individual-topic fact that this module chains into compounding.
