---
id: embver-inter-01
title: Embed the query and the whole corpus with one model version — or a stale vector from another model scores as noise
topic: context-and-retrieval
level: intermediate
status: ready
time: 16 min
summary: A vector index works because similar meanings become nearby vectors, so a query and a relevant document have high cosine — but that guarantee holds only within a single embedding model. Different models, or two versions of the same model, map meaning into different vector spaces, so the same text gets a different vector under v1 than under v2, and a v1 vector and a v2 vector are not comparable: their cosine is not a similarity, it is noise. This is invisible until you upgrade the model. You embed new documents and queries with v2, but the old documents are still v1, so a v2 query is compared against a mix of meaningful v2 vectors and meaningless v1 ones — the relevant old document scores as if random while some irrelevant old document can land close by coordinate coincidence and rank first. The rule is that an index must be homogeneous in embedding version and the query embedded with that version, so upgrading is a re-indexing job, not a config flip. On a fixture where the query truly matches the relevant doc (semantic cosine 0.95) and not the irrelevant one (0.00), both docs are still v1 while the query is v2, so the indexed cosines are scrambled — relevant 0.31, irrelevant 1.00 — ranking the wrong doc first, until re-embedding both with v2 restores the true order.
eli5: Two people describe locations, but one gives directions from the north gate and the other from the east gate. Each is perfectly consistent with themselves, but you can't mix their directions — "200 steps left" means different places to each. Embedding models are like that: each has its own frame of reference, and a vector from one model can't be compared to a vector from another. If you upgrade your model but only re-file half your documents, the query speaks the new model's directions while the old documents still speak the old model's — and the distances you compute between them are gibberish, so the wrong documents come back.
---

## Why this module

A vector search compares numbers, and those numbers only mean "similar" relative to the model that produced them — so the instant two vectors in your index came from different models, comparing them is comparing coordinates in incompatible frames, and the similarity it reports is meaningless.

Semantic search rests on one property: an embedding model places texts with similar meaning near each other, so cosine similarity between a query's vector and a document's vector measures how related they are. That property is a fact about a *single* model's output space. A different model — or the next version of the same model after retraining — learns its own arrangement of meaning in vector space, oriented differently, so the same sentence embeds to a different vector, and the two vectors from the two models have no meaningful geometric relationship. Cosine between a v1 vector and a v2 vector is a real number, but it is not a similarity; it is the accidental alignment of two unrelated coordinate systems. Everything works as long as every vector in the index, and the query vector, came from the same model. The failure appears precisely when that stops being true.

**Vectors are only comparable within one embedding model, so a v1 document vector and a v2 query vector have a cosine that is noise, not similarity — and an index that mixes embedding versions returns confident, meaningless scores for the mismatched vectors.**

The trap is that this mismatch arrives through an ordinary, well-intentioned action: upgrading the embedding model. You switch the service to v2, so new queries and newly-added documents are embedded with v2 — but the millions of documents already in the index are still v1, and re-embedding them takes time and money, so the migration runs in the background or never finishes. In that window the index is heterogeneous: a v2 query is scored against v2 vectors (correctly) and v1 vectors (as noise), side by side, with no error to distinguish them. The relevant old document, embedded v1, scores as though it were random, so it is missed; an irrelevant old document can happen to sit near the query's v2 coordinates and rank first. A half-migrated index is worse than the un-upgraded one, because it fails silently and only for the documents that were not migrated. The rule is that the index must be homogeneous in embedding version and the query embedded with that same version — so upgrading the model is a full re-indexing job, and the index should be version-tagged so a mismatched query is rejected, not scored. This module scores a query against stale vectors and then re-indexed ones.

## Concepts

**An embedding model maps meaning into its own vector space.** We model a model version as a fixed rotation of the semantic space — rotations preserve cosine *within* a version (so each model works internally) but orient the two versions' spaces differently, so their vectors do not align.

```python filename=modules/context-and-retrieval/code/embver-inter-01/embver.py:43-47 COMPLETE
def embed(semantic, version, angles):
    """A model version embeds meaning by rotating the semantic space by its angle (a stand-in for its own vector space)."""
    a = math.radians(angles[version])
    x, y = semantic
    return [x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)]
```

**The indexed cosine** is what the index actually computes: the query embedded by its version against a document embedded by whatever version embedded it. When the versions match it is a real similarity; when they differ it is noise.

```python filename=modules/context-and-retrieval/code/embver-inter-01/embver.py:62-67 COMPLETE
def indexed_cosine(data, doc, doc_version):
    """The cosine the index actually computes: query embedded by its version, doc embedded by doc_version."""
    angles = data["model_angles_deg"]
    qv = embed(data["query_semantic"], data["query_version"], angles)
    dv = embed(doc["semantic"], doc_version, angles)
    return cosine(qv, dv)
```

**The true similarity is model-independent** — it is a property of the meanings, which retrieval is supposed to recover. A correct index reproduces it; a version-mismatched index does not.

<svg role="img" aria-label="The same meaning embeds to different vectors under v1 and v2; comparing a v2 query to a v1 document vector crosses two misaligned spaces" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the same meaning, two model spaces</text>
  <line x1="60" y1="86" x2="60" y2="24" stroke="var(--grid)"/><line x1="20" y1="70" x2="120" y2="70" stroke="var(--grid)"/>
  <line x1="60" y1="70" x2="105" y2="40" stroke="var(--s1)" stroke-width="1.5"/><text x="66" y="36" fill="var(--s1)" font-size="7">v1 vector</text>
  <text x="30" y="94" fill="var(--muted)" font-size="7">model v1 space</text>
  <line x1="230" y1="86" x2="230" y2="24" stroke="var(--grid)"/><line x1="190" y1="70" x2="290" y2="70" stroke="var(--grid)"/>
  <line x1="230" y1="70" x2="230" y2="30" stroke="var(--s2)" stroke-width="1.5"/><text x="236" y="34" fill="var(--s2)" font-size="7">v2 vector</text>
  <text x="200" y="94" fill="var(--muted)" font-size="7">model v2 space</text>
  <text x="128" y="52" fill="var(--muted)" font-size="7">same meaning →</text>
  <text x="128" y="64" fill="var(--muted)" font-size="7">different vectors</text>
  <text x="6" y="100" fill="var(--muted)" font-size="7">a cosine across the two spaces is not a similarity</text>
</svg>
^ The same meaning becomes a different vector in each model's space, so comparing a v2 query vector to a v1 document vector crosses two misaligned frames — the cosine it yields is coincidence, not similarity.

**Compare vectors only within one embedding version: keep the index homogeneous and embed the query with that same version, because a cross-version cosine measures coordinate coincidence, not meaning.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/embver-inter-01/embver.py

The fixture is a v2 query, a relevant and an irrelevant document both still embedded by the stale v1 model, and the two models as rotations.

```json filename=modules/context-and-retrieval/code/embver-inter-01/embver.json:3-10 COMPLETE
  "query_semantic": [1.0, 0.0],
  "query_version": "v2",
  "model_angles_deg": {"v1": 0, "v2": 90},
  "docs": [
    {"id": "relevant", "semantic": [0.95, 0.31], "version": "v1"},
    {"id": "irrelevant", "semantic": [0.0, 1.0], "version": "v1"}
  ],
  "gold": "relevant"
```

Run `--similar` to compare the true similarity with what the mixed index computes.

```text filename=--similar
SIMILAR — true semantic cosine vs the indexed cosine (query v2, docs still v1)
------------------------------------------------------------------------
  doc           true cosine   indexed cosine (mixed versions)
  relevant      0.95          0.31  <- gold
  irrelevant    0.00          1.00
------------------------------------------------------------------------
  indexed ranking: ['irrelevant', 'relevant']  (top = irrelevant, should be relevant)
```

The true-cosine column is the reality retrieval should recover: the relevant document is highly related to the query (0.95) and the irrelevant one is unrelated (0.00). The indexed-cosine column is what the index actually returns with the query at v2 and both documents still at v1, and it is inverted. The relevant document scores 0.31 — its v1 vector, viewed from the v2 query's frame, looks only weakly related, so it is nearly lost. The irrelevant document scores 1.00 — a perfect match — purely because its v1 coordinates happen to coincide with the query's v2 coordinates, a numerical accident with no semantic content. The index ranks the irrelevant document first and the relevant one second: the exact opposite of correct. Nothing errored; every cosine is a valid number; the retrieval is simply and confidently wrong, and it is wrong specifically for the documents that were embedded by the old model. A relevance metric run on this index would report a catastrophic drop, and a team that did not suspect the version mismatch would hunt for the bug everywhere except the one place it lives — in the index's mixed provenance.

<svg role="img" aria-label="True cosines are 0.95 for relevant and 0.00 for irrelevant, but the mixed index scores relevant 0.31 and irrelevant 1.00, inverting the ranking" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">true similarity vs mixed-index score</text>
  <text x="6" y="30" fill="var(--muted)" font-size="8">true</text>
  <rect x="70" y="22" width="171" height="10" fill="var(--s1)"/><text x="244" y="31" fill="var(--muted)" font-size="7">relevant .95</text>
  <rect x="70" y="34" width="2" height="10" fill="var(--s2)"/><text x="76" y="43" fill="var(--muted)" font-size="7">irrelevant .00</text>
  <line x1="6" y1="52" x2="292" y2="52" stroke="var(--grid)"/>
  <text x="6" y="70" fill="var(--muted)" font-size="8">mixed</text>
  <rect x="70" y="62" width="56" height="10" fill="var(--s1)"/><text x="130" y="71" fill="var(--muted)" font-size="7">relevant .31</text>
  <rect x="70" y="74" width="180" height="10" fill="var(--s2)"/><text x="150" y="83" fill="var(--panel)" font-size="7">irrelevant 1.00 ← ranks first ✗</text>
  <text x="6" y="100" fill="var(--muted)" font-size="8">the mixed index inverts the ranking: the irrelevant stale doc wins on a coordinate coincidence</text>
</svg>
^ The true similarities (relevant 0.95, irrelevant 0.00) are inverted by the mixed index (relevant 0.31, irrelevant 1.00), so the irrelevant stale document ranks first on a meaningless cross-version coincidence.

## Build

The fix is to make the index homogeneous. Run `--reindex`, which re-embeds every document with the query's version.

```text filename=--reindex
REINDEX — re-embed every doc with the query's version (v2), then re-rank
------------------------------------------------------------------
  doc           cosine before (mixed)   cosine after (all v2)
  relevant      0.31                    0.95
  irrelevant    1.00                    0.00
------------------------------------------------------------------
  ranking after re-indexing: ['relevant', 'irrelevant']  (top = relevant)
```

Once both documents are re-embedded with v2 — the same model that embedded the query — the indexed cosines snap back to the true similarities: relevant 0.95, irrelevant 0.00. The ranking is now correct, relevant first. Nothing about the documents' meaning changed; only their vectors were recomputed in the query's space, and that alone restored the similarity the mixed index had scrambled. This is why upgrading an embedding model is an operational project, not a setting: you must re-embed the entire corpus before serving v2 queries against it, which for a large index is a substantial batch job, and until it completes you either keep serving v1 queries against the v1 index or you accept broken retrieval for the un-migrated documents. The safe migration keeps the old v1 index serving v1 queries while a new v2 index is built in full, then cuts over atomically — never a query in one version against an index in another. And the index should record which embedding version produced its vectors, so a query embedded with a different version is refused with a clear error instead of silently scored against the wrong space. Version is not metadata to ignore; it is the precondition that makes every cosine in the index mean anything.

<svg role="img" aria-label="Before re-indexing the ranking is irrelevant then relevant; after re-indexing to v2 it is relevant then irrelevant" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">ranking (top to bottom)</text>
  <text x="20" y="30" fill="var(--muted)" font-size="8">mixed (query v2, docs v1)</text>
  <rect x="20" y="36" width="120" height="14" fill="var(--s2)"/><text x="26" y="47" fill="var(--panel)" font-size="7">1. irrelevant ✗</text>
  <rect x="20" y="52" width="120" height="14" fill="var(--s1)"/><text x="26" y="63" fill="var(--panel)" font-size="7">2. relevant</text>
  <text x="170" y="30" fill="var(--muted)" font-size="8">re-indexed (all v2)</text>
  <rect x="170" y="36" width="120" height="14" fill="var(--s1)"/><text x="176" y="47" fill="var(--panel)" font-size="7">1. relevant ✓</text>
  <rect x="170" y="52" width="120" height="14" fill="var(--s2)"/><text x="176" y="63" fill="var(--panel)" font-size="7">2. irrelevant</text>
  <text x="6" y="86" fill="var(--muted)" font-size="8">re-embedding the corpus in the query's version restores the correct order</text>
</svg>
^ The mixed index ranks the irrelevant document first; after re-embedding the corpus in the query's v2 version, the relevant document ranks first — the ranking the true similarities always implied.

## Definition of done

The self-test pins the mismatch and the fix: same-version cosine equals the true cosine, the mixed-version cosine for the gold doc is wrong, the mixed index ranks the wrong doc first, and re-indexing to the query's version restores it.

```python filename=modules/context-and-retrieval/code/embver-inter-01/embver.py:111-124 COMPLETE
    within_matches_true = abs(indexed_cosine(data, goldd, qv) - true_cosine(data["query_semantic"], goldd["semantic"])) < 1e-9
    print("  same-version cosine equals the true semantic cosine = %s (%.3f)" % (within_matches_true, indexed_cosine(data, goldd, qv)))

    mixed_wrong = abs(indexed_cosine(data, goldd, goldd["version"]) - true_cosine(data["query_semantic"], goldd["semantic"])) > 0.1
    print("  the mixed-version cosine for the gold doc is wrong = %s (%.3f vs true %.3f)"
          % (mixed_wrong, indexed_cosine(data, goldd, goldd["version"]), true_cosine(data["query_semantic"], goldd["semantic"])))

    mixed_rank = ranking(data, lambda d: d["version"])
    mixed_ranks_wrong = mixed_rank[0][0] != gold
    print("  the mixed index ranks the wrong doc first = %s (top = %s)" % (mixed_ranks_wrong, mixed_rank[0][0]))

    fixed_rank = ranking(data, lambda d: qv)
    reindex_fixes = fixed_rank[0][0] == gold
    print("  re-indexing to the query's version ranks the gold first = %s (top = %s)" % (reindex_fixes, fixed_rank[0][0]))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — within-version cosine equals the true cosine; mixed-version cosine does not; re-indexing fixes the ranking
------------------------------------------------------------------------------------------------------------------
  same-version cosine equals the true semantic cosine = True (0.951)
  the mixed-version cosine for the gold doc is wrong = True (0.310 vs true 0.951)
  the mixed index ranks the wrong doc first = True (top = irrelevant)
  re-indexing to the query's version ranks the gold first = True (top = relevant)
  a stale irrelevant doc outscores the stale gold doc = True
```

**Done means the version-mismatch failure and its fix are proven: a same-version cosine reproduces the true semantic cosine (0.951), while the mixed-version cosine for the gold doc collapses to 0.310, so the mixed index ranks the irrelevant stale document first — and re-embedding the corpus in the query's v2 version restores the relevant document to the top, the ranking the true similarities always implied.**

## Boss fight

Predict the two ways the version-homogeneity rule is subtler than "always re-index." It is tempting to think matching version strings is sufficient.

The first trap is that "same version" must mean the same model *and* the same preprocessing pipeline, because anything that changes the input to the model changes the output space. Two vectors are only comparable if they came from the identical model weights and the identical tokenization, truncation, normalization, and pooling — so a "minor" change that keeps the version string but alters, say, how text is chunked or lowercased, or whether embeddings are L2-normalized before indexing, silently produces incomparable vectors under the same label. The version tag has to cover the whole embedding function, not just the model name, or two documents tagged "v2" can still live in different spaces. This is the same trap as any reproducibility footgun: the thing that must match is the entire deterministic pipeline, and a label that omits part of it lies. Pin and record the full embedding configuration, and treat any change to it as a new version requiring a re-index.

```python filename=modules/context-and-retrieval/code/embver-inter-01/embver.py:57-59 COMPLETE
def true_cosine(query_sem, doc_sem):
    """The real semantic similarity, model-independent -- what retrieval is supposed to recover."""
    return cosine(query_sem, doc_sem)
```

The second trap is that re-indexing a large corpus is expensive and slow, so the tempting shortcut — a cheap linear "alignment" between the old and new spaces instead of a full re-embed — is only a partial fix. It is sometimes possible to learn a transformation that maps v1 vectors approximately into the v2 space (an orthogonal Procrustes alignment on shared anchor texts), which can salvage an index without re-embedding everything, and for a pure rotation like this fixture it would be exact. But real model upgrades are not rotations: a better model rearranges meaning non-linearly, splitting or merging clusters, so no linear map recovers the new model's geometry, and the alignment leaves residual error that degrades retrieval in ways that are hard to detect. So alignment is a stopgap for a compatible change or a bridge during migration, not a substitute for re-embedding when the model genuinely changed. And the cutover itself must be atomic per query — a single query embedded v2 and scored against a partially-migrated index is broken even if 99% of documents are migrated — which is why the disciplined pattern is build-new-index-then-swap, not migrate-in-place. Version compatibility is a property of the whole retrieval path, and the only fully safe fix for a real upgrade is to re-embed the corpus and cut over atomically.

**Vectors are comparable only within one embedding version, so keep the index homogeneous and embed the query with that version — a mixed index scores stale vectors as noise and can rank an irrelevant stale document first with no error — which makes a model upgrade a full re-embedding job, cut over atomically (build the new index, then swap, never query one version against an index in another); and "version" must tag the entire embedding pipeline (weights, tokenization, normalization, pooling), because a change to any of it produces incomparable vectors under the same label, while a cheap linear alignment only salvages a compatible change, not a genuinely better model that rearranges the space non-linearly.**

## External resources

Any vector-database or embedding-service documentation on re-indexing and model upgrades — the guidance to keep an index single-model, to version-tag embeddings, and to rebuild-and-swap rather than migrate in place.

Writing on embedding space alignment (orthogonal Procrustes, cross-lingual/‑model mapping) — when a linear map between embedding spaces is and is not valid, and why a non-linear model change cannot be aligned away.

The companion "pin the dependency version" and "seed the random generator" modules — all three are reproducibility rules where a program's output depends on a version or configuration that must be recorded and held fixed, and a silent change to it corrupts results that look valid.
