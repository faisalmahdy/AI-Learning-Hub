---
id: retrieval-inter-02
title: Wiki or RAG? Neither — and a careless fusion loses to both
topic: context-and-retrieval
level: intermediate
status: ready
time: 8-10h
summary: Run a wiki-style exact retriever and an embedding-style dense one on one shared eval set and each scores 3/6 — lexical wins every exact-token query and loses every paraphrase, dense does the exact reverse, so the labs' "wiki beats RAG" opinion is revised to a tie that depends entirely on the query mix. Fusing them should win both; done carelessly it scores 1/6, worse than either, because a retriever with no signal still casts its alphabetical tie-break as a vote — until it abstains, and the fused retriever answers 6 of 6.
eli5: Two witnesses: one only reads license plates, the other only recognizes faces. Argue which is better and you miss that each sees what the other can't. Ask both and you solve every case — unless you force the witness who saw nothing to still name someone, and their random guess outvotes the one who actually saw.
---

## Why this module

This is the module the whole track was pointing at. The labs hold a strong, stated opinion — a compiled wiki beats dense RAG — and the scan's verdict on it is the reason this track exists: the claim is "currently unearned because it was never tested." An opinion about retrieval that has never been run on a shared eval set is a belief, not a finding, and this module turns it into one or the other. It takes the exact retriever (a wiki-style lookup that matches surface words) and the dense retriever (an embedding-style match on meaning), points both at the same queries, and reads the score.

The result is not the one the opinion predicts, and it is not the opposite either. Each method scores exactly half, and they disagree on which half — so "wiki beats RAG" turns out to be a claim about your *query mix*, not about the methods. That is the earned version of the opinion, and it points straight at fusion: if each method owns a different half, run both. But fusion has a trap sharper than the one it fixes, and you will watch a naive fuse score *below* either method it combines before a one-line change makes it beat both.

You need `retrieval-basic-01`'s cosine and gold-labelled measurement. One honesty note up front, fenced here because it is load-bearing: the dense retriever's "embedding" is a hand-built concept map — a fixture that groups synonyms under a shared concept — standing in for a learned embedding model we cannot run offline. The *mechanism* it demonstrates, mapping surface words to shared concepts and going blind on words it has no concept for, is exactly what a real embedding does continuously; the numbers are the mechanism's, not a specific model's. Everything runs offline, stdlib Python 3, `$0.00`, one sitting.

Here is the head-to-head, five ways to answer the same six queries:

```
# modules/context-and-retrieval/code/retrieval-inter-02/ — COMPLETE, run from that directory
$ python3 headto.py --methods

HEAD-TO-HEAD — hit@1 over the whole eval set
--------------------------------------------------------------
  lexical (wiki)          3/6
  dense (RAG)             3/6
  ship the champion       3/6  (pick the better single method)
  fuse, no abstention     1/6  (the bug: silent method still votes)
  fuse, with abstention   6/6  (the fix)
```

run: 2026-08-25 · retrievers are deterministic; corpus + concept map are a fixture · n=6 queries, 6 docs · `python3 headto.py --methods`

Read it as a story with a dip in the middle. The two methods tie at 3 of 6. Picking the better one — the whole "wiki vs RAG" debate — still gets 3 of 6, because there is no better one. Fusing them *should* climb, and instead falls to 1 of 6, worse than doing nothing clever. Then abstention takes it to a clean sweep. This module is those five rows and why the fourth is below the first three.

## Concepts

Named here so you can find them again; each is built below.

- **Lexical retrieval** — match on exact surface words (a wiki/BM25-style lookup). Nails rare tokens; blind to synonyms.
- **Dense retrieval** — match on shared concepts (an embedding stand-in). Catches paraphrase; silent on rare tokens.
- **Query type** — exact (answerable only by a rare token) versus paraphrase (answerable only by a shared concept).
- **The champion** — ship the single method with the best overall score. The "pick a winner" baseline.
- **Fusion** — combine both methods' rankings into one.
- **Abstention** — a retriever with no signal sits the query out instead of voting its tie-break. The fix. #3.

## Worked example

Source: faisalmahdy/agent — `agent/memory/retrieval.py` (the dense/embedding side, hybrid ranker) and the labs' compiled-wiki lookup (the lexical side); the scan records the standing claim, "a strong opinion that compiled wikis beat RAG," alongside its own verdict that the opinion is untested. This module is that test.

Script and fixture: `modules/context-and-retrieval/code/retrieval-inter-02/` — `headto.py`, and `corpus.json`, six notes, a concept map, and six gold-labelled queries. Every command runs from there.

### The frame: two witnesses who see different things

Think of the two retrievers as two witnesses to the same scene. One witness only reads license plates: give her an exact string like "14c" or "b4" and she nails it, but describe the car as "the one you commute in" and she has nothing — she does not do meaning. The other witness only remembers faces and gist: ask him about "your commute" and he points to the note about driving to work, but ask for plate "14c" and he shrugs, because a specific code is exactly what gist blurs away. Neither witness is better. They testify about different things, and the "wiki vs RAG" argument is two people insisting their witness is the real one.

The move that should obviously win is to call both witnesses. It does — but only if you handle the case where one of them saw nothing. Force a witness who saw nothing to still name a suspect and they will name whoever comes first alphabetically, and that random pick can outvote the witness who actually saw the crime. That single failure is the whole back half of this module.

### The two retrievers, and the words they go blind on

The lexical retriever counts shared content words — surface match, stopwords dropped.

```
# headto.py:55-58 — COMPLETE (wiki-style: exact surface overlap)
def lexical_score(query, doc, _concepts):
    """Wiki/BM25-style: how many distinct content words (stopwords removed) the
    query shares with the doc. Nails rare tokens (14c, b4); blind to synonyms."""
    return len(set(content(query)) & set(content(doc)))
```

The dense retriever maps every word to a shared concept and scores cosine over concepts — so "commute" and "drive to work" collide on one concept, but a rare token with no concept simply vanishes.

```
# headto.py:61-79 — COMPLETE (embedding stand-in: concepts, and the words that vanish)
def concept_vec(text, concepts):
    """Map surface words to shared concepts; words with no concept are dropped --
    exactly how a rare token becomes invisible to an embedding."""
    v = {}
    for t in toks(text):
        c = concepts.get(t)
        if c:
            v[c] = v.get(c, 0) + 1
    return v


def dense_score(query, doc, concepts):
    """Embedding stand-in: cosine over concept vectors. Catches paraphrase (shared
    concept); scores 0 for every doc when the query is only rare tokens."""
    q, d = concept_vec(query, concepts), concept_vec(doc, concepts)
    dot = sum(w * d.get(c, 0) for c, w in q.items())
    nq = sqrt(sum(w * w for w in q.values()))
    nd = sqrt(sum(w * w for w in d.values()))
    return dot / (nq * nd) if nq and nd else 0.0
```

The `if c:` line is the whole personality of a dense retriever: a token it has no concept for contributes nothing. Feed it a query that is *only* rare tokens — "which seat is 14c" — and its concept vector is empty, so every document scores zero. It has not made a mistake; it has no opinion.

### The head-to-head: neither method wins

Split the six queries by type and the tie stops looking like a tie and starts looking like a division of labor.

```
# $ python3 headto.py --split
#   method           exact        paraphrase
#   lexical (wiki)   3/3          0/3
#   dense (RAG)      0/3          3/3
```

run: 2026-08-25 · fixture · `python3 headto.py --split`

Lexical answers every exact-token query and not one paraphrase; dense does the perfect reverse. This is the earned form of the labs' opinion: "wiki beats RAG" is true if your users ask for exact strings and false if they paraphrase, and since real users do both, the honest statement is that *neither method is the answer and the winner is whatever your query mix happens to be*. Shipping the champion — the better single method — caps you at the better half and abandons the other. On this eval set that is 3 of 6, no matter which champion you crown.

<svg viewBox="0 0 700 200" role="img" aria-label="Two retrievers as two witnesses. Lexical sees exact tokens 14c and b4 but is blind to paraphrase. Dense sees concepts commute equals drive but is blind to rare tokens. A two-by-two shows lexical answering exact 3 of 3 and paraphrase 0 of 3, dense the reverse.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="22" fill="var(--muted)">each retriever is blind to what the other sees</text>
    <rect x="30" y="40" width="300" height="60" rx="6" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="45" y="62" fill="var(--ink)">lexical (wiki)</text>
    <text x="45" y="80" fill="var(--s1)" font-size="9">sees: 14c, b4, 28th (exact strings)</text>
    <text x="45" y="94" fill="var(--s2)" font-size="9">blind: commute ~ drive, checkup ~ dentist</text>
    <rect x="370" y="40" width="300" height="60" rx="6" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="385" y="62" fill="var(--ink)">dense (RAG)</text>
    <text x="385" y="80" fill="var(--s1)" font-size="9">sees: commute ~ drive, checkup ~ dentist</text>
    <text x="385" y="94" fill="var(--s2)" font-size="9">blind: 14c, b4, 28th (no concept)</text>
    <g font-size="10">
      <text x="30" y="135" fill="var(--muted)">hit@1 by type</text>
      <text x="200" y="135" fill="var(--ink)">exact</text><text x="330" y="135" fill="var(--ink)">paraphrase</text>
      <text x="30" y="158" fill="var(--ink)">lexical</text><text x="205" y="158" fill="var(--s1)">3/3</text><text x="345" y="158" fill="var(--s2)">0/3</text>
      <text x="30" y="180" fill="var(--ink)">dense</text><text x="205" y="180" fill="var(--s2)">0/3</text><text x="345" y="180" fill="var(--s1)">3/3</text>
    </g>
  </g>
</svg>
^ The two retrievers see disjoint halves of the eval set: lexical answers exact-token queries and dense answers paraphrases, each blind where the other sees. No single method covers the diagonal, which is why picking a champion caps at half.

### Strategy #2 — fuse them, and let a blind method vote. This is the bug.

If each method owns a half, fuse their rankings and cover the whole board. The fusion adds a reciprocal-rank vote from each method — a standard, scale-free way to combine rankers that disagree on scale.

```
# headto.py:104-115 — COMPLETE (fuse two rankings; the abstain flag is the whole story)
def fuse(docs, query, concepts, abstain):
    """Reciprocal-rank fusion. If abstain is True, a retriever with no signal sits
    the query out; if False (the bug), it votes its arbitrary tie-broken order."""
    fused = {did: 0.0 for did in docs}
    for score in BASE:
        ranked = rank(docs, query, score, concepts)
        if abstain and silent(ranked):
            continue
        for r, (did, _) in enumerate(ranked, 1):
            fused[did] += 1.0 / (RRF_K + r)
    ordered = sorted(fused.items(), key=lambda x: (-x[1], x[0]))
    return ordered
```

Run the fuse with `abstain=False` and it scores 1 of 6 — worse than either method alone. Predict where it goes wrong before the next block: on an exact-token query, what does the dense retriever, which scored zero for every document, contribute to the vote? Write it down.

```
# $ python3 headto.py --fuse "which seat is 14c"
#   lexical top      ('d_flight', 2)
#   dense   top      ('d_bill', 0.0)  (SILENT — all scores 0)
#   fuse no-abstain  -> d_bill
#   fuse abstain     -> d_flight
```

run: 2026-08-25 · fixture · `python3 headto.py --fuse "..."`

The dense retriever scored every document zero, so its "ranking" is just the alphabetical tie-break — `d_bill` first, purely because 'b' sorts early. With no abstention it casts that meaningless order as a full set of votes, and because `d_bill` sits at rank 1 in that phantom ranking, it collects a top vote that outweighs lexical's correct pick of `d_flight` sitting at a middling rank in the *other* phantom half. A witness who saw nothing was made to testify, named the alphabetically-first suspect, and outvoted the witness who read the plate. The fuse did not combine two signals; it combined one signal with one coin flip.

<svg viewBox="0 0 700 200" role="img" aria-label="For the query seat 14c: lexical ranks d_flight first with a real score; dense scored everything zero so its ranking is alphabetical, d_bill first. Without abstention the fuse adds dense's phantom top vote for d_bill and picks d_bill, the wrong answer; with abstention dense drops out and the fuse picks d_flight.">
  <g font-family="var(--mono)" font-size="9.5">
    <text x="20" y="20" fill="var(--muted)">query "which seat is 14c" — dense is silent (all scores 0)</text>
    <text x="30" y="48" fill="var(--ink)">lexical vote</text>
    <rect x="150" y="36" width="150" height="18" rx="3" fill="var(--s1)"></rect><text x="156" y="49" fill="var(--ink)" font-size="8">d_flight @1 (real)</text>
    <text x="30" y="80" fill="var(--ink)">dense vote</text>
    <rect x="150" y="68" width="150" height="18" rx="3" fill="var(--s2)"></rect><text x="156" y="81" fill="var(--ink)" font-size="8">d_bill @1 (alphabetical — phantom)</text>
    <text x="330" y="60" fill="var(--muted)">no abstention:</text>
    <rect x="330" y="68" width="230" height="20" rx="4" fill="var(--panel)" stroke="var(--s2)"></rect>
    <text x="340" y="82" fill="var(--s2)">phantom top vote wins -> d_bill (WRONG)</text>
    <line x1="20" y1="110" x2="680" y2="110" stroke="var(--grid)" stroke-dasharray="3 3"></line>
    <text x="30" y="140" fill="var(--ink)">with abstain</text>
    <rect x="150" y="128" width="150" height="18" rx="3" fill="var(--s1)"></rect><text x="156" y="141" fill="var(--ink)" font-size="8">d_flight @1 (real)</text>
    <text x="330" y="132" fill="var(--muted)">dense sat out:</text>
    <rect x="330" y="128" width="230" height="20" rx="4" fill="var(--panel)" stroke="var(--s1)"></rect>
    <text x="340" y="142" fill="var(--s1)">only real signal remains -> d_flight (RIGHT)</text>
    <text x="20" y="184" fill="var(--muted)">the bug is not the fusion formula; it is letting a no-signal method vote.</text>
  </g>
</svg>
^ The exact query, fused two ways. The dense retriever is silent, so its ranking is alphabetical noise; counting it hands the win to `d_bill`, while abstaining leaves only lexical's real vote and the right answer stands. The formula never changed — only whether the blind witness testifies.

### Strategy #3 — let the blind method abstain

The fix is the `silent` check: a retriever whose best score is zero has no signal, so it sits the query out instead of voting its tie-break.

```
# headto.py:88-91 — COMPLETE (no signal means no vote)
def silent(scored):
    """A retriever has no signal on this query when its best score is 0 -- its
    order is then just the alphabetical tie-break, not evidence."""
    return scored[0][1] == 0
```

With `abstain=True`, every exact query is decided by lexical alone and every paraphrase by dense alone, and the fused retriever scores a clean 6 of 6 — beating both methods and the champion. Nothing about the ranking math changed; the fix was refusing to count a vote that carried no information. The self-test pins the whole ladder down:

```
# $ python3 headto.py --check
#   hit@1  lexical=3 dense=3 champion=3 naive-fuse=1 abstain-fuse=6  (of 6)
#   neither pure method answers everything = True
#   the champion is just the best single method, still short of all = True
#   naive fusion is WORSE than shipping the champion = True (1 < 3)
#   abstaining fusion answers every query = True (6/6)
#   lexical wins exact (3/3), dense wins paraphrase (3/3) = True
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · n=6 queries · `python3 headto.py --check`

<svg viewBox="0 0 700 190" role="img" aria-label="A ladder of five approaches by hit@1 out of 6: lexical 3, dense 3, ship-the-champion 3, naive fusion 1 (a dip below the others), abstaining fusion 6. The naive fuse dips before abstention climbs to a full sweep.">
  <g font-family="var(--mono)" font-size="10">
    <text x="30" y="22" fill="var(--muted)">hit@1 out of 6 — the dip at naive fusion, then the sweep</text>
    <line x1="150" y1="40" x2="150" y2="176" stroke="var(--grid)"></line>
    <text x="20" y="58" fill="var(--ink)">lexical</text><rect x="150" y="48" width="195" height="16" rx="3" fill="var(--muted)"></rect><text x="352" y="61" fill="var(--muted)">3</text>
    <text x="20" y="84" fill="var(--ink)">dense</text><rect x="150" y="74" width="195" height="16" rx="3" fill="var(--muted)"></rect><text x="352" y="87" fill="var(--muted)">3</text>
    <text x="20" y="110" fill="var(--ink)">champion</text><rect x="150" y="100" width="195" height="16" rx="3" fill="var(--muted)"></rect><text x="352" y="113" fill="var(--muted)">3</text>
    <text x="20" y="136" fill="var(--ink)">naive fuse</text><rect x="150" y="126" width="65" height="16" rx="3" fill="var(--s2)"></rect><text x="222" y="139" fill="var(--s2)">1  &lt;- worse than either</text>
    <text x="20" y="162" fill="var(--ink)">abstain fuse</text><rect x="150" y="152" width="390" height="16" rx="3" fill="var(--s1)"></rect><text x="547" y="165" fill="var(--s1)">6/6</text>
  </g>
</svg>
^ The five approaches by hit@1. Three tie at half; the naive fuse dips to 1, below every method it combines; only the abstaining fuse clears the champion and sweeps all six.

**"Which retriever is better?" is the wrong question; each owns a different query type, so the answer is to run both — but a retriever with no signal must abstain, or its noise outvotes the one that knows.**

### The running tally

| approach | hit@1 | what happened |
|---|---|---|
| lexical (wiki) | 3/6 | every exact token, no paraphrase |
| dense (RAG) | 3/6 | every paraphrase, no exact token |
| ship the champion | 3/6 | the wiki-vs-RAG debate; caps at the better half |
| fuse, no abstention | 1/6 | a silent method votes noise and outweighs signal |
| fuse, with abstention | 6/6 | each query decided by the method that can see it |

The eval set never changed; only how we combined the two views did. The dip at row four is the lesson: fusion is not free, and the most natural way to do it is worse than either input, because combining a real ranking with a phantom one is a way to inject noise, not cancel it. Abstention is the discipline that makes fusion actually additive.

### What we did not settle

The corpus is a fixture with cleanly separated query types, so lexical and dense never both have real signal on the same query — in the wild they usually do, and then fusion has to weigh two genuine votes, which is where the reciprocal-rank constant and per-method weights start to matter and where naive score-adding (lexical's integers against dense's cosine) fails for a *different* reason than the one here. Three things we skipped: the concept map is a hand-built stand-in, so the dense numbers show the mechanism, not a specific model's recall; real cost and latency were not measured — a dense retriever pays an embedding cost per query and per document that lexical does not, and a full head-to-head records that alongside accuracy; and "hit@1" ignores that a fused ranking's second and third slots matter when you inject the top-k, not just the top-1. The verdict that transfers is the shape, not the 6/6: neither method dominates, and fusion pays off only when a blind method knows to stay quiet.

## Build

The pipeline in one paragraph: run a lexical and a dense retriever on one shared, gold-labelled eval set; report hit@1 for each and split it by query type to see who owns what; then fuse their rankings with reciprocal-rank fusion, and make any retriever with no signal on a query abstain rather than vote its tie-break. Never crown a single champion from an aggregate score, and never let a zero-signal retriever into the vote.

We opened on the five-row head-to-head. The row that matters:

```
# modules/context-and-retrieval/code/retrieval-inter-02/ — COMPLETE, run from that directory
$ python3 headto.py --methods
  fuse, with abstention   6/6  (the fix)
```

Now run it on your own two retrievers and your own queries. Label each query's type honestly and split the score — if one method wins every type, you have not stress-tested the loser's home turf, so add queries it should own. Your number to beat is the **champion's score**: your fused-with-abstention retriever must clear the better single method, and if it does not, find the query where a silent method is still voting. Bring back the split table and the five-row ladder, and mark the query where fusion first went wrong. Good luck.

## Definition of done

- [ ] A lexical and a dense retriever over one shared corpus, both returning ranked hits
- [ ] Your own `corpus.json`: gold-labelled queries tagged exact vs paraphrase, both types present
- [ ] hit@1 split by query type, showing which method owns which type
- [ ] Reciprocal-rank fusion with an abstention rule: a zero-signal retriever casts no vote
- [ ] The champion and the no-abstention fuse kept for contrast, so the dip is visible
- [ ] `python3 headto.py --check` printing SELF-TEST PASS: neither wins, naive fuse is worse, abstaining fuse sweeps
- [ ] The five-row ladder recorded, and the earned verdict on wiki-vs-RAG for your query mix
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Lexical and dense both scored 3/6. Say why that is a division of labor and not a tie, and what single fact about your users decides which one "wins".
2. Fusing two 3/6 methods scored 1/6 — below either. Explain the mechanism that made the fuse worse than its inputs.
3. Give the one rule that took the fuse from 1/6 to 6/6, and state precisely when a retriever should invoke it.
4. On "which seat is 14c" the dense retriever returned `d_bill`. It never saw `d_bill` as relevant — why did it name it, and what should it have done instead?
5. Your own head-to-head produced a split table. Which method owned which query type, and did fusion beat your champion — if not, which query broke it?

## External resources

- faisalmahdy/agent — `agent/memory/retrieval.py` — my summary: the dense/embedding ranker that is one half of this head-to-head; read it for the real cosine-over-embeddings this module simulates with a concept map, and note it already blends signals, which is fusion by another name.
- Cormack, Clarke & Büttcher, *Reciprocal Rank Fusion* (SIGIR 2009) — https://plg.uwaterloo.ca/~gvcormack/cormacksigir09-rrf.pdf — my summary: the four-line fusion this module uses and why rank-based combining beats score-based across rankers with incompatible scales; read it for the RRF constant's role and treat the abstention rule here as the small operational patch the paper's clean setting does not force.
- Anthropic, *Introducing Contextual Retrieval* — https://www.anthropic.com/news/contextual-retrieval — my summary: a production hybrid of embeddings plus lexical BM25 with reranking, measured; read it for the real-world version of "neither method alone is enough" and for the cost and reranking axes this module names but does not measure.
