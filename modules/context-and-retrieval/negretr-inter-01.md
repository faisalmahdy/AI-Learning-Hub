---
id: negretr-inter-01
title: Enforce a negated query constraint as a hard filter, not through the dense score — the negated term pulls retrieval toward the documents it means to exclude
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: A dense retriever turns text into a vector that encodes which content words are present, and that is exactly why it cannot represent negation. The words "not" and "without" are short, low-content function words that barely move the embedding, while the content word they negate lands in the representation at full weight — so "muscle pain relief without ibuprofen" embeds almost identically to "muscle pain relief ibuprofen." The negated term is not excluded; it is still in the query. Worse, it is active: a document that literally contains the excluded term now shares one more content token with the query, which lifts it above the document the user actually wanted. This module models documents and the query as content-token sets and dense similarity as their cosine — a stylized embedder, but the mechanism is the real one. The query's content tokens are muscle, pain, relief, and ibuprofen; the ibuprofen document matches all four at cosine 1.00 and tops the dense ranking, while the acetaminophen document — the intended answer, which relieves the pain without ibuprofen — matches three at cosine 0.75. Strip the negated term and the two tie at 0.87, which proves the negated term is precisely what promotes the excluded document. No score function fixes this, because a cosine cannot see a NOT; the fix is to parse the negation out of the free-text query and enforce it as a hard structured filter that removes any document containing the excluded term, then rank the survivors by the positive terms — after which the intended acetaminophen document rises to the top at 0.87. The rule: a negated constraint is a filter, not a ranking signal.
eli5: Imagine you tell a helper "find me a fruit salad with no bananas," but the helper only listens for the important words and hears "fruit salad bananas." Now they go looking for exactly the salads that have the most matching words — and a banana salad matches every word you said, banana included, so they proudly bring you the one thing you didn't want. The word "no" slipped right past them. The reason is that they match by which words you mentioned, and you did mention bananas, even though you meant to keep them out. The fix is to split your request into two parts: the things you want (fruit, salad) and a separate hard rule (throw away anything with bananas). Apply the throw-away rule first, then pick the best of what's left — and now the no-banana salad is the only kind that can win.
---

## Why this module

Users write negation constantly. "A lightweight framework, not Spring." "Side effects other than nausea." "Restaurants nearby that aren't Italian." Each of these names something specifically to keep out, and it is often the most important part of the request — the whole point is the exclusion.

A dense retriever hears none of it. It embeds the content of the query, and the small word carrying the negation — "not," "without," "other than," "aren't" — leaves almost no trace in the vector. What survives is the topic you mentioned, including the topic you were trying to avoid. So the retriever goes looking for documents about the excluded thing, because as far as the vector is concerned you asked for it.

This module builds that failure in miniature and shows it is not a near-miss but an active promotion: the negated term does not just fail to exclude the wrong document, it is the single token that lifts the wrong document above the right one. Then it shows why no scoring tweak can save you, and what to do instead — pull the negation out and enforce it as a hard filter before ranking.

**A dense embedding records which topics a query mentions, not which topics it wants kept out, so negation is invisible to it by construction — and a signal the retriever cannot see cannot be a ranking signal.**

## Concepts

Think about what a sentence embedder actually encodes. It maps text to a vector such that texts about similar things land near each other. The features that dominate that vector are the content words — the nouns and verbs that carry topic. Function words like "not," "no," and "without" are everywhere in the language, carry little topical information, and move the vector barely at all.

That is fatal for negation, because negation lives entirely in those function words. "Ibuprofen" and "without ibuprofen" differ by one low-content token and one enormous change in meaning — the first wants ibuprofen, the second forbids it — but the embedder sees almost the same vector for both. The content token "ibuprofen" is present in the query representation either way.

So a query with a negated constraint carries the excluded term as an ordinary positive term. When it is scored against a document that contains that term, the shared token counts in the document's favor, exactly as any matching token would. The negation has been silently dropped and, in its place, the retriever is now rewarding the presence of the thing you wanted gone.

The figure shows the query going through the embedder: the content tokens all pass into the vector, and the negation word — the only thing that made "ibuprofen" an exclusion rather than a request — falls away.

<svg role="img" aria-label="A query phrase muscle pain relief without ibuprofen feeding into an embedder box; the tokens muscle, pain, relief, and ibuprofen come out into the query vector, while the token without is shown faded and dropped before the box" viewBox="0 0 640 220">
<text x="60" y="50" fill="var(--muted)" font-size="12">query: "muscle pain relief without ibuprofen"</text>
<text x="80" y="95" fill="var(--ink)" font-size="12">muscle</text>
<text x="160" y="95" fill="var(--ink)" font-size="12">pain</text>
<text x="220" y="95" fill="var(--ink)" font-size="12">relief</text>
<text x="290" y="95" fill="var(--muted)" font-size="12" opacity="0.4" text-decoration="line-through">without</text>
<text x="370" y="95" fill="var(--ink)" font-size="12">ibuprofen</text>
<rect x="70" y="120" width="400" height="34" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="270" y="142" fill="var(--muted)" font-size="12" text-anchor="middle">embedder (encodes content tokens)</text>
<line x1="270" y1="154" x2="270" y2="180" stroke="var(--line)" stroke-width="1"/>
<polygon points="270,180 264,170 276,170" fill="var(--line)"/>
<text x="270" y="200" fill="var(--ink)" font-size="12" text-anchor="middle">query vector = { muscle, pain, relief, ibuprofen }</text>
</svg>
^ The negation word is the one token that does not survive embedding, so the excluded term "ibuprofen" enters the query vector as an ordinary positive feature.

**The embedder drops the exact word that reverses the query's meaning, so the vector it produces asks for the thing the user forbade.**

## Worked example

The fixture is a negated query and three documents, all as content-token sets. The query wants muscle-pain relief and explicitly excludes ibuprofen.

```json filename=modules/context-and-retrieval/code/negretr-inter-01/negretr.json:3-8 COMPLETE
  "query_positive": ["muscle", "pain", "relief"],
  "query_negated": ["ibuprofen"],
  "documents": {
    "ibuprofen_doc": ["muscle", "pain", "relief", "ibuprofen"],
    "acetaminophen_doc": ["muscle", "pain", "relief", "acetaminophen"],
    "laptop_doc": ["battery", "charge", "laptop"]
```

Dense similarity is the cosine over the token sets — shared tokens over the geometric mean of the sizes. It is a stylized embedder, but presence of content tokens drives the score, which is the real mechanism.

```python filename=modules/context-and-retrieval/code/negretr-inter-01/negretr.py:30-35 COMPLETE
def cosine(query_terms, doc_terms):
    """Set cosine: shared tokens over the geometric mean of the two sizes -- the stylized dense score."""
    q, d = set(query_terms), set(doc_terms)
    if not q or not d:
        return 0.0
    return len(q & d) / (len(q) * len(d)) ** 0.5
```

The crucial line is what the retriever actually embeds: the positive terms plus the negated one, because "without" is invisible to it.

```python filename=modules/context-and-retrieval/code/negretr-inter-01/negretr.py:38-40 COMPLETE
def dense_query(data):
    """What the dense retriever actually embeds: every content token, the negated one included."""
    return data["query_positive"] + data["query_negated"]   # 'without' is invisible; 'ibuprofen' stays in
```

Ranking against that query puts the excluded document on top.

```text filename=negretr.py --dense
DENSE — cosine ranking with the negated term left in the query (as the embedder sees it)
------------------------------------------------------------------------
  query embeds: ['muscle', 'pain', 'relief', 'ibuprofen']   ('without' is invisible to the embedder)
    ibuprofen_doc        cosine 1.0000  <- EXCLUDED term is here
    acetaminophen_doc    cosine 0.7500
    laptop_doc           cosine 0.0000
------------------------------------------------------------------------
  the top hit is the document the user asked to exclude
```

The ibuprofen document scores a perfect 1.00 because it shares all four of the query's embedded tokens — including ibuprofen. The acetaminophen document, the one that actually answers the request, shares only three and scores 0.75. The retriever has ranked the single document the user named for exclusion above the intended answer. The fix is not a better cosine; it is to take the negation out of the query and apply it as a hard filter that drops any document containing the excluded term.

```python filename=modules/context-and-retrieval/code/negretr-inter-01/negretr.py:49-52 COMPLETE
def negation_filter(data, docs):
    """Enforce the negation as a hard NOT: drop any document that contains an excluded term."""
    excluded = set(data["query_negated"])
    return {doc_id: terms for doc_id, terms in docs.items() if not (set(terms) & excluded)}
```

Filter first, then rank the survivors by the positive terms alone.

```text filename=negretr.py --filter
FILTER — parse the negation into a hard NOT filter, then rank by the positive terms
------------------------------------------------------------------------
  positive query: ['muscle', 'pain', 'relief']   NOT: ['ibuprofen']
  removed by filter: ['ibuprofen_doc']
    acetaminophen_doc    cosine 0.8660
    laptop_doc           cosine 0.0000
------------------------------------------------------------------------
  the excluded document is gone before ranking; the intended answer is on top
```

The excluded document is removed before ranking ever runs, and the acetaminophen document rises to the top at 0.87. The figure puts the two rankings side by side.

<svg role="img" aria-label="Two ranked lists; on the left the dense ranking with ibuprofen_doc first at cosine 1.00 marked excluded, acetaminophen_doc second at 0.75 marked intended; on the right after filtering, ibuprofen_doc is removed and acetaminophen_doc is first at 0.87" viewBox="0 0 640 240">
<text x="160" y="34" fill="var(--ink)" font-size="12" text-anchor="middle">dense ranking</text>
<rect x="40" y="50" width="240" height="34" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="5"/>
<text x="56" y="72" fill="var(--ink)" font-size="11">ibuprofen_doc  1.00  (excluded)</text>
<rect x="40" y="92" width="240" height="34" fill="var(--panel)" stroke="var(--line)" stroke-width="1" rx="5"/>
<text x="56" y="114" fill="var(--muted)" font-size="11">acetaminophen_doc  0.75  (intended)</text>
<rect x="40" y="134" width="240" height="30" fill="var(--panel)" stroke="var(--line)" stroke-width="1" rx="5"/>
<text x="56" y="154" fill="var(--muted)" font-size="11">laptop_doc  0.00</text>
<line x1="300" y1="100" x2="350" y2="100" stroke="var(--line)" stroke-width="1.5"/>
<polygon points="350,100 340,95 340,105" fill="var(--line)"/>
<text x="325" y="90" fill="var(--muted)" font-size="10" text-anchor="middle">NOT filter</text>
<text x="490" y="34" fill="var(--ink)" font-size="12" text-anchor="middle">after filtering</text>
<rect x="370" y="50" width="240" height="34" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="5" stroke-dasharray="4 3"/>
<text x="386" y="72" fill="var(--muted)" font-size="11" text-decoration="line-through">ibuprofen_doc removed</text>
<rect x="370" y="92" width="240" height="34" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="5"/>
<text x="386" y="114" fill="var(--ink)" font-size="11">acetaminophen_doc  0.87  (intended)</text>
<rect x="370" y="134" width="240" height="30" fill="var(--panel)" stroke="var(--line)" stroke-width="1" rx="5"/>
<text x="386" y="154" fill="var(--muted)" font-size="11">laptop_doc  0.00</text>
</svg>
^ Removing the excluded document before ranking promotes the intended answer from second to first — the filter does what the score never could.

**The negated term did not slightly disturb the ranking — it was the whole difference between right and wrong, because it is the only token separating a cosine of 1.00 from 0.75.**

## Build

The self-test isolates the mechanism: it confirms the hard filter removes the excluded document, that the intended document then tops the ranking, and that dense alone never returns it.

```python filename=modules/context-and-retrieval/code/negretr-inter-01/negretr.py:103-111 COMPLETE
    filter_removes_excluded = excluded_id not in kept
    print("  the hard NOT filter removes the excluded document = %s" % filter_removes_excluded)

    filtered_top = rank(data, data["query_positive"], kept)[0][0]
    filtered_top_is_intended = filtered_top == intended_id
    print("  after filtering, the top hit is the intended document = %s (%s)" % (filtered_top_is_intended, filtered_top))

    dense_alone_is_wrong = dense_top != intended_id
    print("  dense alone does NOT return the intended document = %s (returned %s)" % (dense_alone_is_wrong, dense_top))
```

The middle flag in the full run is the decisive one: it scores the two documents with and without the negated term in the query. With it, the excluded document leads 1.00 to 0.75; without it, they tie at 0.87. The negated term is the promotion.

```text filename=negretr.py --check
SELF-TEST — the dense ranking returns the excluded document, the negated term is what promotes it, and the hard filter fixes it
----------------------------------------------------------------------------------------------------------------
  dense top hit contains the excluded term = True (ibuprofen_doc)
  the negated term is what lifts the excluded doc above the intended one = True (with 1.0000>0.7500, without 0.8660==0.8660)
  the hard NOT filter removes the excluded document = True
  after filtering, the top hit is the intended document = True (acetaminophen_doc)
  dense alone does NOT return the intended document = True (returned ibuprofen_doc)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  dense_top_is_excluded=True  negated_term_promotes_excluded=True  filter_removes_excluded=True  filtered_top_is_intended=True  dense_alone_is_wrong=True
```

**With the negated term removed the two documents tie exactly, which is the proof: nothing about the acetaminophen document changed, so the ibuprofen document's entire advantage came from the token the user asked to exclude.**

## Definition of done

You are done when a negated constraint never reaches the ranker as text — it is parsed out of the query and applied as a hard structured filter, and only the positive intent is embedded and scored.

The pipeline has three steps. Parse the query into positive terms and a NOT set — from explicit filter syntax if your interface has it, or with a query-understanding step (rules or an LLM) that extracts negations from natural language. Apply the NOT set as a metadata or keyword filter that removes matching documents from the candidate pool. Then embed and rank only the positive terms over the survivors.

<svg role="img" aria-label="A three-stage pipeline: a query box splits into positive terms and a NOT set; the NOT set feeds a hard filter that removes documents; the positive terms then rank the surviving documents" viewBox="0 0 640 210">
<rect x="30" y="80" width="130" height="44" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="95" y="100" fill="var(--ink)" font-size="11" text-anchor="middle">query with</text>
<text x="95" y="115" fill="var(--ink)" font-size="11" text-anchor="middle">negation</text>
<line x1="160" y1="90" x2="215" y2="60" stroke="var(--line)" stroke-width="1"/>
<line x1="160" y1="114" x2="215" y2="140" stroke="var(--line)" stroke-width="1"/>
<rect x="215" y="40" width="150" height="40" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="6"/>
<text x="290" y="64" fill="var(--ink)" font-size="11" text-anchor="middle">NOT set → filter</text>
<rect x="215" y="120" width="150" height="40" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="290" y="144" fill="var(--ink)" font-size="11" text-anchor="middle">positive terms</text>
<line x1="365" y1="60" x2="430" y2="90" stroke="var(--s2)" stroke-width="1"/>
<line x1="365" y1="140" x2="430" y2="110" stroke="var(--s1)" stroke-width="1"/>
<rect x="430" y="80" width="170" height="44" fill="var(--panel)" stroke="var(--ink)" stroke-width="1.5" rx="6"/>
<text x="515" y="100" fill="var(--ink)" font-size="11" text-anchor="middle">rank survivors</text>
<text x="515" y="115" fill="var(--muted)" font-size="10" text-anchor="middle">by positive terms</text>
</svg>
^ The negation is enforced before ranking as a hard filter; only the positive intent is ever embedded.

**Retrieval scores relevance, and a negation is not a degree of relevance but a boolean admissibility rule, so it belongs to the filter stage where booleans are enforced exactly, not to the score where everything is a soft nudge.**

## Boss fight

Your turn: make the exclusion softer and watch it get worse. Change `query_negated` to `["ibuprofen", "aspirin"]` — "relief without ibuprofen or aspirin" — and rerun `--dense`. Every document that contains either drug now shares even more tokens with the embedded query, so the dense ranking pushes them further up, not down. Each term you add to the exclusion list makes the dense retriever prefer the excluded documents more strongly, because to the embedder every one of those terms is a thing you asked for. The `--filter` path, by contrast, simply removes more documents and is unbothered.

Then consider the tempting shortcut some systems reach for: subtract the negated term's vector from the query vector instead of filtering. Try it in your head with the set model — remove "ibuprofen" from the query and you get the 0.87 tie, not an exclusion; the ibuprofen document is still a strong match on the remaining three tokens and can still be returned. Vector subtraction weakens the pull toward the excluded term but does not forbid it, so a document that is excluded on a hard constraint can still surface. That is the deep reason a negation must be a filter: "not X" is a promise that X will never appear, and only a hard boolean gate can keep a promise. A soft score, however you nudge it, can always be outvoted.

**Softening the negation into a score adjustment is answering a yes-or-no question with a maybe; the user said never, and only the filter stage can say never.**

## External resources

The BEIR benchmark paper (Thakur and colleagues, 2021) documents how dense retrievers underperform on queries that hinge on exact or logical constraints, the family that negation belongs to, and is a good grounding for when dense retrieval needs a lexical or structured assist.

Weller and colleagues' work on instruction-following and negation in retrieval ("NevIR" and related evaluations) measures directly how poorly dense retrievers handle negated queries, and quantifies the effect this module demonstrates in miniature.

Most vector databases document a hybrid query interface — a structured metadata or keyword filter applied alongside the vector search; their filtering guides (for example Weaviate's or Qdrant's `must_not` clauses) are the practical tool for enforcing the NOT set described here.
