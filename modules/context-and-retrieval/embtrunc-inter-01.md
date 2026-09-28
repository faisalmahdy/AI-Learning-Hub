---
id: embtrunc-inter-01
title: Size chunks to the embedding model's token limit — a longer chunk is silently truncated and its tail is never embedded or retrievable
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: Every embedding model has a maximum input length measured in tokens — many sentence-transformer models cap at 512 — and the important thing about it is what happens when you exceed it: the model does not error and does not embed the whole input at reduced fidelity, it truncates, keeping the first max_len tokens and discarding the rest. For a chunk longer than the limit, the embedding represents only its beginning, so any fact past the cutoff contributes nothing to the vector because the tokens carrying it were dropped before the model saw them, and a query that should match that fact finds no signal for it and the chunk is not retrieved — even though the text is sitting right there in the stored chunk. The failure is completely silent: no exception, the embedding is produced and looks normal, and the tail of every over-long chunk is invisible to search, so it can pass every test that queries content near the start of chunks and fail only on queries about their ends. The fix is to chunk so each piece fits under the model's max length, measured in the model's own tokens — not characters or words, which undercount, since a 500-word chunk can blow past a 512-token limit — or to use a long-context embedding model. On a fixture where a 9-token chunk meets a 5-token model limit, truncation drops the tail holding the query term "answer", so the long chunk cannot match the query, while splitting into max_len-sized chunks puts "answer" inside a chunk's limit and restores retrieval.
eli5: Imagine a photocopier that can only copy the first page of anything you feed it, no matter how many pages you put in — and it never warns you, it just quietly copies page one and ignores the rest. If you feed it a 5-page document and later search the copies for something written on page 4, it's not there, even though your original clearly has it. Embedding models are like that copier but for text: they only "read" up to a fixed number of words' worth of tokens, and silently ignore anything after. So if a chunk of text is too long, whatever's near its end never makes it into the searchable version, and you can't find it. The fix is to cut your text into pieces small enough that the whole piece fits within what the model can read.
---

## Why this module

Chunking discussions usually focus on semantics — cut at topic boundaries, keep related sentences together, overlap the edges. All of that assumes the chunk you produce is actually embedded in full. There is a hard constraint underneath that assumption: the embedding model has a fixed maximum input length, and it enforces that limit not by complaining but by quietly throwing away everything past it. A chunk that exceeds the limit is not embedded poorly; its tail is not embedded at all.

This is easy to miss because nothing surfaces it. The embedding call returns a normal-looking vector of the right dimension, the index accepts it, retrieval runs. The only symptom is that queries about content near the end of long chunks come back empty, and if your evaluation set — as most do — asks about the salient content that tends to sit near the start of a passage, the bug never shows. It waits for a production query about a detail buried deep in a long chunk, finds nothing, and looks like a relevance failure rather than what it is: the detail was never in the vector.

The constraint is in tokens, which compounds the trap, because token count is larger than word count and varies by tokenizer. This module feeds an over-long chunk to a token-limited model and shows the tail dropping out of retrieval.

**An embedding model silently truncates input beyond its maximum token length, so a chunk longer than the limit has its tail excluded from the vector and unretrievable — chunks must be sized to fit the model's token limit, or the content past the cutoff is invisible to search.**

## Concepts

The fixture is a chunk's token sequence, the model's maximum token length, and a query term the searcher wants — a term that happens to sit in the chunk's tail.

```json filename=modules/context-and-retrieval/code/embtrunc-inter-01/embtrunc.json:3-5 COMPLETE
  "chunk": ["intro", "about", "the", "topic", "filler", "the", "answer", "is", "here"],
  "max_len": 5,
  "query_term": "answer"
}
```

The model embeds only the first max_len tokens — truncation modeled as taking the terms within that prefix. Splitting produces chunks of at most max_len tokens; a term is retrievable if it survives in some chunk's truncated embedding.

```python filename=modules/context-and-retrieval/code/embtrunc-inter-01/embtrunc.py:32-44 COMPLETE
def embed(tokens, max_len):
    """The model truncates to its max length: only the first max_len tokens are embedded."""
    return set(tokens[:max_len])


def split_to_fit(tokens, max_len):
    """Chunk so each piece is at most max_len tokens."""
    return [tokens[i:i + max_len] for i in range(0, len(tokens), max_len)]


def retrievable(term, chunks, max_len):
    """The term is retrievable if it survives in some chunk's truncated embedding."""
    return any(term in embed(c, max_len) for c in chunks)
```

`embed` takes only `tokens[:max_len]` — the model never sees the rest. So whether a term is retrievable depends entirely on whether it falls within the first max_len tokens of some chunk, which splitting controls and a single over-long chunk does not.

<svg role="img" aria-label="A 9-token chunk with a cutoff line after token 5: the first five tokens are embedded, the tail including the answer token is greyed out and dropped" viewBox="0 0 320 100">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">chunk of 9 tokens, model limit 5</text>
  <g font-size="6.5">
  <rect x="12" y="26" width="30" height="16" fill="var(--s1)"/><text x="16" y="37" fill="var(--panel)">intro</text>
  <rect x="44" y="26" width="30" height="16" fill="var(--s1)"/><text x="48" y="37" fill="var(--panel)">about</text>
  <rect x="76" y="26" width="24" height="16" fill="var(--s1)"/><text x="80" y="37" fill="var(--panel)">the</text>
  <rect x="102" y="26" width="30" height="16" fill="var(--s1)"/><text x="106" y="37" fill="var(--panel)">topic</text>
  <rect x="134" y="26" width="30" height="16" fill="var(--s1)"/><text x="138" y="37" fill="var(--panel)">filler</text>
  <rect x="168" y="26" width="24" height="16" fill="none" stroke="var(--line)"/><text x="172" y="37" fill="var(--muted)">the</text>
  <rect x="194" y="26" width="34" height="16" fill="none" stroke="var(--ink)"/><text x="197" y="37" fill="var(--ink)">answer</text>
  <rect x="230" y="26" width="18" height="16" fill="none" stroke="var(--line)"/><text x="233" y="37" fill="var(--muted)">is</text>
  <rect x="250" y="26" width="26" height="16" fill="none" stroke="var(--line)"/><text x="254" y="37" fill="var(--muted)">here</text>
  </g>
  <line x1="166" y1="20" x2="166" y2="48" stroke="var(--s2)" stroke-width="1.5" stroke-dasharray="3 2"/><text x="150" y="18" font-size="7" fill="var(--s2)">cutoff</text>
  <text x="10" y="66" font-size="7.5" fill="var(--s1)">embedded: first 5 tokens</text>
  <text x="10" y="80" font-size="7.5" fill="var(--muted)">dropped: 'the answer is here' — including the query term</text>
</svg>
^ The model embeds the first five tokens and drops everything after the cutoff, including the token 'answer' the query is looking for. The dropped tail is still in the stored chunk's text, but it never entered the vector, so search cannot find it.

**The embedding is the first max_len tokens only, so a term's retrievability depends on falling within some chunk's prefix — which splitting to fit guarantees and a single over-long chunk cannot.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the chunk-embedding step of an indexing pipeline, reduced to nine tokens and a five-token limit so the truncation is checkable by hand.

Run `--embed` to see what the model actually keeps.

```text filename=embtrunc.py --embed
  chunk tokens (9): ['intro', 'about', 'the', 'topic', 'filler', 'the', 'answer', 'is', 'here']
  embedded (first 5): ['intro', 'about', 'the', 'topic', 'filler']
  dropped tail:       ['the', 'answer', 'is', 'here']
```

The chunk has nine tokens; the model's limit is five. It embeds `intro about the topic filler` and drops `the answer is here`. The word "answer" — the thing a searcher would query for — is in the dropped tail, so it contributes nothing to the chunk's vector. Nothing about this is visible from outside: the embedding is produced normally, and the stored chunk still contains all nine tokens, so anyone reading the chunk sees "answer" plainly. It is only absent from the vector.

Now `--retrieve` tests whether the query term can be found, from the long chunk and from the splits.

```python filename=modules/context-and-retrieval/code/embtrunc-inter-01/embtrunc.py:62-63 COMPLETE
    long_ok = retrievable(term, [chunk], max_len)
    split_ok = retrievable(term, split_to_fit(chunk, max_len), max_len)
```

Only the split version finds it.

```text filename=embtrunc.py --retrieve
  from the long (truncated) chunk = False
  from max_len-sized splits       = True ([['intro', 'about', 'the', 'topic', 'filler'], ['the', 'answer', 'is', 'here']])
```

From the long chunk, "answer" is not retrievable — it was truncated away before embedding. Split the same tokens into five-token chunks and it becomes retrievable, because now "answer" sits in the second chunk's prefix, within the model's limit, so it enters that chunk's vector. The text did not change; only the chunking did. This is the entire fix: make every chunk short enough that the model embeds all of it, and nothing gets silently dropped.

<svg role="img" aria-label="Retrieval of the term answer: not retrievable from the long truncated chunk, retrievable after splitting into two max_len chunks" viewBox="0 0 320 100">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">is 'answer' retrievable?</text>
  <text x="10" y="40" font-size="8.5" fill="var(--s2)">long chunk (truncated)</text>
  <rect x="150" y="30" width="30" height="16" fill="var(--s2)"/><text x="156" y="42" font-size="8" fill="var(--panel)">no</text>
  <text x="186" y="42" font-size="8" fill="var(--ink)">tail dropped</text>
  <text x="10" y="70" font-size="8.5" fill="var(--s1)">split to fit</text>
  <rect x="150" y="60" width="60" height="16" fill="var(--s1)"/><text x="168" y="72" font-size="8" fill="var(--panel)">yes</text>
  <text x="216" y="72" font-size="8" fill="var(--ink)">'answer' within a chunk's limit</text>
  <text x="10" y="94" font-size="7.5" fill="var(--muted)">same tokens, different chunking — fitting the limit restores the tail</text>
</svg>
^ The term is unretrievable from the long chunk because truncation dropped it, and retrievable once the chunk is split so the term falls within a piece's token limit. The only change is the chunk size relative to the model's maximum.

**"answer" is unretrievable from the truncated long chunk but retrievable from max_len-sized splits — the content was always in the text; sizing the chunk to the model's limit is what puts it in the vector.**

## Build

The self-test establishes the setup and the silent failure: the chunk exceeds the limit, the query term is in the text but specifically in the dropped tail, and it is not retrievable from the long chunk.

```python filename=modules/context-and-retrieval/code/embtrunc-inter-01/embtrunc.py:78-88 COMPLETE
    chunk_exceeds_maxlen = len(chunk) > max_len
    print("  the chunk is longer than the model's max length = %s (%d > %d)" % (chunk_exceeds_maxlen, len(chunk), max_len))

    term_in_text = term in chunk
    print("  the query term is present in the chunk's text = %s" % term_in_text)

    term_in_dropped_tail = term in chunk[max_len:]
    print("  the query term is in the dropped tail (past max_len) = %s" % term_in_dropped_tail)

    long_chunk_misses = not retrievable(term, [chunk], max_len)
    print("  the term is NOT retrievable from the truncated long chunk = %s" % long_chunk_misses)
```

Then the fix: splitting into max_len-sized chunks makes the term retrievable again.

```python filename=modules/context-and-retrieval/code/embtrunc-inter-01/embtrunc.py:90-91 COMPLETE
    splitting_recovers = retrievable(term, splits, max_len)
    print("  splitting into max_len-sized chunks makes it retrievable = %s" % splitting_recovers)
```

Running the check confirms every clause.

```text filename=embtrunc.py --check
  the chunk is longer than the model's max length = True (9 > 5)
  the query term is present in the chunk's text = True
  the query term is in the dropped tail (past max_len) = True
  the term is NOT retrievable from the truncated long chunk = True
  splitting into max_len-sized chunks makes it retrievable = True
```

**The check pins the miss to a term that is in the chunk's text but past the truncation cutoff — present to a reader, absent from the vector — and shows splitting to fit restoring it.**

## Definition of done

Done means the query term is shown present in the chunk's text but in the truncated tail and therefore unretrievable, and splitting the chunk to fit the model's limit restores retrieval. The clause distinguishing "in the text" from "in the vector" is the crux: the bug is invisible to anyone inspecting the stored chunks, because the content is plainly there — it is missing only from the representation search actually uses.

Two clarifications make this operational. First, the limit is in tokens, and that is where the trap usually springs. Chunkers frequently measure size in characters or words, which undercount: a token is often a sub-word, so a chunk of 500 "words" can be 700 or more tokens and silently overflow a 512-token model, and code containing punctuation and rare identifiers tokenizes even more densely. Size chunks with the same tokenizer the embedding model uses, and leave headroom for any special tokens (like a prepended instruction or a CLS token) the model adds. Second, oversize input is not always a chunk you created — it can be a document you embed whole under the assumption the model handles it, or a query that is unusually long; both truncate the same way. Where long units are genuinely needed, the answer is a long-context embedding model whose token limit exceeds your inputs, or a strategy that embeds sub-parts and combines them, rather than feeding an over-length input and trusting the model to cope. The one thing never to do is assume that because no error was raised, the whole input was embedded.

<svg role="img" aria-label="Two rules: measure chunk length in the model's tokens not words or characters, and for genuinely long inputs use a long-context model or embed sub-parts" viewBox="0 0 320 110">
  <rect x="14" y="20" width="150" height="40" fill="none" stroke="var(--s1)"/>
  <text x="22" y="35" font-size="7.5" fill="var(--s1)">measure in tokens</text>
  <text x="22" y="47" font-size="7" fill="var(--ink)">not words/chars (they undercount)</text>
  <text x="22" y="56" font-size="7" fill="var(--ink)">+ headroom for special tokens</text>
  <rect x="176" y="20" width="130" height="40" fill="none" stroke="var(--s2)"/>
  <text x="184" y="35" font-size="7.5" fill="var(--s2)">genuinely long input?</text>
  <text x="184" y="47" font-size="7" fill="var(--ink)">long-context model, or</text>
  <text x="184" y="56" font-size="7" fill="var(--ink)">embed sub-parts + combine</text>
  <text x="14" y="80" font-size="7.5" fill="var(--muted)">no error raised is not proof the whole input was embedded</text>
  <text x="14" y="100" font-size="7.5" fill="var(--ink)">size to the model's token limit with its own tokenizer</text>
</svg>
^ Size chunks in the model's tokens (using its tokenizer, with headroom for special tokens), not words or characters that undercount; for genuinely long inputs use a long-context model or embed sub-parts. A silent, error-free embedding call is not evidence the whole input was represented.

**Done means the tail term is present in the text but truncated out of the vector and unretrievable until the chunk is split to fit — so chunks are sized to the model's token limit with its own tokenizer, and long inputs go to a long-context model rather than being fed over-length and truncated.**

## Boss fight

A RAG system indexes long documents by splitting them into 800-word chunks and embedding each with a sentence-transformer model. Retrieval works well for questions about the opening of a section but consistently fails for questions whose answer is in the later part of a section, returning unrelated chunks. The chunks clearly contain the answers when you read them. What is wrong, and how do you fix it?

The chunks are longer than the embedding model's maximum token length, so the model is silently truncating them and never embedding the later part of each chunk. An 800-word chunk is well over 1000 tokens for a typical tokenizer, and most sentence-transformer models cap at 512 tokens, so the model embeds only the first ~512 tokens of each chunk and discards the rest — which is exactly the later part of the section where the failing questions' answers live. The embedding call raises no error and returns a normal vector, and the stored chunk still contains the full 800 words, which is why the answers are visibly present when you read the chunks; they are simply absent from the vectors search uses, so a query about late-section content finds no signal and retrieves unrelated chunks. The pattern — opening questions work, later-content questions fail — is the signature of tail truncation. The fix is to size chunks to the model's token limit measured in the model's own tokens, not words: chunk to, say, 400–450 tokens (leaving headroom for any special tokens) using the embedding model's tokenizer, so every chunk is embedded in full. Re-chunk and re-index the corpus with the token-based sizing. If the documents genuinely need larger chunks for context, switch to a long-context embedding model whose token limit comfortably exceeds the chunk size, or embed sub-chunks and aggregate. As a guard against the class of bug, add a check that flags or rejects any chunk whose token count exceeds the model's limit at index time, so truncation can never happen silently again.

## External resources

The documentation for embedding models on maximum sequence length and truncation behavior (the `max_seq_length` and truncation settings in Sentence-Transformers, and the token limits published for hosted embedding APIs) — the exact limits, that overflow truncates rather than errors, and how to configure or check it.

Guidance on token-aware chunking for retrieval (measuring chunk size with the embedding model's tokenizer, accounting for special tokens, and choosing long-context embedding models for large chunks) — the practice of sizing chunks to the model's token limit so no content is silently dropped from the vector.
