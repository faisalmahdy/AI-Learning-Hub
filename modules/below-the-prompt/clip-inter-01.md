---
id: clip-inter-01
title: Clip the gradient's global norm — or one bad batch blows up the update and corrupts every weight
topic: below-the-prompt
level: intermediate
status: ready
time: 21 min
summary: Training is small steps until a rare batch produces a huge gradient and a plain SGD step scales the update by its norm, lurching the weights a huge distance and often to NaN. Clip by global norm — rescale the whole gradient to a threshold — and the spike is capped while its direction is preserved. On a run where normal batches have norm 0.5 and one spike has norm 100, the unclipped spike step moves the weights by 10.0 (200× normal) to |w|=10.2; global-norm clipping caps it at 0.1 (|w|=0.3) at cosine 1.000, while elementwise clamping distorts the direction (cosine 0.990).
eli5: Most steps while learning are gentle nudges, but every so often one wildly wrong nudge tries to shove everything off a cliff. Gradient clipping puts a cap on how big any single nudge can be, so a freak step can't wreck all the careful progress — and it caps it in a way that still points the same direction you meant to go.
---

## Why this module

Training survives thousands of good gradient steps and can be killed by a single bad one, unless you cap how far any step may move the weights.

Most of training is small, well-behaved steps. Each batch produces a gradient, and a plain SGD update moves the weights by the learning rate times that gradient — a gentle nudge downhill. But gradients have a tail. A corrupted example, an unlucky loss spike, a numerical edge in one batch can produce a gradient whose norm is orders of magnitude larger than normal. The update scales directly with that norm, so the weights lurch a huge distance in a single step, undoing thousands of careful updates and frequently sending the loss straight to NaN, from which the run never recovers.

You cannot fix this by lowering the learning rate. A rate small enough to survive a norm-100 spike would make every normal norm-0.5 step a hundred times too small to learn anything — you would trade a rare catastrophe for permanent uselessness. The problem is not the size of the average gradient, which the learning rate is correctly tuned for; it is the size of the rare outlier. You need something that leaves the body of the distribution alone and only touches the tail.

Gradient clipping by global norm is exactly that. Compute the norm of the entire gradient vector across all parameters; if it exceeds a threshold, rescale the whole vector so its norm becomes the threshold. Every component is multiplied by the same factor, so the update points in exactly the same direction as the raw gradient — you still step the way the gradient said to, just no farther than the cap. Normal steps, whose norm is already below the threshold, pass through untouched. The rare spike is the only thing clipped, and it is clipped to a sane size.

The tempting shortcut — clamp each component to a range independently — is subtly wrong, because it changes the direction. On the fixture, normal batches have gradient norm 0.5 and one spike has norm 100, with a clip threshold of 1.0 and learning rate 0.1. Unclipped, the spike step moves the weights by 10.0 — 200 times a normal step — leaving them at norm 10.2. Global-norm clipping caps that step at 0.1 and keeps the direction (cosine 1.000); elementwise clamping distorts the direction (cosine 0.990) and does not even respect the threshold.

**A rare batch can produce a gradient far larger than normal, and a plain step scales the update by its norm, so one spike lurches the weights and often NaNs the run; clipping the global norm caps the update while preserving direction, and you cannot get the same protection by lowering the learning rate.**

## Concepts

The key insight is that clipping should act on the whole gradient as one vector, not on its pieces. The gradient of the loss with respect to all parameters is a single vector in a very high-dimensional space; its norm is how big a step it wants, and its direction is which way. Exploding gradients are a norm problem — the direction is usually fine, the length is insane. So the right intervention rescales the length and leaves the direction alone: if the norm exceeds a threshold c, multiply the entire vector by c divided by its norm. That makes the new norm exactly c, and because every component got the same multiplier, the direction is untouched. This is global-norm clipping, and it is the standard.

<svg role="img" aria-label="A long spike gradient vector, its global-norm-clipped version pointing the same way but short, and its elementwise-clamped version pointing off at an angle" viewBox="0 0 470 185" width="470" height="185">
  <rect x="0" y="0" width="470" height="185" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">the spike gradient and its two clippings (from the origin)</text>
  <line x1="50" y1="160" x2="440" y2="160" stroke="var(--line)"/>
  <line x1="50" y1="160" x2="50" y2="35" stroke="var(--line)"/>
  <line x1="50" y1="160" x2="290" y2="45" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="250" y="42" font-family="var(--mono)" font-size="8" fill="var(--s2)">raw spike [60,80], norm 100</text>
  <line x1="50" y1="160" x2="98" y2="137" stroke="var(--acc-line)" stroke-width="3"/>
  <text x="104" y="132" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">global-norm [0.6,0.8] — same direction, norm 1</text>
  <line x1="50" y1="160" x2="110" y2="100" stroke="var(--s1)" stroke-width="3"/>
  <text x="116" y="96" font-family="var(--mono)" font-size="8" fill="var(--s1)">elementwise [1,1] — tilted off, norm 1.41</text>
</svg>
^ Global-norm clipping lands on the same ray as the raw spike (a shorter arrow in the identical direction); elementwise clamping lands off that ray, so its step is no longer along the descent direction.

Preserving direction matters because the direction is the useful information. The gradient points in the locally steepest-descent direction; a step along it (of any positive length) reduces the loss. Global-norm clipping takes a shorter step in that same descent direction — still downhill, just cautious. Elementwise clamping, by contrast, shortens the large components more than the small ones, which tilts the vector toward the small-component directions. The clamped update can point somewhere that is not downhill at all, so you have not just taken a smaller step — you have taken a step in the wrong direction. Protecting against blow-ups is not worth corrupting the direction, and global-norm clipping does not force that trade.

The threshold plays the role the learning rate cannot. The learning rate sets the scale of a normal step; the clip threshold sets the maximum scale of any step. With both, normal batches move by learning-rate times their norm (unclipped, because they are below threshold), and pathological batches move by at most learning-rate times the threshold. That decoupling is the whole point: you tune the learning rate for the common case and the clip threshold for the worst case, independently. A threshold set just above the typical gradient norm clips almost nothing in normal training and only engages when something has genuinely gone wrong.

This is why gradient clipping is close to free insurance and is on by default in most large-model training. It costs one norm computation and, on the rare clip, one rescale; it never hurts a healthy step; and it converts the most common cause of a dead training run — a single exploding-gradient batch — into a non-event. Recurrent networks, transformers, anything deep enough to occasionally produce a giant gradient, all ship with it. The failure it prevents is abrupt and total (a NaN loss, an unrecoverable run), which makes the cheap guard overwhelmingly worth it.

**Global-norm clipping rescales the whole gradient vector to a threshold, capping the step length while preserving the descent direction; the threshold bounds the worst case independently of the learning rate that tunes the normal case, and elementwise clamping is wrong because it tilts the direction off downhill.**

## Worked example

The fixture is a short run's gradients, a learning rate, and a clip threshold.

```json filename=modules/below-the-prompt/code/clip-inter-01/grads.json:3-11 COMPLETE
  "lr": 0.1,
  "clip": 1.0,
  "gradients": [
    [0.3, 0.4],
    [0.3, 0.4],
    [60.0, 80.0],
    [0.3, 0.4],
    [0.3, 0.4]
  ]
```

Four normal batches with gradient norm 0.5, and one spike (batch 2) with norm 100. The clip rescales the whole vector to the threshold when its norm exceeds it — same direction, capped length.

```python filename=modules/below-the-prompt/code/clip-inter-01/clip.py:54-57 COMPLETE
def clip_global(g, c):
    """Rescale the whole vector so its norm is at most c -- same direction, capped length."""
    n = norm(g)
    return scale(g, c / n) if n > c else list(g)
```

The SGD loop steps the weights by the learning rate times the (optionally clipped) gradient and tracks the update size and running weight norm.

```python filename=modules/below-the-prompt/code/clip-inter-01/clip.py:70-79 COMPLETE
def run(grads, lr, c, clipper):
    """SGD trajectory: return the per-step update norms and the final weight vector."""
    w = [0.0, 0.0]
    steps = []
    for g in grads:
        gc = clipper(g, c) if clipper else g
        update = scale(gc, lr)
        w = [wi - ui for wi, ui in zip(w, update)]
        steps.append({"grad_norm": norm(g), "step": norm(update), "w_norm": norm(w)})
    return steps, w
```

Predict: unclipped, the spike batch moves the weights by 0.1 × 100 = 10.0, a hundred-fold jump that dominates the whole run; clipped, it moves by at most 0.1 × 1.0 = 0.1, the same as a normal step. Run it.

```text filename=modules/below-the-prompt/code/clip-inter-01/clip.py --steps
STEPS — per-step update size and running weight norm (lr 0.10, clip 1.0)
--------------------------------------------------------------
  UNCLIPPED
    batch 0  grad_norm    0.50  update  0.050  |w|  0.050
    batch 1  grad_norm    0.50  update  0.050  |w|  0.100
    batch 2  grad_norm  100.00  update 10.000  |w| 10.100  <-- spike batch
    batch 3  grad_norm    0.50  update  0.050  |w| 10.150
    batch 4  grad_norm    0.50  update  0.050  |w| 10.200
    final |w| = 10.200

  GLOBAL-NORM CLIP
    batch 0  grad_norm    0.50  update  0.050  |w|  0.050
    batch 1  grad_norm    0.50  update  0.050  |w|  0.100
    batch 2  grad_norm  100.00  update  0.100  |w|  0.200  <-- spike batch
    batch 3  grad_norm    0.50  update  0.050  |w|  0.300
    final |w| = 0.300
```

Unclipped, batch 2 moves the weights by 10.000 — 200 times a normal 0.050 step — and the weight norm jumps from 0.100 to 10.100 in one step. The two good steps afterward barely register against that; the run is now dominated by one bad batch, and in a real model this is where the loss goes NaN. Clipped, batch 2's gradient still has norm 100, but the update is 0.100, and the weight norm inches from 0.100 to 0.200 like any other step. The final weight norm is 0.300 clipped versus 10.200 unclipped — a 34-fold difference from a single spike. The clip did nothing to the four normal batches; it only tamed the one that needed it.

<svg role="img" aria-label="Running weight norm over five batches: unclipped jumps to about 10 at the spike and stays there; clipped rises smoothly to 0.3" viewBox="0 0 470 195" width="470" height="195">
  <rect x="0" y="0" width="470" height="195" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">running weight norm |w| across batches (spike at batch 2)</text>
  <line x1="45" y1="165" x2="450" y2="165" stroke="var(--line)"/>
  <line x1="45" y1="40" x2="45" y2="165" stroke="var(--line)"/>
  <line x1="205" y1="40" x2="205" y2="165" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="150" y="52" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">spike batch</text>
  <polyline points="85,163 145,161 205,55 285,54 365,53" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <g fill="var(--s2)"><circle cx="85" cy="163" r="3"/><circle cx="145" cy="161" r="3"/><circle cx="205" cy="55" r="4"/><circle cx="285" cy="54" r="3"/><circle cx="365" cy="53" r="3"/></g>
  <text x="215" y="60" font-family="var(--mono)" font-size="8" fill="var(--s2)">unclipped: leaps to 10.1 and stays</text>
  <polyline points="85,163 145,161 205,159 285,157 365,156" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <g fill="var(--s1)"><circle cx="85" cy="163" r="3"/><circle cx="145" cy="161" r="3"/><circle cx="205" cy="159" r="3"/><circle cx="285" cy="157" r="3"/><circle cx="365" cy="156" r="3"/></g>
  <text x="230" y="150" font-family="var(--mono)" font-size="8" fill="var(--s1)">clipped: smooth to 0.3</text>
</svg>
^ Unclipped, the weight norm leaps two orders of magnitude at the spike batch and never comes back; clipped, the spike is just another small step and the trajectory stays bounded.

## Build

Reproduce the run. Pure standard library, deterministic, so the 10.0 unclipped spike step, the 0.1 clipped cap, and the cosine numbers come out exactly.

Run `--steps` for the two trajectories, `--direction` for the clipping comparison on the spike, `--check` for the gate. The direction view is where global-norm and elementwise clipping part ways.

```text filename=modules/below-the-prompt/code/clip-inter-01/clip.py --direction
DIRECTION — the spike gradient [60.0, 80.0] under each clip (threshold 1.0)
--------------------------------------------------------------
  global-norm:  [0.6, 0.8]   norm 1.000   cosine-to-original 1.000
  elementwise:  [1.0, 1.0]   norm 1.414   cosine-to-original 0.990
--------------------------------------------------------------
  global-norm caps the norm at the threshold and keeps the direction; elementwise does neither.
```

The elementwise clamp is the wrong tool, and its definition shows why — it clamps each component independently, so components that started far apart get pulled to the same rail.

```python filename=modules/below-the-prompt/code/clip-inter-01/clip.py:60-62 COMPLETE
def clip_elementwise(g, c):
    """Clamp each component to [-c, c] independently -- changes the direction (the wrong way)."""
    return [max(-c, min(c, x)) for x in g]
```

Global-norm clipping turns [60, 80] into [0.6, 0.8]: norm exactly 1.0 and cosine exactly 1.000 to the original, because both components were scaled by the same 0.01. Elementwise clamping turns it into [1.0, 1.0]: the two components were clamped by different amounts (60 down to 1, 80 down to 1), so the vector now points at 45° instead of along [3, 4], a cosine of 0.990 — and its norm is 1.414, above the threshold it was supposed to enforce. <svg role="img" aria-label="Per-batch update size: unclipped shows four tiny bars and one towering 10.0 spike; clipped shows five equal small bars" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">update size per batch (spike = batch 2)</text>
  <line x1="40" y1="150" x2="450" y2="150" stroke="var(--line)"/>
  <text x="70" y="40" font-family="var(--mono)" font-size="9" fill="var(--s2)">unclipped</text>
  <g fill="var(--s2)"><rect x="55" y="148" width="18" height="2"/><rect x="78" y="148" width="18" height="2"/><rect x="101" y="48" width="18" height="102"/><rect x="124" y="148" width="18" height="2"/><rect x="147" y="148" width="18" height="2"/></g>
  <text x="90" y="44" font-family="var(--mono)" font-size="8" fill="var(--s2)">10.0</text>
  <text x="290" y="40" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">global-norm clipped</text>
  <g fill="var(--acc-line)"><rect x="290" y="145" width="18" height="5"/><rect x="313" y="145" width="18" height="5"/><rect x="336" y="140" width="18" height="10"/><rect x="359" y="145" width="18" height="5"/><rect x="382" y="145" width="18" height="5"/></g>
  <text x="330" y="132" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">0.1 cap</text>
</svg>
^ Unclipped, batch 2's update towers at 10.0 over four barely-visible 0.05 steps; clipped, the spike is capped to 0.1 and every batch is the same small size.

The self-test pins both the blow-up and the direction property.

```python filename=modules/below-the-prompt/code/clip-inter-01/clip.py:124-127 COMPLETE
    unclipped_blows_up = max_unclipped > 100 * (normal * lr)
    print("  unclipped's biggest step dwarfs a normal step = %s (%.3f vs %.3f)" % (unclipped_blows_up, max_unclipped, normal * lr))

    clip_caps_step = max_clipped <= c * lr + 1e-9
    print("  global-norm clip caps every step at threshold*lr = %s (max %.3f <= %.3f)" % (clip_caps_step, max_clipped, c * lr))
```

```text filename=modules/below-the-prompt/code/clip-inter-01/clip.py --check
SELF-TEST — unclipped blows up on the spike; global-norm clipping caps the step and preserves direction
--------------------------------------------------------------------------------------------------------
  unclipped's biggest step dwarfs a normal step = True (10.000 vs 0.050)
  global-norm clip caps every step at threshold*lr = True (max 0.100 <= 0.100)
  clipped weights stay bounded, unclipped do not = True (|w| 0.300 vs 10.200)
  global-norm clip preserves the gradient direction = True (cosine 1.0000)
  elementwise clamp distorts the direction = True (cosine 0.9899)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  unclipped_blows_up=True  clip_caps_step=True  clip_bounds_weights=True  global_keeps_direction=True  elementwise_distorts=True
```

Five True flags. Unclipped_blows_up: the biggest unclipped step is 10.0 against a normal 0.05. Clip_caps_step: every clipped step is at most threshold times learning rate, 0.1. Clip_bounds_weights: clipped weights end at 0.3, unclipped at 10.2. Global_keeps_direction: the clipped spike has cosine exactly 1.0 to the original. Elementwise_distorts: the clamped spike has cosine 0.99, off the descent direction. The last two flags together are the argument for global-norm over elementwise: same protection, but only one keeps the step pointing downhill.

**The cosine flags decide the method — global-norm clipping caps the spike at cosine 1.000 while elementwise clamping drops to 0.990, so only global-norm gives you the smaller step without a wrong-direction step.**

## Definition of done

You are done when you reproduce the spike's blow-up and its cure, and can explain why the cure preserves direction.

Concretely: `--steps` shows the unclipped spike moving the weights by 10.0 to a final norm of 10.2, and the clipped run capping it at 0.1 to a final norm of 0.3; `--direction` shows global-norm clipping at cosine 1.000 and norm 1.0 versus elementwise at cosine 0.990 and norm 1.414; `--check` prints PASS with five True flags. You can explain that exploding gradients are a norm problem, that rescaling the whole vector by threshold-over-norm caps the length while preserving direction, and that the clip threshold bounds the worst case independently of the learning rate. You can explain why elementwise clamping distorts the direction and can therefore step somewhere not downhill.

The habit to carry: clip the global gradient norm in any training loop deep or recurrent enough to occasionally spike, set the threshold just above the typical gradient norm so it engages only in emergencies, and never substitute elementwise clamping. When a training run dies with a sudden NaN loss after many healthy steps, suspect an unclipped exploding gradient before anything subtle — it is the most common cause and the cheapest to prevent.

## Boss fight

The instructive failure is a transformer run that trains beautifully for hours and then NaNs in a single step.

A model trains smoothly, loss falling, and then at some step the loss jumps to NaN and every subsequent step is NaN — the run is dead and no checkpoint after that point is usable. The logs show one batch with a gradient norm hundreds of times the running average, right before the NaN; a rare bad example produced an enormous gradient, the unclipped update pushed a weight to a huge value, and the next forward pass overflowed. Lowering the learning rate only delays it and slows all the healthy training in between. The fix is global-norm gradient clipping at a threshold a little above the typical norm: the spike batch is rescaled to a sane step, the weights never leave their healthy range, and the run continues. Almost every production training config ships with clipping on for exactly this reason.

Your turn, two moves. First, confirm the learning rate is not the lever. Lower `lr` until the unclipped spike step is small and check that the four normal steps are now uselessly tiny — you cannot separate the spike from the body with the learning rate, which is what the independent clip threshold is for. Second, make the spike direction matter more: use a spike like [3, 400] (mostly in one component) and compare global-norm versus elementwise clipping's cosine to the original; confirm elementwise distorts it badly (it clamps the 400 far more than the 3, nearly axis-aligning the update) while global-norm stays at cosine 1.0 — the more lopsided the spike, the worse elementwise clamping corrupts the direction.

## External resources

The paper that introduced gradient clipping for training, Pascanu, Mikolov, and Bengio's "On the difficulty of training recurrent neural networks" (2013), analyzes exploding gradients and proposes rescaling by the global norm — the exact operation this module implements.

Any deep-learning framework's clip-by-global-norm utility (PyTorch's clip_grad_norm_, TensorFlow's clip_by_global_norm) is the production form; reading its docs shows the convention of computing one norm over all parameters and rescaling them together, and contrasts it with the direction-distorting clip-by-value.

Large-model training reports (GPT, PaLM, and others) routinely list gradient clipping among their default stabilizers alongside learning-rate warmup and loss scaling, which shows how standard the guard has become for deep transformer training.
