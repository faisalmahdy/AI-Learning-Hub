"""Count pairs, not items, or you badly overestimate how many it takes before two things collide.

Ask how many people you need in a room before two of them probably share a birthday, and intuition says a lot --
maybe half of 365, around 180. The real answer is 23. It feels wrong because you are thinking of it as people
versus days: each new person is one more chance to match YOUR birthday, and one person against 365 days is a long
shot. But a shared birthday is any pair matching, not a match to you, and n people form n*(n-1)/2 PAIRS. Pairs grow
quadratically, so 23 people already make 253 pairs, and 253 chances against 365 days is not a long shot at all.
The quantity that drives a collision is the number of pairs, not the number of items, and pairs explode long
before items do.

This is not a party trick; it is the governing law of collisions everywhere. Random identifiers, hash values,
cryptographic nonces, sharded keys -- anything drawn from a space of d slots collides with even odds after only
about the SQUARE ROOT of d draws, not d. The count crosses 50% near sqrt(d) because that is where the number of
pairs, about half the square of the count, reaches the number of slots. So a 32-bit random ID has about four
billion slots but starts colliding around sixty-five thousand IDs; a hash needs twice the bits you would naively
budget to resist a birthday collision. Estimate collision risk by items-versus-slots and you will be safe by a
factor of the square root of the slot count -- which is to say, catastrophically wrong.

On this fixture 23 people in 365 days give a 50.7% chance of a shared birthday -- over half -- while 22 give
47.6%, so 23 is exactly where it crosses. That threshold, 23, is close to sqrt(365) = 19, not to 365. Applying
the same math, 32-bit IDs reach an even chance of collision near 2^16 = 65 thousand. This computes both.

  --curve      the collision probability for a range of group sizes, and where it crosses 50%
  --collisions the 50% threshold vs the slot count, for birthdays and for 32-bit IDs, showing the sqrt rule
  --check      23 people cross 50% (far below 365); the threshold scales like sqrt(slots), driven by pairs

The days, group size, and id size are the fixture; every probability is computed exactly. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "birthday.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def collision_prob(n, slots):
    """P(at least one collision among n items in `slots` slots) = 1 - P(all distinct)."""
    p_distinct = 1.0
    for i in range(n):
        p_distinct *= (slots - i) / slots
    return 1 - p_distinct


def pairs(n):
    """The number of distinct pairs among n items."""
    return n * (n - 1) // 2


def threshold(slots, target=0.5):
    """The smallest n whose collision probability reaches `target`."""
    n = 1
    while collision_prob(n, slots) < target:
        n += 1
    return n


# ----------------------------------------------------------------- printing

def curve_view(data):
    d = data["days"]
    print("CURVE — P(shared birthday) by group size (%d days)" % d)
    print("-" * 58)
    print("  people   pairs   P(collision)")
    for n in (5, 10, 19, 22, 23, 30, 40):
        mark = "  <- crosses 50%" if n == threshold(d) else ""
        print("  %-6d   %-5d   %.4f%s" % (n, pairs(n), collision_prob(n, d), mark))
    print("-" * 58)
    print("  the pairs column, not the people column, is what races the %d days." % d)


def collisions_view(data):
    d, bits = data["days"], data["id_bits"]
    slots_id = 2 ** bits
    print("COLLISIONS — the 50% threshold sits near sqrt(slots), not slots")
    print("-" * 62)
    print("  birthdays:   %d slots   50%% at %d people   (sqrt = %.0f)" % (d, threshold(d), d ** 0.5))
    print("  %d-bit ids:  %d slots   50%% near %d ids   (sqrt = %d = 2^%d)" % (bits, slots_id, threshold_id(slots_id), int(slots_id ** 0.5), bits // 2))
    print("-" * 62)
    print("  a collision gets likely after ~sqrt(slots) draws -- far fewer than the slot count.")


def threshold_id(slots):
    """Approximate 50% collision count for a huge slot space (the birthday bound ~1.177*sqrt(slots))."""
    import math
    return int(1.1774 * math.sqrt(slots))


def check(data):
    print("SELF-TEST — 23 people cross 50% (far below 365); the threshold scales like sqrt(slots), driven by pairs")
    print("-" * 108)
    d, people, bits = data["days"], data["people"], data["id_bits"]

    crosses_at_23 = collision_prob(people, d) >= 0.5 and collision_prob(people - 1, d) < 0.5
    print("  %d people cross 50%% while %d do not = %s (%.4f vs %.4f)" % (people, people - 1, crosses_at_23, collision_prob(people, d), collision_prob(people - 1, d)))

    far_below_days = people < d / 4
    print("  the threshold is far below the number of days = %s (%d << %d)" % (far_below_days, people, d))

    near_sqrt = abs(threshold(d) - d ** 0.5) < 0.4 * (d ** 0.5)
    print("  the 50%% threshold is near sqrt(days) = %s (%d vs %.0f)" % (near_sqrt, threshold(d), d ** 0.5))

    driven_by_pairs = pairs(people) > d / 2
    print("  the pair count already rivals the slot count = %s (%d pairs vs %d days)" % (driven_by_pairs, pairs(people), d))

    id_collision_far_below_slots = threshold_id(2 ** bits) < 2 ** bits / 1000
    print("  %d-bit ids collide far below their slot count = %s (~%d vs %d)" % (bits, id_collision_far_below_slots, threshold_id(2 ** bits), 2 ** bits))

    ok = crosses_at_23 and far_below_days and near_sqrt and driven_by_pairs and id_collision_far_below_slots
    print("-" * 108)
    print("SELF-TEST %s  crosses_at_23=%s  far_below_days=%s  near_sqrt=%s  driven_by_pairs=%s  id_collision_far_below_slots=%s"
          % ("PASS" if ok else "FAIL", crosses_at_23, far_below_days, near_sqrt, driven_by_pairs, id_collision_far_below_slots))
    return ok


def main():
    p = argparse.ArgumentParser(description="The birthday problem: collisions become likely at about sqrt(slots) items, because pairs (not items) race the slots.")
    p.add_argument("--curve", action="store_true")
    p.add_argument("--collisions", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("days=%d  people=%d  id_bits=%d  file=%s  (the parameters are a fixture)"
          % (data["days"], data["people"], data["id_bits"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.curve:
        curve_view(data)
    elif args.collisions:
        collisions_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
