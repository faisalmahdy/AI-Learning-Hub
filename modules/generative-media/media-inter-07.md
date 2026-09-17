---
id: media-inter-07
title: Brightness is weighted by the eye, not (R+G+B)/3 — green is bright, blue is nearly dark
topic: generative-media
level: intermediate
status: ready
time: 5-8h
summary: Collapsing a color to one brightness — for grayscale, a luminance key, or a contrast check — tempts the obvious (R+G+B)/3, and it is wrong because the eye is not equally sensitive to the three primaries: green light looks far brighter than blue of the same intensity, and the standard Rec. 709 weights capture this as 0.2126·R + 0.7152·G + 0.0722·B, with green carrying nearly three-quarters of perceived brightness and blue a fourteenth. The average fails catastrophically on saturated color: pure red, green, and blue all average to 255/3 = 85, so it calls them equally bright and a grayscale built on it flattens a vivid red/green/blue image into three identical grays (spread 0), while perceptual luma spreads them across their true range — green 182, red 54, blue 18, spread 164 — and orders them green > red > blue the way the eye does. On a colored strip the average preserves only 85 levels of contrast against luma's 218. The weights sum to 1, so luma is a proper average, just the one the eye actually takes.
eli5: If you turn a color photo into black-and-white by just averaging the red, green, and blue numbers, something strange happens: a bright green and a deep blue come out the exact same shade of gray, even though your eyes see green as much brighter than blue. That's because your eyes care about green a lot, red a medium amount, and blue barely at all. The right recipe weights them that way — most of the "brightness" comes from green — so the gray version looks like the color version felt: green light, blue dark.
---

## Why this module

A lot of image work needs to turn a color — three numbers, red, green, blue — into a single number for how bright it is. Grayscale conversion is the obvious case, but the same reduction sits under a luminance key, a contrast or accessibility check, a thumbnail's brightness sort, the value channel of many effects. The formula that comes to mind first is the average: add the three channels and divide by three. It is simple, it is symmetric, and it is wrong, because it assumes the eye responds equally to red, green, and blue light, and the eye does no such thing.

Human vision is far more sensitive to green than to red, and far more to red than to blue. The same physical intensity of green light looks much brighter than that intensity of blue. The video and imaging standards encode this as a weighted sum — the Rec. 709 luma coefficients are 0.2126 for red, 0.7152 for green, and 0.0722 for blue. Green carries almost three-quarters of perceived brightness; blue carries about a fourteenth. Those weights are not arbitrary tuning; they are a measurement of the sensors in your eye, and any brightness that ignores them is measuring a quantity no one perceives.

<svg viewBox="0 0 700 130" role="img" aria-label="Two weight bars compared. The naive average splits brightness equally: red, green, blue each one third. Rec. 709 luma splits it 0.2126 red, 0.7152 green, 0.0722 blue, so green fills most of the bar and blue a sliver.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">how each formula splits brightness among the channels</text>
    <text x="30" y="46" fill="var(--muted)" font-size="8">naive</text>
    <rect x="90" y="32" width="187" height="22" fill="var(--s2)"></rect><text x="183" y="47" text-anchor="middle" fill="var(--panel)" font-size="7">red .33</text>
    <rect x="277" y="32" width="187" height="22" fill="var(--s1)"></rect><text x="370" y="47" text-anchor="middle" fill="var(--panel)" font-size="7">green .33</text>
    <rect x="464" y="32" width="186" height="22" fill="var(--muted)"></rect><text x="557" y="47" text-anchor="middle" fill="var(--panel)" font-size="7">blue .33</text>
    <text x="30" y="92" fill="var(--muted)" font-size="8">luma</text>
    <rect x="90" y="78" width="119" height="22" fill="var(--s2)"></rect><text x="149" y="93" text-anchor="middle" fill="var(--panel)" font-size="7">red .21</text>
    <rect x="209" y="78" width="401" height="22" fill="var(--s1)"></rect><text x="409" y="93" text-anchor="middle" fill="var(--panel)" font-size="7">green .72</text>
    <rect x="610" y="78" width="40" height="22" fill="var(--muted)"></rect><text x="630" y="93" text-anchor="middle" fill="var(--panel)" font-size="6">.07</text>
    <text x="90" y="120" fill="var(--muted)" font-size="8">luma gives green nearly three-quarters of the bar and blue a sliver — the eye's real weighting</text>
  </g>
</svg>
^ The average splits brightness into three equal thirds; luma gives green 0.72, red 0.21, and blue just 0.07. Both bars sum to 1, but only the luma split matches how much each primary actually contributes to what you see.

The gap is not subtle on saturated color — it is total. Pure red (255,0,0), pure green (0,255,0), and pure blue (0,0,255) all average to 255/3 = 85, so the naive formula declares the three primaries equally bright and cannot tell them apart by brightness at all. A grayscale built on the average turns a vivid red/green/blue design into three identical grays. Perceptual luma spreads the same three across their real range — green 182, red 54, blue 18 — and orders them the way you see them. This module computes both on a set of color patches, shows the average collapsing the primaries while luma orders them green > red > blue, and confirms the weights form a proper average. Everything runs offline against a color fixture, stdlib Python 3, `$0.00`, with every brightness computed from the weights. The instinct to unlearn is that brightness is the average of the channels. Brightness is the weighted average the eye takes, and green is most of it.

## Concepts

Named here so you can find them again; each is built below.

- **Naive brightness** — the unweighted average (R+G+B)/3; treats the primaries as equal.
- **Perceptual luma** — the Rec. 709 weighted sum 0.2126·R + 0.7152·G + 0.0722·B.
- **Channel weights** — the eye's sensitivity to each primary; green highest, blue lowest.
- **The collapse** — the average mapping pure red, green, and blue all to 85, indistinguishable.
- **Contrast (spread)** — the brightness range a formula assigns across a set of colors.
- **Ordering** — the brightest-first sort; luma gives green > red > blue, the perceptual truth.

## Worked example

Source: the color-to-brightness reduction inside grayscale conversion and luminance keys — the operation every image tool performs and many perform wrong. The color patches stand in for real pixels, chosen to expose the average's collapse on saturated primaries.

Script and fixture: `modules/generative-media/code/media-inter-07/` — `luma.py`, and `colors.json`, six color patches and a small strip. Every command runs from there.

### The two formulas

The two brightnesses differ only in whether the channels are weighted.

```
# luma.py:34-53 — COMPLETE (the Rec. 709 weights, the naive average, and perceptual luma)
WR, WG, WB = 0.2126, 0.7152, 0.0722


def naive_brightness(rgb):
    """The bug: the unweighted average, (R+G+B)/3. Treats the three primaries as equal."""
    r, g, b = rgb
    return (r + g + b) / 3.0


def luma(rgb):
    """Rec. 709 perceptual luma: green counts most, blue least."""
    r, g, b = rgb
    return WR * r + WG * g + WB * b
```

The naive formula weights every channel by 1/3 ≈ 0.333. Luma weights green by 0.715, red by 0.213, blue by 0.072. Same shape — a weighted sum of the three channels — but the naive weights are a guess (all equal) and the luma weights are a measurement of the eye. Ranking a set of colors by either brightness is the same sort under a different scoring function:

```
# luma.py:57-59 — COMPLETE (order patches brightest-first by a brightness function)
def order_by(patches, f):
    """Patch names sorted brightest-first by a brightness function; ties broken by name."""
    return [p["name"] for p in sorted(patches, key=lambda p: (-f(p["rgb"]), p["name"]))]
```

Compute both on the patches:

```
# $ python3 luma.py --patches
#   name       rgb              naive   luma
#   red        [255, 0, 0]      85.0    54.2
#   green      [0, 255, 0]      85.0    182.4
#   blue       [0, 0, 255]      85.0    18.4
#   yellow     [255, 255, 0]    170.0   236.6
#   cyan       [0, 255, 255]    170.0   200.8
#   magenta    [255, 0, 255]    170.0   72.6
#   brightest-first by naive: ['blue', 'green', 'red']
#   brightest-first by luma:  ['green', 'red', 'blue']
```

run: 2026-08-27 · deterministic; the colors are a fixture · 6 patches · `python3 luma.py --patches`

The first three rows are the whole lesson. Red, green, and blue all show naive 85.0 — the average cannot distinguish the three primaries by brightness at all, because each is a single 255 channel divided by three. Luma pulls them apart to 54.2, 182.4, 18.4: green is by far the brightest, red middling, blue nearly dark, exactly as they look. And the ordering lines say it plainly — the naive order is meaningless (all tied at 85, broken alphabetically to blue, green, red), while luma orders them green > red > blue, the perceptual truth.

<svg viewBox="0 0 700 200" role="img" aria-label="Two bar groups for red, green, blue. Under naive average all three bars are the same height at 85. Under luma the green bar is tall at 182, red medium at 54, blue very short at 18. The average flattens them, luma spreads them.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the three primaries: naive average (all equal) vs perceptual luma</text>
    <line x1="50" y1="170" x2="660" y2="170" stroke="var(--line)"></line>
    <text x="150" y="188" text-anchor="middle" fill="var(--muted)" font-size="8">NAIVE (R+G+B)/3</text>
    <rect x="70" y="128" width="40" height="42" fill="var(--muted)"></rect><text x="90" y="122" text-anchor="middle" fill="var(--muted)" font-size="7">85</text><text x="90" y="182" text-anchor="middle" fill="var(--s2)" font-size="7">red</text>
    <rect x="130" y="128" width="40" height="42" fill="var(--muted)"></rect><text x="150" y="122" text-anchor="middle" fill="var(--muted)" font-size="7">85</text><text x="150" y="182" text-anchor="middle" fill="var(--s1)" font-size="7">grn</text>
    <rect x="190" y="128" width="40" height="42" fill="var(--muted)"></rect><text x="210" y="122" text-anchor="middle" fill="var(--muted)" font-size="7">85</text><text x="210" y="182" text-anchor="middle" fill="var(--muted)" font-size="7">blu</text>
    <text x="500" y="188" text-anchor="middle" fill="var(--muted)" font-size="8">LUMA (Rec. 709)</text>
    <rect x="420" y="143" width="40" height="27" fill="var(--s2)"></rect><text x="440" y="137" text-anchor="middle" fill="var(--s2)" font-size="7">54</text><text x="440" y="182" text-anchor="middle" fill="var(--s2)" font-size="7">red</text>
    <rect x="480" y="79" width="40" height="91" fill="var(--s1)"></rect><text x="500" y="73" text-anchor="middle" fill="var(--s1)" font-size="7">182</text><text x="500" y="182" text-anchor="middle" fill="var(--s1)" font-size="7">grn</text>
    <rect x="540" y="161" width="40" height="9" fill="var(--muted)"></rect><text x="560" y="155" text-anchor="middle" fill="var(--muted)" font-size="7">18</text><text x="560" y="182" text-anchor="middle" fill="var(--muted)" font-size="7">blu</text>
  </g>
</svg>
^ The average gives red, green, and blue the identical height 85 — it literally cannot tell primaries apart. Luma gives green 182, red 54, blue 18, matching how much brighter green looks than blue.

### Grayscale: the contrast the average throws away

A grayscale conversion is exactly this reduction applied per pixel, so the collapse becomes visible as lost contrast. Convert a small red/green/blue/yellow strip both ways:

```
# $ python3 luma.py --gray
#   pixel rgb            naive  luma
#   [255, 0, 0]      85     54
#   [0, 255, 0]      85     182
#   [0, 0, 255]      85     18
#   [255, 255, 0]    170    237
#   naive contrast (max-min): 85    luma contrast: 218
```

run: 2026-08-27 · deterministic · `python3 luma.py --gray`

The contrast reported is the brightness range a formula assigns across the strip — how far apart its brightest and darkest pixels land:

```
# luma.py:62-65 — COMPLETE (contrast is the spread a formula assigns across a set of colors)
def spread(patches, f):
    """The brightness range a formula assigns across a set of patches (max - min)."""
    vals = [f(p["rgb"]) for p in patches]
    return max(vals) - min(vals)
```

Under the average, the red, green, and blue regions are all 85 — three different vivid colors rendered as the same flat gray, with the only contrast in the strip coming from yellow. The total contrast (max minus min) is 85. Under luma the four regions are 54, 182, 18, 237 — all distinct, spanning a contrast of 218, more than two and a half times the average's. The average did not just shift the grays; it erased the differences between colored regions that luma preserves, which is why a logo or chart desaturated with the average can lose entire elements into one gray.

<svg viewBox="0 0 700 170" role="img" aria-label="A four-region strip shown as grayscale two ways. The naive row shows red, green, blue regions all as the same medium gray and yellow lighter. The luma row shows red as dark-medium, green as light, blue as very dark, yellow as lightest — four distinct shades.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">grayscale of a red/green/blue/yellow strip: naive flattens, luma keeps contrast</text>
    <text x="30" y="55" fill="var(--muted)" font-size="8">naive</text>
    <rect x="90" y="34" width="90" height="40" fill="var(--muted)"></rect><rect x="180" y="34" width="90" height="40" fill="var(--muted)"></rect><rect x="270" y="34" width="90" height="40" fill="var(--muted)"></rect><rect x="360" y="34" width="90" height="40" fill="var(--line)"></rect>
    <text x="135" y="90" text-anchor="middle" fill="var(--s2)" font-size="7">85</text><text x="225" y="90" text-anchor="middle" fill="var(--s2)" font-size="7">85</text><text x="315" y="90" text-anchor="middle" fill="var(--s2)" font-size="7">85</text><text x="405" y="90" text-anchor="middle" fill="var(--muted)" font-size="7">170</text>
    <text x="470" y="58" fill="var(--s2)" font-size="8">3 regions identical</text>
    <text x="30" y="130" fill="var(--muted)" font-size="8">luma</text>
    <rect x="90" y="108" width="90" height="40" fill="var(--muted)" opacity="0.4"></rect><rect x="180" y="108" width="90" height="40" fill="var(--s1)"></rect><rect x="270" y="108" width="90" height="40" fill="var(--muted)" opacity="0.15"></rect><rect x="360" y="108" width="90" height="40" fill="var(--acc-soft)"></rect>
    <text x="135" y="164" text-anchor="middle" fill="var(--muted)" font-size="7">54</text><text x="225" y="164" text-anchor="middle" fill="var(--s1)" font-size="7">182</text><text x="315" y="164" text-anchor="middle" fill="var(--muted)" font-size="7">18</text><text x="405" y="164" text-anchor="middle" fill="var(--acc-ink)" font-size="7">237</text>
    <text x="470" y="132" fill="var(--s1)" font-size="8">4 distinct shades</text>
  </g>
</svg>
^ The average renders three different colors as one gray (85), keeping only 85 levels of contrast; luma renders all four regions distinctly across 218 levels. The difference is entire image elements surviving desaturation or vanishing.

**Perceived brightness is a weighted sum of the channels — Rec. 709 luma 0.2126·R + 0.7152·G + 0.0722·B, with green dominant and blue negligible — not the unweighted average, which assigns pure red, green, and blue the identical brightness 85 and collapses a colored image into flat gray, because the eye does not respond equally to the three primaries.**

### The self-test

The `--check` mode plants the bug — the average — and proves it: the average calls the three primaries equally bright, while luma orders them green > red > blue, the weights sum to one, and luma's contrast across the primaries is wide where the average's is zero.

```
# $ python3 luma.py --check
#   naive calls red, green, blue equally bright = True (all 85.0)
#   luma orders green > red > blue = True (182.4 > 54.2 > 18.4)
#   the luma weights sum to 1 = True (1.0000)
#   naive spread across primaries is 0, luma spread is wide = True (0.0 vs 164.0)
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 luma.py --check`

The `weights_sum` line answers the natural objection — that weighting is somehow cheating or unnormalized. The luma coefficients sum to exactly 1, so luma is a proper weighted average: white (255,255,255) still maps to 255, black to 0, and every gray to itself. It is the same kind of average as the naive one, with the one correction that makes it match perception — the weights the eye actually uses.

```
# luma.py:103-108 — COMPLETE (the collapse and the ordering, the two core assertions)
    naive_collapses = naive_brightness(r) == naive_brightness(g) == naive_brightness(b)
    print("  naive calls red, green, blue equally bright = %s (all %.1f)"
          % (naive_collapses, naive_brightness(r)))

    luma_orders = luma(g) > luma(r) > luma(b)
    print("  luma orders green > red > blue = %s (%.1f > %.1f > %.1f)"
          % (luma_orders, luma(g), luma(r), luma(b)))
```

### The running tally

| color | naive | luma | naive rank | luma rank |
|---|---|---|---|---|
| green | 85.0 | 182.4 | tied | 1st (brightest) |
| red | 85.0 | 54.2 | tied | 2nd |
| blue | 85.0 | 18.4 | tied | 3rd (darkest) |
| yellow | 170.0 | 236.6 | — | brightest overall |

Read the naive column against the luma column for the primaries: the average gives one number, 85, for all three, so its rank column is a three-way tie — no information about which is brighter. Luma gives three well-separated numbers and a clear order that matches what you see, green brightest and blue nearly dark. The average is not a slightly-off approximation of luma; on saturated primaries it carries zero of the brightness information, because averaging discards exactly the channel weighting that brightness is made of.

### What we did not settle

This is the weighting, and there are two refinements around it. First, luma should be computed in linear light for physical correctness — the Rec. 709 weights are technically defined on linear RGB, and applying them to gamma-encoded sRGB bytes (as here, and as most code does) is an approximation called luma as distinct from true luminance; the module `media-inter-04` is the linear-light step that makes it exact, and the weighting argument here is identical either way. Second, the coefficients differ slightly by standard — Rec. 601 (0.299, 0.587, 0.114) predates Rec. 709 and is still used for older video — but every one of them weights green far above blue; the specific numbers matter less than never using 1/3, 1/3, 1/3. And "brightness" for accessibility contrast has its own formula built on this same weighted luminance. The invariant: brightness is a green-heavy weighted sum, never the flat average.

## Build

The build in one paragraph: reduce a color to brightness with the perceptual weighted sum — 0.2126·R + 0.7152·G + 0.0722·B (Rec. 709) — never the unweighted average, because the eye is far more sensitive to green than to blue and the average collapses saturated primaries to one indistinguishable value; the weights sum to one, so it stays a proper average that fixes white to white and black to black. Compute it in linear light for physical exactness, pick the coefficient set (601 vs 709) your pipeline expects, and use the same weighted luminance for accessibility contrast.

We opened on the collapse. The number that proves the fix is the brightness spread across the primaries:

```
# modules/generative-media/code/media-inter-07/ — COMPLETE, run from that directory
$ python3 luma.py --check
  naive calls red, green, blue equally bright = True (all 85.0)
  naive spread across primaries is 0, luma spread is wide = True (0.0 vs 164.0)
```

Now build your own. Take a real image with saturated color regions and convert it to grayscale both ways. Your number to beat is not the average brightness; it is **the contrast across colored regions, average versus luma** — the average should flatten your primaries toward one gray while luma keeps them distinct. Confirm your luma orders green above red above blue and its weights sum to 1. Bring back both contrast spans. Good luck.

## Definition of done

- [ ] A naive brightness (unweighted average) and a Rec. 709 luma (weighted sum)
- [ ] Both computed on a set of color patches including the three primaries
- [ ] Confirmation the average maps pure red, green, and blue to the identical value
- [ ] Confirmation luma orders green > red > blue
- [ ] Confirmation the luma weights sum to 1 (a proper average)
- [ ] Confirmation luma's contrast across the primaries is wide where the average's is 0
- [ ] `python3 luma.py --check` printing SELF-TEST PASS: naive_collapses, luma_orders, weights_sum, luma_keeps_contrast
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why is (R+G+B)/3 the wrong way to compute brightness? What does it assume that is false?
2. Give the Rec. 709 luma weights. Which channel dominates, and which is nearly negligible?
3. Why does the average assign pure red, green, and blue the identical brightness, and what is that value?
4. Why does it matter that the luma weights sum to 1?
5. Your own image was desaturated both ways. What was the contrast across colored regions under each, and did luma order green > red > blue?

## External resources

- Charles Poynton, *Frequently Asked Questions about Color* / *Digital Video and HD* — my summary: the definitive explanation of luma, luminance, and why the coefficients are what they are; read it for the distinction between gamma-encoded luma and linear luminance.
- The Rec. 601 and Rec. 709 standards (coefficient tables) — my summary: the two common weight sets and where each applies; read them to pick the right coefficients for your video or image pipeline.
- This hub, *media-inter-04* (blend in linear light) — read it for the linear-light step that makes this weighting physically exact rather than the standard gamma-space approximation.
