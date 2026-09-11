"""Label connected blobs with union-find, and choose 4- vs 8-connectivity on purpose -- or you miscount the regions.

After you binarize an image, the next question is almost always how many separate objects the foreground is: how many
cells, how many text glyphs, how many detected regions. That is connected-components labeling -- assign every foreground
pixel a label so that two pixels get the same label exactly when a path of foreground pixels connects them, then count
the distinct labels. Two decisions make it right or wrong. The first is what "connected" means: 4-connectivity joins
pixels sharing an edge (up, down, left, right), while 8-connectivity also joins pixels touching only at a corner. That
is not a detail -- two blobs that kiss at a single diagonal corner are two objects under 4-connectivity and one under 8,
so the same image gives different counts, and which is correct depends entirely on what you are counting.

The second decision is how to resolve label equivalences. Scan the image row by row assigning labels from already-seen
neighbors, and a single component shaped like a U (or reached from two directions) gets two different labels on its two
arms before they meet -- so a naive first pass over-counts. The fix is union-find: give each new foreground pixel a
provisional label, union it with its foreground neighbors' labels, and at the end count the distinct roots. Union-find
merges the arms that turn out to be the same component, so the count is the true number of objects, not the number of
labels the raster pass happened to hand out.

On this fixture a 2x2 block, a lone pixel, and another 2x2 block sit on a diagonal chain. Under 4-connectivity the
diagonal corners do not connect, so there are 3 components; under 8-connectivity the corner-touches chain all three into
1 component. Union-find produces both counts correctly by merging every neighbor relationship in the chosen connectivity.
This computes both.

  --count    the component count under 4-connectivity vs 8-connectivity -- the diagonal chain makes them differ
  --labels   the final label of every foreground pixel under each connectivity -- union-find's merged component ids
  --check    8-connectivity never counts more than 4; the diagonal chain is 3 under 4 and 1 under 8; labels equal roots

The binary image is the fixture; every label and count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "conncomp.json"

NEIGHBORS_4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
NEIGHBORS_8 = NEIGHBORS_4 + [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def find(parent, x):
    """Union-find root of x, with path compression."""
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(parent, a, b):
    """Merge the sets containing a and b."""
    parent[find(parent, a)] = find(parent, b)


def label(image, neighbors):
    """Union-find labeling: union each foreground pixel with its foreground neighbors, return {pixel: component root}."""
    rows, cols = len(image), len(image[0])
    fg = [(r, c) for r in range(rows) for c in range(cols) if image[r][c]]
    parent = {p: p for p in fg}
    for r, c in fg:
        for dr, dc in neighbors:
            nb = (r + dr, c + dc)
            if 0 <= nb[0] < rows and 0 <= nb[1] < cols and image[nb[0]][nb[1]]:
                union(parent, (r, c), nb)
    return {p: find(parent, p) for p in fg}


def count(image, neighbors):
    """The number of connected components = the number of distinct union-find roots."""
    return len(set(label(image, neighbors).values()))


# ----------------------------------------------------------------- printing

def count_view(data):
    img = data["image"]
    print("COUNT — connected components by connectivity")
    print("-" * 46)
    for row in img:
        print("    " + " ".join(str(v) for v in row))
    print("-" * 46)
    print("  4-connectivity (edges only):        %d components" % count(img, NEIGHBORS_4))
    print("  8-connectivity (edges + corners):   %d components" % count(img, NEIGHBORS_8))
    print("-" * 46)
    print("  the diagonal corner-touches merge under 8-connectivity but not under 4.")


def labels_view(data):
    img = data["image"]
    for name, nbrs in (("4-connectivity", NEIGHBORS_4), ("8-connectivity", NEIGHBORS_8)):
        lab = label(img, nbrs)
        ids = {root: i for i, root in enumerate(sorted(set(lab.values())), 1)}  # root -> small id
        print("LABELS — %s" % name)
        print("-" * 46)
        for r in range(len(img)):
            cells = []
            for c in range(len(img[0])):
                cells.append(str(ids[lab[(r, c)]]) if img[r][c] else ".")
            print("    " + " ".join(cells))
        print("    -> %d component(s)" % len(ids))
        print("")


def check(data):
    print("SELF-TEST — 8-connectivity never counts more than 4; the diagonal chain is 3 under 4 and 1 under 8; labels equal roots")
    print("-" * 118)
    img = data["image"]
    c4, c8 = count(img, NEIGHBORS_4), count(img, NEIGHBORS_8)

    four_is_three = c4 == 3
    print("  under 4-connectivity the diagonal chain is 3 separate components = %s (%d)" % (four_is_three, c4))

    eight_is_one = c8 == 1
    print("  under 8-connectivity the corner-touches merge it into 1 = %s (%d)" % (eight_is_one, c8))

    eight_le_four = c8 <= c4
    print("  8-connectivity never counts more components than 4 = %s (%d <= %d)" % (eight_le_four, c8, c4))

    lab8 = label(img, NEIGHBORS_8)
    all_one_root = len(set(lab8.values())) == 1
    print("  under 8-connectivity every foreground pixel shares one root = %s" % all_one_root)

    fg_pixels = sum(sum(row) for row in img)
    labels_cover_fg = len(label(img, NEIGHBORS_4)) == fg_pixels
    print("  every foreground pixel receives a label = %s (%d pixels)" % (labels_cover_fg, fg_pixels))

    ok = four_is_three and eight_is_one and eight_le_four and all_one_root and labels_cover_fg
    print("-" * 118)
    print("SELF-TEST %s  four_is_three=%s  eight_is_one=%s  eight_le_four=%s  all_one_root=%s  labels_cover_fg=%s"
          % ("PASS" if ok else "FAIL", four_is_three, eight_is_one, eight_le_four, all_one_root, labels_cover_fg))
    return ok


def main():
    p = argparse.ArgumentParser(description="Connected-components labeling with union-find: count and label foreground blobs, choosing 4- vs 8-connectivity deliberately and merging equivalent labels a naive single pass would split.")
    p.add_argument("--count", action="store_true")
    p.add_argument("--labels", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("image=%dx%d  file=%s  (the binary image is a fixture)" % (len(data["image"]), len(data["image"][0]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.count:
        count_view(data)
    elif args.labels:
        labels_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
