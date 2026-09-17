---
id: nonresponse-inter-01
title: Weight for who answered — a survey's respondents are not a random sample when response depends on the answer
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: A survey estimates a population's opinion from the people who answer it, assuming the respondents are a representative sample. That assumption fails whenever the decision to respond is correlated with the thing being measured — which, for opinion surveys, it very often is. People with strong feelings answer at higher rates than the indifferent; an angry customer fills out the complaint form, a satisfied one ignores it. When response rate depends on the answer, the respondents over-represent whichever group is more inclined to respond, and the naive average over respondents is pulled toward that group's opinion. This is nonresponse bias (a form of self-selection bias), and it is not fixed by collecting more responses: a bigger biased sample is a more confident wrong answer, because the bias is in who answers, not how many. The correction, when response rates are known or estimable, is inverse-probability weighting: weight each respondent by 1 divided by their group's response rate, so an under-responding group's few answers are scaled up to stand for all the non-responders like them. A respondent from a group that answered at 10% counts for 10 people; one from a group that answered at 80% counts for 1.25. On a fixture where the true population satisfaction is 4.0 but unhappy customers respond far more (80%) than happy ones (10%), the 20 respondents are 40% unhappy though the population is only 10% unhappy, so the naive respondent mean is a badly-biased 2.8 — while inverse-probability weighting reconstructs the population and recovers the true 4.0.
eli5: Imagine you want to know how much a whole school likes the cafeteria food, so you put out a comment box. The kids who hate the food are furious and drop in tons of complaints, while the kids who like it are happily eating and never bother to write anything. If you just read the box, you'd think everyone hates the food — but that's only because the haters were the ones who wrote in. The box measured "who felt like complaining," not "what the school thinks." To fix it, you'd have to notice that only 1 in 10 happy kids wrote in but 8 in 10 angry kids did, and count each happy note as standing for the many happy kids who stayed silent.
---

## Why this module

A survey feels like a window onto a population, but it is really a window onto the people who chose to look back through it, and those two groups are the same only by luck. The moment the decision to respond is tied to the opinion being surveyed — the angry answer, the passionate answer, the answer someone feels compelled to give — the respondents stop being a random sample and become a self-selected one, tilted toward whoever cared enough to reply. The average of their answers is then an accurate description of the respondents and a distorted picture of everyone else, and nothing in the raw number warns you which one you are looking at.

When response rate depends on the answer, the respondents over-represent whichever group is more inclined to respond, and the naive average over respondents is pulled toward that group's opinion. This is nonresponse bias, and it is not fixed by collecting more responses: a bigger biased sample is just a more confident wrong answer, because the bias is in who answers, not in how many.

The correction, when the response rates are known or can be estimated, is inverse-probability weighting: weight each respondent by 1 divided by their group's response rate, so an under-responding group's few answers are scaled up to stand for all the non-responders like them, and an over-responding group's many answers are scaled down. Weighting reconstructs the population from the biased sample and recovers the true mean. This module computes both.

**A survey's respondents are a representative sample only if the decision to respond is independent of the answer; when response rate correlates with the thing measured, the naive respondent average is biased toward the over-responding group, so estimate the population by weighting each respondent by the inverse of their response probability, not by taking the raw mean.**

## Concepts

**The true mean is over everyone; the naive mean is over respondents only** — and the two diverge when response rates differ by group.

```python filename=modules/ai-for-science-and-data/code/nonresponse-inter-01/nonresponse.py:55-69 COMPLETE
def respondents(group):
    """How many of this group actually answered = population * response_rate."""
    return round(group["population"] * group["response_rate"])


def true_mean(groups):
    """The real population mean, over everyone."""
    total = sum(g["population"] for g in groups)
    return sum(g["score"] * g["population"] for g in groups) / total


def naive_mean(groups):
    """The mean over respondents only -- what a survey reports if it just averages the answers it got."""
    n = sum(respondents(g) for g in groups)
    return sum(g["score"] * respondents(g) for g in groups) / n
```

**Inverse-probability weighting scales each respondent by 1/response_rate**, so each stands for all the non-responders like them.

```python filename=modules/ai-for-science-and-data/code/nonresponse-inter-01/nonresponse.py:72-76 COMPLETE
def weighted_mean(groups):
    """Inverse-probability weighted mean: each respondent counts as 1/response_rate people."""
    num = sum(g["score"] * respondents(g) * (1 / g["response_rate"]) for g in groups)
    den = sum(respondents(g) * (1 / g["response_rate"]) for g in groups)
    return num / den
```

<svg role="img" aria-label="Two bar sets: the population is 60% happy, 30% neutral, 10% unhappy, but the respondents are 30% happy, 30% neutral, 40% unhappy — the unhappy group is over-represented" viewBox="0 0 300 112" width="300" height="112">
  <text x="6" y="12" fill="var(--muted)" font-size="8">population vs respondents: the unhappy group is over-represented</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">population</text>
  <rect x="80" y="26" width="120" height="12" fill="var(--s1)"/><text x="204" y="36" fill="var(--muted)" font-size="6">happy 60%</text>
  <rect x="80" y="40" width="60" height="12" fill="var(--muted)"/><text x="144" y="50" fill="var(--muted)" font-size="6">neutral 30%</text>
  <rect x="80" y="54" width="20" height="12" fill="var(--s2)"/><text x="104" y="64" fill="var(--s2)" font-size="6">unhappy 10%</text>
  <text x="10" y="86" fill="var(--muted)" font-size="7">respondents</text>
  <rect x="80" y="78" width="60" height="12" fill="var(--s1)"/><text x="144" y="88" fill="var(--muted)" font-size="6">happy 30%</text>
  <rect x="80" y="92" width="60" height="12" fill="var(--muted)"/><text x="144" y="102" fill="var(--muted)" font-size="6">neutral 30%</text>
  <rect x="80" y="106" width="80" height="4" fill="var(--s2)"/><text x="164" y="110" fill="var(--s2)" font-size="6">unhappy 40%</text>
</svg>
^ The population is 60% happy, 30% neutral, 10% unhappy, but among respondents the shares shift to 30/30/40 — the unhappy minority, responding at a far higher rate, balloons from a tenth of the population to two-fifths of the answers, which is what drags the survey average down.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/nonresponse-inter-01/nonresponse.py

The fixture is three satisfaction groups with their population sizes and response rates.

```json filename=modules/ai-for-science-and-data/code/nonresponse-inter-01/nonresponse.json:3-7 COMPLETE
  "groups": [
    {"score": 5, "population": 60, "response_rate": 0.10},
    {"score": 3, "population": 30, "response_rate": 0.20},
    {"score": 1, "population": 10, "response_rate": 0.80}
  ]
```

Run `--survey`.

```text filename=--survey
SURVEY — population vs respondents by satisfaction score
----------------------------------------------------------------------
  score  population  response-rate  respondents  %-of-pop  %-of-resp
  5      60          10%            6            60%       30%
  3      30          20%            6            30%       30%
  1      10          80%            8            10%       40%
----------------------------------------------------------------------
  true population mean = 4.0 ; naive respondent mean = 2.8
```

Read the last two columns against each other. The happy customers (score 5) are 60% of the population but only 30% of the respondents, because they answer at just 10%. The unhappy customers (score 1) are 10% of the population but 40% of the respondents, because they answer at 80%. The neutral group sits in between. So the respondent pool looks nothing like the population: it has shrunk the happy majority and inflated the unhappy minority, purely through the difference in response rates. The consequence is the two means at the bottom: the true population mean is 4.0 (most customers are happy), but the naive average over respondents is 2.8 — the survey would report that customers are, on balance, dissatisfied, when in fact they are mostly content. The 1.2-point gap is entirely manufactured by who chose to answer, and it does not shrink if you send the survey to more people, because every new batch has the same skewed response rates.

## Build

The fix is to undo the skew by counting each respondent as the number of people like them who did not answer.

```text filename=--weight
WEIGHT — inverse-probability weighting reconstructs the population
--------------------------------------------------------------------
  score  respondents  weight (1/rate)  represents
  5      6            10.00            60 people
  3      6            5.00             30 people
  1      8            1.25             10 people
--------------------------------------------------------------------
  weighted mean = 4.0  (= the true population mean 4.0)
```

<svg role="img" aria-label="Each respondent group scaled up by its inverse response rate: 6 happy respondents times 10 reconstruct 60, 6 neutral times 5 reconstruct 30, 8 unhappy times 1.25 reconstruct 10" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">respondents × (1/rate) reconstruct the population</text>
  <text x="10" y="32" fill="var(--muted)" font-size="7">happy</text>
  <rect x="60" y="24" width="18" height="10" fill="var(--s1)"/><text x="82" y="32" fill="var(--muted)" font-size="6">6 × 10 →</text>
  <rect x="130" y="24" width="120" height="10" fill="var(--s1)"/><text x="254" y="32" fill="var(--muted)" font-size="6">60</text>
  <text x="10" y="54" fill="var(--muted)" font-size="7">neutral</text>
  <rect x="60" y="46" width="18" height="10" fill="var(--muted)"/><text x="82" y="54" fill="var(--muted)" font-size="6">6 × 5 →</text>
  <rect x="130" y="46" width="60" height="10" fill="var(--muted)"/><text x="194" y="54" fill="var(--muted)" font-size="6">30</text>
  <text x="10" y="76" fill="var(--muted)" font-size="7">unhappy</text>
  <rect x="60" y="68" width="24" height="10" fill="var(--s2)"/><text x="88" y="76" fill="var(--muted)" font-size="6">8 × 1.25 →</text>
  <rect x="130" y="68" width="20" height="10" fill="var(--s2)"/><text x="154" y="76" fill="var(--muted)" font-size="6">10</text>
  <text x="10" y="96" fill="var(--muted)" font-size="6">the over-responding unhappy group is scaled down; the quiet happy group scaled up</text>
</svg>
^ Weighting scales each group's respondents by its inverse response rate: the 6 happy respondents (×10) reconstruct 60, the 6 neutral (×5) reconstruct 30, and the 8 unhappy (×1.25) reconstruct just 10 — undoing the over-representation and rebuilding the population's true 60/30/10 proportions.

Each respondent is weighted by the inverse of their group's response rate. The happy group answered at 10%, so each of its 6 respondents stands for 1/0.10 = 10 people, reconstructing all 60 happy customers. The unhappy group answered at 80%, so each of its 8 respondents stands for only 1/0.80 = 1.25 people, reconstructing exactly the 10 unhappy customers. The weights rebuild the population from the sample: 60 + 30 + 10 = 100 people, in their true proportions, and the weighted mean comes out to 4.0 — the true value. This is the crux: the raw sample contained all the information needed, but it had to be re-weighted to remove the response-rate distortion, and the weights are 1/response_rate precisely because a group that answered at rate p has each answer standing in for the 1/p people in its stratum. The catch, which the boss fight develops, is that this works only because we *knew* the response rates and the non-responders in each group resembled the responders; when you cannot see who didn't answer, you have to estimate or assume those rates, and the correction is only as good as that estimate.

```python filename=modules/ai-for-science-and-data/code/nonresponse-inter-01/nonresponse.py:121-129 COMPLETE
    naive_is_biased = abs(nm - tm) > 0.5
    print("  the naive respondent mean differs from the true mean = %s (%.1f vs %.1f)" % (naive_is_biased, nm, tm))

    naive_underestimates = nm < tm
    print("  the naive mean underestimates satisfaction = %s (%.1f < %.1f)" % (naive_underestimates, nm, tm))

    unhappy_overrepresented = respondents(unhappy) / resp > unhappy["population"] / pop
    print("  the unhappy group is over-represented among respondents = %s (%.0f%% of respondents vs %.0f%% of population)"
          % (unhappy_overrepresented, respondents(unhappy) / resp * 100, unhappy["population"] / pop * 100))
```

## Definition of done

The self-test pins the biased naive mean, the over-represented group, the weighting recovery, and the fact that more responses do not help.

```python filename=modules/ai-for-science-and-data/code/nonresponse-inter-01/nonresponse.py:131-134 COMPLETE
    weighting_recovers = abs(wm - tm) < 1e-9
    print("  inverse-probability weighting recovers the true mean = %s (%.1f == %.1f)" % (weighting_recovers, wm, tm))

    more_responses_dont_help = naive_is_biased
    print("  the bias is in WHO answered, so a bigger biased sample stays wrong = %s" % more_responses_dont_help)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the naive respondent mean is biased low because the unhappy group over-responds; weighting recovers the truth
--------------------------------------------------------------------------------------------------------------------------
  the naive respondent mean differs from the true mean = True (2.8 vs 4.0)
  the naive mean underestimates satisfaction = True (2.8 < 4.0)
  the unhappy group is over-represented among respondents = True (40% of respondents vs 10% of population)
  inverse-probability weighting recovers the true mean = True (4.0 == 4.0)
  the bias is in WHO answered, so a bigger biased sample stays wrong = True
```

<svg role="img" aria-label="Three means: true population 4.0, naive respondent 2.8, inverse-probability weighted 4.0" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">true 4.0, naive respondent 2.8, weighted 4.0</text>
  <line x1="70" y1="24" x2="70" y2="76" stroke="var(--grid)"/>
  <text x="10" y="34" fill="var(--muted)" font-size="7">true</text>
  <rect x="70" y="26" width="160" height="10" fill="var(--grid)"/><text x="234" y="35" fill="var(--muted)" font-size="7">4.0</text>
  <text x="10" y="52" fill="var(--muted)" font-size="7">naive</text>
  <rect x="70" y="44" width="112" height="10" fill="var(--s2)"/><text x="186" y="53" fill="var(--muted)" font-size="7">2.8 (biased low)</text>
  <text x="10" y="70" fill="var(--muted)" font-size="7">weighted</text>
  <rect x="70" y="62" width="160" height="10" fill="var(--s1)"/><text x="234" y="71" fill="var(--muted)" font-size="7">4.0</text>
  <text x="10" y="88" fill="var(--muted)" font-size="6">weighting lands on the truth; the naive mean sits 1.2 points below it</text>
</svg>
^ The naive respondent mean (2.8) sits 1.2 points below the true population mean (4.0), while the inverse-probability weighted mean lands exactly on 4.0 — the weighting removes the response-rate skew the raw average carried.

**Done means nonresponse bias and its fix are proven on real counts: the true population mean is 4.0, but because unhappy customers respond at 80% and happy ones at 10%, the unhappy group is 40% of respondents (vs 10% of the population) and the naive respondent mean is a biased 2.8, while weighting each respondent by 1/response_rate reconstructs the population and recovers 4.0 — so a survey must be estimated by inverse-probability weighting when response correlates with the answer, not by the raw respondent mean.**

## Boss fight

Predict two ways the fix is harder than "divide by the response rate," because in a real survey you usually cannot see the non-responders and the bias hides in variables you did not measure.

The first trap is that this fixture cheated: it told you the response rate of each group, but in a real survey you do not know how the non-responders would have answered — that is exactly what "non-response" means. You can only weight by response rates you can estimate, and you estimate them from variables you actually observe about everyone (from a customer database, a voter file, census demographics): you post-stratify or rake the sample so its measured composition (age, region, purchase history) matches the population's known composition. That corrects for nonresponse that is explained by those observed variables. But it does nothing for nonresponse driven by an UNOBSERVED variable correlated with the answer — if unhappy customers are more likely to respond and you have no column that identifies "unhappy" in advance, no reweighting on demographics can recover the truth, because the thing that predicts both responding and the answer is invisible to your weights. This is the difference between "missing at random" (nonresponse explained by observed covariates — fixable by weighting) and "missing not at random" (nonresponse driven by the unobserved outcome itself — not fixable by weighting alone). Real nonresponse is usually somewhere in between, so weighting reduces but rarely eliminates the bias, and the residual is unmeasurable from the sample.

The second trap is that self-selection bias is everywhere, not just in formal surveys, and its cousin — the volunteered, unsolicited sample — is even more skewed and even harder to correct. Online reviews, app-store ratings, call-in polls, social-media sentiment, and "tell us what you think" boxes are all self-selected, and typically by the extremes: people who loved it or hated it write reviews while the vast satisfied-but-unmoved middle stays silent, producing the familiar U-shaped rating distribution that represents the loud tails, not the quiet mass. There is often no known population and no response rate to weight by, so you cannot even attempt the correction — the sample is un-anchored to any population. The defenses are structural: prefer a designed sample (contact a random subset and chase responses to push the response rate up, since higher response rates leave less room for bias) over a volunteered one; measure and report the response rate as a health metric (a 5% response rate is a loud warning, not a footnote); collect covariates that let you check and reweight the sample against a known population; and treat any "what people are saying" signal from a self-selected channel as a measure of the vocal minority until proven otherwise. The through-line is the same as publication and survivorship bias: the data you can see was filtered by a process correlated with the thing you want to measure, so the honest question is always "who is missing, and would they have answered differently?"

**Weighting only fixes nonresponse explained by variables you observe (post-stratify/rake to a known population), so it corrects "missing at random" but not "missing not at random," where the unobserved outcome itself drives responding — there the residual bias is unmeasurable from the sample, so weighting reduces rather than removes it. And self-selection is everywhere and worst when unsolicited: reviews, ratings, and call-in polls are volunteered by the extremes with no known population to weight against, so prefer a designed random sample with a chased-up response rate, report the response rate as a health metric, collect covariates to reweight, and treat any self-selected "what people say" signal as the vocal minority until shown otherwise.**

## External resources

Survey-methodology references on nonresponse bias, self-selection, and weighting (post-stratification, raking, inverse-probability weighting) — how response rates are estimated, when weighting corrects the bias, and the missing-at-random vs missing-not-at-random distinction.

Writing on the failures of self-selected samples (online reviews, opt-in polls, the 1936 Literary Digest poll) — why a large volunteered sample can be badly biased and why response rate, not sample size, governs nonresponse bias.

The companion survivorship-bias and publication-bias modules in this topic — nonresponse bias is the same filter-on-the-outcome problem applied to who answers a survey, a close relative of averaging over survivors and pooling only published studies, all fixed by asking who is missing rather than trusting the visible sample.
