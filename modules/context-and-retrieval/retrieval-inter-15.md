---
id: retrieval-inter-15
title: Retrieve in hops for a bridge question — one-shot retrieval never reaches the answer document
topic: context-and-retrieval
level: intermediate
status: ready
time: 21 min
summary: Some questions connect to their answer only through a bridge entity that neither states — "who directed the film that won the 1994 award" links to a director through the film. The answer document shares no distinctive term with the question, so one-shot retrieval lands on the bridge document (0.571) while the answer scores 0.169, unreachable. Multi-hop retrieval retrieves the bridge first, reformulates the query with the entity it supplies, and the second hop retrieves the answer (0.447).
eli5: If someone asks "who wrote the sequel to the book my sister loves?" you can't answer in one step — you first find out which book, then who wrote its sequel. A search engine is the same: some questions need two lookups, one to find the missing link and another to use it. Doing it in one shot just finds the first fact and stops.
---

## Why this module

A question can be worded so that the document holding its answer shares almost no words with it, and then one retrieval can never find that document no matter how good the retriever is.

Some questions span two facts joined by a bridge. "Who directed the film that won the 1994 best-picture award?" contains the award and asks for the director, but the document that states the director — "Forrest Gump was directed by Robert Zemeckis" — mentions neither the award nor the year. The question and its answer are connected only through the film, a bridge entity that the question does not name and the answer document does not name either. The question knows the award; the answer knows the director; the film links them, and it is missing from both ends of the retrieval.

So retrieve once on the question and you land on the wrong document. The retriever matches words, and the question's distinctive words — the award, the year, "won", "film" — all appear in the bridge document (the one that maps the award to the film), not in the answer document. A perfect retriever will confidently return the bridge fact, because that genuinely is the best match for the question as asked. The answer document, sharing only a generic word or two, sits far down the ranking. This is not a retriever-quality problem you can fix with a better embedding: the answer document is simply not similar to the question, because the term that would connect them was never in the question.

Multi-hop retrieval is the fix, and it mirrors the structure of the question. Retrieve once to get the bridge document, which supplies the missing entity (the film's name). Then reformulate the query using that entity — drop the part of the question the bridge already answered, and carry the film forward — and retrieve again. The second query now contains the film's name, so it matches the answer document. Two facts in the question, two retrievals to follow them; the chain of hops traces the chain of reasoning.

On the fixture, the question is about a 1994 award and the answer is a director. One-shot retrieval's top document is the bridge (similarity 0.571) while the true answer scores only 0.169 to the raw question, below two other documents — unreachable. After hop one supplies the film name and the query is reformulated, the second hop retrieves the answer document as its top result (0.447).

**A bridge question connects to its answer only through an entity neither states, so the answer document is not similar to the question and one-shot retrieval cannot reach it; multi-hop retrieval retrieves the bridge, reformulates the query with the entity it supplies, and the second hop reaches the answer.**

## Concepts

The root issue is that retrieval matches surface similarity, and a bridge question is deliberately dissimilar to its answer. A retriever — lexical or dense — scores documents by how much they look like the query, and for most questions the answer document looks like the question, which is why single-shot retrieval usually works. A bridge (or multi-hop) question breaks that assumption on purpose: the answer document is about a different entity than the question names, so its similarity to the question is low by construction. No amount of retriever quality closes a gap that exists because the connecting term is absent from one side; the term has to be supplied, not matched harder.

<svg role="img" aria-label="The question links to the award, the answer links to the director, and the film bridges them; the question and answer share no term directly" viewBox="0 0 470 160" width="470" height="160">
  <rect x="0" y="0" width="470" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">question and answer connect only through the bridge entity</text>
  <rect x="30" y="60" width="90" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="40" y="78" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">question</text>
  <text x="40" y="90" font-family="var(--mono)" font-size="7" fill="var(--muted)">the award</text>
  <rect x="190" y="60" width="90" height="34" fill="var(--panel)" stroke="var(--s2)"/>
  <text x="200" y="78" font-family="var(--mono)" font-size="8" fill="var(--s2)">bridge</text>
  <text x="200" y="90" font-family="var(--mono)" font-size="7" fill="var(--muted)">the film</text>
  <rect x="350" y="60" width="90" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="360" y="78" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">answer</text>
  <text x="360" y="90" font-family="var(--mono)" font-size="7" fill="var(--muted)">the director</text>
  <line x1="120" y1="77" x2="190" y2="77" stroke="var(--s2)" stroke-width="2"/>
  <text x="128" y="70" font-family="var(--mono)" font-size="7" fill="var(--s2)">shares award</text>
  <line x1="280" y1="77" x2="350" y2="77" stroke="var(--s2)" stroke-width="2"/>
  <text x="288" y="70" font-family="var(--mono)" font-size="7" fill="var(--s2)">shares film</text>
  <path d="M75,100 Q235,145 395,100" fill="none" stroke="var(--muted)" stroke-dasharray="4 3"/>
  <text x="170" y="140" font-family="var(--mono)" font-size="7" fill="var(--muted)">question ↔ answer: no shared term (one hop fails)</text>
</svg>
^ The question shares the award with the bridge and the bridge shares the film with the answer, but the question and answer share nothing directly — so retrieval can hop question-to-bridge and bridge-to-answer, never question-to-answer.

The bridge entity is the thing that has to be supplied, and it lives in a document you can retrieve. The question does not name the film, but a document does — the one mapping the award to the film — and that document is similar to the question, so a first hop finds it. That first hop's payoff is not the answer; it is the entity. Once you have the film's name, the second question ("who directed the film") is an ordinary single-hop question whose answer document is similar to it. Multi-hop retrieval is thus a decomposition: turn one impossible retrieval into two possible ones, using the first to obtain the term the second needs.

Reformulating the query between hops matters as much as retrieving twice. Simply appending the whole first document to the question does not work — the bridge document's boilerplate ("was won by the film") matches other award documents, and re-including the question's award terms keeps pulling back the bridge and its lookalikes. The effective reformulation drops the sub-question the first hop already resolved (the award part) and carries forward the new entity (the film), producing a focused second query that is similar to the answer and dissimilar to the distractors. And the already-retrieved bridge document is excluded from the second hop, because you have its fact and re-retrieving it wastes the slot. Good multi-hop is retrieve, extract, reformulate, exclude, retrieve again.

This is the core of multi-hop question answering, and it generalizes past two hops. Systems like this power questions that require chaining several facts (each hop resolving one link), and the same pattern appears in agentic retrieval, where a model issues a search, reads the result, and issues a follow-up search informed by what it learned. The alternatives and complements are worth knowing: sometimes you can decompose the question up front into sub-questions and retrieve each; sometimes a knowledge graph makes the bridge an explicit edge to traverse. But when the corpus is text and the link is implicit, iterative retrieve-and-reformulate is the workhorse, and recognizing a bridge question — one whose answer document would share no distinctive term with it — is what tells you a single hop cannot succeed.

**Retrieval matches similarity, and a bridge question is dissimilar to its answer by construction, so the fix is not a better retriever but supplying the missing entity: retrieve the bridge to obtain it, reformulate to a focused sub-question and exclude the bridge, then retrieve the now-reachable answer.**

## Worked example

The fixture is a bridge question and a small corpus.

```json filename=modules/context-and-retrieval/code/retrieval-inter-15/corpus.json:3-9 COMPLETE
  "question": "who directed the film that won bestpicture1994",
  "docs": {
    "d_bridge": {"text": "bestpicture1994 was won by the film forrestgump", "answer": false, "bridge": true},
    "d_answer": {"text": "forrestgump was directed by robertzemeckis", "answer": true},
    "d_dist1":  {"text": "bestpicture1995 was won by the film braveheart", "answer": false},
    "d_dist2":  {"text": "titanic was directed by jamescameron", "answer": false}
  }
```

The answer document names the film and the director but not the award; the bridge document maps the award to the film. Similarity is bag-of-words cosine — a stand-in for an embedding so the matching is visible.

```python filename=modules/context-and-retrieval/code/retrieval-inter-15/multihop.py:61-64 COMPLETE
def sims(query, docs):
    """Similarity of the query to every document."""
    qv = vec(query)
    return {d: cosine(qv, vec(docs[d]["text"])) for d in docs}
```

The second hop reformulates: it drops the question terms the bridge document already contains (the award part it answered) and appends the bridge's new entity (the film).

```python filename=modules/context-and-retrieval/code/retrieval-inter-15/multihop.py:86-91 COMPLETE
def second_hop_query(query, docs):
    """Reformulate: drop the sub-question the bridge already answered, carry its entity forward."""
    bridge_text = docs[top(query, docs)]["text"]
    resolved = vec(bridge_text)                                  # terms the bridge doc satisfied
    residual = [w for w in query.split() if w.lower() not in resolved]
    return " ".join(residual) + " " + bridge_entity(query, bridge_text)
```

The corpus view confirms the setup — the answer document shares no distinctive term with the question.

```text filename=modules/context-and-retrieval/code/retrieval-inter-15/multihop.py --corpus
CORPUS — question and documents (answer needs a bridge entity)
--------------------------------------------------------------
  question: who directed the film that won bestpicture1994
  d_bridge  (bridge): bestpicture1994 was won by the film forrestgump
  d_answer  (ANSWER): forrestgump was directed by robertzemeckis
  d_dist1: bestpicture1995 was won by the film braveheart
  d_dist2: titanic was directed by jamescameron
--------------------------------------------------------------
  the answer doc shares no distinctive term with the question.
```

Predict: the raw question matches the bridge document (it shares the award, "won", "film") and barely matches the answer (which shares nothing distinctive). After reformulating with "forrestgump", the second query matches the answer. Retrieve both hops.

```text filename=modules/context-and-retrieval/code/retrieval-inter-15/multihop.py --retrieve
RETRIEVE — one-shot similarity, then second hop after feedback
--------------------------------------------------------------
  hop 1 (raw question):
    d_bridge 0.571
    d_answer 0.169
    d_dist1  0.429
    d_dist2  0.169
  hop 1 top: d_bridge   answer: d_answer
  hop 2 (reformulated with 'forrestgump', excluding d_bridge):
    d_answer 0.447
    d_dist1  0.000
    d_dist2  0.224
  hop 2 top: d_answer   answer: d_answer
```

Hop one ranks the bridge document top at 0.571, and the answer document scores only 0.169 — below even distractor d_dist1 (0.429, the other award document), because the answer shares no distinctive term with the question. One-shot retrieval returns the bridge fact, which is not the answer, and the answer is genuinely unreachable: it is fourth-ranked. Hop two reformulates the query with "forrestgump" and excludes the already-seen bridge; now the answer document tops at 0.447, distractor d_dist1 drops to 0.000 (the reformulated query no longer mentions awards), and the answer is retrieved. The film's name, obtained in hop one, is exactly what made the answer document match.

<svg role="img" aria-label="Hop one ranks the bridge top with the answer near the bottom; hop two, after reformulation, ranks the answer top with the award distractor at zero" viewBox="0 0 470 200" width="470" height="200">
  <rect x="0" y="0" width="470" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">similarity by hop (bar length = score)</text>
  <text x="20" y="40" font-family="var(--mono)" font-size="9" fill="var(--s2)">hop 1 (raw question)</text>
  <text x="30" y="58" font-family="var(--mono)" font-size="8" fill="var(--muted)">bridge</text>
  <rect x="90" y="50" width="171" height="10" fill="var(--s2)"/>
  <text x="30" y="74" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">answer</text>
  <rect x="90" y="66" width="51" height="10" fill="var(--acc-line)"/>
  <text x="150" y="74" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">0.169 — 4th, unreachable</text>
  <text x="30" y="90" font-family="var(--mono)" font-size="8" fill="var(--muted)">dist1</text>
  <rect x="90" y="82" width="129" height="10" fill="var(--muted)"/>
  <text x="20" y="122" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">hop 2 (reformulated, bridge excluded)</text>
  <text x="30" y="140" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">answer</text>
  <rect x="90" y="132" width="134" height="10" fill="var(--acc-line)"/>
  <text x="230" y="140" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">0.447 — top</text>
  <text x="30" y="156" font-family="var(--mono)" font-size="8" fill="var(--muted)">dist2</text>
  <rect x="90" y="148" width="67" height="10" fill="var(--muted)"/>
  <text x="30" y="172" font-family="var(--mono)" font-size="8" fill="var(--muted)">dist1</text>
  <rect x="90" y="164" width="2" height="10" fill="var(--s2)"/>
  <text x="96" y="172" font-family="var(--mono)" font-size="7" fill="var(--s2)">0.000 — award terms gone</text>
</svg>
^ In hop one the answer is fourth and unreachable; after the reformulation in hop two it is first, and the award distractor that ranked high in hop one falls to zero because the query no longer mentions the award.

## Build

Reproduce the hops. Pure standard library, deterministic, so the 0.571 bridge, the 0.169 unreachable answer, and the 0.447 second-hop answer come out exactly.

Run `--corpus` for the documents, `--retrieve` for the two hops, `--check` for the gate. The self-test pins that one-shot misses (lands on the bridge, answer unreachable) and the second hop finds the answer.

```python filename=modules/context-and-retrieval/code/retrieval-inter-15/multihop.py:80-83 COMPLETE
def bridge_entity(query, doc_text):
    """The new content terms a document adds beyond the query -- the bridge it supplies."""
    novel = [w for w in doc_text.lower().split() if w not in vec(query) and w not in STOPWORDS]
    return " ".join(novel)
```

The `bridge_entity` helper is what makes the hop productive: it extracts exactly the terms the first document adds beyond the question — here "forrestgump" — which is the entity the second hop needs.

The second hop also excludes the document the first hop already retrieved, so the slot goes to something new rather than re-fetching the bridge fact you already hold.

```python filename=modules/context-and-retrieval/code/retrieval-inter-15/multihop.py:94-96 COMPLETE
def remaining(docs, exclude):
    """Documents still in play after a hop already retrieved `exclude`."""
    return {d: docs[d] for d in docs if d != exclude}
```

<svg role="img" aria-label="Two-step pipeline: hop one retrieves the bridge and extracts the entity, hop two reformulates and excludes the bridge to retrieve the answer" viewBox="0 0 470 150" width="470" height="150">
  <rect x="0" y="0" width="470" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">retrieve → extract → reformulate → exclude → retrieve</text>
  <rect x="20" y="45" width="90" height="40" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="30" y="62" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">hop 1: get</text>
  <text x="30" y="76" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">bridge (0.571)</text>
  <text x="118" y="68" font-family="var(--mono)" font-size="12" fill="var(--muted)">→</text>
  <rect x="140" y="45" width="110" height="40" fill="var(--panel)" stroke="var(--s2)"/>
  <text x="150" y="62" font-family="var(--mono)" font-size="8" fill="var(--s2)">extract entity</text>
  <text x="150" y="76" font-family="var(--mono)" font-size="8" fill="var(--s2)">'forrestgump'</text>
  <text x="256" y="68" font-family="var(--mono)" font-size="12" fill="var(--muted)">→</text>
  <rect x="278" y="45" width="120" height="40" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="288" y="62" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">hop 2: get</text>
  <text x="288" y="76" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">answer (0.447)</text>
  <text x="120" y="120" font-family="var(--mono)" font-size="8" fill="var(--muted)">each hop resolves one link of the question</text>
</svg>
^ The pipeline chains a retrieval, an entity extraction, and a reformulated retrieval — one hop per link in the question — turning one impossible lookup into two possible ones.

```text filename=modules/context-and-retrieval/code/retrieval-inter-15/multihop.py --check
SELF-TEST — one-shot lands on the bridge and misses the answer; a second hop reaches it
------------------------------------------------------------------------------------------
  one-shot retrieval's top is NOT the answer = True (top d_bridge)
  the answer scores below the one-shot top, so it is unreachable = True (0.169 < 0.571)
  one-shot lands on the bridge document = True (d_bridge)
  the second hop retrieves the answer = True (top d_answer)
  feeding back the bridge lifts the answer's score = True (0.169 -> 0.447)
------------------------------------------------------------------------------------------
SELF-TEST PASS  onehop_misses=True  answer_unreachable=True  onehop_lands_bridge=True  twohop_finds=True  feedback_lifts_answer=True
```

Five True flags. Onehop_misses: one-shot retrieval's top is not the answer. Answer_unreachable: the answer scores 0.169 against the top's 0.571, so it is far down the ranking. Onehop_lands_bridge: what one-shot returns is the bridge document. Twohop_finds: the second hop retrieves the answer. Feedback_lifts_answer: the reformulation raises the answer's score from 0.169 to 0.447. The answer-unreachable flag is the one that proves this needs multiple hops — the answer is not merely second, it is beneath the distractors, so no reranking of a single retrieval could recover it.

**The unreachable flag is the crux — the answer scores 0.169, below two distractors, so it is not a ranking that a reranker could fix but a document a single hop never surfaces; only supplying the bridge entity brings it into reach.**

## Definition of done

You are done when you reproduce the unreachable answer and its recovery by a second hop, and can explain why one hop cannot work.

Concretely: `--retrieve` shows the bridge top at 0.571 with the answer fourth at 0.169 on hop one, and the answer top at 0.447 on hop two; `--check` prints PASS with five True flags. You can explain that retrieval matches similarity and a bridge question is dissimilar to its answer by construction, so the answer document is unreachable in one hop regardless of retriever quality; that the first hop's payoff is the bridge entity, not the answer; and that the effective reformulation drops the resolved sub-question, carries the entity forward, and excludes the already-retrieved document.

The habit to carry: recognize a bridge (multi-hop) question — one whose answer document would share no distinctive term with the question — and retrieve iteratively, feeding each hop's entity into the next query, rather than expecting one retrieval to succeed. When a RAG system confidently returns a document that is related to the question but is not the answer (the award, not the director), suspect a bridge question and add a hop. A reranker cannot save a retrieval that never surfaced the answer.

## Boss fight

The instructive failure is a RAG assistant that answers bridge questions with the wrong-but-related fact.

A documentation assistant is asked "who owns the service that the checkout page calls for payments?" and confidently answers with the checkout page's team, not the payment service's owner — because it retrieved the document about the checkout page (which matched the question) and never retrieved the document about the payment service's ownership (which shared no terms with the question). The single retrieval found the bridge and stopped. Users lose trust because the answer is plausibly related and wrong. The fix is multi-hop: retrieve the checkout doc, extract the payment-service name it references, reformulate to "who owns <payment-service>", and retrieve again — the second hop lands on the ownership doc. The tell for when to add a hop is a question that names one entity but asks about another it is only linked to.

Your turn, two moves. First, break the reformulation on purpose: instead of dropping the resolved award terms, append the whole bridge document to the question and retrieve among all docs (no exclusion), and confirm the second hop returns the bridge or an award distractor rather than the answer — showing that naive feedback fails and the drop-resolved-terms-and-exclude steps are load-bearing, not incidental. Second, extend to three hops: add a document that the answer itself points to (the director's next film) and a question that needs it, and confirm two hops are now insufficient and a third recovers it — the number of hops must match the number of links in the question.

## External resources

The HotpotQA dataset and paper (Yang et al., 2018) is the standard benchmark for multi-hop question answering, with exactly the bridge-question structure this module models, and its analysis shows single-hop retrievers failing on the bridge cases.

Work on iterative and multi-hop retrieval (MDR, "Multi-hop Dense Retrieval," and IRCoT, "Interleaving Retrieval with Chain-of-Thought") formalizes the retrieve-reformulate-retrieve loop and shows the gains over one-shot retrieval on bridge questions.

Agentic-RAG and query-decomposition writing (from LangChain, LlamaIndex, and similar) covers the practical patterns — decomposing a question into sub-questions, or letting a model issue follow-up searches from what it read — which are the production forms of the hopping this module demonstrates.
