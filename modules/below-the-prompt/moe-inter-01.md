---
id: moe-inter-01
title: Balance the expert load and cap it — or a Mixture-of-Experts router sends every token to a few experts and starves the rest
topic: below-the-prompt
level: intermediate
status: ready
time: 17 min
summary: A Mixture-of-Experts layer has many expert sub-networks and a router that sends each token to only one or a few, so the model has huge capacity but activates a small slice per token. The catch is the router. Nothing in "pick the highest-scoring expert" forces the load to spread, so training can drive the router into a corner where a handful of experts win almost every token and the rest receive almost none — those starved experts never get gradients, never improve, and stay dead weight (routing collapse), so a model that paid for many experts effectively runs a few. Two mechanisms keep the load balanced: an auxiliary load-balancing loss (E × Σ fraction-to-e × mean-gate-e, minimized at 1.0 when uniform and rising as load concentrates) added to training to push the router toward spreading tokens, and an expert capacity (capacity_factor × tokens / experts) that hard-caps each expert and drops the overflow. On a fixture where the router prefers expert 0, top-1 routing sends 5 of 8 tokens there (2 to expert 1, 1 to expert 2, 0 to expert 3 — a dead expert), the load-balancing loss is 1.50 against the balanced 1.00, and a capacity of 2 keeps 2 of expert 0's tokens and drops 3.
eli5: Imagine a workshop with many specialists and a dispatcher who hands each job to whichever specialist looks best. If the dispatcher keeps picking the same one or two, those get swamped while the others sit idle and never get good at anything — you paid for a big team but really have a tiny one. Two fixes: score the dispatcher on keeping everyone busy (a penalty for lopsided assignment), and give each specialist a limit on how many jobs they can take, so the overflow gets turned away instead of piling on one desk.
---

## Why this module

A Mixture-of-Experts model's whole promise is many experts specializing in different things, but the router that assigns tokens has no built-in reason to use them evenly — so left alone it concentrates work on a few winners and lets the rest atrophy, quietly converting a large model back into a small one.

The MoE design decouples parameter count from compute: you can have dozens or hundreds of expert feed-forward networks, but a router sends each token to only one or two of them, so a forward pass touches a small fraction of the parameters. The efficiency is real, and it hinges entirely on the router spreading tokens across experts. Here is the problem: the router is trained to minimize the main loss, and the main loss is happiest when tokens go to whichever experts are already best. Early in training a few experts get slightly better, so the router sends them slightly more tokens, so they get more gradient and improve faster, so the router sends them even more — a rich-get-richer feedback loop that ends with a handful of experts doing nearly all the work and the rest receiving nearly nothing. The starved experts get no gradient, never improve, and remain dead weight. This is routing collapse, and it means a model with sixty-four experts might be effectively running four.

**A top-1 MoE router optimizing only the main loss has every incentive to concentrate tokens on the experts that are already good — a rich-get-richer spiral that starves the rest into dead experts, wasting the capacity the many experts were supposed to provide.**

Two mechanisms counter it. The first is an auxiliary load-balancing loss added to the training objective: E times the sum over experts of (fraction of tokens routed there) times (mean gate probability there). It bottoms out at 1.0 when the load is perfectly uniform and rises as the load concentrates, so adding it to the loss creates a gradient that actively pushes the router toward spreading tokens, opposing the collapse the main loss invites. The second is an expert *capacity*: each expert can process only a fixed number of tokens per batch — capacity_factor times tokens over experts — and any tokens beyond that overflow and are dropped (skipped or passed straight through). Capacity is a hard cap that both bounds the damage of imbalance and, just as importantly, keeps each expert's workload a fixed size so the computation stays rectangular for the hardware. The load-balancing loss discourages imbalance; the capacity survives it. This module routes a batch, measures the imbalance, and applies the cap.

## Concepts

**Top-1 routing** sends each token to its highest-gate expert. It is the cheapest routing, and the most prone to collapse, because nothing spreads the load.

```python filename=modules/below-the-prompt/code/moe-inter-01/moe.py:43-45 COMPLETE
def top1_route(gates):
    """Each token goes to the expert with the highest gate probability (argmax)."""
    return [max(range(len(g)), key=lambda e: g[e]) for g in gates]
```

**The load-balancing loss** measures imbalance: E × Σ (fraction routed to e) × (mean gate for e). It is 1.0 when the load is uniform and larger when both the routed fraction and the gate mass concentrate on the same experts.

```python filename=modules/below-the-prompt/code/moe-inter-01/moe.py:53-58 COMPLETE
def balance_loss(gates, routes, num_experts):
    """Switch-Transformer aux loss: E * sum_e (fraction routed to e) * (mean gate for e). 1.0 when balanced."""
    n = len(gates)
    frac = [routes.count(e) / n for e in range(num_experts)]
    mean_gate = [sum(g[e] for g in gates) / n for e in range(num_experts)]
    return num_experts * sum(frac[e] * mean_gate[e] for e in range(num_experts))
```

**Expert capacity** is a per-expert token limit, capacity_factor × tokens / experts. Tokens beyond it overflow and are dropped, bounding imbalance and keeping the compute a fixed shape.

<svg role="img" aria-label="A router sends five of eight tokens to expert 0, two to expert 1, one to expert 2, and none to expert 3, which is dead" viewBox="0 0 300 100" width="300" height="100">
  <rect x="6" y="42" width="50" height="18" fill="none" stroke="var(--line)"/><text x="14" y="55" fill="var(--ink)" font-size="8">router</text>
  <g stroke="var(--s2)"><line x1="56" y1="48" x2="120" y2="24"/><line x1="56" y1="49" x2="120" y2="26"/><line x1="56" y1="50" x2="120" y2="28"/><line x1="56" y1="51" x2="120" y2="30"/><line x1="56" y1="52" x2="120" y2="32"/></g>
  <line x1="56" y1="54" x2="120" y2="52" stroke="var(--s1)"/><line x1="56" y1="55" x2="120" y2="54" stroke="var(--s1)"/>
  <line x1="56" y1="57" x2="120" y2="72" stroke="var(--s1)"/>
  <rect x="122" y="20" width="60" height="16" fill="var(--s2)"/><text x="186" y="32" fill="var(--muted)" font-size="7">expert 0: 5</text>
  <rect x="122" y="44" width="26" height="16" fill="var(--s1)"/><text x="186" y="56" fill="var(--muted)" font-size="7">expert 1: 2</text>
  <rect x="122" y="66" width="14" height="16" fill="var(--s1)"/><text x="186" y="78" fill="var(--muted)" font-size="7">expert 2: 1</text>
  <rect x="122" y="86" width="4" height="10" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/><text x="140" y="95" fill="var(--muted)" font-size="7">expert 3: 0 (dead)</text>
</svg>
^ Top-1 routing funnels five of eight tokens to expert 0 and none to expert 3, so most of the load concentrates on one expert while another gets no gradient at all and dies.

**A top-1 router does not spread load on its own, so add a load-balancing loss (minimized at 1.0 for uniform load) to push tokens across experts, and an expert capacity to hard-cap each expert's tokens and drop the overflow.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/moe-inter-01/moe.py

The fixture is eight tokens' router gates over four experts, chosen so the router favors expert 0, with a capacity factor of 1.0.

```json filename=modules/below-the-prompt/code/moe-inter-01/moe.json:3-14 COMPLETE
  "gates": [
    [0.70, 0.10, 0.10, 0.10],
    [0.60, 0.20, 0.10, 0.10],
    [0.50, 0.30, 0.10, 0.10],
    [0.80, 0.10, 0.05, 0.05],
    [0.40, 0.40, 0.10, 0.10],
    [0.20, 0.50, 0.20, 0.10],
    [0.10, 0.60, 0.20, 0.10],
    [0.30, 0.20, 0.40, 0.10]
  ],
  "num_experts": 4,
  "capacity_factor": 1.0
```

Run `--route` to route the batch and apply capacity.

```text filename=--route
ROUTE — top-1 expert load (8 tokens, 4 experts)
--------------------------------------------------------
  expert   tokens routed   after capacity 2
  0        5               2  <- overflow
  1        2               2
  2        1               1
  3        0               0  <- DEAD (no tokens)
```

Top-1 routing produces a lopsided load: expert 0 receives five of the eight tokens, expert 1 two, expert 2 one, and expert 3 none. Expert 3 is dead — it got no tokens, so it will get no gradient this step, and if this pattern holds it never learns anything and the capacity it represents is wasted. That is the collapse failure in miniature: four experts, but the load of roughly one and a half. The capacity column shows the hard cap doing its job and its cost. With eight tokens over four experts and a capacity factor of 1.0, each expert may take two tokens. Experts 1 and 2 are under the cap and keep all their tokens; expert 0 wanted five but can keep only two, so three tokens overflow and are dropped. Those three tokens get no expert applied — in a real layer they pass through the residual connection unchanged — so imbalance does not just waste experts, it degrades the tokens that lose the capacity lottery. Capacity bounded expert 0 to two tokens and kept the computation rectangular, but the price was three dropped tokens, which only balancing the load in the first place would avoid.

<svg role="img" aria-label="Expert loads are 5, 2, 1, 0; the capacity line at 2 caps expert 0, dropping 3 tokens, and expert 3 is dead" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">tokens routed per expert; capacity = 2</text>
  <line x1="30" y1="84" x2="290" y2="84" stroke="var(--grid)"/>
  <line x1="30" y1="44" x2="290" y2="44" stroke="var(--ink)" stroke-dasharray="3 2"/><text x="250" y="42" fill="var(--muted)" font-size="7">cap 2</text>
  <rect x="45" y="24" width="34" height="60" fill="var(--s2)"/><text x="52" y="94" fill="var(--muted)" font-size="7">e0: 5</text>
  <rect x="45" y="24" width="34" height="16" fill="var(--s2)" opacity="0.4"/><text x="82" y="34" fill="var(--s2)" font-size="6">3 dropped</text>
  <rect x="115" y="60" width="34" height="24" fill="var(--s1)"/><text x="122" y="94" fill="var(--muted)" font-size="7">e1: 2</text>
  <rect x="185" y="72" width="34" height="12" fill="var(--s1)"/><text x="192" y="94" fill="var(--muted)" font-size="7">e2: 1</text>
  <rect x="255" y="82" width="34" height="2" fill="none" stroke="var(--line)"/><text x="258" y="94" fill="var(--muted)" font-size="7">e3: 0 dead</text>
  <text x="30" y="18" fill="var(--muted)" font-size="7">▲ 5</text>
</svg>
^ Loads are 5, 2, 1, 0 — expert 0 overflows the capacity of 2 (three tokens dropped) and expert 3 is dead — the concentration that a load-balancing loss exists to prevent.

## Build

How does training push back on this? Run `--balance` to compute the auxiliary loss.

```text filename=--balance
BALANCE — the load-balancing auxiliary loss (1.0 = perfectly balanced)
----------------------------------------------------------
  fraction routed per expert:  [0.625, 0.25, 0.125, 0.0]
  mean gate per expert:        [0.45, 0.3, 0.156, 0.094]
  load-balancing loss:         1.503   (balanced minimum = 1.000)
```

The loss multiplies two vectors that both peak at expert 0: the fraction of tokens actually routed there (0.625) and the mean gate probability the router assigned it (0.45). When both are high on the same expert, their product is large, and summed over experts and scaled by E = 4 the loss comes to 1.503 — half again above the balanced minimum of 1.0. The design of this loss is subtle and worth seeing: it uses the routed *fraction* (a hard count, which has no gradient) multiplied by the mean *gate* (a soft probability, which does). Multiplying the two makes the loss differentiable through the gate while still being driven by the actual load, so gradient descent can lower it by nudging the router's probabilities away from the overloaded experts. Add this term to the main loss and the router feels a continuous pressure to flatten the fraction vector toward uniform — pushing expert 3's fraction up off zero and expert 0's down — which is exactly the counterweight to the rich-get-richer pull. At perfect balance every fraction is 1/E and the loss hits its floor of 1.0; the gap above 1.0 is a direct readout of how collapsed the routing is, and driving it down is what keeps all the experts alive and earning their parameters.

<svg role="img" aria-label="The load-balancing loss is 1.503 for the collapsed routing versus the balanced minimum of 1.0" viewBox="0 0 300 84" width="300" height="84">
  <text x="6" y="12" fill="var(--muted)" font-size="8">load-balancing loss (1.0 = uniform, higher = collapsed)</text>
  <line x1="40" y1="60" x2="290" y2="60" stroke="var(--grid)"/>
  <line x1="40" y1="24" x2="290" y2="24" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="248" y="22" fill="var(--muted)" font-size="7">min 1.0</text>
  <rect x="70" y="40" width="40" height="20" fill="var(--s1)"/><text x="76" y="74" fill="var(--muted)" font-size="7">balanced 1.00</text>
  <rect x="170" y="24" width="40" height="36" fill="var(--s2)"/><text x="170" y="74" fill="var(--muted)" font-size="7">this routing 1.50</text>
  <text x="6" y="82" fill="var(--muted)" font-size="8">the excess above 1.0 is how collapsed the routing is; training drives it down</text>
</svg>
^ The collapsed routing scores 1.503 against the balanced floor of 1.0, and because the loss is differentiable through the gate, adding it to training gives the router gradient to flatten the load back toward uniform.

## Definition of done

The self-test pins the failure and both fixes: the load is imbalanced with a dead expert, the aux loss exceeds 1.0, capacity caps each expert, and the overflow is dropped.

```python filename=modules/below-the-prompt/code/moe-inter-01/moe.py:117-128 COMPLETE
    imbalanced = max(ld) >= 3 * (min(ld) + 1)
    print("  the load is imbalanced (max %d vs min %d) = %s" % (max(ld), min(ld), imbalanced))

    has_dead_expert = min(ld) == 0
    print("  at least one expert is dead (gets no tokens) = %s (expert %d)" % (has_dead_expert, ld.index(0)))

    loss = balance_loss(gates, routes, E)
    loss_above_balanced = loss > 1.0
    print("  the load-balancing loss exceeds the balanced 1.0 = %s (%.3f)" % (loss_above_balanced, loss))

    capacity_caps = all(k <= cap for k in kept)
    print("  capacity caps every expert's kept tokens at %d = %s (kept %s)" % (cap, capacity_caps, kept))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the load is imbalanced with a dead expert; the aux loss exceeds 1.0; capacity caps load and drops overflow
----------------------------------------------------------------------------------------------------------------------
  the load is imbalanced (max 5 vs min 0) = True
  at least one expert is dead (gets no tokens) = True (expert 3)
  the load-balancing loss exceeds the balanced 1.0 = True (1.503)
  capacity caps every expert's kept tokens at 2 = True (kept [2, 2, 1, 0])
  the overflow beyond capacity is dropped = True (3 dropped)
```

**Done means routing collapse and its two remedies are proven: top-1 routing loads the experts [5, 2, 1, 0] — expert 3 dead — the load-balancing loss is 1.503 above the balanced 1.0 (a differentiable readout of the imbalance the training objective can lower), and a capacity of 2 caps every expert's kept tokens ([2, 2, 1, 0]) and drops the 3 that overflow expert 0.**

## Boss fight

Predict the two tensions the two fixes create. It is tempting to just crank the balancing loss and the capacity until nothing drops.

The first trap is that the load-balancing loss fights the main loss, and weighting it wrong loses either quality or balance. It is an *auxiliary* loss — added with a coefficient — and that coefficient is a real trade-off: too small and the rich-get-richer pull wins, collapse returns, and experts die; too large and you force uniform routing even when uneven routing is genuinely better, sending tokens to experts that do not suit them and hurting the main objective. Perfect balance is not the goal — *useful* balance is — because some imbalance reflects real structure (some kinds of token are simply more common). So the coefficient is tuned to keep every expert alive and adequately trained without overriding the router's legitimate specialization, and a router that is perfectly balanced but ignores the input is as useless as one that is collapsed. Balance is a constraint on the main objective, not a replacement for it.

```python filename=modules/below-the-prompt/code/moe-inter-01/moe.py:66-75 COMPLETE
def apply_capacity(routes, num_experts, cap):
    """Keep up to `cap` tokens per expert in arrival order; count the rest as dropped."""
    kept = [0] * num_experts
    dropped = 0
    for e in routes:
        if kept[e] < cap:
            kept[e] += 1
        else:
            dropped += 1
    return kept, dropped
```

The second trap is that capacity trades dropped tokens against wasted compute, and both ends are costly. A tight capacity factor (near 1.0) keeps the compute small but drops many tokens whenever the load is uneven — and this fixture dropped three of eight, which at inference means those tokens skip the expert layer entirely and get a worse representation. A loose capacity factor (say 2.0) drops almost nothing but reserves twice the buffer per expert, most of which sits empty under imbalance, wasting memory and compute — the padding that keeps the batch rectangular is real cost. So capacity factor is tuned against the load distribution: high enough that few tokens drop, low enough that the buffers are not mostly empty, and the better the load balancing works, the tighter you can set it, because balanced load means each expert's actual count is near its fair share and little padding is needed. The two mechanisms are coupled: good load balancing lets you run a tight, cheap capacity; poor balancing forces you to choose between dropping tokens and paying for empty buffers. And the deployment detail that bites — an expert's capacity is per-batch, so the same token can be served or dropped depending on what else is in its batch, a nondeterminism that has to be handled for reproducible inference.

**A Mixture-of-Experts router does not balance load on its own, so top-1 routing collapses onto a few experts and starves the rest into dead weight — countered by an auxiliary load-balancing loss (differentiable through the gate, minimized at uniform load) and an expert capacity that caps each expert and drops overflow — but the balancing loss is weighted against the main loss (too strong forces useless uniformity, too weak lets collapse return, since useful balance is the goal, not perfect balance), and the capacity factor trades dropped tokens against empty-buffer compute, with the two coupled: good balancing is what lets you run a tight, cheap capacity.**

## External resources

The Switch Transformer and GShard papers (Fedus et al.; Lepikhin et al.) — the load-balancing auxiliary loss, expert capacity and the capacity factor, top-1 versus top-2 routing, and the token-dropping behavior modeled here.

Any survey of Mixture-of-Experts architectures — the routing variants (top-k, expert choice, hash routing), the collapse/dead-expert failure mode, and the balance-versus-quality and capacity-versus-drop trade-offs.

The companion "share key/value heads across query heads" and "the KV cache — reuse the past" modules — all three are ways large models control which parameters or state are activated per token, trading full dense computation for a routed or reused subset, so together they cover the sparsity techniques that make very large models tractable.
