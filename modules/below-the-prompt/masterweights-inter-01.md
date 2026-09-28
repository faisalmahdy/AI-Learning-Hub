---
id: masterweights-inter-01
title: Keep fp32 master weights in mixed precision — a small update added to an fp16 weight rounds away every step and the parameter never moves
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: Mixed-precision training runs the forward and backward passes in fp16 for speed and memory, and this module is about a trap on the update, separate from the gradient-underflow trap that loss scaling fixes. Even when the gradient is perfectly good, the optimizer's step — learning rate times gradient — is usually tiny compared to the weight it is applied to, so a weight near 1.0 with an update of a few ten-thousandths asks fp16 to represent a change far smaller than its resolution at that magnitude. fp16 has about ten mantissa bits, so near 1.0 the gap between representable values (the ulp) is about 2^-10, roughly a thousandth; an update of 0.0004 is less than half that, so w + update rounds to the nearest fp16 value, which is w itself — the addition happens, the result rounds away, and the weight is unchanged, not this step and not any step. The parameter silently stops learning. The fix is to keep the master copy of each weight in fp32: the optimizer applies its update there, where 0.0004 is represented exactly and accumulates step after step, while the fp16 weight used in the fast passes is just a rounded snapshot; after enough steps the accumulated change grows past the fp16 ulp and the snapshot finally moves. This is the second pillar of mixed precision alongside loss scaling. On a fixture applying 0.0004 for 100 steps to a weight of 1.0, the direct-fp16 weight stays 1.0 while the fp32 master reaches 1.04 and its fp16 snapshot then reads 1.04 too.
eli5: Imagine a bank account that can only show whole dollars — no cents. Every day you try to deposit 40 cents. The teller adds it, sees the balance is now $1.40, rounds to the nearest dollar, and writes $1 — so your balance never changes, day after day, even though you keep depositing. Your money is vanishing into the rounding. The fix is to keep a second, precise ledger that tracks cents: there your 40 cents add up honestly — 40, 80, a dollar twenty — and only when you glance at the rounded display does it finally tick up to $1, then $2. The precise ledger banks the small amounts until they're big enough to show. Training a neural network in low precision has the same problem: each tiny weight update is like 40 cents against a dollar it can't display, so it rounds away — unless you keep a precise master copy that adds the small updates up until they're big enough to appear.
---

## Why this module

Mixed-precision training exists because fp16 is half the size and much faster than fp32, and most of the heavy compute — the matrix multiplies in the forward and backward passes — tolerates the lower precision fine. The catch is that a few operations do not tolerate it, and the optimizer's weight update is the one this module is about. It is easy to assume that if the gradient is good, the update is fine, but that skips a second, independent place where fp16 loses information.

The issue is a mismatch of scales. A weight is an ordinary-sized number, often near 1. Its update is learning-rate-times-gradient, which is deliberately small — that is what makes training stable. So you are repeatedly adding a very small number to a much larger one, and fp16's resolution is relative: near a value of 1, it can only represent changes down to about a thousandth. An update smaller than that has nowhere to land; it rounds off.

And it rounds off every step, not occasionally, because the weight and the update keep the same scales throughout. So the parameter does not learn slowly — it does not learn at all, sitting exactly where it started while the logs show a running loss that never quite improves for that weight. This module applies a realistic small update to an fp16 weight step after step, and separately to an fp32 master, and shows one frozen and the other moving.

**Mixed precision loses the update as well as the gradient: a small optimizer step added to a much larger fp16 weight is below fp16's resolution there, so it rounds away every step and the weight never moves.**

## Concepts

The governing fact is that floating-point resolution is relative, measured by the ulp — the gap between one representable number and the next. The ulp grows with magnitude: near 1.0, fp16's ulp is about 2^-10; near 1000 it is a thousand times larger. So whether an update "fits" is not about the update's absolute size but about its size relative to the weight it is added to. A small update can be perfectly representable on its own and still vanish when added to a large weight, because the sum has to snap to the coarse grid around that weight.

This is why the problem is specifically an addition problem, and why it is distinct from gradient underflow. Gradient underflow is a value getting too small to represent at all, near fp16's floor of about 6e-5; loss scaling fixes it by multiplying gradients up before they are stored. Master weights fix a different thing: an update that is representable in isolation but too small relative to the weight to change it. Loss scaling does not help here, because the update is not underflowing to zero — it is being rounded off in the sum. The two failures need two different fixes, and mixed-precision training uses both.

The master-weights fix works by moving the accumulation to where the grid is fine enough. The fp32 master has a ulp near 1.0 of about 2^-23, millions of times finer, so 0.0004 lands exactly and each step's update adds to the running total faithfully. The fp16 weight used in the fast passes is regenerated from the master each step, so a single step still looks like no change in fp16 — but the master keeps the true total, and once that total crosses the fp16 ulp, the regenerated snapshot jumps to the next representable value. The small updates were never lost; they were banked in fp32 until they were big enough to show.

<svg role="img" aria-label="Two mixed-precision failures side by side: gradient underflow, a value below the fp16 floor fixed by loss scaling; and update rounding, a small update lost against a large weight fixed by fp32 master weights" viewBox="0 0 440 130">
<rect x="20" y="25" width="185" height="80" fill="var(--panel)" stroke="var(--line)"/>
<text x="112" y="45" fill="var(--ink)" font-size="10" text-anchor="middle">gradient underflow</text>
<text x="112" y="64" fill="var(--muted)" font-size="9" text-anchor="middle">value below fp16 floor</text>
<text x="112" y="82" fill="var(--muted)" font-size="9" text-anchor="middle">-&gt; flushes to zero</text>
<text x="112" y="99" fill="var(--s1)" font-size="9" text-anchor="middle">fix: loss scaling</text>
<rect x="235" y="25" width="185" height="80" fill="var(--panel)" stroke="var(--line)"/>
<text x="327" y="45" fill="var(--ink)" font-size="10" text-anchor="middle">update rounding</text>
<text x="327" y="64" fill="var(--muted)" font-size="9" text-anchor="middle">update small vs weight</text>
<text x="327" y="82" fill="var(--muted)" font-size="9" text-anchor="middle">-&gt; rounds off in the sum</text>
<text x="327" y="99" fill="var(--s1)" font-size="9" text-anchor="middle">fix: fp32 master weights</text>
</svg>
^ Mixed precision has two underflows: a gradient too small to store (loss scaling) and an update too small to add to its weight (master weights) — different failures, different fixes.

**Resolution is relative, so an update vanishes when it is small relative to the weight, not when it is small absolutely; loss scaling cannot fix that — an fp32 master, whose grid is far finer, banks the update until it exceeds the fp16 ulp.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/masterweights-inter-01. The fixture is a weight, a small per-step update, a step count, and fp16's mantissa width.

```json filename=modules/below-the-prompt/code/masterweights-inter-01/masterweights.json:3-6 COMPLETE
  "weight": 1.0,
  "update": 0.0004,
  "steps": 100,
  "mantissa_bits": 10
```

fp16 rounding snaps a value to the nearest point on the grid for its magnitude — the ulp is 2 to the (exponent minus mantissa bits).

```python filename=modules/below-the-prompt/code/masterweights-inter-01/masterweights.py:35-41 COMPLETE
def round_fp16(x, mantissa_bits):
    """Round x to the nearest value on the fp16 grid for its magnitude (ulp = 2^(exponent - mantissa_bits))."""
    if x == 0:
        return 0.0
    exponent = math.floor(math.log2(abs(x)))
    ulp = 2.0 ** (exponent - mantissa_bits)
    return round(x / ulp) * ulp
```

The direct path applies the update straight to the fp16 weight each step; the master path accumulates in fp32 and rounds only for the snapshot.

```python filename=modules/below-the-prompt/code/masterweights-inter-01/masterweights.py:44-49 COMPLETE
def train_direct(weight, update, steps, mantissa_bits):
    """Apply the update straight to the fp16 weight each step -- the update rounds away."""
    w = round_fp16(weight, mantissa_bits)
    for _ in range(steps):
        w = round_fp16(w + update, mantissa_bits)
    return w
```

```python filename=modules/below-the-prompt/code/masterweights-inter-01/masterweights.py:52-57 COMPLETE
def train_master(weight, update, steps, mantissa_bits):
    """Accumulate the update in an fp32 master; the fp16 weight is a rounded snapshot of it."""
    master = weight  # fp32, full precision
    for _ in range(steps):
        master = master + update
    return master, round_fp16(master, mantissa_bits)
```

Before running it, predict: a single update should round back to 1.0 in fp16, because 0.0004 is below the ulp near 1.0. Run `--step`:

```text filename=masterweights.py --step
STEP — one update of 0.0004 applied to a weight of 1.0
--------------------------------------------------------
  fp16 ulp near 1.0 = 0.000977  (smallest change fp16 can show here)
  direct fp16:  round16(1.0 + 0.0004) = 1.000000
  fp32 master:  1.0 + 0.0004 = 1.0004
```

The prediction holds. The ulp near 1.0 is 0.000977, and the update 0.0004 is less than half of it, so `round16(1.0004)` snaps back to 1.0 — the fp16 weight is unchanged. The fp32 master, with its far finer grid, records 1.0004 exactly.

<svg role="img" aria-label="A number line near 1.0 marked with fp16 grid points spaced about one thousandth apart; the target 1.0004 sits just right of 1.0 and rounds back to the 1.0 grid point, while an fp32 grid is dense enough to hold it" viewBox="0 0 440 140">
<text x="220" y="18" fill="var(--muted)" font-size="9" text-anchor="middle">fp16 grid near 1.0 (ulp ~0.001)</text>
<line x1="40" y1="45" x2="400" y2="45" stroke="var(--line)"/>
<line x1="80" y1="38" x2="80" y2="52" stroke="var(--ink)"/>
<text x="80" y="66" fill="var(--ink)" font-size="9" text-anchor="middle">1.000</text>
<line x1="260" y1="38" x2="260" y2="52" stroke="var(--ink)"/>
<text x="260" y="66" fill="var(--ink)" font-size="9" text-anchor="middle">1.001</text>
<circle cx="152" cy="45" r="4" fill="var(--s2)"/>
<text x="152" y="34" fill="var(--s2)" font-size="8" text-anchor="middle">1.0004</text>
<path d="M148 40 Q 110 20, 84 40" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"/>
<text x="150" y="82" fill="var(--s2)" font-size="8" text-anchor="middle">rounds back to 1.000</text>
<text x="220" y="108" fill="var(--muted)" font-size="9" text-anchor="middle">fp32 grid (ulp ~0.0000001)</text>
<line x1="40" y1="120" x2="400" y2="120" stroke="var(--grid)"/>
<circle cx="152" cy="120" r="4" fill="var(--s1)"/>
<text x="152" y="134" fill="var(--s1)" font-size="8" text-anchor="middle">1.0004 held exactly</text>
</svg>
^ The update lands between two fp16 grid points and rounds back to 1.0; the fp32 grid is fine enough to hold it.

Now run it for all 100 steps both ways. Run `--train`:

```text filename=masterweights.py --train
TRAIN — the weight after 100 updates of 0.0004
--------------------------------------------------------
  direct fp16 weight       = 1.0000  (moved 0.0000)
  fp32 master weight       = 1.0400  (moved 0.0400)
  fp16 snapshot of master  = 1.0400
--------------------------------------------------------
  direct never moved; the master banked every update and the snapshot now shows it
```

After 100 steps the direct-fp16 weight is still exactly 1.0 — it moved zero, because every single step rounded away. The fp32 master reached 1.04, the full 100 × 0.0004, and its fp16 snapshot now reads 1.04 too, because the accumulated 0.04 is many ulps and lands cleanly on the grid. Same updates, same steps; one path learned nothing and the other learned everything.

<svg role="img" aria-label="Two lines over 100 steps: the direct fp16 weight stays flat at 1.0, the fp32 master rises steadily to 1.04" viewBox="0 0 440 150">
<line x1="45" y1="120" x2="410" y2="120" stroke="var(--line)"/>
<line x1="45" y1="20" x2="45" y2="120" stroke="var(--line)"/>
<text x="30" y="30" fill="var(--muted)" font-size="9" text-anchor="middle">1.04</text>
<text x="30" y="118" fill="var(--muted)" font-size="9" text-anchor="middle">1.00</text>
<text x="225" y="140" fill="var(--muted)" font-size="9" text-anchor="middle">step</text>
<line x1="45" y1="118" x2="405" y2="118" stroke="var(--s2)"/>
<text x="350" y="112" fill="var(--s2)" font-size="9">direct fp16 (flat)</text>
<line x1="45" y1="118" x2="405" y2="35" stroke="var(--s1)"/>
<text x="330" y="40" fill="var(--s1)" font-size="9">fp32 master</text>
</svg>
^ The direct-fp16 weight never leaves 1.0; the fp32 master climbs steadily to 1.04 as the small updates accumulate.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that one update rounds back to the same fp16 weight, that the direct weight never moves over all steps, that the fp32 master accumulates faithfully, that the master's fp16 snapshot has moved, and that the master path learned while the direct path did not.

```python filename=modules/below-the-prompt/code/masterweights-inter-01/masterweights.py:92-103 COMPLETE
    single_update_underflows = round_fp16(w + u, mb) == round_fp16(w, mb)
    print("  a single update rounds back to the same fp16 weight = %s (%.6f)" % (single_update_underflows, round_fp16(w + u, mb)))

    direct = train_direct(w, u, s, mb)
    direct_stuck = direct == round_fp16(w, mb)
    print("  direct fp16: the weight never moves over %d steps = %s (%.4f)" % (s, direct_stuck, direct))

    master, master_fp16 = train_master(w, u, s, mb)
    master_accumulates = abs(master - (w + s * u)) < 1e-9
    print("  fp32 master: the update accumulates faithfully = %s (%.4f)" % (master_accumulates, master))

    master_snapshot_moves = master_fp16 != round_fp16(w, mb)
    print("  the fp16 snapshot of the master has moved = %s (%.4f)" % (master_snapshot_moves, master_fp16))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the direct path ever secretly moves or the master path ever stops accumulating:

```text filename=masterweights.py --check
SELF-TEST — a small update underflows against an fp16 weight every step; an fp32 master banks it until it shows
--------------------------------------------------------------------------------------------------------------------
  a single update rounds back to the same fp16 weight = True (1.000000)
  direct fp16: the weight never moves over 100 steps = True (1.0000)
  fp32 master: the update accumulates faithfully = True (1.0400)
  the fp16 snapshot of the master has moved = True (1.0400)
  the master path learned and the direct path did not = True
```

**The self-test asserts both that a single step rounds away and that the direct weight is unchanged after all 100 — proving the failure is per-step and total, not a slow drift that eventually accumulates in fp16 anyway.**

## Definition of done

You can explain why floating-point resolution is relative, and why an update's fate depends on its size relative to the weight, not its absolute size.
You can distinguish this failure from gradient underflow: one is an addition rounding off, the other a value too small to represent, fixed by master weights and loss scaling respectively.
You can explain why the update rounds away every step rather than accumulating slowly in fp16.
You can describe how an fp32 master fixes it — accumulate on the fine grid, snapshot to fp16 for the passes — and predict when the snapshot finally moves.
You can name the two pillars of mixed-precision training and say which underflow each addresses.

## Boss fight

Change the weight to a larger magnitude — say 100.0 — keeping the same 0.0004 update, and reason about what happens. The ulp near 100 is about 2^(6-10) = 0.0625, so the update is now more than a hundred times below the grid spacing; it rounds away even more decisively, and it would take an accumulated change of over 0.06 before the fp16 snapshot moved. The lesson generalizes: the bigger the weight, the coarser its fp16 grid, so the update-to-weight ratio that fp16 can resolve is fixed at roughly the mantissa width — about 2^-10 — regardless of scale. Large weights are exactly where direct fp16 updates fail hardest, which is why master weights matter most for the biggest parameters.

Now consider bf16 instead of fp16. bfloat16 has only 7 mantissa bits (versus fp16's 10), so its ulp near 1.0 is about 2^-7, roughly 0.008 — even coarser than fp16, and the update rounds away even more easily. People sometimes assume bf16 is "safer" than fp16 because it has fp32's exponent range and so does not underflow gradients to zero — and that is true, it needs no loss scaling. But its coarser mantissa makes the update-rounding problem worse, not better, so bf16 needs fp32 master weights just as much. The two precisions trade range for mantissa, and master weights are required either way.

**The resolvable update-to-weight ratio is fixed near 2^(-mantissa bits) at every scale, so larger weights fail harder; and bf16, despite needing no loss scaling, has a coarser mantissa than fp16 and so needs fp32 master weights even more.**

## External resources

Micikevicius et al., "Mixed Precision Training" (2018), introduced both loss scaling and the fp32 master-weight copy, and shows the update-underflow effect directly.
NVIDIA's mixed-precision training guide and the PyTorch AMP documentation describe keeping fp32 master weights in the optimizer while running fp16/bf16 forward and backward passes.
The topic's own module on fp16 loss scaling covers the other half of mixed precision — the gradient-underflow failure that this one is carefully distinguished from.
