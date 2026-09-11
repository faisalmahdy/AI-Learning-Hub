---
id: quant-inter-01
title: Quantize the weights — and watch one outlier wreck the whole grid
topic: below-the-prompt
level: intermediate
status: ready
time: 8-10h
summary: Affine quantization maps float weights onto a small integer grid, trading reconstruction error for memory, and at 8 bits the error is a rounding whisper while the tensor shrinks to a quarter its size. But quantization error is set by the range you have to span, and one outlier weight of 48 among values in [-1.5, 1.5] stretches a single global scale so far that at 4 bits every ordinary weight collapses onto almost no levels — per-tensor bulk RMSE 1.06 — while giving each channel its own scale isolates the outlier and drops the same bulk error to 0.04, 27 times better at the identical bit width. The lesson is that quantization accuracy is a fight against dynamic range, and per-channel scaling is how you stop one weight from spending everyone's precision.
eli5: Turning a photo into a coloring book means picking a few crayons to stand in for millions of colors. If everything is a shade of blue, a handful of blues works fine. But if one pixel is bright red, and you insist on one box of crayons for the whole picture, you waste most of them reaching red and the blues all turn into the same muddy shade. The fix is a separate crayon box per region, so the red pixel does not ruin the blues.
---

## Why this module

A model's weights are floating-point numbers, and floats are expensive to store and move: 32 bits each, or 16 in half precision. Most of that precision is not doing any work — the weights cluster in a narrow band, and the low-order bits are noise. Quantization is the move that cashes this in: map the floats onto a small grid of integers with far fewer bits, keep only the integer codes plus a scale to undo the mapping, and you have shrunk the model — less memory, less bandwidth, and on the right hardware, faster arithmetic. This module builds the simplest real quantizer, affine per-group quantization, and measures the one trade that governs it and the one failure that breaks it.

The trade is bits against error. Fewer bits means a coarser grid, which means each weight lands further from where it started — reconstruction error. At 8 bits that error is a rounding whisper; at 2 bits it is a wrecking ball. But error is not set by the bit count alone. It is set by the bit count and the range the grid has to span, and that second factor is where naive quantization dies on real transformers. A single large-magnitude weight — an outlier, and transformer layers grow them — forces one global scale to stretch across a huge range, so every ordinary weight is quantized as if it too needed that range, and collapses onto a handful of levels. The whole tensor pays for one weight. The fix, and the reason production quantization is per-channel rather than per-tensor, is to give each channel its own scale so the outlier is isolated to its own row.

You need no prior module, only comfort with rounding and a mean. Everything runs offline against a tiny weight fixture — six channels of eight weights, one carrying a planted outlier — stdlib Python 3, `$0.00`. The instinct to unlearn is that quantization error is a function of how many bits you keep. It is a function of bits and dynamic range together, and the range is the half most people forget until an outlier makes it unforgettable.

Here is quantization working exactly as advertised, and then not:

```
# modules/below-the-prompt/code/quant-inter-01/ — COMPLETE, run from that directory
$ python3 quantize.py --sweep

SWEEP — per-tensor quantization: fewer bits, less memory, more error
------------------------------------------------------------------
  bits   memory vs fp32   RMSE (all weights)   max abs error
  8      0.25x           0.0542               0.0955
  4      0.12x           1.0668               1.6220
  3      0.09x           1.5940               2.8200
  2      0.06x           1.5940               2.8200
```

run: 2026-08-26 · deterministic; weights are a fixture · 48 weights · `python3 quantize.py --sweep`

Eight bits shrinks the tensor to a quarter for a rounding-level error. Then it falls off a cliff — RMSE 1.07 at 4 bits, on weights that mostly live inside `[-1.5, 1.5]`. That cliff is not the bit count; it is one weight, and this module is about seeing exactly that.

## Concepts

Named here so you can find them again; each is built below.

- **Affine quantization** — map floats to integers by `q = round((x - zero) / scale)`, undo with `x_hat = zero + q * scale`.
- **Scale and zero-point** — the step size and offset of the integer grid; `scale = range / (2^bits - 1)`.
- **Reconstruction error** — how far a dequantized weight lands from the original; bounded by half a step.
- **Dynamic range** — the spread the grid must span; the second driver of error, alongside bits.
- **Outlier** — one large-magnitude weight that inflates the range and starves the rest of precision.
- **Per-tensor vs per-channel** — one scale for the whole matrix, or one per row; the fix for outliers.

## Worked example

Source: the general post-training quantization pattern that llama.cpp, GPTQ, and LLM.int8() all implement, distilled to its arithmetic; the weight values here stand in for one layer's tensor so the error is exact and checkable. The outlier is the documented failure that motivated per-channel and mixed-precision quantization in real LLM serving.

Script and fixture: `modules/below-the-prompt/code/quant-inter-01/` — `quantize.py`, and `weights.json`, six channels of eight weights, channel 5 carrying a planted outlier of 48.0. Every command runs from there.

### The quantizer: floats onto an integer grid

Affine quantization lays a uniform grid of `2^bits` points across the range of the values and snaps each float to the nearest grid point. The grid is described by two numbers: `scale`, the distance between adjacent points, and `zero`, where the grid starts.

```
# quantize.py:38-49 — COMPLETE (affine quantize + dequantize of one group)
def quantize(values, bits):
    """Affine per-group quantize/dequantize. Returns (x_hat list, scale, zero)."""
    levels = (1 << bits) - 1
    lo, hi = min(values), max(values)
    scale = (hi - lo) / levels if hi > lo else 1.0
    zero = lo
    x_hat = []
    for x in values:
        q = round((x - zero) / scale)
        q = 0 if q < 0 else (levels if q > levels else q)
        x_hat.append(zero + q * scale)
    return x_hat, scale, zero
```

The `scale` is the whole story: it is `range / (2^bits - 1)`. Read that as a fraction with the range on top. More bits enlarges the denominator and shrinks the step — good. But a wider range enlarges the numerator and grows the step — bad. The error on any single weight is at most half a step, `scale / 2`, because rounding lands you within half a grid spacing of the target. So the error is controlled by both terms of that fraction, and either one going the wrong way loosens the bound.

### The trade, measured: bits down, error up

Error is scored two ways: RMSE, the typical distance a weight moved, and the max absolute error, the worst single weight.

```
# quantize.py:52-57 — COMPLETE (the two error measures)
def rmse(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


def max_abs_err(a, b):
    return max(abs(x - y) for x, y in zip(a, b))
```

The sweep quantizes the whole tensor with one scale and reports error against memory. The numbers came from the cold open: at 8 bits, RMSE 0.054 for a 4x shrink; at 4 bits, RMSE 1.07; at 3 and 2 bits, a flat 1.59. That plateau at the bottom is worth a pause — going from 3 bits to 2 does not make it worse, because by then the ordinary weights have already collapsed onto the single lowest level and cannot fall further. They were destroyed earlier, at 4 bits, and by something other than the bit count.

<svg viewBox="0 0 700 190" role="img" aria-label="A curve of per-tensor RMSE against bit width. At 8 bits RMSE is near zero (0.05). At 4 bits it jumps to 1.07. At 3 and 2 bits it is flat at 1.59, a plateau. The drop from 4 to 8 bits is a cliff, not a gentle slope.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">per-tensor RMSE vs bits: a cliff between 4 and 8, a plateau below 4</text>
    <line x1="60" y1="150" x2="640" y2="150" stroke="var(--grid)"></line>
    <line x1="60" y1="30" x2="60" y2="150" stroke="var(--grid)"></line>
    <polyline points="120,150 320,150 460,66 620,143" fill="none" stroke="var(--s2)" stroke-width="2.5"></polyline>
    <circle cx="120" cy="150" r="3" fill="var(--s2)"></circle><circle cx="320" cy="150" r="3" fill="var(--s2)"></circle><circle cx="460" cy="66" r="3" fill="var(--s2)"></circle><circle cx="620" cy="143" r="3" fill="var(--s2)"></circle>
    <text x="120" y="165" text-anchor="middle" fill="var(--muted)">2b</text><text x="320" y="165" text-anchor="middle" fill="var(--muted)">3b</text><text x="460" y="165" text-anchor="middle" fill="var(--muted)">4b</text><text x="620" y="165" text-anchor="middle" fill="var(--muted)">8b</text>
    <text x="128" y="145" fill="var(--muted)" font-size="8">1.59</text><text x="466" y="62" fill="var(--muted)" font-size="8">1.07</text><text x="600" y="138" fill="var(--muted)" font-size="8">0.05</text>
    <text x="200" y="130" fill="var(--muted)" font-size="8">plateau: ordinary weights already pinned to one level</text>
  </g>
</svg>
^ Below 4 bits the curve flattens, not because quantization got kinder but because the ordinary weights had already collapsed onto a single level and had no further to fall. The real event is the 8-to-4 cliff, and it is the outlier's doing.

<svg viewBox="0 0 700 190" role="img" aria-label="A number line from -1.5 to 48. Ordinary weights cluster tightly between -1.5 and 1.5 on the far left. A single outlier sits at 48 on the far right. Grid ticks for a 4-bit per-tensor scale are spaced about 3.3 apart, so only one or two ticks fall anywhere near the cluster of ordinary weights.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">one global 4-bit grid must span -1.5 to 48; its steps are ~3.3 wide</text>
    <line x1="40" y1="90" x2="660" y2="90" stroke="var(--grid)"></line>
    <g stroke="var(--line)">
      <line x1="52" y1="84" x2="52" y2="96"></line><line x1="93" y1="84" x2="93" y2="96"></line><line x1="134" y1="84" x2="134" y2="96"></line><line x1="175" y1="84" x2="175" y2="96"></line><line x1="216" y1="84" x2="216" y2="96"></line><line x1="257" y1="84" x2="257" y2="96"></line><line x1="380" y1="84" x2="380" y2="96"></line><line x1="503" y1="84" x2="503" y2="96"></line><line x1="640" y1="84" x2="640" y2="96"></line>
    </g>
    <g fill="var(--s1)"><circle cx="52" cy="90" r="3"></circle><circle cx="60" cy="90" r="3"></circle><circle cx="46" cy="90" r="3"></circle><circle cx="68" cy="90" r="3"></circle><circle cx="55" cy="90" r="3"></circle></g>
    <circle cx="640" cy="90" r="4" fill="var(--s2)"></circle>
    <text x="55" y="118" text-anchor="middle" fill="var(--s1)" font-size="8">48 ordinary weights, all here</text>
    <text x="640" y="118" text-anchor="middle" fill="var(--s2)" font-size="8">outlier = 48</text>
    <text x="130" y="140" fill="var(--muted)" font-size="8">only ~1 grid step covers the whole cluster -> everyone rounds to nearly the same code</text>
    <g fill="var(--muted)"><text x="40" y="80">-1.5</text><text x="632" y="80">48</text></g>
  </g>
</svg>
^ With one scale for the tensor, the grid must reach the outlier at 48, so its steps are about 3.3 wide. The ordinary weights span barely more than one step, so they all snap to nearly the same integer code — the outlier spent everyone's precision.

### The failure: one outlier, one global scale

Look at where the cliff comes from. The ordinary weights sit in `[-1.5, 1.5]`, a range of 3. The outlier at 48 makes the tensor's range about 49. At 4 bits there are 15 steps, so per-tensor `scale ≈ 49 / 15 ≈ 3.3`. That single step, 3.3, is wider than the entire spread of the ordinary weights. Every one of them rounds to essentially the same code, and dequantizes to essentially the same value — the model's real structure, erased. The reconstruction is still within half a step of each weight, exactly as promised; the trouble is the step is enormous, because it was sized for a weight that is nowhere near the rest.

### The fix: one scale per channel

Give each row its own scale and the outlier can only damage its own row.

```
# quantize.py:62-77 — COMPLETE (per-tensor: one scale; per-channel: one scale per row)
def per_tensor(channels, bits):
    """One scale for the whole matrix. Returns flat original, flat reconstructed."""
    flat = [w for row in channels for w in row]
    x_hat, _, _ = quantize(flat, bits)
    return flat, x_hat


def per_channel(channels, bits):
    """One scale per row. Returns flat original, flat reconstructed (row order)."""
    flat, recon = [], []
    for row in channels:
        r_hat, _, _ = quantize(row, bits)
        flat.extend(row)
        recon.extend(r_hat)
    return flat, recon
```

To judge the fix honestly, we score error on the ordinary rows only — skipping the outlier's own row, since nobody expects that one to quantize cleanly — under each scheme:

```
# quantize.py:84-98 — COMPLETE (score bulk error under one global scale)
def bulk_rmse_per_tensor(data, bits):
    """Quantize the whole tensor with one scale, then score error on the ordinary rows only."""
    channels, oc = data["channels"], data["outlier_channel"]
    flat = [w for row in channels for w in row]
    x_hat, _, _ = quantize(flat, bits)
    orig, recon = [], []
    idx = 0
    for i, row in enumerate(channels):
        for w in row:
            if i != oc:
                orig.append(w)
                recon.append(x_hat[idx])
            idx += 1
    return rmse(orig, recon)
```

Now compare the two schemes on those ordinary rows, at the same 4 bits:

```
# $ python3 quantize.py --outlier
#   the outlier (48.0) lives in channel 5; we score error on the OTHER rows
#   per-tensor  bulk RMSE = 1.0579   (global scale stretched by the outlier)
#   per-channel bulk RMSE = 0.0397   (outlier isolated to its own row)
#   per-channel is 26.7x more accurate on the ordinary weights, same bit width.
```

run: 2026-08-26 · deterministic · `python3 quantize.py --outlier`

Same weights, same 4 bits, same arithmetic — and a 27x difference in error on the weights that matter, decided entirely by whether the outlier's channel shares a scale with everyone else. Per-channel gives each ordinary row a scale of about `3 / 15 = 0.2`, so its step is small and its weights keep their precision; only channel 5, which really does span to 48, gets the wide grid it needs.

<svg viewBox="0 0 700 180" role="img" aria-label="Two horizontal bars showing bulk reconstruction RMSE at 4 bits. The per-tensor bar is long at 1.06. The per-channel bar is a tiny stub at 0.04, about one twenty-seventh the length.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="20" fill="var(--muted)">bulk RMSE on the ordinary weights, 4 bits, same tensor</text>
    <text x="20" y="70" fill="var(--ink)">per-tensor</text>
    <rect x="150" y="58" width="470" height="20" fill="var(--s2)"></rect>
    <text x="628" y="73" fill="var(--s2)" font-size="9">1.06</text>
    <text x="20" y="120" fill="var(--ink)">per-channel</text>
    <rect x="150" y="108" width="18" height="20" fill="var(--s1)"></rect>
    <text x="176" y="123" fill="var(--s1)" font-size="9">0.04</text>
    <text x="150" y="155" fill="var(--muted)" font-size="8">one scale per row isolates the outlier; the ordinary rows keep a tight grid -> 27x less error</text>
  </g>
</svg>
^ The only change between the bars is scope of the scale. Per-tensor lets one weight set the grid for all six rows; per-channel confines it. Same bits, same numbers, 27x apart.

**Quantization error is bounded by half a step, and the step is range over levels — so an outlier that widens the range costs every weight its precision, which is why real quantization scales per channel, not per tensor.**

### The self-test

The `--check` mode asserts the three properties: the round-trip is bounded, more bits help, and per-channel isolation beats one global scale.

```
# $ python3 quantize.py --check
#   per-group reconstruction error <= scale/2 = True (0.0727 <= 0.0773)
#   RMSE falls monotonically as bits rise 2->8 = True (1.594 > 1.594 > 1.067 > 0.054)
#   per-channel bulk RMSE < per-tensor/5 = True (0.0397 vs 1.0579)
#   SELF-TEST PASS  bounded=True  monotone=True  per_channel_wins=True
```

run: 2026-08-26 · deterministic · `python3 quantize.py --check`

The bounded check is the correctness anchor: for any group, no weight ever lands more than half a step from where it started. If a refactor broke the scale or the clamp, that bound would blow first. The monotone check confirms bits still help when the range is fixed. The per-channel check is the lesson, made into a test: at identical bits, confining the scale to a channel cuts bulk error by more than five times — here, twenty-seven.

### The running tally

| scheme | bits | bulk RMSE (ordinary rows) | what set the error |
|---|---|---|---|
| per-tensor | 8 | 0.05 | fine — 255 levels absorb even the wide range |
| per-tensor | 4 | 1.06 | the outlier's range, not the bit count |
| per-channel | 4 | 0.04 | each row's own small range |

Read the middle row against the others. Dropping from 8 to 4 bits did not have to cost 20x error; it cost that much because the range was 49, not 3. Fix the range — confine the scale to a channel — and 4 bits is nearly as clean as 8 was. Bits and range are two separate knobs, and on a tensor with outliers the range is the one that is silently killing you.

### What we did not settle

This is per-tensor vs per-channel; real systems go further. Group-wise quantization splits each channel into small blocks with a scale per block, finer still. Mixed precision (LLM.int8()) keeps the outlier dimensions in full precision and quantizes only the rest. GPTQ and AWQ choose the rounding to minimize output error rather than weight error, since what matters is the layer's activations, not the weights in isolation — a weight can move a lot if it barely affects the output. And we quantized weights only; activation quantization is harder because activations change every forward pass, so their range must be calibrated or computed live. The arithmetic here is the floor all of those build on: a grid, a scale, and a range that an outlier will wreck unless you contain it.

## Build

The quantizer in one paragraph: pick a bit width; for each group (a channel, or a block within it) find its min and max, set `scale = range / (2^bits - 1)` and `zero = min`, snap each weight to `round((x - zero) / scale)` clamped to the grid, and store the codes plus the scale; to use a weight, dequantize with `zero + q * scale`. Measure reconstruction error as RMSE against the originals, and always measure it per scope — the whole tensor hides what one channel suffers. The rule that falls out: error is half a step, the step is range over levels, so shrink the range you quantize together whenever a group holds an outlier.

We opened on the sweep. The number that matters is not the bit width; it is what one scale has to span:

```
# modules/below-the-prompt/code/quant-inter-01/ — COMPLETE, run from that directory
$ python3 quantize.py --outlier
  per-tensor  bulk RMSE = 1.0579
  per-channel bulk RMSE = 0.0397
```

Now quantize your own weights. Take a real weight tensor — a layer from a small open model, or any matrix you have — and quantize it per-tensor and per-channel at 4 bits, scoring RMSE on the non-outlier rows. Your number to beat is not the per-tensor RMSE; it is **the ratio between per-tensor and per-channel bulk error**: the larger it is, the more your tensor has outliers, and the more per-channel (or group-wise) scaling buys you. Then find the outlier channels and confirm they are where the two schemes diverge. Bring back the ratio and which channels drove it. Good luck.

## Definition of done

- [ ] An affine quantizer: `scale = range / (2^bits - 1)`, `zero = min`, round-clamp-dequantize
- [ ] A bit-width sweep showing RMSE rise and memory fall together
- [ ] Per-tensor and per-channel bulk RMSE measured on the same tensor at the same bits
- [ ] Confirmation that per-channel isolates an outlier and cuts bulk error sharply
- [ ] Reconstruction error verified bounded by half a step within each group
- [ ] `python3 quantize.py --check` printing SELF-TEST PASS: bounded, monotone, per-channel wins
- [ ] Your own tensor swept, with the per-tensor/per-channel ratio and the driving channels recorded
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Write the affine quantize and dequantize equations, and state the exact bound on reconstruction error for one weight.
2. Two tensors are quantized at the same 4 bits; one has far higher error. Nothing about the bit width differs. What does, and how would you confirm it from the tensor?
3. Explain why per-channel quantization cut bulk RMSE 27x here while using the identical number of bits.
4. At 2 and 3 bits the per-tensor RMSE was identical. Why did dropping a bit stop making it worse?
5. Your own tensor was swept per-tensor and per-channel. What was the error ratio, which channels drove it, and what would group-wise quantization add on top?

## External resources

- Dettmers et al., *LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale* (2022) — https://arxiv.org/abs/2208.07339 — my summary: the paper that named the outlier-feature problem this module reproduces and fixed it by keeping outlier dimensions in higher precision; read it for why per-tensor int8 breaks on large transformers and what mixed precision does instead.
- Frantar et al., *GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers* (2022) — https://arxiv.org/abs/2210.17323 — my summary: quantization that chooses rounding to minimize output error rather than weight error, at 3-4 bits; read it for the next step past the naive round-to-nearest here, and why minimizing activation error beats minimizing weight error.
- This hub, *tokens-basic-01* — modules/below-the-prompt/tokens-basic-01.md — my summary: the other place a smooth average hides a per-item blowup; read it for the same measurement instinct — never trust a tensor-wide number when one element can dominate it — applied to token budgets.
