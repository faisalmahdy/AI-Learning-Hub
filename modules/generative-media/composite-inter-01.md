---
id: composite-inter-01
title: Composite layers in z-order — the "over" operator is not commutative, and an opaque background over a foreground erases it
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Alpha compositing stacks layers with the Porter-Duff "over" operator: placing a top layer over a bottom one gives out_color = (top·α_top + bottom·α_bottom·(1−α_top)) / α_out, with α_out = α_top + α_bottom·(1−α_top). The crucial factor is (1−α_top) — the fraction of the pixel the top leaves uncovered, which is what lets the bottom show through the top's transparency, and also what makes the operator asymmetric: the top contributes at full strength weighted by its own alpha, the bottom only through the hole the top leaves. So "A over B" and "B over A" are different results, and only the one matching the layers' true z-order (which is in front) is correct. Compositing is associative but not commutative — like stacking physical transparencies, the order you lay them down changes what you see. The worst form of the bug is stark: with an opaque background, compositing correctly (foreground over background) mixes the foreground's color in through its alpha, but compositing backwards (the opaque background over the foreground) puts a fully opaque layer on top whose (1−α_top) is zero, so the foreground contributes nothing and disappears — a layer you drew, simply gone, because it was composited under an opaque layer instead of over it. On a fixture of a semi-transparent red foreground and an opaque blue background, foreground-over-background composites to purple with the red visible, while the reversed order yields pure blue with the foreground erased.
eli5: Think of stacking colored plastic sheets on an overhead projector. If you put a see-through red sheet on top of a solid blue one, the light comes out purple — you see both. But if you put the solid blue sheet on top of the red one, the blue blocks everything and you see only blue; the red underneath is completely hidden. The order you stack them matters, and it especially matters when one sheet is solid: whatever is under a solid sheet vanishes. Computers blend transparent layers the same way, so if the layers get stacked in the wrong order, a picture you carefully made can disappear behind a solid layer that was supposed to be in the back.
---

## Why this module

Compositing feels like it should be a symmetric "blend these two layers" operation, and that intuition is exactly what the bug feeds on. The "over" operator is directional: it answers "what do you see when this specific layer is in front of that one," and front-versus-behind is not something you can swap. The math encodes the asymmetry in one term, (1−α_top), which represents how much of the pixel the top layer leaves for the bottom to fill. The top layer never gets that discount — it contributes by its own alpha — while the bottom only ever contributes through the top's leftover transparency.

That asymmetry means the result depends on which layer you designate as the top, i.e. on the z-order. Get the z-order right and the layers stack as intended; get it wrong and you have literally reversed which one is in front. Compositing is associative, so you can combine a tall stack in any grouping and it still works — but it is not commutative, so you cannot reorder the layers, any more than you can shuffle a deck of stacked transparencies without changing the picture.

The consequence is mild when both layers are translucent (you get a wrong-but-visible blend) and catastrophic when the back layer is opaque, because an opaque layer placed on top blocks everything beneath it. This module composites a translucent foreground and an opaque background both ways and shows the foreground vanishing in the wrong order.

**The "over" operator weights the bottom layer by (1−α_top), so it is not commutative — reversing the z-order changes the result, and compositing an opaque background over a foreground zeroes the foreground's contribution and hides it entirely.**

## Concepts

The fixture is a semi-transparent red foreground and an opaque blue background.

```json filename=modules/generative-media/code/composite-inter-01/composite.json:3-4 COMPLETE
  "fg": {"color": [255, 0, 0], "alpha": 0.5},
  "bg": {"color": [0, 0, 255], "alpha": 1.0}
```

The over operator composites a top layer over a bottom one with the Porter-Duff formula. A helper checks whether a layer's color actually shows up in a result — whether the layer is visible in the composite.

```python filename=modules/generative-media/code/composite-inter-01/composite.py:32-43 COMPLETE
def over(top, bottom):
    """Porter-Duff 'over': top composited over bottom. Returns (color, alpha)."""
    tc, ta = top["color"], top["alpha"]
    bc, ba = bottom["color"], bottom["alpha"]
    out_a = ta + ba * (1 - ta)
    out_c = [(tc[i] * ta + bc[i] * ba * (1 - ta)) / out_a for i in range(3)]
    return [round(x, 1) for x in out_c], round(out_a, 2)


def contributes(layer_color, result_color):
    """Does the layer's color show up in the result (any channel it has, the result also has)?"""
    return any(layer_color[i] > 0 and result_color[i] > 0 for i in range(3))
```

The `(1 - ta)` term is the whole asymmetry: it multiplies the bottom layer only. Call `over(fg, bg)` and the background gets `(1 - α_fg)`; call `over(bg, fg)` and the foreground gets `(1 - α_bg)`, which is zero when the background is opaque.

<svg role="img" aria-label="Two stacks: red-over-blue shows a purple result, blue-over-red shows a pure blue result because the opaque blue on top blocks the red" viewBox="0 0 320 120">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">stacking order changes the result</text>
  <text x="14" y="34" font-size="7.5" fill="var(--ink)">red(α.5) over blue(opaque)</text>
  <rect x="20" y="40" width="60" height="14" fill="var(--s2)"/><text x="26" y="51" font-size="7" fill="var(--panel)">red top</text>
  <rect x="20" y="54" width="60" height="14" fill="var(--s1)"/><text x="26" y="65" font-size="7" fill="var(--panel)">blue bot</text>
  <text x="90" y="58" font-size="8" fill="var(--ink)">→ purple (both show)</text>
  <text x="14" y="90" font-size="7.5" fill="var(--ink)">blue(opaque) over red(α.5)</text>
  <rect x="20" y="96" width="60" height="14" fill="var(--s1)"/><text x="26" y="107" font-size="7" fill="var(--panel)">blue top</text>
  <rect x="20" y="110" width="60" height="8" fill="none" stroke="var(--muted)"/>
  <text x="90" y="106" font-size="8" fill="var(--ink)">→ pure blue (red hidden)</text>
</svg>
^ Red over blue lets the red mix through its half-transparency to give purple; blue over red puts the opaque blue on top, and an opaque top layer blocks everything below, so the red is gone. The only difference is which layer was designated the top.

**The (1−α_top) factor multiplies only the bottom layer, so the over operator is directional — and when the top is opaque that factor is zero, giving the bottom layer no way to contribute.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the layer-compositing step of an image renderer, reduced to two layers so every channel is checkable by hand.

Run `--over` to composite both ways.

```text filename=composite.py --over
  fg=[255, 0, 0]@0.5  bg=[0, 0, 255]@1.0
  fg over bg (correct z-order) = color [127.5, 0.0, 127.5] alpha 1.00
  bg over fg (reversed)        = color [0.0, 0.0, 255.0] alpha 1.00
```

Foreground over background gives [127.5, 0, 127.5] — purple, half the red mixed with half the blue, because the background shows through the foreground's 0.5 transparency. Background over foreground gives [0, 0, 255] — pure blue, the original background unchanged, because the opaque background on top left nothing for the red to contribute to. Same two layers, same operator, opposite results; the operator is not commutative.

Now `--order` composites both ways and asks whether the foreground survives.

```python filename=modules/generative-media/code/composite-inter-01/composite.py:63-64 COMPLETE
    correct = over(fg, bg)[0]
    reversed_ = over(bg, fg)[0]
```

Only one order keeps the foreground.

```text filename=composite.py --order
  correct  (fg over bg): [127.5, 0.0, 127.5]  foreground visible = True
  reversed (bg over fg): [0.0, 0.0, 255.0]  foreground visible = False
```

In the correct order the foreground's red is present in the result — it is visible. In the reversed order the foreground is not visible at all; the result is exactly the background color. This is the failure mode that makes wrong compositing order so damaging: it is not a subtle color shift but a whole layer disappearing. A watermark, an overlay, a UI element drawn and then composited under an opaque background instead of over it is simply not in the output, and nothing errors to say so.

<svg role="img" aria-label="Foreground visibility: present as purple in the correct order, absent (pure blue) in the reversed order" viewBox="0 0 320 100">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">is the foreground in the composite?</text>
  <text x="10" y="40" font-size="8.5" fill="var(--s1)">fg over bg</text>
  <rect x="100" y="30" width="70" height="16" fill="var(--s2)"/><text x="110" y="42" font-size="8" fill="var(--panel)">purple</text>
  <text x="178" y="42" font-size="8" fill="var(--ink)">fg visible</text>
  <text x="10" y="70" font-size="8.5" fill="var(--s2)">bg over fg</text>
  <rect x="100" y="60" width="70" height="16" fill="var(--s1)"/><text x="112" y="72" font-size="8" fill="var(--panel)">blue</text>
  <text x="178" y="72" font-size="8" fill="var(--ink)">fg gone</text>
  <text x="10" y="96" font-size="7.5" fill="var(--muted)">wrong order doesn't shift the color — it deletes the layer</text>
</svg>
^ The correct order keeps the foreground (purple result); the reversed order deletes it (pure blue). Wrong compositing order with an opaque back layer is not a color error but a missing layer.

**Foreground over background gives purple with the foreground visible; the reversed order gives pure background with the foreground gone — the operator is not commutative, and an opaque top layer erases everything beneath it.**

## Build

The self-test establishes non-commutativity and the visibility outcomes: the two orders differ, the foreground shows in the correct order, and it is hidden in the reversed one.

```python filename=modules/generative-media/code/composite-inter-01/composite.py:80-87 COMPLETE
    over_not_commutative = correct != reversed_
    print("  fg-over-bg differs from bg-over-fg (over is not commutative) = %s (%s vs %s)" % (over_not_commutative, correct, reversed_))

    fg_visible_correct = contributes(fg["color"], correct)
    print("  in the correct order the foreground shows in the result = %s (%s)" % (fg_visible_correct, correct))

    fg_hidden_reversed = not contributes(fg["color"], reversed_)
    print("  in the reversed order the foreground is hidden = %s (%s)" % (fg_hidden_reversed, reversed_))
```

Then the mechanism: the opaque background over the foreground equals the background alone, while the correct order mixes both layers into a color that is neither pure.

```python filename=modules/generative-media/code/composite-inter-01/composite.py:89-93 COMPLETE
    bg_opaque = bg["alpha"] == 1.0
    reversed_equals_bg = reversed_ == [round(float(c), 1) for c in bg["color"]]
    print("  the opaque background over the foreground equals the background alone = %s (%s)" % (bg_opaque and reversed_equals_bg, reversed_))

    correct_mixes_both = correct != [round(float(c), 1) for c in bg["color"]] and correct != [round(float(c), 1) for c in fg["color"]]
    print("  the correct order mixes both layers (neither pure) = %s (%s)" % (correct_mixes_both, correct))
```

Running the check confirms every clause.

```text filename=composite.py --check
  fg-over-bg differs from bg-over-fg (over is not commutative) = True ([127.5, 0.0, 127.5] vs [0.0, 0.0, 255.0])
  in the correct order the foreground shows in the result = True ([127.5, 0.0, 127.5])
  in the reversed order the foreground is hidden = True ([0.0, 0.0, 255.0])
  the opaque background over the foreground equals the background alone = True ([0.0, 0.0, 255.0])
  the correct order mixes both layers (neither pure) = True ([127.5, 0.0, 127.5])
```

**The check shows the two orders differing, the foreground present only in the correct one, and the reversed result equal to the opaque background alone — the layer erased, not merely recolored.**

## Definition of done

Done means the over operator is shown non-commutative and the reversed order (opaque background on top) is shown to erase the foreground, equal to the background alone, while the correct order mixes both. The clause that the reversed result equals the background exactly is the concrete danger: the bug does not tint the output slightly, it removes a layer, which is why it can slip through review as "the overlay just isn't showing up" rather than being recognized as a compositing-order error.

Two clarifications carry this to real pipelines. First, over is associative but not commutative, and both facts matter: associativity is what lets a renderer flatten a deep layer stack pair by pair (or a group of layers into one) and still get the right answer, so you are free to regroup; non-commutativity is why you must feed those pairs in z-order, back to front (or use front-to-back compositing with the equivalent accumulation). The rule is to keep an explicit z-order for layers and always composite a layer over the accumulated result beneath it, never the other way. Second, compositing order interacts with the other correctness conditions from neighboring modules: the over formula should be evaluated in premultiplied alpha (so transparent pixels' colors do not bleed) and, for physically correct blending, in linear light (so the mix is not too dark) — order, premultiplication, and linear light are three independent things a correct compositor gets right at once. Getting the order wrong is the most visible of the three because it does not degrade the image, it drops content.

<svg role="img" aria-label="Three independent correctness conditions for compositing: correct z-order, premultiplied alpha, and linear light; wrong order drops a layer while the others degrade quality" viewBox="0 0 320 118">
  <rect x="10" y="22" width="98" height="42" fill="none" stroke="var(--s1)"/>
  <text x="17" y="37" font-size="7.5" fill="var(--s1)">z-order</text>
  <text x="17" y="48" font-size="6.5" fill="var(--ink)">over is non-commutative</text>
  <text x="17" y="58" font-size="6.5" fill="var(--ink)">wrong → layer dropped</text>
  <rect x="112" y="22" width="98" height="42" fill="none" stroke="var(--s2)"/>
  <text x="119" y="37" font-size="7.5" fill="var(--s2)">premultiplied α</text>
  <text x="119" y="48" font-size="6.5" fill="var(--ink)">no color bleed at edges</text>
  <rect x="214" y="22" width="96" height="42" fill="none" stroke="var(--ink)"/>
  <text x="221" y="37" font-size="7.5" fill="var(--ink)">linear light</text>
  <text x="221" y="48" font-size="6.5" fill="var(--ink)">blend not too dark</text>
  <text x="10" y="84" font-size="7.5" fill="var(--muted)">associative → regroup freely; non-commutative → keep z-order, composite back-to-front</text>
  <text x="10" y="104" font-size="7.5" fill="var(--ink)">wrong order is the most visible: it deletes content rather than degrading it</text>
</svg>
^ A correct compositor gets three independent things right: z-order (over is non-commutative), premultiplied alpha (no edge color bleed), and linear light (no darkening). Associativity lets you regroup the stack, but non-commutativity means you must composite in z-order, back to front — and wrong order is the most visible failure because it drops content rather than degrading it.

**Done means the reversed order erases the foreground (result equals the opaque background) while the correct order mixes both — so layers are composited in explicit z-order back to front with the over operator, alongside premultiplied alpha and linear light as the other independent correctness conditions.**

## Boss fight

A design tool lets users stack layers, and a user reports that a semi-transparent logo they placed on top of a photo background "disappears" when they export, though it shows fine while editing. The export code flattens the layers by folding them together with the over operator. The blend math is textbook-correct. What is the likely cause, and how do you fix it?

The export is almost certainly compositing the layers in the wrong z-order — folding the background over the logo instead of the logo over the background. Because the over operator is not commutative, "background over logo" is a different result from "logo over background," and when the background is opaque (a photo), putting it on top makes its (1 − α_top) factor zero, so the logo underneath contributes nothing and vanishes — exactly the reported symptom of a layer that shows in the editor (which draws top-to-bottom correctly) but disappears on export (which folds them in the reverse order). The blend math being textbook-correct is consistent with this: the over formula is right; it is being applied with the operands swapped. The fix is to composite in z-order, back to front: start from the bottom layer and, for each layer above it, compute layer-over-accumulated-result, so each higher layer is the top operand of the over. Concretely, iterate the layer list from the bottom up and always pass the current layer as `top` and the accumulated composite as `bottom`, never the reverse. Because over is associative you are free to fold the stack pairwise in that order and get the correct flattened image; you just cannot reverse any pair. To prevent the class of bug, add a test that composites a translucent foreground over an opaque background and asserts the foreground's color appears in the output (the visibility check this module uses), which catches an order inversion immediately. While auditing the compositor, confirm the two neighboring conditions too — that the over is evaluated in premultiplied alpha so edges do not fringe, and ideally in linear light so blends are not darkened — but the disappearing-layer symptom specifically is the z-order inversion.

## External resources

Porter and Duff's "Compositing Digital Images" and its modern treatments (the over operator, the algebra of compositing operators, and the associativity-but-not-commutativity of over) — the source of the formula this module uses and the reason layer order is a correctness property, not a preference.

Documentation on layer compositing in imaging and graphics systems (the back-to-front "painter's" order, premultiplied-alpha compositing, and z-ordering in renderers and design tools) — the practical mechanics of flattening a layer stack in the correct order and the interaction with premultiplication and color space.
