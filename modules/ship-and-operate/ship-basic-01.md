---
id: ship-basic-01
title: Rebuild-then-diff — a generated file you can't reproduce is one CI can't guard
topic: ship-and-operate
level: basic
status: ready
time: 6-8h
summary: A generated file is only trustworthy if rebuilding it from source gives the same bytes, and a generator that stamps the build time into its output fails that check on every run — two builds seconds apart differ at the timestamp line — so teams switch the gate off and a hand-edit to the generated file then sails through undetected. Drop the timestamp and sort the output and the rebuild is byte-identical across any clock, so rebuild-then-diff catches the hand-edit at line 3, the drift a live gate exists to stop.
eli5: If re-printing a document from its source gives a different page every time, you can never tell a real change from printing noise — so make the output depend only on the source, and then any difference means someone edited the copy instead of the original.
---

## Why this module

This opens the ship-and-operate track — the move from "run these in two terminals" to something that runs unattended — and it starts with the smallest, most-skipped piece of operational hygiene: making a generated file reproducible. Repos are full of files that are built from source: an index, a lockfile, a rendered doc, a compiled schema. The rule that keeps them honest is a CI gate you have already met in this hub — `python tools/build_site.py --check` is one — usually phrased "rebuild the artifact, then `git diff --exit-code`." If the rebuild matches what is committed, the file is honest; if it differs, something is wrong.

The gate only works if the generator is deterministic, and the most common way to break that is the most innocent-looking: stamping the build time into the output. Now every rebuild differs from the last at the timestamp line, so the gate fails on every commit for no real change. Faced with a gate that cries wolf every push, teams do the rational thing and turn it off — and the moment they do, the gate's real job goes unguarded, so when someone hand-edits the generated file instead of its source, nothing catches it. A flaky gate is not a weak gate; it is a disabled gate.

You need nothing but Python 3 and the standard library. Everything runs offline against a small source fixture, `$0.00`, one sitting. The instinct to unlearn is that a generated file's contents are self-evidently correct because a script wrote them. A script wrote them *this time*; the question a gate answers is whether the script would write them the *same* way again.

Here is the reproducibility check on the two generators:

```
# modules/ship-and-operate/code/ship-basic-01/ — COMPLETE, run from that directory
$ python3 gen.py --repro

REPRODUCIBILITY — build twice at different clock times, compare bytes
------------------------------------------------------------
  timestamped (bug)      two builds identical = False
      first difference at line 2: '# built at 1000' vs '# built at 2000'
  deterministic (fix)    two builds identical = True
```

run: 2026-08-25 · deterministic; the clock is passed in to simulate two CI runs · source is a fixture · `python3 gen.py --repro`

Two builds of the same source, seconds apart. The timestamped generator produces different bytes — the timestamp line — so a gate on it fails every time. The deterministic generator produces identical bytes, so the gate is meaningful. This module is the difference between those two lines and why the second is the only one you can build a gate on.

## Concepts

Named here so you can find them again; each is built below.

- **Generated artifact** — a committed file produced from source by a script (an index, a lockfile, a rendered doc).
- **Reproducible build** — rebuilding from the same source yields byte-identical output.
- **The rebuild-then-diff gate** — CI rebuilds the artifact and fails if it differs from what is committed.
- **Non-determinism** — output that varies run to run (a timestamp, a random order); what breaks reproducibility.
- **Drift** — a committed artifact that no longer matches what its source would generate; usually a hand-edit.
- **The flaky-gate trap** — a gate that fails on noise gets disabled, and then misses the real thing.

## Worked example

Source: faisalmahdy/arena-ai, whose CI is a "rebuild-then-diff" gate (regenerate the artifact, then `git diff --exit-code`), and the hub's own `tools/build_site.py --check`. This module builds the smallest honest version of that gate and the bug that defeats it.

Script and fixture: `modules/ship-and-operate/code/ship-basic-01/` — `gen.py`, and `source.json`, a list of items and the committed version of the file generated from them. Every command runs from there.

### The frame: a receipt stamped with the time

Imagine verifying a receipt by re-printing it from the order and checking the two match. If the receipt prints the current time at the top, the reprint never matches the original — not because the order changed, but because the clock did. You cannot use "does the reprint match" to detect a forged receipt, because it never matches anyway. The only way the check works is if the receipt is a pure function of the order: same order, same receipt, every time. Then any mismatch means the receipt was tampered with.

A generated file is that receipt. If its contents depend only on its source, rebuilding is a verification: a match means honest, a mismatch means drift. If its contents also depend on the clock — or on anything else that changes run to run — the rebuild is worthless as a check, and worse, its constant false alarms train everyone to ignore it. The whole module is making the output a pure function of the source.

### The generator, two ways

The generator renders the source list into an index. The deterministic path sorts the items and stamps nothing; the buggy path stamps the build time.

```
# gen.py:37-46 — COMPLETE (deterministic vs timestamped render)
def build(items, deterministic, now=0):
    """Render the index. Deterministic: sort the items, no timestamp -- same source,
    same bytes. Non-deterministic: stamp the build time, so every run differs."""
    lines = ["# generated index"]
    if not deterministic:
        lines.append("# built at %d" % now)          # <- the reproducibility killer
    order = sorted(items) if deterministic else items
    for name in order:
        lines.append("- %s" % name)
    return "\n".join(lines) + "\n"
```

Two things differ between the paths, and both matter. The timestamp is obvious non-determinism. The sort is the subtle one: without it, the output order follows the source's listing order, so a harmless reordering of the source produces a different artifact and a spurious diff. Determinism means the output depends on the source's *content*, not its *arrangement* or the *clock*.

```
# $ python3 gen.py --build
#   deterministic:                timestamped (now=1000):
#     # generated index             # generated index
#     - bills                       # built at 1000
#     - coffee                      - gym
#     - dentist                     - coffee
#     - flights                     - flights
#     - gym                         - bills ...
```

run: 2026-08-25 · fixture · `python3 gen.py --build`

The deterministic build is sorted and timeless; the timestamped one carries a line that changes with the clock and leaves the items in source order.

### Reproducibility is the whole gate

The check is four lines: build the same source twice — here at two different clock times, standing in for two CI runs — and compare the bytes.

```
# gen.py:51-56 — COMPLETE (the heart of the gate: build twice, compare)
def reproducible(items, deterministic):
    """The heart of the gate: build the same source twice (here, at two clock
    times) and check the bytes are identical."""
    a = build(items, deterministic, now=1000)
    b = build(items, deterministic, now=2000)
    return a == b, a, b
```

The timestamped build fails this — the two runs differ at the timestamp line — and the deterministic build passes at any clock. That is the cold-open result, and it is the entire argument: only the reproducible artifact can be gated.

<svg viewBox="0 0 700 180" role="img" aria-label="Two builds of the same source at now=1000 and now=2000. The timestamped versions differ at the 'built at' line. The deterministic versions are byte-identical.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--s2)">timestamped: two runs differ</text>
    <g transform="translate(20,28)">
      <rect x="0" y="0" width="150" height="70" fill="none" stroke="var(--line)"></rect>
      <text x="8" y="16" fill="var(--muted)"># index</text><text x="8" y="30" fill="var(--s2)"># built at 1000</text><text x="8" y="44" fill="var(--muted)">- gym ...</text>
      <rect x="180" y="0" width="150" height="70" fill="none" stroke="var(--line)"></rect>
      <text x="188" y="16" fill="var(--muted)"># index</text><text x="188" y="30" fill="var(--s2)"># built at 2000</text><text x="188" y="44" fill="var(--muted)">- gym ...</text>
      <text x="120" y="40" fill="var(--s2)" font-size="14">≠</text>
    </g>
    <text x="380" y="18" fill="var(--s1)">deterministic: two runs identical</text>
    <g transform="translate(380,28)">
      <rect x="0" y="0" width="140" height="70" fill="none" stroke="var(--line)"></rect>
      <text x="8" y="16" fill="var(--muted)"># index</text><text x="8" y="30" fill="var(--muted)">- bills</text><text x="8" y="44" fill="var(--muted)">- coffee ...</text>
      <rect x="170" y="0" width="140" height="70" fill="none" stroke="var(--line)"></rect>
      <text x="178" y="16" fill="var(--muted)"># index</text><text x="178" y="30" fill="var(--muted)">- bills</text><text x="178" y="44" fill="var(--muted)">- coffee ...</text>
      <text x="150" y="40" fill="var(--s1)" font-size="14">=</text>
    </g>
    <text x="20" y="130" fill="var(--muted)">a gate compares the rebuild to what is committed; it only means something</text>
    <text x="20" y="146" fill="var(--muted)">when the rebuild is stable — the left pair can never pass, the right always can.</text>
  </g>
</svg>
^ Same source, two runs. The timestamped build differs at the "built at" line every time; the deterministic build is byte-identical. Only the right-hand artifact can be guarded by a rebuild-then-diff gate.

### What the gate catches once it works

With a deterministic generator, the gate does its real job: compare the rebuild to the committed file and flag any drift. The comparison finds the first differing line.

```
# gen.py:59-67 — COMPLETE (first differing line between rebuild and committed)
def diff(expected, actual):
    """Return the first differing line pair, or None if identical."""
    e, a = expected.splitlines(), actual.splitlines()
    for i in range(max(len(e), len(a))):
        le = e[i] if i < len(e) else "(missing)"
        la = a[i] if i < len(a) else "(missing)"
        if le != la:
            return i + 1, le, la
    return None
```

The committed fixture was hand-edited — someone changed the generated file directly instead of the source — and the gate catches it:

```
# $ python3 gen.py --drift
#   MISMATCH at line 3:
#     rebuild   : '- coffee'
#     committed : '- coffee (hand edited)'
#   the committed file was hand-edited; the gate rejects it.
```

run: 2026-08-25 · fixture · `python3 gen.py --drift`

That is the drift a live gate exists to stop: a change that lives only in the generated file, which the next legitimate rebuild would silently erase. The gate turns "the generated file and its source have quietly diverged" into a loud CI failure at line 3. But it can only do that because the rebuild is reproducible — on the timestamped generator, this signal is buried under a false alarm on every run.

<svg viewBox="0 0 700 150" role="img" aria-label="The gate flow: source feeds a rebuild; the rebuild is compared to the committed file; identical passes, different fails. A timestamp inserted into the rebuild makes every comparison fail, so the gate is disabled and drift passes.">
  <g font-family="var(--mono)" font-size="10">
    <rect x="20" y="50" width="80" height="30" rx="5" fill="var(--panel)" stroke="var(--line)"></rect><text x="60" y="69" text-anchor="middle" fill="var(--ink)">source</text>
    <rect x="140" y="50" width="90" height="30" rx="5" fill="var(--panel)" stroke="var(--line)"></rect><text x="185" y="69" text-anchor="middle" fill="var(--ink)">rebuild</text>
    <rect x="270" y="46" width="90" height="38" rx="5" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="315" y="61" text-anchor="middle" fill="var(--acc-ink)">diff vs</text><text x="315" y="75" text-anchor="middle" fill="var(--acc-ink)">committed</text>
    <line x1="100" y1="65" x2="138" y2="65" stroke="var(--muted)"></line><line x1="230" y1="65" x2="268" y2="65" stroke="var(--muted)"></line>
    <rect x="400" y="24" width="120" height="26" rx="5" fill="var(--panel)" stroke="var(--s1)"></rect><text x="460" y="41" text-anchor="middle" fill="var(--s1)">match -> pass</text>
    <rect x="400" y="80" width="120" height="26" rx="5" fill="var(--panel)" stroke="var(--s2)"></rect><text x="460" y="97" text-anchor="middle" fill="var(--s2)">differ -> fail</text>
    <line x1="360" y1="58" x2="398" y2="40" stroke="var(--s1)"></line><line x1="360" y1="72" x2="398" y2="92" stroke="var(--s2)"></line>
    <text x="140" y="120" fill="var(--s2)" font-size="8">a timestamp in the rebuild forces 'differ' on every run -> gate gets disabled -> drift passes</text>
  </g>
</svg>
^ The gate: rebuild from source, diff against the committed file, fail on a difference. It catches real drift only if a clean rebuild reliably matches — a timestamp forces failure on every run, and the disabled gate then lets the hand-edit through.

**A generated file must be a pure function of its source: make the rebuild byte-reproducible, or the gate that guards it fails on noise, gets turned off, and stops guarding anything.**

The self-test confirms both halves — the bug and the fix:

```
# $ python3 gen.py --check
#   timestamped build reproducible = False   deterministic build reproducible = True
#   deterministic build ignores the clock = True
#   rebuild-vs-committed catches the hand-edit = True (line 3)
#   deterministic build is independent of source order = True
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · `python3 gen.py --check`

## Build

The pipeline in one paragraph: make every generated artifact a pure function of its source — sort collections, drop timestamps and random ids, pin any ordering — so rebuilding yields identical bytes; commit the generated file; and in CI, rebuild it and `git diff --exit-code` so any drift or non-determinism fails the build. Never commit a generated file whose rebuild you have not confirmed is byte-stable, and never edit a generated file by hand.

We opened on reproducibility. The line the gate depends on:

```
# modules/ship-and-operate/code/ship-basic-01/ — COMPLETE, run from that directory
$ python3 gen.py --repro
  deterministic (fix)    two builds identical = True
```

Now gate your own generated files. Take a file your repo builds from source, rebuild it twice, and diff the two rebuilds — any difference is non-determinism to hunt down (a timestamp, an unsorted set, a dict order, an absolute path). Your number to beat is **zero bytes of difference between two rebuilds**; until you hit it, a rebuild-then-diff gate will be flaky and worthless. Then hand-edit the committed file and confirm the gate catches the drift. Bring back the two-rebuild diff (empty) and the caught hand-edit. Good luck.

## Definition of done

- [ ] A generator whose output is a pure function of its source: sorted, no timestamps, no random ids
- [ ] Two rebuilds of the same source confirmed byte-identical
- [ ] A rebuild-then-diff check that fails on any difference from the committed artifact
- [ ] Your own `source.json` (or real source) with a committed artifact, including a hand-edited version to catch
- [ ] The non-deterministic variant kept for contrast, so the flaky-gate trap is visible
- [ ] `python3 gen.py --check` printing SELF-TEST PASS: timestamped not reproducible, deterministic reproducible, drift caught, order-independent
- [ ] The empty two-rebuild diff recorded, and the caught hand-edit
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. A rebuild-then-diff gate fails on every commit for no real change, so the team disables it. Name the likely cause and the worse thing that happens next.
2. Why does sorting the output matter for reproducibility, separately from removing the timestamp?
3. State what "a generated file is a pure function of its source" means, and the one comparison that verifies it.
4. The gate caught a mismatch at line 3 between the rebuild and the committed file. What does that mismatch mean, and what would erase the committed change if left alone?
5. Your own generator's two rebuilds differed. What was the source of non-determinism, and how did you remove it?

## External resources

- faisalmahdy/arena-ai — the rebuild-then-diff CI gate — my summary: regenerates artifacts and fails on `git diff`, plus seeded RNG so screenshots reproduce; read it for a real generate-then-prove pipeline and for the determinism disciplines (seeds, sorted output) this module distills.
- Reproducible Builds project — https://reproducible-builds.org/ — my summary: the industry effort to make software builds bit-for-bit reproducible, and its catalog of non-determinism sources (timestamps, file order, locale, paths); read it for the full list of things that break the gate this module builds.
- This hub, `tools/build_site.py` (the `--check` gate) — my summary: the hub's own rebuild-then-check gate that every module in this repo passes; read it as a working example of the pattern, and note it is exactly the discipline this module teaches, applied to the hub itself.
