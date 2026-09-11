---
id: adamw-inter-01
title: Decouple weight decay from the gradient (AdamW) — as an L2 loss term, Adam's per-parameter scaling under-regularizes the high-gradient weights
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: Adam adapts the step size per parameter by dividing the update by sqrt(v), the running average of squared gradients, so a parameter with consistently large gradients takes proportionally smaller steps. Weight decay wants the opposite — pull every weight toward zero by the same fraction each step, a uniform regularization independent of gradient size. The mistake is implementing weight decay as an L2 penalty added to the loss: since the gradient of (wd/2)·w² is wd·w, adding L2 to the loss adds wd·w to the gradient, which then flows through Adam's 1/sqrt(v) scaling like everything else. The decay a weight actually receives becomes (lr·wd·w)/sqrt(v), inversely scaled by the parameter's gradient RMS — so high-gradient parameters (the ones a big model has many of) get their decay shrunk while low-gradient parameters get more, and the uniform regularization you asked for arrives wildly non-uniform. AdamW decouples the decay: it runs the Adam update on the raw loss gradient and separately subtracts lr·wd·w from each weight, outside the adaptive scaling, so every weight decays by the same fraction lr·wd regardless of gradient history. It is a one-line change in where the decay is applied, and it is why AdamW, not Adam-with-L2, is the default for training modern models. On a fixture where a "steep" parameter has 16× the second moment of a "flat" one (4× the gradient RMS), coupled L2 decays steep by 0.0025 and flat by 0.01 — four times less for the steep one — while AdamW decays both by 0.01.
eli5: Imagine you want every kid to give back the same fraction of their candy at the end of the day — a fair, flat tax. But you have a helper who, to be "fair," already gives kids who run around a lot (burning energy) smaller portions of everything. If you route the candy-tax through that helper, the energetic kids end up giving back way less candy than the calm kids, even though the tax was supposed to be equal for all. The fix is to collect the candy tax yourself, separately, after the helper is done — then everyone gives back the same fraction, no matter how much they ran around. In training, "weight decay" is that flat tax, and Adam is the helper; you have to apply the decay separately (that's AdamW) instead of feeding it through Adam.
---

## Why this module

Two mechanisms in modern training pull in opposite philosophies, and the bug is what happens when you route one through the other. Adam is adaptive on purpose: it gives each parameter its own effective learning rate, scaled down for parameters with big gradients so training stays stable across wildly different gradient magnitudes. Weight decay is deliberately non-adaptive: it is a regularizer that should shrink every weight by the same proportion, indifferent to gradients, to keep the model from over-relying on any parameter.

The collision happens because the mathematically-tidy way to add weight decay looks like it should be free. An L2 penalty (wd/2)·w² in the loss has gradient wd·w, so "adding weight decay" becomes "add wd·w to each gradient." That is correct for plain SGD, where the decay then just subtracts lr·wd·w from the weight. But under Adam the gradient — now carrying the decay term — is divided by sqrt(v) per parameter, so the decay inherits Adam's adaptivity it was never supposed to have. A parameter with large gradients, whose sqrt(v) is large, sees its decay divided down; a parameter with small gradients sees its decay amplified.

The result is a regularizer that does the opposite of uniform, and it matters most in exactly the large models where Adam is used. This module computes the decay each of two parameters actually receives under the coupled and decoupled formulations.

**Adding weight decay as an L2 loss term routes it through Adam's per-parameter 1/sqrt(v) scaling, so high-gradient weights get less decay and low-gradient weights get more — AdamW applies the decay directly to the weights, restoring the uniform regularization the coupling destroys.**

## Concepts

The fixture is a learning rate, a weight-decay coefficient, and two parameters at the same weight but with different Adam second moments — "steep" with large gradients, "flat" with small.

```json filename=modules/below-the-prompt/code/adamw-inter-01/adamw.json:3-8 COMPLETE
  "lr": 0.1,
  "wd": 0.1,
  "params": {
    "steep": {"w": 1.0, "v": 16.0},
    "flat": {"w": 1.0, "v": 1.0}
  }
```

The gradient RMS is sqrt(v). Coupled decay — L2 in the loss — is the decay term wd·w scaled by Adam's 1/sqrt(v), because it travels inside the gradient. Decoupled decay — AdamW — is lr·wd·w applied straight to the weight, untouched by the adaptive scaling.

```python filename=modules/below-the-prompt/code/adamw-inter-01/adamw.py:33-44 COMPLETE
def rms(param):
    return math.sqrt(param["v"])


def coupled_decay(param, lr, wd):
    """L2-in-loss: the decay term wd*w flows through Adam's 1/sqrt(v) scaling."""
    return lr * wd * param["w"] / rms(param)


def decoupled_decay(param, lr, wd):
    """AdamW: decay applied directly to the weight, outside the adaptive scaling."""
    return lr * wd * param["w"]
```

The only difference is the division by the gradient RMS. Decoupled decay does not divide, so it is the same for every weight of the same magnitude; coupled decay divides, so it shrinks for parameters with large gradients.

<svg role="img" aria-label="For the steep parameter the coupled decay is divided by its gradient RMS of 4, cutting it to a quarter, while the decoupled decay is unchanged; for the flat parameter both are equal" viewBox="0 0 320 130">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">decay received (same weight, wd, lr)</text>
  <text x="14" y="34" font-size="8" fill="var(--s1)">steep (RMS 4)</text>
  <rect x="110" y="26" width="18" height="12" fill="var(--s2)"/><text x="132" y="36" font-size="7.5" fill="var(--s2)">Adam+L2 0.0025 (÷4)</text>
  <rect x="110" y="42" width="72" height="12" fill="var(--s1)"/><text x="186" y="52" font-size="7.5" fill="var(--s1)">AdamW 0.01</text>
  <text x="14" y="80" font-size="8" fill="var(--s1)">flat (RMS 1)</text>
  <rect x="110" y="72" width="72" height="12" fill="var(--s2)"/><text x="186" y="82" font-size="7.5" fill="var(--s2)">Adam+L2 0.01</text>
  <rect x="110" y="88" width="72" height="12" fill="var(--s1)"/><text x="186" y="98" font-size="7.5" fill="var(--s1)">AdamW 0.01</text>
  <text x="14" y="120" font-size="7.5" fill="var(--muted)">coupled decay is divided by the gradient RMS; decoupled is not</text>
</svg>
^ For the flat parameter (RMS 1), the two formulations agree. For the steep parameter (RMS 4), coupled L2 divides the decay by 4 — down to 0.0025 — while AdamW leaves it at 0.01. The gap is exactly the gradient RMS the coupling injected.

**Decoupled decay omits the 1/sqrt(v) division, so it is uniform across weights of equal magnitude; coupled decay includes it, so it shrinks precisely for the high-gradient parameters.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the weight-decay step of an optimizer, reduced to two parameters so every decay is checkable by hand.

Run `--decay` to see the decay each parameter receives.

```text filename=adamw.py --decay
  param   weight   grad RMS   Adam+L2 decay   AdamW decay
  steep   1.00     4.00       0.0025          0.0100
  flat    1.00     1.00       0.0100          0.0100
```

Both parameters sit at weight 1.0 and share the same wd and lr, so a uniform regularizer should decay them identically. AdamW does: 0.0100 for each. Adam+L2 does not: the flat parameter gets 0.0100, but the steep parameter — with 4× the gradient RMS — gets 0.0025, a quarter as much, because its decay was divided by its RMS of 4. The high-gradient parameter is under-regularized, and by exactly the factor of its gradient magnitude relative to the others.

Now `--uniform` collects the decays each way and takes the ratio across parameters.

```python filename=modules/below-the-prompt/code/adamw-inter-01/adamw.py:64-65 COMPLETE
    c = [coupled_decay(p, lr, wd) for p in ps]
    d = [decoupled_decay(p, lr, wd) for p in ps]
```

The two ratios could not be more different.

```text filename=adamw.py --uniform
  Adam+L2 decays: [0.0025, 0.01]   ratio 4.0x
  AdamW decays:   [0.01, 0.01]     ratio 1.0x
```

AdamW's decay ratio across the two parameters is 1.0× — perfectly uniform. Adam+L2's is 4.0× — the flat parameter is decayed four times as hard as the steep one, purely because of their gradient histories. In a real model with thousands of parameters spanning a wide range of gradient scales, that ratio is not 4× between two weights but a whole spectrum of decay strengths that nobody chose, all an artifact of coupling the regularizer to the adaptive optimizer. The wd you set is not the decay any particular weight gets.

<svg role="img" aria-label="Decay uniformity: AdamW gives a flat 1x ratio across parameters, Adam+L2 gives a 4x ratio, decaying the flat parameter four times harder than the steep one" viewBox="0 0 320 110">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">decay ratio across parameters (1x = uniform)</text>
  <text x="10" y="42" font-size="8.5" fill="var(--s1)">AdamW</text>
  <rect x="80" y="32" width="45" height="16" fill="var(--s1)"/><text x="130" y="44" font-size="8" fill="var(--ink)">1.0x (uniform)</text>
  <text x="10" y="72" font-size="8.5" fill="var(--s2)">Adam+L2</text>
  <rect x="80" y="62" width="180" height="16" fill="var(--s2)"/><text x="264" y="74" font-size="8" fill="var(--ink)">4.0x</text>
  <text x="10" y="98" font-size="7.5" fill="var(--muted)">the wd you set is not the decay any given weight receives under coupled L2</text>
</svg>
^ AdamW decays every equal-weight parameter by the same fraction (1.0× ratio); Adam+L2 decays them across a 4.0× range set by their gradient magnitudes. The coupling turns a single wd knob into an unintended per-parameter regularization schedule.

**AdamW decays the two parameters identically (1.0× ratio) while Adam+L2 spans 4.0×, under-regularizing the steep parameter — the decay a weight receives under coupled L2 is not the wd you set but wd divided by its gradient RMS.**

## Build

The self-test establishes the setup and the failure: the steep parameter has a larger gradient RMS, Adam+L2 decays the two unequally, and it gives the high-gradient parameter less decay.

```python filename=modules/below-the-prompt/code/adamw-inter-01/adamw.py:80-88 COMPLETE
    steep_has_bigger_gradients = rms(steep) > rms(flat)
    print("  the steep parameter has a larger gradient RMS = %s (%.1f vs %.1f)" % (steep_has_bigger_gradients, rms(steep), rms(flat)))

    coupled_uneven = abs(coupled_decay(steep, lr, wd) - coupled_decay(flat, lr, wd)) > 1e-9
    print("  Adam+L2 decays the two parameters unequally = %s (%.4f vs %.4f)"
          % (coupled_uneven, coupled_decay(steep, lr, wd), coupled_decay(flat, lr, wd)))

    coupled_underdecays_steep = coupled_decay(steep, lr, wd) < coupled_decay(flat, lr, wd)
    print("  Adam+L2 gives the high-gradient parameter LESS decay = %s" % coupled_underdecays_steep)
```

Then the fix: AdamW decays both equally, and the steep parameter is under-regularized under Adam+L2 relative to AdamW.

```python filename=modules/below-the-prompt/code/adamw-inter-01/adamw.py:90-94 COMPLETE
    adamw_uniform = abs(decoupled_decay(steep, lr, wd) - decoupled_decay(flat, lr, wd)) < 1e-9
    print("  AdamW decays both equally (same weight) = %s (%.4f == %.4f)"
          % (adamw_uniform, decoupled_decay(steep, lr, wd), decoupled_decay(flat, lr, wd)))

    steep_underregularized = coupled_decay(steep, lr, wd) < decoupled_decay(steep, lr, wd)
    print("  under Adam+L2 the steep parameter is under-regularized vs AdamW = %s (%.4f < %.4f)"
          % (steep_underregularized, coupled_decay(steep, lr, wd), decoupled_decay(steep, lr, wd)))
```

Running the check confirms every clause.

```text filename=adamw.py --check
  the steep parameter has a larger gradient RMS = True (4.0 vs 1.0)
  Adam+L2 decays the two parameters unequally = True (0.0025 vs 0.0100)
  Adam+L2 gives the high-gradient parameter LESS decay = True
  AdamW decays both equally (same weight) = True (0.0100 == 0.0100)
  under Adam+L2 the steep parameter is under-regularized vs AdamW = True (0.0025 < 0.0100)
```

**The check ties the uneven decay to the gradient RMS division — the steep parameter under-regularized fourfold — and shows AdamW's decay identical across the two, the uniformity the decoupling restores.**

## Definition of done

Done means Adam+L2 is shown to decay parameters unequally by their gradient RMS (under-regularizing the high-gradient one) and AdamW to decay equal weights equally. The clause pinning the coupled steep decay below the AdamW steep decay is the concrete harm: the parameters that most need regularization — the ones being pushed hard by large gradients — are exactly the ones coupled L2 protects least.

Two clarifications keep this precise. First, the second moment v used here is a stand-in for the parameter's running gradient RMS, which is what Adam divides by; the demonstration uses a fixed v per parameter to make the decay exactly computable, whereas in a live run v evolves, but the structural point holds every step — the decay term rides through the same 1/sqrt(v) scaling as the gradient. AdamW's decoupling means the decay never touches v at all. Second, this is not a niche correctness nit; it changed practice. The AdamW paper showed that decoupling weight decay materially improves generalization and makes the decay coefficient independent of the learning rate schedule (with coupled L2, changing lr silently rescales the effective decay), which is why AdamW is the default optimizer for training transformers and why frameworks expose a distinct weight_decay argument that is applied decoupled rather than folded into the loss. The practical rule: use AdamW (or your framework's decoupled weight-decay path) and never hand-roll weight decay as an L2 term added to the loss when the optimizer is adaptive.

<svg role="img" aria-label="Two update paths: Adam+L2 adds wd*w to the gradient then divides everything by sqrt(v), coupling decay to the adaptive scaling; AdamW updates from the raw gradient then subtracts lr*wd*w separately" viewBox="0 0 320 120">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">where the decay is applied</text>
  <text x="14" y="36" font-size="7.5" fill="var(--s2)">Adam+L2:</text>
  <text x="70" y="36" font-size="7" fill="var(--ink)">(grad + wd·w) ÷ sqrt(v)  → decay scaled by 1/sqrt(v)</text>
  <text x="14" y="64" font-size="7.5" fill="var(--s1)">AdamW:</text>
  <text x="70" y="64" font-size="7" fill="var(--ink)">grad ÷ sqrt(v), then  w −= lr·wd·w  → decay uniform</text>
  <text x="14" y="92" font-size="7.5" fill="var(--muted)">decoupling makes the decay independent of the gradient RMS and the lr scaling</text>
  <text x="14" y="108" font-size="7.5" fill="var(--ink)">use AdamW / the framework's decoupled path; never add L2 to the loss under Adam</text>
</svg>
^ Adam+L2 folds wd·w into the gradient, so it is divided by sqrt(v) and the decay becomes gradient-dependent. AdamW updates from the raw gradient and subtracts the decay separately, keeping it uniform and independent of the adaptive scaling. Decoupling is a change in where, not how much.

**Done means Adam+L2 under-regularizes high-gradient parameters via the 1/sqrt(v) division while AdamW decays equal weights uniformly — so the rule is to use AdamW's decoupled decay, never an L2 loss term, whenever the optimizer is adaptive.**

## Boss fight

A team ports a training script from SGD to Adam to speed up convergence, keeping their existing weight decay implemented as an L2 term added to the loss. Convergence improves, but the model generalizes worse than the SGD version, and they find that increasing the learning rate schedule seems to also weaken regularization for no reason they can see. What is going on, and what is the fix?

Two symptoms, one cause: weight decay implemented as an L2 loss term behaves incorrectly under Adam. Because the L2 penalty adds wd·w to the gradient, and Adam divides the gradient by each parameter's sqrt(v), the decay each weight receives is (lr·wd·w)/sqrt(v) — scaled down for high-gradient parameters and up for low-gradient ones, rather than uniform. Under SGD there is no 1/sqrt(v) term, so the same L2 code gave the intended uniform decay; moving to Adam silently turned it into a non-uniform, gradient-dependent regularization that under-regularizes exactly the parameters being pushed hardest, hurting generalization. The second symptom follows from the same coupling: because the decay travels inside the update that is multiplied by lr, changing the learning rate rescales the effective decay, so raising lr weakens regularization — the decay coefficient is not independent of the lr schedule when coupled. The fix is to decouple the weight decay: switch to AdamW (or set weight_decay on the optimizer, which frameworks apply decoupled) and remove the L2 term from the loss. AdamW runs Adam on the raw loss gradient and subtracts lr·wd·w from each weight separately, so every weight decays by the same fraction regardless of its gradient history, and the decay coefficient becomes independent of the adaptive scaling. Expect generalization to recover toward or past the SGD baseline, and the strange lr-weakens-regularization coupling to disappear. The general lesson: weight decay and L2 regularization are equivalent only for plain SGD; under an adaptive optimizer they are different operations, and the decoupled form (AdamW) is the correct one.

## External resources

The AdamW paper, "Decoupled Weight Decay Regularization" (Loshchilov and Hutter) — the derivation of why L2 and weight decay diverge under adaptive optimizers, the generalization improvement from decoupling, and the independence of the decay coefficient from the learning rate.

Optimizer documentation for AdamW in deep-learning frameworks (PyTorch `torch.optim.AdamW` and the weight-decay handling in Adam vs AdamW) — the exact update equations showing where the decay is applied, and the guidance to use the decoupled path rather than an L2 loss term.
