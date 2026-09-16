"""Keep the first tokens in a sliding-window cache -- the model dumps excess attention on them, and evicting them forces that mass onto recent tokens.

Long-context inference cannot keep every past token's key and value in memory forever, so a common fix is a SLIDING WINDOW: keep only the last W tokens in the KV cache and evict the rest. It seems safe -- attention is local, recent tokens matter most -- and it quietly breaks generation quality in a way that puzzled people until it was explained. The cause is a property of trained transformers called the ATTENTION SINK: models learn to send a large share of their attention to the very first token(s), not because those tokens are informative, but because the softmax over attention scores must sum to 1, and when a query has little it genuinely needs to attend to, that leftover probability has to go somewhere. The model learns to park it on the first token -- a stable, always-present place to dump attention it does not want.

That makes the first token a load-bearing part of the mechanism even though it carries no relevant content. When the sliding window evicts it, the softmax is suddenly taken over the recent tokens only, and the large attention mass that used to rest on the sink has nowhere to go. It does not vanish -- softmax renormalizes -- so it is forced onto the recent tokens, ballooning their weights and massively over-concentrating attention on whatever is in the window. The model, which had learned to attend to almost nothing (the sink) in many situations, is now compelled to attend hard to recent tokens, and its outputs degrade -- the fluent-but-wrong collapse that appears exactly when the earliest tokens roll out of the window.

The fix, from the StreamingLLM work, is small and surgical: always keep the first few tokens in the cache as dedicated attention sinks, alongside the recent sliding window. The sink tokens absorb the excess attention as the model expects, so the recent-token weights stay at their correct (small) magnitudes, and streaming inference over arbitrarily long inputs stays stable at bounded memory. You do not need the first tokens' content; you need their role as a sink.

The rule: in a sliding-window KV cache, keep the first few tokens as attention sinks rather than evicting them, because trained models dump excess attention on the first token(s), so evicting them forces that large attention mass onto the recent tokens -- over-concentrating attention and collapsing quality -- while retaining them lets the sink absorb the excess and keeps the recent-token weights correct.

On this fixture the query's attention logits are 5 to the sink and 1,0,2 to three window tokens. With the sink, softmax gives it 0.93 of the attention and the window tokens their small correct weights; dropping the sink forces the softmax onto the window only, ballooning the top window weight from 0.046 to 0.665. This computes both.

  --weights   the softmax attention weights with the sink present vs with it evicted
  --sink      how much attention the sink absorbs, and how the window weights inflate when it is removed
  --check     the sink absorbs most attention; evicting it inflates and over-concentrates the recent-token weights

sink_logit and window_logits are the fixture; every softmax weight, with and without the sink, is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "attnsink.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


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


# ----------------------------------------------------------------- printing

def fmt(ws):
    return "[" + ", ".join("%.3f" % w for w in ws) + "]"


def weights_view(data):
    sink, window = data["sink_logit"], data["window_logits"]
    sw, ww = with_sink(sink, window)
    dw = drop_sink(window)
    print("WEIGHTS — attention with the sink present vs evicted")
    print("-" * 60)
    print("  window logits          = %s" % window)
    print("  with sink:  sink %.3f  window %s" % (sw, fmt(ww)))
    print("  drop sink:            window %s" % fmt(dw))
    print("-" * 60)
    print("  evicting the sink forces its attention mass onto the window tokens")


def sink_view(data):
    sink, window = data["sink_logit"], data["window_logits"]
    sw, ww = with_sink(sink, window)
    dw = drop_sink(window)
    print("SINK — how much the sink absorbs, and the window inflation on eviction")
    print("-" * 62)
    print("  sink absorbs %.1f%% of the attention (the excess the model parks there)" % (100 * sw))
    print("  top window weight: with sink %.3f -> dropped %.3f (%.1fx larger)" % (max(ww), max(dw), max(dw) / max(ww)))
    print("-" * 62)
    print("  argmax window token unchanged (order preserved); magnitudes corrupted")


def check(data):
    print("SELF-TEST — the sink absorbs most attention; evicting it inflates and over-concentrates the recent-token weights")
    print("-" * 118)
    sink, window = data["sink_logit"], data["window_logits"]
    sw, ww = with_sink(sink, window)
    dw = drop_sink(window)

    sink_logit_highest = sink > max(window)
    print("  the sink's attention logit is the largest (a learned sink) = %s (%.1f > %.1f)" % (sink_logit_highest, sink, max(window)))

    sink_absorbs_majority = sw > 0.5
    print("  the sink absorbs the majority of attention = %s (%.3f)" % (sink_absorbs_majority, sw))

    dropping_inflates_window = all(dw[i] > ww[i] for i in range(len(window)))
    print("  evicting the sink inflates every window weight = %s (%s -> %s)" % (dropping_inflates_window, fmt(ww), fmt(dw)))

    dropping_overconcentrates = max(dw) > 3 * max(ww)
    print("  evicting the sink over-concentrates attention on recent tokens = %s (top %.3f -> %.3f)" % (dropping_overconcentrates, max(ww), max(dw)))

    order_preserved = ww.index(max(ww)) == dw.index(max(dw))
    print("  the relative order among window tokens is preserved = %s (info present, magnitudes wrong)" % order_preserved)

    keep_sink_preserves = abs(ww[-1] - 0.046) < 0.01
    print("  keeping the sink preserves the small correct window weights = %s (top window %.3f)" % (keep_sink_preserves, max(ww)))

    ok = (sink_logit_highest and sink_absorbs_majority and dropping_inflates_window and dropping_overconcentrates
          and order_preserved and keep_sink_preserves)
    print("-" * 118)
    print("SELF-TEST %s  sink_logit_highest=%s  sink_absorbs_majority=%s  dropping_inflates_window=%s  dropping_overconcentrates=%s  order_preserved=%s  keep_sink_preserves=%s"
          % ("PASS" if ok else "FAIL", sink_logit_highest, sink_absorbs_majority, dropping_inflates_window, dropping_overconcentrates, order_preserved, keep_sink_preserves))
    return ok


def main():
    p = argparse.ArgumentParser(description="Attention sinks: in a sliding-window KV cache, keep the first few tokens as attention sinks rather than evicting them, because trained models dump excess attention on the first token(s), so evicting them forces that large attention mass onto the recent tokens -- over-concentrating attention and collapsing quality -- while retaining them lets the sink absorb the excess and keeps the recent-token weights correct.")
    p.add_argument("--weights", action="store_true")
    p.add_argument("--sink", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("sink_logit=%.1f  window_logits=%s  file=%s  (the attention logits are a fixture)"
          % (data["sink_logit"], data["window_logits"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.weights:
        weights_view(data)
    elif args.sink:
        sink_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
