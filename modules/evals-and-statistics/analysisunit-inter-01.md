---
id: analysisunit-inter-01
title: Analyze a ratio metric at the randomization unit, not the impression — pooling correlated impressions understates the variance and fakes significance
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: A rate metric — click-through rate, conversion rate, any total-over-total — is a ratio, and the tempting test pools every impression across all users, treats each as an independent coin flip, and uses the binomial standard error sqrt(p(1−p)/N) with N the impression count, which is enormous, so the standard error is tiny and almost any difference looks significant. The formula is right for independent trials and wrong here, because the experiment randomized users, not impressions, and a user's impressions are strongly correlated: some users click nearly everything, others click nothing, so a hundred impressions from one user carry far less information than a hundred from a hundred different users. The independent unit — the thing randomly assigned to an arm — is the user, so the true sample size is the user count, smaller by the impressions-per-user factor, and treating impressions as independent inflates the effective sample size by that factor, shrinks the standard error, and turns a difference well inside the noise into a confident "significant" result. The correct analysis respects the randomization unit: compute the metric per user and treat each user's value as one observation, so the standard error reflects how much users actually vary (or use the delta method to get the ratio's variance from per-user totals). On a fixture where both arms have four users of a hundred impressions each and a CTR difference of 0.25, the impression-level analysis reports SE 0.033 and z = 7.6 (wildly significant) while the user-level analysis reports SE 0.38 and z = 0.65 (not significant).
eli5: Imagine testing whether a new poster makes people clap more. You show it to 4 people, but each person walks past it 100 times, and you count every walk-past as a separate "vote." Two of your 4 people love it and clap every single time (200 claps), the others never clap. If you treat all 400 walk-passes as 400 independent people, it looks like a huge, rock-solid result. But really you only asked 4 people — and people are all-or-nothing, so you basically have 4 opinions, not 400. With only 4 opinions, two happening to be clappers could easily be luck. The honest way is to count each person once, not each walk-past, and then the "sure thing" turns out to be noise.
---

## Why this module

The unit of analysis is the quietest assumption in an experiment and one of the most consequential. When you compute a rate by pooling — total clicks over total impressions — and then reach for the standard binomial standard error, you have silently declared that every impression is an independent trial. That declaration sets your sample size to the number of impressions, which is huge, and a huge sample size makes the standard error tiny and almost everything significant. The arithmetic is impeccable; the premise is false.

It is false because the experiment did not randomly assign impressions to arms — it assigned users, and then those users generated impressions. Impressions from the same user are not independent draws: a user has a propensity to click that governs all their impressions at once, so their hundred impressions move together, not separately. The information in the data is carried by how many independent users you have and how much they vary, not by how many impressions those users happened to generate. Counting impressions as independent inflates your effective sample size by the impressions-per-user ratio and correspondingly shrinks the standard error you report.

The consequence is false confidence: a difference that is ordinary user-to-user noise gets stamped "highly significant." This module computes the same CTR difference two ways — pooling impressions and respecting users — and watches the verdict flip.

**A ratio metric's impressions are correlated within a user, so pooling them as independent trials sets the sample size to the impression count and understates the variance — inflating significance; the metric must be analyzed at the randomization unit, the user, whose count is the real sample size.**

## Concepts

The fixture is two arms, each four users of a hundred impressions, with the clicks each user produced. The users are deliberately all-or-nothing clickers — the extreme of within-user correlation.

```json filename=modules/evals-and-statistics/code/analysisunit-inter-01/analysisunit.json:3-6 COMPLETE
  "arms": {
    "A": [[100, 100], [100, 100], [100, 0], [100, 0]],
    "B": [[100, 100], [100, 0], [100, 0], [100, 0]]
  }
```

Two standard errors. The naive one is the binomial SE with N set to the impression count — the impression-level analysis. The correct one is the SE of the mean of per-user rates, with N the number of users — the user-level analysis. A helper combines two arms' SEs for the difference.

```python filename=modules/evals-and-statistics/code/analysisunit-inter-01/analysisunit.py:33-58 COMPLETE
def pooled_ctr(arm):
    clicks = sum(k for _, k in arm)
    impressions = sum(i for i, _ in arm)
    return clicks / impressions, impressions


def naive_se(arm):
    """Impression-level: binomial SE with N = number of impressions (trials assumed independent)."""
    p, n = pooled_ctr(arm)
    return math.sqrt(p * (1 - p) / n)


def user_rates(arm):
    return [k / i for i, k in arm]


def user_se(arm):
    """User-level: SE of the mean of per-user rates, with N = number of users."""
    rates = user_rates(arm)
    m = sum(rates) / len(rates)
    var = sum((x - m) ** 2 for x in rates) / (len(rates) - 1)
    return math.sqrt(var / len(rates))


def combine(a, b):
    return math.sqrt(a * a + b * b)
```

`naive_se` divides by the impression count (400 per arm); `user_se` divides by the user count (4). That factor-of-100 difference in N is the whole error, showing up as a factor-of-10 difference in the standard error.

<svg role="img" aria-label="Two views of arm A: 400 impressions treated as independent dots giving a tiny error bar, versus 4 users each all-or-nothing giving a wide error bar" viewBox="0 0 320 120">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">what counts as one independent observation?</text>
  <text x="14" y="36" font-size="8" fill="var(--s2)">impression view: N=400</text>
  <line x1="150" y1="32" x2="170" y2="32" stroke="var(--s2)" stroke-width="2"/><text x="176" y="35" font-size="7.5" fill="var(--s2)">SE 0.03 (tiny)</text>
  <text x="14" y="64" font-size="8" fill="var(--s1)">user view: N=4</text>
  <line x1="150" y1="60" x2="270" y2="60" stroke="var(--s1)" stroke-width="2"/><text x="176" y="74" font-size="7.5" fill="var(--s1)">SE 0.38 (wide)</text>
  <text x="14" y="96" font-size="7.5" fill="var(--ink)">the 100 impressions per user are one propensity, not 100 trials</text>
  <text x="14" y="110" font-size="7.5" fill="var(--muted)">dividing by 400 instead of 4 shrinks the error bar tenfold</text>
</svg>
^ The impression view treats 400 correlated impressions as 400 independent observations and gets a tiny error bar; the user view recognizes 4 independent users and gets a wide one. The 100 impressions per user reflect one clicking propensity, not a hundred separate trials, so dividing by 400 rather than 4 understates the uncertainty by an order of magnitude.

**The naive SE divides by the impression count and the correct SE by the user count — the same ratio metric, but one treats correlated impressions as independent and the other counts the users that were actually randomized.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the significance-test step of an A/B analysis, reduced to four users per arm so every rate is checkable by hand.

Run `--arms` to see the per-user rates.

```text filename=analysisunit.py --arms
  arm A: 4 users, per-user CTR [1.0, 1.0, 0.0, 0.0], pooled CTR 0.50 (400 impressions)
  arm B: 4 users, per-user CTR [1.0, 0.0, 0.0, 0.0], pooled CTR 0.25 (400 impressions)
```

Arm A has two users who click every time and two who never click; arm B has one clicker and three who never do. The pooled CTRs are 0.50 and 0.25 — a 0.25 difference. But look at the per-user rates: they are all 1.0 or 0.0, pure all-or-nothing. That is maximal within-user correlation — a user's hundred impressions tell you their one propensity and nothing more — so the 400 impressions per arm are really just 4 pieces of information each.

Now `--test` combines each arm's standard error both ways and forms the z-scores.

```python filename=modules/evals-and-statistics/code/analysisunit-inter-01/analysisunit.py:77-79 COMPLETE
    diff = pA - pB
    n_se = combine(naive_se(A), naive_se(B))
    u_se = combine(user_se(A), user_se(B))
```

The two standard errors are an order of magnitude apart.

```text filename=analysisunit.py --test
  CTR difference (A - B)                = 0.25
  impression-level: SE 0.0331, z = 7.56, significant = True
  user-level:       SE 0.3819, z = 0.65, significant = False
```

The impression-level analysis reports a standard error of 0.033 and z = 7.56 — a result so significant it would never be questioned. The user-level analysis reports a standard error of 0.38 and z = 0.65 — not remotely significant. The difference in CTR is identical; only the assumed sample size changed. With four users per arm, "two clickers versus one clicker" is exactly the kind of split that happens by chance all the time, and the user-level test correctly says so, while the impression-level test, fooled into thinking it has 400 independent data points, calls random noise a discovery.

<svg role="img" aria-label="Two z-scores for the same 0.25 CTR difference: impression-level z of 7.6 far past the significance line, user-level z of 0.65 well short of it" viewBox="0 0 320 110">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">z-score for the same CTR difference (significance at z=1.96)</text>
  <line x1="70" y1="22" x2="70" y2="92" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 3"/><text x="56" y="104" font-size="7" fill="var(--ink)">1.96</text>
  <text x="10" y="42" font-size="8" fill="var(--s2)">impression</text>
  <rect x="30" y="32" width="240" height="14" fill="var(--s2)"/><text x="274" y="43" font-size="8" fill="var(--s2)">7.6</text>
  <text x="10" y="72" font-size="8" fill="var(--s1)">user</text>
  <rect x="30" y="62" width="20" height="14" fill="var(--s1)"/><text x="54" y="73" font-size="8" fill="var(--s1)">0.65</text>
  <text x="10" y="100" font-size="7.5" fill="var(--muted)">impression-level sails past the threshold; user-level falls far short</text>
</svg>
^ The identical 0.25 CTR difference gives z = 7.6 at the impression level — far past the 1.96 significance line — and z = 0.65 at the user level, well short of it. The analysis unit alone moves the verdict from a certain discovery to ordinary noise.

**The same 0.25 CTR difference is z = 7.56 (significant) by impression and z = 0.65 (noise) by user — the impression-level SE of 0.033 is tenfold too small because it counted 400 correlated impressions as independent instead of 4 users.**

## Build

The self-test establishes the correlation and its effect: users are all-or-nothing clickers, so the impression-level SE comes out smaller than the user-level SE and the impression-level test reads as significant.

```python filename=modules/evals-and-statistics/code/analysisunit-inter-01/analysisunit.py:98-105 COMPLETE
    within_user_correlated = any(r in (0.0, 1.0) for r in user_rates(A) + user_rates(B))
    print("  users are all-or-nothing clickers (impressions correlated within a user) = %s" % within_user_correlated)

    naive_se_smaller = n_se < u_se
    print("  the impression-level SE is smaller than the user-level SE = %s (%.4f < %.4f)" % (naive_se_smaller, n_se, u_se))

    naive_significant = n_z > 1.96
    print("  the impression-level test is 'significant' = %s (z=%.2f)" % (naive_significant, n_z))
```

Then the correction and the punchline: the user-level test is not significant, so the choice of analysis unit alone flips the conclusion.

```python filename=modules/evals-and-statistics/code/analysisunit-inter-01/analysisunit.py:107-110 COMPLETE
    user_not_significant = u_z < 1.96
    print("  the user-level test is NOT significant = %s (z=%.2f)" % (user_not_significant, u_z))

    conclusion_flips = naive_significant and user_not_significant
    print("  the analysis unit flips the conclusion = %s" % conclusion_flips)
```

Running the check confirms every clause.

```text filename=analysisunit.py --check
  users are all-or-nothing clickers (impressions correlated within a user) = True
  the impression-level SE is smaller than the user-level SE = True (0.0331 < 0.3819)
  the impression-level test is 'significant' = True (z=7.56)
  the user-level test is NOT significant = True (z=0.65)
  the analysis unit flips the conclusion = True
```

**The check ties the false significance to counting correlated impressions as independent — a tenfold-too-small SE — and shows the user-level analysis returning the honest verdict, the conclusion turning on the analysis unit alone.**

## Definition of done

Done means the impression-level analysis is shown to understate the SE and manufacture significance while the user-level analysis does not, with the within-user correlation identified as the cause. The clause that the conclusion flips is the whole stakes: this is not a small variance correction but the difference between shipping a feature on a phantom result and correctly seeing there is no evidence.

Two clarifications generalize it. First, the all-or-nothing users here are the extreme case, chosen so the effect is stark; real users are only partly correlated, so the inflation is smaller than tenfold but always present and always in the same direction — the impression-level SE is too small whenever impressions cluster within users, which is essentially always. The size of the error grows with the impressions-per-user ratio and with how much users differ in their rates, and it never helps you; it only ever fabricates confidence. Second, the per-user-rate analysis shown here is the simplest correct method, and it is exact when every user has the same number of impressions; when denominators vary across users, the honest analyses are the delta method (which computes the ratio's variance from the per-user numerator and denominator totals and their covariance) or the cluster-robust / bootstrap-over-users approaches, all of which take the user as the unit. The principle behind all of them is one sentence: the standard error must be computed over the units that were randomized, because those are the independent draws — analyzing at a finer grain than the randomization unit always understates uncertainty.

<svg role="img" aria-label="A rule: randomize by user, analyze by user; correct methods are per-user rate, delta method, or cluster bootstrap; analyzing per impression understates variance" viewBox="0 0 320 118">
  <rect x="14" y="22" width="150" height="40" fill="none" stroke="var(--s1)"/>
  <text x="22" y="37" font-size="7.5" fill="var(--s1)">randomized by user</text>
  <text x="22" y="49" font-size="7" fill="var(--ink)">→ analyze by user:</text>
  <text x="22" y="58" font-size="7" fill="var(--ink)">per-user rate / delta / bootstrap</text>
  <rect x="176" y="22" width="130" height="40" fill="none" stroke="var(--s2)"/>
  <text x="184" y="37" font-size="7.5" fill="var(--s2)">analyze by impression</text>
  <text x="184" y="49" font-size="7" fill="var(--ink)">SE too small,</text>
  <text x="184" y="58" font-size="7" fill="var(--ink)">always inflates significance</text>
  <text x="14" y="84" font-size="7.5" fill="var(--muted)">the SE must be computed over the units that were randomized</text>
  <text x="14" y="104" font-size="7.5" fill="var(--ink)">finer-than-randomization-unit analysis always understates uncertainty</text>
</svg>
^ Randomize by user, analyze by user — via the per-user rate, the delta method, or a cluster bootstrap over users. Analyzing at the impression level always understates the variance and inflates significance, because the standard error must be computed over the units that were actually randomized.

**Done means the impression-level analysis fabricates significance the user-level analysis refutes, from within-user correlation — so a ratio metric is analyzed at the randomization unit (per-user rate, delta method, or cluster bootstrap), never at a finer grain that understates uncertainty.**

## Boss fight

A team A/B tests a new feed ranking and reports that it lifts click-through rate with p < 0.0001, computed by pooling all impressions in each arm and running a proportion test on the pooled clicks and impressions. A skeptic points out that a handful of power users generate most of the impressions. Should the team trust the result, and how should they analyze it?

The team should not trust the result as computed: the pooled-impression proportion test uses the number of impressions as its sample size, which assumes every impression is an independent trial, and that assumption is false because the experiment randomized users, not impressions. Impressions from the same user are correlated — a user has a browsing and clicking propensity that governs all their impressions together — so the true number of independent observations is the number of users, not impressions. Pooling impressions inflates the effective sample size by the impressions-per-user ratio, which the skeptic's observation makes severe: if a handful of power users generate most impressions, the data is dominated by a few correlated clusters, and the pooled test's tiny p-value reflects a sample size the experiment does not actually have. The p < 0.0001 is very likely manufactured by this variance understatement. To analyze it correctly, take the user as the unit: compute each user's click-through rate and run the test on the per-user rates (a t-test on per-user CTRs between arms), or, because users have different impression counts, use the delta method to get the ratio metric's variance from the per-user click and impression totals, or a cluster bootstrap resampling users. All of these will produce a larger, honest standard error and a p-value that reflects the real number of independent units. The team should rerun with a user-level analysis and only trust the lift if it survives; if the power users are driving both the impressions and the apparent effect, the user-level test will likely show the result is far weaker or not significant. The general rule: always analyze at the unit you randomized, because that is where the independence assumption holds, and a metric computed at a finer grain than the randomization unit will always understate its uncertainty.

## External resources

The experimentation literature on the analysis unit and ratio metrics (Deng et al. and the Microsoft/experimentation-platform treatments of the delta method for ratio metrics, and the "randomization unit vs analysis unit" discussion in Kohavi, Tang, and Xu) — why per-impression variance is wrong for user-randomized experiments and the delta-method and cluster-robust corrections.

Statistical background on clustered/correlated data (the design effect and intraclass correlation, cluster-robust standard errors, and the cluster bootstrap) — the general reason that analyzing correlated observations as independent understates variance, and the standard methods for computing standard errors over the clustering (randomization) unit.
