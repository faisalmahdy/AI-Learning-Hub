"""Upsert a changed document by id -- delete its old vector, write the new one -- do not merely append the new embedding, or the index holds two vectors for one document and a query can retrieve the stale one and serve the old content.

A vector index is a set of (id, vector) entries. When a document's text changes, its embedding changes, so the correct update is to replace the entry for that id. The trap is that a naive indexing pipeline appends: it computes the new embedding and inserts it, and unless something explicitly deletes the prior vector for that id, the index now holds two vectors for one document -- the stale one (the old text's embedding) and the fresh one (the new text's embedding).

Both are searchable, and that is the bug. A query can retrieve the stale vector and serve the document's old, outdated content -- and because the old text may match the query better than the edited text does, the stale vector can outrank the fresh one and take the top slot, so the system confidently returns the pre-edit answer. The document also shows up twice in the results, spending two slots on one source.

This is a different failure from index freshness. Freshness is about a new document that is not yet indexed, so it is invisible; here the new content is indexed correctly, but the old content was never removed, so the stale copy lingers and competes. The fix is upsert-by-id: delete any existing vector for the id, then insert the new one, so the index holds exactly one vector per document -- the current one.

On this fixture document d1 was edited; its old embedding matches the query slightly better than its new one. The append index keeps both d1 vectors and its search returns the stale one at the top (old content); the upsert index keeps only the new d1 vector and returns the fresh content. This computes both.

  --index    the entries in the append index (two d1 vectors) vs the upsert index (one)
  --search   the ranked results of each index, and which content d1 returns
  --check    the append index duplicates d1 and returns its stale content; the upsert index holds one d1 and returns the fresh content

query, the edited document's old and new vectors, and the other docs are the fixture; the index contents, rankings, and returned content are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "upsert.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def cosine(a, b):
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def append_index(data):
    """The naive update: the old d1 vector is still here, and the new one was appended -- two entries for d1."""
    entries = [(data["updated_doc"], "stale", data["old_vector"]),
               (data["updated_doc"], "fresh", data["new_vector"])]
    for cid, vec in data["other_docs"].items():
        entries.append((cid, "-", vec))
    return entries


def upsert_index(data):
    """The correct update: delete d1's old vector, then write the new one -- one entry for d1."""
    entries = [(data["updated_doc"], "fresh", data["new_vector"])]
    for cid, vec in data["other_docs"].items():
        entries.append((cid, "-", vec))
    return entries


def rank(query, entries):
    """Rank index entries by cosine to the query."""
    scored = [(cid, ver, cosine(query, vec)) for cid, ver, vec in entries]
    return sorted(scored, key=lambda t: t[2], reverse=True)


# ----------------------------------------------------------------- printing

def index_view(data):
    ai, ui = append_index(data), upsert_index(data)
    doc = data["updated_doc"]
    print("INDEX — entries for the edited document %s after the update" % doc)
    print("-" * 56)
    print("  append index : %s" % [(cid, ver) for cid, ver, _ in ai])
    print("  upsert index : %s" % [(cid, ver) for cid, ver, _ in ui])
    print("-" * 56)
    print("  append leaves two %s vectors (stale + fresh); upsert leaves one" % doc)


def search_view(data):
    q = data["query"]
    doc = data["updated_doc"]
    at = rank(q, append_index(data))
    ut = rank(q, upsert_index(data))
    print("SEARCH — ranked results for the query")
    print("-" * 56)
    print("  append index:")
    for cid, ver, s in at:
        print("      %-4s %-6s cos %.4f" % (cid, ver, s))
    print("  append top-1 = %s (%s)  ->  returns the %s content" % (at[0][0], at[0][1], at[0][1]))
    print("  upsert index:")
    for cid, ver, s in ut:
        print("      %-4s %-6s cos %.4f" % (cid, ver, s))
    print("  upsert top-1 = %s (%s)  ->  returns the %s content" % (ut[0][0], ut[0][1], ut[0][1]))
    print("-" * 56)
    print("  the append index serves the pre-edit content; the upsert index serves the current content")


def check(data):
    print("SELF-TEST — the append index duplicates the doc and returns its stale content; the upsert index holds one and returns the fresh content")
    print("-" * 112)
    q, doc = data["query"], data["updated_doc"]
    ai, ui = append_index(data), upsert_index(data)
    at, ut = rank(q, ai), rank(q, ui)

    append_duplicates_doc = sum(1 for cid, _, _ in ai if cid == doc) == 2
    print("  the append index holds two vectors for %s = %s" % (doc, append_duplicates_doc))

    upsert_single_entry = sum(1 for cid, _, _ in ui if cid == doc) == 1
    print("  the upsert index holds exactly one vector for %s = %s" % (doc, upsert_single_entry))

    stale_outranks_fresh = cosine(q, data["old_vector"]) > cosine(q, data["new_vector"])
    print("  the stale vector outscores the fresh one for this query = %s (%.4f > %.4f)"
          % (stale_outranks_fresh, cosine(q, data["old_vector"]), cosine(q, data["new_vector"])))

    append_returns_stale = at[0][0] == doc and at[0][1] == "stale"
    print("  the append search returns the stale content at the top = %s (%s %s)" % (append_returns_stale, at[0][0], at[0][1]))

    upsert_returns_fresh = ut[0][0] == doc and ut[0][1] == "fresh"
    print("  the upsert search returns the fresh content at the top = %s (%s %s)" % (upsert_returns_fresh, ut[0][0], ut[0][1]))

    ok = (append_duplicates_doc and upsert_single_entry and stale_outranks_fresh
          and append_returns_stale and upsert_returns_fresh)
    print("-" * 112)
    print("SELF-TEST %s  append_duplicates_doc=%s  upsert_single_entry=%s  stale_outranks_fresh=%s  append_returns_stale=%s  upsert_returns_fresh=%s"
          % ("PASS" if ok else "FAIL", append_duplicates_doc, upsert_single_entry, stale_outranks_fresh,
             append_returns_stale, upsert_returns_fresh))
    return ok


def main():
    p = argparse.ArgumentParser(description="Upsert by id: when a document changes, delete its old vector and write the new one under the same id, do not merely append the new embedding, or the index holds two vectors for one document and a query can retrieve the stale one and serve the pre-edit content.")
    p.add_argument("--index", action="store_true")
    p.add_argument("--search", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query=%s  updated_doc=%s  file=%s  (these are a fixture)" % (data["query"], data["updated_doc"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.index:
        index_view(data)
    elif args.search:
        search_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
