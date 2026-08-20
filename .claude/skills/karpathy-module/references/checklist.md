# Pass/fail gate for a Karpathy-style hub module

Run every line. A "no" on any line means the draft is not done. Line numbers in brackets refer to moves/sections in `docs/karpathy-style.md`.

## Renderer-legal (hard build facts)

- [ ] Only `## ` and `### ` headings; no `# `, `#### `, `---`, `> `, nested lists, or raw HTML other than `<svg>`.
- [ ] Every paragraph is a single unwrapped line.
- [ ] All seven mandatory sections present, in order: Why this module / Concepts / Worked example / Build / Definition of done / Boss fight / External resources.
- [ ] Frontmatter complete: id, title, topic, level, status, time, summary.
- [ ] `python tools/build_site.py --check` passes.

## Honesty (hub doctrine — these are the ones that get modules rejected)

- [ ] Every number in the prose appears in the committed script's actual output (or is arithmetic the reader watches happen). No invented numbers anywhere, including in figures.
- [ ] The script path is stated, the one command that reproduces the numbers is printed, fixtures are committed, and it runs without API keys.
- [ ] Every model-derived or measured output carries a run stamp (date · model/seed or "deterministic" · n).
- [ ] Every headline metric ships n and a spread over ≥3 runs, or an explicit "n too small, raw spread is…" [Move 18]. No delta called an improvement or failure unless it clears the spread.
- [ ] Every headline metric's first appearance carries its bracket: chance level (arithmetic shown), floor/ceiling, real-world counterpart [Move 14].
- [ ] The absorbed artifact carries `Source: faisalmahdy/<repo> — <path>` and is de-personalized; the micro-example comes from a real lab system [Move 19, AP21].

## The core moves (all levels)

- [ ] Cold open: contract paragraph, then the finished artifact run with real pasted output and the payoff labeled as a preview; payoff reappears at the end "(again)" [Move 1]. The payoff is something worth showing someone — not a bare score.
- [ ] Contract: 3–5 sentences — contents, omissions with reasons, prereq bar in casual register, hardest-part flag, runtime + cost + sitting length [Move 2]. No learning-objectives box anywhere [AP10].
- [ ] At least one prediction ask before a number lands, and at least one genuinely surprising one, with the expected wrong answer stated and the surprise sized at reconciliation [Move 3]. Answer hidden by a text-native device (next-section answer / interposed figure / checkbox list), never `<details>`.
- [ ] Every term: mechanism first → "this is called **X**" → one-sentence deflation. No term before its thing [Move 4, AP1]. Formulas get a "reading the symbols" paragraph.
- [ ] Ugly first: manual pass until the tedium is felt, then Strategy #1/#2/#3 ladder, each run + conceded + killed by a named adversarial case with a quantified limit [Move 6].
- [ ] One micro-example carried unchanged through the whole module, full intermediate state printed, scalar-level loops before any vectorization, altitude named in headers [Move 7, AP13].
- [ ] Printed evidence twice: results as trailing comments, raw traces verbatim, every derived quantity cross-checked by a dumber route or mainstream library with both numbers printed [Move 8, AP7].
- [ ] Boundaries fenced inline at the moment they occur, with reasons; magic numbers confessed; a "what we did not settle" close [Move 12, AP15].
- [ ] Module close: pipeline restated in one paragraph → promise discharged against the cold open → FAQ (naive + philosophical + "why is mine slow") → hand-off to the reader's own system with one primary dial and a number to beat, ending on a send-off [Moves 15, 20, AP17, AP18].
- [ ] Boss fight: 5 closed-book questions, ≥1 requiring the reader's own run's number [Move 17].

## Level-gated moves

- [ ] intermediate+: planted bug with verbatim error/wrong number, hard stop, autopsy, minimal reproducer, diff fix, "why it still seemed to work", named bug class [Move 9] — and running tally in prose or a table re-rendered only when a number moved, failures kept in, each section ending on the "and yet" cliffhanger [Move 13].
- [ ] intermediate+: takeaway lines — at most one per major section, only if quotable standalone and true [Move 16].
- [ ] advanced: break-it-on-purpose knob sweep with ≥1 bad value, spread per swept value, symptom table [Move 10]; null results kept with their real cause [Move 12].
- [ ] basic: none of the above faked — a basic module reproduces a worked example and has no original null results.

## Figures

- [ ] Within the level's figure budget; at least one figure a learner could redraw from memory (it is boss-fight material).
- [ ] Each figure fires at one of the spec's ten mandatory moments (§5) — no decorative diagrams [AP16].
- [ ] Two-state figures use identical coordinates; every figure has a "how to read this" line naming the failure signature, a threshold badge where diagnostic, `role="img"` + `aria-label`, a `^ caption`, and only CSS-variable colors.

## Voice spot-checks

- [ ] No hype adjectives; every exclamation welded to a printed number [AP8].
- [ ] No "as we know / obviously / trivially"; no unrestated back-references; no pronouns crossing section boundaries [AP11].
- [ ] One substrate metaphor, numbers carried inside it, bridge sentence back to the mechanism, standard terms in code/identifiers [Move 5, AP12].
- [ ] No staged "oops" stumbles; wrong results and dead ends stay in [Voice table].
- [ ] Word count inside the level's budget; no closer-stacking (one "and yet" + at most one recap device per section) [AP20].
