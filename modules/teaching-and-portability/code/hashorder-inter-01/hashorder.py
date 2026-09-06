"""Sort a set before you serialize it, or the same data writes different bytes -- and a different hash -- on every run.

Python randomizes the hash of str objects once per process, seeded from the environment (PYTHONHASHSEED). A set
stores its members in slots chosen by their hash, and it iterates in slot order -- so the ITERATION ORDER of a set
of strings is different every time the interpreter starts. The set contains the same members; only the order they
come out in changes. That is invisible until you serialize the set: join it into a manifest line, write it to a
cache key, or hash it into a config digest, and the bytes you produce depend on a per-process random seed you never
chose. The same tags on the same code produce one string today and a different string tomorrow, one digest on your
machine and another on your colleague's -- and a cache keyed on that digest misses, a "did the config change?"
check fires on no change, and a golden-file test fails for nobody's reason.

The fix is one word: sort. `sorted(s)` returns the members in a total order that does not depend on hashing, so the
serialization is identical across processes, machines, and Python versions. Sets and dict-key iteration are for
membership and lookup, never for output; the moment a collection crosses into something you write, hash, compare,
or commit, impose an order. Sorting is the cheap, universal fix; the deeper rule is that reproducible output must
never depend on a container's internal iteration order.

To make the non-determinism deterministic to demonstrate, this drives two child interpreters with fixed but
DIFFERENT PYTHONHASHSEED values and captures how each iterates the same set. Across the two seeds the raw set order
differs and its digest differs; the sorted order and its digest are identical. This computes both.

  --order    the set's iteration order under two hash seeds (differs) vs the sorted order (identical)
  --digest   the sha256 of the joined set order per seed (two digests) vs the joined sorted order (one digest)
  --check    raw set order and its digest differ across seeds; sorted order and its digest are identical
  --worker   internal: print this process's set order for one seed (used by the two subcommands above)

The tags and the two seeds are the fixture; the ordering and hashing are real, run in child processes. Stdlib only.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "hashorder.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def digest(items):
    """A sha256 over the joined items -- the kind of digest a cache key or config hash would use."""
    return hashlib.sha256("|".join(items).encode("utf-8")).hexdigest()


def set_order(tags):
    """The order a fresh set iterates these strings -- decided by their per-process randomized hashes."""
    return list(set(tags))


def run_worker(seed, tags):
    """Run --worker in a child interpreter pinned to `seed`, and return that process's set iteration order."""
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    out = subprocess.run([sys.executable, str(Path(__file__)), "--worker"],
                         capture_output=True, text=True, env=env, check=True)
    return out.stdout.strip().split(",")


# ----------------------------------------------------------------- printing

def order_view(data):
    tags, seeds = data["tags"], data["seeds"]
    print("ORDER — the same set iterates differently under different hash seeds")
    print("-" * 78)
    orders = [run_worker(s, tags) for s in seeds]
    for s, o in zip(seeds, orders):
        print("  set order  (PYTHONHASHSEED=%d):  %s" % (s, ", ".join(o)))
    print("  differ across the two seeds?  %s" % (orders[0] != orders[1]))
    print("")
    print("  sorted     (any seed):           %s" % ", ".join(sorted(tags)))
    print("  identical across every seed?     %s" % all(sorted(run_worker(s, tags)) == sorted(tags) for s in seeds))
    print("-" * 78)
    print("  the set holds the same members every time; only the order it hands them back changes.")


def digest_view(data):
    tags, seeds = data["tags"], data["seeds"]
    print("DIGEST — serialize the set directly and its hash is a coin flip; sort first and it is fixed")
    print("-" * 78)
    raw = [digest(run_worker(s, tags)) for s in seeds]
    for s, d in zip(seeds, raw):
        print("  sha256(join(set order))  seed=%d:  %s" % (s, d))
    print("  the two digests differ?  %s" % (raw[0] != raw[1]))
    print("")
    srt = [digest(sorted(run_worker(s, tags))) for s in seeds]
    print("  sha256(join(sorted))     any seed:  %s" % srt[0])
    print("  identical across seeds?  %s" % (len(set(srt)) == 1))
    print("-" * 78)
    print("  a cache key or config hash built on the raw set order misses on the next run for no real change.")


def check(data):
    print("SELF-TEST — raw set order and its digest differ across seeds; sorted order and its digest are identical")
    print("-" * 104)
    tags, seeds = data["tags"], data["seeds"]
    orders = [run_worker(s, tags) for s in seeds]

    order_differs = orders[0] != orders[1]
    print("  the raw set iteration order differs across the two seeds = %s" % order_differs)

    same_members = set(orders[0]) == set(orders[1]) == set(tags)
    print("  yet both hold exactly the same members = %s" % same_members)

    digest_differs = digest(orders[0]) != digest(orders[1])
    print("  so the digest of the joined set order differs across seeds = %s" % digest_differs)

    sorted_identical = sorted(orders[0]) == sorted(orders[1]) == sorted(tags)
    print("  sorting recovers one identical order for every seed = %s" % sorted_identical)

    sorted_digest_stable = len({digest(sorted(o)) for o in orders}) == 1
    print("  and the digest of the sorted order is stable across seeds = %s" % sorted_digest_stable)

    ok = order_differs and same_members and digest_differs and sorted_identical and sorted_digest_stable
    print("-" * 104)
    print("SELF-TEST %s  order_differs=%s  same_members=%s  digest_differs=%s  sorted_identical=%s  sorted_digest_stable=%s"
          % ("PASS" if ok else "FAIL", order_differs, same_members, digest_differs, sorted_identical, sorted_digest_stable))
    return ok


def main():
    p = argparse.ArgumentParser(description="Set/dict-key iteration order depends on per-process hash randomization, so serializing a set directly is non-reproducible; sort before you serialize.")
    p.add_argument("--order", action="store_true")
    p.add_argument("--digest", action="store_true")
    p.add_argument("--check", action="store_true")
    p.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = p.parse_args()

    data = load()

    if args.worker:
        # Print this process's set iteration order; the parent pins PYTHONHASHSEED before launching us.
        print(",".join(set_order(data["tags"])))
        return 0

    print("tags=%d  seeds=%s  file=%s  (the tags and seeds are a fixture; ordering runs in child processes)"
          % (len(data["tags"]), data["seeds"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.order:
        order_view(data)
    elif args.digest:
        digest_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
