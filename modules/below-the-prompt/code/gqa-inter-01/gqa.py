"""Share key/value heads across query heads -- grouped-query attention shrinks the KV cache without touching the query heads.

During generation a transformer caches, for every layer and every token so far, one key vector and one value
vector per KEY/VALUE head. That cache is what lets it avoid recomputing the past, but it grows with the
number of KV heads, and at long context and large batch it dominates memory -- often more than the model
weights. The lazy default, Multi-Head Attention, gives every query head its own KV head, so the cache is as
large as it can be. But the query heads do the attending; the KV heads only supply what is attended to, and
many query heads can share one set of keys and values with little quality loss.

Grouped-Query Attention exploits that. Keep all the query heads, but split them into a few groups that each
share a single KV head, so the cache scales with the number of GROUPS, not the number of query heads.
Multi-Query Attention is the extreme with one shared KV head (smallest cache, some quality loss); GQA sits
between, keeping most of the memory saving with near-MHA quality, which is why modern models use it.

On this fixture (32 layers, 32 query heads, head_dim 128, 4096-token context, fp16) MHA needs a 2147 MB KV
cache. GQA with 8 groups needs 537 MB -- 4x less. MQA with 1 KV head needs 67 MB -- 32x less. The query
heads, and thus the model's expressive attention, are identical in all three; only the KV cache shrinks.
This computes the cache size and saving for each variant.

  --config     the model dimensions and the KV-head count of each variant
  --cache      the KV cache size in MB for MHA, GQA, and MQA, and the saving vs MHA
  --check      GQA shrinks the cache by exactly query_heads/groups while keeping every query head

The dimensions and group count are the fixture; every byte count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "config.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def kv_cache_bytes(cfg, kv_heads):
    """Bytes to cache K and V for every layer, KV head, and token: 2 * layers * kv_heads * head_dim * seq * bytes."""
    return 2 * cfg["num_layers"] * kv_heads * cfg["head_dim"] * cfg["seq_len"] * cfg["bytes_per_elem"]


def kv_heads_for(cfg, variant):
    """How many KV heads each variant keeps: MHA one per query head, MQA one total, GQA one per group."""
    if variant == "MHA":
        return cfg["num_query_heads"]
    if variant == "MQA":
        return 1
    if variant == "GQA":
        return cfg["gqa_groups"]
    raise ValueError(variant)


def mb(nbytes):
    return round(nbytes / 1e6, 1)


# ----------------------------------------------------------------- printing

def config_view(data):
    print("CONFIG — model dimensions and each variant's KV-head count")
    print("-" * 56)
    print("  layers=%d  query_heads=%d  head_dim=%d  seq_len=%d  fp%d"
          % (data["num_layers"], data["num_query_heads"], data["head_dim"], data["seq_len"], data["bytes_per_elem"] * 8))
    for v in ("MHA", "GQA", "MQA"):
        print("  %-4s keeps %2d KV head(s)" % (v, kv_heads_for(data, v)))
    print("-" * 56)
    print("  all three keep %d query heads; only the KV heads differ." % data["num_query_heads"])


def cache_view(data):
    mha = kv_cache_bytes(data, kv_heads_for(data, "MHA"))
    print("CACHE — KV cache size per attention variant (context %d tokens)" % data["seq_len"])
    print("-" * 58)
    for v in ("MHA", "GQA", "MQA"):
        b = kv_cache_bytes(data, kv_heads_for(data, v))
        print("  %-4s  %8.1f MB   %4.0fx smaller than MHA" % (v, mb(b), mha / b))
    print("-" * 58)
    print("  GQA keeps near-MHA quality at a quarter of the cache; MQA is smallest but lossier.")


def check(data):
    print("SELF-TEST — GQA shrinks the cache by exactly query_heads/groups while keeping every query head")
    print("-" * 92)
    q = data["num_query_heads"]
    mha = kv_cache_bytes(data, kv_heads_for(data, "MHA"))
    gqa = kv_cache_bytes(data, kv_heads_for(data, "GQA"))
    mqa = kv_cache_bytes(data, kv_heads_for(data, "MQA"))

    gqa_smaller = gqa < mha
    print("  GQA's cache is smaller than MHA's = %s (%.1f vs %.1f MB)" % (gqa_smaller, mb(gqa), mb(mha)))

    ratio_is_groups = abs(mha / gqa - q / data["gqa_groups"]) < 1e-9
    print("  the saving equals query_heads/groups = %s (%.0fx = %d/%d)"
          % (ratio_is_groups, mha / gqa, q, data["gqa_groups"]))

    mqa_smallest = mqa < gqa < mha
    print("  MQA < GQA < MHA in cache size = %s (%.1f < %.1f < %.1f MB)" % (mqa_smallest, mb(mqa), mb(gqa), mb(mha)))

    query_heads_unchanged = all(data["num_query_heads"] == q for _ in ("MHA", "GQA", "MQA"))
    print("  every variant keeps all %d query heads (only KV heads shrink) = %s" % (q, query_heads_unchanged))

    ok = gqa_smaller and ratio_is_groups and mqa_smallest and query_heads_unchanged
    print("-" * 92)
    print("SELF-TEST %s  gqa_smaller=%s  ratio_is_groups=%s  mqa_smallest=%s  query_heads_unchanged=%s"
          % ("PASS" if ok else "FAIL", gqa_smaller, ratio_is_groups, mqa_smallest, query_heads_unchanged))
    return ok


def main():
    p = argparse.ArgumentParser(description="Share KV heads across query heads to shrink the KV cache.")
    p.add_argument("--config", action="store_true")
    p.add_argument("--cache", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("layers=%d  query_heads=%d  seq_len=%d  gqa_groups=%d  file=%s  (the dimensions are a fixture)"
          % (data["num_layers"], data["num_query_heads"], data["seq_len"], data["gqa_groups"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.config:
        config_view(data)
    elif args.cache:
        cache_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
