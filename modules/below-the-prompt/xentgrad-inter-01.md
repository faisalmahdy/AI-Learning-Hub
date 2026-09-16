---
id: xentgrad-inter-01
title: The softmax cross-entropy gradient is just (softmax − one-hot) — not −1/p, and that clean form is why backprop is cheap and stable
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: Softmax cross-entropy is the standard classification loss — softmax turns the logits into a probability distribution, and the loss is the negative log of the probability on the true class. To train, backprop needs the gradient of this loss with respect to the logits, and although the loss composes a log with a softmax (whose derivative is a full Jacobian coupling every output to every input), the gradient collapses to one of the cleanest results in deep learning: the gradient with respect to logit i is p_i − y_i, the predicted probability minus the target (1 for the true class, 0 otherwise) — softmax minus the one-hot label. That clean form is why training is fast and stable: each component is a probability minus a 0/1 target, bounded in [−1, 1], negative for the true class (raise its logit) and positive for the others (lower theirs), and the components sum to zero because softmax and the one-hot label each sum to 1. The common mistake is to differentiate only the visible −log(p_true) term, get −1/p_true for the true class and 0 for the rest, which treats the logit as the probability and forgets that softmax couples the logits — a gradient that is wrong, unbounded as p_true → 0, and zeroes classes that should be pushed down. On a fixture with logits [2.0, 1.0, 0.1] and class 0 correct, softmax is [0.659, 0.242, 0.099], the correct p − y gradient [−0.341, 0.242, 0.099] matches a numerical gradient and sums to 0, while the naive −1/p gradient [−1.517, 0, 0] does not match.
eli5: When a model guesses among options, it gives each a probability, and we grade it by how much probability it put on the right answer. To improve, the model needs to know which way to nudge each score. The beautiful shortcut is: for every option, nudge it by "how much probability I gave it minus how much I should have" — so the right answer (should be 1) gets pushed up, and every wrong answer (should be 0) gets pushed down, each by a gentle, bounded amount. A tempting wrong shortcut only pushes the right answer and ignores the wrong ones, and it can shove infinitely hard — which would make training explode. The gentle balanced nudge is what keeps learning smooth.
---

## Why this module

The loss that trains almost every classifier and language model looks like it should have an ugly derivative — a log wrapped around a softmax that tangles every output together. It does not, and the reason it does not is the small miracle that makes the whole training loop practical. Miss it, and you either reimplement the gradient wrong or never understand why frameworks fuse two operations into one.

Softmax cross-entropy is the standard classification loss: the model emits raw scores (logits), softmax turns them into a probability distribution, and the loss is the negative log of the probability placed on the true class. Minimizing it pushes probability toward the correct class. To train, backprop needs the gradient of this loss with respect to the logits — and here something remarkable happens. The loss is a composition of a log and a softmax, whose derivative is a full Jacobian coupling every output to every input, so you would expect a messy gradient. Instead it collapses to one of the cleanest results in deep learning: the gradient with respect to logit i is simply p_i − y_i, the predicted probability minus the target (1 for the true class, 0 otherwise). Softmax minus the one-hot label, nothing more.

That clean form is not a convenience, it is why the training loop is fast and numerically stable. Each gradient component is a probability minus a 0-or-1 target, so it is bounded in [−1, 1]: never explosive, always pointing the right way — negative for the true class (raise its logit) and positive for the others (lower theirs) — and the components sum to zero, because softmax outputs and the one-hot label each sum to 1. Frameworks fuse softmax and cross-entropy into one op precisely so they can emit p − y directly, skipping the ill-conditioned intermediate of computing softmax, then log, then dividing by a possibly-tiny probability. This module computes the gradient three ways — the clean form, a naive wrong form, and a numerical check — and shows which one is right.

**Despite composing a softmax and a log, the softmax cross-entropy gradient with respect to the logits is exactly p − y (softmax minus the one-hot label), which is bounded in [−1, 1] and sums to zero — and the naive −1/p_true gradient, which forgets that softmax couples the logits, is wrong and unbounded.**

## Concepts

**The analytic gradient** is the whole result: predicted probability minus target, per class. The one-hot label subtracts 1 from the true class only, so that component goes negative and the rest stay positive.

```python filename=modules/below-the-prompt/code/xentgrad-inter-01/xentgrad.py:61-64 COMPLETE
def analytic_grad(logits, true_class):
    """The clean gradient of softmax cross-entropy wrt the logits: p_i - y_i (softmax minus one-hot)."""
    p = softmax(logits)
    return [p[i] - (1.0 if i == true_class else 0.0) for i in range(len(logits))]
```

**The naive gradient** is the tempting mistake: differentiate only the `−log(p_true)` you can see, get `−1/p_true`, and leave the other classes at 0. It treats the logit as if it were the probability and ignores softmax's coupling.

```python filename=modules/below-the-prompt/code/xentgrad-inter-01/xentgrad.py:67-70 COMPLETE
def naive_grad(logits, true_class):
    """The WRONG gradient: differentiate only -log(p_true), get -1/p_true, and leave the other classes at 0."""
    p = softmax(logits)
    return [-1.0 / p[i] if i == true_class else 0.0 for i in range(len(logits))]
```

<svg role="img" aria-label="Logits flow through softmax to probabilities; subtracting the one-hot target gives the gradient, negative on the true class and positive on the others" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">gradient = softmax probability − one-hot target, per class</text>
  <g font-size="7">
  <text x="10" y="34" fill="var(--muted)">class</text><text x="70" y="34" fill="var(--muted)">p</text><text x="120" y="34" fill="var(--muted)">− y</text><text x="180" y="34" fill="var(--muted)">= grad</text>
  <text x="10" y="52" fill="var(--muted)">0 (true)</text><text x="66" y="52" fill="var(--muted)">0.659</text><text x="118" y="52" fill="var(--muted)">−1</text>
  <rect x="180" y="43" width="60" height="10" fill="var(--s2)"/><text x="244" y="52" fill="var(--muted)">−0.341 ↓push up</text>
  <text x="10" y="70" fill="var(--muted)">1</text><text x="66" y="70" fill="var(--muted)">0.242</text><text x="118" y="70" fill="var(--muted)">−0</text>
  <rect x="180" y="61" width="40" height="10" fill="var(--s1)"/><text x="224" y="70" fill="var(--muted)">+0.242 ↑push down</text>
  <text x="10" y="88" fill="var(--muted)">2</text><text x="66" y="88" fill="var(--muted)">0.099</text><text x="118" y="88" fill="var(--muted)">−0</text>
  <rect x="180" y="79" width="18" height="10" fill="var(--s1)"/><text x="202" y="88" fill="var(--muted)">+0.099</text>
  </g>
  <text x="10" y="108" fill="var(--muted)" font-size="7">the three components sum to zero: (0.659+0.242+0.099) − 1 = 0</text>
</svg>
^ Softmax gives each class a probability, and subtracting the one-hot target (1 on the true class, 0 elsewhere) yields the gradient — negative on the true class to raise its logit, positive on the rest to lower theirs, summing to zero.

**The gradient is predicted-minus-target per class, so it is bounded, points the true class up and the others down, and sums to zero — none of which the naive −1/p form, which touches only the true class, can give.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/xentgrad-inter-01/xentgrad.py

The fixture is three logits with class 0 correct.

```json filename=modules/below-the-prompt/code/xentgrad-inter-01/xentgrad.json:3-4 COMPLETE
  "logits": [2.0, 1.0, 0.1],
  "true_class": 0
```

Run `--gradient` for the softmax and both gradient formulas.

```text filename=--gradient
GRADIENT — softmax and the analytic vs naive gradient (true class = 0)
--------------------------------------------------------------
  logits           = [+2.000, +1.000, +0.100]
  softmax p        = [+0.659, +0.242, +0.099]  (sums to 1.000)
--------------------------------------------------------------
  analytic  p - y  = [-0.341, +0.242, +0.099]   <- correct, bounded in [-1,1]
  naive   -1/p_true= [-1.517, +0.000, +0.000]   <- wrong: ignores softmax coupling, unbounded
```

The softmax puts 0.659 on the true class, 0.242 and 0.099 on the others. The analytic gradient subtracts the one-hot label: the true class becomes 0.659 − 1 = −0.341, the others stay at their probabilities 0.242 and 0.099. Read what those numbers *do*: gradient descent steps against the gradient, so the negative −0.341 raises the true class's logit and the positive 0.242 and 0.099 lower the other two — exactly the update you want, and each move is small and bounded. The naive gradient, meanwhile, reports −1.517 for the true class and 0 for the others. It is more than four times larger on the true class (and grows without limit as the true probability shrinks), and it says to do *nothing* to the wrong classes — but softmax is a competition, so the only way to raise one class's probability is to lower the others', and a gradient that leaves the others untouched has fundamentally misunderstood the loss. The two forms are not close.

## Build

To settle which is right, compute the gradient the dumb, assumption-free way — nudge each logit and measure the loss change. Run `--numeric`.

```text filename=--numeric
NUMERIC — finite-difference gradient vs the two formulas
------------------------------------------------------------
  numerical (truth)  = [-0.341, +0.242, +0.099]
  analytic  p - y    = [-0.341, +0.242, +0.099]   diff 1.37e-12
  naive   -1/p_true  = [-1.517, +0.000, +0.000]   diff 1.18e+00
```

The numerical gradient — the loss's actual slope in each logit direction, found by finite differences and assuming no formula at all — is [−0.341, 0.242, 0.099], identical to the analytic p − y to twelve decimal places. The naive form is off by 1.18, more than a whole unit of gradient on the true class, and completely wrong on the other two. This is the proof: p − y is not a convenient approximation, it is *the* gradient, exactly, and the naive −1/p is simply a different (wrong) function. The finite-difference check is the tool that catches a hand-derived gradient that is subtly wrong — it needs no calculus, only the loss itself, which is why it is the standard way to verify a backward pass.

```python filename=modules/below-the-prompt/code/xentgrad-inter-01/xentgrad.py:73-80 COMPLETE
def numerical_grad(logits, true_class, h=1e-5):
    """Finite-difference gradient of the loss wrt each logit -- the ground truth to check against."""
    g = []
    for i in range(len(logits)):
        up = list(logits); up[i] += h
        dn = list(logits); dn[i] -= h
        g.append((cross_entropy(up, true_class) - cross_entropy(dn, true_class)) / (2 * h))
    return g
```

<svg role="img" aria-label="Three gradients compared: the numerical truth and the analytic p-minus-y are identical, while the naive minus-one-over-p is far off on the true class and zero on the others" viewBox="0 0 300 120" width="300" height="120">
  <text x="6" y="12" fill="var(--muted)" font-size="8">p − y matches the numerical truth; naive −1/p does not</text>
  <line x1="30" y1="40" x2="290" y2="40" stroke="var(--line)"/><text x="24" y="43" fill="var(--muted)" font-size="7" text-anchor="end">0</text>
  <g font-size="6">
  <text x="6" y="58" fill="var(--muted)">class 0</text>
  <rect x="150" y="40" width="34" height="7" fill="var(--s2)"/><text x="186" y="46" fill="var(--muted)">numeric/analytic −0.341</text>
  <rect x="40" y="49" width="110" height="7" fill="var(--muted)"/><text x="40" y="64" fill="var(--muted)">naive −1.517</text>
  <text x="6" y="82" fill="var(--muted)">class 1</text>
  <rect x="150" y="72" width="24" height="7" fill="var(--s1)"/><text x="176" y="78" fill="var(--muted)">+0.242 (naive: 0)</text>
  <text x="6" y="102" fill="var(--muted)">class 2</text>
  <rect x="150" y="92" width="10" height="7" fill="var(--s1)"/><text x="162" y="98" fill="var(--muted)">+0.099 (naive: 0)</text>
  </g>
  <line x1="150" y1="34" x2="150" y2="108" stroke="var(--line)" stroke-dasharray="2 2"/>
</svg>
^ For each class the analytic p − y lands exactly on the numerical gradient, while the naive −1/p is far too large on the true class and wrongly zero on the other two — the finite-difference check exposes the wrong formula instantly.

## Definition of done

The self-test pins the p − y identity, the numerical match, the zero sum, the sign pattern, and the naive form's failure.

```python filename=modules/below-the-prompt/code/xentgrad-inter-01/xentgrad.py:123-133 COMPLETE
    is_p_minus_y = ana == [p[i] - (1.0 if i == tc else 0.0) for i in range(len(logits))]
    print("  the analytic gradient is exactly softmax minus one-hot = %s (%s)" % (is_p_minus_y, _fmt(ana)))

    matches_numeric = max(abs(a - n) for a, n in zip(ana, num)) < 1e-4
    print("  it matches the numerical gradient = %s (max diff %.2e)" % (matches_numeric, max(abs(a - n) for a, n in zip(ana, num))))

    sums_to_zero = abs(sum(ana)) < 1e-9
    print("  the gradient components sum to zero = %s (%.2e)" % (sums_to_zero, sum(ana)))

    true_class_negative = ana[tc] < 0 and all(ana[i] > 0 for i in range(len(logits)) if i != tc)
    print("  true-class gradient is negative, others positive = %s" % true_class_negative)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the analytic gradient equals p - y, matches the numerical gradient, sums to zero, and the naive form is wrong
----------------------------------------------------------------------------------------------------------------------------
  the analytic gradient is exactly softmax minus one-hot = True ([-0.341, +0.242, +0.099])
  it matches the numerical gradient = True (max diff 1.37e-12)
  the gradient components sum to zero = True (0.00e+00)
  true-class gradient is negative, others positive = True
  the naive -1/p gradient does NOT match the truth = True (max diff 1.18e+00)
```

**Done means the clean gradient and the naive error are both proven on real numbers: the analytic gradient is exactly softmax minus the one-hot label ([−0.341, +0.242, +0.099]), it matches the numerical gradient to 1e-12 and sums to zero with the true class negative and the others positive, while the naive −1/p gradient is off by 1.18 — so the softmax cross-entropy gradient is p − y, and the −1/p shortcut is simply wrong.**

## Boss fight

Predict two ways the clean p − y form matters beyond deriving it once, because it explains both a stability practice and a training pathology.

The first trap is *why* frameworks fuse softmax and cross-entropy into a single op instead of composing the two library functions, and it is the same numerical-stability story as the log-sum-exp trick. If you compute softmax explicitly, then take its log for the loss, you pass through `log(exp(logit)/sum)` — and for a confident wrong prediction the true class's probability can underflow to 0, making the log `−inf` and the naive `−1/p` gradient blow up. A fused softmax-cross-entropy computes the loss as `logsumexp(logits) − logit_true` (never forming the tiny probability) and emits the gradient directly as p − y (always bounded), so both the forward and backward passes stay finite even when a probability is astronomically small. This is why every framework has a combined `cross_entropy(logits, target)` that takes *logits*, not probabilities, and warns you not to apply softmax first: doing your own softmax then a separate log/NLL reintroduces exactly the underflow the fused op exists to avoid, and can even double-apply softmax. The clean gradient is inseparable from the stable implementation — they are the same result read forward and backward.

The second trap is that p − y being bounded is a feature with a shadow: the gradient *vanishes* as the model gets confident, which is usually good but is the mechanism behind a real failure mode. When the model already puts p ≈ 1 on the true class, p − y ≈ 0 and there is almost no gradient — correct examples stop contributing, so training naturally focuses on the still-wrong ones. But that same saturation means a *confidently wrong* prediction (high probability on the wrong class) also produces a bounded gradient — at most magnitude 1 per logit — so a single mislabeled example or a hard case cannot generate a corrective signal larger than any other, and under heavy class imbalance the many easy negatives, each contributing a small p − y, can collectively swamp the few hard positives. <svg role="img" aria-label="The true-class gradient magnitude, one minus p, plotted against the model's probability on the true class: it is 1 when p is 0 and falls to 0 as p approaches 1, so confident examples contribute almost no gradient" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">true-class gradient |p−1| shrinks to 0 as confidence rises</text>
  <line x1="34" y1="96" x2="285" y2="96" stroke="var(--line)"/>
  <line x1="34" y1="24" x2="34" y2="96" stroke="var(--line)"/>
  <text x="28" y="28" fill="var(--muted)" font-size="7" text-anchor="end">1</text>
  <text x="28" y="96" fill="var(--muted)" font-size="7" text-anchor="end">0</text>
  <text x="34" y="110" fill="var(--muted)" font-size="7">p_true = 0</text>
  <text x="250" y="110" fill="var(--muted)" font-size="7">1</text>
  <line x1="34" y1="24" x2="285" y2="96" stroke="var(--s1)"/>
  <circle cx="120" cy="72" r="3" fill="var(--s2)"/><text x="126" y="70" fill="var(--muted)" font-size="6">p=0.66 → |grad| 0.34</text>
  <text x="150" y="44" fill="var(--muted)" font-size="7">confident → tiny gradient</text>
</svg>
^ The true-class gradient magnitude is 1 − p_true, so a barely-right prediction (p small) gets a large corrective push while a confident one (p near 1) gets almost none — the boundedness that keeps training stable is also why easy, already-correct examples stop contributing.

This is precisely the problem focal loss was designed to fix: it down-weights easy, already-correct examples so the bounded gradient is spent on the hard ones. So the boundedness that makes softmax cross-entropy stable is also why, on imbalanced or hard-example-dominated problems, the raw loss can under-train the cases you care about — and why the fix is to reshape the loss, not to hunt for a bigger gradient. The p − y form tells you both that training is stable and exactly where it will quietly stall.

**The clean p − y gradient is one half of a single fact: frameworks fuse softmax and cross-entropy so the forward pass uses logsumexp (no underflow) and the backward pass emits p − y directly (bounded), which is why the combined op takes logits and you must not softmax first — and that same boundedness means the gradient vanishes on confident predictions, so easy or majority examples stop contributing and hard/minority ones can be swamped, the pathology focal loss and class weighting exist to correct.**

## External resources

Any deep-learning course's derivation of the softmax cross-entropy gradient (e.g. CS231n) — the cancellation that yields p − y, why the combined loss takes logits, and the log-sum-exp trick for numerical stability.

Framework documentation for the fused softmax-cross-entropy op (PyTorch's CrossEntropyLoss, which takes logits) — the explicit warning not to apply softmax beforehand, and why the fused forward and backward pass avoid underflow.

The companion softmax and residual-stream modules in this topic, and the focal-loss / class-imbalance literature — the gradient's boundedness is why softmax cross-entropy is stable and also why confident or majority examples stop contributing, which reshaped losses address.
