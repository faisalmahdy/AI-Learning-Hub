---
id: berkson-inter-01
title: Selecting on a collider invents a correlation — two independent traits look related the moment you condition on something they both cause
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: Two traits are genuinely unrelated in the population — a performer's skill and their looks, independent, knowing one tells you nothing about the other. Study a selected group, famous performers, and the two traits are correlated: the more skilled are less good-looking, the better-looking less skilled. The correlation is real in that data, it replicates, and it is entirely an artifact of who was let into the sample. This is Berkson's paradox, and the mechanism is selection on a collider — a variable two others both influence. Fame is a collider (both skill and looks cause it), and "famous performers" is the population conditioned on it; conditioning on a collider is exactly the operation that induces a dependence between its causes. The intuition is elimination: if fame requires skill OR looks, a famous performer who lacks skill must have looks (there was no other way in), so within the famous group low skill predicts high looks. The traits did not become related; the selection rule tied them together by dropping the one cell — low skill and low looks — where their independence was visible. It is dangerous because the correlation is stable and plausible: restrict a medical study to hospitalized patients (hospitalization is a collider) and unrelated diseases show up correlated; study only funded startups, admitted students, or churned users and you find relationships among the inputs that are absent in the population. On a fixture where skill and looks are independent (phi 0.0, a balanced 25/25/25/25 table), selecting the famous — skill OR looks, dropping only the low-low cell — makes them correlated at phi -0.5 in the subgroup, with P(looks | skill=0) jumping to 1.0 against 0.5 for skill=1.
eli5: Imagine dating is like a club you can only get into if you are either really funny or really good-looking (or both). Out in the whole world, being funny and being good-looking have nothing to do with each other — plenty of people are both, neither, or one but not the other. But inside the club, something strange happens: if you meet someone there who turns out not to be funny at all, you can bet they are good-looking, because that is the only way they could have gotten in. So inside the club it looks like funny people are less good-looking and vice versa — a rule that is completely false out in the world. Nothing about the people changed; the door policy quietly created the pattern by keeping out everyone who was neither.
---

## Why this module

A correlation you can measure, that replicates every time you re-run the study, feels like a fact about the world. Berkson's paradox is the reason that feeling is not safe: it produces correlations that are stable, replicable, and entirely manufactured by how the sample was chosen. The trap is worth internalizing because it does not look like a bias — the data are not fabricated, the statistics are computed correctly, and the effect is robust. It is a real correlation in a sample that was quietly selected in a way that guarantees it.

The setup is two traits that are independent in the population. Nothing links them; the value of one carries no information about the other. Then you study not the population but a subgroup selected by a rule that depends on both traits — famous performers (skill or looks got them there), hospitalized patients (many conditions land you in a hospital), funded startups (traction or a pedigreed team gets you funded). That selecting variable is a collider: two arrows point into it, one from each trait. And conditioning on a collider — restricting to those who cleared its threshold — is precisely the operation that creates a dependence between the things pointing into it.

The intuition is a process of elimination, and it is worth holding onto because it makes the paradox stop feeling paradoxical. This module takes two provably independent traits, selects on their collider, and measures the correlation before and after.

**When a sample is selected by a threshold on a variable that several traits jointly influence (a collider), do not read correlations among those traits in the sample as real — because conditioning on the collider induces a spurious association between its causes (a low value on one trait implies a high value on another just to clear the threshold), so the relationship is an artifact of selection, absent in the unconditioned population.**

## Concepts

The fixture is a population of 100 with two binary traits, skill and looks, arranged so they are exactly independent: all four cells hold 25 people, so each trait is 50/50 and the joint counts equal the product of the marginals. The selection rule is the collider: a person is "famous" if skill + looks meets the threshold of 1 — that is, skill OR looks.

```json filename=modules/ai-for-science-and-data/code/berkson-inter-01/berkson.json:11-17 COMPLETE
  "groups": [
    {"skill": 1, "looks": 1, "count": 25},
    {"skill": 1, "looks": 0, "count": 25},
    {"skill": 0, "looks": 1, "count": 25},
    {"skill": 0, "looks": 0, "count": 25}
  ],
  "admit_if_sum_at_least": 1
```

The measure of association is the phi correlation for a 2×2 table — the same idea as a Pearson correlation for two binary variables. It is the cross-product difference (skilled-and-attractive times unskilled-and-unattractive, minus the two off-diagonal cells) normalized by the four margins; zero means independent, negative means the traits move oppositely.

```python filename=modules/ai-for-science-and-data/code/berkson-inter-01/berkson.py:63-77 COMPLETE
def phi(groups):
    """Phi correlation for the 2x2 of skill by looks: (ad - bc) / sqrt of the four margins."""
    a = cell(groups, 1, 1)
    b = cell(groups, 1, 0)
    c = cell(groups, 0, 1)
    d = cell(groups, 0, 0)
    denom = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    if denom == 0:
        return 0.0
    val = (a * d - b * c) / denom
    return 0.0 if abs(val) < 1e-9 else val
```

Selecting on the collider is one line — keep the cells whose skill + looks clears the threshold — and it is the entire cause of the paradox. With threshold 1 it drops exactly one cell: the low-skill, low-looks group, the only people who are neither.

```python filename=modules/ai-for-science-and-data/code/berkson-inter-01/berkson.py:80-88 COMPLETE
def select(groups, threshold):
    """Keep only the cells whose skill + looks meets the collider threshold (fame = skill OR looks)."""
    return [g for g in groups if g["skill"] + g["looks"] >= threshold]


def p_looks_given_skill(groups, skill):
    """P(looks = 1 | skill) in whatever groups are passed."""
    total = cell(groups, skill, 1) + cell(groups, skill, 0)
    return cell(groups, skill, 1) / total if total else 0.0
```

<svg role="img" aria-label="A causal diagram: skill and looks each point an arrow into fame; a box around fame marks conditioning, with a dashed spurious link drawn back between skill and looks" viewBox="0 0 320 150">
  <text x="30" y="45" font-size="11" fill="var(--ink)">skill</text>
  <text x="250" y="45" font-size="11" fill="var(--ink)">looks</text>
  <rect x="130" y="105" width="60" height="26" fill="none" stroke="var(--ink)" stroke-width="2"/>
  <text x="140" y="122" font-size="11" fill="var(--ink)">fame</text>
  <text x="196" y="122" font-size="8" fill="var(--muted)">(selected on)</text>
  <line x1="45" y1="52" x2="140" y2="103" stroke="var(--s1)" stroke-width="1.5"/>
  <line x1="258" y1="52" x2="180" y2="103" stroke="var(--s2)" stroke-width="1.5"/>
  <path d="M 55 40 Q 150 20 250 40" fill="none" stroke="var(--muted)" stroke-width="1.3" stroke-dasharray="4 3"/>
  <text x="110" y="18" font-size="8.5" fill="var(--muted)">spurious link induced by conditioning on fame</text>
</svg>
^ Skill and looks each cause fame — fame is the collider where their arrows meet. Boxing fame (selecting on it) opens the dashed back-path between the two causes, which is the correlation Berkson's paradox measures.

**Conditioning on a collider is not a statistical mistake in the computation — the phi is correct — it is a mistake in reading a selected sample as if it were the population.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the cohort-selection step of a data analysis, reduced to a 2×2 population so every conditional and correlation is checkable by hand.

Run `--population` first: the full table, provably independent.

```text filename=berkson.py --population
           looks=0   looks=1
  skill=1    25        25
  skill=0    25        25
  P(looks=1 | skill=1) = 0.50 ; P(looks=1 | skill=0) = 0.50
  phi correlation = 0.00 (skill and looks are independent)
```

The conditional probability of good looks is 0.50 whether skill is high or low — that equality is the definition of independence, and the phi correlation confirms it at 0.00. In the population, knowing someone's skill tells you exactly nothing about their looks.

Now `--selected` conditions on the collider and recomputes.

```text filename=berkson.py --selected
           looks=0   looks=1
  skill=1    25        25
  skill=0    0         25
  the low-low cell is dropped: (skill 0, looks 0) = 25 people removed
  P(looks=1 | skill=1) = 0.50 ; P(looks=1 | skill=0) = 1.00
  phi correlation = -0.50 (skill and looks now negatively correlated -- an artifact)
```

One cell went to zero — the 25 people who were neither skilled nor good-looking are gone, because they never became famous. Look at what that does to the conditionals: among the famous, P(looks=1 | skill=1) is still 0.50, but P(looks=1 | skill=0) has jumped to 1.00. Every unskilled famous person is good-looking, because being good-looking was the only door they had. The phi correlation is now −0.50 where it was 0.00, and nothing about any individual changed — the door policy manufactured the correlation by removing the one group where independence showed.

<svg role="img" aria-label="Four bars of P(looks=1 given skill): in the population both are 0.5, in the famous subgroup skill=1 stays 0.5 but skill=0 jumps to 1.0" viewBox="0 0 330 140">
  <line x1="30" y1="110" x2="310" y2="110" stroke="var(--line)" stroke-width="1"/>
  <text x="10" y="40" font-size="8" fill="var(--muted)">1.0</text>
  <text x="10" y="113" font-size="8" fill="var(--muted)">0</text>
  <text x="40" y="128" font-size="8.5" fill="var(--muted)">population</text>
  <rect x="45" y="72" width="30" height="38" fill="var(--s1)"/>
  <text x="42" y="70" font-size="7.5" fill="var(--muted)">skill=1</text>
  <rect x="85" y="72" width="30" height="38" fill="var(--s1)"/>
  <text x="82" y="70" font-size="7.5" fill="var(--muted)">skill=0</text>
  <text x="200" y="128" font-size="8.5" fill="var(--muted)">famous</text>
  <rect x="200" y="72" width="30" height="38" fill="var(--s2)"/>
  <text x="197" y="70" font-size="7.5" fill="var(--muted)">skill=1</text>
  <rect x="240" y="35" width="30" height="75" fill="var(--s2)"/>
  <text x="237" y="33" font-size="7.5" fill="var(--muted)">skill=0</text>
  <text x="150" y="16" font-size="8.5" fill="var(--ink)">P(looks=1 | skill)</text>
</svg>
^ In the population the two bars are equal (0.5 = independence). Among the famous, skill=1 is unchanged at 0.5 but skill=0 rises to 1.0 — every unskilled famous person is good-looking, which is the negative correlation the phi reports.

**Dropping a single corner of the table — the people who cleared the threshold on neither trait — is enough to swing the correlation from 0.00 to −0.50; the sample is honest, the reading of it as a population fact is not.**

## Build

The self-test asserts the whole chain: the traits are independent in the population, the selection drops exactly the low-low cell, and the correlation appears only after conditioning. Asserting the population independence first is what makes the sample correlation provably an artifact rather than a real effect the sample happened to reveal.

```python filename=modules/ai-for-science-and-data/code/berkson-inter-01/berkson.py:104-119 COMPLETE
    phi_pop = phi(groups)
    independent_in_population = abs(phi_pop) < 1e-9
    print("  skill and looks are independent in the population = %s (phi = %.2f)" % (independent_in_population, phi_pop))

    pop_conditionals_equal = abs(p_looks_given_skill(groups, 1) - p_looks_given_skill(groups, 0)) < 1e-9
    print("  P(looks | skill) does not depend on skill in the population = %s (%.2f vs %.2f)"
          % (pop_conditionals_equal, p_looks_given_skill(groups, 1), p_looks_given_skill(groups, 0)))

    dropped = [g for g in groups if g["skill"] + g["looks"] < thr]
    selection_on_collider = len(dropped) == 1 and dropped[0]["skill"] == 0 and dropped[0]["looks"] == 0
    print("  selection on the collider drops exactly the low-low cell = %s" % selection_on_collider)

    phi_sel = phi(sel)
    spurious_negative_in_sample = phi_sel < 0
    print("  skill and looks are negatively correlated in the famous subgroup = %s (phi = %.2f)" % (spurious_negative_in_sample, phi_sel))
```

<svg role="img" aria-label="Two 2x2 grids: the population with all four cells filled and phi 0, and the selected subgroup with the low-low cell empty and phi negative 0.5" viewBox="0 0 330 140">
  <text x="20" y="20" font-size="9" fill="var(--muted)">population — phi 0.00</text>
  <rect x="20" y="30" width="40" height="40" fill="var(--s1)"/>
  <rect x="62" y="30" width="40" height="40" fill="var(--s1)"/>
  <rect x="20" y="72" width="40" height="40" fill="var(--s1)"/>
  <rect x="62" y="72" width="40" height="40" fill="var(--s1)"/>
  <text x="33" y="54" font-size="9" fill="var(--panel)">25</text>
  <text x="75" y="54" font-size="9" fill="var(--panel)">25</text>
  <text x="33" y="96" font-size="9" fill="var(--panel)">25</text>
  <text x="75" y="96" font-size="9" fill="var(--panel)">25</text>
  <text x="200" y="20" font-size="9" fill="var(--muted)">famous — phi -0.50</text>
  <rect x="200" y="30" width="40" height="40" fill="var(--s2)"/>
  <rect x="242" y="30" width="40" height="40" fill="var(--s2)"/>
  <rect x="200" y="72" width="40" height="40" fill="none" stroke="var(--line)" stroke-width="1.5" stroke-dasharray="3 2"/>
  <rect x="242" y="72" width="40" height="40" fill="var(--s2)"/>
  <text x="213" y="54" font-size="9" fill="var(--panel)">25</text>
  <text x="255" y="54" font-size="9" fill="var(--panel)">25</text>
  <text x="211" y="96" font-size="9" fill="var(--muted)">0</text>
  <text x="255" y="96" font-size="9" fill="var(--panel)">25</text>
  <text x="200" y="128" font-size="8" fill="var(--muted)">low-low cell removed by selection</text>
</svg>
^ The only difference between the two tables is the emptied low-low corner (dashed). That single removed cell is the entire cause of the correlation swinging from 0.00 to −0.50 — the paradox is one missing corner.

Running the check confirms every clause, including the elimination signature.

```text filename=berkson.py --check
  skill and looks are independent in the population = True (phi = 0.00)
  P(looks | skill) does not depend on skill in the population = True (0.50 vs 0.50)
  selection on the collider drops exactly the low-low cell = True
  skill and looks are negatively correlated in the famous subgroup = True (phi = -0.50)
  the sample correlation is absent in the population (an artifact) = True (-0.50 in sample vs 0.00 in population)
  in the subgroup, low skill implies higher looks (elimination) = True (1.00 > 0.50)
```

**The check proves independence in the population and correlation only after selection — so the −0.50 is demonstrably manufactured by the door policy, not discovered in the people.**

## Definition of done

Two properties close it. The correlation must be genuinely absent in the population and genuinely present in the selected sample — a difference in phi larger than any rounding — and the mechanism must show the elimination signature: in the subgroup, low skill implies higher looks, because clearing the threshold on one trait is the only way the low-on-the-other survivors got in.

```python filename=modules/ai-for-science-and-data/code/berkson-inter-01/berkson.py:121-127 COMPLETE
    correlation_is_artifact = abs(phi_sel - phi_pop) > 0.4
    print("  the sample correlation is absent in the population (an artifact) = %s (%.2f in sample vs %.2f in population)"
          % (correlation_is_artifact, phi_sel, phi_pop))

    low_skill_implies_looks = p_looks_given_skill(sel, 0) > p_looks_given_skill(sel, 1)
    print("  in the subgroup, low skill implies higher looks (elimination) = %s (%.2f > %.2f)"
          % (low_skill_implies_looks, p_looks_given_skill(sel, 0), p_looks_given_skill(sel, 1)))
```

The direction of the induced correlation is worth stating so the tool is not mis-generalized. Selecting on an OR-style collider (fame from skill or looks) induces a negative correlation among the causes. The sign can flip with the selection rule: conditioning on a collider can create positive or negative associations depending on how the threshold combines the inputs, and conditioning on a common effect's descendant does it too. The invariant is not the sign but the origin — the association is created by the conditioning and does not exist in the unconditioned population. The remedy is never a cleverer statistic on the selected sample; it is recognizing that the sample was defined by a collider and refusing to read its internal correlations as population relationships, or going back to an unselected sample.

**Done means the correlation is provably absent in the population and present only after collider selection, with the elimination signature visible — an association manufactured by conditioning, not a fact about the people.**

## Boss fight

A hospital study finds that among admitted patients, having diabetes is associated with a lower rate of a particular cancer — a protective effect that makes headlines. The data are clean, the sample is large, and the association is strong and replicable across the hospital's records. Before anyone designs a drug trial, what is the one question you would ask about the sample, and how would you show whether the protective effect is real or a Berkson artifact?

The question is: what got these patients into the sample — is admission (hospitalization) a collider that both diabetes and this cancer influence? It almost certainly is: both conditions independently raise the chance of being hospitalized, so "admitted patients" is the population conditioned on a collider they both point into. That is the exact setup for a spurious association, and the direction — a protective-looking negative correlation — is what selecting on an OR-style collider produces: an admitted patient without the cancer is more likely to have been admitted for something else, like diabetes, so within the admitted group the two look inversely related. To show whether it is real, you leave the collider-selected sample: measure the diabetes–cancer association in the general population, not among the hospitalized — a community cohort or registry that was not selected on admission. If the association vanishes (or reverses) in the unconditioned population, it was a Berkson artifact of studying hospital patients; if it persists in a sample not selected on the collider, it is worth investigating. No reweighting of the admitted sample fixes this, because the information needed — the people who were never admitted — is not in it.

## External resources

Joseph Berkson's original 1946 note ("Limitations of the Application of Fourfold Table Analysis to Hospital Data") — the short paper that first described the hospital-admission artifact this module models, still the cleanest statement of the trap.

Judea Pearl and Dana Mackenzie, *The Book of Why*, the chapter on colliders and the "explaining away" effect — the modern causal-graph account of why conditioning on a collider opens a spurious path between its causes, with the celebrity talent-and-looks example used here worked through in detail.
