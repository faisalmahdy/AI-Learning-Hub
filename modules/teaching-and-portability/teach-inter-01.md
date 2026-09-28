---
id: teach-inter-01
title: Portable means a stranger can run it — scan for what only works on your machine
topic: teaching-and-portability
level: intermediate
status: ready
time: 8-10h
summary: An extracted module that runs perfectly for its author still fails on line one for everyone else, because it carries references that resolve only on the author's machine — an absolute /home path, a hardcoded API token, a personal email, the IP of a box on their desk. A portability scan finds all four blockers in the as-extracted module and zero in the de-personalized one, and it is the only honest check that a stranger could run it, because "looks generic" is not the same as "has no machine-specific reference" — and one of the four is a leaked secret.
eli5: A recipe that says "bake at the usual temperature and use the spice from the jar on my left" works only in your kitchen. To share it, replace everything that means something only to you — and check that nothing personal is left, especially a password you forgot was written in.
---

## Why this module

This track is about turning a personal system into something others can use, and this module builds the gate that decides whether an extracted module is actually shareable. The curriculum's first teaching task is blunt about the standard: "de-personalize paths and content" so that "a stranger could run them." The gap between a module that works for its author and one that works for anyone is not features or docs — it is a handful of references that silently assume the author's machine, and every one of them is invisible to the author precisely because it works for them.

The trap is that the module looks done. It runs end to end, the code is clean, the README reads well — on the author's laptop, where `/home/faisal/projects` exists, where the API token is already exported, where `192.168.1.42` is the box under the desk. Hand it to someone else and it fails immediately: a path that does not exist, a token that is not set, a service at an address on a network they are not on. And one of those machine-specific references is worse than a bug — a hardcoded secret that should never have been in the module at all, now published for everyone. "Portable" is not a vibe; it is the property that a scan for machine-specific references comes back empty.

You need the extraction instinct from this track. Everything runs offline against two variants of one module — as-extracted and de-personalized — stdlib Python 3, `$0.00`. The instinct to unlearn is that code which runs is code which ports. It runs *for you*; portability is whether it runs for someone who is not you, and the only way to know before you publish is to look for the things that are only true on your machine.

Here is the as-extracted module scanned:

```
# modules/teaching-and-portability/code/teach-inter-01/ — COMPLETE, run from that directory
$ python3 portability.py --scan raw

SCAN — raw variant
--------------------------------------------------------------------
  setup.md    :1    home_path         /home/faisal
  config.py   :1    local_address     192.168.1.42:8080
  config.py   :2    hardcoded_secret  sk-9fJ2kd0slQ8xM
  README.md   :1    personal_email    faisal.mahdy@example.com
```

run: 2026-08-25 · deterministic; module variants are a fixture · 4 rules, 2 variants · `python3 portability.py --scan raw`

Four references that resolve only on the author's machine — and the third is a secret. Each one is a wall a stranger hits. This module is the scan that finds them and the de-personalization that clears them.

## Concepts

Named here so you can find them again; each is built below.

- **Extraction** — lifting a working piece out of a personal project into a standalone module.
- **De-personalization** — replacing everything that means something only to the author.
- **Machine-specific reference** — a path, address, secret, or identity that resolves only on the author's setup.
- **Portability scan** — a search for those references; empty means a stranger can run it.
- **Blocker** — a machine-specific reference that stops someone else; a hardcoded secret is the worst kind.
- **Portable** — the property that the scan returns zero, not the impression that the code looks generic.

## Worked example

Source: the track's extraction task — CLAUDE.md contracts, orchestration docs, and framework files de-personalized into hub modules — held to the "a stranger could run them" standard. This module builds the scan that standard needs.

Script and fixture: `modules/teaching-and-portability/code/teach-inter-01/` — `portability.py`, and `files.json`, two variants of the same extracted module. Every command runs from there.

### The frame: a recipe written for your own kitchen

Picture handing a friend a recipe you wrote for yourself. It says "bake at the usual temperature," "use the spice from the jar on the left," "finish when it looks right." Every instruction is complete to you and useless to your friend, because each one points at something only in your kitchen — your oven's "usual," your shelf's "left," your eye's "right." To share it you replace each private reference with a public one: an actual temperature, the spice by name, a doneness test anyone can apply.

An extracted module is that recipe. `/home/faisal/projects` is "the jar on the left"; the exported token is "the usual temperature." De-personalizing is rewriting each private reference as a public one — a path variable, an environment lookup, a placeholder. And the portability scan is the friend trying to cook from it: it hits every instruction that only means something in your kitchen and stops. The whole module is running that scan before you hand the recipe over.

### The rules: what only works on your machine

The scan looks for a small set of machine-specific patterns — the references that resolve for the author and nobody else.

```
# portability.py:30-35 — COMPLETE (the patterns that break a module for a stranger)
RULES = [
    ("home_path", r"/(?:home|Users)/[A-Za-z][\w.-]*"),
    ("hardcoded_secret", r"\b(?:sk-[A-Za-z0-9]{6,}|AKIA[0-9A-Z]{8,}|ghp_[A-Za-z0-9]{6,})\b"),
    ("personal_email", r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    ("local_address", r"\b(?:127\.0\.0\.1|localhost|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)(?::\d+)?\b"),
]
```

Each rule is a different way the author's setup leaks in: an absolute home path that exists only on their disk, a secret that should never be in the source, an email that personalizes a shared artifact, a private network address no one else can reach. The scan walks every file line by line and records each match.

```
# portability.py:43-51 — COMPLETE (find every machine-specific reference)
def scan(files):
    """Every machine-specific reference in a set of files: (file, line, kind, text)."""
    hits = []
    for name, content in files.items():
        for lineno, line in enumerate(content.splitlines(), 1):
            for kind, pat in RULES:
                for m in re.finditer(pat, line):
                    hits.append((name, lineno, kind, m.group(0)))
    return hits
```

Portability is then a one-line property: the scan returns nothing.

```
# portability.py:54-55 — COMPLETE (portable = no machine-specific references)
def is_portable(files):
    return len(scan(files)) == 0
```

<svg viewBox="0 0 700 180" role="img" aria-label="The raw module's four files with four flagged references: setup.md a home path, config.py a local address and a hardcoded secret, README.md a personal email. Each is labeled as a blocker for a stranger.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">the as-extracted module: four references that resolve only for the author</text>
    <rect x="30" y="30" width="620" height="26" rx="4" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="40" y="47" fill="var(--ink)">setup.md:  clone to </text><text x="230" y="47" fill="var(--s2)">/home/faisal/projects/agent</text>
    <text x="470" y="47" fill="var(--s2)" font-size="8">home_path</text>
    <rect x="30" y="60" width="620" height="26" rx="4" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="40" y="77" fill="var(--ink)">config.py: API_URL = </text><text x="230" y="77" fill="var(--s2)">http://192.168.1.42:8080</text>
    <text x="470" y="77" fill="var(--s2)" font-size="8">local_address</text>
    <rect x="30" y="90" width="620" height="26" rx="4" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5"></rect>
    <text x="40" y="107" fill="var(--ink)">config.py: TOKEN = </text><text x="230" y="107" fill="var(--s2)">sk-9fJ2kd0slQ8xM</text>
    <text x="450" y="107" fill="var(--s2)" font-size="8">hardcoded_secret (worst)</text>
    <rect x="30" y="120" width="620" height="26" rx="4" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="40" y="137" fill="var(--ink)">README.md: email </text><text x="230" y="137" fill="var(--s2)">faisal.mahdy@example.com</text>
    <text x="470" y="137" fill="var(--s2)" font-size="8">personal_email</text>
    <text x="20" y="168" fill="var(--muted)">all four read fine to the author; all four stop everyone else -- and one is a secret.</text>
  </g>
</svg>
^ The four blockers in the extracted module. Each is a reference the author never notices because it works for them; a stranger hits the first one and stops, and the leaked token is a security problem on top of a portability one.

### The as-extracted module fails; the de-personalized one passes

Scan the de-personalized variant and it comes back empty — every private reference has been rewritten as a public one.

```
# $ python3 portability.py --scan portable
#   no machine-specific references -- a stranger can run this.
#   0 blocker(s). portable = True
```

run: 2026-08-25 · fixture · `python3 portability.py --scan portable`

The de-personalization is small and mechanical: `/home/faisal/projects/agent` became `$PROJECT_DIR`, the hardcoded token became `os.environ['TOKEN']`, the private address became `os.environ['API_URL']`, the email became "open an issue." None of it changed what the module *does*; all of it changed who can run it. The comparison makes the gap one number:

```
# $ python3 portability.py --compare
#   raw        4 blocker(s)  ['hardcoded_secret', 'home_path', 'local_address', 'personal_email']
#   portable   0 blocker(s)  clean
```

run: 2026-08-25 · fixture · `python3 portability.py --compare`

Four to zero. The raw module "looks done and runs — for its author"; the portable one runs for anyone. And note the raw module would pass a functional test on the author's machine with flying colors — the tests, too, run in the author's kitchen. Functionality and portability are orthogonal, which is why a passing test suite is no evidence a module ports.

<svg viewBox="0 0 700 170" role="img" aria-label="A two-by-two of works-for-author versus works-for-anyone. The raw module sits in works-for-author-yes, works-for-anyone-no. The portable module sits in yes-yes. A passing test suite only measures the author axis.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">functionality (works for author) and portability (works for anyone) are separate</text>
    <line x1="200" y1="30" x2="200" y2="150" stroke="var(--grid)"></line>
    <line x1="60" y1="90" x2="620" y2="90" stroke="var(--grid)"></line>
    <text x="90" y="130" fill="var(--muted)" text-anchor="middle">fails for author</text>
    <text x="400" y="130" fill="var(--muted)" text-anchor="middle">works for author</text>
    <text x="30" y="60" fill="var(--muted)">anyone: yes</text>
    <text x="30" y="120" fill="var(--muted)">anyone: no</text>
    <circle cx="420" cy="120" r="6" fill="var(--s2)"></circle><text x="432" y="123" fill="var(--s2)">raw (4 blockers)</text>
    <circle cx="420" cy="60" r="6" fill="var(--s1)"></circle><text x="432" y="63" fill="var(--s1)">portable (0 blockers)</text>
    <text x="220" y="60" fill="var(--muted)" font-size="8">(impossible: can't work</text><text x="220" y="72" fill="var(--muted)" font-size="8">for others, not you)</text>
    <text x="220" y="164" fill="var(--muted)" font-size="8">a test suite only moves you along the horizontal axis, never up.</text>
  </g>
</svg>
^ A test suite proves the module works for its author — the horizontal axis — and says nothing about the vertical one. De-personalization is the only move that lifts a working module from "runs for me" to "runs for anyone."

<svg viewBox="0 0 700 150" role="img" aria-label="Before and after de-personalization. Raw: 4 blockers, runs for the author only. Portable: 0 blockers, runs for anyone. Each blocker maps to a fix: home path to a variable, secret to an env lookup, address to an env lookup, email to an issue link.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">de-personalization: each private reference becomes a public one</text>
    <g fill="var(--ink)">
      <text x="30" y="44">/home/faisal/projects/agent</text><text x="270" y="44" fill="var(--s1)">-> $PROJECT_DIR</text>
      <text x="30" y="64">sk-9fJ2kd0slQ8xM</text><text x="270" y="64" fill="var(--s1)">-> os.environ['TOKEN']</text>
      <text x="30" y="84">192.168.1.42:8080</text><text x="270" y="84" fill="var(--s1)">-> os.environ['API_URL']</text>
      <text x="30" y="104">faisal.mahdy@example.com</text><text x="270" y="104" fill="var(--s1)">-> open an issue</text>
    </g>
    <rect x="470" y="34" width="90" height="30" rx="5" fill="var(--panel)" stroke="var(--s2)"></rect><text x="480" y="53" fill="var(--s2)">raw: 4, you</text>
    <rect x="470" y="80" width="90" height="30" rx="5" fill="var(--panel)" stroke="var(--s1)"></rect><text x="480" y="99" fill="var(--s1)">portable: 0, all</text>
    <text x="20" y="138" fill="var(--muted)">the module does the same thing; only who can run it changed.</text>
  </g>
</svg>
^ Each blocker has a mechanical fix that turns a private reference into a public one. The behavior is unchanged; the audience goes from one person to anyone, and the leaked secret is removed in the bargain.

**A module is portable only when a scan for machine-specific references comes back empty — not when it looks generic, because the paths, secrets, and addresses that break it for a stranger are exactly the ones that are invisible to its author.**

The self-test confirms the scan catches the blockers, especially the secret, and that de-personalization clears every kind:

```
# $ python3 portability.py --check
#   raw has machine-specific blockers = True (4)
#   portable has none = True
#   the scan catches the hardcoded secret in raw = True
#   every blocker kind in raw is gone in portable = True (raw=['hardcoded_secret', 'home_path', 'local_address', 'personal_email'])
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · `python3 portability.py --check`

### What we did not settle

The scan is a set of patterns, and patterns both miss and over-flag. Real complications we skipped: it will miss machine-specific assumptions that are not textual — a script that relies on a tool being installed, a default that only works in one timezone, a path separator that only works on one OS — so the scan is necessary, not sufficient, and the real test is a stranger (or a clean container) actually running it; it will over-flag, too, since `localhost` is legitimate in a docstring telling the user to visit their own server, so a real scan needs an allowlist and human judgment on each hit; and a hardcoded secret is not merely a portability blocker but a security incident — once committed it must be rotated, not just deleted, which is a whole discipline of its own. The dial here is a text scan; the standard is a clean machine running the module from scratch.

## Build

The pipeline in one paragraph: before publishing an extracted module, scan every file for machine-specific references — absolute home paths, hardcoded secrets, personal identities, private addresses; de-personalize each into a public form (a variable, an environment lookup, a placeholder, an issue link); rotate any secret the scan finds, because deleting it from the source does not un-leak it; and treat the module as portable only when the scan is empty and, ideally, a clean container runs it end to end. Never publish a module you have only run on your own machine.

We opened on the four blockers. The state to publish from:

```
# modules/teaching-and-portability/code/teach-inter-01/ — COMPLETE, run from that directory
$ python3 portability.py --compare
  portable   0 blocker(s)  clean
```

Now scan your own extracted module. Run the portability scan over its files and de-personalize every hit — and rotate any secret it finds. Your number to beat is **zero blockers**, and your real acceptance test is a clean container or a colleague running it from scratch, since the scan catches text but not every machine-specific assumption. Add a hardcoded token to a file and confirm the scan flags it before you would have published it. Bring back the before-and-after blocker counts and the list of kinds you fixed. Good luck.

## Definition of done

- [ ] A portability scan over a module's files for machine-specific references (paths, secrets, identities, addresses)
- [ ] De-personalization of every hit into a public form, and rotation of any secret found
- [ ] A portable check that is true only when the scan returns zero
- [ ] Your own extracted module scanned before and after de-personalization
- [ ] The as-extracted variant kept for contrast, so the blockers are visible, not assumed
- [ ] `python3 portability.py --check` printing SELF-TEST PASS: raw blocked, portable clean, secret caught, every kind fixed
- [ ] The before-and-after blocker counts recorded, and a clean-machine run of the portable version
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. A module runs perfectly for its author and fails on line one for everyone else. Explain why the failing references are exactly the ones the author cannot see.
2. Why is a passing functional test suite no evidence that a module is portable?
3. Name the four machine-specific reference kinds the scan looks for, and which one is a security incident rather than just a portability blocker.
4. Why does the scan being empty count as "necessary but not sufficient" for portability? Give one thing it would miss.
5. Your own module was scanned. How many blockers before and after, and did you rotate any secret the scan found?

## External resources

- The hub's own extraction standard (`modules/README.md` absorption rules) — my summary: own material must be de-personalized with paths, names, and personal content scrubbed and a `Source:` line; read it for the exact de-personalization bar every module in this hub already meets.
- git-secrets / gitleaks — https://github.com/gitleaks/gitleaks — my summary: production scanners for committed secrets, the industrial version of this module's `hardcoded_secret` rule; read it for a real pattern set and for the pre-commit hook that stops a secret before it is ever published.
- This hub, *ship-basic-01* — modules/ship-and-operate/ship-basic-01.md — my summary: making a generated file a pure function of its source; read it for the sibling discipline — where that module removes non-determinism, this one removes machine-specificity, both so the artifact behaves the same off its author's machine.
