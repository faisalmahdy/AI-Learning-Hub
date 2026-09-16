"""Count and truncate a string by grapheme clusters -- user-perceived characters -- not by the code points len() returns, because a grapheme can be several code points, so len() overcounts the visible length and slicing by code points can split a grapheme and mangle it.

A grapheme cluster is what a person calls a character: a base letter plus the combining marks that stack on it, or an emoji assembled from several code points joined by zero-width joiners. Python's len() counts code points, not grapheme clusters, so it reports more characters than a person sees for any string with such a cluster. (JavaScript and Java count UTF-16 code units and overcount even further, splitting a single astral code point into two.) None of these is the count a user means by 'how many characters.'

The count being wrong is annoying; truncation being wrong is a bug. When you slice a string to N code points to fit a column, a tweet limit, or a database field, the cut can land in the middle of a grapheme: it drops a combining accent, turning a letter into a different one, or it splits a multi-code-point emoji into a fragment -- a family emoji sliced down to a lone figure, or worse, a dangling joiner. The string looks fine in your test with plain ASCII and corrupts the first real name or emoji it meets.

This is a different problem from Unicode normalization, which a companion module covers. Normalizing to NFC makes two canonically-equivalent spellings equal, and it does collapse some base-plus-mark sequences to a single precomposed code point. But it does not reduce every grapheme to one code point: an emoji joined by zero-width joiners, a skin-tone-modified emoji, and a base letter with no precomposed accented form all stay several code points after NFC. So length and truncation need grapheme awareness that normalization does not give you.

On this fixture the string is 'Hi ' + a family emoji (five code points joined by zero-width joiners that render as one glyph) + '!': nine code points but five perceived characters. Truncating to four characters by code points yields 'Hi ' plus a lone figure -- the family split apart -- while truncating by grapheme clusters keeps the whole family. This computes both.

  --length    the string's code-point length, its grapheme-cluster count, and the clusters themselves
  --truncate  truncate to four perceived characters by code points vs by grapheme clusters
  --check     len() overcounts the visible length and a code-point slice splits the emoji; grapheme truncation keeps it, and NFC does not fix the length

codepoints is the fixture; the string, its lengths, clusters, and truncations are computed. Stdlib only.
"""
import argparse
import json
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "grapheme.json"

ZWJ = chr(0x200D)
VS16 = chr(0xFE0F)


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def text_of(data):
    return "".join(chr(c) for c in data["codepoints"])


def clusters(s):
    """Group code points into grapheme clusters: a base plus following combining marks, zero-width-joined sequences, variation selectors, and skin-tone modifiers (a simplified UAX #29)."""
    out = []
    i, n = 0, len(s)
    while i < n:
        cluster = s[i]
        i += 1
        while i < n:
            ch = s[i]
            if unicodedata.combining(ch) or ch == VS16 or "\U0001F3FB" <= ch <= "\U0001F3FF":
                cluster += ch
                i += 1
            elif ch == ZWJ:
                cluster += ch
                i += 1
                if i < n:            # a zero-width joiner pulls the next code point in too
                    cluster += s[i]
                    i += 1
            else:
                break
        out.append(cluster)
    return out


def naive_truncate(s, n):
    """Slice to n code points -- what s[:n] does, blind to graphemes."""
    return s[:n]


def grapheme_truncate(s, n):
    """Keep the first n grapheme clusters whole."""
    return "".join(clusters(s)[:n])


# ----------------------------------------------------------------- printing

def length_view(data):
    s = text_of(data)
    cl = clusters(s)
    print("LENGTH — code points vs grapheme clusters")
    print("-" * 52)
    print("  string              : %s" % s)
    print("  len() code points   : %d" % len(s))
    print("  grapheme clusters   : %d" % len(cl))
    print("  clusters            : %s" % [c for c in cl])
    print("-" * 52)
    print("  len() reports %d, but a reader sees %d characters" % (len(s), len(cl)))


def truncate_view(data):
    s = text_of(data)
    n = 4
    print("TRUNCATE — cut to %d perceived characters" % n)
    print("-" * 52)
    print("  by code points  s[:%d]        : %r  (%d clusters)" % (n, naive_truncate(s, n), len(clusters(naive_truncate(s, n)))))
    print("  by graphemes    first %d      : %r  (%d clusters)" % (n, grapheme_truncate(s, n), len(clusters(grapheme_truncate(s, n)))))
    print("-" * 52)
    print("  the code-point slice splits the family emoji; the grapheme slice keeps it whole")


def check(data):
    print("SELF-TEST — len() overcounts the visible length and a code-point slice splits the emoji; grapheme truncation keeps it, and NFC does not fix the length")
    print("-" * 112)
    s = text_of(data)
    cl = clusters(s)
    grapheme_len = len(cl)

    codepoints_exceed_graphemes = len(s) > grapheme_len
    print("  len() (code points) exceeds the grapheme count = %s (%d > %d)" % (codepoints_exceed_graphemes, len(s), grapheme_len))

    one_grapheme_many_codepoints = max(len(c) for c in cl) > 1
    print("  one grapheme is several code points = %s (longest cluster is %d code points)" % (one_grapheme_many_codepoints, max(len(c) for c in cl)))

    naive = naive_truncate(s, 4)
    naive_truncate_breaks_grapheme = clusters(naive)[-1] != cl[3]
    print("  the code-point slice splits a grapheme = %s (its 4th char is %r, not the family)" % (naive_truncate_breaks_grapheme, clusters(naive)[-1]))

    gt = grapheme_truncate(s, 4)
    grapheme_truncate_preserves = clusters(gt)[-1] == cl[3] and gt == "".join(cl[:4])
    print("  grapheme truncation keeps the family whole = %s (%r)" % (grapheme_truncate_preserves, gt))

    nfc = unicodedata.normalize("NFC", s)
    nfc_does_not_reduce_length = len(nfc) > grapheme_len
    print("  NFC normalization does not fix the length = %s (NFC is still %d code points)" % (nfc_does_not_reduce_length, len(nfc)))

    ok = (codepoints_exceed_graphemes and one_grapheme_many_codepoints and naive_truncate_breaks_grapheme
          and grapheme_truncate_preserves and nfc_does_not_reduce_length)
    print("-" * 112)
    print("SELF-TEST %s  codepoints_exceed_graphemes=%s  one_grapheme_many_codepoints=%s  naive_truncate_breaks_grapheme=%s  grapheme_truncate_preserves=%s  nfc_does_not_reduce_length=%s"
          % ("PASS" if ok else "FAIL", codepoints_exceed_graphemes, one_grapheme_many_codepoints,
             naive_truncate_breaks_grapheme, grapheme_truncate_preserves, nfc_does_not_reduce_length))
    return ok


def main():
    p = argparse.ArgumentParser(description="Grapheme clusters: count and truncate a string by grapheme clusters (user-perceived characters), not by the code points len() returns, because a grapheme can be several code points, so len() overcounts the visible length and slicing by code points can split a grapheme and mangle it.")
    p.add_argument("--length", action="store_true")
    p.add_argument("--truncate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("codepoints=%s  file=%s  (the code points are a fixture)" % (data["codepoints"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.length:
        length_view(data)
    elif args.truncate:
        truncate_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
