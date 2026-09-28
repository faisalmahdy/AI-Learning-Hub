---
id: grounded-inter-01
title: Verify each claim in the answer against the retrieved passages — a model hallucinates a claim no passage supports even when retrieval succeeded
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: It is tempting to think retrieval-augmented generation is safe once the retriever returns relevant passages — the facts are in the context, so the answer must come from them. But the generation step is still a language model, and handed the right passages it will answer from them and then, just as fluently, add a statement that was not in any of them: a fact it remembers, a plausible average, a smooth continuation. That extra statement arrives with the same confidence as the supported ones and, because the system is "grounded in retrieval," with an implicit citation it does not deserve. Crucially this is not a retrieval failure: on the fixture the passages support two of the answer's three claims (a side effect and a dose), so the retriever did its job, yet the third claim — "drug_x is safe during pregnancy" — appears in no passage and is a hallucination. A relevance floor or a better ranker cannot catch a claim the model invented out of good context, because the defect is in the answer, not the retrieval. The fix is a groundedness check that is a separate step: decompose the answer into atomic claims and verify each against the retrieved passages, keeping the supported claims and flagging the unsupported one for dropping, re-answering, or human review. On this fixture the naive path ships all three claims including the false one; the grounded path keeps the two supported claims and flags the third. The rule: an answer is grounded only if every claim in it is supported by the retrieved context, so check claim by claim rather than trusting that good retrieval produced a faithful answer.
eli5: Imagine you ask a friend to answer a question using only the pages you handed them, and they give you three facts. Two of them really are on the pages — great. But the third one they just remembered from somewhere else and said it in the same confident voice, so it sounds like it came from the pages too. If you don't check, you can't tell which facts actually came from the pages and which your friend made up. The fix is to go through their answer one fact at a time and point to where on the pages each fact is written; the one you can't find anywhere is the made-up one, and you set it aside. Handing them the right pages didn't stop them from adding something extra — only checking does.
---

## Why this module

The promise of retrieval-augmented generation is that the answer is backed by real sources: fetch the relevant passages, put them in the context, and the model answers from them instead of from its fallible memory. That promise is only half-kept by retrieval. Retrieval decides what the model can see; it does not decide what the model says.

The gap is the generation step. A language model handed perfect context will use it — and will still, in the same answer, produce a sentence that no passage contains. It is not being adversarial; producing fluent, plausible text is what it does, and a plausible sentence that happens to be unsupported is indistinguishable, on the surface, from a supported one. The result is a hallucination wearing the credibility of the retrieved sources.

This module builds exactly that case: passages that support most of an answer, and an answer that adds one claim they do not support. The naive path ships all of it. Then it adds the missing step — check each claim against the passages — and shows the grounded path keeping the supported claims and flagging the invented one. The key point is that retrieval succeeded; groundedness is a separate check that the retriever, however good, cannot perform.

**Good retrieval puts the right facts in front of the model but does not stop the model from adding a wrong one, so a faithful answer requires verifying the answer, not just trusting the context.**

## Concepts

Separate two questions that "grounded" runs together. Did the retriever find relevant context? That is a retrieval question, answered by the passages. Does the answer say only what the context supports? That is a generation question, answered by the answer. A system can pass the first and fail the second, and the second is the one a user actually cares about, because it is the answer they read.

Failing the second looks like this: the model composes an answer that is mostly drawn from the passages and includes one claim that is not. That claim can come from the model's parametric memory (a fact it learned in training), from over-generalizing the passages (they mention a related fact and it extrapolates), or from sheer fluency (the sentence is a natural continuation). Whatever the source, it is asserted with no support in the retrieved context, and nothing about its wording marks it as different from the supported claims around it.

A relevance floor, a better reranker, more passages — none of these can catch it, because they all operate on the retrieval side, and the defect is on the generation side. You could retrieve the single most perfect passage in the world and the model could still append an unsupported sentence to its answer. The only thing that catches an unsupported claim is checking the claims against the context.

That check is claim-level, not answer-level. Asking "is this answer grounded?" as one yes/no is too coarse — an answer with four supported claims and one invented one is neither fully grounded nor fully hallucinated. Decomposing the answer into atomic claims and checking each against the passages localizes the problem: it keeps the four, flags the one, and tells you exactly which sentence to drop or re-derive.

<svg role="img" aria-label="A pipeline: retrieve passages, then generate an answer, then a groundedness check that splits the answer's claims into supported (kept) and unsupported (flagged). The check is drawn as a separate stage after generation, not part of retrieval" viewBox="0 0 640 200">
<rect x="20" y="80" width="90" height="40" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="65" y="104" fill="var(--ink)" font-size="10" text-anchor="middle">retrieve</text>
<line x1="110" y1="100" x2="145" y2="100" stroke="var(--line)" stroke-width="1"/>
<polygon points="145,100 137,95 137,105" fill="var(--line)"/>
<rect x="145" y="80" width="90" height="40" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="190" y="104" fill="var(--ink)" font-size="10" text-anchor="middle">generate</text>
<line x1="235" y1="100" x2="270" y2="100" stroke="var(--line)" stroke-width="1"/>
<polygon points="270,100 262,95 262,105" fill="var(--line)"/>
<rect x="270" y="76" width="110" height="48" fill="var(--panel)" stroke="var(--ink)" stroke-width="1.5" rx="6"/>
<text x="325" y="96" fill="var(--ink)" font-size="10" text-anchor="middle">groundedness</text>
<text x="325" y="110" fill="var(--muted)" font-size="10" text-anchor="middle">check per claim</text>
<line x1="380" y1="88" x2="430" y2="66" stroke="var(--s1)" stroke-width="1"/>
<line x1="380" y1="112" x2="430" y2="134" stroke="var(--s2)" stroke-width="1"/>
<rect x="430" y="48" width="190" height="34" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="525" y="69" fill="var(--ink)" font-size="10" text-anchor="middle">supported claims → keep</text>
<rect x="430" y="118" width="190" height="34" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="6"/>
<text x="525" y="139" fill="var(--ink)" font-size="10" text-anchor="middle">unsupported claim → flag</text>
</svg>
^ Groundedness is a stage after generation, splitting the answer's claims into supported and unsupported — a check the retrieve and generate stages cannot do for it.

**Retrieval and groundedness are different guarantees at different stages: the retriever certifies the context is relevant, and only a claim-level check certifies the answer used it faithfully.**

## Worked example

The fixture is the retrieved passages, as the facts they state, and the candidate answer, broken into atomic claims.

```json filename=modules/context-and-retrieval/code/grounded-inter-01/grounded.json:3-11 COMPLETE
  "passages": {
    "p1": ["drug_x causes nausea", "drug_x causes headache"],
    "p2": ["drug_x dose is 200mg daily"]
  },
  "answer_claims": [
    "drug_x causes nausea",
    "drug_x dose is 200mg daily",
    "drug_x is safe during pregnancy"
  ]
```

The passages' facts are the only things an answer may assert.

```python filename=modules/context-and-retrieval/code/grounded-inter-01/grounded.py:30-35 COMPLETE
def supported_facts(passages):
    """The set of facts actually stated by the retrieved passages -- the only things an answer may assert."""
    facts = set()
    for passage in passages.values():
        facts.update(passage)
    return facts
```

A claim is grounded only if some passage states it — modeled here as fact membership, a stylized stand-in for a real entailment check.

```python filename=modules/context-and-retrieval/code/grounded-inter-01/grounded.py:38-40 COMPLETE
def is_supported(claim, passages):
    """A claim is grounded iff some retrieved passage states it (stylized entailment: exact-fact membership)."""
    return claim in supported_facts(passages)
```

The grounded answer keeps only the supported claims.

```python filename=modules/context-and-retrieval/code/grounded-inter-01/grounded.py:43-45 COMPLETE
def grounded_answer(claims, passages):
    """Keep only the claims the passages support -- the answer that says only what the sources say."""
    return [c for c in claims if is_supported(c, passages)]
```

Checking the candidate answer marks two claims supported and one unsupported.

```text filename=grounded.py --answer
ANSWER — the candidate answer's claims against the retrieved passages
--------------------------------------------------------------------
  [supported] drug_x causes nausea
  [supported] drug_x dose is 200mg daily
  [UNSUPPORTED] drug_x is safe during pregnancy
--------------------------------------------------------------------
  the naive path ships every claim, including the one no passage supports
```

The nausea and dose claims are in the passages; the pregnancy-safety claim is in none. The naive path, trusting that good retrieval produced a faithful answer, ships all three. The grounded path keeps the two and flags the one.

```text filename=grounded.py --grounded
GROUNDED — keep the supported claims, flag the unsupported ones
--------------------------------------------------------------------
  kept (grounded answer):
    - drug_x causes nausea
    - drug_x dose is 200mg daily
  flagged as ungrounded: ['drug_x is safe during pregnancy']
--------------------------------------------------------------------
  the answer now asserts only what the retrieved passages actually say
```

The figure shows the answer's three claims checked against the passages.

<svg role="img" aria-label="Three answer claims each checked against the passages. Nausea and 200mg dose are marked supported with the passage that contains them. Safe during pregnancy is marked unsupported with no passage, flagged as a hallucination" viewBox="0 0 640 210">
<text x="60" y="30" fill="var(--ink)" font-size="11">answer claims → checked against passages</text>
<rect x="40" y="46" width="330" height="34" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="5"/>
<text x="54" y="67" fill="var(--ink)" font-size="11">drug_x causes nausea</text>
<text x="500" y="67" fill="var(--s1)" font-size="10" text-anchor="middle">supported (p1)</text>
<rect x="40" y="88" width="330" height="34" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="5"/>
<text x="54" y="109" fill="var(--ink)" font-size="11">drug_x dose is 200mg daily</text>
<text x="500" y="109" fill="var(--s1)" font-size="10" text-anchor="middle">supported (p2)</text>
<rect x="40" y="130" width="330" height="34" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="5"/>
<text x="54" y="151" fill="var(--ink)" font-size="11">drug_x is safe during pregnancy</text>
<text x="500" y="147" fill="var(--s2)" font-size="10" text-anchor="middle">no passage</text>
<text x="500" y="160" fill="var(--s2)" font-size="10" text-anchor="middle">→ hallucination</text>
</svg>
^ Two claims point to a passage that supports them; the third points to nothing, so it is flagged rather than shipped.

**The unsupported claim is not a retrieval miss — the retriever surfaced passages that back two-thirds of the answer — it is a claim the generator added, catchable only by checking the answer against the context.**

## Build

The self-test pins the crucial pair: the answer contains an unsupported claim, and retrieval nonetheless succeeded — so the defect is in the answer, not the retrieval.

```python filename=modules/context-and-retrieval/code/grounded-inter-01/grounded.py:86-93 COMPLETE
    has_unsupported_claim = len(flagged) > 0
    print("  the answer contains an unsupported claim = %s (%s)" % (has_unsupported_claim, flagged))

    retrieval_succeeded = len(kept) > 0
    print("  retrieval succeeded -- passages support other claims = %s (%d of %d supported)" % (retrieval_succeeded, len(kept), len(claims)))

    naive_ships_unsupported = any(c in claims for c in flagged)
    print("  the naive (unchecked) answer ships the unsupported claim = %s" % naive_ships_unsupported)
```

The remaining flags confirm the grounded answer drops the unsupported claim and keeps every supported one. All five pass.

```text filename=grounded.py --check
SELF-TEST — the answer contains an unsupported claim though retrieval succeeded, the naive path ships it, and the grounded check flags it while keeping the supported claims
----------------------------------------------------------------------------------------------------------------
  the answer contains an unsupported claim = True (['drug_x is safe during pregnancy'])
  retrieval succeeded -- passages support other claims = True (2 of 3 supported)
  the naive (unchecked) answer ships the unsupported claim = True
  the grounded answer drops every unsupported claim = True
  the grounded answer keeps every supported claim = True (2 kept)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  has_unsupported_claim=True  retrieval_succeeded=True  naive_ships_unsupported=True  grounded_drops_unsupported=True  grounded_keeps_supported=True
```

**"Retrieval succeeded — 2 of 3 supported" is the flag that names the whole lesson: the passages were good, so no improvement to retrieval would have prevented the third claim, and only a groundedness check does.**

## Definition of done

You are done when a retrieval-augmented answer is verified claim by claim against the retrieved passages before it is shown, and any claim no passage supports is dropped, re-derived, or surfaced for review rather than shipped.

The pipeline adds two steps after generation. Decompose the answer into atomic claims — individual, checkable statements, since a paragraph is too coarse to verify as a unit. Then check each claim for support in the retrieved passages, using an entailment or natural-language-inference model (or an LLM judge prompted to answer "is this claim supported by these passages, yes or no, with the supporting span") rather than the exact-match stand-in this module uses. On an unsupported claim you have choices matched to the stakes: drop it and answer with only the grounded claims, force a re-generation constrained to the passages, ask the model to cite a span for every sentence and reject sentences it cannot cite, or route the answer to a human. The same machinery gives you a citation for each kept claim as a by-product, since checking support means finding the passage that provides it.

<svg role="img" aria-label="A flow: decompose the answer into atomic claims, check each against the passages with an entailment model, and route by result. Supported claims are kept and cited; an unsupported claim is dropped, re-answered, or reviewed" viewBox="0 0 640 190">
<rect x="20" y="76" width="120" height="44" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="80" y="94" fill="var(--ink)" font-size="10" text-anchor="middle">answer →</text>
<text x="80" y="109" fill="var(--muted)" font-size="10" text-anchor="middle">atomic claims</text>
<line x1="140" y1="98" x2="180" y2="98" stroke="var(--line)" stroke-width="1"/>
<polygon points="180,98 172,93 172,103" fill="var(--line)"/>
<rect x="180" y="76" width="130" height="44" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="245" y="94" fill="var(--ink)" font-size="10" text-anchor="middle">entailment check</text>
<text x="245" y="109" fill="var(--muted)" font-size="10" text-anchor="middle">vs passages</text>
<line x1="310" y1="86" x2="360" y2="64" stroke="var(--s1)" stroke-width="1"/>
<line x1="310" y1="110" x2="360" y2="132" stroke="var(--s2)" stroke-width="1"/>
<rect x="360" y="46" width="260" height="36" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="490" y="68" fill="var(--ink)" font-size="10" text-anchor="middle">supported → keep + cite the span</text>
<rect x="360" y="114" width="260" height="36" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="6"/>
<text x="490" y="136" fill="var(--ink)" font-size="10" text-anchor="middle">unsupported → drop / re-answer / review</text>
</svg>
^ Decompose, check each claim against the passages, and route by result — keeping and citing the supported claims, stopping the unsupported one.

**A groundedness check turns "trust me, it's from the sources" into "here is the source for each claim," and the claim it cannot source is exactly the one that should never have shipped.**

## Boss fight

Your turn: make the hallucination subtle instead of obvious. Change the third claim to "drug_x causes drowsiness" — a claim of the same kind as the supported ones (a side effect), phrased identically, but still in no passage. The exact-match check still flags it, but notice how much harder a human skim would find it: it sits among real side effects, reads like them, and only a check against the actual passages reveals that this particular side effect was never stated. This is why groundedness must be mechanical and claim-level — the dangerous hallucinations are the ones that look exactly like the supported claims, and a human reviewer scanning for something that "looks wrong" will not find them.

Then confront the check's own hard part: real support is not exact-match. Change a supported claim's wording to "drug_x can make you feel nauseous" — the same fact as "drug_x causes nausea," but not the identical string, so the exact-match stand-in wrongly flags it as unsupported. A production groundedness check must use entailment, not string equality, so a paraphrase of a supported fact counts as supported while a genuinely new fact does not — and that is exactly where it gets difficult, because the entailment model has its own errors: too strict and it flags faithful paraphrases (annoying but safe), too loose and it passes a claim the passages only vaguely relate to (dangerous). The exact-match model here makes the mechanism clear; the engineering is in the entailment step that decides "does this passage actually support this claim," which is the real frontier of faithful RAG.

**The exact-match check shows the shape of the fix, but the substance is entailment — deciding when a passage truly supports a claim — and that judgment, not the retrieval, is where a faithful RAG system is won or lost.**

## External resources

The RAGAS framework and its "faithfulness" metric operationalize exactly this — decompose the answer into claims and score what fraction are entailed by the retrieved context — and are a practical starting point for measuring groundedness.

Research on attributed question answering and "citation" evaluation (for example Google's work on attributable-to-identified-sources, AIS) formalizes the requirement that every statement in an answer be supported by a cited source.

The natural-language-inference literature (SNLI, MNLI, and entailment models built on them) supplies the entailment check that a real groundedness step needs in place of the exact-match stand-in used here.
