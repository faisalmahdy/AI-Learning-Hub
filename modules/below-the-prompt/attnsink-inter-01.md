---
id: attnsink-inter-01
title: Keep the first tokens in a sliding-window cache — the model dumps excess attention on them, and evicting them collapses quality
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: Long-context inference cannot keep every past token's key and value in memory forever, so a common fix is a sliding window — keep only the last W tokens in the KV cache and evict the rest. It seems safe (attention is local, recent tokens matter most) and quietly breaks generation quality, for a reason that puzzled people until it was explained: the attention sink. Trained transformers learn to send a large share of their attention to the very first token(s), not because those tokens are informative, but because the softmax over attention scores must sum to 1, and when a query has little it genuinely needs to attend to, that leftover probability has to go somewhere — the model learns to park it on the first token, a stable always-present place to dump attention it does not want. That makes the first token load-bearing even though it carries no relevant content. When the sliding window evicts it, the softmax is taken over the recent tokens only, and the large mass that used to rest on the sink has nowhere to go; softmax renormalizes, so it is forced onto the recent tokens, ballooning their weights and over-concentrating attention exactly when the earliest tokens roll out of the window. The fix, from StreamingLLM, is surgical: always keep the first few tokens as dedicated sinks alongside the recent window, so they absorb the excess attention and the recent-token weights stay correct at bounded memory. On a fixture where the query's attention logits are 5 to the sink and 1, 0, 2 to three window tokens, keeping the sink gives it 0.93 of the attention and the window tokens small correct weights (0.017, 0.006, 0.046), while evicting it forces the softmax onto the window and balloons the top window weight from 0.046 to 0.665 — a 14× over-concentration, with the relative order preserved but the magnitudes corrupted.
eli5: Imagine a person who, when they don't have anything important to look at, always rests their eyes on a blank spot on the wall — it's a comfortable default place to "look at nothing." Now imagine you cover up that blank spot. Their eyes can't rest on nothing anymore, so they're forced to stare hard at whatever else is in the room, even things they didn't care about, and they start acting on those unimportant things. The blank spot wasn't interesting, but it was doing an important job: absorbing their gaze when nothing mattered. The fix is simple — leave the blank spot uncovered. In a language model, the "blank spot" is the first token, and covering it up is what a sliding-window cache does when it throws the earliest tokens away.
---

## Why this module

The KV cache grows with context length, so streaming or very-long-context inference needs to bound it, and a sliding window — keep the last W tokens, drop the rest — is the obvious bound. It is also a trap, and the trap is instructive because it reveals something non-obvious about how trained transformers actually use attention: they rely on a token that carries no information at all. Understanding the attention sink explains a class of "the model gets fluent-but-wrong the moment the context scrolls" bugs, and it is a clean example of an emergent behavior that only shows up when you probe the mechanism.

The sink arises from softmax. Attention weights are a softmax over scores, so they must sum to 1 — the model cannot choose to attend to nothing, only to redistribute a fixed total. But there are many positions where the model genuinely has little it needs from the context, and it needs a place to put the attention it is forced to allocate. It learns to put it on the first token: always present, positionally stable, and (because the model learns not to write useful information there) safe to ignore as a value. The first token becomes a sink that soaks up excess attention.

Evicting that sink, as a naive sliding window does, removes the drain and forces the excess onto real tokens. This module computes the attention weights with the sink present and with it evicted.

**In a sliding-window KV cache, keep the first few tokens as attention sinks rather than evicting them, because trained models dump excess attention on the first token(s), so evicting them forces that large attention mass onto the recent tokens — over-concentrating attention and collapsing quality — while retaining them lets the sink absorb the excess and keeps the recent-token weights correct.**

## Concepts

The fixture is one query's attention logits: a large score to the sink (the first token) and the real relevance scores to three tokens in the recent window.

```json filename=modules/below-the-prompt/code/attnsink-inter-01/attnsink.json:3-4 COMPLETE
  "sink_logit": 5.0,
  "window_logits": [1.0, 0.0, 2.0]
```

Attention is a softmax over the scores. With the sink, the softmax runs over `[sink] + window`; without it (the sliding window having evicted the first token), it runs over the window alone.

```python filename=modules/below-the-prompt/code/attnsink-inter-01/attnsink.py:33-48 COMPLETE
def softmax(logits):
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    total = sum(exps)
    return [e / total for e in exps]


def with_sink(sink, window):
    """Softmax over [sink] + window; returns (sink_weight, window_weights)."""
    w = softmax([sink] + window)
    return w[0], w[1:]


def drop_sink(window):
    """Softmax over the window only (sink evicted by the sliding cache)."""
    return softmax(window)
```

The key fact is that softmax sums to 1: the sink's large share is not free-floating, it is part of a fixed budget, so removing the sink does not remove its share — it redistributes it onto whatever remains.

<svg role="img" aria-label="Two attention distributions summing to 1: with the sink, most mass is on the sink and window weights are tiny; without the sink, the same total mass is forced onto the window tokens, making them large" viewBox="0 0 320 130">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">attention weights (each row sums to 1)</text>
  <text x="10" y="40" font-size="8" fill="var(--s2)">with sink</text>
  <rect x="70" y="30" width="200" height="16" fill="var(--muted)"/><text x="120" y="42" font-size="7.5" fill="var(--panel)">sink 0.93</text>
  <rect x="270" y="30" width="15" height="16" fill="var(--s1)"/>
  <text x="288" y="42" font-size="7" fill="var(--s1)">window tiny</text>
  <text x="10" y="76" font-size="8" fill="var(--s1)">drop sink</text>
  <rect x="70" y="66" width="53" height="16" fill="var(--s1)" opacity="0.5"/><text x="76" y="78" font-size="7" fill="var(--panel)">0.245</text>
  <rect x="123" y="66" width="19" height="16" fill="var(--s1)" opacity="0.5"/>
  <rect x="142" y="66" width="143" height="16" fill="var(--s1)"/><text x="180" y="78" font-size="7.5" fill="var(--panel)">0.665 (was 0.046)</text>
  <text x="10" y="110" font-size="7.5" fill="var(--ink)">the sink's 0.93 doesn't vanish — softmax forces it onto the window tokens</text>
</svg>
^ Both rows sum to 1. With the sink, it holds 0.93 and the window tokens are tiny. Evicting the sink does not delete its 0.93 — the softmax renormalizes and pours it onto the window tokens, so the top one jumps from 0.046 to 0.665.

**The sink is a drain for attention the model is forced to allocate but does not want — remove the drain and the same fixed attention budget floods the recent tokens.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the attention step of a streaming decoder, reduced to one query over a sink plus a three-token window so every weight is checkable by hand.

Run `--weights` to see the attention with and without the sink.

```text filename=attnsink.py --weights
  window logits          = [1.0, 0.0, 2.0]
  with sink:  sink 0.930  window [0.017, 0.006, 0.046]
  drop sink:            window [0.245, 0.090, 0.665]
  evicting the sink forces its attention mass onto the window tokens
```

With the sink present, the query puts 0.93 of its attention on it and only tiny amounts on the window tokens (the largest is 0.046). That is the model attending to "nothing much" — parking its budget on the sink. Drop the sink, and the window tokens absorb the freed mass: 0.245, 0.090, 0.665. The token that had 0.046 now has 0.665. The model that wanted to barely attend to the window is now attending overwhelmingly to it, because the softmax had to put the sink's 0.93 somewhere.

The `--sink` view computes the absorbed share and the inflation factor directly.

```python filename=modules/below-the-prompt/code/attnsink-inter-01/attnsink.py:71-77 COMPLETE
    sink, window = data["sink_logit"], data["window_logits"]
    sw, ww = with_sink(sink, window)
    dw = drop_sink(window)
    print("SINK — how much the sink absorbs, and the window inflation on eviction")
    print("-" * 62)
    print("  sink absorbs %.1f%% of the attention (the excess the model parks there)" % (100 * sw))
    print("  top window weight: with sink %.3f -> dropped %.3f (%.1fx larger)" % (max(ww), max(dw), max(dw) / max(ww)))
```

Running it quantifies the absorption and the inflation.

```text filename=attnsink.py --sink
  sink absorbs 93.0% of the attention (the excess the model parks there)
  top window weight: with sink 0.046 -> dropped 0.665 (14.4x larger)
  argmax window token unchanged (order preserved); magnitudes corrupted
```

The sink absorbs 93% — proof it is a genuine sink, not a minor contributor. Evicting it makes the top window weight 14.4× larger. And the note matters: the argmax among the window tokens is unchanged (the third token is still the strongest both ways), so the information about which token matters is preserved; what is destroyed is the magnitude — the model is forced into attending 66% to a token it wanted to attend 5% to, and that over-concentration is what degrades the generation.

**Evicting the sink turns a 0.046 window weight into 0.665, a 14× over-concentration, while keeping which token is strongest — the ranking survives, the calibration of attention does not, and that miscalibration is the quality collapse.**

## Build

The self-test asserts the mechanism: the sink's logit is the largest (a learned sink), it absorbs the majority of attention, and evicting it inflates every window weight.

```python filename=modules/below-the-prompt/code/attnsink-inter-01/attnsink.py:89-99 COMPLETE
    sink_logit_highest = sink > max(window)
    print("  the sink's attention logit is the largest (a learned sink) = %s (%.1f > %.1f)" % (sink_logit_highest, sink, max(window)))

    sink_absorbs_majority = sw > 0.5
    print("  the sink absorbs the majority of attention = %s (%.3f)" % (sink_absorbs_majority, sw))

    dropping_inflates_window = all(dw[i] > ww[i] for i in range(len(window)))
    print("  evicting the sink inflates every window weight = %s (%s -> %s)" % (dropping_inflates_window, fmt(ww), fmt(dw)))

    dropping_overconcentrates = max(dw) > 3 * max(ww)
    print("  evicting the sink over-concentrates attention on recent tokens = %s (top %.3f -> %.3f)" % (dropping_overconcentrates, max(ww), max(dw)))
```

<svg role="img" aria-label="A sliding window over tokens: naive eviction drops the sink token at position 0 and quality collapses; StreamingLLM keeps the sink plus the recent window and stays stable" viewBox="0 0 320 120">
  <text x="10" y="16" font-size="8.5" fill="var(--s2)">naive sliding window: evict position 0 (the sink)</text>
  <rect x="14" y="24" width="20" height="16" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/><text x="18" y="36" font-size="7" fill="var(--muted)">0✗</text>
  <rect x="40" y="24" width="20" height="16" fill="var(--s2)"/><rect x="62" y="24" width="20" height="16" fill="var(--s2)"/><rect x="84" y="24" width="20" height="16" fill="var(--s2)"/>
  <text x="112" y="36" font-size="7.5" fill="var(--s2)">sink gone → attention floods window → collapse</text>
  <text x="10" y="72" font-size="8.5" fill="var(--s1)">StreamingLLM: keep the sink + recent window</text>
  <rect x="14" y="80" width="20" height="16" fill="var(--s1)"/><text x="18" y="92" font-size="7" fill="var(--panel)">0</text>
  <text x="36" y="92" font-size="9" fill="var(--muted)">…</text>
  <rect x="48" y="80" width="20" height="16" fill="var(--s1)"/><rect x="70" y="80" width="20" height="16" fill="var(--s1)"/><rect x="92" y="80" width="20" height="16" fill="var(--s1)"/>
  <text x="120" y="92" font-size="7.5" fill="var(--s1)">sink retained → absorbs excess → stable</text>
</svg>
^ The naive window evicts the first token to save memory, removing the sink; StreamingLLM keeps the first few tokens as sinks plus the recent window. A few extra cached tokens is the entire cost of avoiding the collapse.

Running the check confirms every clause, including that the order is preserved and keeping the sink preserves the small correct weights.

```text filename=attnsink.py --check
  the sink's attention logit is the largest (a learned sink) = True (5.0 > 2.0)
  the sink absorbs the majority of attention = True (0.930)
  evicting the sink inflates every window weight = True ([0.017, 0.006, 0.046] -> [0.245, 0.090, 0.665])
  evicting the sink over-concentrates attention on recent tokens = True (top 0.046 -> 0.665)
  the relative order among window tokens is preserved = True (info present, magnitudes wrong)
  keeping the sink preserves the small correct window weights = True (top window 0.046)
```

**The check pins the collapse to softmax renormalization — the sink's absorbed mass reappears on the window tokens when it is evicted — and shows the ranking surviving, so the failure is miscalibrated magnitudes, not lost information.**

## Definition of done

Two properties close it. The sink must absorb the majority of attention (it is a genuine sink, not incidental), and evicting it must over-concentrate the window while keeping the sink preserves the correct small weights. Together they show the sink is load-bearing and that retaining it is the fix.

```python filename=modules/below-the-prompt/code/attnsink-inter-01/attnsink.py:101-105 COMPLETE
    order_preserved = ww.index(max(ww)) == dw.index(max(dw))
    print("  the relative order among window tokens is preserved = %s (info present, magnitudes wrong)" % order_preserved)

    keep_sink_preserves = abs(ww[-1] - 0.046) < 0.01
    print("  keeping the sink preserves the small correct window weights = %s (top window %.3f)" % (keep_sink_preserves, max(ww)))
```

Three clarifications keep the mechanism accurate. First, the sink is not something you configure — it is emergent: models trained with softmax attention learn it on their own, which is why it is a property of the model you must respect at inference time, not a knob. StreamingLLM showed you can also train models with an explicit dedicated sink token to make the behavior cleaner, but for an existing model the fix is purely a caching decision. Second, the fix keeps the first few tokens (typically ~4), not their content specifically — you need the positions' role as sinks, so even keeping their keys/values while the actual text scrolls out of the usable context works; that is the whole trick of StreamingLLM, unbounded streaming at fixed memory. Third, this is distinct from ordinary context truncation quality loss: truncation drops information the model needed, whereas here the evicted token carried no information and dropping it still broke generation — the failure is mechanical (softmax renormalization), which is why it surprised people and why the fix is so cheap. The related lesson is to be suspicious of any cache-eviction or attention-masking change that removes the earliest tokens; they are doing a job even when they look empty.

<svg role="img" aria-label="Softmax forces a fixed budget of 1.0; with a sink slot the excess parks there, without one it must inflate the content weights" viewBox="0 0 320 100">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">softmax budget = 1.0 (must sum to one)</text>
  <text x="10" y="40" font-size="8" fill="var(--s1)">with sink slot:</text>
  <rect x="110" y="30" width="120" height="14" fill="var(--muted)"/><text x="118" y="41" font-size="7" fill="var(--panel)">excess → sink</text>
  <rect x="230" y="30" width="20" height="14" fill="var(--s1)"/><text x="254" y="41" font-size="7" fill="var(--s1)">content ok</text>
  <text x="10" y="72" font-size="8" fill="var(--s2)">no sink slot:</text>
  <rect x="110" y="62" width="140" height="14" fill="var(--s2)"/><text x="140" y="73" font-size="7" fill="var(--panel)">excess forced onto content</text>
  <text x="10" y="94" font-size="7.5" fill="var(--ink)">removing the sink slot doesn't shrink the budget — it relocates the excess onto content</text>
</svg>
^ Softmax must allocate a total of 1. A sink slot gives the model somewhere to put the excess it does not want on content; remove that slot and the same excess is forced onto the content tokens. The budget is conserved either way — only where the excess lands changes.

**Done means the sink absorbs the majority of attention, evicting it over-concentrates the window, and keeping it preserves the correct weights — a mechanical collapse from softmax renormalization, fixed by retaining a few emergent sink tokens at bounded memory.**

## Boss fight

Your team deploys a chat model with a sliding-window KV cache to support very long conversations at fixed memory, keeping the most recent 4096 tokens. It works well until a conversation exceeds the window, at which point the model starts producing fluent but increasingly incoherent and repetitive output — and the degradation begins right when the oldest tokens start getting evicted. A teammate blames the model's long-context training. What is actually happening, and what is the minimal fix?

It is the attention-sink collapse, not a training problem. The model learned to dump excess attention onto the first few tokens of the sequence, which serve as attention sinks — positions where it parks the attention budget softmax forces it to allocate when it has nothing else it needs to attend to. As long as the conversation fits in the window, those first tokens are cached and do their job. The moment the conversation exceeds 4096 tokens, the sliding window starts evicting the oldest tokens — including the sinks — and now the softmax has no sink to absorb the excess attention, so it renormalizes that large mass onto the recent tokens, over-concentrating attention and producing the fluent-but-incoherent, repetitive output you see. The timing (degradation starts exactly when eviction of the oldest tokens begins) is the giveaway. The minimal fix is the StreamingLLM approach: never evict the first few tokens (about four) — keep them pinned in the cache as attention sinks alongside the recent sliding window. You keep their cached keys and values even though their text is long out of the usable context; you need their role as a sink, not their content. That restores the sink so recent-token attention weights stay correctly calibrated, and streaming stays stable indefinitely at bounded memory, with essentially no extra cost (four tokens). Retraining is unnecessary — the model is fine; the cache eviction policy was removing a load-bearing part of the attention mechanism.

## External resources

Xiao et al., "Efficient Streaming Language Models with Attention Sinks" (StreamingLLM, 2023) — the paper that identified the attention-sink phenomenon, showed that evicting the initial tokens in a sliding-window cache collapses quality, and introduced keeping a few sink tokens (and training with a dedicated sink) as the fix.

Follow-up analyses of attention sinks (for example, work on why softmax forces the behavior and on "off-by-one"/softmax-with-a-null-slot proposals) — discussions of the root cause in the softmax normalization and alternative fixes at the architecture level, useful for seeing why the sink emerges and how else it can be addressed.
