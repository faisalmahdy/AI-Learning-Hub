---
id: retrieval-inter-01
title: Chunking: cut too fine and the answer falls between the pieces
topic: context-and-retrieval
level: intermediate
status: ready
time: 8-10h
summary: Index whole notes and one fact is buried in a long note the retriever ranks below a shorter off-topic one — 4/5 recall at 31 tokens injected. Cut into 12-token windows and recall drops to 3/5, because a no-overlap boundary splits two facts down the middle so no chunk holds either whole. Add 6 tokens of overlap and recall climbs to 5/5 at 12 tokens injected, beating whole-document retrieval on both accuracy and cost — because chunk size trades recall for precision and overlap buys back the recall the cut destroyed.
eli5: Cut a page into strips to file them. Whole pages are easy to find but bulky; tiny strips are tidy but a sentence that crosses a cut gets sliced in half and neither strip answers. Overlap the cuts and every sentence stays whole on some strip.
---

## Why this module

The previous module measured retrieval and left one dial untouched: what a "document" even is. The labs' retrieval systems index whole pages — the wiki compiler embeds an entire note as one vector — and the scan names this as a genuine gap: "chunking (whole pages embedded today)." A whole-page index has two problems this module makes you feel. First, the answer to a question is usually one sentence inside a page that is mostly about other things, so a long page's vector is dominated by its bulk and the relevant sentence is drowned — the exact length dilution the last module fixed for scoring, now back at the level of the index. Second, when you retrieve a whole page you must inject the whole page, and context is the budget you are always overspending.

The obvious fix is to cut pages into smaller chunks so each fact gets its own vector. This module builds that, and then trips over the trap that makes chunking subtle: cut with straight, abutting cuts and a fact that happens to lie across a cut is severed, its two halves filed as separate chunks, and neither chunk can answer. You will watch recall get *worse* when you first shrink the chunk — from 4 of 5 to 3 of 5 — before a three-character change to the cutter makes it better than whole pages ever were.

You need `retrieval-basic-01` — its length-fair cosine and its gold-labelled measurement are the tools here; this module only changes what gets indexed. Everything runs offline against a five-note fixture, stdlib Python 3, `$0.00`, one sitting. The one instinct to unlearn: that smaller chunks are simply better. Chunk size is a dial with a wrong answer at both ends, and the cut *strategy* matters as much as the size.

Here is where we land — the same corpus indexed four ways, each scored for recall and for the tokens it makes you inject:

```
# modules/context-and-retrieval/code/retrieval-inter-01/ — COMPLETE, run from that directory
$ python3 chunk.py --ablate

CHUNK ABLATION — recall@1 (top chunk holds the whole fact) and cost
--------------------------------------------------------------------
  chunker                recall@1   avg tokens injected
  whole document          4/5         31.4
  24-token, overlap 6     5/5         22.6
  12-token, no overlap    3/5         12.0
  12-token, overlap 6     5/5         12.0
```

run: 2026-08-25 · retriever is deterministic; corpus is a fixture · n=5 queries, 5 notes · `python3 chunk.py --ablate`

Read it top to bottom as a story. Whole documents get 4 of 5 but haul in 31 tokens a query. Shrinking to 12-token windows with straight cuts should help and instead *drops* to 3 of 5. The only difference between that row and the last is six tokens of overlap — and that row scores a perfect 5 of 5 at the same 12-token cost, beating whole documents on both axes. This module is the three rows below the first, and why they go down before they go up.

## Concepts

Named here so you can find them again; each is built below.

- **Chunk** — the unit you actually index and retrieve: a slice of a document, not the whole thing.
- **Chunk size** — how many tokens per slice. The dial with a wrong answer at both ends.
- **Stride / overlap** — how far the window steps. Stride equal to size means no overlap; stride smaller means neighbouring chunks share tokens.
- **The boundary split** — a fact whose tokens land in two different abutting chunks, so no single chunk holds it whole.
- **recall@1** — did the single top-ranked chunk contain the entire gold fact? The accuracy axis.
- **Injected tokens** — the size of the chunk you return; the cost axis. Chunking is a recall-versus-cost trade.

## Worked example

Source: faisalmahdy/agent — `agent/memory/retrieval.py` embeds and ranks a wiki page as one unit; the scan's skills matrix records the gap plainly — "chunking (whole pages embedded today)." This module builds the chunking layer that file never had, and measures what it buys with the same cosine that file already uses.

Script and fixture: `modules/context-and-retrieval/code/retrieval-inter-01/` — `chunk.py`, and `docs.json`, five personal notes, each holding one two-token fact. Every command runs from there.

### The frame: filing a page by cutting it into strips

Think of indexing as filing a document by cutting it into strips and dropping each strip in a drawer. The whole-page strategy files each page as one strip: easy to find the right page, but the fact you wanted is a line buried in it, and you carry the whole page back to your desk. So you cut finer, into fixed-length strips — and here is the catch that governs everything. If you cut with straight scissors at every twelfth token, a sentence like "the seat is 14c" whose words straddle a cut gets severed: "…the seat is" on one strip, "14c on the evening flight…" on the next. Now no single strip contains "seat" and "14c" together, and a query for your seat matches a strip that has one word but not the other. The fact is still in the cabinet; you sliced it in half and filed the halves apart.

The fix is to overlap the cuts — shingle them, so each strip starts partway into the last. Any sentence shorter than the overlap survives whole on at least one strip. That is the entire idea, and the numbers below are it happening.

### Look at the data: five notes, five facts, two of them living on a boundary

```
# $ python3 chunk.py --index 12 12
#   d_flight -> 3 chunk(s)
#   d_health -> 3 chunk(s)
#   ...
#   13 chunks total across 5 docs.
```

run: 2026-08-25 · fixture · `python3 chunk.py --index 12 12`

Each note is about thirty tokens and carries one fact: the flight note hides "seat 14c", the health log hides "dentist … 9am", and so on. Two of those facts were placed on purpose so their two tokens fall on opposite sides of a twelve-token boundary — you will see exactly where in a moment. The other three sit comfortably inside a single window. That mix is the whole experiment: three facts a straight cut leaves whole, two it severs.

### Strategy #1 — index whole documents. The fact drowns in the page.

The baseline indexes each note as one chunk and retrieves with the cosine from the last module. It gets four of five — and the one it misses is the tell.

```
# chunk.py:73-86 — COMPLETE (index whole docs / any chunker, then rank chunks by cosine)
def build_index(docs, size, stride):
    """One flat list of (doc_id, chunk_index, chunk_tokens) across the corpus."""
    idx = []
    for did, text in docs.items():
        for ci, ch in enumerate(chunks_of(text, size, stride)):
            idx.append((did, ci, ch))
    return idx


def top_chunk(index, query):
    q_vec = tf(tokens(query))
    scored = [((did, ci, ch), cosine(q_vec, tf(ch))) for (did, ci, ch) in index]
    scored.sort(key=lambda x: (-x[1], x[0][0], x[0][1]))
    return scored[0][0]        # (doc_id, chunk_index, chunk_tokens)
```

The query it misses is "what time is the dentist appointment". The dentist fact lives in `d_health`, a health log that is mostly about sleep, meals, and the gym, mentioning the dentist once near the end. As one vector that page is *about* health habits, not the dentist, so cosine ranks a shorter, blander note above it and the answer never surfaces. This is last module's length dilution wearing a new hat: there we fixed it by normalising the score, but normalisation cannot rescue a page whose subject is genuinely diluted across thirty tokens. The fix has to happen at the index — cut the dentist sentence out of the health log so it can stand on its own.

<svg viewBox="0 0 700 190" role="img" aria-label="A long health-log document shown as a bar mostly filled with sleep, meals, and gym tokens, with a small dentist-appointment slice near the end. As one vector the document reads as health habits; the dentist fact is a small fraction, so a whole-document retriever ranks it below a shorter note.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="24" fill="var(--muted)">d_health as one vector — the dentist fact is a sliver of a page about habits</text>
    <rect x="20" y="40" width="620" height="34" rx="4" fill="var(--panel)" stroke="var(--line)"></rect>
    <rect x="24" y="44" width="150" height="26" fill="var(--grid)"></rect><text x="34" y="61" fill="var(--muted)" font-size="9">sleep</text>
    <rect x="176" y="44" width="140" height="26" fill="var(--grid)"></rect><text x="186" y="61" fill="var(--muted)" font-size="9">meals</text>
    <rect x="318" y="44" width="160" height="26" fill="var(--grid)"></rect><text x="328" y="61" fill="var(--muted)" font-size="9">gym, mood</text>
    <rect x="480" y="44" width="120" height="26" fill="var(--s1)"></rect><text x="490" y="61" fill="var(--ink)" font-size="9">dentist 9am</text>
    <rect x="602" y="44" width="34" height="26" fill="var(--grid)"></rect>
    <text x="20" y="104" fill="var(--s2)">whole-doc cosine ranks this below a shorter note -> the dentist query misses</text>
    <text x="20" y="132" fill="var(--muted)" font-size="9">cut the "dentist 9am" slice into its own chunk and it stands on its own topic</text>
    <rect x="480" y="146" width="120" height="26" rx="4" fill="var(--s1)"></rect><text x="490" y="163" fill="var(--ink)" font-size="9">dentist 9am</text>
    <text x="610" y="163" fill="var(--muted)" font-size="9">a chunk that is only about the appointment</text>
  </g>
</svg>
^ The dentist fact is one slice of a long health log; as a single vector the page reads as habits, so a whole-document retriever drowns it. Chunking exists to give that slice its own vector.

### Strategy #2 — cut into 12-token windows with straight cuts. This is the bug.

So cut the pages into small windows and index each. The cutter is a sliding window; stride equal to size means the windows abut with no overlap.

```
# chunk.py:56-70 — COMPLETE (windows of `size` tokens stepping by `stride`)
def chunks_of(text, size, stride):
    """Windows of `size` tokens stepping by `stride`. stride==size means no
    overlap (windows abut); stride<size means the windows overlap by size-stride.
    size==0 is the whole document as a single chunk."""
    toks = tokens(text)
    if size == 0 or size >= len(toks):
        return [toks]
    out = []
    i = 0
    while i < len(toks):
        out.append(toks[i:i + size])
        if i + size >= len(toks):
            break
        i += stride
    return out
```

Predict before you run it. Smaller chunks should isolate each fact and *raise* recall. Does it? The ablation says 12-token no-overlap scores 3 of 5 — worse than whole documents. Two facts vanished. Here is where they went:

```
# $ python3 chunk.py --miss
#   which seat is on my flight         gold ['seat', '14c'] at token positions [10, 12]
#        -> a boundary at 12/24/... falls between them; no 12-token
#           window holds both, so the top chunk cannot answer.
#   what time is the dentist appointme gold ['dentist', '9am'] at token positions [23, 27]
#        -> a boundary at 12/24/... falls between them; no 12-token
#           window holds both, so the top chunk cannot answer.
```

run: 2026-08-25 · fixture · `python3 chunk.py --miss`

"seat" is token 10 and "14c" is token 12 — the cut at 12 falls between them, so "seat" is the tail of chunk one and "14c" is the head of chunk two. A `covers` check makes the failure precise: a chunk answers only if it holds *every* token of the fact, and no twelve-token window holds both.

```
# chunk.py:91-105 — COMPLETE (a chunk answers only if it holds the whole fact; recall + cost)
def covers(chunk_toks, gold_toks):
    """A chunk answers the query only if it holds every token of the gold fact."""
    s = set(chunk_toks)
    return all(t in s for t in gold_toks)


def evaluate(docs, queries, size, stride):
    hits = 0
    injected = []
    for item in queries:
        did, ci, ch = top_chunk(build_index(docs, size, stride), item["q"])
        injected.append(len(ch))
        if did == item["gold_doc"] and covers(ch, item["gold"]):
            hits += 1
    return hits, sum(injected) / len(injected)
```

The fact was in the corpus the entire time. The chunker hid it — not by losing data, but by drawing a line through the middle of it. This is the most common and most invisible retrieval bug there is: it passes every "is the text indexed?" check, because every token *is* indexed, just never together.

<svg viewBox="0 0 700 210" role="img" aria-label="The flight note as a token strip. A no-overlap cut at token 12 separates 'seat' at position 10 from '14c' at position 12 into two chunks, so neither holds both. An overlapping window from token 6 to 18 contains both, recovering the fact.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="20" fill="var(--muted)">d_flight tokens 6..18   (seat = 10, 14c = 12)</text>
    <g>
      <rect x="60" y="30" width="52" height="24" fill="var(--grid)" stroke="var(--panel)"></rect><text x="74" y="46" fill="var(--muted)">the</text>
      <rect x="112" y="30" width="70" height="24" fill="var(--grid)" stroke="var(--panel)"></rect><text x="120" y="46" fill="var(--muted)">assigned</text>
      <rect x="182" y="30" width="60" height="24" fill="var(--s1)" stroke="var(--panel)"></rect><text x="194" y="46" fill="var(--ink)">seat</text>
      <rect x="242" y="30" width="40" height="24" fill="var(--grid)" stroke="var(--panel)"></rect><text x="252" y="46" fill="var(--muted)">is</text>
      <rect x="282" y="30" width="56" height="24" fill="var(--s1)" stroke="var(--panel)"></rect><text x="294" y="46" fill="var(--ink)">14c</text>
      <rect x="338" y="30" width="40" height="24" fill="var(--grid)" stroke="var(--panel)"></rect><text x="348" y="46" fill="var(--muted)">on</text>
      <rect x="378" y="30" width="56" height="24" fill="var(--grid)" stroke="var(--panel)"></rect><text x="388" y="46" fill="var(--muted)">the</text>
    </g>
    <line x1="262" y1="24" x2="262" y2="70" stroke="var(--s2)" stroke-width="2"></line>
    <text x="200" y="84" fill="var(--s2)" font-size="9">no-overlap cut at token 12</text>
    <rect x="60" y="96" width="202" height="18" rx="3" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"></rect>
    <text x="66" y="109" fill="var(--s2)" font-size="8">chunk [0:12] has seat, not 14c</text>
    <rect x="262" y="96" width="172" height="18" rx="3" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"></rect>
    <text x="268" y="109" fill="var(--s2)" font-size="8">chunk [12:24] has 14c, not seat</text>
    <rect x="60" y="140" width="374" height="20" rx="3" fill="none" stroke="var(--s1)" stroke-width="1.5"></rect>
    <text x="66" y="154" fill="var(--s1)" font-size="8">overlap window [6:18] holds seat AND 14c — recovered</text>
    <text x="20" y="188" fill="var(--muted)" font-size="9">straight cuts sever a fact on the boundary; a shingled window keeps it whole.</text>
  </g>
</svg>
^ The flight fact, cut. A no-overlap boundary at token 12 puts "seat" in one chunk and "14c" in the next, so neither answers; an overlapping window spanning the boundary holds both. The severed fact was never missing, only divided.

### Strategy #3 — overlap the windows. The recall comes back, cheaper than whole pages.

The fix is to step the window by less than its width so consecutive chunks share tokens. A window of twelve tokens stepping by six overlaps its neighbour by six, and any fact whose tokens are within six of each other now lands whole inside at least one window. The cutter code does not change — only the stride argument does, from `12` to `6`.

```
# chunk.py:110-116 — COMPLETE (the four configs the ablation runs)
CONFIGS = [
    ("whole document", 0, 0),
    ("24-token, overlap 6", 24, 18),
    ("12-token, no overlap", 12, 12),
    ("12-token, overlap 6", 12, 6),
]
```

Run the ablation and the last row is the payoff: 12-token windows with overlap 6 score 5 of 5 — every fact, including the two the straight cut severed and the dentist fact that drowned in the whole page — while injecting twelve tokens a query instead of thirty-one. It beats whole-document retrieval on accuracy *and* cost at once, which almost nothing in this hub does; usually you trade. Chunking with overlap is the rare free lunch, and the reason is that it fixes two different failures with one move: it isolates the buried fact (helping recall the way Strategy 1 could not) and it keeps boundary facts whole (fixing the damage Strategy 2 did).

The self-test nails all of it down:

```
# $ python3 chunk.py --check
#   recall@1: whole=4/5  12-noverlap=3/5  12-overlap=5/5  24-overlap=5/5
#   no-overlap loses recall the overlap chunker keeps = True (3 < 5)
#   12-overlap recall >= whole-doc recall = True (5 >= 4), and cheaper = True (12.0 < 31.4 tok)
#   every gold fact lives whole inside some 12-overlap chunk = True (5/5)
#   SELF-TEST PASS  split_shows=True  recovers=True  cheaper=True  reachable=True  det=True
```

run: 2026-08-25 · deterministic · n=5 queries · `python3 chunk.py --check`

The `reachable` line is the one that proves the diagnosis rather than the symptom: every gold fact provably lives whole inside *some* 12-overlap chunk, so the recall ceiling is real and the no-overlap chunker's misses were self-inflicted, not a property of the data.

<svg viewBox="0 0 700 210" role="img" aria-label="A scatter of the four chunkers on two axes: injected tokens on the horizontal, recall on the vertical. Whole document is high-cost at 4 of 5; 12-token no-overlap is low-cost but only 3 of 5; 12-token overlap 6 and 24-token overlap 6 are both 5 of 5, with the 12-overlap one cheapest.">
  <g font-family="var(--mono)" font-size="9">
    <text x="30" y="20" fill="var(--muted)">recall vs cost — down-and-right is the no-overlap trap, up-and-left is the win</text>
    <line x1="70" y1="170" x2="660" y2="170" stroke="var(--grid)"></line>
    <line x1="70" y1="40" x2="70" y2="170" stroke="var(--grid)"></line>
    <text x="360" y="196" fill="var(--muted)" text-anchor="middle">injected tokens per query (cost) -></text>
    <text x="24" y="105" fill="var(--muted)" transform="rotate(-90 24 105)">recall -></text>
    <circle cx="150" cy="90" r="6" fill="var(--s1)"></circle><text x="160" y="86" fill="var(--ink)">12-overlap 6  5/5 @ 12</text>
    <circle cx="330" cy="90" r="6" fill="var(--s1)"></circle><text x="340" y="86" fill="var(--ink)">24-overlap 6  5/5 @ 23</text>
    <circle cx="150" cy="140" r="6" fill="var(--s2)"></circle><text x="160" y="150" fill="var(--s2)">12-no-overlap  3/5 @ 12</text>
    <circle cx="430" cy="110" r="6" fill="var(--muted)"></circle><text x="440" y="106" fill="var(--muted)">whole doc  4/5 @ 31</text>
  </g>
</svg>
^ The four chunkers on recall against cost. No-overlap sits low (the split); whole-document sits far right (the cost); both overlap chunkers reach full recall, and 12-overlap does it cheapest — up and to the left of everything.

### The running tally

| chunker | recall@1 | tokens injected | what happened |
|---|---|---|---|
| whole document | 4/5 | 31.4 | the dentist fact drowned in a long page |
| 12-token, no overlap | 3/5 | 12.0 | two facts severed on the boundary |
| 24-token, overlap 6 | 5/5 | 22.6 | whole recall, moderate cost |
| 12-token, overlap 6 | 5/5 | 12.0 | full recall at the smallest cost |

The corpus never changed; only the cut did. Shrinking the chunk helped the drowned fact and hurt the boundary facts, which is why recall dipped before it rose — the dip is not noise, it is a second failure mode the first strategy did not have. Overlap is what lets you shrink safely.

**Chunk size trades recall for precision; a no-overlap cut throws away recall for free, and overlap is the three-token change that buys it back.**

### What we did not settle

The corpus is a fixture with two-token facts, so the split is clean and the recovery is total. Real complications we skipped: facts longer than the overlap still split, so overlap size is itself a dial you tune against your facts' length, not a constant; semantic chunking cuts on sentence and section boundaries instead of a fixed token count, which avoids most mid-fact cuts but makes chunk sizes uneven and the cost harder to predict; and this measured retrieval of the chunk, not the answer the model then writes from it — a tight chunk that omits the surrounding context can retrieve perfectly and still mislead the generator, which is why production systems attach a little parent-document context to each chunk. The dial here is size and overlap; the next dials are where you cut and how much neighbourhood you carry.

## Build

The pipeline in one paragraph: cut each document into overlapping token windows; index every window as its own vector; retrieve the single best window with length-fair cosine; and to choose the chunker, measure recall@1 against gold facts and the tokens each chunker injects, sweeping size and overlap. Never ship a no-overlap fixed-size cutter, and never assume smaller is better without the recall curve.

We opened on the ablation. The winning row, again:

```
# modules/context-and-retrieval/code/retrieval-inter-01/ — COMPLETE, run from that directory
$ python3 chunk.py --ablate
  12-token, overlap 6     5/5         12.0
```

Now sweep your own corpus. The dials are `size` and `stride` in `CONFIGS`: point the chunker at your notes, label a gold fact per query, and plot recall@1 and injected tokens across a few sizes with and without overlap. Your number to beat is not recall alone — it is **recall at a fixed injected-token budget**: the chunker that answers the most queries per token you spend. Add a fact whose two words sit exactly on a boundary and confirm a no-overlap cut drops it while overlap keeps it. Bring back the curve — recall against cost for four chunkers — and mark the knee. Good luck.

## Definition of done

- [ ] A chunker that cuts documents into fixed-size token windows with a configurable overlap
- [ ] Your own `docs.json`: notes with one gold fact each, at least one placed on a chunk boundary
- [ ] recall@1 and average injected tokens computed for whole-doc, small no-overlap, and small-overlap chunkers
- [ ] A `covers` check that counts a hit only when the top chunk holds every token of the fact
- [ ] `python3 chunk.py --check` printing SELF-TEST PASS: the split shows, overlap recovers it, it is cheaper, every fact is reachable, deterministic
- [ ] The recall-versus-cost numbers for at least four chunkers, and the knee identified
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Whole-document retrieval missed the dentist query even though the fact was indexed. Say why, and connect it to the length lesson from the previous module.
2. Shrinking to 12-token chunks *lowered* recall from 4/5 to 3/5. Explain the failure mode that caused the drop, and why it did not exist for whole documents.
3. Give the one change that took the 12-token chunker from 3/5 to 5/5, and state the rule for which facts it rescues.
4. Define recall@1 and "injected tokens", and say why chunking is a trade between them — then name the one chunker in the table that did not trade.
5. Your own ablation printed a recall-versus-cost curve. Where was the knee, and which fact (if any) sat on a boundary and split?

## External resources

- faisalmahdy/agent — `agent/memory/retrieval.py` — my summary: the wiki ranker that embeds a whole page as one unit; read it to see the whole-document baseline this module improves on, and note that adding a chunking layer in front of its cosine is a drop-in change, not a rewrite.
- Anthropic, *Introducing Contextual Retrieval* — https://www.anthropic.com/news/contextual-retrieval — my summary: measures chunk-level retrieval failure and reduces it by prepending a short context blurb to each chunk before embedding; read it for the "chunk loses its surrounding context" problem this module flags in what-we-did-not-settle, and for how overlap and context together move the numbers.
- Pinecone, *Chunking Strategies for LLM Applications* — https://www.pinecone.io/learn/chunking-strategies/ — my summary: a practical tour of fixed-size, overlapping, sentence, and semantic chunking with the tradeoffs; read it for the semantic-chunking option this module names but does not build, and treat every claim as a hypothesis to run through your own recall-versus-cost harness.
