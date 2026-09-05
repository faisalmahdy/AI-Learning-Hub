---
id: media-inter-08
title: Subsample chroma, not luma — the eye barely sees color detail but is sharp on brightness
topic: generative-media
level: intermediate
status: ready
time: 5-8h
summary: Compression that throws away resolution has to choose what to throw away, and an image split into luma (brightness, Y) and chroma (color, Cb, Cr) offers an easy answer: the eye is far more sensitive to fine detail in brightness than in color, so halving a chroma channel's resolution is almost invisible while halving luma visibly softens the image. To isolate the principle, all three channels here carry the identical high-frequency pattern, so subsampling any one produces the exact same raw reconstruction error of 109.5 — the only thing that differs is the perceptual weight, luma 0.85 against each chroma channel's 0.075. Subsampling luma therefore costs 93.1 perceptual units while subsampling a chroma channel costs 8.2: the same 4 samples saved and the same raw error, but 11.3 times the visible damage when you take it from the wrong channel. This is why JPEG and essentially every video codec store chroma at half or quarter resolution (4:2:0) and keep luma full — same bytes, wildly different perceptual cost, so you spend your compression budget on the channels the eye cannot check.
eli5: Your eyes are like a camera that sees sharp black-and-white detail but blurry color. So when a picture needs to be shrunk to save space, you can blur the color a lot and almost nobody notices, but if you blur the brightness the same amount the picture looks obviously fuzzy. Smart compression blurs the color and keeps the brightness crisp — same space saved, but it hides the damage where your eyes weren't looking anyway.
---

## Why this module

Lossy image and video compression is, at bottom, the art of throwing away information the viewer will not miss. The single biggest lever for that is a fact about human vision: we resolve fine detail in brightness far better than in color. Our eyes have many more receptors for light level than for hue, so a rapid change in brightness reads as a crisp edge while the same rapid change in color reads as a soft smear we can barely locate. A compressor that knows this can throw away color detail almost for free while guarding brightness detail carefully.

To exploit it, you first stop thinking in red-green-blue and start thinking in luma and chroma. An image is transformed into a luma channel (Y, the brightness) and two chroma channels (Cb and Cr, the color). Now the channels are not interchangeable: luma carries the detail the eye is sharp on, chroma the detail the eye is blurry on.

<svg viewBox="0 0 700 160" role="img" aria-label="Two grids representing the eye's acuity. The luma grid is a fine, sharp checkerboard, showing the eye resolves brightness detail. The chroma grid is a blurry, smeared version, showing the eye barely resolves color detail. Same underlying detail, seen sharply in luma and blurrily in chroma.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the same fine detail: crisp to the eye in luma, blurry in chroma</text>
    <text x="120" y="44" text-anchor="middle" fill="var(--s1)" font-size="8">LUMA — eye is sharp</text>
    <g>
      <rect x="60" y="52" width="24" height="24" fill="var(--ink)"></rect><rect x="84" y="52" width="24" height="24" fill="var(--panel)"></rect><rect x="108" y="52" width="24" height="24" fill="var(--ink)"></rect><rect x="132" y="52" width="24" height="24" fill="var(--panel)"></rect>
      <rect x="60" y="76" width="24" height="24" fill="var(--panel)"></rect><rect x="84" y="76" width="24" height="24" fill="var(--ink)"></rect><rect x="108" y="76" width="24" height="24" fill="var(--panel)"></rect><rect x="132" y="76" width="24" height="24" fill="var(--ink)"></rect>
    </g>
    <text x="120" y="118" text-anchor="middle" fill="var(--muted)" font-size="7">every edge visible</text>
    <text x="470" y="44" text-anchor="middle" fill="var(--s2)" font-size="8">CHROMA — eye is blurry</text>
    <g opacity="0.5">
      <rect x="410" y="52" width="48" height="48" fill="var(--muted)"></rect><rect x="458" y="52" width="48" height="48" fill="var(--line)"></rect>
    </g>
    <text x="470" y="118" text-anchor="middle" fill="var(--muted)" font-size="7">detail smears together</text>
    <text x="60" y="146" fill="var(--muted)" font-size="8">so blur chroma freely; guard luma — that is where the eye checks</text>
  </g>
</svg>
^ The eye reads a fine checkerboard sharply in brightness but sees color as a smear, so the same detail loss is glaring in luma and nearly invisible in chroma. That asymmetry is what chroma subsampling exploits. Reducing the resolution of a channel — subsampling it — costs perceptually in proportion to how much the eye cares about that channel's detail, and the eye cares enormously more about luma. So the right move is to keep luma at full resolution and subsample chroma, which is exactly what the ubiquitous 4:2:0 scheme does: full-resolution Y, half-resolution Cb and Cr.

This module isolates the principle to a single number. It gives all three channels the identical high-frequency pattern, so subsampling any one of them produces the exact same raw reconstruction error — the same physical loss of detail. The only difference left is the perceptual weight of the channel, and the result is stark: subsampling luma costs 93 perceptual units, subsampling a chroma channel costs 8, for the same bytes saved and the same raw error. Everything runs offline against a channel fixture, stdlib Python 3, `$0.00`, with every error computed. The instinct to unlearn is that all pixels and channels are equally worth keeping. They are not — the eye audits brightness detail and waves color detail through, so a compressor should spend its resolution where the eye will check and skimp where it will not.

## Concepts

Named here so you can find them again; each is built below.

- **Luma (Y)** — the brightness channel; the detail the eye resolves sharply.
- **Chroma (Cb, Cr)** — the color channels; detail the eye resolves poorly.
- **Subsampling** — halving a channel's resolution (average pairs) to save bytes.
- **Raw reconstruction error** — the physical detail lost when a channel is subsampled and rebuilt.
- **Perceptual weight** — how much the eye's acuity depends on a channel's detail; luma high, chroma low.
- **Perceptual cost** — raw error times perceptual weight; what the viewer actually notices.

## Worked example

Source: the resolution-reduction step inside a lossy codec — the choice of which channel to subsample. The channels stand in for the luma/chroma decomposition JPEG and video use; the identical patterns are a deliberate control so the only variable is perceptual sensitivity, not the content.

Script and fixture: `modules/generative-media/code/media-inter-08/` — `chroma.py`, and `image.json`, three channels. Every command runs from there.

### Subsample, reconstruct, and the raw error

Subsampling halves a channel by averaging adjacent pairs; the raw error is how far the rebuilt channel drifts from the original.

```
# chroma.py:39-52 — COMPLETE (halve by averaging pairs, then measure the reconstruction error)
def subsample_reconstruct(channel):
    """Halve resolution by averaging adjacent pairs, then reconstruct by duplicating each average."""
    out = []
    for i in range(0, len(channel), 2):
        avg = (channel[i] + channel[i + 1]) / 2
        out.extend([avg, avg])
    return out


def raw_error(channel):
    """Mean absolute error between the channel and its subsample-then-reconstruct version."""
    recon = subsample_reconstruct(channel)
    return sum(abs(a - b) for a, b in zip(channel, recon)) / len(channel)
```

The bytes saved is just how many samples the halving removes:

```
# chroma.py:54-56 — COMPLETE (subsampling a channel removes half its samples)
def saved_samples(channel):
    """How many samples subsampling this channel removes (half of them)."""
    return len(channel) // 2
```

<svg viewBox="0 0 700 150" role="img" aria-label="The 4:2:0 layout. Luma is a full 4x2 grid of samples. Each chroma channel is a half-resolution 2x2 grid. Luma kept full, chroma halved.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">4:2:0 — luma at full resolution, chroma halved</text>
    <text x="30" y="52" fill="var(--s1)" font-size="8">Y (luma, full)</text>
    <g fill="var(--acc-soft)" stroke="var(--acc-line)">
      <rect x="150" y="38" width="22" height="22"></rect><rect x="172" y="38" width="22" height="22"></rect><rect x="194" y="38" width="22" height="22"></rect><rect x="216" y="38" width="22" height="22"></rect>
      <rect x="150" y="60" width="22" height="22"></rect><rect x="172" y="60" width="22" height="22"></rect><rect x="194" y="60" width="22" height="22"></rect><rect x="216" y="60" width="22" height="22"></rect>
    </g>
    <text x="270" y="60" fill="var(--muted)" font-size="7">8 samples</text>
    <text x="30" y="110" fill="var(--s2)" font-size="8">Cb, Cr (chroma, half)</text>
    <g fill="var(--panel)" stroke="var(--s2)">
      <rect x="150" y="96" width="44" height="22"></rect><rect x="194" y="96" width="44" height="22"></rect>
    </g>
    <text x="290" y="110" fill="var(--muted)" font-size="7">4 samples each — each block covers 2 luma samples</text>
  </g>
</svg>
^ In 4:2:0 the luma grid keeps every sample while each chroma sample covers a 2-wide block, so the color channels store half the samples. The eye gets its sharp brightness and never notices the coarser color.

The raw error is a physical quantity — bytes of detail lost — with no perception in it yet. Look at the three channels:

```
# $ python3 chroma.py --channels
#   channel  role        pattern                 raw error  weight
#   Y        luma        [16, 235, 16, 235, ...] 109.5      0.850
#   Cb       chroma      [16, 235, 16, 235, ...] 109.5      0.075
#   Cr       chroma      [16, 235, 16, 235, ...] 109.5      0.075
```

run: 2026-08-27 · deterministic; channel patterns and weights are a fixture · 3 channels · `python3 chroma.py --channels`

All three channels carry the same pattern and so lose the same 109.5 of raw detail when subsampled — that equality is on purpose, a control. If the channels differed in content the comparison would confound content with sensitivity; by making the content identical, the only thing left to explain any difference in cost is the weight column, where luma's 0.85 towers over each chroma channel's 0.075. The physical loss is equal; the perceptual loss cannot be, because the eye weights these channels a factor of eleven apart.

### Perceptual cost, and which channel to spend

The perceptual cost scales the raw error by the channel's sensitivity.

```
# chroma.py:61-63 — COMPLETE (perceptual cost: raw error weighted by the eye's sensitivity)
def perceptual_cost(name, data):
    """Raw error of subsampling one channel, weighted by that channel's perceptual sensitivity."""
    return raw_error(data["channels"][name]) * data["weights"][name]
```

Now compare subsampling luma against subsampling a chroma channel — same operation, same bytes saved:

```
# $ python3 chroma.py --cost
#   subsample Y   : saves 4 samples, raw error 109.5, perceptual cost 93.1
#   subsample Cb  : saves 4 samples, raw error 109.5, perceptual cost 8.2
#   luma subsampling costs 11.3x more for the same bytes.
```

run: 2026-08-27 · deterministic · `python3 chroma.py --cost`

Both choices save the same 4 samples and inflict the same 109.5 of raw error — they are identical on every axis except the one that matters to a viewer. Subsampling luma costs 93.1 perceptual units; subsampling chroma costs 8.2, eleven times less, for exactly the same compression. That ratio is the entire justification for 4:2:0: given a fixed budget of detail to discard, discard it from chroma, where the eye is not looking, and keep luma sharp, where it is. A compressor that subsampled luma instead would pay eleven times the visible cost for nothing extra in return.

<svg viewBox="0 0 700 190" role="img" aria-label="Two bars for the same operation. Subsampling luma: raw error 109.5, perceptual cost 93.1 (tall bar). Subsampling chroma: raw error 109.5, perceptual cost 8.2 (short bar). Both save the same 4 samples. The perceptual bars differ 11x though the raw error bars are equal.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">same bytes saved, same raw error — 11x difference in what the eye sees</text>
    <line x1="60" y1="160" x2="660" y2="160" stroke="var(--line)"></line>
    <text x="180" y="178" text-anchor="middle" fill="var(--muted)" font-size="8">subsample LUMA</text>
    <rect x="100" y="150" width="50" height="10" fill="var(--muted)"></rect><text x="125" y="144" text-anchor="middle" fill="var(--muted)" font-size="7">raw 109.5</text>
    <rect x="190" y="45" width="50" height="115" fill="var(--s2)"></rect><text x="215" y="39" text-anchor="middle" fill="var(--s2)" font-size="7">percept 93.1</text>
    <text x="500" y="178" text-anchor="middle" fill="var(--muted)" font-size="8">subsample CHROMA</text>
    <rect x="420" y="150" width="50" height="10" fill="var(--muted)"></rect><text x="445" y="144" text-anchor="middle" fill="var(--muted)" font-size="7">raw 109.5</text>
    <rect x="510" y="150" width="50" height="10" fill="var(--s1)"></rect><text x="535" y="144" text-anchor="middle" fill="var(--s1)" font-size="7">percept 8.2</text>
    <text x="60" y="120" fill="var(--muted)" font-size="8">the raw-error bars are equal; only the perceptual bars diverge — spend from the right channel</text>
  </g>
</svg>
^ Both operations lose the same raw detail (109.5) and save the same bytes, but the perceptual cost of taking it from luma (93.1) dwarfs taking it from chroma (8.2). The eye audits the left bar and ignores the right.

**The eye resolves brightness detail far better than color detail, so subsample chroma and keep luma sharp — with identical content and identical 109.5 raw error, subsampling luma costs 93.1 perceptual units against chroma's 8.2, an 11x difference for the same bytes; a codec spends its discarded resolution where the viewer cannot check (chroma), which is exactly what 4:2:0 does.**

### The self-test

The `--check` mode plants the bug — subsampling the wrong channel — and proves it: luma and chroma subsampling save the same bytes and inflict the same raw error, yet luma costs far more perceptually because its weight is higher.

```
# $ python3 chroma.py --check
#   subsampling luma and chroma save the same number of samples = True (4 each)
#   the raw reconstruction error is identical for both = True (109.5)
#   subsampling luma costs much more perceptually = True (93.1 vs 8.2, 11.3x)
#   luma's perceptual weight exceeds chroma's = True (0.850 vs 0.075)
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 chroma.py --check`

The `same_bytes` and `raw_equal` lines are the controls that make the conclusion airtight: because the two choices are identical on bytes saved and on raw error, the entire difference in perceptual cost must come from the weight, not from the operation or the content. This is the experimental discipline the whole hub insists on — hold everything constant but the one variable you are testing, so the effect you measure can only be that variable.

```
# chroma.py:106-111 — COMPLETE (the controls: identical raw error, so only the weight differs)
    raw_equal = abs(raw_error(data["channels"][luma]) - raw_error(data["channels"][chroma])) < 1e-9
    print("  the raw reconstruction error is identical for both = %s (%.1f)"
          % (raw_equal, raw_error(data["channels"][luma])))

    cl, cc = perceptual_cost(luma, data), perceptual_cost(chroma, data)
    luma_costlier = cl > 3 * cc
```

### The running tally

| subsample | samples saved | raw error | perceptual weight | perceptual cost |
|---|---|---|---|---|
| luma (Y) | 4 | 109.5 | 0.850 | 93.1 |
| chroma (Cb) | 4 | 109.5 | 0.075 | 8.2 |
| chroma (Cr) | 4 | 109.5 | 0.075 | 8.2 |

Read across: the first three columns are identical for every row, and only the last two diverge. That is the experiment reduced to a table — same savings, same physical loss, and the perceptual cost tracking the weight alone. Subsample both chroma channels together, as 4:2:0 actually does, and you save twice the bytes (8 samples) for a combined perceptual cost of about 16 — still a fraction of luma's 93 for half the savings. Any way you slice it, chroma is where the compression budget should be spent, because the eye simply is not checking there.

### What we did not settle

This is the perceptual argument for 4:2:0; a full codec has more. The subsampling here is a crude box average; real codecs use better filters (and must, per the aliasing module `media-inter-03`, low-pass before decimating) and often subsample chroma vertically too (4:2:0 versus 4:2:2). The RGB-to-YCbCr transform itself is where luma and chroma are separated, and it is lossy in fixed point, a separate budget. Chroma subsampling has real failure cases — sharp saturated color edges (red text on black) and chroma keying can show visible artifacts, which is why professional/intermediate formats sometimes keep 4:4:4 full chroma. And the weights here are a stylized stand-in for the eye's contrast-sensitivity function, which is spatial-frequency dependent, not a single number. The invariant: brightness detail is precious and color detail is cheap, so discard resolution from chroma first.

## Build

The build in one paragraph: transform the image into luma and chroma, then spend your resolution budget by keeping luma at full resolution and subsampling the chroma channels — because the eye resolves brightness detail far better than color, so a given amount of discarded resolution costs a fraction as much perceptually when taken from chroma; measure the cost as raw error times a channel's perceptual weight, not raw error alone. Low-pass filter before subsampling (aliasing), consider vertical chroma subsampling too, and keep full 4:4:4 chroma for content with sharp saturated color edges or chroma keying where the artifacts show.

We opened on the channels. The number that proves the choice is the perceptual cost of subsampling each:

```
# modules/generative-media/code/media-inter-08/ — COMPLETE, run from that directory
$ python3 chroma.py --cost
  subsample Y   : saves 4 samples, raw error 109.5, perceptual cost 93.1
  subsample Cb  : saves 4 samples, raw error 109.5, perceptual cost 8.2
```

Now build your own. Take a real image, transform to YCbCr, and subsample luma versus a chroma channel by the same amount. Your number to beat is not the byte count — it is identical; it is **the perceptual cost of each, weighted by the eye's channel sensitivity** — subsampling chroma should cost a small fraction of subsampling luma for the same savings. Confirm the raw error is equal so the difference is purely perceptual. Bring back both perceptual costs. Good luck.

## Definition of done

- [ ] A subsample-and-reconstruct that halves a channel by averaging pairs
- [ ] A raw reconstruction error, identical across channels with identical content
- [ ] A perceptual cost: raw error times a channel's perceptual weight
- [ ] Confirmation luma and chroma subsampling save the same bytes and inflict the same raw error
- [ ] Confirmation subsampling luma costs far more perceptually than chroma
- [ ] Confirmation luma's perceptual weight exceeds chroma's
- [ ] `python3 chroma.py --check` printing SELF-TEST PASS: same_bytes, raw_equal, luma_costlier, weight_luma_high
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why can a codec throw away color detail almost for free but not brightness detail?
2. What does 4:2:0 keep at full resolution and what does it subsample?
3. Why does the fixture give all three channels the identical pattern?
4. Same bytes saved, same raw error — where does the 11x difference in perceptual cost come from?
5. Your own image was subsampled in luma and in chroma. What perceptual cost did each incur, and was the raw error equal?

## External resources

- Any JPEG or video-codec reference on chroma subsampling (4:4:4 vs 4:2:2 vs 4:2:0) — my summary: the sampling schemes, their byte savings, and where each is appropriate; read it for the vertical subsampling and edge-case artifacts this module leaves out.
- Material on the human contrast sensitivity function (luminance vs chrominance) — my summary: why the eye's acuity for color is far lower than for brightness, and its spatial-frequency dependence; read it for the perceptual weights stated as a single number here.
- This hub, *media-inter-07* (perceptual luma weights) and *media-inter-03* (filter before you downsample) — read them for how luma is computed from RGB and why subsampling must low-pass filter first.
