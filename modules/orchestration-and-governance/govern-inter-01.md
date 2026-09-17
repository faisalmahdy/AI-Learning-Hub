---
id: govern-inter-01
title: Earned autonomy — promote on the confidence bound, not the streak
topic: orchestration-and-governance
level: intermediate
status: ready
time: 8-10h
summary: Grant an agent more autonomy when its human-acceptance rate clears 80% and a rookie that went 5-for-5 gets promoted — 100% ≥ 80% — even though five decisions cannot tell a 100% agent from a 65% one. Gate on the Wilson lower confidence bound instead and the same rookie is held at a bound of 0.57 while a veteran at 47/50 clears it at 0.84, so the rate rule makes 2 premature promotions and the bound rule makes 0, because autonomy should follow the accuracy you can prove, not the streak you happened to see.
eli5: A new driver with five perfect trips isn't a proven safe driver — five trips can't tell lucky from good. Wait for enough trips that you're sure they're above the bar, and the beginner keeps practicing while the veteran with hundreds of safe miles gets the keys.
---

## Why this module

The last module derived which agents are working. This one decides how much to trust the ones that are: how much autonomy an agent has earned to act without asking. The labs designed this — a "personal-command-center accuracy spine" that tracks whether a human accepted, revised, or rejected each agent suggestion — but the scan flags the crucial half as unbuilt: "earned-autonomy outcome linkage is designed-not-built." A tracker that counts accepts is not yet a rule that promotes; the rule is where the judgment lives, and a careless rule is worse than none because it grants autonomy on the strength of noise.

The obvious rule is to promote an agent when its acceptance rate clears a threshold. It fails the moment an agent has a short, lucky record: five accepted decisions out of five is a 100% rate, clears any bar, and promotes an agent you have barely watched. Five decisions cannot distinguish an agent that is truly excellent from one that is mediocre and got a good week — the *rate* is real, but your *confidence* in it is not, and autonomy should follow confidence. The fix is to promote on the lower bound of a confidence interval: not "how good does this agent look" but "how good are we sure it is."

You need the evals track's instinct that a number needs its uncertainty — this is that instinct pointed at a governance decision. Everything runs offline against a six-agent fixture, stdlib Python 3, `$0.00`. The tool it introduces is the Wilson score interval, the standard interval for a pass rate at small sample sizes, which shrinks a short streak's credit exactly the way this decision needs.

Here is the promotion decision measured against what each agent is truly worth:

```
# modules/orchestration-and-governance/code/govern-inter-01/ — COMPLETE, run from that directory
$ python3 autonomy.py --measure

PROMOTION QUALITY — premature promotions against each agent's true rate
--------------------------------------------------------------------
  naive (rate)           premature: 2  ['rookiehot', 'flakyhot']
  earned (lower bound)   premature: 0
```

run: 2026-08-25 · deterministic; ledgers and true rates are a fixture · bar 80%, z=1.96, n=6 agents · `python3 autonomy.py --measure`

The rate rule promotes two agents whose true acceptance rate is below the bar — it was fooled by a short perfect streak. The bound rule promotes none of them. Every premature promotion is an agent granted unattended autonomy it has not earned, which is the exact failure the whole idea of earned autonomy exists to prevent. This module is those two numbers and the interval that separates them.

## Concepts

Named here so you can find them again; each is built below.

- **Acceptance rate** — the fraction of an agent's decisions a human accepted. The track record.
- **Autonomy tier** — how much an agent may do without asking; promotion moves it up a tier.
- **The threshold** — the acceptance rate an agent must clear to earn the next tier. Here, 80%.
- **Wilson lower bound** — the low end of a confidence interval for a rate; what you are *sure* the rate is at least.
- **Premature promotion** — promoting an agent whose true rate is below the bar. The dangerous error.
- **The point-rate rule** — promote when the raw rate clears the bar. The bug.

## Worked example

Source: faisalmahdy/personal-command-center — the accuracy spine that logs accept / revise / reject per agent suggestion, "architected to eventually earn tiered autonomy"; the scan records the linkage from that record to an actual promotion as designed-not-built. This module builds the linkage and its guardrail.

Script and fixture: `modules/orchestration-and-governance/code/govern-inter-01/` — `autonomy.py`, and `ledger.json`, six agents' acceptance records with a hidden true rate. Every command runs from there.

### The frame: graduated licensing, not a hot first week

Think of autonomy like a driver's license. You do not hand a new driver the keys to a truck full of cargo because their first five trips were flawless — five trips is not evidence of a safe driver, it is evidence you have barely watched them. Graduated licensing waits for enough miles that you can be confident, not just impressed. The acceptance rate is the trip record; the question a promotion asks is not "did the last few trips go well" but "have there been enough good trips that we can rule out luck."

That distinction is the whole module. A rate answers "how did the sample go." A lower confidence bound answers "given this sample, how good is the agent *at least*, allowing for the sample being kind." Promote on the first and a lucky streak buys autonomy; promote on the second and the agent has to earn it with volume, which is exactly what "earned" should mean.

### The record: a rate can lie, a bound cannot

```
# $ python3 autonomy.py --ledger
#   agent       accepted/total   rate     wilson-lower   true
#   proven       90/100          0.90     0.83           0.90
#   veteran      47/50           0.94     0.84           0.94
#   steady       40/50           0.80     0.67           0.80
#   weak         30/50           0.60     0.46           0.60
#   flakyhot      8/8            1.00     0.68           0.70
#   rookiehot     5/5            1.00     0.57           0.65
```

run: 2026-08-25 · fixture · `python3 autonomy.py --ledger`

Look at `rookiehot`: a perfect 5-of-5, rate 1.00, the best-looking agent in the fleet — and a Wilson lower bound of 0.57, the *worst*. Five perfect decisions are consistent with a true rate anywhere from about 57% to 100%, so the most you can be sure of is 57%, well under the 80% bar. Now `proven`: 90-of-100, a merely-good 0.90 rate, but ninety accepted decisions pin the lower bound to 0.83 — above the bar. The rate ranks `rookiehot` first and `proven` fourth; the bound ranks them the other way, and the bound is the one that reflects how much you actually know.

<svg viewBox="0 0 700 180" role="img" aria-label="For each agent a point rate and a Wilson lower bound. rookiehot and flakyhot have rate 1.0 but low bounds (0.57, 0.68). proven and veteran have rates 0.90 and 0.94 with bounds 0.83 and 0.84 above the 0.80 bar. The bar is drawn at 0.80.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">point rate (dot) and Wilson lower bound (bar start), bar = 0.80</text>
    <line x1="120" y1="30" x2="120" y2="165" stroke="var(--grid)"></line>
    <text x="20" y="34" fill="var(--muted)">0.4</text><text x="640" y="34" fill="var(--muted)">1.0</text>
    <line x1="440" y1="26" x2="440" y2="165" stroke="var(--s1)" stroke-width="1.4" stroke-dasharray="4 3"></line>
    <text x="446" y="36" fill="var(--s1)" font-size="8">bar 0.80</text>
    <g>
      <text x="20" y="55" fill="var(--ink)">rookiehot</text><line x1="253" y1="52" x2="640" y2="52" stroke="var(--s2)" stroke-width="3"></line><circle cx="640" cy="52" r="4" fill="var(--s2)"></circle><text x="200" y="55" fill="var(--s2)" font-size="8">0.57</text>
      <text x="20" y="77" fill="var(--ink)">flakyhot</text><line x1="360" y1="74" x2="640" y2="74" stroke="var(--s2)" stroke-width="3"></line><circle cx="640" cy="74" r="4" fill="var(--s2)"></circle><text x="315" y="77" fill="var(--s2)" font-size="8">0.68</text>
      <text x="20" y="99" fill="var(--ink)">steady</text><line x1="300" y1="96" x2="520" y2="96" stroke="var(--muted)" stroke-width="3"></line><circle cx="520" cy="96" r="4" fill="var(--muted)"></circle><text x="255" y="99" fill="var(--muted)" font-size="8">0.67</text>
      <text x="20" y="121" fill="var(--ink)">proven</text><line x1="487" y1="118" x2="620" y2="118" stroke="var(--s1)" stroke-width="3"></line><circle cx="620" cy="118" r="4" fill="var(--s1)"></circle><text x="450" y="121" fill="var(--s1)" font-size="8">0.83</text>
      <text x="20" y="143" fill="var(--ink)">veteran</text><line x1="493" y1="140" x2="640" y2="140" stroke="var(--s1)" stroke-width="3"></line><circle cx="640" cy="140" r="4" fill="var(--s1)"></circle><text x="456" y="143" fill="var(--s1)" font-size="8">0.84</text>
    </g>
  </g>
</svg>
^ Each bar starts at the agent's Wilson lower bound and ends at its rate. The perfect streaks (rookiehot, flakyhot) have rates at 1.0 but bounds far left of the bar; the long records (proven, veteran) sit entirely right of it. Promotion should read the left end of the bar, not the dot.

### The Wilson lower bound

The bound is a closed form — no simulation. It pulls a rate toward 0.5 and widens the interval when the sample is small, so a short streak cannot clear a high bar.

```
# autonomy.py:43-52 — COMPLETE (the low end of the Wilson score interval)
def wilson_lower(accepted, n, z=Z):
    """Lower bound of the Wilson score interval for a proportion. Shrinks toward
    0.5 and widens when n is small, so a short streak cannot clear a high bar."""
    if n == 0:
        return 0.0
    p = accepted / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z / denom) * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return center - margin
```

The `n` in every denominator is the point: at `n=5` the margin is huge and the bound sits far below the rate; at `n=100` the margin is small and the bound hugs the rate. Wilson is the standard choice here because at a perfect rate the ordinary interval collapses to zero width — it would call 5/5 a certain 100% — while Wilson keeps an honest spread.

<svg viewBox="0 0 700 180" role="img" aria-label="The Wilson lower bound of a flawless record climbs with sample size: 0.57 at n=5, 0.68 at n=8, 0.77 at n=13, 0.84 at n=20, 0.90 at n=35, 0.93 at n=50. It crosses the 0.80 bar between n=13 and n=20, around 16 decisions.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">lower bound of a PERFECT record vs number of decisions</text>
    <line x1="60" y1="150" x2="660" y2="150" stroke="var(--grid)"></line>
    <line x1="60" y1="30" x2="60" y2="150" stroke="var(--grid)"></line>
    <text x="30" y="45" fill="var(--muted)">1.0</text><text x="30" y="153" fill="var(--muted)">0.5</text>
    <line x1="60" y1="66" x2="660" y2="66" stroke="var(--s1)" stroke-width="1.3" stroke-dasharray="4 3"></line>
    <text x="620" y="62" fill="var(--s1)" font-size="8">bar 0.80</text>
    <polyline points="90,124 150,101 250,74 340,50 480,32 620,25" fill="none" stroke="var(--muted)" stroke-width="2"></polyline>
    <circle cx="90" cy="124" r="3.5" fill="var(--s2)"></circle><text x="82" y="140" fill="var(--s2)" font-size="8">n=5: 0.57</text>
    <circle cx="150" cy="101" r="3.5" fill="var(--s2)"></circle>
    <circle cx="250" cy="74" r="3.5" fill="var(--muted)"></circle><text x="230" y="70" fill="var(--muted)" font-size="8">n=13</text>
    <circle cx="340" cy="50" r="3.5" fill="var(--s1)"></circle><text x="330" y="46" fill="var(--s1)" font-size="8">n=20: 0.84</text>
    <circle cx="620" cy="25" r="3.5" fill="var(--s1)"></circle>
    <line x1="295" y1="30" x2="295" y2="150" stroke="var(--s1)" stroke-width="1" stroke-dasharray="2 2"></line>
    <text x="298" y="145" fill="var(--s1)" font-size="8">clears bar ~16</text>
  </g>
</svg>
^ Even a flawless agent's lower bound climbs slowly: it does not clear the 0.80 bar until about the sixteenth decision. That curve is the earned rule's whole behavior — perfection is not enough; only perfection sustained over enough decisions promotes.

### The two rules

The naive rule reads the rate; the earned rule reads the bound. That single substitution is the entire fix.

```
# autonomy.py:57-66 — COMPLETE (promote on the rate, or on the bound)
def promote_naive(agent):
    """THE BUG: promote when the raw acceptance rate clears the threshold. Blind
    to how few decisions that rate is built on."""
    return rate(agent) >= THRESHOLD


def promote_earned(agent):
    """Promote only when the lower confidence bound clears the threshold -- i.e.
    we are 95% sure the TRUE rate is above the bar, not just this sample's."""
    return wilson_lower(agent["accepted"], agent["total"]) >= THRESHOLD
```

Run both across the fleet:

```
# $ python3 autonomy.py --decide
#   agent       rate   lower   naive        earned
#   proven      0.90   0.83    PROMOTE      PROMOTE
#   veteran     0.94   0.84    PROMOTE      PROMOTE
#   steady      0.80   0.67    PROMOTE      hold
#   weak        0.60   0.46    hold         hold
#   flakyhot    1.00   0.68    PROMOTE      hold      <-- lucky streak
#   rookiehot   1.00   0.57    PROMOTE      hold      <-- lucky streak
```

run: 2026-08-25 · fixture · `python3 autonomy.py --decide`

The naive rule promotes five agents, two of them on a perfect streak that their true rate does not back up. The earned rule promotes only the two with the record to prove it. Note `steady`: its rate is exactly 0.80, so the naive rule promotes it, but its bound is 0.67, so the earned rule holds — and `steady`'s true rate is exactly 0.80, sitting on the bar. This is the honest cost of the earned rule: it is conservative, and it will make a genuinely-at-bar agent keep earning before it promotes. That conservatism is a feature for autonomy — the price of never promoting a fluke is occasionally delaying a deserving agent until it has the volume to prove it.

### Measure the failure that matters

The dangerous error is a premature promotion: autonomy granted to an agent whose true rate is below the bar. Count them for each rule.

```
# autonomy.py:71-73 — COMPLETE (promotions of agents whose true rate is below the bar)
def premature(agents, rule):
    """Promotions the rule makes for agents whose TRUE rate is below the bar."""
    return [a["id"] for a in agents if rule(a) and a["true_rate"] < THRESHOLD]
```

The rate rule makes two premature promotions; the bound rule makes zero. The self-test ties it to the mechanism — a perfect short streak is promoted by the rate and held by the bound, and the longest-record agent earns it under both:

```
# $ python3 autonomy.py --check
#   naive premature promotions   = ['rookiehot', 'flakyhot']
#   earned premature promotions  = none
#   a perfect short streak (flakyhot, rookiehot) is promoted by rate, held by bound = True
#   the longest-record agent (proven) is earned-promoted and truly qualifies = True
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · n=6 agents · `python3 autonomy.py --check`

**Autonomy should track the accuracy you can prove, not the accuracy you happened to see: gate on the lower confidence bound, and a lucky streak buys nothing until it becomes a long record.**

### The running tally

| rule | promotes | premature | what happened |
|---|---|---|---|
| naive (rate ≥ bar) | 5 | 2 | two perfect streaks promoted on 5 and 8 decisions |
| earned (bound ≥ bar) | 2 | 0 | only the long, proven records cleared the bound |

<svg viewBox="0 0 700 150" role="img" aria-label="The naive rate rule promotes 5 agents, 2 of them premature. The earned bound rule promotes 2 agents, 0 premature.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="20" fill="var(--muted)">promotions made, and how many were premature (true rate below the bar)</text>
    <text x="20" y="58" fill="var(--ink)">naive (rate)</text>
    <rect x="150" y="46" width="300" height="18" rx="3" fill="var(--muted)"></rect><text x="456" y="60" fill="var(--muted)">5 promoted</text>
    <rect x="150" y="46" width="120" height="18" rx="3" fill="var(--s2)"></rect><text x="156" y="60" fill="var(--panel)" font-size="8">2 premature</text>
    <text x="20" y="102" fill="var(--ink)">earned (bound)</text>
    <rect x="150" y="90" width="120" height="18" rx="3" fill="var(--s1)"></rect><text x="276" y="104" fill="var(--s1)">2 promoted, 0 premature</text>
  </g>
</svg>
^ Same six agents. The rate rule promotes more but grants two unearned tiers; the bound rule promotes fewer and grants none it cannot back with evidence.

The records never changed; only whether the rule read the rate or the bound. The rate treats every agent's number as equally trustworthy regardless of how many decisions built it, which is how a five-decision streak outranks a hundred-decision record. The bound bakes the sample size into the decision, so credit is proportional to evidence — and demotion is the same rule in reverse: when an agent's recent record decays enough that its bound drops below the bar, autonomy is pulled by the same logic that granted it.

### What we did not settle

The fixture hands you each agent's `true_rate`, which in production you never have — you only ever see the ledger and the interval, which is the whole reason the bound matters. Real complications we skipped: acceptance is not stationary, so a bound over an agent's whole history can mask a recent decline — a real system windows the record or weights recent decisions, and pairs promotion with continuous demotion on the same bound; the 80% bar and the 95% confidence are policy choices, not physics, and a higher-stakes tier should demand both a higher bar and a tighter interval; and "accepted by a human" is itself a noisy label — a rubber-stamping reviewer inflates every agent's rate at once, which is why the accept signal needs its own calibration, exactly as the evals track's judge did. The dial here is the bound; the next dials are the window and the bar.

## Build

The pipeline in one paragraph: log every agent decision as accepted or not; compute the Wilson lower bound of its acceptance rate; promote an autonomy tier only when that bound clears the tier's threshold, and demote when it drops below; and validate the rule by counting premature promotions against a held-out or later-confirmed outcome, never against the rate that drove the decision. Never gate autonomy on a raw rate, and never let a short streak clear a high bar.

We opened on the premature-promotion counts. The rule that makes zero:

```
# modules/orchestration-and-governance/code/govern-inter-01/ — COMPLETE, run from that directory
$ python3 autonomy.py --decide
  earned (lower bound) promotes only proven and veteran
```

Now gate your own agents. The dials are `THRESHOLD` and `Z`: raise the bar and the confidence for higher-stakes tiers. Your number to beat is the **premature-promotion rate** on a replay of your accept/reject history — promotions your rule made that a later, larger sample showed were unearned. Build an agent with a short perfect streak and confirm the rate rule promotes it while the bound rule waits. Bring back both rules' premature counts and the sample size at which your hot agents finally cleared the bound. Good luck.

## Definition of done

- [ ] An accept/reject ledger per agent, with total decisions recorded, not just the rate
- [ ] A Wilson lower bound computed from accepted and total
- [ ] A promotion rule gated on the bound clearing a threshold, and a demotion rule on it dropping below
- [ ] Your own `ledger.json` including at least one short perfect streak and one long strong record
- [ ] The naive rate rule kept for contrast, so premature promotions are counted, not asserted
- [ ] `python3 autonomy.py --check` printing SELF-TEST PASS: the rate rule overreaches, the bound rule is clean, the streak is held, the veteran earns it
- [ ] The premature-promotion counts for both rules, and the threshold and confidence you chose
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. An agent went 5-for-5 and was promoted; a 90-of-100 agent was not, under the rate rule the other way around. Explain which promotion is dangerous and why the rate cannot see it.
2. Define the Wilson lower bound in words, and say what happens to it as the sample size grows at a fixed rate.
3. Give the one-line change from the naive rule to the earned rule, and state exactly what the earned rule is 95% sure of.
4. The earned rule held `steady`, whose true rate was exactly at the bar. Is that a bug? Argue the tradeoff.
5. Your own run counted premature promotions for both rules. What were they, and at what sample size did a hot agent finally clear the bound?

## External resources

- faisalmahdy/personal-command-center — the accuracy spine — my summary: the accept / revise / reject tracker this module turns into a promotion rule; read it for the outcome signal the bound consumes, and note the scan's flag that the tracker-to-promotion linkage was designed-not-built — the gap this module fills.
- Wilson, E. B., *Probable Inference, the Law of Succession, and Statistical Inference* (1927), via the modern write-up at https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm — my summary: the score interval used here and why it beats the normal approximation at extreme rates and small n; read it for why 5/5 is not a certain 100%, which is the whole hinge of the module.
- This hub, *evals-inter-01* — modules/evals-and-statistics/evals-inter-01.md — my summary: the paired interval and sign test on an A/B eval; read it for the same "a number needs its uncertainty" discipline this module applies to a governance decision instead of a leaderboard.
