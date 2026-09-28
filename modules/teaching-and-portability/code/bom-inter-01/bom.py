"""Strip the UTF-8 BOM when reading, or an invisible byte corrupts the first field and a lookup by its name silently fails.

Some programs -- Excel exporting a CSV, Notepad, many Windows editors -- write a UTF-8 file with a BYTE-ORDER MARK at the
very front: the three bytes EF BB BF, which decode to the Unicode character U+FEFF. For UTF-8 the BOM is pointless (UTF-8
has no byte order to mark) but harmless as a signature that the file is Unicode, so these editors add it. It becomes a bug
the moment another program reads the file with a plain 'utf-8' decoder, because that decoder faithfully includes the BOM
in the resulting string. The BOM lands on the very first character of the file, so the first field -- a CSV's first column
header, a JSON's leading whitespace, the first line of a config -- comes back with an invisible U+FEFF glued to its front.

The reason this is so pernicious is that the BOM is INVISIBLE when printed. A header that is actually '﻿name' displays
as 'name', looks exactly like 'name' in a log or a debugger, and compares UNEQUAL to the string 'name'. So a program that
reads the columns and then looks up the row by data['name'] gets a KeyError -- or worse, silently finds nothing -- for a
column that is right there on screen. The developer stares at a file whose first column is plainly 'name', a lookup for
'name' that fails, and no visible reason why, because the one byte that differs cannot be seen. And it only ever affects
the FIRST field, so most of the data is fine and only the first column is mysteriously unreachable, which makes it look
like a logic bug rather than an encoding one.

The fix is to decode with 'utf-8-sig' instead of 'utf-8' when reading files that might carry a BOM: the -sig codec
recognizes and strips a leading BOM (and reads BOM-less files identically), so the first field comes back clean. Writing,
by contrast, should NOT add a BOM (use plain 'utf-8'), so you do not inflict the same trap on the next reader.

The rule: read text that may have been saved by a BOM-adding editor (Excel, Windows tools) with 'utf-8-sig', not plain
'utf-8', because a UTF-8 BOM decodes to an invisible U+FEFF glued to the first field, so a lookup by that field's clean name
silently fails even though the field looks correct -- and write with plain 'utf-8' so you do not add a BOM yourself.

On this fixture a CSV 'name,age,city / Alice,30,NYC' is saved with a BOM. Read with plain utf-8, the first header is
'﻿name', so a lookup for 'name' fails. Read with utf-8-sig, the BOM is stripped, the first header is 'name', and the
lookup returns 'Alice'. This computes both.

  --bytes    the file's leading bytes (the BOM), and how plain-utf8 vs utf-8-sig decode the first header
  --lookup   parse the CSV both ways and look up the row by 'name': plain fails, utf-8-sig returns 'Alice'
  --check    the BOM corrupts only the first field under plain utf-8 and the lookup fails; utf-8-sig strips it and it works

columns, row, and lookup_key are the fixture; the BOM, decoded headers, and every lookup are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "bom.json"

BOM = "﻿"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def saved_file_bytes(data):
    """The bytes a BOM-adding editor would write for this CSV: content encoded with utf-8-sig (which prepends the BOM)."""
    content = ",".join(data["columns"]) + "\n" + ",".join(data["row"])
    return content.encode("utf-8-sig")


def headers_plain(raw):
    """Decode with plain utf-8 (the BOM survives) and split the first line into headers."""
    text = raw.decode("utf-8")
    return text.splitlines()[0].split(",")


def headers_sig(raw):
    """Decode with utf-8-sig (the BOM is stripped) and split the first line into headers."""
    text = raw.decode("utf-8-sig")
    return text.splitlines()[0].split(",")


def row_dict(headers, row):
    return dict(zip(headers, row))


# ----------------------------------------------------------------- printing

def bytes_view(data):
    raw = saved_file_bytes(data)
    print("BYTES — the saved file starts with the UTF-8 BOM (EF BB BF)")
    print("-" * 60)
    print("  first 6 bytes: %s" % " ".join("%02X" % b for b in raw[:6]))
    print("  plain utf-8   first header = %r" % headers_plain(raw)[0])
    print("  utf-8-sig     first header = %r" % headers_sig(raw)[0])
    print("-" * 60)
    print("  both print as 'name', but the plain-utf8 one carries an invisible U+FEFF in front.")


def lookup_view(data):
    raw = saved_file_bytes(data)
    key = data["lookup_key"]
    plain = row_dict(headers_plain(raw), data["row"])
    sig = row_dict(headers_sig(raw), data["row"])
    print("LOOKUP — parse the CSV and look up the row by %r" % key)
    print("-" * 62)
    print("  plain utf-8  headers = %s" % headers_plain(raw))
    print("    row[%r] = %r" % (key, plain.get(key, "<KeyError: not found>")))
    print("  utf-8-sig    headers = %s" % headers_sig(raw))
    print("    row[%r] = %r" % (key, sig.get(key, "<KeyError: not found>")))
    print("-" * 62)
    print("  the column is plainly 'name' on screen, yet the plain-utf8 lookup finds nothing.")


def check(data):
    print("SELF-TEST — the BOM corrupts only the first field under plain utf-8 and the lookup fails; utf-8-sig strips it and it works")
    print("-" * 124)
    raw = saved_file_bytes(data)
    key = data["lookup_key"]
    hp = headers_plain(raw)
    hs = headers_sig(raw)
    plain = row_dict(hp, data["row"])
    sig = row_dict(hs, data["row"])

    bom_present = raw[:3] == b"\xef\xbb\xbf"
    print("  the saved file begins with the UTF-8 BOM = %s (%s)" % (bom_present, " ".join("%02X" % b for b in raw[:3])))

    plain_corrupts_first = hp[0] == BOM + key and hp[0] != key
    print("  plain utf-8 glues the BOM to the first header = %s (%r != %r)" % (plain_corrupts_first, hp[0], key))

    plain_lookup_fails = key not in plain
    print("  the lookup by the clean key fails under plain utf-8 = %s" % plain_lookup_fails)

    sig_lookup_works = sig.get(key) == data["row"][0]
    print("  utf-8-sig strips the BOM and the lookup returns the value = %s (%r)" % (sig_lookup_works, sig.get(key)))

    only_first_affected = hp[1:] == hs[1:]
    print("  only the first field is affected; the rest are identical = %s (%s == %s)" % (only_first_affected, hp[1:], hs[1:]))

    ok = bom_present and plain_corrupts_first and plain_lookup_fails and sig_lookup_works and only_first_affected
    print("-" * 124)
    print("SELF-TEST %s  bom_present=%s  plain_corrupts_first=%s  plain_lookup_fails=%s  sig_lookup_works=%s  only_first_affected=%s"
          % ("PASS" if ok else "FAIL", bom_present, plain_corrupts_first, plain_lookup_fails, sig_lookup_works, only_first_affected))
    return ok


def main():
    p = argparse.ArgumentParser(description="UTF-8 BOM: read text that may have been saved by a BOM-adding editor (Excel, Windows tools) with 'utf-8-sig', not plain 'utf-8', because a UTF-8 BOM decodes to an invisible U+FEFF glued to the first field, so a lookup by that field's clean name silently fails even though the field looks correct -- and write with plain 'utf-8' so you do not add a BOM yourself.")
    p.add_argument("--bytes", action="store_true")
    p.add_argument("--lookup", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("columns=%s  row=%s  lookup_key=%r  file=%s  (the CSV content is a fixture)"
          % (data["columns"], data["row"], data["lookup_key"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.bytes:
        bytes_view(data)
    elif args.lookup:
        lookup_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
