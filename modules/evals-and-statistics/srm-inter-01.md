---
id: srm-inter-01
title: Check the A/B split ratio before trusting any metric — a sample ratio mismatch means the randomization is broken
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: Every A/B experiment starts with an intended split — usually 50/50 — and a randomizer that should send each unit to an arm with that probability. Almost nobody checks that the split actually came out as intended, which is a mistake, because when the observed split is meaningfully off (5200 vs 4800 when you asked for 5000/5000) something in the pipeline is broken: a redirect dropping users before assignment, a bot filter removing one arm's traffic unevenly, a logging join losing rows. This is a Sample Ratio Mismatch (SRM), and its consequence is severe — if the arms were not populated by the fair coin you assumed, the groups are not exchangeable, so any difference you measure, however significant, may be an artifact of the broken assignment rather than the treatment. The check is a chi-square goodness-of-fit test on the assignment counts alone. A 52/48 split looks fine to the eye but at 10,000 units the standard error of a count is sqrt(10000·0.25)=50, so 200 off from 5000 is 4 standard errors — a roughly 1-in-16,000 event under fair randomization. Because a true SRM should almost never happen by chance, the alarm threshold is strict (p<0.001). On a fixture of two experiments, the healthy split (5030/4970, 0.6 SE off, p≈0.55) passes and the broken split (5200/4800, 4 SE off, chi-square 16, p≈0.00006) trips the guard, so its metric must not be trusted.
eli5: Before you compare two teams, you promised to split the players evenly — 50 on each side. If you count afterward and find 52 on one side and 48 on the other, that's suspicious: a fair coin flip for 100 players almost never lands that lopsided, so somebody must have been miscounted or sent to the wrong side. And if the teams weren't split fairly to begin with, then whichever team "wins" tells you nothing — maybe they only won because they secretly got the better players. So you check the head count first, and if it's off, you throw the game out and fix the sorting hat before you trust any score.
---

## Why this module

The first number to check in an A/B test is not the metric — it is the head count in each arm. Everyone jumps straight to "did B beat A?" and reads a p-value on the metric, on the unspoken assumption that the two groups were populated by a fair coin so they are comparable. If that assumption is quietly false — if the assignment or the logging dropped units unevenly between the arms — then the groups are not comparable, and the metric's p-value is measuring a difference between two populations that were never exchangeable to begin with. The dangerous part is that a broken split does not announce itself; the metric still computes, still gets a confidence interval, still looks like a result.

Almost nobody checks that the split came out as intended, and that is a mistake, because a meaningfully off split (5200 in one arm, 4800 in the other, when you asked for 5000/5000) means something in the pipeline is broken: a redirect that drops some users before assignment, a bot filter that removes one arm's traffic unevenly, a logging join that loses rows. This is a Sample Ratio Mismatch (SRM), and its consequence is that the arms are not exchangeable — so any difference you measure between them, however large, however statistically significant, may be an artifact of the broken assignment rather than the treatment.

The check is a chi-square goodness-of-fit test on the assignment counts alone. A "52/48" split that looks fine to the eye is alarming at scale: at 10,000 units the standard error of a count is sqrt(10000·0.25)=50, so being 200 off from 5000 is 4 standard errors, a roughly 1-in-16,000 event under fair randomization. Because a true SRM should almost never happen by chance, the alarm threshold is strict (p<0.001), so firing it is strong evidence of a real bug. This module runs the guard on a healthy split and a broken one.

**Before reading any A/B metric, test the arm counts against the intended split with a chi-square goodness-of-fit test, and if the split is off beyond a strict threshold (p<0.001), treat the experiment as invalid — a sample ratio mismatch means the groups are not exchangeable, so no downstream comparison can be trusted, and "the split looks close enough" is exactly the intuition that scale defeats.**

## Concepts

**The SRM test works on the assignment counts, not the metric:** a chi-square goodness-of-fit statistic measures how far the observed split is from the expected one, and its p-value says how surprising that is under fair randomization.

```python filename=modules/evals-and-statistics/code/srm-inter-01/srm.py:50-68 COMPLETE
def chi_square_stat(a, b, p_a):
    """Goodness-of-fit chi-square (df=1) of the split (a, b) against the intended fraction p_a for arm A."""
    n = a + b
    exp_a = n * p_a
    exp_b = n * (1.0 - p_a)
    return (a - exp_a) ** 2 / exp_a + (b - exp_b) ** 2 / exp_b


def chi_square_p_df1(chi2):
    """Upper-tail p-value of a chi-square statistic with 1 degree of freedom, via the complementary error function."""
    return math.erfc(math.sqrt(chi2 / 2.0))


def standard_errors_off(a, b, p_a):
    """How many standard errors arm A's count is from its expected count (the z behind the chi-square)."""
    n = a + b
    exp_a = n * p_a
    se = math.sqrt(n * p_a * (1.0 - p_a))
    return (a - exp_a) / se
```

**One evaluation per experiment** bundles the statistic, the p-value, the standard-errors-off, and the pass/fail verdict against the strict threshold.

```python filename=modules/evals-and-statistics/code/srm-inter-01/srm.py:71-78 COMPLETE
def evaluate(exp, p_a, threshold):
    a, b = exp["a"], exp["b"]
    chi2 = chi_square_stat(a, b, p_a)
    p = chi_square_p_df1(chi2)
    return {
        "name": exp["name"], "a": a, "b": b, "exp_a": (a + b) * p_a, "exp_b": (a + b) * (1 - p_a),
        "chi2": chi2, "p": p, "z": standard_errors_off(a, b, p_a), "srm": p < threshold,
    }
```

<svg role="img" aria-label="A distribution of the split count under fair randomization centered at 5000 with a standard error of 50: the healthy split at 5030 sits near the center, the broken split at 5200 sits far out in the tail past 4 standard errors" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">fair-coin distribution of arm A's count (center 5000, SE 50)</text>
  <path d="M30 90 Q90 90 120 40 Q150 20 180 40 Q210 90 270 90" fill="none" stroke="var(--grid)"/>
  <line x1="150" y1="30" x2="150" y2="92" stroke="var(--line)"/><text x="138" y="104" fill="var(--muted)" font-size="6">5000</text>
  <circle cx="159" cy="90" r="3" fill="var(--s1)"/><text x="150" y="24" fill="var(--s1)" font-size="6">healthy 5030 (0.6 SE)</text>
  <circle cx="260" cy="90" r="3" fill="var(--s2)"/><text x="214" y="80" fill="var(--s2)" font-size="6">broken 5200</text>
  <text x="222" y="90" fill="var(--s2)" font-size="6">(4 SE)</text>
  <line x1="250" y1="70" x2="250" y2="92" stroke="var(--line)" stroke-dasharray="1 2"/><text x="238" y="104" fill="var(--muted)" font-size="6">5200</text>
  <text x="14" y="116" fill="var(--muted)" font-size="6">0.6 SE off is an ordinary wobble; 4 SE off is a ~1-in-16000 fluke → SRM</text>
</svg>
^ Under fair randomization arm A's count is distributed around 5000 with a standard error of 50; the healthy split (5030) sits 0.6 SE from center, an ordinary wobble, while the broken split (5200) is 4 SE out in the tail — a deviation so unlikely by chance that it signals a broken pipeline.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/srm-inter-01/srm.py

The fixture is two experiments, both intended 50/50, with their observed arm counts.

```json filename=modules/evals-and-statistics/code/srm-inter-01/srm.json:3-8 COMPLETE
  "expected_fraction": 0.5,
  "srm_threshold": 0.001,
  "experiments": [
    {"name": "healthy", "a": 5030, "b": 4970},
    {"name": "broken", "a": 5200, "b": 4800}
  ]
```

Run `--split`.

```text filename=--split
SPLIT — observed vs intended (50/50) assignment; SRM alarm at p < 0.001
------------------------------------------------------------------------------
  experiment  arm A / arm B   expected      chi-square   p-value     SRM?
  healthy      5030 / 4970    5000 / 5000   0.36        0.54851     ok
  broken       5200 / 4800    5000 / 5000   16          6.3342e-05  SRM! invalid
------------------------------------------------------------------------------
  a tripped SRM means the arms are not exchangeable, so the metric cannot be trusted at all.
```

Read the two rows. The healthy experiment split 5030/4970 against an expected 5000/5000; its chi-square statistic is 0.36 and the p-value is 0.55, so the deviation is exactly the kind of wobble a fair coin produces all the time — the guard passes and you may go on to read the metric. The broken experiment split 5200/4800; its chi-square is 16 and the p-value is 0.00006, far below the 0.001 alarm, so the guard fires: SRM, invalid. Note what the verdict does *not* depend on — the metric. The SRM check never looked at whether B beat A; it looked only at whether the two groups were populated as intended. Because the broken experiment's groups were not, its metric is untrustworthy no matter what it says, and reporting "B won, p<0.05" from that experiment would be reporting an artifact of whatever broke the assignment.

## Build

Why does 5200/4800 — which the eye reads as "basically even" — fail so hard? Scale.

```text filename=--why
WHY — '5200/4800 looks close' fails because the standard error of the count is tiny at this scale
----------------------------------------------------------------------------
  healthy  N=10000  expected A=5000  observed A=5030  off by +30  = 0.6 standard errors (SE=50)
  broken   N=10000  expected A=5000  observed A=5200  off by +200  = 4.0 standard errors (SE=50)
----------------------------------------------------------------------------
  the eye reads 52% vs 50% as 'about the same'; at N=10000 it is 4 SE, a ~1-in-16000 fluke.
```

The intuition that "52% is close to 50%" ignores the sample size, and sample size is the whole story. The standard error of the count in one arm is sqrt(N·p·(1−p)) = sqrt(10000·0.25) = 50. So the healthy split's +30 is 0.6 standard errors — deep inside the range fair randomization visits constantly — while the broken split's +200 is 4.0 standard errors, and a 4-sigma deviation happens by chance about once in 16,000 times. The percentage framing hides this because it does not scale with N: 52% feels the same whether it comes from 100 units or 10,000, but the *evidence* that the coin is unfair is vastly stronger at 10,000, because the expected wobble shrinks (in relative terms) as N grows. This is the same reason a strict threshold is right: because a real SRM is a bug that will show up as many sigma, setting the alarm at p<0.001 rather than the usual 0.05 keeps the guard from crying wolf on the ordinary wobbles while still catching the genuine breaks with overwhelming margin.

<svg role="img" aria-label="A ruler marked in standard errors of 50 units each from the expected 5000: the healthy deviation of +30 lands just past the first tick, the broken deviation of +200 lands at the fourth tick, well past the alarm line" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">deviation measured in standard errors (1 SE = 50 units)</text>
  <line x1="30" y1="50" x2="280" y2="50" stroke="var(--grid)"/>
  <line x1="30" y1="44" x2="30" y2="56" stroke="var(--line)"/><text x="20" y="68" fill="var(--muted)" font-size="6">5000</text>
  <line x1="90" y1="46" x2="90" y2="54" stroke="var(--grid)"/><text x="82" y="68" fill="var(--muted)" font-size="6">1 SE</text>
  <line x1="150" y1="46" x2="150" y2="54" stroke="var(--grid)"/><text x="140" y="68" fill="var(--muted)" font-size="6">2 SE</text>
  <line x1="210" y1="46" x2="210" y2="54" stroke="var(--grid)"/><text x="200" y="68" fill="var(--muted)" font-size="6">3 SE</text>
  <line x1="270" y1="42" x2="270" y2="58" stroke="var(--s2)"/><text x="258" y="68" fill="var(--muted)" font-size="6">4 SE</text>
  <text x="192" y="40" fill="var(--muted)" font-size="6">alarm ~ p&lt;0.001</text>
  <line x1="240" y1="30" x2="240" y2="58" stroke="var(--line)" stroke-dasharray="1 2"/>
  <circle cx="66" cy="50" r="3" fill="var(--s1)"/><text x="44" y="88" fill="var(--s1)" font-size="6">healthy +30 (0.6 SE)</text>
  <circle cx="270" cy="50" r="3" fill="var(--s2)"/><text x="210" y="88" fill="var(--s2)" font-size="6">broken +200 (4 SE)</text>
</svg>
^ On a ruler where each tick is one standard error (50 units), the healthy split's +30 lands barely past the first mark while the broken split's +200 reaches the fourth — the same "2%" gap in percentage terms is an ordinary wobble in one case and a far-tail alarm in the other, entirely because of N.

```python filename=modules/evals-and-statistics/code/srm-inter-01/srm.py:119-126 COMPLETE
    expected_balanced = abs(healthy["exp_a"] - healthy["exp_b"]) < 1e-9 and abs(healthy["exp_a"] - 5000) < 1e-9
    print("  the intended split expects 5000/5000 = %s (%.0f/%.0f)" % (expected_balanced, healthy["exp_a"], healthy["exp_b"]))

    healthy_passes = not healthy["srm"]
    print("  healthy (5030/4970) passes the SRM guard = %s (p=%.4g, %.1f SE off)" % (healthy_passes, healthy["p"], healthy["z"]))

    broken_flagged = broken["srm"]
    print("  broken (5200/4800) trips the SRM guard = %s (p=%.5g, %.1f SE off)" % (broken_flagged, broken["p"], broken["z"]))
```

## Definition of done

The self-test pins the expected split, the healthy pass, the broken alarm, and the exact 4-sigma deviation behind it.

```python filename=modules/evals-and-statistics/code/srm-inter-01/srm.py:128-132 COMPLETE
    broken_is_4_se = abs(broken["z"] - 4.0) < 1e-9
    print("  the broken split is exactly 4 standard errors off = %s (z=%.1f, chi2=%.0f)" % (broken_is_4_se, broken["z"], broken["chi2"]))

    verdicts_differ = healthy["srm"] != broken["srm"]
    print("  the guard separates the two experiments = %s (healthy ok, broken invalid)" % verdicts_differ)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the healthy split passes the SRM guard and the broken split trips it, invalidating its metric
--------------------------------------------------------------------------------------------------------
  the intended split expects 5000/5000 = True (5000/5000)
  healthy (5030/4970) passes the SRM guard = True (p=0.5485, 0.6 SE off)
  broken (5200/4800) trips the SRM guard = True (p=6.3342e-05, 4.0 SE off)
  the broken split is exactly 4 standard errors off = True (z=4.0, chi2=16)
  the guard separates the two experiments = True (healthy ok, broken invalid)
```

<svg role="img" aria-label="Two experiment verdicts: healthy passes the SRM guard and proceeds to read the metric; broken trips the guard and its metric is discarded as invalid" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">SRM guard runs before the metric — pass to proceed, fail to stop</text>
  <text x="10" y="38" fill="var(--muted)" font-size="7">healthy</text>
  <rect x="70" y="26" width="90" height="16" fill="var(--s1)"/><text x="76" y="38" fill="var(--panel)" font-size="7">p=0.55 → ok</text>
  <text x="170" y="38" fill="var(--muted)" font-size="7">→ read the metric</text>
  <text x="10" y="66" fill="var(--muted)" font-size="7">broken</text>
  <rect x="70" y="54" width="90" height="16" fill="var(--s2)"/><text x="76" y="66" fill="var(--panel)" font-size="7">p=6e-5 → SRM</text>
  <text x="170" y="66" fill="var(--muted)" font-size="7">→ discard, fix pipeline</text>
  <text x="10" y="88" fill="var(--muted)" font-size="6">the broken metric is never reported, however significant it looks</text>
</svg>
^ The SRM guard is a gate before the metric: the healthy experiment passes and its metric may be read, while the broken experiment is stopped at the gate and its metric discarded — the split check, not the metric's p-value, decides whether the experiment counts.

**Done means the guard's decision is proven on real counts: the healthy split (5030/4970, 0.6 SE off, p≈0.55) passes and the broken split (5200/4800, 4 SE off, chi-square 16, p≈0.00006) trips the strict SRM threshold — so the arm counts must be tested against the intended split before any metric is trusted, because a mismatch makes the groups non-exchangeable and invalidates the whole experiment.**

## Boss fight

Predict two ways the SRM check itself is misused, because a guardrail applied carelessly can either miss the break or manufacture a false alarm.

The first trap is diagnosing the SRM instead of debugging it — treating the alarm as a nuisance to be silenced rather than a symptom to be traced. When SRM fires, the temptation is to "fix" it statistically: drop the extra units to rebalance the arms, or reweight, or just rerun until the split looks even. All of these are wrong, because the missing or extra units are not random — whatever mechanism unbalanced the arms (a redirect, a bot filter, a broken join) removed a *biased* slice, so the imbalance is a fingerprint pointing at which population was lost, and papering over the count destroys the evidence while leaving the bias. The correct response is to find the pipeline stage where the counts diverge (instrument each step: assignment, exposure, logging, and the metric join, and see where A and B stop matching) and fix that stage, then rerun. An SRM is a bug report, not a statistical inconvenience; the number 5200/4800 is telling you *where* to look, and the fix is upstream in the data pipeline, never in the analysis.

The second trap is getting the expected ratio or the unit wrong, which either hides a real SRM or invents a fake one. The test compares against the *intended* split, so if the experiment was designed 90/10 (a small canary arm) and you test against 50/50, the guard screams SRM on a perfectly healthy experiment — the expected fraction must be the one the randomizer actually targeted, not a default. Conversely, the counts must be at the level of the randomization unit: if you randomize by user but count sessions, a heavier-using arm inflates the session count and can trip SRM even though users were split fairly, or mask a real user-level SRM behind balanced sessions. And the threshold interacts with how often you look — an SRM check run continuously as data streams in will eventually cross p<0.001 by chance if you let it peek forever, so the check belongs at the analysis boundary (or with a peeking-aware method), the same discipline as not stopping an A/B test at the first significant metric. The guard is only as good as three things being right: the expected ratio matches the design, the counted unit matches the randomized unit, and the test is applied once at the decision point rather than continuously mined for an alarm.

**When SRM fires, debug the pipeline, never rebalance the counts — the imbalance is a biased-loss fingerprint pointing at the broken stage, and dropping or reweighting units destroys the evidence while keeping the bias; and make the check honest by testing against the ratio the randomizer actually targeted (not a 50/50 default), counting at the randomization unit (users if you randomized users, not sessions), and applying it once at the decision point rather than peeking continuously until chance trips it.**

## External resources

The experimentation literature on Sample Ratio Mismatch (Fabijan et al., "Diagnosing Sample Ratio Mismatch in Online Controlled Experiments," and Microsoft/Booking.com/Airbnb write-ups) — why an SRM invalidates an experiment, common pipeline causes, and how to trace the stage where the arms diverge.

Documentation for chi-square goodness-of-fit testing and the standard error of a proportion — how the assignment counts are tested against the intended split and why the alarm threshold is set far stricter than the usual 0.05.

The companion peeking and paired-comparison modules in this topic — the SRM guard runs before and independently of the metric test, and its "apply once at the decision point" discipline is the same one that stops you from calling an A/B test at the first significant look.
