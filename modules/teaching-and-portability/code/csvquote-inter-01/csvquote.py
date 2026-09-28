"""Write CSV with a real CSV writer that quotes special fields -- joining fields with commas and rows with newlines corrupts any field that itself contains a comma or a newline, so the row gains a phantom column or splits in two.

CSV looks like the one file format you can write by hand: commas between the fields, a newline between the rows. And it works, right up until a field contains one of the two characters that carry structural meaning -- a comma or a newline. Real data is full of them: an address like 'Paris, France', a free-text note that wraps onto a second line. The naive writer emits those characters raw, and the moment it does, the reader downstream can no longer tell a field's own comma from a field separator, or a field's own newline from a row separator.

The corruption is silent because the output is still perfectly valid-looking text. A field containing a comma splits into two fields when read back, so the row that should have three columns now has four -- a phantom column, with every field after it shifted. A field containing a newline looks like the end of the row, so one row is read back as two, one of them a fragment. Nobody sees an error; the data just quietly has the wrong shape.

The fix is to stop treating the delimiters as if fields could never contain them. A CSV library escapes exactly this: any field that holds a delimiter, a quote, or a newline is wrapped in double quotes (and internal quotes are doubled), so the special characters are carried literally inside the quotes and the reader knows the field is not over until the closing quote. Write with the library and read with the library and the round-trip returns exactly the rows you started with, shape intact.

The rule: write and read CSV with a real CSV writer and reader, never by joining on commas and newlines, because a field that contains a delimiter or a newline corrupts the structure -- gaining a phantom column or splitting a row -- while proper quoting carries those characters literally and round-trips exactly.

On this fixture one field is 'Paris, France' (an embedded comma) and one is a two-line note (an embedded newline). The naive writer's output re-parses with the wrong number of columns and the wrong number of rows; the CSV writer's output round-trips to the original rows exactly. This computes both.

  --naive   the naively-joined text and how it re-parses -- with the wrong shape
  --safe    the CSV-writer text and its correct round-trip back to the original rows
  --check   naive join corrupts fields with a comma or newline; a CSV writer quotes them and round-trips

rows is the fixture; the two serializations and their re-parsed shapes are computed. Stdlib only.
"""
import argparse
import csv
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "csvquote.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def naive_write(rows):
    """Join fields with commas and rows with newlines -- no quoting."""
    return "\n".join(",".join(field for field in row) for row in rows)


def naive_parse(text):
    """Split rows on newline and fields on comma -- the mirror of naive_write."""
    return [line.split(",") for line in text.split("\n")]


def csv_write(rows):
    """Write with the csv module, which quotes any field holding a comma, quote, or newline."""
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue()


def csv_parse(text):
    return list(csv.reader(io.StringIO(text)))


# ----------------------------------------------------------------- printing

def naive_view(data):
    rows = data["rows"]
    text = naive_write(rows)
    parsed = naive_parse(text)
    print("NAIVE — join on commas and newlines, then read it back")
    print("-" * 58)
    print("  wrote %d rows; the text has %d physical lines" % (len(rows), text.count("\n") + 1))
    print("  re-parsed into %d rows (should be %d):" % (len(parsed), len(rows)))
    for i, r in enumerate(parsed):
        print("    row %d -> %d fields: %s" % (i, len(r), r))
    print("-" * 58)
    print("  the comma field split a column; the newline field split a row")


def safe_view(data):
    rows = data["rows"]
    text = csv_write(rows)
    parsed = csv_parse(text)
    print("SAFE — write and read with the csv module")
    print("-" * 58)
    print("  serialized (quotes added around the special fields):")
    for line in text.splitlines():
        print("    %s" % line)
    print("  re-parsed into %d rows (should be %d):" % (len(parsed), len(rows)))
    for i, r in enumerate(parsed):
        print("    row %d -> %d fields: %s" % (i, len(r), r))
    print("-" * 58)
    print("  every field is carried literally; the round-trip is exact")


def check(data):
    print("SELF-TEST — naive join corrupts fields with a comma or newline; a CSV writer quotes them and round-trips")
    print("-" * 108)
    rows = data["rows"]

    naive_parsed = naive_parse(naive_write(rows))
    csv_parsed = csv_parse(csv_write(rows))

    naive_wrong_row_count = len(naive_parsed) != len(rows)
    print("  naive: re-parsed row count is wrong = %s (%d vs %d)"
          % (naive_wrong_row_count, len(naive_parsed), len(rows)))

    naive_wrong_field_count = any(len(p) != len(r) for p, r in zip(naive_parsed, rows))
    print("  naive: some re-parsed row has the wrong field count = %s" % naive_wrong_field_count)

    naive_not_roundtrip = naive_parsed != rows
    print("  naive: the round-trip does not equal the original = %s" % naive_not_roundtrip)

    csv_right_row_count = len(csv_parsed) == len(rows)
    print("  csv: re-parsed row count is correct = %s (%d)" % (csv_right_row_count, len(csv_parsed)))

    csv_roundtrips = csv_parsed == rows
    print("  csv: the round-trip equals the original exactly = %s" % csv_roundtrips)

    ok = (naive_wrong_row_count and naive_wrong_field_count and naive_not_roundtrip
          and csv_right_row_count and csv_roundtrips)
    print("-" * 108)
    print("SELF-TEST %s  naive_wrong_row_count=%s  naive_wrong_field_count=%s  naive_not_roundtrip=%s  csv_right_row_count=%s  csv_roundtrips=%s"
          % ("PASS" if ok else "FAIL", naive_wrong_row_count, naive_wrong_field_count,
             naive_not_roundtrip, csv_right_row_count, csv_roundtrips))
    return ok


def main():
    p = argparse.ArgumentParser(description="CSV quoting: write and read CSV with a real CSV writer and reader, never by joining on commas and newlines, because a field that contains a delimiter or a newline corrupts the structure -- gaining a phantom column or splitting a row -- while proper quoting carries those characters literally and round-trips exactly.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--safe", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    rows = data["rows"]
    print("rows=%d  file=%s  (fields include an embedded comma and an embedded newline; the rows are a fixture)"
          % (len(rows), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.naive:
        naive_view(data)
    elif args.safe:
        safe_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
