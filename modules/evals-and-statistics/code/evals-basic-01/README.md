# evals-basic-01 — three graders, one set of 30 answers

30 held-out questions against the **Query workflow** of the AI Engineering LLM Wiki
(209 concept pages, 8 domains), graded three ways so you can watch the first two
graders fail for reasons you can name.

Stdlib Python 3, no network, no API keys, no model calls. `cases.json` stores the
answers being graded, so every run prints the same numbers. Read
`_meta.how_answers_were_produced` in `cases.json` before quoting any of them.

## One command per strategy

```
python3 eval.py --strategy exact      # string identity vs the reference
python3 eval.py --strategy overlap    # token-overlap F1 vs the same reference
python3 eval.py --strategy rubric     # six boolean checks per case
python3 eval.py --strategy all        # all three side by side, with disagreements
python3 eval.py --check               # re-derive the rubric score by a second route
```

Run from this directory (the script finds `cases.json` next to itself).

## The six checks

| id | name | dimension |
|----|------|-----------|
| C1 | cites-valid-slug | grounding — at least one `[[slug]]`, none invented |
| C2 | cites-required-page | grounding — did it route to the right page |
| C3 | key-facts-present | correctness — every fact the answer must contain |
| C4 | no-known-error | correctness — the specific wrong claim this question attracts |
| C5 | refusal-honesty | honest-refusal — refuses exactly when the wiki cannot answer |
| C6 | well-formed | completeness — length band, plus a `Sources:` line |

Rubric score is checks passed over `6 × n`. `clean_cases` counts the answers that
passed all six — the harsher and more useful number.

## Case spread

10 factual · 10 synthesis-across-pages · 10 not-answerable-from-the-wiki.
Every case names the lab file it derives from in `source_file`. Six cases are
deliberately planted — F04, F09, S07, S10, U02, U08 — described in the five
`_meta.planted_cases` entries, because S10 and U02 share one entry.

## Source lines

- Source: faisalmahdy/ai-engineer-learning — `CLAUDE.md` (section 4: the Ingest / Query / Lint contract; section 6 rule 7: date volatile facts)
- Source: faisalmahdy/ai-engineer-learning — `schema/relation-types.md`
- Source: faisalmahdy/ai-engineer-learning — `wiki/tiers.md`
- Source: faisalmahdy/ai-engineer-learning — `wiki/index.json`
- Source: faisalmahdy/ai-engineer-learning — `wiki/graph.json`
- Source: faisalmahdy/ai-engineer-learning — `wiki/MASTER-CONCEPT-LIST.md`
- Source: faisalmahdy/ai-engineer-learning — `wiki/source-index.md`
- Source: faisalmahdy/ai-engineer-learning — `llms.txt`
- Source: faisalmahdy/ai-engineer-learning — `raw/sources-manifest.json`
- Source: faisalmahdy/ai-engineer-learning — `raw/transcripts/`
- Source: faisalmahdy/ai-engineer-learning — `wiki/concepts/` (26 named pages; each case names its own in `source_file`)
- Source: faisalmahdy/second-brain-through-agents — `raw/topics/agent-systems/second-brain-evaluation/2026-07-04-10-persona-usage-harness-verdicts.md` (the hand-run rubric harness this script mechanizes)
