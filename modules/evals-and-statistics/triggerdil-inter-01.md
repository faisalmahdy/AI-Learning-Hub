---
id: triggerdil-inter-01
title: Measure the A/B effect on the users who triggered the feature, not on everyone — unaffected users dilute a real effect toward zero
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: Many experiments test a change that only fires on a code path a minority of users reach — a new checkout flow only for users who reach checkout, a fix for an error only some sessions hit, a recommendation shown only when a particular shelf renders. Users who never trigger the feature are, by construction, unaffected: their metric is identical in the treatment and control arms, because from their perspective nothing changed, so they are dead weight in the comparison. Average the metric over every assigned user and that dead weight silently taxes the result — the real effect lives entirely in the triggered minority, but the mean spreads it across the whole assigned population, so the measured lift is the true effect multiplied by the trigger rate. A genuine +0.20 improvement among the 20% who trigger shows up as a diluted +0.04 over all users, five times too small, easy to dismiss as noise and easy to fail to power for, so a real large effect comes back inconclusive. The fix is trigger-based analysis: log the trigger condition in both arms — wherever a user meets the condition that would fire the feature, not only where it actually fires — so you can identify the control users who would have triggered, then compute the effect only among triggered users in treatment versus would-have-triggered users in control. That comparison is still a valid randomized experiment, because triggering is determined by user behavior rather than by the treatment, and it recovers the true effect on the population the change can move. On a fixture where 20% of users trigger, the true effect among them is +0.20 conversion but dilutes to +0.04 over everyone — exactly the trigger rate times the true effect.
eli5: Imagine you invent a new slide for the playground, but only the kids who walk to the far corner ever see it, and that's just one in five kids. The far-corner kids love it and play twice as long — a big effect. But if you measure "how long did ALL the kids play today," most of them never went near the slide, so their unchanged playtime waters down the average and it looks like the slide barely mattered. To judge the slide fairly you should only compare the kids who reached the far corner against the kids who WOULD have reached it on a normal day. Then you see the real, big effect instead of a tiny watered-down one. Measuring everyone hides the effect among the few it actually reached.
---

## Why this module

Not every experiment changes something every user sees. A great many test a feature that only fires on a specific path: the user has to reach checkout, hit the error, land on the page where the new shelf renders. Everyone gets randomized into treatment or control, but only the subset who reach the trigger point actually experience the change. The rest are assigned to a treatment they never encountered, and their behavior is identical to what it would have been in control — the feature could not have moved them, because it never ran for them.

This creates a mismatch between who was randomized and who was affected, and the standard analysis — average the metric over everyone in each arm — is blind to it. The effect is real and concentrated in the triggered users, but the arm-wide mean divides that effect across the whole assigned population. The more users who never trigger, the more the effect is diluted, and the dilution is exactly proportional: measured effect equals true effect times the fraction who triggered. A powerful change with a low trigger rate can look like nothing.

The consequence is not just a smaller number; it is wrong decisions. You sized the experiment to detect the effect you expected, then measured a fraction of it, so the test comes back underpowered and inconclusive and a genuine win is shelved. This module runs one such experiment both ways and shows the dilution and its fix.

**When only a fraction of assigned users trigger a feature, averaging the metric over all of them dilutes the true effect by the trigger rate — the effect must be measured on the triggered population, treatment-triggered versus would-have-triggered in control.**

## Concepts

The fixture splits each arm by whether the user triggered the feature. In treatment, 20 of 100 triggered and converted at a high rate; the other 80 never saw the feature. Control is logged the same way — the 20 who met the trigger condition are tracked separately from the 80 who did not.

```json filename=modules/evals-and-statistics/code/triggerdil-inter-01/triggerdil.json:3-9 COMPLETE
  "treatment": {
    "triggered": {"n": 20, "conv": 6},
    "not_triggered": {"n": 80, "conv": 8}
  },
  "control": {
    "triggered": {"n": 20, "conv": 2},
    "not_triggered": {"n": 80, "conv": 8}
  }
```

A handful of rates carry the whole argument. The conversion rate of a cell, each arm's overall rate (pooling triggered and not), and the trigger rate — the fraction of an arm that reached the feature.

```python filename=modules/evals-and-statistics/code/triggerdil-inter-01/triggerdil.py:32-49 COMPLETE
def rate(cell):
    return cell["conv"] / cell["n"]


def arm_totals(arm):
    n = arm["triggered"]["n"] + arm["not_triggered"]["n"]
    conv = arm["triggered"]["conv"] + arm["not_triggered"]["conv"]
    return n, conv


def overall_rate(arm):
    n, conv = arm_totals(arm)
    return conv / n


def trigger_rate(arm):
    n, _ = arm_totals(arm)
    return arm["triggered"]["n"] / n
```

The all-users effect subtracts the two overall rates; the triggered-only effect subtracts the two triggered rates. Those are the two analyses, and they disagree because the non-triggered users sit in the first and not the second.

<svg role="img" aria-label="A bar for the true effect of 0.20 among triggered users, shrinking to 0.04 when spread across all users because only 20 percent triggered" viewBox="0 0 320 120">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">the true +0.20 effect, spread over all users, becomes +0.04</text>
  <text x="10" y="40" font-size="8" fill="var(--s1)">triggered (20%)</text>
  <rect x="98" y="30" width="160" height="14" fill="var(--s1)"/><text x="262" y="41" font-size="8" fill="var(--ink)">+0.20</text>
  <text x="10" y="72" font-size="8" fill="var(--s2)">all users</text>
  <rect x="98" y="62" width="32" height="14" fill="var(--s2)"/><text x="134" y="73" font-size="8" fill="var(--ink)">+0.04</text>
  <text x="98" y="98" font-size="7.5" fill="var(--muted)">0.20 × trigger rate 0.20 = 0.04 — the 80% unaffected users dilute it</text>
</svg>
^ The effect among triggered users is +0.20, but averaging over the full arm — 80% of whom never triggered — multiplies it by the trigger rate to +0.04. The dilution is exactly the fraction who did not trigger, dragging the effect toward zero.

**Two analyses, two rates: the all-users effect pools in the untouched non-triggering users and shrinks; the triggered-only effect compares like with like and holds the true size.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the analysis step of a feature experiment, reduced to 100 users per arm so every rate is checkable by hand.

Run `--populations` to see the four cells.

```text filename=triggerdil.py --populations
  arm        group          n    conv   rate
  treatment  triggered      20   6      0.30
  treatment  not_triggered  80   8      0.10
  control    triggered      20   2      0.10
  control    not_triggered  80   8      0.10
```

Look at the non-triggered rows first: 0.10 in treatment and 0.10 in control, identical. That is the signature of trigger dilution — the users who never met the feature convert exactly the same in both arms, because nothing about their experience differed. The action is entirely in the triggered rows: 0.30 in treatment versus 0.10 in control, a large lift among the users who actually saw the feature.

Now `--effect` computes both analyses — the diluted difference of overall rates and the triggered-only difference — plus the trigger rate that links them.

```python filename=modules/evals-and-statistics/code/triggerdil-inter-01/triggerdil.py:69-71 COMPLETE
    diluted = overall_rate(t) - overall_rate(c)
    triggered = rate(t["triggered"]) - rate(c["triggered"])
    tr = trigger_rate(t)
```

The printed numbers make the relationship exact.

```text filename=triggerdil.py --effect
  overall treatment rate = 0.14, control rate = 0.10
  all-users (diluted) effect        = +0.04
  triggered-only effect (the truth) = +0.20
  trigger rate                      = 0.20
  trigger_rate x triggered_effect   = +0.04  (equals the diluted effect)
```

The all-users analysis reports +0.04: treatment's overall 0.14 (the 0.30 triggered rate pulled down by the 0.10 non-triggered majority) minus control's 0.10. The triggered-only analysis reports +0.20 — the real effect. And the fourth line proves the mechanism exactly: trigger rate 0.20 times the true effect 0.20 equals 0.04, the diluted number. The dilution is not noise or bias, it is a clean multiplicative shrink by the trigger rate, so a lower trigger rate would shrink it further — at a 2% trigger rate the +0.20 would read as +0.004 and vanish entirely.

<svg role="img" aria-label="Two arm rates broken into triggered and non-triggered contributions, showing treatment overall 0.14 versus control 0.10, with the gap much smaller than the triggered-only gap" viewBox="0 0 320 120">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">overall rate = triggered (20%) blended with non-triggered (80%)</text>
  <text x="10" y="40" font-size="8" fill="var(--s1)">treatment</text>
  <rect x="70" y="30" width="24" height="14" fill="var(--s1)"/><text x="72" y="41" font-size="7" fill="var(--panel)">.30</text>
  <rect x="94" y="30" width="80" height="14" fill="none" stroke="var(--line)"/><text x="120" y="41" font-size="7" fill="var(--muted)">.10 (80%)</text>
  <text x="180" y="41" font-size="8" fill="var(--ink)">→ 0.14</text>
  <text x="10" y="72" font-size="8" fill="var(--s2)">control</text>
  <rect x="70" y="62" width="24" height="14" fill="var(--s2)"/><text x="72" y="73" font-size="7" fill="var(--panel)">.10</text>
  <rect x="94" y="62" width="80" height="14" fill="none" stroke="var(--line)"/><text x="120" y="73" font-size="7" fill="var(--muted)">.10 (80%)</text>
  <text x="180" y="73" font-size="8" fill="var(--ink)">→ 0.10</text>
  <text x="10" y="104" font-size="7.5" fill="var(--muted)">the shared 80% at 0.10 cancels, leaving only 20% of the triggered gap: 0.04</text>
</svg>
^ Each arm's overall rate blends the triggered cell with the large non-triggered cell. The non-triggered 0.10 is identical in both arms and cancels in the difference, so the overall gap is just the triggered gap scaled by the 20% who triggered — 0.04 instead of 0.20.

**The all-users effect is +0.04 and the triggered-only effect is +0.20, and the difference is exactly the trigger rate: averaging over the unaffected 80% shrinks the real effect fivefold.**

## Build

The self-test establishes the setup — only a fraction trigger, and the non-triggered users show zero effect — then the dilution: the all-users effect understates the true effect, and equals the trigger rate times it.

```python filename=modules/evals-and-statistics/code/triggerdil-inter-01/triggerdil.py:92-99 COMPLETE
    only_fraction_triggers = tr < 1.0
    print("  only a fraction of users trigger the feature = %s (%.0f%%)" % (only_fraction_triggers, 100 * tr))

    nontriggered_unaffected = abs(nontrig) < 1e-9
    print("  non-triggered users are unaffected (zero effect) = %s (%+.2f)" % (nontriggered_unaffected, nontrig))

    diluted_understates = abs(diluted) < abs(triggered)
    print("  the all-users effect understates the true effect = %s (%+.2f vs %+.2f)" % (diluted_understates, diluted, triggered))
```

Then the two clauses that pin the mechanism and the fix: the diluted effect equals trigger rate times the true effect, and the triggered-only analysis recovers the true +0.20.

```python filename=modules/evals-and-statistics/code/triggerdil-inter-01/triggerdil.py:101-105 COMPLETE
    dilution_matches_rate = abs(diluted - tr * triggered) < 1e-9
    print("  the diluted effect equals trigger_rate x true effect = %s (%.2f x %+.2f = %+.2f)" % (dilution_matches_rate, tr, triggered, tr * triggered))

    triggered_recovers = abs(triggered - 0.20) < 1e-9
    print("  the triggered-only analysis recovers the true +0.20 effect = %s (%+.2f)" % (triggered_recovers, triggered))
```

Running the check confirms every clause.

```text filename=triggerdil.py --check
  only a fraction of users trigger the feature = True (20%)
  non-triggered users are unaffected (zero effect) = True (+0.00)
  the all-users effect understates the true effect = True (+0.04 vs +0.20)
  the diluted effect equals trigger_rate x true effect = True (0.20 x +0.20 = +0.04)
  the triggered-only analysis recovers the true +0.20 effect = True (+0.20)
```

**The check ties the shrunken effect to the untouched non-triggering users and proves the shrink is exactly the trigger rate — then shows the triggered-only analysis recovering the true effect the dilution hid.**

## Definition of done

Done means the all-users effect is shown to be the true effect times the trigger rate, and the triggered-only analysis recovers the true effect. The clause that the non-triggered users have zero effect is what licenses the whole thing: it confirms the dilution is inert dead weight, not a real subgroup where the feature backfired — if the non-triggered users had moved, that would be a different problem (a spillover or a broken trigger), not dilution.

Two cautions keep trigger-based analysis valid. First, you must log the trigger condition in the control arm too, and log it as "would this user have triggered," not "did the feature fire" — the feature does not fire in control, so you need the underlying behavioral condition (reached checkout, hit the error) recorded identically in both arms. Comparing treatment-triggered against all of control, or against a differently-defined control group, breaks the randomization and reintroduces bias; the comparison is only valid because triggering depends on user behavior that is unaffected by the assignment, so the triggered subsets of both arms are still comparable. Second, trigger-based analysis answers a narrower question — the effect on users who experience the feature — which is the right question for iterating on the feature itself, while the diluted all-users number is the right question for a launch decision about total impact across the whole population. They are both correct answers to different questions; the error is computing the all-users number and interpreting it as the effect of the feature, or powering the experiment as if the whole population were affected.

<svg role="img" aria-label="A decision guide: to judge the feature use the triggered-only effect, to judge total launch impact use the all-users effect, but never read the all-users number as the feature's effect" viewBox="0 0 320 120">
  <rect x="16" y="24" width="130" height="34" fill="none" stroke="var(--s1)"/>
  <text x="26" y="38" font-size="7.5" fill="var(--s1)">iterating on the feature?</text>
  <text x="26" y="51" font-size="7.5" fill="var(--ink)">→ triggered-only (+0.20)</text>
  <rect x="170" y="24" width="134" height="34" fill="none" stroke="var(--s2)"/>
  <text x="180" y="38" font-size="7.5" fill="var(--s2)">total launch impact?</text>
  <text x="180" y="51" font-size="7.5" fill="var(--ink)">→ all-users (+0.04)</text>
  <text x="16" y="82" font-size="7.5" fill="var(--muted)">both are correct answers to different questions</text>
  <text x="16" y="100" font-size="7.5" fill="var(--ink)">the error: reading all-users (+0.04) as the feature's effect</text>
</svg>
^ The triggered-only effect and the all-users effect answer different questions — the feature's effect on those it reaches, versus its total impact across the population. The mistake is powering for one and reading the other, treating the diluted number as the feature's effect.

**Done means the diluted effect is proven to equal the true effect times the trigger rate and the triggered-only analysis recovers it, with the trigger condition logged in both arms so the triggered subsets stay comparable and each number is read as the answer to its own question.**

## Boss fight

A team ships an A/B test for a new "smart reply" button that appears only in threads with a detected question. The overall conversion metric moves +0.3%, which fails to clear their significance bar, and they conclude smart reply does not work. A skeptic notes that only about 8% of threads ever show the button. Is the conclusion safe, and what would you do differently?

The conclusion is not safe — it is a textbook trigger-dilution artifact. The smart reply button can only affect the ~8% of threads where a question is detected and the button renders; the other ~92% of assigned users never see it and behave identically in both arms, so averaging the metric over everyone divides the real effect by roughly the 8% trigger rate. A measured +0.3% over all users is consistent with an effect of around +0.3% / 0.08 ≈ +3.75% among the users who actually saw the button, which could be a large, valuable, and significant effect on the population the feature reaches — completely hidden by the dilution, and made worse because the experiment was almost certainly powered to detect an all-users effect it was never going to produce. What to do differently: analyze the triggered population. Log the trigger condition — "this thread contained a detected question," evaluated in both arms — so you can identify the control threads that would have shown the button, then compare conversion among treatment-triggered threads against would-have-triggered control threads. That comparison is a valid randomized contrast because triggering depends on thread content, not on assignment, and it estimates the effect on the users the feature can actually move. Re-power the test on that triggered population (far fewer users, so plan for the sample size the triggered subset provides), and keep the all-users number too — but label it as total launch impact, not as evidence about whether smart reply works. The decision "does smart reply work" is answered by the triggered analysis; the decision "how much does launching it move the top line" is answered by the diluted one, and conflating them is exactly the error that nearly killed a working feature.

## External resources

Writing on trigger/dilution and "triggered analysis" in online experimentation (Kohavi, Tang, and Xu's Trustworthy Online Controlled Experiments, and the experimentation-platform literature on analyzing the affected population) — how to log triggering in both arms, why the triggered contrast stays unbiased, and how dilution relates to statistical power.

Material on the distinction between the effect on the treated and the intent-to-treat effect (the diluted all-users estimate is essentially an intent-to-treat effect, and the triggered estimate targets the effect on the affected users) — the standard framing from causal inference for why both estimands are valid and answer different questions.
