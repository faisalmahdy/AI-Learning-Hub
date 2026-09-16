---
id: conjunction-inter-01
title: A conjunction is never more probable than its parts — yet the detailed, representative story feels the most likely
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 16 min
summary: Ask which is more probable — that someone is a bank teller, or that they are a bank teller and an activist — and add a fitting detail (they were described as socially engaged), and intuition insists the second is more likely because it paints a more coherent picture. It cannot be: the people who are both tellers and activists are a subset of the people who are tellers, so their count, and their probability, is smaller or equal. Every condition added to a hypothesis can only shrink the set that satisfies it, so a more specific hypothesis is never more probable than a broader one it contains — P(A and B) ≤ P(A), always. The trap is that the mind judges probability by representativeness (how well a description fits a prototype), not by set size, and adding a fitting detail raises representativeness while lowering probability, so the two move in opposite directions. On a fixture of 12 people with 4 tellers, of whom 1 is also an activist, P(teller) = 0.33 while P(teller and activist) = 0.08 — a quarter as probable, though it sounds more specific — and the conjunction's probability never exceeds either part's for any tag pair.
eli5: Imagine a big box of toys. "A red toy" describes a lot of them. "A red toy that is also a car" describes fewer, because it has to be both. So "red and a car" can never be more common than "red" — you've added a requirement, which can only rule things out. But if someone tells you a story that sounds just right — "it's red and it's a car and it has a little bell" — the detailed version feels more likely, even though each added detail actually makes it rarer. A better-fitting story is not a more probable one.
---

## Why this module

Probability is set size — the fraction of ways the world could be that make a statement true — and adding a detail to a statement can only remove ways, so a richer, better-fitting story is describing a smaller set even as it feels like a surer bet.

Here is the classic setup. You read a description of a person and are asked which is more probable: that they are a bank teller, or that they are a bank teller *and* an activist. If the description mentioned social engagement, almost everyone picks the second — it fits the description better, it tells a more coherent story. And it is impossible for it to be more probable. The set of people who are both tellers and activists is contained inside the set of people who are tellers; you cannot be the first without being the second. A contained set is no larger than the set that contains it, so its probability is no larger. Adding the "and an activist" clause did not make a subgroup that the "teller" clause missed — it carved a piece *out* of the tellers. Every conjunct you tack on can only shrink the target, never grow it, so `P(A and B) ≤ P(A)` with no exceptions and no dependence on what A and B are.

**Adding a condition to a hypothesis can only shrink the set that satisfies it, so a conjunction is never more probable than either part — P(A and B) ≤ P(A) and ≤ P(B) — however specific and fitting the extra condition makes the story sound.**

The reason the error is so natural is that people do not estimate probability by counting the set; they estimate it by *representativeness* — how well the hypothesis matches a mental prototype of the evidence. A detailed hypothesis that lines up with every clue feels highly representative, and representativeness is read off as probability. But adding a detail that fits raises representativeness while, mechanically, lowering probability, so the two signals point in opposite directions and intuition follows the wrong one. This is not confined to puzzles about tellers: a specific forecast ("a recession triggered by an oil shock in Q3") is judged likelier than the broad event containing it ("a recession"), and an over-fitted explanation that accounts for every data point beats a simple one — the detail buys plausibility and spends probability. This module counts a small population to show the conjunction always losing.

## Concepts

**A hypothesis' probability is the fraction of the population it matches** — its set size divided by the whole. To match a set of tags, a person must contain every tag in it.

```python filename=modules/ai-for-science-and-data/code/conjunction-inter-01/conjunction.py:41-43 COMPLETE
def matches(population, tags):
    """Indices of people whose tag set contains every tag in `tags`."""
    return [i for i, person in enumerate(population) if all(t in person for t in tags)]
```

**A conjunction is an intersection** — the people matching "teller and activist" are exactly those in both the teller set and the activist set, so the conjunction's set is contained in each part's set.

```python filename=modules/ai-for-science-and-data/code/conjunction-inter-01/conjunction.py:46-48 COMPLETE
def prob(population, tags):
    """The fraction of the population matching all of `tags` -- our probability estimate."""
    return len(matches(population, tags)) / len(population)
```

**Representativeness moves opposite to probability.** A more detailed hypothesis fits the evidence better (more representative) but matches fewer cases (less probable), and the mind tracks the first while the question asks the second.

<svg role="img" aria-label="The set of tellers-who-are-activists is drawn as a small circle entirely inside the larger circle of tellers, so it is necessarily smaller" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the conjunction is a subset, so its probability cannot be larger</text>
  <circle cx="110" cy="56" r="40" fill="var(--s1)" opacity="0.25" stroke="var(--s1)"/>
  <text x="86" y="30" fill="var(--s1)" font-size="8">tellers</text>
  <circle cx="120" cy="64" r="16" fill="var(--s2)" opacity="0.5" stroke="var(--s2)"/>
  <text x="104" y="66" fill="var(--ink)" font-size="6">+ activist</text>
  <text x="180" y="50" fill="var(--muted)" font-size="8">P(teller) = 4/12 = 0.33</text>
  <text x="180" y="66" fill="var(--muted)" font-size="8">P(teller & activist) = 1/12 = 0.08</text>
  <text x="180" y="82" fill="var(--muted)" font-size="8">subset ⇒ 0.08 ≤ 0.33, always</text>
</svg>
^ The "teller and activist" set sits entirely inside the "teller" set, so it holds no more people and its probability, 0.08, cannot exceed the broad hypothesis' 0.33.

**Estimate a hypothesis' probability by the size of the set it matches, not by how well it fits the story — because a fitting detail raises representativeness while shrinking the set, so the most convincing conjunction is the least probable claim.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/conjunction-inter-01/conjunction.py

The fixture is a 12-person reference population tagged with professions and traits, and three broad/extra tag pairs to compare.

```json filename=modules/ai-for-science-and-data/code/conjunction-inter-01/conjunction.json:3-17 COMPLETE
  "population": [
    ["teller", "activist"],
    ["teller"],
    ["teller"],
    ["teller"],
    ["teacher", "activist"],
    ["teacher"],
    ["artist", "activist"],
    ["artist", "activist"],
    ["nurse"],
    ["nurse", "activist"],
    ["engineer"],
    ["lawyer", "activist"]
  ],
  "pairs": [["teller", "activist"], ["artist", "activist"], ["teacher", "activist"]]
```

Run `--rank` to compare each single hypothesis with its conjunction.

```text filename=--rank
RANK — P(single hypothesis) vs P(the conjunction), for each pair (n=12)
----------------------------------------------------------------------
  broad hypothesis        conjunction                     P(broad)  P(both)
  'teller'                'teller and activist'           0.333     0.083
  'artist'                'artist and activist'           0.167     0.167
  'teacher'               'teacher and activist'          0.167     0.083
```

For the teller pair, the broad hypothesis matches 4 of 12 people (0.333) and the conjunction matches 1 (0.083) — the "and an activist" clause carved three people out, so the more specific claim is a quarter as probable. The teacher pair does the same, 0.167 down to 0.083. The artist pair is the instructive edge case: P(artist) = 0.167 and P(artist and activist) = 0.167, exactly equal, because in this population every artist happens to be an activist, so the extra clause removed no one. That is the inequality's boundary — the conjunction can *equal* the part when the extra condition is already implied, but it can never *exceed* it. In no row does the conjunction come out higher, and it cannot, because a subset is never larger than its superset. The "and activist" version sounds more specific and, for the teller who was described as socially engaged, more fitting — and the fitting version is the less probable one in every row where it differs at all.

<svg role="img" aria-label="For the teller pair, P(teller) is 0.333 and P(teller and activist) is 0.083; representativeness of the conjunction is higher while its probability is lower" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">teller pair: probability vs how the mind rates it</text>
  <text x="6" y="34" fill="var(--muted)" font-size="8">P(teller)</text>
  <rect x="90" y="26" width="130" height="12" fill="var(--s1)"/><text x="224" y="36" fill="var(--muted)" font-size="7">0.333</text>
  <text x="6" y="54" fill="var(--muted)" font-size="8">P(both)</text>
  <rect x="90" y="46" width="32" height="12" fill="var(--s2)"/><text x="126" y="56" fill="var(--muted)" font-size="7">0.083 — lower probability</text>
  <line x1="90" y1="74" x2="250" y2="74" stroke="var(--grid)"/>
  <polygon points="120,68 250,68 250,80 120,80" fill="var(--s2)" opacity="0.3"/><text x="150" y="90" fill="var(--muted)" font-size="7">feels more representative →</text>
  <text x="6" y="90" fill="var(--muted)" font-size="7">probability falls</text>
</svg>
^ The conjunction "teller and activist" has the lower probability (0.083 vs 0.333) yet the higher representativeness — the detail that makes it feel more likely is the same detail that makes it less likely.

## Build

The inequality is not a statistical tendency but a hard fact of set containment. Run `--space` to see it.

```text filename=--space
SPACE — who matches 'teller' vs 'teller and activist'
------------------------------------------------------------
  match 'teller':            people [0, 1, 2, 3]  (4)
  match 'teller and activist':  people [0]  (1)
  is the conjunction a subset of the broad set? True
```

The people matching "teller" are indices 0, 1, 2, 3; the people matching "teller and activist" are index 0 alone — and index 0 is one of the four. The conjunction's set is literally a subset of the broad set, confirmed by the containment check. This is why the inequality has no exceptions and needs no data: it is not that conjunctions *tend* to be rarer, it is that the matching set can only lose members when you add a requirement, so its size is monotonically non-increasing in the number of conjuncts.

<svg role="img" aria-label="Of twelve people, four are tellers and only one of those is also an activist, so the conjunction cell count is one, a subset of the four" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">12 people; tellers outlined, teller AND activist filled</text>
  <g>
  <rect x="20" y="22" width="20" height="20" fill="var(--s2)" stroke="var(--s1)" stroke-width="2"/><text x="26" y="36" fill="var(--panel)" font-size="7">0</text>
  <rect x="44" y="22" width="20" height="20" fill="none" stroke="var(--s1)" stroke-width="2"/><text x="50" y="36" fill="var(--ink)" font-size="7">1</text>
  <rect x="68" y="22" width="20" height="20" fill="none" stroke="var(--s1)" stroke-width="2"/><text x="74" y="36" fill="var(--ink)" font-size="7">2</text>
  <rect x="92" y="22" width="20" height="20" fill="none" stroke="var(--s1)" stroke-width="2"/><text x="98" y="36" fill="var(--ink)" font-size="7">3</text>
  <rect x="116" y="22" width="20" height="20" fill="none" stroke="var(--line)"/><rect x="140" y="22" width="20" height="20" fill="none" stroke="var(--line)"/><rect x="164" y="22" width="20" height="20" fill="none" stroke="var(--line)"/>
  <rect x="20" y="46" width="20" height="20" fill="none" stroke="var(--line)"/><rect x="44" y="46" width="20" height="20" fill="none" stroke="var(--line)"/><rect x="68" y="46" width="20" height="20" fill="none" stroke="var(--line)"/><rect x="92" y="46" width="20" height="20" fill="none" stroke="var(--line)"/><rect x="116" y="46" width="20" height="20" fill="none" stroke="var(--line)"/>
  </g>
  <text x="200" y="34" fill="var(--s1)" font-size="8">tellers: 4</text>
  <text x="200" y="50" fill="var(--s2)" font-size="8">+ activist: 1 (subset)</text>
  <text x="6" y="86" fill="var(--muted)" font-size="8">the filled cell is one of the four outlined ones — the conjunction cannot exceed the part</text>
</svg>
^ Four of the twelve people are tellers (outlined) and only one of those is also an activist (filled) — the conjunction is a single cell inside the four, so its count and probability cannot exceed the broad hypothesis'.

```python filename=modules/ai-for-science-and-data/code/conjunction-inter-01/conjunction.py:85-92 COMPLETE
    conj_le_broad = all(prob(pop, [a, b]) <= prob(pop, [a]) for a, b in data["pairs"])
    print("  every conjunction is no more probable than its broad part = %s" % conj_le_broad)

    conj_le_extra = all(prob(pop, [a, b]) <= prob(pop, [b]) for a, b in data["pairs"])
    print("  every conjunction is no more probable than its extra part = %s" % conj_le_extra)

    subset_always = all(set(matches(pop, [a, b])).issubset(set(matches(pop, [a]))) for a, b in data["pairs"])
    print("  the conjunction's people are always a subset of the broad set = %s" % subset_always)
```

Because it is a fact about sets and not about this particular population, it holds for any A and B on any data — which is exactly why "add a plausible detail" is such a reliable way to make a claim feel stronger while making it weaker. The discipline it demands in analysis is to distrust the specific, well-fitting hypothesis precisely when it feels most compelling: a model that explains every wrinkle in the data, a forecast pinned to a particular mechanism, a diagnosis that ties every symptom together. Each added specificity is a conjunct, and each conjunct can only lower the probability that the whole story is true, no matter how much it raises the story's coherence. The simplest hypothesis consistent with the evidence is not just cleaner; it is, by the conjunction rule, at least as probable as any elaboration of it.

## Definition of done

The self-test pins the rule across every pair, and marks where the inequality is strict versus tight.

```python filename=modules/ai-for-science-and-data/code/conjunction-inter-01/conjunction.py:94-98 COMPLETE
    strict_somewhere = any(prob(pop, [a, b]) < prob(pop, [a]) for a, b in data["pairs"])
    print("  at least one conjunction is strictly less probable (the detail costs mass) = %s" % strict_somewhere)

    a0, b0 = data["pairs"][0]
    example_gap = prob(pop, [a0]) - prob(pop, [a0, b0])
    print("  example: P('%s')=%.3f vs P('%s and %s')=%.3f, gap %.3f"
          % (a0, prob(pop, [a0]), a0, b0, prob(pop, [a0, b0]), example_gap))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — P(A and B) <= P(A) and <= P(B) for every pair; adding a condition never raises probability
------------------------------------------------------------------------------------------------------------
  every conjunction is no more probable than its broad part = True
  every conjunction is no more probable than its extra part = True
  the conjunction's people are always a subset of the broad set = True
  at least one conjunction is strictly less probable (the detail costs mass) = True
  example: P('teller')=0.333 vs P('teller and activist')=0.083, gap 0.250
```

**Done means the conjunction rule is proven by counting: every conjunction's probability is ≤ its broad part's and ≤ its extra part's, the conjunction's matching people are always a subset of the broad set, and where the extra condition removes anyone the inequality is strict — P(teller) = 0.333 versus P(teller and activist) = 0.083, a gap of 0.250 that the more-specific, more-fitting hypothesis pays for its detail.**

## Boss fight

Predict the two places the conjunction rule is misread. It is tempting to conclude "always prefer the vaguest hypothesis."

The first trap is confusing *probability* with *usefulness*. The conjunction rule says the broad hypothesis is always at least as probable, but the broad hypothesis is often useless precisely because it is broad — "something will happen" is certain and worthless. Analysis needs specific, falsifiable, informative claims, and those are conjunctions with lower probability by construction. So the rule is not "prefer the vaguer claim"; it is "do not let a claim's specificity fool you into thinking it is more probable." The skill is to hold the two apart: judge a detailed hypothesis on its evidence and its explanatory value, while remembering that each detail lowers its prior probability, so a specific claim needs correspondingly more evidence to reach the same posterior. Detail must be paid for in evidence, not granted for free because it fits.

The second trap is that the rule governs the probability of the conjunction *as a claim about one case*, not the frequency of the pattern in a population — and conflating those reintroduces the error in reverse. That an added condition lowers a probability does not mean added conditions are never worth conditioning on: conditioning on more evidence (Bayesian updating) can raise your belief, because P(hypothesis | more evidence) is a different quantity from P(hypothesis and that evidence). The conjunction fallacy is about ranking `P(A)` against `P(A and B)` — two unconditional joint probabilities where the second is a subset of the first. It is not about `P(A)` against `P(A | B)`, the conditional, which can be anything. Mixing them up leads people to either dismiss useful evidence ("adding conditions always lowers probability, so ignore B") or to commit the original fallacy again. The clean statements are: a conjunction is never more probable than its conjuncts, and a conditional probability is a separate thing entirely — keep the joint and the conditional in different mental columns.

**A conjunction can never be more probable than either of its parts, because its matching set is a subset — so distrust a detailed, well-fitting hypothesis exactly when its specificity makes it feel most probable, and require more evidence for a more specific claim rather than crediting the detail; but do not overcorrect into preferring vacuous broad claims (they are probable and useless) or into confusing the joint P(A and B), which the rule ranks, with the conditional P(A given B), which is a different quantity that added evidence can legitimately raise.**

## External resources

Tversky and Kahneman's "Extensional versus intuitive reasoning: The conjunction fallacy in probability judgment" — the original Linda experiment, the representativeness heuristic behind it, and the many variants that reproduce the error.

Any probability text's statement of the monotonicity of measure (P(A ∩ B) ≤ P(A)) and of the distinction between joint and conditional probability — the formal backbone of why the fallacy is a fallacy and where its boundary (equality) lies.

The companion "a 99% detector that is mostly wrong when it fires" (base-rate) and "switching wins Monty Hall 2/3 of the time" modules — all three are probability-reasoning traps where an intuitive judgment (representativeness, ignoring the base rate, treating remaining options as equal) diverges from the correct set-counting or conditional answer.
