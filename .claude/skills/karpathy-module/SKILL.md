---
name: karpathy-module
description: Author, rewrite, or review an AI-Learning-Hub learning module (modules/<topic>/<id>.md) in the hub's verified Karpathy teaching style — complex things spelled out from scratch, one carried micro-example, printed evidence, planted bugs, honest numbers with intervals, and redrawable inline-SVG figures. Use this skill whenever the task touches a hub module in any way — writing a new module, rewriting or improving an existing one, reviewing a module draft, making module content more visual, more fun, simpler, or easier to understand — even if the request never says "Karpathy" or "style". Also use it when adding a new topic's first module or when asked whether a module "follows the style".
---

# Writing a Karpathy-style hub module

The style contract is `docs/karpathy-style.md` — a spec distilled from verbatim transcripts of Karpathy's *Zero to Hero* lectures and his written teaching, with every rule either evidence-tagged or explicitly marked `[hub]` (our own doctrine). This skill is the operating procedure around that spec; the spec always wins on conflict.

## Why this order matters

The style's authority comes from honesty: every printed number is real, every code block runs, every figure is redrawable. That is only possible if the artifact exists and has been run **before** the prose is written. Write prose first and you will invent numbers, then backfill code to match — which is the exact failure the hub's doctrine ("measure or it didn't happen") exists to prevent.

## Procedure

### 1. Load the contract

Read, fully, in this order:
1. `docs/karpathy-style.md` — House constraints, the 20 moves, Voice, Structure template, Visuals, Anti-patterns. Do not write from memory of it.
2. `modules/README.md` — frontmatter, the seven mandatory `## ` sections, absorption rules.
3. `references/checklist.md` (in this skill) — the pass/fail gate you will run at the end.

Pick the module's level (`basic` / `intermediate` / `advanced`) and note its **budget row** from the spec's House constraints: prose words, figure count, code blocks, and which moves are core at that level. The moves are a palette with a mandatory core, not 20 checkboxes — firing everything at every section is Anti-pattern 20 ("Grind") and kills the voice.

### 2. Build and run the artifact first

- The worked example must anchor to a real file in the labs (`Source: faisalmahdy/<repo> — <path>`, de-personalized) — never an invented generic toy (Anti-pattern 21).
- Write the runnable script at a real repo path (convention: `modules/<topic>/code/<module-id>/`), with committed fixtures so it runs without API keys or spend.
- **Run it.** Capture the actual console output to a file. Every number, trace, and error message that will appear in the module comes from this run — including the planted bug's verbatim error text and the wrong-but-plausible numbers.
- Record the run stamp: date, model/version if any, temperature/seed, n. Deterministic scripts still get a stamp (`scorer is deterministic · n=…`).

### 3. Write the module

Follow the spec's Structure template (§4) inside the seven mandatory sections. While drafting, keep these renderer facts in front of you — this renderer is minimal and unforgiving (spec House constraints has the full table):

- One line per paragraph — a soft line-wrap becomes a new `<p>`.
- Headings: `## ` and `### ` only. No `# `, no `#### `, no `---` rules, no `> ` blockquotes, no nested lists, no `<details>`.
- Takeaway lines are a **bolded sentence alone on its own line**.
- Figures: inline `<svg role="img" aria-label="…">` with all strokes/fills from CSS variables (`var(--ink)`, `var(--line)`, `var(--grid)`, `var(--panel)`, `var(--muted)`, `var(--s1)`/`var(--s2)` for series — never literal black or white), followed by a `^ caption` line. Grow figures by accretion; for two-state figures copy the block and edit only `<text>` nodes.
- Code blocks carry filename + `COMPLETE` or `DELTA` in their first comment line, and real output in trailing comments. The one exception: the deliberate `# your turn:` stub.

Voice: write like the spec's Voice table — first-person plural for labor, singular for judgment; blunt verdicts; admitted ignorance; deflation ("literally", "just", a stated size) instead of hype; no staged verbal stumbles; every celebration welded to a printed number.

### 4. Self-check, then build-check

1. Run every item in `references/checklist.md` against your draft. Fix what fails.
2. `python tools/build_site.py --check` must pass.
3. Re-read the draft asking one question per anti-pattern in spec §6: "where does this draft do exactly that?" The most common misses: an unprinted claim (AP7), a term used before its mechanism (AP1), a metric without n/spread (AP14), and grind (AP20).

### 5. What review will hold you to

An adversarial reviewer will check the draft against the spec with the sources open. In particular they will:
- grep the committed script's real output against every number printed in the prose;
- verify the planted bug's error text is verbatim;
- check the surprise prediction actually discriminates (Move 3) and its reconciliation states the size of the surprise;
- check the tally only re-renders when a number moved, and every delta clears its spread before being called anything.

Write as if that review has already happened.
