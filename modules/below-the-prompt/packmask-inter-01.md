---
id: packmask-inter-01
title: Mask packed training sequences block-diagonally by document — a bare causal mask lets one packed document attend into another
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: Short training sequences waste compute — pad a 200-token document out to a 2048-token block and the model runs attention over 1848 padding positions per 200 real ones. Packing fixes this by concatenating many short documents into one full-length sequence, so nearly every position carries a real token, and it is one of the highest-leverage efficiency tricks in training. But packing changes what a "sequence" is. The usual causal mask lets a position attend to itself and everything before it, which is right when the sequence is one document; after packing, the positions before a token may belong to a different document concatenated ahead of it. Under a bare causal mask the first token of the second document can attend to every token of the first — two unrelated texts bleeding into each other — and the model learns to predict the second document's tokens using the first document's content. That dependency is pure contamination: at inference each document arrives on its own with nothing packed before it, so the model has learned to lean on a signal that will not be there, and it has been taught spurious cross-document correlations from whatever happened to be packed together. The fix is a block-diagonal attention mask: keep the causal constraint and add one more — a position may attend to another only if they share the same document (segment) — so attention splits into independent blocks along the diagonal and each document attends only within itself, at full token efficiency. On a fixture packing two 3-token documents, a bare causal mask gives the second document 9 attention edges reaching into the first while the block-diagonal mask gives 0, both preserving all 12 within-document edges.
eli5: Imagine cramming two separate short stories onto one page to save paper. Normally when the model reads, it's allowed to look back at everything earlier on the page to guess the next word. That's fine within one story — but now the second story is on the same page, so when it starts reading story two, it can peek back at all of story one, which has nothing to do with it. It ends up "learning" that story one helps predict story two, which is nonsense and won't be true later when story two shows up by itself. The fix is a rule: you may only look back at words from the SAME story, never across the line where one story ends and the next begins. Then packing two stories on one page is just as good as reading them separately, but you save the paper.
---

## Why this module

Packing is an efficiency trick with an easy-to-miss correctness condition. The efficiency is real: training on padded short sequences burns most of the attention compute on padding, and concatenating documents until the block is full recovers almost all of it. Nearly every serious pretraining and fine-tuning pipeline packs. The correctness condition is that the model must still treat the packed documents as separate — and a plain causal attention mask does not.

The causal mask encodes one rule: a token may attend to itself and to every token before it. That rule assumes "before" means "earlier in the same document." Packing breaks the assumption, because the tokens before a given position now include whatever unrelated document was concatenated ahead of it. Nothing errors — the shapes are fine, the loss is a number — but the attention pattern quietly lets each document read the ones packed before it, and the model dutifully learns from that. It learns cross-document dependencies that exist only because of an arbitrary packing order, and it comes to rely on context that will be absent at inference, where documents are served one at a time.

This module packs two tiny documents into one sequence and compares the causal mask with the block-diagonal mask, counting exactly how much attention crosses the boundary.

**Packing concatenates unrelated documents into one sequence, so a bare causal mask lets a later document attend into an earlier one — teaching cross-document dependencies absent at inference; a block-diagonal mask requiring same-document attention confines each document to itself.**

## Concepts

The fixture packs two documents into one six-token sequence. The segment id records which document each token belongs to — tokens 0–2 are document 0, tokens 3–5 are document 1.

```json filename=modules/below-the-prompt/code/packmask-inter-01/packmask.json:3-4 COMPLETE
  "tokens": [11, 12, 13, 21, 22, 23],
  "segment": [0, 0, 0, 1, 1, 1]
```

The two masks differ by one clause. The causal mask allows attention from position i to j whenever j is at or before i. The block-diagonal mask adds the requirement that i and j share a segment — same document — so attention cannot cross a document boundary.

```python filename=modules/below-the-prompt/code/packmask-inter-01/packmask.py:32-39 COMPLETE
def causal_mask(i, j):
    """A position may attend to itself and earlier positions."""
    return j <= i


def blockdiag_mask(i, j, segment):
    """Causal AND same document: a position attends only within its own segment."""
    return j <= i and segment[i] == segment[j]
```

An attention edge is an allowed (i, j) pair; a cross-document edge is one where the two tokens are in different segments. Every cross-document edge is a place the model can read across the boundary.

```python filename=modules/below-the-prompt/code/packmask-inter-01/packmask.py:42-47 COMPLETE
def edges(n, allowed):
    return [(i, j) for i in range(n) for j in range(n) if allowed(i, j)]


def cross_doc(edge_list, segment):
    return [(i, j) for i, j in edge_list if segment[i] != segment[j]]
```

The single extra clause — same segment — is the whole fix, and its effect is to zero out every cross-document edge while leaving the within-document edges untouched.

<svg role="img" aria-label="Two 6x6 attention masks: the causal mask is a full lower triangle spanning both documents, the block-diagonal mask is two separate 3x3 lower triangles, one per document" viewBox="0 0 320 150">
  <text x="10" y="12" font-size="8" fill="var(--muted)">attention allowed (rows attend to columns); doc A = 0–2, doc B = 3–5</text>
  <text x="30" y="30" font-size="7.5" fill="var(--s2)">causal</text>
  <g>
  <rect x="20" y="34" width="72" height="72" fill="none" stroke="var(--line)"/>
  <rect x="20" y="34" width="12" height="12" fill="var(--s1)"/>
  <rect x="20" y="46" width="24" height="12" fill="var(--s1)"/>
  <rect x="20" y="58" width="36" height="12" fill="var(--s1)"/>
  <rect x="20" y="70" width="48" height="12" fill="var(--s2)"/>
  <rect x="20" y="82" width="60" height="12" fill="var(--s2)"/>
  <rect x="20" y="94" width="72" height="12" fill="var(--s2)"/>
  <line x1="56" y1="34" x2="56" y2="106" stroke="var(--ink)" stroke-dasharray="2 2"/>
  <line x1="20" y1="70" x2="92" y2="70" stroke="var(--ink)" stroke-dasharray="2 2"/>
  </g>
  <text x="200" y="30" font-size="7.5" fill="var(--s1)">block-diagonal</text>
  <g>
  <rect x="190" y="34" width="72" height="72" fill="none" stroke="var(--line)"/>
  <rect x="190" y="34" width="12" height="12" fill="var(--s1)"/>
  <rect x="190" y="46" width="24" height="12" fill="var(--s1)"/>
  <rect x="190" y="58" width="36" height="12" fill="var(--s1)"/>
  <rect x="226" y="70" width="12" height="12" fill="var(--s1)"/>
  <rect x="226" y="82" width="24" height="12" fill="var(--s1)"/>
  <rect x="226" y="94" width="36" height="12" fill="var(--s1)"/>
  <line x1="226" y1="34" x2="226" y2="106" stroke="var(--ink)" stroke-dasharray="2 2"/>
  <line x1="190" y1="70" x2="262" y2="70" stroke="var(--ink)" stroke-dasharray="2 2"/>
  </g>
  <text x="20" y="124" font-size="7.5" fill="var(--s2)">the shaded lower-left block is doc B reading doc A — contamination</text>
  <text x="20" y="138" font-size="7.5" fill="var(--s1)">block-diagonal keeps only the two per-document triangles</text>
</svg>
^ The causal mask is one lower triangle spanning both documents; its lower-left block (doc B attending to doc A) is the contamination. The block-diagonal mask keeps only the two per-document triangles, so each document attends within itself and the cross block is gone.

**The causal and block-diagonal masks agree inside each document and differ only in the cross block — the extra same-segment clause deletes exactly the edges that reach across the boundary.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the attention-masking step of a packed training pipeline, reduced to two 3-token documents so every edge is countable by hand.

Run `--masks` to print both masks row by row.

```text filename=packmask.py --masks
  causal (segments [0, 0, 0, 1, 1, 1]):
    pos 0 [doc 0]  A.....
    pos 1 [doc 0]  AA....
    pos 2 [doc 0]  AAA...
    pos 3 [doc 1]  AAAA..
    pos 4 [doc 1]  AAAAA.
    pos 5 [doc 1]  AAAAAA
  block-diagonal (segments [0, 0, 0, 1, 1, 1]):
    pos 3 [doc 1]  ...A..
    pos 4 [doc 1]  ...AA.
    pos 5 [doc 1]  ...AAA
```

Read position 3 — the first token of document 1. Under the causal mask its row is `AAAA..`: it attends to positions 0, 1, 2 (all of document 0) and itself. Under the block-diagonal mask its row is `...A..`: it attends only to itself, because positions 0–2 are a different document. The first three rows (document 0) are identical between the two masks; only document 1's rows change, losing exactly the columns that belong to document 0.

Now `--leak` builds both edge sets and counts how many cross the boundary.

```python filename=modules/below-the-prompt/code/packmask-inter-01/packmask.py:70-71 COMPLETE
    c_edges = edges(n, lambda i, j: causal_mask(i, j))
    b_edges = edges(n, lambda i, j: blockdiag_mask(i, j, seg))
```

The counts make the leak concrete.

```text filename=packmask.py --leak
  causal:         21 edges, 9 cross-document
  block-diagonal: 12 edges, 0 cross-document
  cross-document edges under causal: [(3, 0), (3, 1), (3, 2), (4, 0), (4, 1), (4, 2), (5, 0), (5, 1), (5, 2)]
```

The causal mask allows 21 edges, 9 of which cross the boundary — every token of document 1 (positions 3, 4, 5) attending to every token of document 0 (positions 0, 1, 2). Those 9 edges are the contamination: document 1 learning from document 0, which will never be present at inference. The block-diagonal mask allows 12 edges, 0 crossing — the 9 cross-document edges are gone, and the 12 within-document edges (6 per document) are exactly the ones both masks keep. The efficiency of packing is preserved; the leakage is removed.

<svg role="img" aria-label="Edge counts: causal mask has 21 total edges with 9 crossing the document boundary, block-diagonal has 12 total with 0 crossing, both keeping the 12 within-document edges" viewBox="0 0 320 120">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">attention edges (within-document vs cross-document)</text>
  <text x="10" y="40" font-size="8.5" fill="var(--s2)">causal</text>
  <rect x="70" y="30" width="120" height="16" fill="var(--s1)"/><text x="115" y="42" font-size="8" fill="var(--panel)">12 within</text>
  <rect x="190" y="30" width="90" height="16" fill="var(--s2)"/><text x="212" y="42" font-size="8" fill="var(--panel)">9 cross</text>
  <text x="10" y="70" font-size="8.5" fill="var(--s1)">block-diag</text>
  <rect x="70" y="60" width="120" height="16" fill="var(--s1)"/><text x="115" y="72" font-size="8" fill="var(--panel)">12 within</text>
  <text x="196" y="72" font-size="8" fill="var(--ink)">0 cross</text>
  <text x="10" y="98" font-size="7.5" fill="var(--muted)">block-diagonal deletes the 9 cross-document edges, keeps all 12 within-document</text>
</svg>
^ Both masks keep the same 12 within-document edges; the causal mask adds 9 cross-document edges and the block-diagonal mask adds none. The block-diagonal mask is the causal mask minus exactly the contaminating cross block.

**The causal mask leaks 9 cross-document attention edges — doc B reading all of doc A — while the block-diagonal mask leaks 0 and keeps every one of the 12 within-document edges.**

## Build

The self-test asserts the setup and both sides: more than one document is packed, the causal mask allows cross-boundary attention, the block-diagonal mask allows none, and both preserve the within-document edges.

```python filename=modules/below-the-prompt/code/packmask-inter-01/packmask.py:93-103 COMPLETE
    multiple_docs_packed = len(set(seg)) > 1
    print("  more than one document is packed into the sequence = %s (%d docs)" % (multiple_docs_packed, len(set(seg))))

    causal_leaks_across = len(c_cross) > 0
    print("  the causal mask allows attention across the document boundary = %s (%d edges)" % (causal_leaks_across, len(c_cross)))

    blockdiag_no_cross = len(b_cross) == 0
    print("  the block-diagonal mask allows NO cross-document attention = %s (%d edges)" % (blockdiag_no_cross, len(b_cross)))

    intra_preserved = c_intra == b_intra and len(b_intra) > 0
    print("  both masks preserve every within-document edge = %s (%d edges)" % (intra_preserved, len(b_intra)))
```

Running the check confirms every clause, including that doc B's first token sees doc A under causal masking but is isolated under block-diagonal masking.

```text filename=packmask.py --check
  more than one document is packed into the sequence = True (2 docs)
  the causal mask allows attention across the document boundary = True (9 edges)
  the block-diagonal mask allows NO cross-document attention = True (0 edges)
  both masks preserve every within-document edge = True (12 edges)
  doc B's first token sees doc A under causal but not block-diagonal = True (pos 3)
```

**The check pins the contamination to the cross block the causal mask allows, shows the block-diagonal mask removing it entirely, and confirms every within-document edge survives — the fix targets exactly the leak and nothing else.**

## Definition of done

Done means the causal mask is shown to leak attention across the document boundary and the block-diagonal mask to remove it while preserving every within-document edge. The "intra preserved" clause is what proves the fix is surgical: it changes only the cross-document edges, so a packed sequence with the block-diagonal mask trains identically to running each document separately — same efficiency, no contamination.

Two related mechanics complete the picture. First, positions: the same boundary problem afflicts positional encodings. If positions run 0..N across the whole packed sequence, document 1 starts at a large position offset it would never have on its own, so position ids should reset at each document boundary (each document numbered from 0), just as attention is confined to each document. With relative position schemes like RoPE the block-diagonal mask already prevents cross-document positional interactions, but absolute position ids need the explicit reset. Second, the loss: the last token of one document should not be trained to predict the first token of the next — that next-token target crosses the boundary too — so the label at each document's final position is masked out of the loss (or the documents are separated by a boundary token whose prediction is not supervised). Attention masking, position reset, and loss masking at the boundaries are the three parts of doing packing correctly; this module isolates the attention part, which is the one most often forgotten because a bare causal mask looks like it is already doing the right thing.

<svg role="img" aria-label="Three parts of correct packing at a document boundary: block-diagonal attention mask, position ids reset per document, and loss masked at the boundary token" viewBox="0 0 320 120">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">doing packing correctly at each document boundary</text>
  <text x="16" y="40" font-size="8" fill="var(--s1)">1. attention</text>
  <text x="90" y="40" font-size="7.5" fill="var(--ink)">block-diagonal (same-document only)</text>
  <text x="16" y="64" font-size="8" fill="var(--s1)">2. positions</text>
  <text x="90" y="64" font-size="7.5" fill="var(--ink)">reset to 0 at each document start</text>
  <text x="16" y="88" font-size="8" fill="var(--s1)">3. loss</text>
  <text x="90" y="88" font-size="7.5" fill="var(--ink)">mask the boundary target (no cross-doc next-token)</text>
  <text x="16" y="110" font-size="7.5" fill="var(--muted)">this module isolates part 1 — the one a bare causal mask hides</text>
</svg>
^ Correct packing has three parts at each boundary: block-diagonal attention, per-document position reset, and loss masking of the cross-boundary target. This module isolates the attention part, the one a plausible-looking causal mask silently gets wrong.

**Done means block-diagonal masking removes every cross-document edge and preserves every within-document one, so packed training matches separate training — alongside position reset and boundary loss masking as the other two parts of correct packing.**

## Boss fight

A team enables sequence packing to speed up fine-tuning and sees throughput improve, but validation loss gets slightly worse and the model occasionally produces text that seems to blend two unrelated topics. They packed documents end to end and kept their existing causal attention mask. What is the likely cause, and what is the complete fix?

The likely cause is cross-document attention: they packed unrelated documents into shared sequences but left a bare causal mask, so every token can attend to all earlier tokens in the packed sequence, including tokens from the previous document. During training the model learns dependencies between documents that were concatenated only by chance, which both wastes capacity on spurious correlations (hurting validation loss) and teaches the model that context from an unrelated preceding document is relevant — surfacing at generation as blended topics. The complete fix has three parts, all keyed to the document boundaries. First and most important, replace the bare causal mask with a block-diagonal (document-aware) mask: a token may attend to a previous token only if they belong to the same document, so attention splits into independent per-document blocks and no token reads across a boundary; modern attention kernels support this via a segment/document id or a list of sequence lengths (FlashAttention's variable-length/`cu_seqlens` interface is exactly this). Second, reset position ids at each document boundary so each document is numbered from 0 rather than continuing the running offset — required for absolute positions, and handled by the mask for relative schemes like RoPE. Third, mask the loss at each boundary so the last token of one document is not trained to predict the first token of the next. With those three, packing keeps its throughput win and trains identically to processing each document alone; without the attention mask in particular, packing is silently teaching the model to attend across documents.

## External resources

Documentation for packed/variable-length attention in training frameworks (FlashAttention's `cu_seqlens`/varlen interface, and the "attention mask for packed sequences" support in libraries like Hugging Face Transformers and the block-diagonal masks in xFormers) — the production mechanics of confining attention to each document while packing at full efficiency.

Writeups on sequence packing for LLM pretraining and fine-tuning (the efficiency motivation, and the correctness triad of intra-document attention masking, position id reset, and boundary loss masking) — why naive packing with a bare causal mask degrades quality and how the document-aware mask fixes it.
