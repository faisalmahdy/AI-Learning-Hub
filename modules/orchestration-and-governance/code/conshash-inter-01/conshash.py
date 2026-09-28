"""Place keys on a ring, not with hash % N -- adding one node under modulo hashing moves almost every key at once.

Sharding keys across N nodes -- cache servers, database partitions -- needs a rule mapping each key to a node. The obvious
rule is modulo hashing: node = hash(key) % N. It spreads keys evenly and is one line, and it has a catastrophic property:
the answer depends on N, so the moment N changes -- you add a node to scale out, or one dies -- almost every key's hash %
N lands on a different node than before. For a cache that means a near-total miss storm (every key must be refetched from
the origin at once); for a stateful store it means moving almost all the data across the network to rebalance. A single
node joining a 4-node cluster can invalidate roughly 80% of the placements, so the cheap rule makes scaling the cluster --
the exact operation you add nodes to perform -- a self-inflicted outage.

Consistent hashing fixes the coupling between the placement and N. Put both the nodes and the keys on a ring (a circular
hash space); each key is owned by the first node clockwise from it. Now a node owns a contiguous arc of the ring -- the
span from the previous node up to itself -- and adding a node only splits ONE arc: the new node inserts at its position
and takes over the keys between it and the previous node, stealing them from the single node that used to own that arc.
Every other key is untouched, because every other arc is unchanged. So adding one node to N moves only about K/N keys (the
new node's fair share), and each moved key goes to the new node, never bouncing between two existing nodes. Removing a
node is the mirror image: only its arc's keys move, to the next node clockwise.

On this fixture there are four nodes on a 0..99 ring and ten keys. Adding a fifth node between two existing ones should
disturb as little as possible. Under modulo hashing, going from N=4 to N=5 moves 8 of the 10 keys (80%). Under consistent
hashing, adding the node at ring position 72 moves only the 2 keys sitting in the arc it steals (20%), both to the new
node, and no key moves between two old nodes. This computes both.

  --remap    keys moved when a node is added: modulo hashing (8 of 10) vs the ring (2 of 10), and where the moved keys go
  --ring     each node's arc on the ring, the keys it owns before and after adding the new node, and the single arc that splits
  --check    modulo hashing remaps most keys; the ring remaps few, all to the new node, with no moves between two old nodes

The ring positions and hashes are the fixture; every assignment and move count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "conshash.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mod_assign(keys, node_names):
    """Modulo hashing: key -> node index hash % N, mapped to a node name by that index."""
    n = len(node_names)
    return {k["id"]: node_names[k["hash"] % n] for k in keys}


def ring_assign(keys, node_positions):
    """Consistent hashing: each key goes to the first node clockwise on the ring (wrapping past the top)."""
    ring = sorted((pos, name) for name, pos in node_positions.items())
    out = {}
    for k in keys:
        out[k["id"]] = next((name for pos, name in ring if pos >= k["pos"]), ring[0][1])
    return out


def moved(before, after):
    """Keys whose owning node changed between two assignments."""
    return [kid for kid in before if before[kid] != after[kid]]


# ----------------------------------------------------------------- printing

def remap_view(data):
    keys = data["keys"]
    nodes4 = data["nodes"]
    nodes5 = dict(nodes4); nodes5.update(data["new_node"])
    names4 = sorted(nodes4); names5 = sorted(nodes5)
    new_name = next(iter(data["new_node"]))
    print("REMAP — keys moved when adding a node (%d keys, %d -> %d nodes)" % (len(keys), len(nodes4), len(nodes5)))
    print("-" * 62)
    mod_moved = moved(mod_assign(keys, names4), mod_assign(keys, names5))
    print("  modulo hashing (hash %% N): %d of %d keys move  (%.0f%%)" % (len(mod_moved), len(keys), 100 * len(mod_moved) / len(keys)))
    ring_before = ring_assign(keys, nodes4)
    ring_after = ring_assign(keys, nodes5)
    ring_moved = moved(ring_before, ring_after)
    print("  consistent hashing (ring): %d of %d keys move  (%.0f%%)  -> %s" % (len(ring_moved), len(keys), 100 * len(ring_moved) / len(keys), ring_moved))
    print("-" * 62)
    print("  every moved key goes to the new node %s; the other %d keys never move." % (new_name, len(keys) - len(ring_moved)))


def ring_view(data):
    keys = data["keys"]
    nodes4 = data["nodes"]
    nodes5 = dict(nodes4); nodes5.update(data["new_node"])
    before = ring_assign(keys, nodes4)
    after = ring_assign(keys, nodes5)
    print("RING — node arcs and key ownership before/after adding %s@%d" % (next(iter(data["new_node"])), next(iter(data["new_node"].values()))))
    print("-" * 66)
    print("  node positions (before): %s" % dict(sorted(nodes4.items(), key=lambda kv: kv[1])))
    for k in sorted(keys, key=lambda k: k["pos"]):
        mark = "  <- moved to %s" % after[k["id"]] if before[k["id"]] != after[k["id"]] else ""
        print("  key %-3s @pos %-3d  owner %s -> %s%s" % (k["id"], k["pos"], before[k["id"]], after[k["id"]], mark))
    print("-" * 66)
    print("  only the arc just before %s changed hands; every other arc is identical." % next(iter(data["new_node"])))


def check(data):
    print("SELF-TEST — modulo hashing remaps most keys; the ring remaps few, all to the new node, with no moves between two old nodes")
    print("-" * 124)
    keys = data["keys"]
    nodes4 = data["nodes"]
    nodes5 = dict(nodes4); nodes5.update(data["new_node"])
    names4 = sorted(nodes4); names5 = sorted(nodes5)
    new_name = next(iter(data["new_node"]))

    mod_moved = moved(mod_assign(keys, names4), mod_assign(keys, names5))
    mod_remaps_most = len(mod_moved) >= 0.7 * len(keys)
    print("  modulo hashing moves most keys on one node add = %s (%d of %d)" % (mod_remaps_most, len(mod_moved), len(keys)))

    before = ring_assign(keys, nodes4)
    after = ring_assign(keys, nodes5)
    ring_moved = moved(before, after)
    ring_remaps_few = len(ring_moved) <= 0.3 * len(keys)
    print("  consistent hashing moves few keys = %s (%d of %d)" % (ring_remaps_few, len(ring_moved), len(keys)))

    ring_fewer = len(ring_moved) < len(mod_moved)
    print("  the ring moves strictly fewer keys than modulo = %s (%d < %d)" % (ring_fewer, len(ring_moved), len(mod_moved)))

    all_to_new = all(after[k] == new_name for k in ring_moved)
    print("  every moved key goes to the new node = %s (%s)" % (all_to_new, ring_moved))

    no_old_to_old = all(before[kid] == after[kid] or after[kid] == new_name for kid in before)
    print("  no key moves between two existing nodes = %s" % no_old_to_old)

    ok = mod_remaps_most and ring_remaps_few and ring_fewer and all_to_new and no_old_to_old
    print("-" * 124)
    print("SELF-TEST %s  mod_remaps_most=%s  ring_remaps_few=%s  ring_fewer=%s  all_to_new=%s  no_old_to_old=%s"
          % ("PASS" if ok else "FAIL", mod_remaps_most, ring_remaps_few, ring_fewer, all_to_new, no_old_to_old))
    return ok


def main():
    p = argparse.ArgumentParser(description="Consistent hashing: modulo hashing (hash % N) couples key placement to N, so adding or removing a node remaps almost every key (a cache-miss storm or mass data move); a hash ring makes each node own a contiguous arc, so adding a node moves only the keys in the one arc it splits (~K/N), all to the new node, leaving every other key in place.")
    p.add_argument("--remap", action="store_true")
    p.add_argument("--ring", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("nodes=%s  new_node=%s  keys=%d  file=%s  (the ring positions and hashes are a fixture)"
          % (data["nodes"], data["new_node"], len(data["keys"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.remap:
        remap_view(data)
    elif args.ring:
        ring_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
