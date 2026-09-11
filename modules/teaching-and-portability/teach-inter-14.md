---
id: teach-inter-14
title: Score by knowledge component, not whole item — or you know a student is failing but not which skill to fix
topic: teaching-and-portability
level: intermediate
status: ready
time: 21 min
summary: Most problems exercise several skills at once, so a whole-item right/wrong score tells you whether a student got it, not why they missed it — and remediation must target a skill, which a percentage names. Two students can share the identical item accuracy while lacking completely different skills. Tagging each item with its required components and computing per-skill success localizes the deficit. On 6 items, two students both score 0.50, but component analysis pins one's failure to fractions (0.00) and the other's to multiplication.
eli5: If a recipe comes out wrong, "it tasted bad" doesn't tell you what to fix — was it the salt, the oven, the timing? You need to know which step failed. A test question usually needs several skills at once, so marking it just right-or-wrong hides which skill broke. Track each skill separately and you can see exactly what to practice.
---

## Why this module

Knowing a student got a problem wrong is a grade; knowing which skill they lack is a diagnosis, and a whole-item score gives you only the first.

Most real problems exercise several skills at once. A word problem needs reading, then setting up the equation, then doing the arithmetic; a proof needs three separate lemmas; a coding task needs syntax, logic, and an edge case. When you mark such an item as a single right-or-wrong, you collapse all of those skills into one bit. That bit tells you whether the student succeeded overall, but not why they failed — and the two are different questions with different uses. The overall bit lets you compute an accuracy; it does not let you teach, because teaching means choosing what to practice next, and "70% correct" names no skill to practice.

The failure is sharpest when you notice that item accuracy cannot distinguish students who need completely different help. Two students can answer the same test and get the identical number of items right, yet be missing entirely different skills — one stuck on fractions, the other on multiplication. Their whole-item scores are the same number, so any decision made from that number treats them identically, which means at least one of them gets sent to the wrong practice. The item score has thrown away the very information that would route each student correctly: which skills their errors share.

Decomposing each item into its knowledge components recovers that information. Tag every item with the skills it requires, and for each skill compute the student's success rate across just the items that use it. A missing skill now reveals itself as a low success rate on exactly the items requiring it, while the skills the student has stay high. The deficit is localized to a component instead of smeared across items: not "70% correct, remediate something," but "fractions are at 0%, everything else is fine, remediate fractions." Same responses, attributed to skills instead of items — a diagnosis instead of a grade.

On the fixture, two students each score 3 of 6 items — an identical whole-item accuracy of 0.50. But student P misses every item requiring fractions and student Q misses every item requiring multiplication. The item score is blind to the difference; the per-component analysis pins P's deficit to fractions (0.00 there, fine elsewhere) and Q's to multiplication.

**A whole-item score collapses the several skills a problem needs into one bit, so it can say a student failed but not which skill to remediate — and two students with identical item accuracy can need different help; tagging items with their knowledge components and scoring per skill localizes each deficit.**

## Concepts

The unit of teaching is the skill, not the item, and that mismatch is the whole problem. An item is a bundle of skills, chosen for convenience of testing, not because it isolates one thing to learn. A student's competence, though, lives at the level of skills — you master fractions, or you don't — and remediation acts at that level too, because you practice a skill, not an item. So a score reported at the item level is reported in the wrong unit for the decision it feeds. Converting from item-level evidence to skill-level knowledge is exactly what component scoring does, and skipping that conversion is why an item percentage cannot drive teaching.

<svg role="img" aria-label="An item bundles several skills into one right-or-wrong bit; the diagnosis needs the skills separated back out" viewBox="0 0 470 165" width="470" height="165">
  <rect x="0" y="0" width="470" height="165" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">an item is a bundle; teaching needs the parts</text>
  <rect x="40" y="45" width="70" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="52" y="61" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">add</text>
  <rect x="40" y="72" width="70" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="52" y="88" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">frac</text>
  <text x="120" y="75" font-family="var(--mono)" font-size="14" fill="var(--muted)">-></text>
  <rect x="150" y="58" width="70" height="24" fill="var(--panel)" stroke="var(--line)"/>
  <text x="160" y="74" font-family="var(--mono)" font-size="8" fill="var(--ink)">item: wrong</text>
  <text x="230" y="74" font-family="var(--mono)" font-size="8" fill="var(--s2)">one bit — which skill broke?</text>
  <text x="40" y="125" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">component scoring un-bundles it back:</text>
  <text x="60" y="145" font-family="var(--mono)" font-size="8" fill="var(--ink)">add 0.67 (fine)   frac 0.00 (the deficit)</text>
</svg>
^ The item fuses add and frac into a single wrong, which names no skill; component scoring un-bundles the responses back into per-skill rates, where the deficit is visible.

The reason item accuracy loses the diagnosis is that it marginalizes over skills. When an item requires skills A and B and the student gets it wrong, the item score records "wrong" without recording whether A, B, or both failed. Aggregate many such items and you get an accuracy that is some blend of the student's competence on every skill, weighted by how often each appears — a single number that many different skill profiles can produce. That many-to-one collapse is why two students with different deficits can share an accuracy: the accuracy is a projection that discards the direction the profiles differ in. Component scoring keeps the skills separate, so the profiles that item accuracy conflated stay distinct.

Attribution works by looking across items that share a skill. No single item can tell you which of its skills failed, but a set of items can, because the skills they require overlap differently. If a student fails every item that requires fractions and passes items that do not, fractions is the common factor in the failures — the skill whose presence predicts the miss. Computing a per-skill success rate is the simple version of this inference: for each skill, restrict to the items using it and measure the success rate there. The skill the student lacks shows a low rate on its items; the skills they have show high rates even on items that also touch the weak skill only when that weak skill is absent. The overlap in the item-skill mapping is what makes the deficit identifiable.

This is the core idea behind cognitive tutors and knowledge tracing: model the student as a vector of per-skill mastery, tag items with the skills (a "Q-matrix" mapping items to knowledge components), and update the skill estimates from responses so the tutor always knows which component to practice next. The deterministic all-or-nothing model here — an item is correct exactly when every required skill is mastered — is the clean skeleton; real systems add slip and guess probabilities and track mastery as it grows. But the essential move is this module's: never let the item be the final unit of analysis, because the item is a bundle and teaching needs the parts. Score the components, and the grade becomes a diagnosis.

**Competence and remediation live at the skill level while items bundle several skills, so an item score is in the wrong unit and marginalizes over skills into a many-to-one blur; scoring per component, using the overlap in which items share a skill, keeps the skill profiles distinct and identifies the deficit.**

## Worked example

The fixture is a set of skills, items tagged with the skills they require, and two students' mastered skills.

```json filename=modules/teaching-and-portability/code/teach-inter-14/skills.json:3-15 COMPLETE
  "skills": ["add", "mult", "frac"],
  "items": [
    ["add"],
    ["mult"],
    ["add", "mult"],
    ["frac"],
    ["add", "frac"],
    ["mult", "frac"]
  ],
  "students": {
    "P": ["add", "mult"],
    "Q": ["add", "frac"]
  }
```

Six items over three skills. Student P has mastered add and mult but not frac; student Q has add and frac but not mult. An item is correct exactly when the student has every skill it requires.

```python filename=modules/teaching-and-portability/code/teach-inter-14/components.py:41-47 COMPLETE
def correct(item_skills, mastered):
    """An item is correct iff the student has mastered every skill it requires."""
    return all(s in mastered for s in item_skills)


def item_accuracy(items, mastered):
    return round(sum(correct(it, mastered) for it in items) / len(items), 3)
```

The component analysis restricts to the items using each skill and measures the success rate there; the weakest skill is the one to remediate.

```python filename=modules/teaching-and-portability/code/teach-inter-14/components.py:50-62 COMPLETE
def component_rates(items, skills, mastered):
    """Per-skill success: fraction of items requiring that skill the student got right."""
    rates = {}
    for s in skills:
        using = [it for it in items if s in it]
        rates[s] = round(sum(correct(it, mastered) for it in using) / len(using), 3) if using else None
    return rates


def weakest(items, skills, mastered):
    """The skill with the lowest success rate -- the one to remediate."""
    rates = component_rates(items, skills, mastered)
    return min(rates, key=lambda s: rates[s])
```

Predict: P and Q will each get 3 of 6 (an item accuracy of 0.50), because each has two of three skills and the items are symmetric — but they will miss different items. Look at the responses.

```text filename=modules/teaching-and-portability/code/teach-inter-14/components.py --responses
RESPONSES — each item's required skills and whether each student got it right
--------------------------------------------------------------
  item  skills                  P   Q
  1     add                    Y     Y
  2     mult                   Y     n
  3     add+mult               Y     n
  4     frac                   n     Y
  5     add+frac               n     Y
  6     mult+frac              n     n
--------------------------------------------------------------
  P item accuracy: 0.50
  Q item accuracy: 0.50
```

Both students score 0.50 — identical whole-item accuracy. But look at the columns: P gets items 1, 2, 3 (the ones without fractions) and misses 4, 5, 6 (all with fractions); Q gets 1, 4, 5 (the ones without multiplication) and misses 2, 3, 6 (all with multiplication). The pattern of misses is completely different, and it is invisible in the 0.50. Now run the component analysis.

```text filename=modules/teaching-and-portability/code/teach-inter-14/components.py --components
COMPONENTS — per-skill success rate and inferred weakest skill
--------------------------------------------------------------
  P:  add 0.67   mult 0.67   frac 0.00   -> remediate frac
  Q:  add 0.67   mult 0.00   frac 0.67   -> remediate mult
--------------------------------------------------------------
  same 0.50 item accuracy, different skill at fault.
```

Now the two students are clearly different. P's fractions success is 0.00 while add and mult are 0.67 — fractions is the deficit. Q's multiplication is 0.00 while add and frac are 0.67 — multiplication is the deficit. The same 0.50 item accuracy that made them look identical resolves, under component scoring, into two different diagnoses and two different remediation targets. The 0.67 on the healthy skills (not 1.00) is itself informative: those skills show failures only on items that also require the missing skill, which is exactly the signature of a single localized deficit.

<svg role="img" aria-label="Two students both at 0.50 item accuracy; per-skill bars show P failing only fractions and Q failing only multiplication" viewBox="0 0 470 200" width="470" height="200">
  <rect x="0" y="0" width="470" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">same 0.50 item accuracy → different per-skill deficits</text>
  <text x="70" y="40" font-family="var(--mono)" font-size="9" fill="var(--ink)">student P</text>
  <text x="20" y="60" font-family="var(--mono)" font-size="7" fill="var(--muted)">add</text>
  <rect x="45" y="52" width="70" height="12" fill="var(--acc-line)"/>
  <text x="20" y="78" font-family="var(--mono)" font-size="7" fill="var(--muted)">mult</text>
  <rect x="45" y="70" width="70" height="12" fill="var(--acc-line)"/>
  <text x="20" y="96" font-family="var(--mono)" font-size="7" fill="var(--muted)">frac</text>
  <rect x="45" y="88" width="2" height="12" fill="var(--s2)"/>
  <text x="120" y="98" font-family="var(--mono)" font-size="7" fill="var(--s2)">0.00 -> fractions</text>
  <text x="70" y="132" font-family="var(--mono)" font-size="9" fill="var(--ink)">student Q</text>
  <text x="20" y="152" font-family="var(--mono)" font-size="7" fill="var(--muted)">add</text>
  <rect x="45" y="144" width="70" height="12" fill="var(--acc-line)"/>
  <text x="20" y="170" font-family="var(--mono)" font-size="7" fill="var(--muted)">mult</text>
  <rect x="45" y="162" width="2" height="12" fill="var(--s2)"/>
  <text x="120" y="172" font-family="var(--mono)" font-size="7" fill="var(--s2)">0.00 -> multiplication</text>
  <text x="20" y="188" font-family="var(--mono)" font-size="7" fill="var(--muted)">frac</text>
  <rect x="45" y="180" width="70" height="12" fill="var(--acc-line)"/>
</svg>
^ Item accuracy is 0.50 for both, but the per-skill bars separate them cleanly — P's only short bar is fractions, Q's is multiplication — which is the remediation target the single number could not name.

## Build

Reproduce the diagnosis. Pure standard library, deterministic, so the 0.50 accuracies and the 0.00 deficits come out exactly.

Run `--responses` for the item grid, `--components` for the per-skill rates and inferred deficit, `--check` for the gate. The self-test pins that the two students share one item accuracy but get different, correct diagnoses.

```python filename=modules/teaching-and-portability/code/teach-inter-14/components.py:100-105 COMPLETE
    same_item_accuracy = item_accuracy(items, students[p]) == item_accuracy(items, students[q])
    print("  the two students have identical item accuracy = %s (%.2f = %.2f)"
          % (same_item_accuracy, item_accuracy(items, students[p]), item_accuracy(items, students[q])))

    dp, dq = weakest(items, skills, students[p]), weakest(items, skills, students[q])
    different_deficits = dp != dq
    print("  the component analysis finds different deficits = %s (%s vs %s)" % (different_deficits, dp, dq))
```

```text filename=modules/teaching-and-portability/code/teach-inter-14/components.py --check
SELF-TEST — both students share one item accuracy but have different, correctly identified skill deficits
--------------------------------------------------------------------------------------------------------
  the two students have identical item accuracy = True (0.50 = 0.50)
  the component analysis finds different deficits = True (frac vs mult)
  each inferred deficit is the truly missing skill = True (P missing ['frac'], Q missing ['mult'])
  the missing skill sits at 0.00 success while others are higher = True
  the student's other skills are clearly above the deficit = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  same_item_accuracy=True  different_deficits=True  identifies_truth=True  deficit_is_zero=True  others_high=True
```

The diagnosis reduces to picking the lowest per-skill rate — one helper that turns the rate table into a single remediation target.

```python filename=modules/teaching-and-portability/code/teach-inter-14/components.py:59-62 COMPLETE
def weakest(items, skills, mastered):
    """The skill with the lowest success rate -- the one to remediate."""
    rates = component_rates(items, skills, mastered)
    return min(rates, key=lambda s: rates[s])
```

<svg role="img" aria-label="A grid: item accuracy is one column identical for both students; the per-skill columns differ, isolating each student's deficit" viewBox="0 0 470 165" width="470" height="165">
  <rect x="0" y="0" width="470" height="165" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">one item-accuracy column vs three skill columns</text>
  <text x="120" y="42" font-family="var(--mono)" font-size="8" fill="var(--ink)">item acc</text>
  <text x="210" y="42" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">add</text>
  <text x="280" y="42" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">mult</text>
  <text x="350" y="42" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">frac</text>
  <text x="20" y="80" font-family="var(--mono)" font-size="9" fill="var(--ink)">P</text>
  <text x="120" y="80" font-family="var(--mono)" font-size="9" fill="var(--muted)">0.50</text>
  <text x="210" y="80" font-family="var(--mono)" font-size="9" fill="var(--ink)">.67</text>
  <text x="280" y="80" font-family="var(--mono)" font-size="9" fill="var(--ink)">.67</text>
  <text x="350" y="80" font-family="var(--mono)" font-size="9" fill="var(--s2)">.00</text>
  <text x="20" y="120" font-family="var(--mono)" font-size="9" fill="var(--ink)">Q</text>
  <text x="120" y="120" font-family="var(--mono)" font-size="9" fill="var(--muted)">0.50</text>
  <text x="210" y="120" font-family="var(--mono)" font-size="9" fill="var(--ink)">.67</text>
  <text x="280" y="120" font-family="var(--mono)" font-size="9" fill="var(--s2)">.00</text>
  <text x="350" y="120" font-family="var(--mono)" font-size="9" fill="var(--ink)">.67</text>
  <line x1="160" y1="30" x2="160" y2="135" stroke="var(--line)" stroke-dasharray="3 3"/>
  <text x="120" y="150" font-family="var(--mono)" font-size="7" fill="var(--muted)">same</text>
  <text x="250" y="150" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">different — the deficit shows here</text>
</svg>
^ The item-accuracy column is 0.50 for both, but the skill columns diverge — P's zero is under frac, Q's under mult — so the single number the two share splits into two distinct diagnoses.

Five True flags. Same_item_accuracy: both students are at 0.50, indistinguishable by item score. Different_deficits: component analysis finds frac for P and mult for Q. Identifies_truth: each inferred deficit is the skill the student actually did not master — the diagnosis is correct, not just different. Deficit_is_zero and others_high: the missing skill sits at 0.00 while the others are clearly above it, so the deficit is unambiguous. The identifies-truth flag is the one that matters: component scoring does not merely produce two different numbers, it produces the two right diagnoses.

**The identifies-truth flag is the payoff — component scoring recovers each student's actually-missing skill from responses that item accuracy rendered identical, turning one uninformative number into two correct, actionable diagnoses.**

## Definition of done

You are done when you reproduce the identical item accuracy and the two distinct diagnoses, and can explain why one hides what the other shows.

Concretely: `--responses` shows both students at 0.50 with opposite miss patterns; `--components` shows P at frac 0.00 and Q at mult 0.00 with the rest at 0.67; `--check` prints PASS with five True flags including that each deficit matches the truly missing skill. You can explain that competence and remediation live at the skill level while items bundle skills, that item accuracy marginalizes over skills into a many-to-one blur, and that attribution works by looking across items that share a skill — the overlap in the item-skill map is what makes the deficit identifiable. You can connect this to knowledge tracing and the Q-matrix.

The habit to carry: tag items with their knowledge components and report per-skill mastery, not just an item score, whenever the goal is to decide what a learner should practice. When two learners with the same overall score clearly need different help, or when a tutor keeps assigning practice that does not fix the problem, suspect that scoring is happening at the item level and the actual deficit is a component the item score cannot see. Score the parts, not the bundle.

## Boss fight

The instructive failure is an adaptive tutor that keeps a student stuck because it remediates the item, not the skill.

A tutor tracks each student's percent-correct on multi-step algebra problems and, when it drops, assigns more problems of the same type. One student is stuck at 60% and not improving despite dozens of assigned problems, because the tutor never noticed that every missed problem shares one sub-skill — combining like terms — while the rest of each problem is fine. Re-serving whole problems makes the student re-practice the parts they already have and only incidentally the part they lack, so progress is slow and demoralizing. The fix is a Q-matrix: tag each problem with its sub-skills, track mastery per skill, and when combining-like-terms shows a low rate, assign targeted practice on that component alone. The student fixes the one broken skill in a fraction of the problems.

Your turn, two moves. First, add a student who has mastered only one skill and confirm component scoring still localizes the two deficits correctly, while item accuracy would lump this weaker student in with anyone else at the same percentage — the more skills involved, the more diagnoses one accuracy number hides. Second, add a slip: mark one item wrong even though the student has its skills (a careless error), and watch how it dents the affected skills' rates slightly without moving the true deficit off 0.00 — which is why real knowledge tracing models a slip probability, so a single careless miss is not mistaken for a missing skill.

## External resources

The cognitive-tutor literature (Anderson, Corbett, Koedinger, and Pelletier's "Cognitive Tutors: Lessons Learned") introduces knowledge-component modeling and the Q-matrix that maps items to skills, which is the framework this module distills.

Corbett and Anderson's "Knowledge Tracing" (1994) is the canonical model for estimating per-skill mastery from a stream of responses, including the slip and guess parameters that extend the deterministic model here.

Work on the Q-matrix and cognitive diagnosis models (Tatsuoka's rule-space method and later DINA/DINO models) formalizes inferring which skills a student has from responses to items with known skill requirements, which is the attribution step this module performs by success rate.
