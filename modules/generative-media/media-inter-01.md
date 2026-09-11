---
id: media-inter-01
title: The style anchor — reference one look, don't retype it per scene
topic: generative-media
level: intermediate
status: ready
time: 8-10h
summary: Write the visual style into each shot's prompt by hand and a five-scene storyboard composes into five slightly different looks — five distinct style signatures where there should be one — because each retyped style is paraphrased a little differently. Reference a single Master Visual Anchor from every scene and there is exactly one style across all five, and when the art director changes the palette the anchor reaches all 5 scenes from one edit while the retyped version reaches only 3, silently missing the two shots that spelled the palette a different way.
eli5: If every shot in a film sets up its own lighting by eye, the film looks like five films. Have one lighting setup that every shot points to, and they match — and when you change it, you change it once instead of hunting through every shot and missing some.
---

## Why this module

The first generative-media module made an asset's identity honest; this one makes a storyboard's *look* consistent. A multi-scene image or video prompt has to render as one film — same palette, lens, film stock, mood, across every shot — and the scan points at the exact pattern the labs use for it: a "Master Visual Anchor + Director Style Presets" system that keeps multi-scene generation visually consistent, described as "akin to a manual RAG/context-injection scheme." This module builds the smallest honest version of that anchor and the drift it prevents.

The tempting way to style a storyboard is to write the look into each scene's prompt as you go. It reads fine shot by shot and it fails as a whole, in two compounding ways. First, no two hand-written style clauses are byte-identical — you write "teal and orange grade" in one shot and "teal-and-orange palette" in the next — so the model renders a slightly different look each time and the film drifts. Second, the style is now duplicated across every scene, so when the art director changes the palette you must find and edit every copy, and because the copies are phrased differently, a find-and-replace misses the ones you paraphrased. The fix is a single anchor referenced by every scene: one string, prepended identically, one place to change.

You need no image model — the composed prompt string is the stand-in for the render, where the style clauses either match across scenes or do not. Stdlib Python 3, offline, `$0.00`. The instinct to unlearn is that repeating the style in each prompt is harmless because each prompt reads correctly. Correct-per-shot and consistent-across-shots are different properties, and only the second makes a film.

Here is a storyboard styled both ways:

```
# modules/generative-media/code/media-inter-01/ — COMPLETE, run from that directory
$ python3 anchor.py --consistency

STYLE CONSISTENCY — distinct style signatures across 5 scenes
--------------------------------------------------------------------
  drift     : 5 distinct styles  (looks like 5 different films)
  anchored  : 1 distinct style   (one film)
```

run: 2026-08-25 · deterministic; storyboard is a fixture · 5 scenes · `python3 anchor.py --consistency`

Five hand-typed styles produce five different looks; one referenced anchor produces one. This module is those two numbers and the palette change that turns the difference from cosmetic into a bug.

## Concepts

Named here so you can find them again; each is built below.

- **Master Visual Anchor** — one style string (palette, lens, stock, mood) that defines the film's look.
- **Scene prompt** — a shot's action, composed with a style to make the full prompt.
- **Style drift** — retyping the style per scene, so each shot's look differs slightly.
- **Style signature** — the style clause of a composed prompt; consistency means one signature across scenes.
- **Restyle** — changing the shared look; cheap and complete with an anchor, error-prone when duplicated.
- **Reference vs copy** — pointing every scene at one anchor, versus pasting the style into each.

## Worked example

Source: faisalmahdy/ai-studio's `docs/system-prompts.md` and `director-presets.md` — the Master Visual Anchor and Director Style Presets the scan describes for style-consistent multi-scene generation. This module builds the anchor-versus-drift mechanism those presets exist to enforce.

Script and fixture: `modules/generative-media/code/media-inter-01/` — `anchor.py`, and `storyboard.json`, a five-shot storyboard with one anchor and five hand-typed style clauses. Every command runs from there.

### The frame: one lighting setup, not five eyeballed ones

On a film set the director of photography sets the look — the lens, the stock, the color, the light — and every shot inherits it. Imagine instead that each camera operator eyeballs their own lighting per shot. Every shot looks fine in the monitor, and the assembled film is a patchwork, because "fine" was judged locally and consistency is a global property. Worse, when the director says "warm it up two hundred kelvin," the DP with one setup changes it once; the five operators each have to remember and redo it, and one of them, who set their look a little differently, doesn't get the memo.

A storyboard prompt is that set. The Master Visual Anchor is the DP's one setup; retyping the style per scene is the five operators eyeballing it. The anchor makes consistency structural — every scene literally shares the same string — rather than a matter of the author's discipline. The whole module is making the look a reference, not a copy.

### The two composers

The anchored composer prepends the one anchor to every scene — identical style, everywhere.

```
# anchor.py:43-45 — COMPLETE (reference the one anchor from every scene)
def compose_anchored(anchor, scenes):
    """Reference the one anchor from every scene: identical style prefix everywhere."""
    return [anchor + " | " + s["action"] for s in scenes]
```

The drift composer uses a per-scene style string — what an author produces by retyping the look each time, paraphrasing slightly.

```
# anchor.py:48-51 — COMPLETE (the bug: a retyped, per-scene style)
def compose_drift(scenes, drift_styles):
    """THE BUG: retype the style per scene (each paraphrased differently), so the
    look drifts shot to shot and no two prompts share a style string."""
    return [drift_styles[i] + " | " + s["action"] for i, s in enumerate(scenes)]
```

Look at what each produces:

```
# $ python3 anchor.py --compose
#   DRIFT:
#     35mm film, teal-and-orange, dusk, shallow focus | a fishing boat ...
#     shot on film, teal and orange grade, evening light, bokeh | the captain ...
#     cinematic 35mm, teal-and-orange palette, dusk, wide aperture | gulls ...
#     filmic look, cyan-amber tones, twilight, soft background | a storm ...
#   ANCHORED:
#     35mm film, teal-and-orange, dusk light, shallow depth of field | a fishing boat ...
#     35mm film, teal-and-orange, dusk light, shallow depth of field | the captain ...
```

run: 2026-08-25 · fixture · `python3 anchor.py --compose`

The drift prompts each open differently — "teal-and-orange" becomes "teal and orange grade" becomes "cyan-amber tones" — so the model has a different style instruction per shot. The anchored prompts open with byte-identical style every time. To the author each drift line looked right; assembled, they are four different films.

<svg viewBox="0 0 700 190" role="img" aria-label="Five scenes. In drift, each scene has a different colored style bar. In anchored, all five scenes share the same colored style bar, then their own scene action.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--s2)">drift: a different style per scene</text>
    <g>
      <rect x="20" y="26" width="70" height="12" fill="var(--s2)"></rect><rect x="92" y="26" width="90" height="12" fill="var(--grid)"></rect>
      <rect x="20" y="42" width="84" height="12" fill="var(--s1)"></rect><rect x="106" y="42" width="90" height="12" fill="var(--grid)"></rect>
      <rect x="20" y="58" width="60" height="12" fill="var(--acc)"></rect><rect x="82" y="58" width="90" height="12" fill="var(--grid)"></rect>
      <rect x="20" y="74" width="96" height="12" fill="var(--muted)"></rect><rect x="118" y="74" width="90" height="12" fill="var(--grid)"></rect>
      <rect x="20" y="90" width="76" height="12" fill="var(--ink)"></rect><rect x="98" y="90" width="90" height="12" fill="var(--grid)"></rect>
    </g>
    <text x="380" y="16" fill="var(--s1)">anchored: the same style, every scene</text>
    <g>
      <rect x="380" y="26" width="80" height="12" fill="var(--s1)"></rect><rect x="462" y="26" width="90" height="12" fill="var(--grid)"></rect>
      <rect x="380" y="42" width="80" height="12" fill="var(--s1)"></rect><rect x="462" y="42" width="90" height="12" fill="var(--grid)"></rect>
      <rect x="380" y="58" width="80" height="12" fill="var(--s1)"></rect><rect x="462" y="58" width="90" height="12" fill="var(--grid)"></rect>
      <rect x="380" y="74" width="80" height="12" fill="var(--s1)"></rect><rect x="462" y="74" width="90" height="12" fill="var(--grid)"></rect>
      <rect x="380" y="90" width="80" height="12" fill="var(--s1)"></rect><rect x="462" y="90" width="90" height="12" fill="var(--grid)"></rect>
    </g>
    <text x="20" y="128" fill="var(--muted)">left: five style colors = five looks. right: one style color = one film.</text>
    <text x="20" y="150" fill="var(--muted)">(grey bars are the scene actions, which of course differ; the style must not.)</text>
  </g>
</svg>
^ The colored bar is each scene's style clause. Drift gives five different colors — five looks; the anchor gives one color repeated — one look. Consistency is whether the style column is uniform, and only the reference makes it so.

### Measuring the drift

Consistency is one number: how many distinct style signatures appear across the storyboard.

```
# anchor.py:56-58 — COMPLETE (distinct style signatures; 1 means consistent)
def distinct_styles(prompts):
    """How many different style signatures appear across the storyboard. 1 = consistent."""
    return len({style_of(p) for p in prompts})
```

Drift scores 5, anchored scores 1, as the cold open showed. Five is not "a bit inconsistent" — it is the maximum possible for five scenes, meaning no two shots even agree.

<svg viewBox="0 0 700 120" role="img" aria-label="Distinct style signatures across five scenes. Drift: five distinct styles shown as five different colored blocks. Anchored: one style shown as five identical blocks.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="20" fill="var(--s2)">drift: 5 distinct signatures</text>
    <rect x="220" y="10" width="24" height="16" fill="var(--s2)"></rect><rect x="248" y="10" width="24" height="16" fill="var(--s1)"></rect><rect x="276" y="10" width="24" height="16" fill="var(--acc)"></rect><rect x="304" y="10" width="24" height="16" fill="var(--muted)"></rect><rect x="332" y="10" width="24" height="16" fill="var(--ink)"></rect>
    <text x="370" y="23" fill="var(--s2)">-> 5 films</text>
    <text x="20" y="58" fill="var(--s1)">anchored: 1 distinct signature</text>
    <rect x="220" y="48" width="24" height="16" fill="var(--s1)"></rect><rect x="248" y="48" width="24" height="16" fill="var(--s1)"></rect><rect x="276" y="48" width="24" height="16" fill="var(--s1)"></rect><rect x="304" y="48" width="24" height="16" fill="var(--s1)"></rect><rect x="332" y="48" width="24" height="16" fill="var(--s1)"></rect>
    <text x="370" y="61" fill="var(--s1)">-> 1 film</text>
    <text x="20" y="100" fill="var(--muted)">consistency is one number: distinct style signatures. It must be 1.</text>
  </g>
</svg>
^ The consistency metric in one picture: five colors for the retyped styles, one color repeated for the anchor. The target is always one.

But the consistency problem is the mild half. The expensive half shows up when the look changes.

### The restyle bug: a change that reaches only some scenes

The art director changes the palette. With the anchor, you edit one string and every scene inherits it. With the duplicated styles, you find-and-replace the old palette — and only the scenes that spelled it the canonical way get updated.

```
# anchor.py:66-77 — COMPLETE (restyle by editing each retyped style; misses paraphrases)
def restyle_drift(new_palette, scenes, drift_styles):
    """Change the palette by editing each scene's retyped style. Simulates a human
    find-and-replace that only catches the scenes phrased the expected way."""
    out = []
    for i, s in enumerate(scenes):
        st = drift_styles[i]
        # the art director searches for the old palette word and swaps it -- but only
        # the scenes that spelled it the canonical way get updated.
        if OLD_PALETTE in st:
            st = st.replace(OLD_PALETTE, new_palette)
        out.append(st + " | " + s["action"])
    return out
```

Change the palette to sepia and see who actually gets it:

```
# $ python3 anchor.py --restyle sepia-monochrome
#   anchored: scenes with the new palette = 5/5 [0, 1, 2, 3, 4]
#   drift:    scenes with the new palette = 3/5 [0, 2, 4]
```

run: 2026-08-25 · fixture · `python3 anchor.py --restyle "..."`

The anchor reaches all five scenes from one edit. The drift restyle reaches three — scenes 0, 2, and 4, which spelled the palette "teal-and-orange" — and silently misses scenes 1 and 3, which had paraphrased it as "teal and orange grade" and "cyan-amber tones." The storyboard is now half sepia, half teal-and-orange: a worse, more confusing inconsistency than before the change, and no error announced it. Duplicated knowledge is not just redundant; it drifts out of sync exactly when you edit it.

<svg viewBox="0 0 700 160" role="img" aria-label="After changing the palette to sepia. Anchored: all five scenes show the new sepia palette. Drift: scenes 0, 2, 4 show sepia; scenes 1 and 3 still show the old teal-and-orange, missed by the find-and-replace.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--s1)">anchored after restyle: all sepia</text>
    <g fill="var(--acc)"><rect x="30" y="26" width="26" height="16"></rect><rect x="60" y="26" width="26" height="16"></rect><rect x="90" y="26" width="26" height="16"></rect><rect x="120" y="26" width="26" height="16"></rect><rect x="150" y="26" width="26" height="16"></rect></g>
    <text x="185" y="38" fill="var(--muted)">5/5 updated</text>
    <text x="20" y="76" fill="var(--s2)">drift after restyle: half old, half new</text>
    <g><rect x="30" y="86" width="26" height="16" fill="var(--acc)"></rect><rect x="60" y="86" width="26" height="16" fill="var(--s2)"></rect><rect x="90" y="86" width="26" height="16" fill="var(--acc)"></rect><rect x="120" y="86" width="26" height="16" fill="var(--s2)"></rect><rect x="150" y="86" width="26" height="16" fill="var(--acc)"></rect></g>
    <text x="185" y="98" fill="var(--muted)">3/5 updated; scenes 1 &amp; 3 still on the old palette</text>
    <text x="20" y="138" fill="var(--muted)">one edit reaches all; find-and-replace reaches only the canonical spellings.</text>
  </g>
</svg>
^ After the palette change: the anchor updated every scene, the duplicated style updated only the scenes spelled the expected way. The two shots phrased differently kept the old look, so the film is now internally inconsistent — the drift's failure mode is worst right when you touch it.

**A shared look must be referenced from one place, not retyped per scene: an anchor makes every shot identical and updates them all from one edit, while duplicated style drifts shot to shot and a restyle silently misses the copies you phrased differently.**

The self-test confirms both failures and both fixes:

```
# $ python3 anchor.py --check
#   anchored has exactly one style across all scenes = True
#   drift has more than one style = True (5 distinct)
#   restyle reaches every anchored scene = True (5/5)
#   restyle misses some drift scenes = True (3/5)
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · `python3 anchor.py --check`

### What we did not settle

The fixture treats the composed prompt string as the render, so "consistent" means identical style clauses; a real model can still drift somewhat on identical prompts (sampling), and can hold style reasonably across mild paraphrase, so the effect is a strong tendency, not the hard guarantee the string comparison suggests. Two real extensions: a subject anchor (a recurring character described identically) matters as much as the visual style and drifts the same way when retyped; and Director Style Presets are anchors you switch between — a library of looks referenced by name — which only works if each preset is defined once and referenced, the same discipline one level up. The dial here is one visual anchor over five scenes; the pattern is single-source styling across a whole production.

## Build

The pipeline in one paragraph: define the film's look once as a Master Visual Anchor — palette, lens, stock, mood — and compose every scene prompt by referencing that one string, never by retyping the style; measure consistency as the number of distinct style signatures across scenes (it must be one); and confirm that changing the look edits exactly one place and reaches every scene. Never paste the style into each prompt.

We opened on the consistency counts. The composition that holds:

```
# modules/generative-media/code/media-inter-01/ — COMPLETE, run from that directory
$ python3 anchor.py --consistency
  anchored  : 1 distinct style   (one film)
```

Now anchor your own storyboard. Take a multi-scene prompt set, factor the shared style into one anchor, and compose each scene by reference. Your number to beat is **one distinct style signature** across all scenes, and your stress test is a restyle: change the anchor once and confirm every scene picks it up. Build the drift version too, and confirm a find-and-replace on the palette misses the scenes you paraphrased. Bring back the distinct-style counts and the restyle coverage for both. Good luck.

## Definition of done

- [ ] A single Master Visual Anchor string defining the shared look
- [ ] Scene prompts composed by referencing the anchor, not retyping the style
- [ ] A consistency metric: the number of distinct style signatures across scenes (target 1)
- [ ] A restyle that edits the anchor once and reaches every scene
- [ ] The drift (retyped-per-scene) version kept for contrast, so the inconsistency and missed restyle are visible
- [ ] `python3 anchor.py --check` printing SELF-TEST PASS: anchored consistent, drift varies, restyle reaches all anchored, misses some drift
- [ ] The distinct-style counts and restyle coverage recorded for both approaches
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Five hand-typed style clauses each read correctly, yet the storyboard is inconsistent. Explain how correct-per-shot and consistent-across-shots differ.
2. Why does referencing one anchor make consistency structural rather than a matter of author discipline?
3. A palette change reached only 3 of 5 drift scenes. State the mechanism and which scenes were missed.
4. Why is duplicated style "worst right when you touch it" — that is, why does a restyle make a drifted storyboard more inconsistent, not less?
5. Your own storyboard was anchored and restyled. How many distinct styles before and after, and did every scene pick up the change?

## External resources

- faisalmahdy/ai-studio — `docs/system-prompts.md` and `director-presets.md` — my summary: the Master Visual Anchor and Director Style Presets this module distills; read them for the real preset library and how a named anchor is referenced across a production.
- Anthropic, *Prompt engineering — system prompts and consistency* — https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/system-prompts — my summary: putting stable, shared instructions in one system prompt rather than repeating them per turn; read it for the same single-source discipline applied to text generation, the sibling of this module's visual anchor.
- This hub, *ship-basic-01* — modules/ship-and-operate/ship-basic-01.md — my summary: a generated file as a pure function of one source, and the drift when it is edited in two places; read it for the same reference-not-copy principle in a different domain — the anchor is to a storyboard what the single source is to a generated file.
