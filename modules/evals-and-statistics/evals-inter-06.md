---
id: evals-inter-06
title: Optimize the proxy and it stops measuring the target — select on a held-out score
topic: evals-and-statistics
level: intermediate
status: ready
time: 6-9h
summary: An automatic eval metric — keyword overlap, answer length, a rubric of surface checks — is a proxy for the quality you actually want, and it ranks systems honestly right up until you select or tune one to maximize it, at which point the system finds the cheap way to move the proxy without moving the target and the proxy stops measuring anything. Across three variants scored on the same cases by a proxy and a held-out target, the gamed variant drives its proxy to 0.85 (up 0.25 from baseline) while its true quality falls to 0.52 (down 0.08 below baseline), so selecting the highest-proxy system ships a genuine regression, while the genuinely-better variant sits at proxy 0.70 and target 0.75 (up 0.15) and is only chosen when you rank by the held-out target the systems were never tuned against. The tell is per-variant divergence — a variant whose proxy rose while its target fell has been gamed — and the fix is to hold out a target metric you never optimize against, because a measure that becomes a target ceases to be a good measure.
eli5: Say you pay workers by how many nails they hammer, to get a strong fence. Soon someone hammers a thousand tiny nails badly and "wins" your count while building the worst fence on the row. The nail-count was a fine clue about good work — until you made it the prize, and then people chased the clue instead of the work. The fix is to keep one judge who quietly grades the actual fence, a score nobody is allowed to game, and hand the job to whoever that judge ranks first, not whoever hammered the most nails.
---

## Why this module

Every cheap eval metric is a proxy. You want answers a careful human would endorse, but you cannot afford a human on every run, so you measure something correlated and computable — does the answer contain the gold keywords, is it the right length, does it pass a rubric of surface checks — and you trust that metric to rank your systems. It does rank them, honestly, as long as none of the systems was built to maximize it. The moment you select the best-scoring variant, or tune a system against the metric, you change what the metric measures: the system now has an incentive to move the number the cheap way, and the cheap way to add gold keywords is not to write a better answer. This is Goodhart's law — when a measure becomes a target, it ceases to be a good measure — and it is the failure mode that turns a working eval into a machine for shipping the worse system with a green dashboard.

This module makes the divergence concrete and measurable. Three system variants are scored on the same eval cases by two metrics: a proxy (the automatic surface score) and a target (a held-out true-quality score the systems were never tuned against). One variant games the proxy — it drives the proxy up while the target falls below baseline. One variant genuinely improves both. Selecting by the proxy ships the gamed variant, a regression against baseline on the metric that actually matters; selecting by the held-out target ships the real improvement. The gap between those two picks is the whole cost of trusting a proxy you optimize against.

The instinct to unlearn is that a metric that correlates with quality can be used to select for quality. Correlation across systems you did not optimize is not correlation across systems you did — selection breaks the very correlation it relies on. Everything here runs offline against a per-case score fixture, stdlib Python 3, `$0.00`, and the means and picks are computed from the data so the numbers are real. The discipline this buys is cheap and non-negotiable: hold out at least one target metric you never select against, and read it every time you choose a system.

## Concepts

Named here so you can find them again; each is built below.

- **Proxy metric** — a cheap, computable score correlated with quality: keyword overlap, length, a surface rubric.
- **Target metric** — the held-out true-quality score you actually care about, never optimized against.
- **Goodhart's law** — a measure that becomes a target stops being a good measure.
- **Gaming** — driving the proxy up without moving (or while lowering) the target.
- **Divergence** — a variant whose proxy rose while its target fell; the fingerprint of gaming.
- **Held-out selection** — choosing the system by the target metric, not the proxy.

## Worked example

Source: a system-selection decision of the kind an eval harness runs every time it picks a winner from several candidates — the automatic score stands in for any cheap proxy (BLEU, keyword-match, a length or format rubric), and the held-out target stands in for the human-judged quality it is supposed to predict.

Script and fixture: `modules/evals-and-statistics/code/evals-inter-06/` — `goodhart.py`, and `runs.json`, three variants over eight shared cases. Every command runs from there.

### Two metrics per variant

Each metric is a mean over the same cases; the only difference is which column it reads.

```
# goodhart.py:46-51 — COMPLETE (the two metrics: same cases, different column)
def proxy_mean(variant):
    return mean([c["proxy"] for c in variant["cases"]])


def target_mean(variant):
    return mean([c["target"] for c in variant["cases"]])
```

The proxy is the score you can compute on every run; the target is the score you can only afford occasionally, or hold out on purpose. On any single honest system they track each other — that is why the proxy is worth having. The question is what happens across systems that were built to compete on the proxy.

### The scores, and the divergence

Compute each variant's two means and its change against the baseline:

```
# goodhart.py:54-64 — COMPLETE (each variant's proxy, target, and deltas vs baseline)
def deltas_vs_baseline(data):
    """For each variant, its proxy and target change relative to the baseline variant."""
    variants = data["variants"]
    base = next(v for v in variants if v["id"] == data["baseline"])
    bp, bt = proxy_mean(base), target_mean(base)
    out = {}
    for v in variants:
        out[v["id"]] = {"proxy": proxy_mean(v), "target": target_mean(v),
                        "dproxy": proxy_mean(v) - bp, "dtarget": target_mean(v) - bt}
    return out, bp, bt
```

Run it:

```
# $ python3 goodhart.py --scores
#   variant      proxy   target   dproxy   dtarget   gamed?
#   v1_base     0.600   0.600   +0.000   +0.000   False
#   v2_gamed    0.850   0.520   +0.250   -0.080   True
#   v3_genuine  0.700   0.750   +0.100   +0.150   False
```

run: 2026-08-27 · deterministic; per-case scores are a fixture · 3 variants × 8 cases · `python3 goodhart.py --scores`

Read v2_gamed against v3_genuine. v2 has the best proxy by a mile — 0.85 against v3's 0.70 — and on a proxy-only dashboard it is the obvious winner. But its target is 0.52, *below* the 0.60 baseline: it is the worst system in the set on true quality, and shipping it is a regression. v3 has a lower proxy but the highest target, 0.75, up 0.15 on baseline — the only variant that actually improved the thing you care about. The proxy ranks them exactly backwards, and it does so precisely because v2 was the one built to move the proxy.

<svg viewBox="0 0 700 220" role="img" aria-label="Grouped bars for three variants, proxy versus target. v1_base: proxy 0.60, target 0.60, equal. v2_gamed: proxy 0.85 tall, target 0.52 short and below the baseline line — the proxy rose while quality fell. v3_genuine: proxy 0.70, target 0.75, both above baseline. A dashed baseline at 0.60 shows v2_gamed's target dips below it.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">proxy (filled) vs held-out target (outlined) per variant</text>
    <line x1="60" y1="180" x2="660" y2="180" stroke="var(--line)"></line>
    <line x1="60" y1="108" x2="660" y2="108" stroke="var(--muted)" stroke-dasharray="4 3"></line><text x="664" y="111" fill="var(--muted)" font-size="7">baseline 0.60</text>
    <rect x="110" y="108" width="34" height="72" fill="var(--s1)"></rect><rect x="150" y="108" width="34" height="72" fill="var(--panel)" stroke="var(--acc-line)"></rect><text x="147" y="196" text-anchor="middle" fill="var(--muted)" font-size="8">v1_base</text><text x="127" y="102" text-anchor="middle" fill="var(--s1)" font-size="7">.60</text>
    <rect x="300" y="78" width="34" height="102" fill="var(--s1)"></rect><rect x="340" y="118" width="34" height="62" fill="var(--panel)" stroke="var(--s2)"></rect><text x="337" y="196" text-anchor="middle" fill="var(--s2)" font-size="8">v2_gamed</text><text x="317" y="72" text-anchor="middle" fill="var(--s1)" font-size="7">.85</text><text x="357" y="112" text-anchor="middle" fill="var(--s2)" font-size="7">.52</text>
    <rect x="490" y="96" width="34" height="84" fill="var(--s1)"></rect><rect x="530" y="90" width="34" height="90" fill="var(--panel)" stroke="var(--acc-line)"></rect><text x="527" y="196" text-anchor="middle" fill="var(--muted)" font-size="8">v3_genuine</text><text x="507" y="90" text-anchor="middle" fill="var(--s1)" font-size="7">.70</text><text x="547" y="84" text-anchor="middle" fill="var(--acc-ink)" font-size="7">.75</text>
    <text x="300" y="214" fill="var(--s2)" font-size="8">v2's proxy is highest but its target dips below baseline — gamed</text>
  </g>
</svg>
^ v2_gamed has the tallest proxy bar and the only target bar below the baseline line — the signature of gaming. v3_genuine's proxy is modest but its target is the highest. Ranking by the filled bars ships the wrong system.

The `gamed?` column is a one-line diagnostic: a variant whose proxy rose but whose target did not.

```
# goodhart.py:66-68 — COMPLETE (the divergence test: proxy up, target not)
def is_gamed(d):
    """Gamed: the proxy rose but the target did not -- the metric moved without the quality."""
    return d["dproxy"] > 0 and d["dtarget"] <= 0
```

Only v2 trips it: dproxy +0.25, dtarget −0.08. This is the fingerprint of Goodhart — the two metrics, normally moving together, pulled apart exactly on the system that was optimized for one of them.

<svg viewBox="0 0 700 220" role="img" aria-label="A scatter of proxy on the x-axis versus target on the y-axis. A dashed diagonal marks where an honest system sits, proxy equal to target. v1_base sits on the diagonal at 0.60,0.60 and v3_genuine sits near it above at 0.70,0.75. v2_gamed sits far to the lower right at 0.85,0.52, well below the diagonal — high proxy, low target — the gamed point.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">proxy (x) vs target (y): honest systems sit on the diagonal, gamed ones fall below it</text>
    <line x1="80" y1="190" x2="80" y2="40" stroke="var(--line)"></line>
    <line x1="80" y1="190" x2="620" y2="190" stroke="var(--line)"></line>
    <text x="76" y="44" text-anchor="end" fill="var(--muted)" font-size="7">target 0.9</text>
    <text x="76" y="190" text-anchor="end" fill="var(--muted)" font-size="7">0.4</text>
    <text x="80" y="204" text-anchor="middle" fill="var(--muted)" font-size="7">proxy 0.4</text>
    <text x="620" y="204" text-anchor="middle" fill="var(--muted)" font-size="7">0.9</text>
    <line x1="80" y1="190" x2="620" y2="40" stroke="var(--muted)" stroke-dasharray="4 3"></line><text x="560" y="56" fill="var(--muted)" font-size="7">proxy = target</text>
    <circle cx="296" cy="130" r="5" fill="var(--panel)" stroke="var(--acc-line)"></circle><text x="296" y="122" text-anchor="middle" fill="var(--muted)" font-size="7">v1_base</text>
    <circle cx="404" cy="70" r="5" fill="var(--s1)"></circle><text x="404" y="62" text-anchor="middle" fill="var(--acc-ink)" font-size="7">v3_genuine</text>
    <circle cx="566" cy="154" r="5" fill="var(--s2)"></circle><text x="566" y="172" text-anchor="middle" fill="var(--s2)" font-size="7">v2_gamed</text>
    <line x1="566" y1="154" x2="566" y2="63" stroke="var(--s2)" stroke-dasharray="2 2"></line><text x="600" y="110" fill="var(--s2)" font-size="7">gap = gaming</text>
  </g>
</svg>
^ On a proxy-versus-target scatter, honest systems cluster on the diagonal; v2_gamed sits far below it — its proxy is high but its target is low. The vertical gap from the diagonal is exactly the quality the proxy is failing to see.

### The two selection rules

Selecting a system is an argmax. The only choice is which metric you argmax over.

```
# goodhart.py:73-81 — COMPLETE (rank by the proxy you can always see, or the target you held out)
def select_by_proxy(data):
    """The naive rule: ship the variant with the highest proxy score."""
    return max(data["variants"], key=lambda v: (proxy_mean(v), v["id"]))["id"]


def select_by_target(data):
    """The held-out rule: ship the variant with the highest target score."""
    return max(data["variants"], key=lambda v: (target_mean(v), v["id"]))["id"]
```

The naive rule is not lazy or foolish — it is the rule every proxy-only harness runs, because the proxy is the number it has. Run both rules and read what each one ships:

```
# $ python3 goodhart.py --select
#   select by proxy  -> v2_gamed     (true target 0.520, dtarget -0.080)
#   select by target -> v3_genuine   (true target 0.750, dtarget +0.150)
```

run: 2026-08-27 · deterministic · `python3 goodhart.py --select`

The proxy rule ships v2_gamed, whose true quality is 0.52 — a system worse than the baseline it replaced. The target rule ships v3_genuine at 0.75. Same three candidates, same data; the only difference is which score you trusted to rank them, and it is the difference between an improvement and a regression.

<svg viewBox="0 0 700 170" role="img" aria-label="Two selection rules and their outcomes. Rank by proxy points to v2_gamed, ending at true quality 0.52 marked regression below baseline. Rank by target points to v3_genuine, ending at true quality 0.75 marked improvement above baseline. The two rules diverge to opposite outcomes.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">same candidates, two rules, opposite outcomes</text>
    <rect x="40" y="40" width="150" height="30" fill="var(--panel)" stroke="var(--s2)"></rect><text x="115" y="59" text-anchor="middle" fill="var(--s2)" font-size="8">rank by PROXY</text>
    <line x1="190" y1="55" x2="300" y2="55" stroke="var(--s2)"></line>
    <rect x="300" y="40" width="120" height="30" fill="var(--s2)"></rect><text x="360" y="59" text-anchor="middle" fill="var(--panel)" font-size="8">v2_gamed</text>
    <text x="440" y="59" fill="var(--s2)" font-size="8">target 0.52 → REGRESSION</text>
    <rect x="40" y="100" width="150" height="30" fill="var(--panel)" stroke="var(--acc-line)"></rect><text x="115" y="119" text-anchor="middle" fill="var(--acc-ink)" font-size="8">rank by TARGET</text>
    <line x1="190" y1="115" x2="300" y2="115" stroke="var(--acc-line)"></line>
    <rect x="300" y="100" width="120" height="30" fill="var(--s1)"></rect><text x="360" y="119" text-anchor="middle" fill="var(--panel)" font-size="8">v3_genuine</text>
    <text x="440" y="119" fill="var(--s1)" font-size="8">target 0.75 → IMPROVEMENT</text>
    <text x="40" y="156" fill="var(--muted)" font-size="8">the proxy is the number you have; the target is the number you actually want</text>
  </g>
</svg>
^ The proxy-argmax and target-argmax rules run on identical data and ship opposite systems: one a regression, one an improvement. The proxy is not wrong about v3 — it is wrong about v2, the variant built to fool it.

**A metric ranks systems honestly only until one is selected or tuned to maximize it; then the optimized system moves the proxy without the target and the proxy inverts the true ranking — so you must hold out a target metric you never optimize against and select on that, because a measure that becomes a target stops measuring what you wanted.**

### The self-test

The `--check` mode plants the bug — trusting the proxy — and proves it ships a regression, while confirming the held-out rule ships the true best.

```
# $ python3 goodhart.py --check
#   the proxy-argmax pick is a gamed variant = True (v2_gamed: dproxy +0.250, dtarget -0.080)
#   shipping the proxy pick REGRESSES true quality vs baseline = True (dtarget -0.080)
#   the target-argmax pick has the highest true quality = True (v3_genuine, target 0.750)
#   the two rules disagree (the proxy would mislead you) = True (v2_gamed vs v3_genuine)
#   the held-out pick actually improves on baseline = True (dtarget +0.150)
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 goodhart.py --check`

The two load-bearing lines are `proxy_regresses` and `target_best`. The first is the cost of the bug stated in the currency that matters — not "the proxy pick has a lower target" but "shipping it makes your product worse than before." The second is the payoff of the fix: the held-out metric picks the system that is actually best, every time, because nothing was optimized against it.

```
# goodhart.py:119-124 — COMPLETE (the planted bug's cost: the proxy pick is a real regression)
    proxy_picks_gamed = is_gamed(d[by_p])
    print("  the proxy-argmax pick is a gamed variant = %s (%s: dproxy %+.3f, dtarget %+.3f)"
          % (proxy_picks_gamed, by_p, d[by_p]["dproxy"], d[by_p]["dtarget"]))

    proxy_regresses = d[by_p]["dtarget"] < 0
    print("  shipping the proxy pick REGRESSES true quality vs baseline = %s (dtarget %+.3f)"
          % (proxy_regresses, d[by_p]["dtarget"]))
```

### The running tally

| variant | proxy | target | dtarget vs base | proxy rank | target rank | verdict |
|---|---|---|---|---|---|---|
| v1_base | 0.600 | 0.600 | +0.000 | 3rd | 2nd | honest reference |
| v2_gamed | 0.850 | 0.520 | −0.080 | 1st | 3rd | gamed — regression |
| v3_genuine | 0.700 | 0.750 | +0.150 | 2nd | 1st | real improvement |

Read the two rank columns: they are nearly inverted. The proxy crowns v2 and buries v3; the target does the opposite. The only variant whose two ranks agree is the honest baseline, which was not optimized for either. That is the general shape of Goodhart — the more a system is tuned to the proxy, the further its proxy rank runs ahead of its target rank, and selection by proxy sorts systems by how hard they gamed, not by how good they are.

### What we did not settle

This is one held-out target and a single selection; a real harness has more to manage. The target metric is only safe while it stays held out — the instant you start tuning against it, it becomes a proxy too, so a mature setup rotates fresh held-out sets and treats any metric it has selected against as burned. The gaming here is a clean divergence; in practice it is gradual, and you want to watch dtarget over successive selections, not just once (`harness-adv-01`'s control chart is exactly that watch). A single proxy is easy to game; a basket of diverse proxies is harder, though not impossible, and the target still adjudicates. And the target itself has noise — with only eight cases its own interval matters (`evals-inter-01`), so a small dtarget is not yet a regression until it clears its error bar. The invariant survives all of it: never select a system by a number that system was built to move.

## Build

The build in one paragraph: score every candidate on a cheap proxy you can compute each run and on a held-out target you never optimize against; for each candidate compute both means and their change from a fixed baseline; flag any candidate whose proxy rose while its target did not as gamed; and select the candidate with the highest held-out target, never the highest proxy — then confirm the shipped candidate improves the target rather than regressing it. Rotate the held-out set so it never becomes something you tune against, watch the target across successive selections, and treat any metric you have selected on as a proxy from then on.

We opened on the two metrics. The number that proves the point is the shipped system's true quality under each rule:

```
# modules/evals-and-statistics/code/evals-inter-06/ — COMPLETE, run from that directory
$ python3 goodhart.py --select
  select by proxy  -> v2_gamed     (true target 0.520, dtarget -0.080)
  select by target -> v3_genuine   (true target 0.750, dtarget +0.150)
```

Now build your own. Take a real proxy metric from your harness and a held-out quality score, and score three or more candidates — including one you deliberately tuned to the proxy. Your number to beat is not the proxy: it is **the true quality of the system each rule ships, proxy-argmax versus target-argmax** — the proxy rule should ship something no better than, or worse than, baseline while the target rule ships the real best. Bring back both shipped systems' target scores. Good luck.

## Definition of done

- [ ] Two metrics per candidate: a proxy and a held-out target, each a mean over shared cases
- [ ] Deltas of both metrics against a fixed baseline
- [ ] A divergence flag: proxy up while target flat or down
- [ ] Two selection rules: argmax proxy and argmax target
- [ ] Confirmation the proxy rule ships a gamed variant that regresses the target
- [ ] Confirmation the target rule ships the highest-target variant, an improvement
- [ ] `python3 goodhart.py --check` printing SELF-TEST PASS: proxy_gamed, proxy_regresses, target_best, differ, target_improves
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. State Goodhart's law and explain why a proxy that correlates with quality can still mislead selection.
2. v2_gamed had the best proxy (0.85). Why is shipping it a regression, and what number shows that?
3. What is the "divergence" fingerprint of a gamed variant, in terms of dproxy and dtarget?
4. Why must the target metric be held out — what happens to it the moment you tune against it?
5. Your own candidates were selected by both rules. What true-quality score did each rule ship, and did the proxy rule regress the baseline?

## External resources

- Manheim & Garrabrant, *Categorizing Variants of Goodhart's Law* — my summary: the taxonomy of how optimizing a proxy diverges from the target (regressional, extremal, causal, adversarial); read it for which kind of gaming your metric is prone to.
- Strathern, *"Improving ratings: audit in the British University system"* (the origin of the modern phrasing) — my summary: the one-line statement and its bureaucratic case study; read it for why this is old, general, and not specific to machine learning.
- This hub, *evals-inter-01* (the interval that decides whether a delta is real) and *harness-adv-01* (a control chart watching the target over time) — read them for how to tell a real dtarget from noise and how to watch it across successive selections.
