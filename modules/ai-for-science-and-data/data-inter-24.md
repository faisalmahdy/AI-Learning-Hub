---
id: data-inter-24
title: Count pairs, not items — or you badly overestimate how many it takes before two things collide
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 17 min
summary: How many people are needed before two probably share a birthday? Intuition says a lot — maybe half of 365. The answer is 23. It feels wrong because you picture it as people versus days: each new person is one more chance to match your birthday, and one person against 365 is a long shot. But a shared birthday is any pair matching, and n people form n(n−1)/2 pairs, which grows quadratically — 23 people already make 253 pairs, and 253 against 365 is not a long shot. The quantity that drives a collision is the number of pairs, not items, and pairs explode long before items do. This is the governing law of collisions everywhere: anything drawn from a space of d slots collides with even odds after only about √d draws, not d. On the fixture, 23 people in 365 days give a 50.7% chance of a shared birthday (22 give 47.6%), the threshold 23 sits near √365 = 19, and the same math puts 32-bit IDs at an even chance of collision near 2¹⁶ = 65 thousand, not 4 billion.
eli5: You'd think you need loads of people before two share a birthday — after all, there are 365 days. But you're not looking for someone who matches YOU; you're looking for any two people who match each other, and a small group has a surprising number of pairs to check. Just 23 people make 253 different pairs, and with that many pairs a match becomes more likely than not. The same trick means random ID numbers start repeating far sooner than you'd guess.
---

## Why this module

Estimating how soon two draws collide by comparing the number of items to the number of slots gives an answer that is wrong by a factor of the square root of the slot count, because collisions are driven by pairs and pairs grow quadratically.

Ask how many people you need before two probably share a birthday and the intuitive answer is large — you are imagining each person as one more ticket in a lottery against 365 days, and it takes a lot of tickets to likely hit one specific day. But that frames the wrong question. A shared birthday is not a match to *you*; it is a match between *any two* people, and the number of pairs among n people is n(n−1)/2, which grows with the square of n. Twenty-three people are only 23 tickets, but they are 253 pairs, and 253 chances of two matching among 365 days is not a long shot at all — it is better than even. The item count is what your intuition tracks; the pair count is what actually races the slots, and the pair count reaches the slot count while the item count is still small.

**A collision is driven by the number of pairs, not the number of items, and n items make about n²/2 pairs — so the pair count reaches the slot count while the item count is still near the square root of it.**

This is not a party trick; it is the law that governs collisions in every system that draws from a finite space. Random identifiers, hash values, cryptographic nonces, sharded keys — anything from a space of d slots collides with even odds after only about √d draws, not d, because √d draws make about d/2 pairs, which is where a collision becomes likely. A 32-bit random ID has four billion slots but starts colliding around sixty-five thousand IDs; a hash meant to resist collisions needs twice the bits you would naively budget. Estimate collision risk by items-versus-slots and you are safe by a factor of √d — catastrophically wrong. This module computes the birthday probabilities exactly and shows the threshold track √d rather than d.

## Concepts

**The collision probability** for n items in d slots is `1 − P(all distinct)`, where `P(all distinct) = (d/d)·((d−1)/d)·…·((d−n+1)/d)`. It is computed exactly, not estimated.

```python filename=modules/ai-for-science-and-data/code/data-inter-24/birthday.py:42-47 COMPLETE
def collision_prob(n, slots):
    """P(at least one collision among n items in `slots` slots) = 1 - P(all distinct)."""
    p_distinct = 1.0
    for i in range(n):
        p_distinct *= (slots - i) / slots
    return 1 - p_distinct
```

**Pairs, not items, drive collisions.** n items make `n(n−1)/2` pairs, which grows quadratically, so the pair count races ahead of the item count.

```python filename=modules/ai-for-science-and-data/code/data-inter-24/birthday.py:50-60 COMPLETE
def pairs(n):
    """The number of distinct pairs among n items."""
    return n * (n - 1) // 2


def threshold(slots, target=0.5):
    """The smallest n whose collision probability reaches `target`."""
    n = 1
    while collision_prob(n, slots) < target:
        n += 1
    return n
```

**The √d rule.** The 50% threshold lands near the square root of the slot count, because √d items make about d/2 pairs — the point where a collision becomes likely.

**The counterintuition is the item-versus-slot frame.** Thinking "n items against d slots" makes the threshold feel like it should be near d; the pair count is what makes it near √d instead.

**Collisions become likely at about the square root of the slot count, not the slot count itself, because the number of pairs — which is what collides — grows as the square of the number of items.**

<svg role="img" aria-label="Doubling the number of items roughly quadruples the number of pairs, so pairs race ahead of items toward the slot count" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">items grow linearly, pairs grow as the square</text>
  <text x="8" y="34" fill="var(--muted)" font-size="8">items</text>
  <rect x="55" y="26" width="20" height="12" fill="var(--grid)"/><text x="78" y="36" fill="var(--muted)" font-size="7">5</text>
  <rect x="55" y="42" width="40" height="12" fill="var(--grid)"/><text x="98" y="52" fill="var(--muted)" font-size="7">10 (x2)</text>
  <text x="8" y="76" fill="var(--s1)" font-size="8">pairs</text>
  <rect x="55" y="62" width="14" height="12" fill="var(--s1)"/><text x="72" y="72" fill="var(--muted)" font-size="7">10</text>
  <rect x="55" y="78" width="63" height="12" fill="var(--s1)"/><text x="121" y="88" fill="var(--muted)" font-size="7">45 (x4.5)</text>
  <text x="150" y="52" fill="var(--muted)" font-size="7">double the items →</text>
  <text x="150" y="88" fill="var(--muted)" font-size="7">~quadruple the pairs</text>
</svg>
^ Doubling the items from 5 to 10 roughly quadruples the pairs from 10 to 45 — the quadratic growth that makes the pair count reach the slots while the item count is still near √d.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/data-inter-24/birthday.py

The fixture is the classic setup — 365 days, 23 people — plus a 32-bit ID space for the application.

```json filename=modules/ai-for-science-and-data/code/data-inter-24/birthday.json:1-5 COMPLETE
{
  "_meta": "The birthday problem, and its lesson for collisions. days is the number of equally-likely slots (365 for birthdays). people is the classic group size (23). The probability that at least two of n people share a slot is 1 - product over i of (days-i)/days -- the chance that all n are distinct, subtracted from 1. The surprise is how FEW people it takes: the count crosses 50% at just 23, far below 365, because what matters is not people-versus-days but PAIRS-versus-days, and n people make n*(n-1)/2 pairs, which grows quadratically. The 50% point lands near the square root of days, not near days. id_bits applies the same math to random identifiers: with id_bits-bit random IDs there are 2^id_bits slots, and a collision becomes likely after only about sqrt(2^id_bits) = 2^(id_bits/2) IDs -- so 32-bit IDs collide around 65 thousand, not 4 billion.",
  "days": 365,
  "people": 23,
  "id_bits": 32
}
```

Run `--curve` to watch the probability climb with group size.

```text filename=--curve
CURVE — P(shared birthday) by group size (365 days)
----------------------------------------------------------
  people   pairs   P(collision)
  5        10      0.0271
  10       45      0.1169
  19       171     0.3791
  22       231     0.4757
  23       253     0.5073  <- crosses 50%
  30       435     0.7063
  40       780     0.8912
----------------------------------------------------------
  the pairs column, not the people column, is what races the 365 days.
```

Read the pairs column beside the people column. Five people are a negligible 2.7% because they are only 10 pairs against 365 days. By 23 people — still a small group — the pairs have grown to 253, comfortably comparable to 365, and the probability crosses 50%. The jump from 22 to 23 takes it from 47.6% to 50.7%. Notice how fast the pair count climbs relative to the people: doubling from 10 to 20 people roughly quadruples the pairs (45 to ~190), because pairs go as the square. The people column is what you count when you walk into the room; the pairs column is what determines whether two of them match, and it is already large when the room still looks small.

<svg role="img" aria-label="As people grow linearly, pairs grow quadratically and the collision probability rises past 50 percent at 23 people" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">P(shared birthday) vs group size</text>
  <line x1="30" y1="20" x2="30" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="95" x2="285" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="57" x2="285" y2="57" stroke="var(--line)" stroke-width="1" stroke-dasharray="3 3"/><text x="255" y="55" fill="var(--muted)" font-size="7">50%</text>
  <polyline points="40,93 70,84 110,60 130,49 160,39 200,29 250,22" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <circle cx="130" cy="49" r="3" fill="var(--s1)"/><text x="112" y="44" fill="var(--s1)" font-size="7">23 → 0.51</text>
  <text x="40" y="106" fill="var(--muted)" font-size="7">5</text><text x="126" y="106" fill="var(--muted)" font-size="7">23</text><text x="245" y="106" fill="var(--muted)" font-size="7">40</text>
  <text x="30" y="118" fill="var(--muted)" font-size="8">the curve crosses 50% at 23, not near 180 — pairs climb faster than people</text>
</svg>
^ The probability rises steeply and crosses the dashed 50% line at just 23 people, far left of the halfway-to-365 point intuition expects, because the pairs driving it grow quadratically.

## Build

The threshold's real scaling is the practical lesson. Run `--collisions`.

```text filename=--collisions
COLLISIONS — the 50% threshold sits near sqrt(slots), not slots
--------------------------------------------------------------
  birthdays:   365 slots   50% at 23 people   (sqrt = 19)
  32-bit ids:  4294967296 slots   50% near 77162 ids   (sqrt = 65536 = 2^16)
```

For birthdays, the 50% threshold of 23 sits near √365 = 19, not near 365 — the square root, not the count. The same relationship governs random identifiers, where it matters far more. A 32-bit ID has 4.29 billion slots, so intuition budgets billions of IDs before worrying about a collision; the birthday math says an even chance arrives at about 77,000 — near 2¹⁶, the square root of the space. That is five orders of magnitude sooner than the slot count. It is why 32-bit IDs are unsafe as unique keys at any real scale, why cryptographic hashes need 256 bits to resist a 128-bit birthday attack (an attacker only needs √(2²⁵⁶) = 2¹²⁸ work to find a collision), and why "the space is huge, collisions are impossible" is one of the most expensive wrong intuitions in systems design. The safe rule: to avoid collisions among m items, you need a space of about m² slots, not m.

<svg role="img" aria-label="For a 32-bit space of 4.29 billion, the 50 percent collision threshold is about 77 thousand, near the square root, far below the slot count" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">32-bit space: slots vs 50% collision threshold (log scale)</text>
  <line x1="30" y1="78" x2="285" y2="78" stroke="var(--grid)" stroke-width="1"/>
  <rect x="30" y="30" width="240" height="14" fill="var(--s2)"/><text x="34" y="41" fill="var(--panel)" font-size="8">slots: 4.29 billion (2^32)</text>
  <rect x="30" y="52" width="120" height="14" fill="var(--s1)"/><text x="34" y="63" fill="var(--panel)" font-size="8">50% collision: ~77k (≈2^16)</text>
  <text x="30" y="94" fill="var(--muted)" font-size="8">collisions start at the square root of the space — 5 orders of magnitude sooner</text>
</svg>
^ The collision threshold sits at roughly the square root of the slot count — about 77 thousand for a 4.29-billion space — so "the space is huge" is no protection at scale.

## Definition of done

The self-test pins it: 23 crosses 50% while 22 does not, the threshold is far below the days and near √days, the pair count rivals the slots, and 32-bit IDs collide far below their slot count.

```python filename=modules/ai-for-science-and-data/code/data-inter-24/birthday.py:99-112 COMPLETE
    crosses_at_23 = collision_prob(people, d) >= 0.5 and collision_prob(people - 1, d) < 0.5
    print("  %d people cross 50%% while %d do not = %s (%.4f vs %.4f)" % (people, people - 1, crosses_at_23, collision_prob(people, d), collision_prob(people - 1, d)))

    far_below_days = people < d / 4
    print("  the threshold is far below the number of days = %s (%d << %d)" % (far_below_days, people, d))

    near_sqrt = abs(threshold(d) - d ** 0.5) < 0.4 * (d ** 0.5)
    print("  the 50%% threshold is near sqrt(days) = %s (%d vs %.0f)" % (near_sqrt, threshold(d), d ** 0.5))

    driven_by_pairs = pairs(people) > d / 2
    print("  the pair count already rivals the slot count = %s (%d pairs vs %d days)" % (driven_by_pairs, pairs(people), d))

    id_collision_far_below_slots = threshold_id(2 ** bits) < 2 ** bits / 1000
    print("  %d-bit ids collide far below their slot count = %s (~%d vs %d)" % (bits, id_collision_far_below_slots, threshold_id(2 ** bits), 2 ** bits))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — 23 people cross 50% (far below 365); the threshold scales like sqrt(slots), driven by pairs
------------------------------------------------------------------------------------------------------------
  23 people cross 50% while 22 do not = True (0.5073 vs 0.4757)
  the threshold is far below the number of days = True (23 << 365)
  the 50% threshold is near sqrt(days) = True (23 vs 19)
  the pair count already rivals the slot count = True (253 pairs vs 365 days)
  32-bit ids collide far below their slot count = True (~77162 vs 4294967296)
------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  crosses_at_23=True  far_below_days=True  near_sqrt=True  driven_by_pairs=True  id_collision_far_below_slots=True
```

**Done means the surprise is quantified: 23 people cross 50% (0.5073) while 22 do not (0.4757), the threshold 23 is near √365 = 19 not near 365, the 253 pairs already rival the 365 days, and 32-bit IDs reach an even chance of collision near 77,000 — five orders of magnitude below their 4.29-billion slot count.**

## Boss fight

The birthday math assumed a fresh space each time. Predict how it changes when collisions are what you WANT, and the assumption that breaks it. It is tempting to treat √d as a universal constant.

Sometimes the collision is the goal, and then the √d law works for you instead of against you. Pollard's rho algorithm factors numbers and breaks discrete logarithms by deliberately walking a sequence until it collides with itself, which happens after about √d steps rather than d — turning an intractable d-sized search into a feasible √d one. Probabilistic data structures exploit the same math: a Bloom filter accepts a controlled false-positive (collision) rate to store a set in far less space, and hash-based sketches like HyperLogLog count distinct items by watching collision statistics. So the birthday bound is a two-edged tool — a hazard when you need uniqueness and a shortcut when you need a collision — and recognizing which case you are in tells you whether √d is a threat to defend against or a budget to spend.

The assumption that breaks the clean √d rule is uniformity. The birthday calculation assumes every slot is equally likely; real distributions are not uniform, and non-uniformity makes collisions happen even SOONER. If some birthdays (or hash outputs, or IDs) are more common than others, pairs concentrate on the popular values and the collision probability rises above the uniform prediction — the uniform case is the best case, not the typical one. This is why a hash function's quality matters so much: a hash that clusters its outputs collides far faster than √d, and an ID scheme with any structure (sequential prefixes, timestamp bits, non-random sources) collides faster still. So √d is the optimistic bound under perfect uniformity; assume it as an upper limit on safety, size your space with margin above m², and never let a non-uniform or attacker-influenced source feed a space you were sizing by the uniform birthday math.

```python filename=modules/ai-for-science-and-data/code/data-inter-24/birthday.py:88-91 COMPLETE
def threshold_id(slots):
    """Approximate 50% collision count for a huge slot space (the birthday bound ~1.177*sqrt(slots))."""
    import math
    return int(1.1774 * math.sqrt(slots))
```

**Collisions among items drawn from d slots become likely at about √d items, not d, because n items make n²/2 pairs and pairs are what collide — so size an ID or hash space at roughly the square of the number of items you expect (32-bit IDs collide near 65 thousand, not 4 billion), remember the collision can be a tool (Pollard's rho, Bloom filters) as well as a hazard, and treat √d as the optimistic uniform bound because any non-uniformity makes collisions come sooner.**

## External resources

Any probability text's treatment of the birthday problem — the exact formula, the √d scaling, and the surprising 23, presented as the canonical illustration of counterintuitive combinatorics.

Writing on the "birthday attack" in cryptography and on Pollard's rho — the same math as a security threat (why hash outputs need 2× the collision-resistance bits) and as an algorithmic tool (finding a collision in √d work).

The companion "a 99% detector that is mostly wrong when it fires — the base-rate fallacy" and "the law of small numbers" modules — three cases where the intuitive probability is off by a large factor, and correcting it requires counting the right quantity (pairs, base rates, sample sizes).
