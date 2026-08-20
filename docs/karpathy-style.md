# SPEC — Karpathy-Style Writing for AI-Learning-Hub Modules

> **How this was made (2026-08-20).** A 10-agent research workflow distilled this spec from primary sources: full Whisper transcripts of *Neural Networks: Zero to Hero* episodes 1–4 ([karcaps](https://averkij.github.io/karcaps/)), Karpathy's written corpus (Hacker's Guide `nntutorial.md`, the 2019 *Recipe*, the 2026 microGPT post, course READMEs), and his public statements on education (Eureka Labs, LLM101n). Four transcript analysts + a written-corpus analyst + a web researcher fed a synthesizer; an evidence critic then grep-verified every quote against the sources (killing three fabrications) and a translation critic audited every rule for video→text transfer; a reviser resolved both reports. The moves in §2 are enforced by the `karpathy-module` skill (`.claude/skills/karpathy-module/`).

**Scope.** How to write a learning module as markdown + inline SVG **that renders in this hub and passes `tools/build_site.py --check`**. Every style rule is traced to verbatim evidence from the source corpus. Every rule that is *ours* rather than his is tagged `[hub]` and says so — the previous draft of this spec dressed several house preferences as observed Karpathy practice, and that is now forbidden.

**Source key.**

| Tag | What it covers | Verification |
|---|---|---|
| `[ep1]` | micrograd lecture transcript (`001.txt`) | local ✓ |
| `[ep2]` | makemore lecture transcript (`002.txt`) | local ✓ |
| `[ep3]` | MLP lecture transcript (`003.txt`) | local ✓ |
| `[ep4]` | activations/batchnorm lecture transcript (`004.txt`) | local ✓ |
| `[written]` | `nntutorial.md` (Hacker's Guide); `_posts/2019-04-25-recipe.markdown`; `_posts/2026-02-12-microgpt.markdown`; `_posts/2021-06-21-blockchain.markdown`; `nn-zero-to-hero/README.md`; micrograd `README.md` | local ✓ |
| `[written†]` | nanoGPT `README.md` | web only — **not** in the local audit set |
| `[public]` | public statements: the Eureka Labs launch post, tweets | web only — **not** locally auditable |
| `[hub]` | this hub's own doctrine (`README.md`, `modules/README.md`, `CURRICULUM.md`, `docs/asset-pipeline.md`). Not Karpathy-observed. | local ✓ |

Any quote carrying `[written†]` or `[public]` could not be checked against a local file. Do not add new quotes at those tiers without a URL in the commit message.

**Quote convention.** All text inside quotation marks is verbatim. `…` marks **omitted words only**. Joining two adjacent transcript lines is *not* an omission and takes no mark — the previous convention allowed `…` for line-joins, which made a real elision indistinguishable from a cosmetic one. Lowercase, typos, and repetitions inside quotes are his. A templated sentence with placeholders is **not** a quote and never takes quotation marks.

---

**House constraints.** `[hub]` These are not style; a module that ignores them does not build. Read this block before writing a line.

**Frontmatter is mandatory.** `tools/build_site.py --check` hard-fails on any missing key (`REQUIRED` at `build_site.py:25`).

```
---
id: evals-basic-01
title: Your first output-quality eval — a mechanized rubric
topic: evals-and-statistics
level: basic
status: ready
time: 6-8h
summary: One-sentence card text for the explorer.
---
```

`title` carries the promise — that is Move 1's job, done in frontmatter, not in a prose `# ` heading. `summary` is the explorer-card sentence and has no Karpathy analogue; write it last, as the one line you would say to someone deciding whether to open this. `time` is **learner-hours at 8–12 h/week** — a different number from the code runtime and from the reading sitting that Move 2 asks for. Never conflate the three.

**What the renderer actually supports.** Verified by executing `md_to_html` against each construct:

| Renders | Does **not** render |
|---|---|
| `## `, `### ` | `# `, `#### ` (emit a literal paragraph) |
| fenced code blocks | `> ` blockquote (emits a literal `>`) |
| flat `-`/`*` lists, `1.` lists | nested lists (silently flattened) |
| `- [ ]` / `- [x]` checkbox lists | raw HTML other than `<svg>` — `<details>` is **escaped and its answer shown in plain sight** |
| pipe tables with a `---` separator row | `---` horizontal rules |
| `![alt](file.png "caption")` | soft-wrapped paragraphs — **every line becomes its own `<p>`** |
| inline `<svg>` … `</svg>` + a `^ caption` line | |

So: **one line per paragraph, no line wrapping.** No `#`, no `####`, no `---`, no nesting, no `<details>`.

Two devices in the older draft of this spec were unrenderable and have been re-specified: the takeaway blockquote (Move 16) is now a bolded standalone line; the hidden answer (Move 3) now uses a text-native device. If someone later adds a `>` → `<blockquote>` branch and a `#### ` → `<h5>` branch to `md_to_html` (about three lines each, alongside the existing `## `/`### ` cases), switch Move 16 back to `>` and revisit the Recipe variant's `####` headings — until then, do not write them.

**Section schema.** The hub mandates seven `## ` sections in fixed order (`modules/README.md`). Karpathy's flow nests *inside* them; it does not replace them.

| Hub section | What goes in it | Moves |
|---|---|---|
| `## Why this module` | the gap with evidence, then the contract paragraph, then the cold open and its payoff preview | 1, 2 |
| `## Concepts` | terse, written **last**, each entry ≤2 lines naming the mechanism in plain words + where it is built | 4 (naming beat only) |
| `## Worked example` | the body: substrate, ladder, micro-example, printed evidence, planted bug, sweep, scoreboard, brackets | 3–14, 16, 18 |
| `## Build` | the learner points the artifact at **their own** system; hand-off, FAQ, errata, what-we-did-not-settle | 12, 15, 20 |
| `## Definition of done` | checklist written before starting, incl. run stamp and committed script | 8, 18 |
| `## Boss fight` | closed-book recall; passing writes a dated ledger entry | 17 |
| `## External resources` | links + own summaries only | 19 |

Two reconciliations follow from this table, and both override the older draft:

- `## Why this module` is required and Anti-pattern 10 used to ban "why this matters" preambles outright. The ban is now narrower: **no learning-objective bullet boxes, and no motivational preamble** — `Why this module` states a gap and cites evidence for it, which is what `evals-basic-01` already does.
- `## Concepts` is required and Move 4 bans terms-before-mechanism. Resolution: Concepts is a **map, not a lesson**. Open it with one line — *these are named here so you can find them again; each is built below* — then one terse entry per term pointing forward. The explanation still happens only after the mechanism runs.

**Size budget and move profiles.** The 16 style moves are a **palette with a mandatory core**, not 16 checkboxes. The reference module `evals-basic-01` is 909 prose words, 3 SVGs, 0 code blocks; a module that fired every move at every section would run 8,000–15,000 words and be unreadable and unwritable.

| Level | Prose words | Figures | Code blocks | Moves |
|---|---|---|---|---|
| basic | 1,200–2,000 | 2–4 | 4–8 | core: 1, 2, 3, 4, 6, 7, 8, 12, 14, 15, 17, 18, 19, 20 |
| intermediate | 2,000–3,500 | 3–6 | 8–15 | core + 5, 9, 11, 13, 16 |
| advanced | 3,500–6,000 | 4–8 | 12–25 | all, incl. 10 and the null-results half of 12 |

A `basic` module reproduces an existing worked example, so it has no original null results and no failed-experiment scoreboard of its own. Do not fake them.

**Code protocol.** Text has no live editor, so cumulative code state is invisible unless we legislate it.

- Every code block carries its filename and is labelled **COMPLETE** (runnable exactly as shown) or **DELTA** (a diff against a named file).
- Imports appear once, in the first COMPLETE block.
- A full final listing closes the build so the reader can diff their file against it.
- The code lives at a stated repo path and the module prints the one command that runs it.
- Rationale: a pasted trace in a document is indistinguishable from a fabricated one. Video earns trust by liveness; **text earns it by the committed, re-runnable script.** Without that, Move 8 discharges nothing.

**Run stamps.** Every printed model output carries one line beneath it: date, model id/version, temperature/seed, n. A lecture's numbers are witnessed once and archived; a hub module lives for years while judge models drift and get deprecated. This mirrors the provenance-manifest rule that `--check` already enforces for generated media (`docs/asset-pipeline.md`).

**Cost.** State API spend in the contract, mark which steps cost money, and commit recorded outputs as fixtures so the module stays readable and its numbers checkable without a key or a budget.

**Who runs it.** The author ships the finished, committed, runnable artifact **and** its real output — that is what makes printed evidence honest in a medium with no liveness. `Build` and `Definition of done` then move the learner to re-running it against **their own** system and data, producing their own numbers. This satisfies doctrine #4, keeps `Boss fight` and the ledger meaningful, and makes the hand-off the climax rather than an appendix. Everything below is read through this split.

**Figure conventions.** `^ caption` on the line immediately after `</svg>`; `role="img"` + `aria-label` on every `<svg>`; all strokes and fills from CSS variables.

---

## 1. The stance

A module exists so the reader ends up holding a working thing, and the prose is the scaffolding around the build, not the product — "in the spirit of "what I cannot create I do not understand", what better way to do this than implement it from scratch?" `[written]`, and "I'm going to build it out step-by-step, and I'm going to spell everything out." `[ep2]`. Understanding must be **bounded out loud**: state the finite size of what is being learned so the reader can see the ceiling — "is literally 100 lines of code" `[ep1]`, "Everything else is just efficiency. I cannot simplify this any further." `[written]`. Math is not the medium; small numbers running through real code are — "this tutorial will contain **very little math** (I don't believe it is necessary and it can sometimes even obfuscate simple concepts)" `[written]`. Nothing is asserted that could have been printed, and nothing derived is trusted until a second, dumber route agrees with it — "nodes of it so this is the claim and now let's verify it" `[ep1]`. Failure is curriculum rather than embarrassment: bugs, dead ends, and admitted ignorance stay on the page, because in this domain wrong code usually does not crash — "i thought about redoing it but i figured i should just leave the error in here" `[ep1]`, "#### 2) Neural net training fails silently" `[written]`.

The register is one patient expert sitting beside one person — "deeply passionate, great at teaching, infinitely patient and fluent in all of the world's languages" `[public]`.

**On effort and delight.** "Learning is not supposed to be fun. It doesn't have to be actively not fun either, but the primary feeling should be that of effort." `[public]` Read that narrowly: it forbids **substituting entertainment for the work** — jokes in place of manipulation steps, a scroll in place of a sitting. It does not license a joyless module, and the older draft of this spec made exactly that mistake, elevating the effort line to governing stance while filing everything enjoyable in the Voice table as if it were decoration. It is not decoration. The delight in the sources is load-bearing and it is all in the same place: a machine hallucinating plausible names, "// -5.87! exciting." `[written]`, "I think it is beautiful 🥹" `[written]`, "Now I would like to scare you a little bit." `[ep2]`. Three things follow, and they are requirements, not flavour:

- **The payoff must be worth wanting** (Move 1). If your payoff is a bare score, find the thing behind the score.
- **At least one prediction per module must be genuinely surprising** (Move 3), with the size of the surprise stated when you reconcile it. The model of this is "I do not expect 27." / "which is 3.29, much, much lower than 27." `[ep4]`
- **The module must end pointed at the reader's own system** (Move 20), not at the author's toy.

The reader should finish tired and correct: "You want the mental equivalent of sweating." `[public]`

---

## 2. The moves

Moves 1–16 are observed in the sources. Moves 17–20 are `[hub]` requirements with no Karpathy precedent and are labelled as such.

### 1. Cold Open on the Working Artifact
`[ep1] [written]`

**RULE.** After the contract paragraph, the first thing the reader meets is the artifact: one sentence naming what they will be able to do; a complete runnable code block; its real pasted output; and the module's final payoff under a "preview / skipping ahead" label. Reproduce that same payoff block verbatim at the end with "(again)". No definitions, no learning-objective bullets.

**The payoff must be something the reader would want to show someone else** — a generated artifact, a caught bug, a number that flips an assumption. A bare pass count is not a payoff. If the honest headline is a score, open on the thing behind the score.

**EVIDENCE.**
- "of micrograd is I think best illustrated by an example" `[ep1]`
- "As a preview, by the end of the script our model will generate ("hallucinate"!) new, plausible-sounding names. Skipping ahead, we'll get:" `[written]`

**MODULE EXAMPLE.** An evals module opens by running the finished 40-line harness over 12 test cases and pasting the actual console output. The payoff is not `passed 9/12` — it is the diff between what the grader said and what the author said, printed side by side, with one line under it: "the grader and I disagree on three cases. On one of them the grader is right and I was wrong; we find out which in the calibration section." The same block reappears at the end with "(again)".

---

### 2. The Pedagogy Contract
`[written]` + `[hub]`

**RULE.** Three to five sentences at the top of `## Why this module`, after the gap statement, in the author's own voice: what this module contains, what it deliberately omits and why, the prerequisite bar stated casually, and a flag on which part is hardest with a pointer to a slower treatment. Never a bulleted "learning objectives" box.

Also state, `[hub]`, the runtime, the API spend, and the sitting length — **none of these is Karpathy-observed** (microgpt's own preamble states neither runtime nor cost), and all three are hub additions because a module that costs money to run must say so before the reader starts.

**EVIDENCE.**
- "Basically, I will strive to present the algorithms in a way that I wish I had come across when I was starting out." / "Assumes basic knowledge of Python and a vague recollection of calculus from high school." `[written]`
- "I realize that this is the most mathematically and algorithmically intense part and I have a 2.5 hour video on it" `[written]` (microgpt, Autograd section)

**MODULE EXAMPLE.** "This module builds a retrieval eval from scratch: BM25 scored by hand, recall@k, and one LLM judge. No vector database, no framework, no statistics beyond averaging and a spread — I don't think you need more to see the mechanism. You need to know what a Python dict is. It runs in about 90 seconds on a laptop and costs about $0.40 in judge calls, or nothing if you use the committed fixtures. The judge-calibration part is the hard one."

---

### 3. Make the Reader Commit First
`[ep1] [ep4] [written]`

**RULE.** No number appears before the reader has been asked what it should be. Grade the ask to what is guessable — sign before magnitude, shape before value. **At least one prediction per module must discriminate between real mental models and have a surprising answer**; state the expected wrong answer out loud, then state how big the surprise was. A coin flip that everyone gets right half the time teaches nobody anything.

**Hiding the answer.** `<details>` does not render here — it is escaped, and the answer sits in plain sight, inverting the move. Pick one of these and use it consistently:

1. the answer opens the next `## `-level section, named in the question ("answered at the top of Worked example");
2. a full-width figure sits between question and answer, pushing the answer off-screen;
3. a `- [ ]` checkbox list of candidate answers (renders natively as `<ul class='checks'>`) with the key at the end of the section.

Do not write "below the fold" — there is no fold in a continuously scrolling single-column reader with reader-controlled zoom.

At least once per module, withhold entirely: ship a stub with `# your turn: what goes here?` and reveal a paragraph later. That stub is the one code block exempt from Move 8's printed-output rule.

**EVIDENCE.**
- "In this case, I do not expect 27." / "which is 3.29, much, much lower than 27." `[ep4]`
- "here you can potentially pause the video and think about what should go here" `[ep1]`; "var x = a * a;\nvar da = //???" `[written]`

**MODULE EXAMPLE.** "The corpus has near-duplicate chunks. Before we dedupe them — will recall@10 go up or down? Most people say up: fewer distractors, cleaner ranking." Then a full-width figure. Then: `recall@10: 0.62 → 0.54`. Then the reconciliation: "It went *down*, and by more than the noise. The 0.62 was counting the same gold document twice inside the top ten. The duplicates were not distractors — they were the score."

---

### 4. Mechanism, Then the Name, Then the Deflation
`[ep2] [written]`

**RULE.** A term never appears before the thing it names. Fixed three-beat cadence: (1) build/use the mechanism under a descriptive name of your own, (2) a single bolded sentence "this is called **X**", (3) one sentence naming and dissolving the intimidation, plus the acronym expanded inline. All three beats, every time — an example that skips the deflation has not demonstrated the move. Every displayed formula gets a "reading the symbols" paragraph that names the likely misparse, blames the notation, and restates the thing as arithmetic on two numbers.

**EVIDENCE.**
- "So these last two lines, by the way, here, are called the softmax, which I pulled up here." `[ep2]`
- "This looks a bit scary if you're not comfortable with your calculus, but this is literally just multiplying two numbers in an intuitive way." `[written]`; "I know it's confusing but it's standard notation. Anyway, I hope it doesn't look too scary because it isn't" `[written]`

**MODULE EXAMPLE.** A retrieval module computes "how far down the list the right document sits, averaged over queries" for three queries by hand (positions 1, 4, 2), then: "This is called **MRR** — mean reciprocal rank." Then the deflation: "MRR is not a statistical object. It is 1/1 + 1/4 + 1/2, divided by three. You just did it. The formula `1/N · Σ 1/rank_i` looks like notation because `Σ` is written in Greek; it means 'add these up'."

---

### 5. One Physical Substrate, Coined and Reused
`[ep1] [written]`

**RULE.** Pick exactly one mechanical substrate per module and hold it for the whole module — never stack a second metaphor later. Carry real numbers inside the analogy, close with the bridge sentence ("X is the same idea: …"), and coin a plain-English name if the standard term obscures things, admitting you coined it. Give each component a one-line quoted job description and immediately trace it through one concrete instance from the module's own toy data.

**Where the substrate vocabulary may live: prose and figure labels only.** Identifiers, code comments, and metric names use the standard term from the moment the naming beat lands. The older draft prescribed `# how much slop in the ruler?` in place of `# variance`; that makes the code ungreppable and unrecognisable against the literature, and it fights Move 4 and the bridge-to-formalism step. Write `# variance (the ruler's slop)` instead — the metaphor survives, the code stays searchable.

**EVIDENCE.**
- "if a car travels twice as fast as a bicycle and the bicycle is four times as fast as a walking man then the car travels two times four eight times as fast as a man" `[ep1]`
- "Instead of definining loss functions, I would like to base the explanation on the *force specification* (I just made this term up by the way) of a Support Vector Machine, which I personally find much more intuitive." `[written]`
- Job descriptions, one line each: "Intuitively, the query says "what am I looking for?", the key says "what do I contain?", and the value says "what do I offer if selected?"" `[written]`

**MODULE EXAMPLE.** An evals module runs on one substrate: **the grader is a ruler**. "A ruler with 3% slop cannot measure a 2% improvement — you will read noise and ship it." Job descriptions in the same shape as the query/key/value line: the rubric says "what am I measuring?", the gold label says "what is the true length?", the spread says "how much can I trust this reading?" Every figure labels the axis "ruler reading"; the judge's disagreement rate is drawn as tick marks of varying width; the code comment reads `# variance (the ruler's slop)`.

---

### 6. Ugly First
`[ep1] [written]`

**RULE.** Never present the good method first. Do the work by hand until the tedium is unmistakable, then name the tedium as the motivation, then present the code as a one-to-one transcription of the moves just performed. Where several implementations exist, use literal numbered headings — "Strategy #1", "#2", "#3" — each with runnable code, its real output, a sentence conceding it works, and a specific quantified reason it dies. End the ladder with a cost comparison across all rungs. Pair any clean abstraction with the fully expanded flat version and comment on the tedium.

**Relationship to Move 7.** The carried micro-example is the *spine*; the cases that kill each rung are a small, named **adversarial set** introduced one at a time, at the rung each one kills. Name the set on first use and keep it fixed. Without this the two moves appear to contradict — by construction the killers are not the spine.

**EVIDENCE.**
- "so doing the back propagation manually is obviously" / "ridiculous so we are now going to put an end to this suffering" `[ep1]`
- "This is a perfectly fine strategy for tiny problems with a few gates if you can afford the compute time, but it won't do if we want to eventually consider huge circuits with millions of inputs. It turns out that we can do much better." `[written]`; "Obviously, you want to modularize your code nicely but I expended this example for you in the hope that it makes things much more concrete and simpler to understand." `[written]`

**MODULE EXAMPLE.** Grade ten model answers yourself, in a printed markdown table, one row at a time, with your reasoning in a column — then: "Doing this by hand for 10 answers took me four minutes. For 2,000 it is not happening." Strategy #1 is exact string match (3 lines, prints `0.40`, killed by adversarial case A, a correct paraphrase); #2 is token F1 (`0.71`, killed by case B, a wrong answer that shares most of its tokens with the right one); #3 is the judge.

---

### 7. One Micro-Example at Scalar Altitude
`[ep2] [ep4] [written]`

**RULE.** Choose one micro-example and carry it through the entire module unchanged, so the reader tracks identity across sections. Print its full intermediate state at every step. Enumerate derived items rather than asserting counts. Write the reference implementation with zero vectorization — explicit loops over single numbers — and state the altitude in the section header ("one query at a time" / "now on batches"). Scale to the real data in a short final passage whose whole point is that no code changed.

**EVIDENCE.**
- "And then we don't actually want to take all the words just yet because I want everything to be manageable. So let's just do the first word, which is emma." / "So this single word, as I mentioned, has one, two, three, four, five examples for our neural network." `[ep2]`
- "So here's a smaller four-dimensional example of the issue." `[ep4]`; "The math is identical, just corresponds to many scalars processed in parallel." `[written]`

**MODULE EXAMPLE.** A retrieval module uses one 8-document corpus and one query, `"how do I rotate an API key"`, for every section. BM25 is computed for one (query, term, document) triple with all four numbers written out — `tf=2, df=3, N=8, avgdl=41` — then the per-document loop, then the whole 50-query run at the end with the note that only the input path changed.

---

### 8. Printed Evidence, Twice
`[ep1] [written]` + `[hub]`

**RULE.** No code block ships without its real output — the one exception is Move 3's deliberate `# your turn` stub. Put results in trailing comments on the line that produced them, including intermediate values and the messy tail digits; paste raw console traces verbatim with a `...` elision rather than paraphrasing them. Then every derived quantity gets a second computation by a slow, obviously-correct route — or by the mainstream library — with both numbers printed adjacently and the match called out. Never claim an equivalence you did not print.

`[hub]` Printed evidence only discharges anything if the script is committed and re-runnable. Every module names the script path and the one command that reproduces the pasted numbers, and every model-derived output carries its run stamp. Otherwise a pasted trace carries exactly as much authority as a bare claim.

**EVIDENCE.**
- "so those are our claims let's delete this and" / "let's verify them" / "we're doing here is kind of like an inline gradient check" `[ep1]`
- "**Numerical Gradient Check.** Before we finish with this section, lets just make sure that the (analytic) gradient we computed by backprop above is correct as a sanity check." / "and we get `[-4, -4, 3]`, as computed with backprop. phew! :)" `[written]`

**MODULE EXAMPLE.** After the vectorized scorer: `print(f"{score:.4f}")  # 0.7143 — same as the hand loop below`, then the naive `for` loop over the same 12 cases printing `0.7143`, then the same metric from an off-the-shelf library printing `0.7143`, with one sentence of bookkeeping: identical algorithm, different speed. Under it: `run: 2026-08-20 · scorer is deterministic · n=12 · reproduce with python evals/retrieval_eval.py --check`.

---

### 9. Plant the Bug, Leave the Bug In
`[ep1] [ep2] [ep3]`

**RULE.** Plant at least one deliberate failure per module and say out loud that you planted it. Format: a one-line "what do you expect?" → the code → the **verbatim** error text or the plausible-looking wrong number → a hard stop ("Stop here. Why is this wrong?") → the autopsy → a three-line minimal reproducer → the fix as a diff → a paragraph on **why it still seemed to work** → the one-line assertion that would have caught it. Name the bug class so the reader can recognise it in the wild. Do not sanitise error text.

**Scope of "leave it in": wrong results, dead ends, planted bugs, admitted ignorance.** Not performed verbal stumbles — see the Voice table, which now splits these.

**EVIDENCE.**
- "And I'm making some of these errors intentionally, just so you get to see some errors and how to fix them." `[ep3]`
- "Now, if I run this, you'd expect it to work, but it doesn't. You actually get garbage. You get a wrong result because this is actually a bug." `[ep2]`; "you may have lots of bugs in the code and your network might actually work just like ours worked" / "the only reason that worked is that this is a very very simple problem" `[ep1]`

**MODULE EXAMPLE.** The retrieval eval scores `recall@5 = 0.90` and looks great. Stop-and-think block. Autopsy: chunking produced two near-identical chunks of the same source doc, so the gold document is counted twice inside top-5. Minimal reproducer with 3 chunks. Fix as a diff (`dedupe by doc_id before truncation`). Then "why it still looked plausible": on this corpus every duplicate happened to be relevant, so the number only inflated — it never went wrong enough to notice. Named: **`duplicate-gold inflation`**.

---

### 10. Break It On Purpose and Read the Symptom
`[ep1] [ep4]` · *advanced*

**RULE.** After establishing the healthy state, sabotage it deliberately and ask "how would you have noticed?" before answering. Sweep a knob across 3–5 values including at least one that is wrong, reporting what each does. Then a symptom table: rows are injected bugs, columns are your diagnostic views, cells are one-line signatures. State the prediction above every result. Every swept value reports its spread, not a point (Move 18).

**EVIDENCE.**
- "Let's say that we forgot to apply this fan-in normalization." / "What happens to our, how do we notice that something's off?" `[ep4]`; "Let's try 3." `[ep4]`
- "if you go too fast by the way if you try to make it too big of a step you may actually overstep" / "we actually overstepped so we got too too eager" `[ep1]`

**MODULE EXAMPLE.** Sweep judge temperature `0.0 / 0.7 / 1.0`, three reruns each on n=12, printing the score and its spread: `0.750 (spread 0.00) / 0.736 (spread 0.04) / 0.708 (spread 0.11)`. Then a symptom table: *swapped A/B order* → score moves 0.08 and always favours position A; *rubric with no tie option* → 0% ties, suspiciously; *no gold labels* → judge agreement 95% but a rubber-stamp baseline also scores 90%.

---

### 11. Intercept the Objection the Reader Is Forming
`[ep4] [written]`

**RULE.** At each transition where a sharp reader would push back, write their complaint as an italicised quoted interruption, say "Good question.", then answer in staccato yes/no. After each code block, add a "you might notice" paragraph naming the wrong inference explicitly before correcting it — including where *your* simplification is the unusual choice. Where the reaction depends on background, fork the audience.

**EVIDENCE.**
- "But hold on, you say: *"The analytic gradient was trivial to derive for your super-simple expression. This is useless. What do I do when the expressions are much larger? Don't the equations get huge and complex very fast?"*. Good question. Yes the expressions get much more complex. No, this doesn't make it much harder." `[written]`
- "Now you're probably wondering, can we just set this to zero?" `[ep4]`; "You might notice that we're using a KV cache during training, which is unusual." `[written]`

**MODULE EXAMPLE.** *"But hold on, you say: "my judge agrees with my own labels 95% of the time. Why do I need labels at all?""* Good question. Yes, 95% is high. No, it means nothing here: 90% of these cases pass anyway, so a grader that returns PASS unconditionally scores 90%. The number you want is agreement on the 10% that fail.

---

### 12. Honest Fence-Posting
`[ep1] [ep3] [ep4]` · *null-results half is intermediate+*

**RULE.** Mark boundaries inline, at the moment each one occurs, with a reason attached — "skipped for efficiency, the math is unchanged" reads differently from "a real topic, later". Flag every teaching-only shortcut as an admission, not a warning. Confess magic numbers before deriving them. Say what you could not find or do not understand. Keep genuine uncertainty as uncertainty. Close with a "what we did not settle" passage including null results, and absolve the reader for residual confusion.

**Limit.** You may fence off the *depth* of a technique to another module. You may never fence off the **uncertainty on a number this module acts on** — see Move 18. "We skip significance testing here" is fine only if the module still reports n and spread and never calls a within-noise delta an improvement.

**Errata.** `[hub]` Ship a visible **Errata** subsection from version one with first-person notes on mistakes made while writing, and record when a printed number was re-run and changed. **This has no Karpathy precedent** — the string "errata" appears nowhere in the corpus. It is our addition, kept because hub modules are long-lived and their numbers rot.

**EVIDENCE.**
- "But what we have here now is all these magic numbers, … Like, where do I come up with this?" / "I tried searching briefly for where this comes from, but I wasn't able to find anything." / "We certainly haven't, I would say, solved initialization." `[ep4]`
- "never be doing any of this in production it's real just for them for pedagogical reasons" / "about 15 minutes and i couldn't find 10h" `[ep1]`; "Obviously, this is janky and not exactly how you would train it in production." `[ep3]`

**MODULE EXAMPLE.** Inline: "The 0.6 pass threshold is a number I made up by eyeballing ten outputs — we derive a defensible one below." / "We skip significance testing here; it is a real topic and it needs its own module. What we do not skip is the spread — every number below carries one." / "I looked for fifteen minutes and could not find where the standard harness defines partial credit, so this implementation is my guess." Closing: "The judge did **not** beat token-F1 on this corpus, and on n=50 the gap is inside the noise either way. Here is the honest version: the corpus is too lexically easy to separate the two, and 50 queries cannot resolve a 4-point difference." Absolution, written out: "If the judge-calibration section still feels slippery, that is the correct reaction — it is the part I am least sure of, and every other section runs without it."

---

### 13. The Running Tally and the Lurking Defect
`[ep3] [ep4]` · *intermediate+*

**RULE.** Restate the running tally after every fix — the starting number, what each fix addressed, the new number — and keep the failures in the tally. This is the observed pattern, and it is **prose**: both cited lectures narrate a spoken running total, and no table exists in either. Rendering the tally as a table is **our formatting choice**, not an observed one; the only tabular precedent in the corpus is microgpt's two-column Progression table (File / What it adds). The older draft's five named columns were invented.

Re-render the table **only when a number actually changed**, not after every section. End every section with an explicit "and yet" sentence naming the next lurking defect by name, so the boundary is a cliffhanger. **This is the primary inter-section device** — see Move 15, where the competing closers are cut back around it.

**EVIDENCE.**
- "we started off with a validation loss of 2.17 … By fixing the softmax being confidently wrong, we came down to 2.13. And by fixing the 10H layer being way too saturated, we came down to 2.10." / "Now let's look at the second problem." `[ep4]`
- "And so far we are what's called underfitting because the training loss and the dev or test losses are roughly equal." / "So you see how the training and the validation performance are starting to slightly slowly depart." `[ep3]`

**MODULE EXAMPLE.** A tally that reports intervals, because a delta cannot be adjudicated without one:

| fix | addressed | recall@10, n=50 | Δ (paired) |
|---|---|---|---|
| baseline BM25 | — | 0.62 [0.48–0.74] | — |
| dedupe gold | duplicate-gold inflation | 0.54 [0.40–0.67] | −0.08; 4 queries broken, 0 fixed — the bug is proven by the reproducer, but at n=50 the *metric* move is inside the noise |
| chunk 256→512 | answers split across chunks | 0.71 [0.57–0.82] | +0.17; 11 fixed, 2 broken, sign test p≈0.02 — real |
| add reranker | lexical-only matching | 0.71 [0.57–0.82] | 0.00; 0 fixed, 0 broken — no effect at all, not "too small to see". Kept as a failure. |

Each section ends: "and yet — we still have not checked the judge against a single human label."

---

### 14. Anchor the Toy to the Real Thing
`[ep1] [written]`

**RULE.** Every **headline** metric, and every metric's **first appearance**, ships with its bracket: the value at chance/initialisation (arithmetic shown in the text), the theoretical floor, and where you landed — plus its real-world counterpart. Install a named baseline early and reuse the same number verbatim later as the yardstick.

**Scope.** This does *not* apply to intermediate values inside a printed trace. The older draft said "never state a size, count, or metric without its real-world counterpart in the same sentence", which collides head-on with Move 7's "print full intermediate state" and Move 8's "including the messy tail digits" — you cannot append a production counterpart to every number in a console dump. Stating the absolute unfollowably trains writers to treat this spec's absolutes as optional.

Close the module with a **Real stuff** passage that walks the same components in the same order, one bolded paragraph each, **renaming freely and adding production-only components** — microgpt's teaching headings are Dataset / Tokenizer / Autograd / Parameters / Architecture / Training loop / Inference, and its Real stuff heads are Data / Tokenizer / Autograd / Architecture / Training / Optimization / Post-training / Inference. Same components, same order; not byte-identical, and the older draft's claim that they were is false. State up front that none of it alters the core.

**EVIDENCE.**
- "In our tiny model this comes out to 4,192 parameters. GPT-2 had 1.6 billion, and modern LLMs have hundreds of billions." / "microgpt contains the complete algorithmic essence of training and running a GPT. But between this and a production LLM like ChatGPT, there is a long list of things that change. None of them alter the core algorithm and the overall layout … Walking through the same sections in order:" `[written]`
- "but it works on fundamentally the exact same principles" `[ep1]`

**MODULE EXAMPLE.** "Eight documents here; a production index is 40M chunks. Twelve test cases here; a real suite is 2,000–50,000." And the baseline: "Random ranking over 8 documents gives recall@1 = 1/8 = 0.125. Perfect is 1.0. We are at 0.62 [0.48–0.74] — so there is a lot of room, and anything near 0.125 means our scorer is doing nothing." The closing passage bolds *Corpus*, *Scorer*, *Metric*, *Judge*, *Aggregation*, plus *Serving* and *Drift monitoring*, which had no teaching counterpart.

---

### 15. Close the Loop: Recap, Discharge, Hand Over the Knobs
`[ep1] [ep3] [written]`

**RULE — section closers, capped at two.** End a section with the "and yet" cliffhanger (Move 13) plus **either** a two-to-four-sentence "where we are" prose paragraph **or** a labelled **Recap** block of 3–6 bullets — never both. Across eighteen sections the older draft stacked five terminal devices, roughly ninety closers that fought each other: "where we are" looks backward while "and yet" looks forward, and a bullet Recap immediately after a deliberately-not-bullets prose paragraph is the same content twice. Where a Recap is used, bold every newly earned term so it doubles as the glossary feeding `## Concepts`. Recap bullets state INPUT / OUTPUT / the strategies we tried — but note they must not become the learning-objectives box that Move 2 and Anti-pattern 10 ban, relocated to the end.

**RULE — module close.** In order: the whole pipeline restated in one paragraph; a "we promised X, here is X" walk back through the finished artifact; a short **FAQ** of 5–8 bolded reader-voice questions including the naive one, the philosophical one, and "why is mine slow"; then the hand-off (Move 20).

**EVIDENCE.**
- "in the beginning of this video i told you that by the end of it you would understand" / "everything in micrograd and then we'd slowly build it up let me briefly prove that to you" `[ep1]`
- "**Does the model "understand" anything?** That's a philosophical question, but mechanically: no magic is happening." / "Whether this constitutes "understanding" is up to you, but the mechanism is fully contained in the 200 lines above." `[written]`; "Now I invite you to beat this number." `[ep3]`

**MODULE EXAMPLE.** Pipeline paragraph: query → retrieve top-k → generate → grade → aggregate → repeat. Then the promise discharged by pointing at the cold open's disagreement and naming it as the duplicate-gold bug. FAQ, with the three required kinds written out:
- "**Why not just eyeball the outputs?**" — You did, in the ugly-first pass: four minutes for ten answers, and you and the grader still disagreed on three. Eyeballing does not scale and does not leave a number anyone can re-check.
- "**Is an LLM grading an LLM circular?**" — The judge only sees text and a rubric; it has no access to the generator's weights, and its slop is measured against human labels above — here is the number.
- "**Why is mine slow?**" — The judge calls are serial, one per case, at `evals/judge.py:41`. Twelve cases is 90 seconds; 2,000 cases is five hours until you batch that loop.

---

### 16. The Standalone Takeaway Line
`[single-source: written]` · *intermediate+*

**RULE.** Roughly one takeaway line per major derivation — the single source has 11 across ~14,000 words, about one per 1,275 words. State the takeaway in one or two sentences, using the module's own substrate vocabulary, quotable standalone. Sometimes it is a permission slip rather than a definition; sometimes it is a quoted self-echo of the paragraph above.

This is a **cap, not a quota**: at most one per major section, and only when the sentence is genuinely quotable on its own. A quota manufactures filler aphorisms. The older draft demanded "every 400–800 words, exactly one single-sentence blockquote, no attribution, never two in a row" — every quantified clause of which is falsified by the one source it cites: the spacing is ~1,275 words, three of the eleven are quotation-marked self-attributions, one is two sentences, one contains an embedded enumerated list, and two of them are separated only by a short paragraph.

The line must also be **true**. It is a takeaway, not a flourish, and it is still bound by Anti-pattern 8 and Move 12.

**Rendering.** `> ` does not render — it emits a literal `>`. Write the line as a bolded sentence alone on its own line. Switch to `> ` only if `md_to_html` gains a blockquote branch.

**EVIDENCE.**
- "> The derivative can be thought of as a force on each input as we pull on the output to become higher." `[written]`
- "> If this makes sense, you understand backpropagation." `[written]`

**MODULE EXAMPLE.** After the judge-calibration derivation: **A grader you have not measured is not a measurement.** The older draft's second example — "If this makes sense, you understand every retrieval metric in the literature" — is deleted: it is false (nDCG's rank discounting is not reciprocal rank), and it violated both the inflation ban and honest fence-posting. A true replacement: **Recall@k asks one question — did the right document make the cut? Everything else you have heard about ranking is a different question.**

---

### 17. Boss Fight: Closed-Book Recall
`[hub]` — no Karpathy precedent

**RULE.** `## Boss fight` holds 5 closed-book questions answerable only by someone who actually built the thing, at least one requiring a number the reader's **own** run produced. Passing writes a dated entry to `ledger/recall-ledger.json`. Hub doctrine #1 is "Assets are not learning — dated recall is", and `modules/README.md` gates completion on that ledger pass, "No exceptions".

Distinguish it from its neighbours: **Drills** are open-book and attached to their section; **FAQ** answers reader objections; **Boss fight** is from memory, with the module closed. Drills cannot substitute — they are open-book by construction and cannot produce the closed-book pass the ledger records.

**MODULE EXAMPLE.** "Without looking: name the two numbers that make a recall figure interpretable, and say what each rules out." / "Your own run printed a spread on the judge at temperature 0.7. What was it, and what would you have concluded if it had been three times larger?"

---

### 18. Every Number Gets an Interval
`[hub]` — hub doctrine #3

**RULE.** No headline metric ships without **n**, the **spread across at least three runs** (or an explicit "n is too small for an interval, here is the raw spread"), and no scoreboard delta may be called an improvement or a failure unless it clears that spread. Doctrine #3 is "every claim gets a number, every number gets an uncertainty"; `CURRICULUM.md` names "reports point scores with no variance" as the #1 diagnosed portfolio gap, and `evals-basic-01` flags its own missing variance as the reason `evals-basic-02` exists.

The older draft mandated a bracket (Move 14) and a cross-check (Move 8) but never an interval, and every one of its examples printed a bare point — `9/12`, `recall@10 = 0.62`, `0.7143`, `recall@5 = 0.90` — while its flagship scoreboard adjudicated `−0.08 / +0.17 / 0.00` deltas on 50 queries and called one "kept as a failure", a call that is unmakeable without a spread.

"It seems better" is banned vocabulary.

**MODULE EXAMPLE.** See Move 13's tally, which is written to this rule: the `−0.08` is explicitly *not* claimed as a regression, and the `0.00` is distinguished from "too small to see" by reporting that zero queries changed in either direction.

---

### 19. Provenance and External Resources
`[hub]` — `modules/README.md` absorption rules

**RULE.** `## External resources` is links + your own summaries, never copies. Every absorbed own-artifact carries `Source: faisalmahdy/<repo> — <path>` and is de-personalised (paths, names, personal content scrubbed).

**And the micro-example itself must come from a real system in the labs**, not an invented generic toy. Doctrine #4 is "Learn against your own artifacts, not toy exercises", and `evals-basic-01` anchors everything to a named source file. Every example in this spec is a generic invention precisely so it can illustrate a move without anchoring; **a real module may not do that.**

---

### 20. Point It at Your Own System
`[hub]` — doctrine #4, and the best hook available

**RULE.** `## Build` ends by turning the finished artifact on the reader's own system and data. Name actual variables to change and their expected effects, expose **one primary dial** with the rest derived (Anti-pattern 18), give a number to beat, and end with a send-off rather than a summary.

**EVIDENCE.** "These are the same knobs that matter at scale." `[written]` (microgpt FAQ) · "Now I invite you to beat this number." `[ep3]` · "Good luck!" `[written]`

**MODULE EXAMPLE.** "Point this at your own retrieval system. The one dial is `k` — start at 5, then 20; `chunk_size` and the judge's tie clause are derived from it in `config.py` and you should not touch them until `k` stops moving the number. On my corpus the suite scores 0.71 [0.57–0.82] over 50 queries. Yours will be a different number on different documents, which is the point — bring back the interval, not the score. Good luck."

---

## 3. Voice

| DO | DON'T | Evidence |
|---|---|---|
| First-person plural for the labor, first-person singular for judgment and promises. | An institutional or passive voice ("it is recommended that…"). | "We're going to build it out slowly and together." `[ep2]` · "I expect a much lower number, … and we can calculate it together." `[ep4]` |
| Blunt, unhedged verdicts on your own artifacts, in ordinary words. | Technical euphemism for "this is bad" ("suboptimal", "has limitations"). | "It's just bigram is so terrible and we have to do better." `[ep2]` · "Obviously, this is janky and not exactly how you would train it in production." `[ep3]` |
| Admit ignorance flatly, and keep calibrated hedges. | Bluff authority, or hedge the math to sound humble. | "i don't know what these files are doing honestly" `[ep1]` · "honestly, I have no idea where 5 over 3 came from in PyTorch when we were looking at the counting initialization." `[ep4]` |
| Say when the standard source or standard definition is bad. | Defer to docs/textbooks you find unhelpful. | "this is not a very good definition of derivative this is a definition of" / "what it means to be differentiable" `[ep1]` · "So that's not confusing at all." `[ep2]` |
| Deflate with "just", "literally", and a stated size. | Inflate with "powerful", "state-of-the-art", "cutting-edge". | "is literally 100 lines of code" `[ep1]` · "this is literally just multiplying two numbers in an intuitive way" `[written]` |
| One-word celebrations welded to a real printed number. | Manufactured enthusiasm with no artifact under it. | "forwardMultiplyGate(-2, 3); // returns -6. Exciting." `[written]` · "lol  `¯\_(ツ)_/¯`. Not bad for a character-level model after 3 minutes of training on a GPU." `[written†]` (nanoGPT README — web-verified, not in the local corpus) |
| Anthropomorphize freely, then cash the metaphor out in the very next sentence. | Vibes-only metaphor with no mechanism attached. | "So W wants to be zero and the probabilities want to be uniform, but they also simultaneously want to match up your probabilities as indicated by the data." `[ep2]` · "Intuitively, the query says "what am I looking for?"" `[written]` |
| Name the reader's fear and ask for a posture toward it. | Pretend the hard part isn't scary. | "Now I would like to scare you a little bit." `[ep2]` · "Anyway, I hope it doesn't look too scary because it isn't" `[written]` |
| Tell the reader which sections they can skim and which they cannot, and give an explicit skip path. | Meta-narrate your own pacing. | Karpathy's "Now, I'm skipping through this section a little bit quickly, and I'm doing that actually intentionally." `[ep4]` is a **video** device: the viewer cannot control the rate, so the narrator must announce rate changes. In text the reader sets the rate entirely and announcing your own speed is meaningless. Translate it to density signalling — label a section *skimmable* / *read slowly* / *do it yourself*, and write "if you already know BM25, jump to the judge". |
| Leave wrong results, dead ends, planted bugs, and admitted ignorance in. | Sand every seam smooth so the module reads as a finished monument. | "i thought about redoing it but i figured i should just leave the error in here" `[ep1]` · "And I'm making some of these errors intentionally" `[ep3]` |
| — | Do **not** stage verbal stumbles. | "Oops. Sorry. This is the mean, and this is the variance." `[ep4]` and "Oops, I should not have printed. I meant to erase that. Let's kill this." `[ep2]` are authentic in live video because redoing them costs a 2.5-hour re-record and the viewer feels that constraint. In prose every "oops" is typed on purpose and then preserved through revision, so it reads as costume. Keep the wrong *result*; drop the performed stumble. |
| Re-state the number or shape instead of using a pronoun. | "as we saw earlier" with no restatement. | "So if this is h, then h slash shape is now the 100-dimensional activations for every one of our 32 examples." `[ep3]` |
| Repeat the key sentence verbatim at the takeaway moment. | Vary the wording for style at the one point retention matters. | "none of this will really fundamentally change. None of this will fundamentally change." `[ep2]` |
| Aesthetic vocabulary for code and math — cute, ugly, gross, pleasing. | Neutral clinical description of things you have an opinion about. | "gross and people don't like this too much." `[ep2]` · "I think it is beautiful 🥹" `[written]` |
| Warm, forward-pointing send-off. | A summary flourish or a motivational conclusion. | "So that's going to be pretty awesome, and I'm looking forward to it. For now, bye." `[ep2]` · "Good luck!" `[written]` |
| First-person war stories with the scar shown. | Abstracted advice ("be careful with preprocessing"). | "And I've shot myself in the foot with this layer over and over again in my life. And I don't want you to suffer the same." `[ep4]` · "One time I discovered that the data contained duplicate examples." `[written]` |

---

## 4. Structure template

The canonical flow, expressed as `###` subsections nesting inside the seven mandatory `## ` sections. **Contract first, then the artifact** — the older draft contradicted itself, telling the writer both that "Section 0 contains a complete runnable code block" and that the contract comes "before the first heading", with a structure template that ordered them the other way.

**Inside `## Why this module`.**
1. **The gap, with evidence.** What this closes, cited. This is the hub's required opening and is *not* a motivational preamble.
2. **The contract.** 3–5 sentences: contents, omissions, prereqs in his register, runtime, cost, sitting length, hardest-part flag `[written]` `[hub]`.
3. **Cold open on the artifact.** Run the finished thing, paste real output, show the payoff as a preview, one small "where this module sits" ladder figure, and a one-line launch: "we have to start here, character level language modeling. Let's go." `[ep2]`. One human sentence on why anyone would want this is permitted here — it is the single sanctioned why-sentence, and Anti-pattern 10 is scoped to allow it. Where a previous module exists, open instead on *its* re-run and quantified death — "And the whole thing just kind of explodes and doesn't work very well." `[ep3]` — so the new mechanism arrives as a rescue, not a topic.

**Inside `## Concepts`.** Written last. The lead line, then one terse entry per term with a forward pointer. No definitions doing explanatory work.

**Inside `## Worked example`.**
4. **Refuse the expected entry point; install the frame.** One paragraph postponing what the reader came for, then a frame sentence of the form *In my opinion, the best way to think of X is as Y* — the verbatim instance being "In my opinion, the best way to think of Neural Networks is as real-valued circuits" `[written]`. Note the template itself is not a quote and carries no quotation marks. All later vocabulary comes from that frame.
5. **Look at the data.** Cheap concrete facts and felt scale before any modeling — "The first step to training a neural net is to not touch any neural net code at all and instead begin by thoroughly inspecting your data." `[written]`; the 32,000-words / shortest-2 / longest-15 beat `[ep2]`. Then reframe the data (one item is secretly many examples).
6. **Base case.** Literal heading "Base Case: <the one-element version>", matching nntutorial.md's "### Base Case: Single Gate in the Circuit". Under ten lines, one figure, on the micro-example, goal stated as a single italicised question `[written]`.
7. **Strategy ladder.** Numbered dumb-to-good attempts, each run, conceded, then killed by a named adversarial case with a quantified limit; closing cost comparison `[written] [ep2] [ep3]`. Manual-by-hand pass first where the operation can be done by hand at all `[ep1]`.
8. **Recursive case.** Two base-case units wired together; say out loud that nothing new is required, only one composition step. Twin figure here `[written]`.
9. **Correctness crisis #1.** Immediately after the first apparent success, per `[ep1]`'s `b = a + a` and `[ep2]`'s planted broadcasting bug. Autopsy, minimal reproducer, fix, "why it still worked".
10. **Cross-check against the oracle**, before scaling up `[ep1] [written]`.
11. **Scale up.** Same code, real data, explicit observation that nothing in the code changed `[ep2]`.
12. **Break it on purpose.** Knob sweep with bad settings, sabotage, symptom table `[ep1] [ep4]`. *Advanced.*
13. **Recap + tally.** One Recap block in earned vocabulary; tally re-rendered only if a number moved; the "and yet" sentence naming the next defect `[written] [ep4]`.
14. **Bridge to the standard formalism.** Translate your homemade scaffolding into the field's notation, warn the reader nobody outside uses your terms, assert the equivalence, walk the standard formula with real arithmetic `[written]`.
15. **Real stuff.** Same components, same order, at production scale; one bolded paragraph each; production-only components added freely `[written]`.
16. **What we did not settle.** Null results with their real cause, unexplained constants, open questions, one absolving sentence `[ep4]`. *Intermediate+.*

**Inside `## Build`.**
17. **Drills.** 6–10 micro-exercises in identical format, escalating one feature at a time, joined by conversational one-liners, at least one answer withheld `[written]`. Attached to their section, not dumped at the end.
18. **Point it at your own system** (Move 20), then **FAQ**, then **Errata** `[hub]`.

**Inside `## Definition of done`, `## Boss fight`, `## External resources`.** The checklist written before starting, incl. committed script and run stamp; the five closed-book questions and the ledger entry; links with your own summaries.

**Two invariants across the whole flow.** (a) Each step is gated: hypothesis → one change → check → gate, with a literal stop sign in the prose — "If they do not, there is a bug somewhere and we cannot continue to the next stage." `[written]`. (b) Complexity is strictly monotonic and each notch reuses the previous artifact `[ep1] [ep2]`.

**Variant — process/craft modules** (the Recipe shape, `[written]`). Cross-referenced from step 3 above so a writer on a governance or ship-and-operate module finds it before writing the cold open. Two named meta-failure-mode headings first — "#### 1) Neural net training is a leaky abstraction", "#### 2) Neural net training fails silently" `[written]` — then N numbered stages in execution order, each a list of bolded-imperative bullets, section titles as verbs ("#### 1. Become one with the data" `[written]`).

Two adjustments for this hub. **Headings drop to `### `**, since `#### ` renders as a literal paragraph. And the source's zero-figure posture — `2019-04-25-recipe.markdown` is 3,903 words and contains zero images, SVGs, or `![` references, verified by grep — **does not carry here**: `modules/README.md` requires that "Every module should teach its core mechanism with at least one figure a learner could redraw from memory — the figure *is* boss-fight material", and three whole tracks (orchestration-and-governance, ship-and-operate, teaching-and-portability) are process-shaped. Process modules ship at least one mechanism figure. The variant suspends Moves 1, 6, 7, 9, 10 and the scalar-altitude requirement; Moves 2, 4, 11, 12, 14, 15, 17, 18, 19, 20 still bind.

**Worked check on a non-eval topic.** To confirm the flow generalises past retrieval and judging, here it is on an orchestration-and-governance module, *a contract checker for a three-agent fan-out*. Cold open: run the finished checker over one real fan-out; the payoff is not a pass count but the rejected payload printed in full, with the missing field highlighted — `agent-3 rejected · schema: missing 'confidence'`. Substrate: **the contract is a customs desk** — every returning agent presents a declaration, and the desk either stamps it or sends it back. Micro-example: one agent, one response, one schema, checked field by field in a `for` loop. Ladder: #1 `try: json.loads()` (killed by a response that parses but omits a required key); #2 key-presence check (killed by `confidence: "high"` where a float was required); #3 typed schema validation. Planted bug: the checker passes a payload where `confidence: 1.4`, because the range check was written `if c > 1 or c < 0` against a string. Sweep: retry count `0 / 1 / 3`, five fan-outs each, reporting the spread on rejection rate. Bracket: "three agents here; the production fleet fans out to 40." Figure: the customs desk drawn once with a conformant declaration and once with the rejected one, identical coordinates.

---

## 5. Visuals

**A figure is mandatory at exactly these moments** — his observed timing, not a general aesthetic. Cap the total at the level's figure budget.

1. **When an array or table stops being readable as prose.** Escalate legibility in stages and let the reader feel why each was needed: raw dump → bare grid → fully labeled grid with the value *inside* each cell. "So if we print n, this is the array, but of course it looks ugly." / "but even this, I would say, is still pretty ugly." `[ep2]`
2. **When the same structure must be seen in two states.** The signature figure: draw the topology once, then again below at *identical coordinates* with the second pass's numbers, captioned `(Values)` and `(Gradients)` — or pack two numbers per node with the reading convention stated in prose first. "it shows both the data (left number in each node) and the gradient (right number in each node)" `[written]` (micrograd README — verified, outside the seven-source audit set).
3. **At most two states of the same diagram per module** — before and after — or one figure using the two-numbers-per-node convention above. Karpathy re-renders after every change of state ("and now we are going to be showing both the data and the grad" `[ep1]`), which is cheap on a live canvas the viewer watches change, and brutally expensive in text: one hand-authored inline SVG per state, with the accretion rule below forcing byte-identical coordinates across all of them. Ten state changes would mean ten near-duplicate hand-coded SVGs. Author the first, then **copy the block and edit only the `<text>` nodes** — never re-derive coordinates.
4. **When a knob is swept.** Small multiples sharing one axis, captioned with the knob value, its resulting number **and its spread**, including at least one deliberately bad setting `[ep4]`.
5. **When a set is closed and enumerable.** A markdown table, *after* the intuition — one row per instance ("The full set of lego blocks": Operation / Forward / Local gradients) `[written]`.
6. **When a quantity moves over time.** Paste the raw trace verbatim rather than plotting it — "step    1 / 1000 | loss 3.3660" with a trailing `...` and a reading instruction: "Watch it go down from ~3.3 (random) toward ~2.37." `[written]`. Plot only when the *shape* is the argument, and then annotate the chance line and the floor directly on the SVG, justify any axis transform honestly ("log squashes it in, so it just looks nicer" `[ep3]`), and explain the artifacts rather than hiding them.
7. **When a function's curve is the explanation.** The log curve, the exponential, the flat tanh tail — reached for at the moment of need, referenced by geometry rather than equation `[ep2] [ep4]`.
8. **When the reasoning frame itself needs defining.** The zoomed single node with everything beyond its immediate neighbours faded, captioned in first person: "so i'm a little times node inside a massive graph and i only know that i did a times b" `[ep1]`.
9. **When two artifacts must be shown equal.** Side-by-side panels with the identical numbers highlighted `[ep2] [ep3]`.
10. **The payoff.** The artifact's own output is the most important image in the document, shown twice — preview and "(again)" `[written]`.

**Process and craft advice gets bolded imperative bullets, not diagrams** — with the hub exception in §4: every module, process modules included, still ships at least one redrawable mechanism figure, because the figure is boss-fight material. The supporting fact is a count, not a quote: `2019-04-25-recipe.markdown` is 3,903 words with zero figures. (The older draft cited an aphorism here — "Process gets typography; mechanism gets diagrams." — which appears nowhere in the corpus and was this spec's own invention wearing a `[written]` tag.)

**Style rules.**
- **All strokes and fills come from CSS variables**: `var(--ink)`, `var(--line)`, `var(--grid)`, `var(--panel)`, `var(--muted)`, and `var(--s1)`/`var(--s2)` for chart series (a colorblind-validated pair). **Never literal black or white.** The site ships a theme toggle and dark tokens (`--bg:#0d1117`, `--panel:#161c24`), so a hard-coded black stroke is invisible in dark mode and a white fill is a glaring slab.
- Keep the primitive spirit — thin strokes, no shadows, no gradients, hand-written coordinates. The crudeness signals the reader could draw it too `[written]`. But use `rx=6`/`rx=8` to match the established house style; the older draft's "no rounded corners" would make new figures clash with every existing one.
- `role="img"` and a descriptive `aria-label` on every `<svg>`, and a `^ caption` line immediately after `</svg>`.
- Grow figures by accretion, never redesign: the earlier boxes do not move when you add one `[written]`.
- Every figure gets a **"how to read this"** line naming the failure signature — "So in the Boolean tensor, you get a white" if true, black if false; hunt for a fully white column `[ep4]`.
- Pair each diagnostic figure with a numeric health threshold in a small badge, so the reader leaves with a number, not a vibe: "Our saturation is roughly 5%, which is a pretty good number." `[ep4]`
- Label points with the actual thing, not a legend, and name the outliers individually — "Q is kind of treated as an exception" `[ep3]`.
- State exactly what the picture licenses and no more: "And it's definitely not random, and these embeddings make sense." `[ep3]`
- Use the figure as a **debugging instrument**: add a "scrutinize this" paragraph pointing at an anomaly in your *own* figure, and make the next section the redesign it forces `[ep2]`.
- Keep one toy dimension small on purpose so an honest figure exists at all, then scale up — "But once I make this greater than 2, we won't be able to visualize them." `[ep3]`
- Deliberately show an overwhelming figure when scale is the point, and react to it in the text instead of pretending it is readable: "we've built up now which is kind of excessive" `[ep1]`.
- Say when a node in the diagram is fake/pedagogical and not a real object `[ep1]`. Ship healthy and broken versions of the same figure side by side `[ep4]`.
- One decorative image (mascot, the code as an object) is allowed, declared as doing no explanatory work: `![awww](puppy.jpg)` `[written]`.
- Prescribe figures the reader should make themselves: "visualize *exactly* what goes into your network" `[written]` (recipe, "visualize just before the net").

---

## 6. Anti-patterns

Each is the negation of a move above.

1. **Undeflated jargon.** A term appearing before its mechanism, or defined in a glossary/footnote instead of in the same sentence as its first use. Violates move 4. The tell: a paragraph the reader cannot parse without scrolling. Note the `## Concepts` reconciliation in House constraints — a forward-pointing map is not a violation; a lesson delivered in Concepts is.
2. **Magic imports and magic numbers.** `from framework import Evaluator` on line 1, or a threshold of `0.6` used without confession. Contrast: "But what we have here now is all these magic numbers, … Like, where do I come up with this?" `[ep4]`
3. **The 30-line miracle snippet.** "Numerous libraries and frameworks take pride in displaying 30-line miracle snippets that solve your data problems, giving the (false) impression that this stuff is plug and play." `[written]` If your module reads like `model = SuperCrossValidator(...)` + `# conquer world here`, you have written the strawman, not the lesson.
4. **Only the final clean version.** No manual pass, no Strategy #1, no expanded flat version, no failed experiment kept in the tally. The reader gets the answer and none of the reasons.
5. **Sanitized errors.** Paraphrasing a traceback, or fixing a bug off-page and presenting the happy path. Violates move 9; the "why it still seemed to work" paragraph is the part that gets skipped and it is the most valuable one. This is about wrong *results*, not staged verbal stumbles — see the Voice table.
6. **Asserted failure modes.** "Be careful, the judge can be position-biased." Without the sweep, the printed spread, and the symptom table, this is advice, not data. Violates move 10.
7. **Unprinted claims.** "This is equivalent to the standard metric" / "the loss decreases" / "the results were comparable". Never claim an equivalence you did not print; never paraphrase a trace; never paste a trace no committed script can reproduce.
8. **Fake enthusiasm.** Exclamation marks with no number under them, hype adjectives, "powerful", "revolutionary". His enthusiasm is always welded to a printed artifact — "// -5.87! exciting." `[written]` — and his default register toward his own work is deflationary: "this neural network library built on top of the autograd engine is like a joke" `[ep1]`. A takeaway line that overstates is this anti-pattern wearing move 16's clothes.
9. **Cherry-picked output.** Showing only the good samples. The correct move is the honest one plus a reaction: "It doesn't look like much, but from the perspective of a model like ChatGPT, your conversation with it is just a funny looking "document"." `[written]`
10. **Learning-objective boxes and roadmap bullets.** Replaced by the running artifact and the contract paragraph. Never let the opening paragraph contain a formal definition `[ep2]`. **Scoped:** `## Why this module` is required and states a gap with evidence; one human sentence on why anyone would want the artifact is sanctioned in the cold open. What is banned is the bulleted objectives box and the motivational preamble — including a Recap block relocated to the end and doing the same job.
11. **"As we know" / "obviously" / "it is trivial to see."** Also unrestated back-references ("as we saw earlier") and pronouns crossing a section boundary. Violates the infinitely-patient-tutor standard `[public]`.
12. **Metaphor stacking.** A second competing analogy introduced later, or an analogy without numbers inside it, or one that never gets the bridge sentence back to the mechanism. One substrate per module — and it stays out of the identifiers `[written]`.
13. **Tensor-first / abstraction-first.** Vectorized code before a scalar version has been run and verified; a general helper before the hardcoded special case works. "I like to write a very specific function to what I'm doing right now, get that to work, and then generalize it later making sure that I get the same result." `[written]`
14. **Unbracketed metrics.** A headline number with no chance-level, no floor, no production counterpart — or, worse, no n and no spread. Violates moves 14 and 18.
15. **Disclaimers at the top instead of fences inline.** A blanket "this is simplified" header, then no in-place marking of *which* thing was simplified and why. Fence at the moment, with the reason attached; a scope note near the end listing what was deliberately left out beats a disclaimer at the top. (Unquoted: this is our editorial rule. The older draft attributed a sentence to `[ep1]` that does not exist in the transcript — the word "disclaimer" appears nowhere in it. The genuine ep1 fence is "never be doing any of this in production it's real just for them for pedagogical reasons".)
16. **Decorative figures.** A diagram that shows nothing in two states, enumerates nothing closed, and defines no frame — or one with no "how to read this" line and no threshold badge. Also: hard-coded black/white fills, a missing `aria-label`, or a missing `^ caption`.
17. **Recap-as-conclusion.** Ending on a summary rather than a discharged promise, named knobs, a number to beat, and a send-off. Also: no Errata, no "what we did not settle", no Boss fight, no ledger entry.
18. **Many knobs for the reader to set.** If the reader must set five numbers to run your example, you have shifted your design problem onto them. Expose one primary dial per experiment and derive the rest — and never more than three across the module. (Unquoted: our rule. The older draft carried an invented `[public]` quote here. The genuine adjacent line is "These are the same knobs that matter at scale." `[written]`, which supports move 20's hand-off, not this constraint.)
19. **Frictionless edutainment.** Sizing the module for a scroll instead of a sitting, substituting jokes for the work, or removing the manipulation steps. "The people watching enjoy thinking they are learning (but actually they are just having fun). … But as far as learning goes, this is a trap." `[public]` The reader should finish tired and correct: "You want the mental equivalent of sweating." `[public]`
20. **Grind.** The mirror of 19, and the newer failure mode. Firing all sixteen moves at all eighteen steps, stacking five closers at every boundary, re-rendering the tally when nothing changed, and manufacturing an aphorism on a word count. Mechanical repetition is what kills the voice being cloned. The moves are a palette with a mandatory core; the budgets in House constraints are the enforcement.
21. **Ownerless examples.** A generic invented toy where doctrine #4 requires the reader's own artifacts — and an absorbed own-artifact with no `Source:` line or no de-personalisation. Violates move 19.

---

## Rejected critique items

Five items are rejected or amended. Everything else in both reports was verified against the sources and applied.

**1. Rejected — "MISQUOTE (inserted word)" on the micrograd README figure quote.** The evidence critic claims the leading "it" in "it shows both the data (left number in each node) and the gradient (right number in each node)" is this spec's insertion, and that the README reads "`![2d neuron](gout.svg)` shows both the data…". The local copy of the README reads, verbatim: "…arrived at by calling `draw_dot` on the code below, and **it shows both the data (left number in each node) and the gradient (right number in each node)**." The "it" is in the source. The quote stands unchanged. The *other* half of that finding was correct and is applied: the tag is now `[written]` only, with an explicit note that the micrograd README sits outside the original seven-source audit set.

**2. Rejected in part — "delete the Feynman epigraph."** The critic verified it is absent from the seven audited sources and from the micrograd README, and concluded there is no evidence it belongs in a Karpathy-sourced spec. That conclusion is wrong: the line is genuine Karpathy, in a source neither report searched. `_posts/2021-06-21-blockchain.markdown` reads "And in the spirit of "what I cannot create I do not understand", what better way to do this than implement it from scratch?". So the epigraph is re-sourced and re-tagged `[written]` rather than deleted. The critic *was* right about the specific string: the form the spec used — "What I cannot create, I do not understand. -Richard Feynman" — with title-case, a comma, and an attribution line, is not Karpathy's wording anywhere, so that form is gone.

**3. Amended — "SPURIOUS ELLIPSES (5 instances)."** The five marks were removed, so the fix lands. But the finding as stated — that they violate the spec's own convention — was not correct. The original convention read "`…` marks an elided transcript line-join or omitted clause", which explicitly licensed marking a line-join where nothing was removed. The real defect was the convention, which made a genuine elision indistinguishable from a cosmetic one. Both are now fixed: the convention is tightened to *omitted words only*, and the five cosmetic marks are gone. In the Move 13 tally quote only the first `…` survives, because it alone elides real words ("when we started.").

**4. Amended — the "Base Case" heading level.** The capitalisation fix is correct and applied. The critic quotes the source heading as `#### Base Case: Single Gate in the Circuit`; it is `### Base Case: Single Gate in the Circuit` at `nntutorial.md:26`. Moot for output either way, since `#### ` does not render in this hub and `### ` does.

**5. Deferred, not rejected — patching `tools/build_site.py`.** The translation critic's preferred fix for the three unrenderable devices is to add a blockquote branch, an `<h5>` branch, and a raw-HTML passthrough for `<details>` to `md_to_html`. Changing the hub's build tooling is outside the scope of a spec revision, and a spec must be followable against the renderer that exists today. So the spec is written renderer-legal as-is: the takeaway line is a bolded standalone sentence, the hidden answer uses one of three text-native devices, and the Recipe variant's headings drop to `### `. The patch is recorded in House constraints as an optional follow-up with the switch-back conditions stated, so the change is a two-line spec edit if someone does it.

**One clarification, no change.** The translation critic notes that Move 5's query/key/value evidence quote "illustrates a different rule than the ruler example it is paired with". The quote does correctly evidence one clause of the rule — the one-line quoted job description. The mismatch was that the ruler example never demonstrated that clause. Fixed by writing ruler-substrate job descriptions into the example, not by dropping the quote.
