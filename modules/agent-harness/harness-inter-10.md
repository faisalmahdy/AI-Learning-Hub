---
id: harness-inter-10
title: Keep the prompt's stable segments first — a volatile token up front busts the cache and reprocesses everything
topic: agent-harness
level: intermediate
status: ready
time: 21 min
summary: A prompt cache reuses the longest leading run of tokens identical to the last request, so where you place a changing segment decides the whole cache. A 20-token timestamp placed first drops the cache to 0 and reprocesses all 1820 tokens; placed last, the cache covers the 1800-token stable prefix and reprocesses only 20 — the same content, 91× less work.
eli5: Imagine re-reading a long book from the start every time one word on the first page changes. If the changing word is on the last page instead, you can keep everything you already read and just re-read that page. A prompt cache is the same: put the thing that changes at the end, not the beginning.
---

## Why this module

Where the harness puts one changing line in the prompt can be the difference between reprocessing twenty tokens and reprocessing two thousand, on every single request.

Modern model APIs cache the prompt prefix. When a request's prompt begins with the same tokens as the previous one, the model reuses the computation for that shared leading run and only processes the tokens after the first point of difference. This is a large, real speedup and cost saving — the cached prefix is often billed at a fraction of the normal rate and skips most of the compute. But it works on the *prefix*, the longest common run from the very start, and that makes it exquisitely sensitive to order. The cache reuses tokens up to the first difference and not one token further.

So a single volatile segment — a timestamp, a per-request id, a random nonce, the current date — placed at the top of the prompt is catastrophic for caching. It differs on every request, so the very first tokens differ, so the common prefix is zero, so nothing is cached and the entire prompt is reprocessed from scratch every time. The system prompt, the tool definitions, the whole conversation history — all of it stable, all of it re-crunched, because one small changing thing sat in front of it. The harness assembled a perfectly cacheable prompt and then defeated the cache with placement.

The fix is just ordering: put the stable segments first and the volatile ones last. The system prompt, tools, and history form a long stable prefix the cache can reuse in full; the changing timestamp goes at the end, where only its few tokens fall outside the cache. Same content, same tokens, one reordering, and the reprocessed work drops by orders of magnitude.

We will lay out the same four segments two ways. Volatile-first caches 0 tokens and reprocesses all 1820. Volatile-last caches 1800 and reprocesses 20. The entire difference is the position of a 20-token segment.

**A prompt cache reuses the longest common prefix, so one volatile segment at the front zeroes it out; move the changing content to the end and the whole stable prefix caches.**

## Concepts

The cache's unit is the common prefix, and the word prefix is doing all the work. The cache compares this prompt to the last one token by token from position zero, and it can reuse everything up to the first token that differs — then it must process everything from that point to the end, because a change anywhere invalidates the cache for all tokens after it. This is not a limitation to engineer around; it is inherent to how attention builds representations left to right, where each token's computation depends on everything before it. A token can only be cached if every token before it is unchanged.

That gives a simple rule for what to cache: order the prompt from most stable to least stable. The system prompt almost never changes — it belongs first. Tool definitions change rarely — next. Conversation history grows but its existing prefix is stable within a request pair — after that. And anything that changes every request goes last, so it is the only thing outside the cache. The reprocessed cost becomes just the size of the volatile tail, no matter how large the stable prefix is. Violate the ordering — sprinkle a volatile value early — and you truncate the cacheable prefix at that point, throwing away the caching of everything after it.

<svg role="img" aria-label="Reprocessed tokens as the volatile segment moves from front to middle to back of the prompt: 1820, then 1020, then 20" viewBox="0 0 460 160" width="460" height="160">
  <rect x="0" y="0" width="460" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">reprocessed tokens vs the volatile segment's position</text>
  <line x1="60" y1="130" x2="440" y2="130" stroke="var(--line)"/>
  <rect x="90" y="35" width="70" height="95" fill="var(--s2)" stroke="var(--line)"/><text x="104" y="29" font-family="var(--mono)" font-size="9" fill="var(--s2)">1820</text><text x="92" y="146" font-family="var(--mono)" font-size="8" fill="var(--muted)">front</text>
  <rect x="200" y="77" width="70" height="53" fill="var(--s1)" stroke="var(--line)"/><text x="214" y="71" font-family="var(--mono)" font-size="9" fill="var(--ink)">1020</text><text x="205" y="146" font-family="var(--mono)" font-size="8" fill="var(--muted)">middle</text>
  <rect x="310" y="128" width="70" height="2" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="324" y="122" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">20</text><text x="326" y="146" font-family="var(--mono)" font-size="8" fill="var(--muted)">back</text>
</svg>
^ The reprocessed cost is everything from the volatile segment onward, so moving it back down the prompt monotonically shrinks the bill — front is worst, back is best.

The magnitude of the mistake is what surprises people. It is not proportional to the size of the volatile segment; it is proportional to how much stable content sits *behind* it. A 20-token timestamp at the front does not cost you 20 tokens — it costs you the caching of the 1800 tokens it precedes. The smaller the volatile segment and the larger the prompt behind it, the more disproportionate the damage, which is exactly the case for agents: a huge stable system-and-tools-and-history prefix, defeated by one tiny changing field placed carelessly.

The common culprits are worth memorizing because they look innocent. A "current time" injected at the top of the system prompt for freshness. A request id added to the front for tracing. A retrieved-context block reordered each turn. A tool list re-sorted nondeterministically. Each is a small, well-intentioned change that moves or introduces a difference early in the prompt and silently collapses the cache hit rate. The habit that prevents all of them is to treat prompt order as a cache-optimization decision: stable first, volatile last, order deterministic.

**The cost of a volatile segment is not its own size but the size of the stable content behind it — so a tiny changing field early in a big prompt is the most expensive placement there is.**

## Worked example

The fixture is the same four segments arranged two ways.

```json filename=modules/agent-harness/code/harness-inter-10/prompt.json:25-38 COMPLETE
  "layouts": {
    "volatile_first": [
      "timestamp",
      "system",
      "tools",
      "history"
    ],
    "volatile_last": [
      "system",
      "tools",
      "history",
      "timestamp"
    ]
  }
```

The segments are a 500-token system prompt, 300 tokens of tools, 1000 tokens of history — all stable — and a 20-token timestamp that changes every request. The two layouts differ only in where the timestamp goes.

```text filename=modules/agent-harness/code/harness-inter-10/prefix.py --layouts
LAYOUTS — the two segment orderings (V marks the volatile segment)
------------------------------------------------------------
  volatile_first timestamp(V) system tools history
  volatile_last  system tools history timestamp(V)
------------------------------------------------------------
  same segments, same tokens (1820 total) -- only the order differs.
```

The cache reuses the leading run of stable segments and breaks at the first volatile one.

```python filename=modules/agent-harness/code/harness-inter-10/prefix.py:41-51 COMPLETE
def cached_tokens(order, segments):
    """Longest common prefix with the previous request: the leading run of STABLE segments, in tokens.

    The cache breaks at the first segment that changed (a volatile one); everything from there is reprocessed.
    """
    cached = 0
    for name in order:
        if not segments[name]["stable"]:
            break               # first volatile segment: the common prefix ends here
        cached += segments[name]["tokens"]
    return cached
```

The total is the sum of all segments, and everything not cached is reprocessed.

```python filename=modules/agent-harness/code/harness-inter-10/prefix.py:54-55 COMPLETE
def total_tokens(segments):
    return sum(s["tokens"] for s in segments.values())
```

```python filename=modules/agent-harness/code/harness-inter-10/prefix.py:58-59 COMPLETE
def reprocessed(order, segments):
    return total_tokens(segments) - cached_tokens(order, segments)
```

Predict: volatile-first breaks at token 0, so cached 0 and reprocessed 1820. Volatile-last has the three stable segments first (500 + 300 + 1000 = 1800) before it breaks, so cached 1800 and reprocessed 20. Run it.

```text filename=modules/agent-harness/code/harness-inter-10/prefix.py --cache
CACHE — cached vs reprocessed tokens per layout (total 1820)
------------------------------------------------------------
  volatile_first cached    0   reprocessed 1820   (0% cached)
  volatile_last  cached 1800   reprocessed   20   (99% cached)
------------------------------------------------------------
  volatile-first reprocesses everything; volatile-last reprocesses only the timestamp.
```

Volatile-first caches nothing — 0% — and reprocesses the full 1820 tokens on every request, because the timestamp at position zero makes the common prefix empty. Volatile-last caches 1800 tokens, 99%, and reprocesses only the 20-token timestamp. Ninety-one times less work, from moving one segment from the front to the back. The content is byte-for-byte identical between the two layouts; the only thing that changed is that the volatile segment stopped shadowing the stable ones.

<svg role="img" aria-label="Two prompt layouts as bars: volatile-first has the timestamp at the start so the cache break is at position zero; volatile-last has it at the end so the stable prefix caches" viewBox="0 0 460 180" width="460" height="180">
  <rect x="0" y="0" width="460" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">volatile-first: cache breaks immediately</text>
  <rect x="20" y="30" width="18" height="26" fill="var(--s2)" stroke="var(--line)"/><text x="20" y="72" font-family="var(--mono)" font-size="8" fill="var(--s2)">V 20</text>
  <rect x="38" y="30" width="100" height="26" fill="var(--acc-soft)" stroke="var(--line)"/><text x="60" y="47" font-family="var(--mono)" font-size="8" fill="var(--ink)">system 500</text>
  <rect x="138" y="30" width="70" height="26" fill="var(--acc-soft)" stroke="var(--line)"/><text x="150" y="47" font-family="var(--mono)" font-size="8" fill="var(--ink)">tools 300</text>
  <rect x="208" y="30" width="200" height="26" fill="var(--acc-soft)" stroke="var(--line)"/><text x="260" y="47" font-family="var(--mono)" font-size="8" fill="var(--ink)">history 1000</text>
  <line x1="20" y1="26" x2="20" y2="60" stroke="var(--s2)" stroke-width="2"/><text x="80" y="88" font-family="var(--mono)" font-size="8" fill="var(--s2)">reprocess all 1820 →</text>
  <text x="16" y="112" font-family="var(--mono)" font-size="10" fill="var(--muted)">volatile-last: stable prefix caches</text>
  <rect x="20" y="122" width="100" height="26" fill="var(--acc-line)" stroke="var(--line)"/><text x="42" y="139" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">system 500</text>
  <rect x="120" y="122" width="70" height="26" fill="var(--acc-line)" stroke="var(--line)"/><text x="132" y="139" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">tools 300</text>
  <rect x="190" y="122" width="200" height="26" fill="var(--acc-line)" stroke="var(--line)"/><text x="242" y="139" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">history 1000</text>
  <rect x="390" y="122" width="18" height="26" fill="var(--s2)" stroke="var(--line)"/><text x="390" y="164" font-family="var(--mono)" font-size="8" fill="var(--s2)">V 20</text>
  <line x1="390" y1="118" x2="390" y2="152" stroke="var(--s2)" stroke-width="2"/><text x="120" y="164" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">← cached 1800   reprocess 20 →</text>
</svg>
^ The cache reaches from the start to the first changing segment; put it at the front and the reach is zero, put it at the back and the reach is the whole stable prefix.

<svg role="img" aria-label="Cached versus reprocessed tokens: volatile-first 0 cached and 1820 reprocessed, volatile-last 1800 cached and 20 reprocessed" viewBox="0 0 460 160" width="460" height="160">
  <rect x="0" y="0" width="460" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">reprocessed tokens per request (lower is better)</text>
  <line x1="60" y1="130" x2="440" y2="130" stroke="var(--line)"/>
  <rect x="100" y="35" width="90" height="95" fill="var(--s2)" stroke="var(--line)"/><text x="112" y="29" font-family="var(--mono)" font-size="10" fill="var(--s2)">1820</text><text x="98" y="146" font-family="var(--mono)" font-size="8" fill="var(--muted)">volatile-first</text>
  <rect x="280" y="129" width="90" height="1" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="300" y="123" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">20</text><text x="278" y="146" font-family="var(--mono)" font-size="8" fill="var(--muted)">volatile-last</text>
</svg>
^ The same prompt reprocesses 1820 tokens per request in the bad order and 20 in the good one — a 91× gap decided by segment placement.

## Build

Reproduce the cache counts. Pure standard library, deterministic, so 0/1820 and 1800/20 come out exactly.

Run `--layouts` for the orderings, `--cache` for the counts, `--check` for the gate. The self-test pins the mechanism: volatile-first caches nothing, volatile-last caches the whole stable prefix, it reprocesses far less, and the two layouts are the identical content.

```python filename=modules/agent-harness/code/harness-inter-10/prefix.py:97-103 COMPLETE
    first_caches_nothing = cached_tokens(first, segs) == 0
    print("  volatile-first caches nothing (reprocesses all) = %s (cached %d, reprocessed %d)"
          % (first_caches_nothing, cached_tokens(first, segs), reprocessed(first, segs)))

    last_caches_prefix = cached_tokens(last, segs) == stable_total
    print("  volatile-last caches the whole stable prefix = %s (cached %d of %d stable)"
          % (last_caches_prefix, cached_tokens(last, segs), stable_total))
```

The `same_content` check — that both layouts contain the identical set of segments — is what makes the result a lesson about *ordering* rather than about content. Without it, someone could dismiss the win as "volatile-last just has less stuff." Forcing the two layouts to be permutations of the same segments proves that not a single token was added or removed; the 91× difference is purely where the volatile segment sits. Here is the full gate.

```text filename=modules/agent-harness/code/harness-inter-10/prefix.py --check
SELF-TEST — the volatile-first layout caches nothing; volatile-last caches the whole stable prefix
--------------------------------------------------------------------------------------------
  volatile-first caches nothing (reprocesses all) = True (cached 0, reprocessed 1820)
  volatile-last caches the whole stable prefix = True (cached 1800 of 1800 stable)
  volatile-last reprocesses far fewer tokens = True (20 vs 1820)
  the two layouts contain the identical segments = True (order is the only difference)
--------------------------------------------------------------------------------------------
SELF-TEST PASS  first_caches_nothing=True  last_caches_prefix=True  last_reprocesses_less=True  same_content=True
```

Four True flags. First_caches_nothing: the volatile-first layout has a zero-token cache prefix. Last_caches_prefix: the volatile-last layout caches all 1800 stable tokens. Last_reprocesses_less: 20 tokens instead of 1820. Same_content: the layouts are permutations, so order is the only variable. The last flag is the control — it rules out the boring explanation and leaves only the real one.

**The same-content check forces the two layouts to be permutations, so the 91× gap is attributable to order alone, not to one layout carrying less.**

## Definition of done

You are done when you reproduce the counts and can explain why the cost is what it is.

Concretely: `--cache` shows volatile-first at 0 cached / 1820 reprocessed and volatile-last at 1800 / 20; `--check` prints PASS with four True flags. You can explain why a prompt cache works on the common prefix and why a change anywhere invalidates everything after it (left-to-right attention). You can state the ordering rule — most stable first, volatile last — and explain why the cost of a misplaced volatile segment is the size of the stable content behind it, not its own size. And you can name the common culprits: an injected timestamp, a request id, a re-sorted tool list, a reordered context block.

The habit to carry: treat prompt assembly order as a cache decision. Put the system prompt, tools, and stable history first; put anything that changes per request last; keep the ordering of everything deterministic. When cache hit rates are low or per-request latency is mysteriously high, look for a volatile value that migrated toward the front of the prompt.

## Boss fight

The instructive failure is a latency regression that a one-line "improvement" caused and that no profiler points at.

An agent runs fine, with high cache hit rates, until someone adds the current timestamp to the top of the system prompt so the model "knows what time it is." It is one line, it passes review, and it quietly drops the cache hit rate to zero: every request now reprocesses the entire multi-thousand-token prompt because the first thing in it changes every second. Latency doubles, token costs spike, and the timestamp — twenty tokens of it — is blamed for none of it because it is so small. The fix is to move the timestamp to the end of the prompt, after the stable content, where it costs its own twenty tokens and nothing more. The bug was not the timestamp; it was its position.

Your turn, two moves. First, quantify the leverage. The volatile segment is 20 tokens but sitting first it costs the caching of 1800. Move it to the middle — after system and tools but before history — and predict: it now caches 800 (system + tools) and reprocesses 1020 (history + timestamp), a partial loss proportional to what sits behind it. Confirm that the reprocessed count is always "everything from the first volatile segment onward," so the volatile segment's position directly sets the bill. Second, handle unavoidable volatility. Sometimes you genuinely need per-request data early — say a user id the system prompt references. Predict the mitigation: split the prompt so the truly-stable part (generic system instructions, tools) forms a cacheable prefix and the per-user part comes after it, so at least the shared prefix caches across all users even if the per-user tail does not. The principle generalizes: push every difference as late as its dependencies allow, so the longest possible prefix stays common.

## External resources

Anthropic's prompt caching documentation and OpenAI's automatic prompt caching guide both state the prefix rule explicitly — the cache matches from the start of the prompt and breaks at the first difference — and both advise putting static content first and variable content last.

For the agent-specific angle, guides on building with tool use and long system prompts emphasize keeping tool definitions and system instructions stable and early precisely so they stay cached across a multi-turn session.

For why the prefix constraint is fundamental rather than an implementation choice, any explanation of the transformer KV cache covers it: cached keys and values are valid only if every preceding token is unchanged, which is the same left-to-right dependency that makes the prompt cache a prefix cache.
