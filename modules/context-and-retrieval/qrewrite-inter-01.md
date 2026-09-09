---
id: qrewrite-inter-01
title: Rewrite a follow-up into a self-contained query before retrieving — a pronoun like "it" has no entity to match
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: Retrieval in a conversation has a problem retrieval on a single question does not: the query is often not self-contained. A user asks "Tell me about the Falcon 9 rocket," then follows up with "How much does it cost per launch?" To a human the second question obviously means the Falcon 9, but the words taken alone do not say so — the entity is carried only by the pronoun "it." A retriever embeds or keyword-matches the text it is given, and that text contains "cost" and "launch" and no mention of the Falcon 9. So it cannot distinguish a Falcon-9-specific cost document from a generic rocket-cost document — both match "cost" and "launch" equally — and it may return the wrong one, or a tie it breaks arbitrarily. The fix is conversational query rewriting: before retrieving, rewrite the follow-up into a stand-alone query by resolving its references against the history — replace "it" with the entity it refers to, carry forward the subject. "How much does it cost per launch?" becomes "How much does the Falcon 9 rocket cost per launch?", which now carries the entity terms the retriever needs to match the right document. This differs from query expansion, which broadens an already-self-contained query with synonyms; rewriting fills in what the follow-up left implicit from the dialogue. On a fixture where the follow-up's own terms are only {cost, launch}, raw retrieval ties the Falcon-9 cost doc with the generic rocket-cost doc (both score 2), while rewriting to include the carried-over entity {falcon, 9, rocket} makes the Falcon-9 doc win 5 to 3.
eli5: Imagine you tell a librarian "I want a book about the Falcon 9 rocket," and then, pointing at nothing, you ask "how much does it cost?" A librarian who only heard the second sentence — with no memory of the first — hears "how much does IT cost?" and has no idea what "it" is, so they can't tell you the Falcon 9 book from any random rocket book. The trick is to fix the question before you hand it over: turn "how much does it cost?" into "how much does the Falcon 9 rocket cost?" so the question stands on its own. Now even a forgetful librarian finds exactly the right book, because you put the name back into the question.
---

## Why this module

A conversation carries its subject forward silently, and a retriever cannot hear that. When a person asks a follow-up, they drop the entity to a pronoun or omit it entirely, trusting the listener to remember — and a human does. But the retrieval step sees only the query string it is handed, with none of the dialogue that gave the pronoun its meaning. So a perfectly clear follow-up, to a person, arrives at the retriever as a fragment that has lost its subject, and the retriever matches on what is left: the generic content words, which point at generic documents.

A retriever embeds or keyword-matches the text it is given, and for the follow-up "How much does it cost per launch?" that text contains the content terms "cost" and "launch" and no mention of the Falcon 9 at all. So the retriever cannot distinguish a Falcon-9-specific cost document from a generic rocket-cost document — both match "cost" and "launch" equally — and it may return the wrong one, or a tie it resolves arbitrarily.

The fix is conversational query rewriting: before retrieving, rewrite the follow-up into a stand-alone query by resolving its references against the conversation history — replace "it" with the entity it refers to, carry forward the subject. "How much does it cost per launch?" becomes "How much does the Falcon 9 rocket cost per launch?", which now contains the entity terms the retriever needs. This module runs retrieval both ways.

**Before retrieving in a multi-turn conversation, rewrite a follow-up into a self-contained query by resolving its references against the history (replace "it" with the entity it refers to), because a retriever matches only the text it is given, and a follow-up whose entity is a pronoun has no term to match — so it cannot distinguish the specific document from a generic one.**

## Concepts

**The raw query is the follow-up's own terms; the rewritten query merges in the entity carried from the conversation** — the one operation that resolves the pronoun.

```python filename=modules/context-and-retrieval/code/qrewrite-inter-01/qrewrite.py:49-60 COMPLETE
def raw_query(data):
    """The follow-up's own content terms -- no entity, because it was a pronoun."""
    return list(data["follow_up_terms"])


def rewritten_query(data):
    """Resolve the reference: merge the entity terms carried from the conversation into the follow-up."""
    terms = list(data["follow_up_terms"])
    for t in data["history_terms"]:
        if t not in terms:
            terms.append(t)
    return terms
```

**Retrieval scores each document by keyword overlap and ranks them** — a stand-in for the embedding similarity a real retriever computes, with the same dependence on the query carrying the right terms.

```python filename=modules/context-and-retrieval/code/qrewrite-inter-01/qrewrite.py:63-70 COMPLETE
def score(query_terms, doc_terms):
    """Keyword-overlap score: how many query terms the document contains."""
    return sum(1 for t in query_terms if t in doc_terms)


def rank(data, query_terms):
    scored = [(doc, score(query_terms, terms)) for doc, terms in data["documents"].items()]
    return sorted(scored, key=lambda kv: (-kv[1], kv[0]))
```

<svg role="img" aria-label="A conversation: turn 1 says Falcon 9 rocket, turn 2 says how much does it cost; the retriever sees only turn 2, where the entity is the pronoun 'it', so it receives cost and launch with no entity" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the retriever sees the follow-up alone — the entity is a pronoun</text>
  <rect x="14" y="22" width="180" height="16" fill="none" stroke="var(--muted)"/><text x="20" y="34" fill="var(--ink)" font-size="7">turn 1: "the Falcon 9 rocket"</text>
  <text x="200" y="34" fill="var(--s1)" font-size="6">entity established</text>
  <rect x="14" y="46" width="180" height="16" fill="none" stroke="var(--ink)"/><text x="20" y="58" fill="var(--ink)" font-size="7">turn 2: "how much does IT cost?"</text>
  <text x="200" y="58" fill="var(--s2)" font-size="6">entity = pronoun</text>
  <line x1="14" y1="72" x2="286" y2="72" stroke="var(--grid)"/>
  <text x="14" y="88" fill="var(--muted)" font-size="7">retriever receives:</text>
  <rect x="120" y="78" width="90" height="16" fill="var(--s2)"/><text x="126" y="90" fill="var(--panel)" font-size="7">{cost, launch}</text>
  <text x="14" y="110" fill="var(--muted)" font-size="6">no 'falcon', no '9' — nothing to tell the specific doc from a generic one</text>
</svg>
^ Turn 1 establishes the entity, but the retriever only receives turn 2, where the entity is the pronoun "it" — so it gets {cost, launch} with no entity term, and cannot tell the Falcon-9 document from a generic rocket one.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/qrewrite-inter-01/qrewrite.py

The fixture is three documents, the entity terms established in turn 1, and the follow-up's own terms.

```json filename=modules/context-and-retrieval/code/qrewrite-inter-01/qrewrite.json:3-9 COMPLETE
  "documents": {
    "d1_falcon9_cost": ["falcon", "9", "rocket", "cost", "launch", "price"],
    "d2_generic_rocket_cost": ["rocket", "cost", "launch", "overview"],
    "d3_falcon9_specs": ["falcon", "9", "rocket", "specifications", "engine"]
  },
  "history_terms": ["falcon", "9", "rocket"],
  "follow_up_terms": ["cost", "launch"]
```

Run `--retrieve`.

```text filename=--retrieve
RETRIEVE — keyword-overlap scores, raw follow-up vs rewritten query
------------------------------------------------------------------
  raw query      = ['cost', 'launch']
    d1_falcon9_cost          2
    d2_generic_rocket_cost   2
    d3_falcon9_specs         0
  rewritten query = ['cost', 'launch', 'falcon', '9', 'rocket']
    d1_falcon9_cost          5
    d2_generic_rocket_cost   3
    d3_falcon9_specs         3
------------------------------------------------------------------
  raw top: ('d1_falcon9_cost', 2) ; rewritten top: ('d1_falcon9_cost', 5)
```

Read the two score blocks. On the raw follow-up, the Falcon-9 cost document (d1) and the generic rocket-cost document (d2) both score 2 — they each contain "cost" and "launch", and the query has nothing else to offer, so the retriever cannot tell them apart. It is a tie, and the only reason d1 appears on top is an arbitrary alphabetical tie-break; flip the document ids and the generic doc wins. The retriever is guessing. On the rewritten query, which now carries "falcon", "9", and "rocket" from the conversation, d1 scores 5 while d2 and d3 score 3 — d1 wins decisively, because it is the only document that matches both the content terms (cost, launch) and the entity terms (falcon, 9). The rewrite did not make the retriever smarter; it gave the retriever the words it needed, which the follow-up had left in the previous turn.

## Build

The rewrite is a single, mechanical resolution step: pull the entity out of the history and put it back into the query.

```text filename=--rewrite
REWRITE — making the follow-up self-contained
------------------------------------------------------------
  turn 1 established the entity: ['falcon', '9', 'rocket']
  follow-up 'How much does IT cost per launch?' terms: ['cost', 'launch']
  'it' has no entity term -> resolve it from the history:
  rewritten query terms = follow-up + entity = ['cost', 'launch', 'falcon', '9', 'rocket']
```

<svg role="img" aria-label="Two term sets merging: the follow-up's cost and launch, plus the history entity falcon, 9, rocket, combine into a self-contained query carrying all five terms" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">rewrite = follow-up terms + entity from history</text>
  <rect x="14" y="24" width="90" height="20" fill="none" stroke="var(--s2)"/><text x="20" y="37" fill="var(--s2)" font-size="7">cost, launch</text>
  <text x="108" y="37" fill="var(--muted)" font-size="9">+</text>
  <rect x="120" y="24" width="120" height="20" fill="none" stroke="var(--s1)"/><text x="126" y="37" fill="var(--s1)" font-size="7">falcon, 9, rocket</text>
  <text x="14" y="60" fill="var(--muted)" font-size="8">↓ merge (resolve 'it')</text>
  <rect x="14" y="66" width="226" height="20" fill="var(--panel)" stroke="var(--ink)"/><text x="20" y="79" fill="var(--ink)" font-size="7">cost, launch, falcon, 9, rocket — self-contained</text>
</svg>
^ The rewrite merges the follow-up's own terms {cost, launch} with the entity {falcon, 9, rocket} carried from turn 1, producing a self-contained query that names the Falcon 9 explicitly — the pronoun's referent restored into the query text.

The rewrite happens before any embedding or search: the follow-up's own terms are {cost, launch}, the entity established in the prior turn is {falcon, 9, rocket}, and rewriting merges them so the query stands on its own. In a real system a small model (or a rule-based coreference resolver) does this rewriting, taking the conversation history and the raw follow-up and emitting a self-contained query string; here it is a set union, but the effect is identical — the pronoun's referent is made explicit in the query text. The reason this must happen *before* retrieval, and cannot be fixed afterward, is that retrieval is a lossy bottleneck: whatever the retriever fails to fetch is simply absent from everything downstream, so if the ambiguous follow-up fetched the generic document, no amount of clever reranking or prompting can recover the Falcon-9 document it never retrieved. The query is the only channel through which the entity can reach the retriever, and if the entity is not in the query, it is not in the search.

```python filename=modules/context-and-retrieval/code/qrewrite-inter-01/qrewrite.py:109-118 COMPLETE
    raw_ties = score(raw, data["documents"][specific]) == score(raw, data["documents"][generic])
    print("  raw follow-up ties the specific and generic docs = %s (%d == %d)"
          % (raw_ties, score(raw, data["documents"][specific]), score(raw, data["documents"][generic])))

    rewrite_adds_entity = set(rew) - set(raw) == set(data["history_terms"])
    print("  rewriting adds exactly the entity terms the follow-up lacked = %s (%s)" % (rewrite_adds_entity, sorted(set(rew) - set(raw))))

    rewritten_top = rank(data, rew)[0][0]
    rewrite_ranks_specific = rewritten_top == specific
    print("  the rewritten query ranks the specific doc first = %s (%s)" % (rewrite_ranks_specific, rewritten_top))
```

## Definition of done

The self-test pins the raw tie, the entity the rewrite restores, the decisive win, and the specific doc's risen score.

```python filename=modules/context-and-retrieval/code/qrewrite-inter-01/qrewrite.py:120-125 COMPLETE
    rewrite_breaks_tie = score(rew, data["documents"][specific]) > score(rew, data["documents"][generic])
    print("  the rewritten query beats the generic doc, not ties it = %s (%d > %d)"
          % (rewrite_breaks_tie, score(rew, data["documents"][specific]), score(rew, data["documents"][generic])))

    specific_score_rose = score(rew, data["documents"][specific]) > score(raw, data["documents"][specific])
    print("  the specific doc scores higher after rewriting = %s (%d > %d)"
          % (specific_score_rose, score(rew, data["documents"][specific]), score(raw, data["documents"][specific])))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the raw follow-up ties the specific and generic docs; the rewritten query ranks the specific one first
------------------------------------------------------------------------------------------------------------------
  raw follow-up ties the specific and generic docs = True (2 == 2)
  rewriting adds exactly the entity terms the follow-up lacked = True (['9', 'falcon', 'rocket'])
  the rewritten query ranks the specific doc first = True (d1_falcon9_cost)
  the rewritten query beats the generic doc, not ties it = True (5 > 3)
  the specific doc scores higher after rewriting = True (5 > 2)
```

<svg role="img" aria-label="Scores for the specific and generic documents: on the raw query both score 2 (a tie), on the rewritten query the specific doc scores 5 and the generic 3" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">raw: tie at 2; rewritten: specific 5 beats generic 3</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">raw, specific</text>
  <rect x="110" y="26" width="46" height="11" fill="var(--s1)"/><text x="160" y="35" fill="var(--muted)" font-size="7">2</text>
  <text x="10" y="50" fill="var(--muted)" font-size="7">raw, generic</text>
  <rect x="110" y="42" width="46" height="11" fill="var(--s2)"/><text x="160" y="51" fill="var(--muted)" font-size="7">2 (tie)</text>
  <line x1="14" y1="60" x2="286" y2="60" stroke="var(--grid)"/>
  <text x="10" y="78" fill="var(--muted)" font-size="7">rewritten, specific</text>
  <rect x="110" y="70" width="115" height="11" fill="var(--s1)"/><text x="229" y="79" fill="var(--muted)" font-size="7">5</text>
  <text x="10" y="94" fill="var(--muted)" font-size="7">rewritten, generic</text>
  <rect x="110" y="86" width="69" height="11" fill="var(--s2)"/><text x="183" y="95" fill="var(--muted)" font-size="7">3</text>
</svg>
^ On the raw follow-up the specific and generic documents tie at 2, so the retriever cannot choose; on the rewritten query the specific document rises to 5 and clears the generic's 3 — the carried-over entity terms are what turn a tie into a decisive, correct ranking.

**Done means the ambiguity and its fix are proven on real scores: the raw follow-up {cost, launch} ties the Falcon-9 cost doc with the generic rocket-cost doc (2 == 2), while rewriting adds exactly the entity terms {falcon, 9, rocket} the follow-up lacked, lifting the specific doc to 5 and ranking it first over the generic 3 — so a conversational follow-up must be rewritten into a self-contained query before retrieval.**

## Boss fight

Predict two ways conversational rewriting goes wrong, because resolving references from a dialogue is harder than a pronoun swap and the rewrite is now a component that can fail on its own.

The first trap is that the rewriter must decide *what* to carry forward, and both over- and under-carrying hurt. Under-carrying is the failure this module fixes — leaving the entity implicit — but over-carrying is just as real: a conversation accumulates many entities and topics, and a follow-up usually refers to only the most recent or most salient one, so a rewriter that dumps *all* prior entities into every query pollutes it with stale terms and drags retrieval toward earlier, now-irrelevant topics. Worse is topic-shift: when the user changes subject ("Actually, forget rockets — what's the weather in Boston?"), carrying the Falcon 9 forward actively corrupts the new query. So the rewriter needs to model salience and detect topic boundaries — which entity is the follow-up actually about, and has the conversation moved on — not mechanically append history. This is why rewriting is usually a learned step (a small LLM prompted with the recent history and the follow-up) rather than a rule, and why it must be evaluated: a bad rewrite can retrieve worse than the raw query, by confidently resolving a reference to the wrong antecedent.

The second trap is that the rewrite is now a pipeline stage with its own latency, failure modes, and error propagation, and it interacts with the rest of retrieval. Every turn now pays for an extra model call before search, which adds latency to the user-facing path and a new thing that can time out or hallucinate; a rewriter that invents an entity not in the conversation sends the retriever chasing a phantom. And because retrieval is the lossy bottleneck, a rewriting error is unrecoverable downstream in exactly the way the original ambiguity was — you have moved the point of failure, not removed it. Robust systems therefore hedge: keep the rewrite but also retrieve on the original query and fuse the results, or condition the rewrite on retrieved candidates, or fall back to the raw query when the rewriter is low-confidence, so a single bad rewrite does not silently starve the answer. And the rewrite should be logged and evaluated as its own metric (does the rewritten query retrieve the gold document more often than the raw one?), because it is easy to add a rewriter that helps on average while quietly breaking the cases where it resolves the wrong referent.

**A rewriter must resolve to the right antecedent, not just any prior entity: over-carrying pollutes the query with stale topics and breaks on a topic shift, so model salience and detect when the conversation has moved on rather than appending all history. And treat the rewrite as its own fallible stage — it adds latency and can hallucinate an entity, and because retrieval is lossy its errors are unrecoverable downstream — so hedge (retrieve on the raw query too and fuse, or fall back when low-confidence) and evaluate the rewrite directly on whether it retrieves the gold document more often than the raw follow-up.**

## External resources

The conversational-search and query-rewriting literature (the TREC CAsT conversational-search track, and query-rewriting-for-conversational-retrieval papers such as QReCC and CQR work) — how follow-ups are made self-contained, coreference and ellipsis resolution, and evaluation of the rewrite step.

Documentation for conversational RAG pipelines (LangChain/LlamaIndex "condense question" or "chat history" retrievers) — the standard pattern of rewriting a follow-up against the chat history before retrieval, and the fallbacks used when the rewrite is uncertain.

The companion query-expansion, HyDE, and multi-hop retrieval modules in this topic — rewriting resolves what a follow-up left implicit (reference resolution), expansion broadens a self-contained query (breadth), and multi-hop chains retrievals; all three shape the query so the lossy retrieval step receives the terms it needs.
