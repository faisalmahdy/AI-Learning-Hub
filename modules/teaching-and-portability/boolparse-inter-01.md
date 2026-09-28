---
id: boolparse-inter-01
title: Parse a boolean config value against known tokens, never with bool() on the string — bool("false") is True
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: A boolean setting almost never reaches your code as a boolean — it comes from a config file, a command-line flag, or an environment variable, all of which carry text: the string "false", not the value False. The tempting one-liner to convert it is bool(value), and that is the bug: bool() applied to a string does not read the string's meaning, it tests whether the string is empty. Every non-empty string is truthy, so bool("true"), bool("false"), bool("0"), and bool("no") are all True — only the empty string is False. The setting is therefore inverted for exactly the values a person uses to turn something off: someone writes FEATURE_ENABLED=false expecting the feature off, bool("false") returns True, and the feature is on, silently, with no error. It looks like it works in a quick test that only tries the true case, because "true" and "1" happen to come out right. The fix is an explicit parser that lowercases and strips the string, matches it against a known set of truthy tokens (true, 1, yes, on) and falsy tokens (false, 0, no, off), and rejects anything else rather than guessing. On a fixture of nine config strings, bool() reads all eight non-empty ones as True — including "false", "0", "no", "off" — while the explicit parser reads the four falsy tokens as False and rejects the empty string instead of silently accepting it.
eli5: Imagine you leave a note for a helper that says whether to water the plants: you write "no." The helper, instead of reading the word, just checks whether you left a note at all — you did, so they water the plants. Any note means yes to them, even a note that says no, because they only notice that the paper is not blank. The only way to get "don't water" is to leave a completely empty page, which is the opposite of clear. The fix is a helper who actually reads the word and knows that "no," "false," and "off" mean don't, while "yes," "true," and "on" mean do — and who asks you if you write something they don't recognize, instead of guessing.
---

## Why this module

Configuration is where booleans go to become strings. You set a flag in a YAML file, pass `--verbose` on the command line, or read `DEBUG` from the environment, and in every one of those channels the value arrives as text. The code that consumes it has to turn the string "true" or "false" into an actual boolean, and that conversion is a decision point that looks too trivial to get wrong.

The trivial-looking conversion is `bool(value)`, and it is wrong in a way that is easy to ship. `bool()` is not a string parser. Given a string, it does not look at what the string says — it looks at whether the string has any characters. Non-empty is True, empty is False. That rule has nothing to do with the words "true" and "false"; it is about length, not meaning.

So `bool("false")` is True, and so is `bool("0")`, `bool("no")`, and `bool("off")`. Every conventional way of writing "off" is a non-empty string, so every one of them reads as on. The setting comes out backwards precisely for the values someone would choose to disable a feature, and nothing complains — the program runs, the flag is just the opposite of what the config says.

**A boolean from config arrives as a string, and bool() of a string tests emptiness, not meaning — so bool("false"), bool("0"), and bool("no") are all True, silently inverting the setting for exactly the values that mean off.**

## Concepts

The root of it is Python's truthiness rule for strings, which is a rule about the container, not the contents. An empty string is falsy; any non-empty string is truthy. This rule is useful for "did the user type anything," and it is exactly the wrong rule for "does this word mean true," because the word "false" is a perfectly non-empty string. `bool()` never had a chance to be right here — it was answering a different question.

<svg role="img" aria-label="A gate labeled bool() that tests only whether a string is empty. The strings true, false, 0, no, off all pass through as True because they are non-empty; only the empty string comes out False." viewBox="0 0 440 140">
<text x="20" y="16" fill="var(--muted)" font-size="9">bool(string) asks: is it non-empty? — not: what does it mean?</text>
<rect x="30" y="30" width="60" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="60" y="41" fill="var(--ink)" font-size="8" text-anchor="middle">"true"</text>
<rect x="30" y="48" width="60" height="14" fill="var(--panel)" stroke="var(--s2)"/><text x="60" y="59" fill="var(--s2)" font-size="8" text-anchor="middle">"false"</text>
<rect x="30" y="66" width="60" height="14" fill="var(--panel)" stroke="var(--s2)"/><text x="60" y="77" fill="var(--s2)" font-size="8" text-anchor="middle">"0"</text>
<rect x="30" y="84" width="60" height="14" fill="var(--panel)" stroke="var(--s2)"/><text x="60" y="95" fill="var(--s2)" font-size="8" text-anchor="middle">"no"</text>
<rect x="30" y="102" width="60" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="60" y="113" fill="var(--ink)" font-size="8" text-anchor="middle">""</text>
<rect x="180" y="55" width="60" height="34" fill="var(--panel)" stroke="var(--line)"/><text x="210" y="76" fill="var(--ink)" font-size="9" text-anchor="middle">bool()</text>
<line x1="90" y1="37" x2="180" y2="66" stroke="var(--line)"/><line x1="90" y1="55" x2="180" y2="70" stroke="var(--s2)"/><line x1="90" y1="73" x2="180" y2="72" stroke="var(--s2)"/><line x1="90" y1="91" x2="180" y2="74" stroke="var(--s2)"/><line x1="90" y1="109" x2="180" y2="82" stroke="var(--line)"/>
<text x="330" y="52" fill="var(--s2)" font-size="9">True: "true","false","0","no",...</text>
<text x="330" y="88" fill="var(--ink)" font-size="9">False: "" only</text>
</svg>
^ bool() routes on emptiness, so every non-empty config string — including the falsy words — comes out True, and only the empty string comes out False.

The fix is to answer the actual question: parse the string against the vocabulary of booleans. Normalize it first — strip surrounding whitespace and lowercase it, so " True " and "TRUE" and "true" are the same token — then look it up in a set of known truthy words and a set of known falsy words. The meaning now comes from the lookup table, which encodes what the strings mean, rather than from `bool()`, which encodes only whether they exist.

<svg role="img" aria-label="A parser mapping strings to booleans via two token sets. The truthy set true, 1, yes, on maps to True; the falsy set false, 0, no, off maps to False; an unrecognized value goes to a raised error rather than a guess." viewBox="0 0 440 130">
<rect x="20" y="30" width="150" height="30" fill="var(--panel)" stroke="var(--s1)"/><text x="95" y="42" fill="var(--s1)" font-size="8" text-anchor="middle">truthy: true, 1, yes, on</text><text x="95" y="54" fill="var(--muted)" font-size="7" text-anchor="middle">-&gt; True</text>
<rect x="20" y="66" width="150" height="30" fill="var(--panel)" stroke="var(--s2)"/><text x="95" y="78" fill="var(--s2)" font-size="8" text-anchor="middle">falsy: false, 0, no, off</text><text x="95" y="90" fill="var(--muted)" font-size="7" text-anchor="middle">-&gt; False</text>
<rect x="240" y="48" width="180" height="30" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="4 3"/><text x="330" y="60" fill="var(--ink)" font-size="8" text-anchor="middle">anything else -&gt; ValueError</text><text x="330" y="72" fill="var(--muted)" font-size="7" text-anchor="middle">rejected, not guessed</text>
<text x="205" y="66" fill="var(--muted)" font-size="8">strip + lowercase, then look up</text>
</svg>
^ The explicit parser normalizes the string and maps it through known truthy and falsy token sets, sending anything unrecognized to an error rather than a silent guess.

Two design choices in that parser matter. First, normalize before lookup, so case and whitespace variants of the same word all resolve — otherwise "False" from a config file misses a table keyed only on "false" and falls through. Second, reject the unknown rather than default it: if a value is neither a known truthy nor a known falsy token, raising an error surfaces a typo ("flase", "yes please") at startup, where it is cheap to fix, instead of silently choosing a direction that might be wrong. A parser that guesses on unrecognized input reintroduces the very silence you are trying to eliminate.

**Parse the string by normalizing it (strip, lowercase) and looking it up in explicit truthy and falsy token sets, and reject anything unrecognized rather than guessing — the meaning lives in the table, not in whether the string is empty.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/boolparse-inter-01. The fixture is a list of boolean-like config strings as they would arrive from a file or environment.

```json filename=modules/teaching-and-portability/code/boolparse-inter-01/boolparse.json:3 COMPLETE
  "values": ["true", "false", "False", "0", "1", "yes", "no", "off", ""]
```

The known token sets encode what the strings mean.

```python filename=modules/teaching-and-portability/code/boolparse-inter-01/boolparse.py:27-28 COMPLETE
TRUTHY = {"true", "1", "yes", "on"}
FALSY = {"false", "0", "no", "off"}
```

The naive conversion is bool() on the string, which tests emptiness.

```python filename=modules/teaching-and-portability/code/boolparse-inter-01/boolparse.py:35-37 COMPLETE
def naive_bool(s):
    """The bug: bool() of a string tests emptiness, not meaning."""
    return bool(s)
```

The explicit parser normalizes and looks up, rejecting the unrecognized.

```python filename=modules/teaching-and-portability/code/boolparse-inter-01/boolparse.py:40-47 COMPLETE
def parse_bool(s):
    """Map the string against known tokens; raise on anything unrecognized rather than guess."""
    key = s.strip().lower()
    if key in TRUTHY:
        return True
    if key in FALSY:
        return False
    raise ValueError("not a recognized boolean: %r" % s)
```

Before running it, predict: bool() will return True for every non-empty string, so "false", "0", "no", and "off" will all read as on. Run `--naive`:

```text filename=boolparse.py --naive
NAIVE — bool() applied to each config string
--------------------------------------------
  bool('true'  ) = True
  bool('false' ) = True
  bool('False' ) = True
  bool('0'     ) = True
  bool('1'     ) = True
  bool('yes'   ) = True
  bool('no'    ) = True
  bool('off'   ) = True
  bool(''      ) = False
--------------------------------------------
  every non-empty string is True -- 'false', '0', 'no', 'off' all read as on
```

The prediction holds completely. Eight of the nine strings are non-empty, so bool() returns True for all eight — "false" and "False" and "0" and "no" and "off" included. The only False is the empty string, and that is an accident of emptiness, not an understanding that "" means off. A feature flag set to any of the four falsy words is now on. And a test that only checked `bool("true") == True` would pass and see nothing wrong.

Now the explicit parser on the same strings. Run `--parse`:

```text filename=boolparse.py --parse
PARSE — the explicit token parser applied to each config string
--------------------------------------------
  parse_bool('true'  ) = True
  parse_bool('false' ) = False
  parse_bool('False' ) = False
  parse_bool('0'     ) = False
  parse_bool('1'     ) = True
  parse_bool('yes'   ) = True
  parse_bool('no'    ) = False
  parse_bool('off'   ) = False
  parse_bool(''      ) -> ValueError (not a recognized boolean: '')
--------------------------------------------
  the falsy tokens read as False; an unrecognized value is rejected, not guessed
```

Now the words mean what they say. "false", "False", "0", "no", and "off" all read as False; "true", "1", "yes" read as True. Note "False" with a capital letter also parses correctly, because the parser lowercased it before the lookup — a table keyed only on "false" would have missed it. And the empty string, which bool() quietly called False, is now a ValueError: rather than guess a direction for an unrecognized value, the parser refuses, surfacing the ambiguity where you can fix it instead of shipping a silent default.

<svg role="img" aria-label="Two columns comparing bool() and the parser for each config string. bool() column is all True except the empty string. Parser column has false, False, 0, no, off as False, matching their meaning, with the four commonly-inverted ones highlighted." viewBox="0 0 440 160">
<text x="130" y="14" fill="var(--muted)" font-size="9">value      bool()      parser</text>
<text x="20" y="32" fill="var(--ink)" font-size="8">true</text><text x="150" y="32" fill="var(--ink)" font-size="8">True</text><text x="250" y="32" fill="var(--ink)" font-size="8">True</text>
<text x="20" y="48" fill="var(--s2)" font-size="8">false</text><text x="150" y="48" fill="var(--s2)" font-size="8">True</text><text x="250" y="48" fill="var(--s1)" font-size="8">False</text><text x="300" y="48" fill="var(--s2)" font-size="7">inverted</text>
<text x="20" y="64" fill="var(--s2)" font-size="8">0</text><text x="150" y="64" fill="var(--s2)" font-size="8">True</text><text x="250" y="64" fill="var(--s1)" font-size="8">False</text><text x="300" y="64" fill="var(--s2)" font-size="7">inverted</text>
<text x="20" y="80" fill="var(--s2)" font-size="8">no</text><text x="150" y="80" fill="var(--s2)" font-size="8">True</text><text x="250" y="80" fill="var(--s1)" font-size="8">False</text><text x="300" y="80" fill="var(--s2)" font-size="7">inverted</text>
<text x="20" y="96" fill="var(--s2)" font-size="8">off</text><text x="150" y="96" fill="var(--s2)" font-size="8">True</text><text x="250" y="96" fill="var(--s1)" font-size="8">False</text><text x="300" y="96" fill="var(--s2)" font-size="7">inverted</text>
<text x="20" y="112" fill="var(--ink)" font-size="8">1 / yes</text><text x="150" y="112" fill="var(--ink)" font-size="8">True</text><text x="250" y="112" fill="var(--ink)" font-size="8">True</text>
<text x="20" y="128" fill="var(--ink)" font-size="8">""</text><text x="150" y="128" fill="var(--ink)" font-size="8">False</text><text x="250" y="128" fill="var(--ink)" font-size="8">error</text>
<text x="130" y="150" fill="var(--muted)" font-size="8">bool() inverts every falsy word; the parser reads each correctly</text>
</svg>
^ bool() and the parser agree only on the truthy words; on "false", "0", "no", and "off" bool() is inverted, and on "" the parser refuses rather than guess.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that bool() is True for every falsy-looking string, that the only string bool() reads as False is the empty string, that bool() and the parser disagree on every falsy token, that the parser reads the falsy tokens as False, and that it reads the truthy tokens as True.

```python filename=modules/teaching-and-portability/code/boolparse-inter-01/boolparse.py:78-91 COMPLETE
    falsy_strings = ["false", "False", "0", "no", "off"]
    bool_true_on_falsy = all(naive_bool(s) is True for s in falsy_strings)
    print("  bool() is True for every falsy-looking string = %s (%s)" % (bool_true_on_falsy, falsy_strings))

    only_empty_is_false = [v for v in values if naive_bool(v) is False] == [""]
    print("  the only string bool() reads as False is the empty string = %s" % only_empty_is_false)

    naive_inverts_falsy = all(naive_bool(s) != parse_bool(s) for s in ["false", "0", "no", "off"])
    print("  bool() and the parser disagree on every falsy token = %s" % naive_inverts_falsy)

    parser_reads_falsy = all(parse_bool(s) is False for s in ["false", "False", "0", "no", "off"])
    print("  the parser reads the falsy tokens as False = %s" % parser_reads_falsy)

    parser_reads_truthy = all(parse_bool(s) is True for s in ["true", "1", "yes", "on"])
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if bool() ever stopped inverting the falsy tokens or the parser ever misread one:

```text filename=boolparse.py --check
SELF-TEST — bool() reads every non-empty string as True, inverting the falsy ones; the explicit parser reads them correctly
----------------------------------------------------------------------------------------------------------------
  bool() is True for every falsy-looking string = True (['false', 'False', '0', 'no', 'off'])
  the only string bool() reads as False is the empty string = True
  bool() and the parser disagree on every falsy token = True
  the parser reads the falsy tokens as False = True
  the parser reads the truthy tokens as True = True
```

**The self-test asserts bool() and the parser disagree on every falsy token — not merely that bool() is often wrong — so a pass certifies the inversion is systematic for exactly the values that mean off, which is what makes the bug a silent config inversion rather than an occasional slip.**

## Definition of done

You can explain why a boolean from config arrives as a string and why that requires a parse.
You can explain why bool() of a string tests emptiness, not meaning, and predict its result for any string.
You can name which config values bool() inverts and why they are the dangerous ones.
You can write an explicit parser that normalizes and looks up truthy and falsy tokens.
You can explain why rejecting unrecognized values beats defaulting them, and why normalization must precede lookup.

## Boss fight

Suppose you write the parser but define only a truthy set and treat everything else as False — no explicit falsy set. Reason about what breaks. It fixes the headline bug (now "false" is False) but reintroduces the silence for a different class: a typo like "ture" or an unexpected token like "enabled" falls into the else branch and is silently read as False, so a feature someone tried to turn on stays off, with no error. A truthy-only or falsy-only parser trades one silent inversion for another; the robust version enumerates both sets and errors on the gap between them, so the only values that pass are ones you explicitly recognized. The lesson: the safety comes from rejecting the unknown, not from which side the unknown defaults to — a parser with a default direction is still guessing.

Now the trap that makes even a good parser inconsistent across a system: everyone rolls their own token set. One module accepts "yes"/"no", another "on"/"off", another only "true"/"false", and a value that is truthy to one is a ValueError or, worse, silently falsy to another, so the same config string means different things in different parts of the program. And the environment adds its own conventions — an environment variable that is unset is different from one set to the empty string, which is different from one set to "false", and shells and container runtimes treat these differently. The fix is one shared, documented boolean parser used everywhere, with a single agreed token vocabulary and a single rule for unset-versus-empty, rather than each site inventing its own. Consistency of the vocabulary across the codebase is as important as the parse being correct at any one site, because a boolean that means different things in different modules is its own class of bug.

**A truthy-only (or falsy-only) parser trades one silent inversion for another — safety comes from rejecting the unknown, not from the default direction; and because ad-hoc token sets make a value mean different things in different modules, use one shared, documented parser with a single vocabulary and a defined unset-versus-empty rule.**

## External resources

Python's own distutils.util.strtobool (and its many successors after distutils' removal) is the canonical example of an explicit truthy/falsy token parser and its raise-on-unrecognized behavior.
The Twelve-Factor App guidance on configuration in the environment, and argparse's handling of boolean flags, describe why config arrives as strings and how to convert it deliberately.
The topic's own modules on JSON type round-trips and on Unicode normalization cover neighboring "the value is not the type or form you assumed" hazards; this one is the boolean case, where the string's meaning must be parsed rather than inferred from its truthiness.
