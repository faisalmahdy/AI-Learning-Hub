---
id: gqa-inter-01
title: Share key/value heads across query heads — grouped-query attention shrinks the KV cache 4×
topic: below-the-prompt
level: intermediate
status: ready
time: 21 min
summary: The KV cache grows with the number of key/value heads, and at long context it dominates memory. Multi-head attention gives every query head its own KV head; grouped-query attention splits the query heads into a few groups that share KV heads. On a 32-head model at 4096 tokens, MHA needs a 2147 MB cache, GQA (8 groups) needs 537 MB — 4× less — and MQA needs 67 MB, all with the same query heads.
eli5: Imagine 32 note-takers who each keep their own copy of the same lecture notes — that's a lot of paper. If instead they work in 8 groups sharing one copy each, you keep 8 copies, not 32, and everyone still takes their own notes. Sharing the reference copies saves most of the paper without changing who's listening.
---

## Why this module

At long context lengths, the thing that runs you out of memory is not the model — it is the KV cache, and grouped-query attention is how modern models make it fit.

During generation, a transformer avoids recomputing the past by caching, for every layer and every token seen so far, the key and value vectors that attention will reattend to. That cache is essential for speed, but it grows with sequence length, batch size, number of layers, and number of key/value heads — and at the context lengths people now want, it balloons. For a large model at a long context, the KV cache can exceed the size of the model weights themselves, and it is what caps how long a context or how large a batch you can serve on a given GPU. The cache, not the parameters, is the binding constraint.

The default architecture, multi-head attention, makes the cache as large as it can be. It gives every query head its own key/value head, so if the model has 32 attention heads, it caches 32 keys and 32 values per token per layer. But look at what the heads do: the query heads are the ones doing the attending — asking "what should I look at?" — while the key/value heads only supply what is looked at. It turns out many query heads can share the same keys and values with very little loss in quality, because the diversity that matters most lives in the queries, not the keys and values.

Grouped-query attention exploits exactly that. Keep all the query heads — the model's attention capacity is unchanged — but split them into a few groups, and let each group share a single key/value head. Now the cache scales with the number of groups, not the number of query heads. Multi-query attention takes it to the extreme with one shared KV head (smallest cache, but some measurable quality loss); GQA sits in between, capturing most of the memory saving while staying close to full multi-head quality, which is why it is the standard in current large models.

We will size the cache for one model three ways. Multi-head: 2147 MB. Grouped-query with 8 groups: 537 MB, a 4× reduction. Multi-query: 67 MB, 32× less. The query heads are identical in all three; only the number of cached key/value heads changes.

**The KV cache scales with the number of key/value heads, so sharing them across query-head groups shrinks the cache by the group factor — GQA keeps every query head and a quarter of the cache.**

## Concepts

Start with the cache-size formula, because everything follows from it. The KV cache holds, for keys and for values (that is the factor of 2), across every layer, for every key/value head, a head-dimension-sized vector for every token in the context, at some bytes per element. So its size is 2 × layers × kv_heads × head_dim × sequence_length × bytes. Every term but one is fixed by the model and the workload; the one you can trade is kv_heads. Multi-head attention sets kv_heads equal to the number of query heads — the maximum. That is the lever GQA pulls.

The key realization is that query heads and key/value heads are separable. In standard attention, each head has its own query, key, and value projections, and they come in matched sets. But nothing forces the count of key/value heads to equal the count of query heads. You can have 32 query heads and only 8 key/value heads, with each key/value head shared by a group of 4 query heads. The query heads still each compute their own attention pattern — they each ask their own question — they just look up into a shared set of keys and values. The attention computation is unchanged in shape; only the number of distinct K and V projections shrinks, and with it the cache.

<svg role="img" aria-label="A spectrum from MHA to MQA: cache shrinks left to right while quality stays flat until dropping near MQA, with GQA marked as the sweet spot" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">the KV-head spectrum: cache vs quality</text>
  <line x1="50" y1="140" x2="440" y2="140" stroke="var(--line)"/>
  <text x="40" y="156" font-family="var(--mono)" font-size="8" fill="var(--muted)">MHA (32 KV)</text><text x="210" y="156" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">GQA (8)</text><text x="390" y="156" font-family="var(--mono)" font-size="8" fill="var(--muted)">MQA (1 KV)</text>
  <polyline points="60,40 210,100 340,120 420,128" fill="none" stroke="var(--s1)" stroke-width="2"/><text x="70" y="52" font-family="var(--mono)" font-size="9" fill="var(--ink)">cache (falls fast)</text>
  <polyline points="60,55 210,58 340,66 420,100" fill="none" stroke="var(--acc-ink)" stroke-width="2"/><text x="250" y="52" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">quality (flat, then drops)</text>
  <line x1="210" y1="40" x2="210" y2="140" stroke="var(--acc-ink)" stroke-dasharray="3 2"/><text x="180" y="34" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">sweet spot</text>
</svg>
^ Moving right shrinks the cache steeply while quality stays nearly flat — until it falls off near MQA, so GQA sits where almost all the memory is saved and almost all the quality kept.

This gives a clean spectrum. At one end, multi-head attention: kv_heads = query_heads, maximum cache, maximum head diversity. At the other, multi-query attention: kv_heads = 1, minimum cache, all query heads share one set of keys and values. In between, grouped-query attention: kv_heads = groups, somewhere between 1 and the full head count. The cache size and the quality both interpolate along this spectrum, and the empirical finding — the reason GQA exists — is that quality degrades slowly as you reduce kv_heads until you get near 1, so a moderate number of groups keeps almost all the quality while paying almost none of the memory. Eight groups on a 32-head model is a typical, well-tested choice.

What GQA does not change is worth stating, because it is where the free lunch comes from. The number of query heads, the model's hidden dimension, the number of layers, the parameter count of the attention — all essentially unchanged (GQA slightly reduces the K/V projection parameters, a minor effect). The expressive attention capacity is preserved. The only thing that shrinks is the number of distinct keys and values that must be stored and reattended, which is precisely the thing that was eating your memory at long context. You are not trading model quality for memory in any large way; you are removing a redundancy in what gets cached.

**Query heads and key/value heads need not be equal in number; GQA keeps the query heads and shares the key/value heads in groups, shrinking the one cache term you control while leaving attention capacity intact.**

## Worked example

The fixture is a model's dimensions and the GQA group count.

```json filename=modules/below-the-prompt/code/gqa-inter-01/config.json:7-12 COMPLETE
  "num_layers": 32,
  "num_query_heads": 32,
  "head_dim": 128,
  "seq_len": 4096,
  "bytes_per_elem": 2,
  "gqa_groups": 8
```

A 32-layer, 32-query-head model, head dimension 128, a 4096-token context, fp16 (2 bytes), and GQA with 8 groups. The cache size is the formula.

```python filename=modules/below-the-prompt/code/gqa-inter-01/gqa.py:39-41 COMPLETE
def kv_cache_bytes(cfg, kv_heads):
    """Bytes to cache K and V for every layer, KV head, and token: 2 * layers * kv_heads * head_dim * seq * bytes."""
    return 2 * cfg["num_layers"] * kv_heads * cfg["head_dim"] * cfg["seq_len"] * cfg["bytes_per_elem"]
```

The only thing that varies between the three variants is how many KV heads they keep.

```python filename=modules/below-the-prompt/code/gqa-inter-01/gqa.py:44-52 COMPLETE
def kv_heads_for(cfg, variant):
    """How many KV heads each variant keeps: MHA one per query head, MQA one total, GQA one per group."""
    if variant == "MHA":
        return cfg["num_query_heads"]
    if variant == "MQA":
        return 1
    if variant == "GQA":
        return cfg["gqa_groups"]
    raise ValueError(variant)
```

```python filename=modules/below-the-prompt/code/gqa-inter-01/gqa.py:55-56 COMPLETE
def mb(nbytes):
    return round(nbytes / 1e6, 1)
```

Confirm the KV-head counts first, and note the query heads are the same across all three.

```text filename=modules/below-the-prompt/code/gqa-inter-01/gqa.py --config
CONFIG — model dimensions and each variant's KV-head count
--------------------------------------------------------
  layers=32  query_heads=32  head_dim=128  seq_len=4096  fp16
  MHA  keeps 32 KV head(s)
  GQA  keeps  8 KV head(s)
  MQA  keeps  1 KV head(s)
--------------------------------------------------------
  all three keep 32 query heads; only the KV heads differ.
```

MHA keeps 32 KV heads, GQA 8, MQA 1 — but all three keep 32 query heads. Predict the cache: it scales linearly with KV heads, so GQA should be 32/8 = 4× smaller than MHA, and MQA 32× smaller. Run it.

```text filename=modules/below-the-prompt/code/gqa-inter-01/gqa.py --cache
CACHE — KV cache size per attention variant (context 4096 tokens)
----------------------------------------------------------
  MHA     2147.5 MB      1x smaller than MHA
  GQA      536.9 MB      4x smaller than MHA
  MQA       67.1 MB     32x smaller than MHA
----------------------------------------------------------
  GQA keeps near-MHA quality at a quarter of the cache; MQA is smallest but lossier.
```

Multi-head attention needs 2147 MB — over two gigabytes of KV cache for a single 4096-token sequence, and that scales with batch size, so a batch of eight would need 17 GB just for the cache. Grouped-query with 8 groups needs 537 MB, exactly a quarter, because it caches 8 KV heads instead of 32. Multi-query needs 67 MB, a thirty-second. That 4× from GQA is the difference between fitting a long-context batch on a GPU and not, and it costs essentially nothing in quality — the 32 query heads still attend exactly as they did, just into 8 shared sets of keys and values instead of 32 private ones.

<svg role="img" aria-label="Three attention variants: MHA maps 8 query heads to 8 KV heads one-to-one, GQA maps 8 query heads to 2 shared KV heads in groups, MQA maps all 8 to 1 shared KV head" viewBox="0 0 460 200" width="460" height="200">
  <rect x="0" y="0" width="460" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="9" fill="var(--muted)">query heads (top) → KV heads (bottom)</text>
  <g font-family="var(--mono)" font-size="8">
    <text x="30" y="34" fill="var(--muted)">MHA</text>
    <g fill="var(--acc-soft)" stroke="var(--acc-line)"><rect x="70" y="28" width="12" height="12"/><rect x="88" y="28" width="12" height="12"/><rect x="106" y="28" width="12" height="12"/><rect x="124" y="28" width="12" height="12"/></g>
    <g fill="var(--s1)" stroke="var(--line)"><rect x="70" y="52" width="12" height="12"/><rect x="88" y="52" width="12" height="12"/><rect x="106" y="52" width="12" height="12"/><rect x="124" y="52" width="12" height="12"/></g>
    <g stroke="var(--ink)"><line x1="76" y1="40" x2="76" y2="52"/><line x1="94" y1="40" x2="94" y2="52"/><line x1="112" y1="40" x2="112" y2="52"/><line x1="130" y1="40" x2="130" y2="52"/></g>
    <text x="150" y="48" fill="var(--muted)">4 KV heads — biggest cache</text>
    <text x="30" y="102" fill="var(--muted)">GQA</text>
    <g fill="var(--acc-soft)" stroke="var(--acc-line)"><rect x="70" y="96" width="12" height="12"/><rect x="88" y="96" width="12" height="12"/><rect x="106" y="96" width="12" height="12"/><rect x="124" y="96" width="12" height="12"/></g>
    <g fill="var(--s1)" stroke="var(--line)"><rect x="79" y="120" width="12" height="12"/><rect x="115" y="120" width="12" height="12"/></g>
    <g stroke="var(--ink)"><line x1="76" y1="108" x2="85" y2="120"/><line x1="94" y1="108" x2="85" y2="120"/><line x1="112" y1="108" x2="121" y2="120"/><line x1="130" y1="108" x2="121" y2="120"/></g>
    <text x="150" y="116" fill="var(--acc-ink)">2 KV heads (groups) — 1/2 cache</text>
    <text x="30" y="170" fill="var(--muted)">MQA</text>
    <g fill="var(--acc-soft)" stroke="var(--acc-line)"><rect x="70" y="164" width="12" height="12"/><rect x="88" y="164" width="12" height="12"/><rect x="106" y="164" width="12" height="12"/><rect x="124" y="164" width="12" height="12"/></g>
    <g fill="var(--s2)" stroke="var(--line)"><rect x="97" y="188" width="12" height="10"/></g>
    <g stroke="var(--ink)"><line x1="76" y1="176" x2="103" y2="188"/><line x1="94" y1="176" x2="103" y2="188"/><line x1="112" y1="176" x2="103" y2="188"/><line x1="130" y1="176" x2="103" y2="188"/></g>
    <text x="150" y="180" fill="var(--s2)">1 KV head — smallest cache</text>
  </g>
</svg>
^ All three keep the same four query heads; they differ only in how many key/value heads those queries share — four, two, or one — and the cache shrinks with that count.

<svg role="img" aria-label="KV cache sizes: MHA 2147 MB, GQA 537 MB, MQA 67 MB" viewBox="0 0 460 160" width="460" height="160">
  <rect x="0" y="0" width="460" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">KV cache size (MB) at 4096 tokens</text>
  <line x1="60" y1="130" x2="440" y2="130" stroke="var(--line)"/>
  <rect x="90" y="35" width="70" height="95" fill="var(--s1)" stroke="var(--line)"/><text x="96" y="29" font-family="var(--mono)" font-size="10" fill="var(--ink)">2147</text><text x="98" y="146" font-family="var(--mono)" font-size="9" fill="var(--muted)">MHA</text>
  <rect x="210" y="106" width="70" height="24" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="222" y="100" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">537</text><text x="212" y="146" font-family="var(--mono)" font-size="9" fill="var(--muted)">GQA (4×)</text>
  <rect x="330" y="127" width="70" height="3" fill="var(--s2)" stroke="var(--line)"/><text x="342" y="121" font-family="var(--mono)" font-size="10" fill="var(--s2)">67</text><text x="332" y="146" font-family="var(--mono)" font-size="9" fill="var(--muted)">MQA (32×)</text>
</svg>
^ The cache falls linearly with KV-head count — GQA at a quarter, MQA at a thirty-second — while every variant runs the same 32 query heads.

## Build

Reproduce the cache sizes. Pure arithmetic, so 2147.5, 536.9, and 67.1 MB come out exactly.

Run `--config` for the KV-head counts, `--cache` for the sizes, `--check` for the gate. The self-test pins the mechanism: GQA is smaller, the saving equals query_heads/groups exactly, the three order correctly, and every variant keeps all the query heads.

```python filename=modules/below-the-prompt/code/gqa-inter-01/gqa.py:91-96 COMPLETE
    gqa_smaller = gqa < mha
    print("  GQA's cache is smaller than MHA's = %s (%.1f vs %.1f MB)" % (gqa_smaller, mb(gqa), mb(mha)))

    ratio_is_groups = abs(mha / gqa - q / data["gqa_groups"]) < 1e-9
    print("  the saving equals query_heads/groups = %s (%.0fx = %d/%d)"
          % (ratio_is_groups, mha / gqa, q, data["gqa_groups"]))
```

The `ratio_is_groups` check is an exact equality — the MHA/GQA cache ratio equals query_heads divided by groups, to floating-point precision. That is what proves the saving is a clean linear function of the group count and not an approximation: halve the groups and you exactly halve the cache. It also makes the design dial legible — you pick the groups, you get exactly query_heads/groups reduction, and you can read the memory budget straight off the ratio. Here is the full gate.

```text filename=modules/below-the-prompt/code/gqa-inter-01/gqa.py --check
SELF-TEST — GQA shrinks the cache by exactly query_heads/groups while keeping every query head
--------------------------------------------------------------------------------------------
  GQA's cache is smaller than MHA's = True (536.9 vs 2147.5 MB)
  the saving equals query_heads/groups = True (4x = 32/8)
  MQA < GQA < MHA in cache size = True (67.1 < 536.9 < 2147.5 MB)
  every variant keeps all 32 query heads (only KV heads shrink) = True
--------------------------------------------------------------------------------------------
SELF-TEST PASS  gqa_smaller=True  ratio_is_groups=True  mqa_smallest=True  query_heads_unchanged=True
```

Four True flags. Gqa_smaller: GQA beats MHA on cache. Ratio_is_groups: by exactly the group factor. Mqa_smallest: the spectrum orders as expected. Query_heads_unchanged: the attention capacity is preserved across all three. The last flag is the one that makes this a near-free win — you shrink the cache without removing a single query head.

**The exact query_heads/groups ratio makes GQA a legible dial: pick the groups, get precisely that reduction, and read the memory budget off the ratio.**

## Definition of done

You are done when you reproduce the cache sizes and can explain the spectrum.

Concretely: `--cache` shows MHA at 2147 MB, GQA at 537 MB, MQA at 67 MB; `--check` prints PASS with four True flags. You can write the KV-cache size formula and identify kv_heads as the term GQA trades. You can explain why query heads and KV heads need not be equal, and place MHA, GQA, and MQA on the spectrum from most heads/most cache to one head/least cache. And you can state the empirical reason GQA is the standard: quality degrades slowly as kv_heads drops until near 1, so a moderate group count keeps almost all the quality at a fraction of the memory.

The habit to carry: when KV cache memory limits your context length or batch size, GQA is the first lever, and it is nearly free — reducing kv_heads shrinks the cache linearly while leaving the query heads and the model's attention capacity intact. Read the reduction straight off query_heads/groups.

## Boss fight

The instructive failure is a long-context feature that runs out of memory on the cache, not the model.

A team fine-tunes a 32-head multi-head-attention model and wants to serve it at 32K context for document analysis. The weights fit comfortably on the GPU, but at 32K tokens the KV cache is eight times the 4096-token size — 17 GB for a single sequence — and with any batch at all it blows past the GPU's memory. They conclude the model is "too big for long context" and cap the feature at 4K, disappointing users. But the model was never the problem; the cache was, and converting the attention to GQA with 8 groups would have cut the cache 4× — 32K context back within reach, batches possible — at a small, recoverable quality cost that a brief fine-tune recovers. Modern models ship with GQA from the start precisely so this wall is never hit; a model that did not can often be converted.

Your turn, two moves. First, find the group count for a memory budget. If your GPU can spare 800 MB for the KV cache at 4096 tokens, what GQA group count fits? The MHA cache is 2147 MB, so you need a reduction of at least 2147/800 ≈ 2.7×, which means query_heads/groups ≥ 2.7, so groups ≤ 32/2.7 ≈ 11 — round to 8 (a 4× reduction, 537 MB) for headroom. The group count is a direct function of your memory budget. Second, see the quality-memory trade at the extreme. Drop to MQA (1 group, 32× reduction, 67 MB) and predict: the cache is tiny, but with all 32 query heads sharing a single set of keys and values you lose the head diversity in what gets attended to, and measured quality drops more than with GQA. That is why GQA, not MQA, is the default — MQA's extra memory saving over GQA (67 MB vs 537 MB) is usually not worth its larger quality hit, so the sweet spot is a handful of groups, not one.

## External resources

Ainslie et al., "GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints" (2023), is the paper that named GQA and showed you can convert an existing MHA model to GQA with a short uptraining, landing near MHA quality at MQA-like speed.

Shazeer's "Fast Transformer Decoding: One Write-Head is All You Need" (2019) introduced multi-query attention and the KV-cache-memory motivation, the extreme end of the spectrum this module walks.

For the practical footprint, the Llama 2 and later model papers document their use of GQA and the context lengths and batch sizes it enables; their inference-memory discussions show the KV cache, not the weights, as the long-context bottleneck that GQA relieves.
