---
id: csvquote-inter-01
title: Write CSV with a real CSV writer, not comma-and-newline joins — a field holding a comma gains a phantom column and one with a newline splits the row
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: CSV looks like the one file format you can safely write by hand — commas between the fields, a newline between the rows — and it works right up until a field itself contains one of the two characters that carry structural meaning, a comma or a newline. Real data is full of them: an address like "Paris, France", a free-text note that wraps onto a second line. A naive writer that does ",".join(fields) then "\n".join(rows) emits those characters raw, and the moment it does, the reader downstream can no longer tell a field's own comma from a separator or a field's own newline from a row boundary. The corruption is silent because the output is still valid-looking text: a field with a comma splits into two fields so the row gains a phantom column with everything after it shifted, and a field with a newline looks like the end of the row so one row is read back as two. The fix is to let a CSV library do it — it wraps any field that holds a delimiter, a quote, or a newline in double quotes (doubling internal quotes), so the special characters are carried literally and the round-trip returns exactly the original rows. On a fixture where one field is "Paris, France" and one is a two-line note, the naive writer re-parses into the wrong number of rows and columns while the CSV writer round-trips exactly.
eli5: Imagine you're writing down a list of people, one per line, with their name, city, and job separated by commas — "Ada, Paris France, engineer". Easy. But then someone lives in "Paris, France" with a comma in it, and now when your friend reads the line back they count four things separated by commas instead of three, and they think the city is just "Paris" and "France" is the job. Worse, if someone's note runs onto a second line, your friend thinks that second line is a whole new person. Nothing looks broken — the page is full of neat commas and lines — but the information is scrambled. The trick real programs use is quotation marks: put quotes around anything that has a comma or a line break inside it, so the reader knows "this whole thing is one item, don't chop it up". Let the proper tool add those quotes for you, and the list survives the trip.
---

## Why this module

CSV is deceptively simple, and the simplicity is a trap. The format's entire structure rests on two characters doing double duty: a comma separates fields, a newline separates rows. That is fine as long as those characters never appear inside a field. But fields are just text, and text contains commas and newlines all the time — a city written "Paris, France", a comment that spans two lines, a quoted phrase. The format has to survive data that contains its own delimiters, and hand-rolled writers do not.

Write a row by joining fields with commas, write the file by joining rows with newlines, and you have thrown away the distinction between a delimiter and a delimiter-shaped character inside a value. When the reader splits that text back apart, it splits on every comma and every newline, including the ones that were part of the data. There is no way for it to know which was which, because the writer erased the difference.

What makes this bug pernicious is that nothing looks wrong. The output is clean, valid-looking text; it opens in a spreadsheet; most rows are fine. Only the rows with a comma or newline in a field are corrupted, and they are corrupted silently — a phantom extra column here, a row split in two there. This module writes a table both ways and re-parses each to show the shape breaking.

**CSV's delimiters are ordinary characters that appear inside real data, so a writer that emits them raw cannot be read back unambiguously — the fix is quoting, and the place quoting lives is the CSV library.**

## Concepts

The core idea is escaping: when a character has structural meaning, a value that contains that character literally must be marked so the parser does not treat it as structure. CSV's escaping rule is quoting — wrap the field in double quotes, and any comma or newline inside the quotes is data, not a delimiter; a literal double quote inside is written as two. This is not optional decoration; it is the mechanism that lets the format carry its own delimiters.

A hand-rolled writer skips escaping entirely, which is why it fails. And the failure is asymmetric in a way that hides it: the writer succeeds — it produces output without error — and only the reader discovers, too late and without an exception, that the shape is wrong. The data has already been written and perhaps distributed before anyone notices the phantom columns.

The two corruptions have different shapes worth naming. An embedded comma is a within-row corruption: the row gains a field, and every column after the offending one is shifted, so a downstream consumer reading "column 3" gets the wrong thing. An embedded newline is a cross-row corruption: one logical row becomes two physical rows, one of them a fragment, changing the row count itself. Both come from the same cause and both are fixed by the same quoting.

<svg role="img" aria-label="Two corruption shapes side by side: an embedded comma adds a column within one row, and an embedded newline splits one row into two rows" viewBox="0 0 440 130">
<text x="110" y="18" fill="var(--ink)" font-size="10" text-anchor="middle">embedded comma</text>
<text x="110" y="32" fill="var(--muted)" font-size="9" text-anchor="middle">within-row: +1 column</text>
<rect x="45" y="42" width="130" height="18" fill="var(--panel)" stroke="var(--line)"/>
<line x1="88" y1="42" x2="88" y2="60" stroke="var(--line)"/>
<line x1="131" y1="42" x2="131" y2="60" stroke="var(--line)"/>
<rect x="45" y="66" width="130" height="18" fill="var(--s2)" stroke="var(--line)"/>
<line x1="77" y1="66" x2="77" y2="84" stroke="var(--line)"/>
<line x1="109" y1="66" x2="109" y2="84" stroke="var(--line)"/>
<line x1="142" y1="66" x2="142" y2="84" stroke="var(--line)"/>
<text x="110" y="104" fill="var(--muted)" font-size="9" text-anchor="middle">fields after it all shift</text>
<text x="330" y="18" fill="var(--ink)" font-size="10" text-anchor="middle">embedded newline</text>
<text x="330" y="32" fill="var(--muted)" font-size="9" text-anchor="middle">cross-row: +1 row</text>
<rect x="270" y="42" width="120" height="18" fill="var(--panel)" stroke="var(--line)"/>
<rect x="270" y="66" width="120" height="18" fill="var(--s1)" stroke="var(--line)"/>
<rect x="270" y="90" width="60" height="18" fill="var(--s1)" stroke="var(--line)"/>
<text x="360" y="104" fill="var(--muted)" font-size="9" text-anchor="middle">one row -&gt; two</text>
</svg>
^ The two failures have different shapes — a comma adds a column within the row, a newline adds a whole row — but one quoting rule fixes both.

**Escaping is the mechanism that lets a format carry its own delimiters; a CSV library implements it and a comma-join does not, which is why the library round-trips and the hand-roll silently changes the table's shape.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/csvquote-inter-01. The fixture is a small table where one field holds an embedded comma and one holds an embedded newline.

```json filename=modules/teaching-and-portability/code/csvquote-inter-01/csvquote.json:3-6 COMPLETE
  "rows": [
    ["name", "city", "role"],
    ["Ada", "Paris, France", "engineer"],
    ["Bo", "Rome", "wri\nter"]
  ]
```

The naive writer joins fields with commas and rows with newlines — no quoting.

```python filename=modules/teaching-and-portability/code/csvquote-inter-01/csvquote.py:34-36 COMPLETE
def naive_write(rows):
    """Join fields with commas and rows with newlines -- no quoting."""
    return "\n".join(",".join(field for field in row) for row in rows)
```

Its mirror-image reader splits rows on newline and fields on comma — exactly undoing the write, if only the data were clean.

```python filename=modules/teaching-and-portability/code/csvquote-inter-01/csvquote.py:39-41 COMPLETE
def naive_parse(text):
    """Split rows on newline and fields on comma -- the mirror of naive_write."""
    return [line.split(",") for line in text.split("\n")]
```

Before running it, predict: the row with "Paris, France" should re-parse into four fields instead of three, and the row with the two-line note should re-parse into two rows. Run `--naive`:

```text filename=csvquote.py --naive
NAIVE — join on commas and newlines, then read it back
----------------------------------------------------------
  wrote 3 rows; the text has 4 physical lines
  re-parsed into 4 rows (should be 3):
    row 0 -> 3 fields: ['name', 'city', 'role']
    row 1 -> 4 fields: ['Ada', 'Paris', ' France', 'engineer']
    row 2 -> 3 fields: ['Bo', 'Rome', 'wri']
    row 3 -> 1 fields: ['ter']
```

Both predictions hold. Row 1's "Paris, France" split into "Paris" and " France", giving four fields and shifting "engineer" into what a reader expects to be a fourth column. Row 2's newline split it into "Bo,Rome,wri" and a fragment "ter", turning three rows into four. The table's shape is wrong in two different ways.

<svg role="img" aria-label="A row with three fields where the middle field Paris comma France splits into two cells, producing four cells and shifting engineer; and a row that splits across a newline into two physical rows" viewBox="0 0 440 170">
<text x="220" y="16" fill="var(--muted)" font-size="10" text-anchor="middle">embedded comma: phantom column</text>
<rect x="30" y="26" width="60" height="22" fill="var(--panel)" stroke="var(--line)"/>
<text x="60" y="41" fill="var(--ink)" font-size="10" text-anchor="middle">Ada</text>
<rect x="90" y="26" width="120" height="22" fill="var(--s2)" stroke="var(--line)"/>
<text x="150" y="41" fill="var(--ink)" font-size="9" text-anchor="middle">Paris, France</text>
<rect x="210" y="26" width="80" height="22" fill="var(--panel)" stroke="var(--line)"/>
<text x="250" y="41" fill="var(--ink)" font-size="10" text-anchor="middle">engineer</text>
<rect x="30" y="60" width="60" height="22" fill="var(--panel)" stroke="var(--line)"/>
<text x="60" y="75" fill="var(--ink)" font-size="9" text-anchor="middle">Ada</text>
<rect x="90" y="60" width="58" height="22" fill="var(--s1)" stroke="var(--line)"/>
<text x="119" y="75" fill="var(--ink)" font-size="9" text-anchor="middle">Paris</text>
<rect x="148" y="60" width="62" height="22" fill="var(--s1)" stroke="var(--line)"/>
<text x="179" y="75" fill="var(--ink)" font-size="9" text-anchor="middle">France</text>
<rect x="210" y="60" width="80" height="22" fill="var(--panel)" stroke="var(--line)"/>
<text x="250" y="75" fill="var(--ink)" font-size="9" text-anchor="middle">engineer</text>
<text x="360" y="75" fill="var(--s1)" font-size="9" text-anchor="middle">4 cells</text>
<text x="220" y="108" fill="var(--muted)" font-size="10" text-anchor="middle">embedded newline: one row becomes two</text>
<rect x="90" y="118" width="120" height="20" fill="var(--panel)" stroke="var(--line)"/>
<text x="150" y="132" fill="var(--ink)" font-size="9" text-anchor="middle">Bo,Rome,wri</text>
<rect x="90" y="142" width="60" height="20" fill="var(--panel)" stroke="var(--line)"/>
<text x="120" y="156" fill="var(--ink)" font-size="9" text-anchor="middle">ter</text>
</svg>
^ The comma inside a field adds a cell and shifts the rest; the newline inside a field breaks one row into two.

Now the CSV writer, which quotes any field holding a special character.

```python filename=modules/teaching-and-portability/code/csvquote-inter-01/csvquote.py:44-48 COMPLETE
def csv_write(rows):
    """Write with the csv module, which quotes any field holding a comma, quote, or newline."""
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue()
```

Run `--safe` to see the quoting and the exact round-trip:

```text filename=csvquote.py --safe
SAFE — write and read with the csv module
----------------------------------------------------------
  serialized (quotes added around the special fields):
    name,city,role
    Ada,"Paris, France",engineer
    Bo,Rome,"wri
    ter"
  re-parsed into 3 rows (should be 3):
    row 0 -> 3 fields: ['name', 'city', 'role']
    row 1 -> 3 fields: ['Ada', 'Paris, France', 'engineer']
    row 2 -> 3 fields: ['Bo', 'Rome', 'wri\nter']
----------------------------------------------------------
  every field is carried literally; the round-trip is exact
```

The writer wrapped "Paris, France" and the two-line note in double quotes; the reader saw the quotes and kept each field whole, including reading the newline as part of the field rather than a row break. Three rows in, three rows out, every field identical.

<svg role="img" aria-label="A field containing a comma shown wrapped in double quotes, so the reader treats the whole quoted span as one cell and the round-trip returns three rows unchanged" viewBox="0 0 440 120">
<text x="220" y="18" fill="var(--muted)" font-size="10" text-anchor="middle">quoting marks the field as one unit</text>
<rect x="30" y="30" width="60" height="24" fill="var(--panel)" stroke="var(--line)"/>
<text x="60" y="46" fill="var(--ink)" font-size="10" text-anchor="middle">Ada</text>
<rect x="90" y="30" width="150" height="24" fill="var(--s1)" stroke="var(--line)"/>
<text x="165" y="46" fill="var(--ink)" font-size="10" text-anchor="middle">"Paris, France"</text>
<rect x="240" y="30" width="90" height="24" fill="var(--panel)" stroke="var(--line)"/>
<text x="285" y="46" fill="var(--ink)" font-size="10" text-anchor="middle">engineer</text>
<text x="380" y="46" fill="var(--s1)" font-size="9" text-anchor="middle">3 cells</text>
<text x="220" y="86" fill="var(--muted)" font-size="10" text-anchor="middle">the comma inside the quotes is data, not a delimiter</text>
<text x="220" y="104" fill="var(--ink)" font-size="10" text-anchor="middle">round-trip: 3 rows in, 3 rows out</text>
</svg>
^ The quotes tell the reader the comma is inside the field, so the row keeps three cells and the round-trip is exact.

## Build

The self-test plants the failure and names each claim as a boolean flag. It writes the table both ways and re-parses each, checking that the naive round-trip has the wrong row count, the wrong field count, and does not equal the original, while the CSV round-trip has the right row count and equals the original exactly.

```python filename=modules/teaching-and-portability/code/csvquote-inter-01/csvquote.py:95-108 COMPLETE
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
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the naive writer ever stops corrupting or the CSV writer ever stops round-tripping:

```text filename=csvquote.py --check
SELF-TEST — naive join corrupts fields with a comma or newline; a CSV writer quotes them and round-trips
------------------------------------------------------------------------------------------------------------
  naive: re-parsed row count is wrong = True (4 vs 3)
  naive: some re-parsed row has the wrong field count = True
  naive: the round-trip does not equal the original = True
  csv: re-parsed row count is correct = True (3)
  csv: the round-trip equals the original exactly = True
------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  naive_wrong_row_count=True  naive_wrong_field_count=True  naive_not_roundtrip=True  csv_right_row_count=True  csv_roundtrips=True
```

**The self-test asserts the exact round-trip equality, not just that the shape differs — so it proves the CSV writer preserves every field's content, including the newline inside a field, and not merely that the counts happen to match.**

## Definition of done

You can explain why CSV's delimiters being ordinary text characters is what makes a hand-rolled writer unsafe.
You can name the escaping mechanism CSV uses — quoting a field, doubling internal quotes — and say what it lets the format carry.
You can distinguish the within-row corruption from an embedded comma (a phantom column, shifted fields) from the cross-row corruption from an embedded newline (one row read as two).
You can explain why the bug is silent: the writer succeeds, and only the reader discovers the wrong shape, without an exception.
You can say what to use instead — a CSV library for both writing and reading — and why using it on both ends is what guarantees the round-trip.

## Boss fight

Add a field that itself contains a double quote — say `["Cy", 'the "best" cafe', "owner"]` — and rerun `--safe`. The CSV writer quotes the field and doubles the internal quote, writing it as `"the ""best"" cafe"`, and the reader collapses the doubled quotes back to one on the way in, so the round-trip is still exact. This is the third special character quoting has to handle, and the library handles it for free; a hand-rolled quoter that forgets to double internal quotes would corrupt exactly this field. The lesson deepens: escaping has edge cases, and the reason to use the library is that it has already found them.

Now try the tempting half-fix: keep the naive writer but switch the delimiter to a tab, on the theory that tabs never appear in data. Rerun with a field that contains a tab, or a newline, and it breaks again — the newline still splits the row, and any field with a tab still splits a column. Choosing a rarer delimiter narrows the failure but does not close it; only quoting handles a field that contains whatever character you chose as the delimiter. A rare delimiter is a smaller target, not a safe one.

**A rarer delimiter shrinks the failure surface but never removes it, because a field can contain any character — only quoting, which marks where a field truly ends, makes the format safe for arbitrary data.**

## External resources

RFC 4180 defines the common CSV dialect, including the quoting rules — fields with commas, quotes, or line breaks are enclosed in double quotes and internal quotes are doubled.
Python's csv module documentation describes its writer and reader, dialects, and why it exists rather than leaving the format to string joins.
The topic's own modules on line-ending normalization and on locale-independent number formatting cover the other ways tabular text data fails to survive a trip between machines.
