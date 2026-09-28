---
id: pathjail-inter-01
title: Normalize a tool's path before checking containment — a raw prefix check lets ".." escape the sandbox
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: When an agent has a file tool — read_file, write_file, list_dir — the harness must confine every path the model proposes to a sandbox root, or the model (led by a confused plan, a prompt-injected instruction in a document, or plain error) can reach credentials, other tenants' data, or system files. The confinement is a containment check, and the obvious implementation is subtly, dangerously wrong: join the requested path onto the root and test whether the result starts with the root. That is defeated by the ".." parent segment, because it never resolves the path. The string "/work/project/../secrets.env" literally starts with "/work/project", so the naive check says "inside, allowed" — but that path resolves to "/work/secrets.env", outside the sandbox. This is the classic directory-traversal vulnerability, as exploitable in an agent's tool sandbox as in a web server. The fix is to normalize the joined path first — collapse the ".." and "." segments to the real target — and only then test containment; the escape resolves outside the root and is correctly denied. Normalization also stops over-blocking: "sub/../notes.txt" contains ".." but resolves back inside, so a guard that just bans the substring ".." wrongly rejects a legitimate path. On a fixture with root /work/project, the naive check allows "../secrets.env" and "../../etc/passwd" (their un-normalized joins start with the root) even though they resolve to /work/secrets.env and /etc/passwd outside it, while the correct check denies both and still allows the safe "sub/../notes.txt".
eli5: Imagine a hotel where guests may only enter rooms on their own floor. The guard checks the room number written on your request slip: if it starts with your floor number, you're in. But a sneaky guest writes "Floor 5 → take the stairs down to Floor 1 → room 3." The slip starts with "Floor 5," so the guard waves them through — yet following the directions actually lands them on Floor 1, where they don't belong. The fix is for the guard to actually follow the directions first ("okay, that ends up on Floor 1") and THEN check the floor. Now the sneaky route is caught, while an honest guest whose directions loop back to their own floor is still let in.
---

## Why this module

An agent's file tool is a door to the filesystem, and the harness is the only thing deciding which side of the sandbox wall each request lands on. The instinct is to treat "is this path inside the sandbox?" as a string question — does the path, once glued to the root, begin with the root? — and that instinct hands the model a key to the whole disk. The reason is that a filesystem path is not just a string; it contains navigation, and the ".." segment means "go up," so a path that textually begins inside the root can walk right back out of it. A guard that compares strings without following the navigation is checking the wrong thing entirely.

When an agent has a file tool, the harness must confine every path the model proposes to a sandbox root, or the model — led by a confused plan, a prompt-injected instruction in some document, or plain error — can reach files it was never meant to touch: credentials, other tenants' data, system files. The obvious implementation joins the requested path onto the root and tests whether the result starts with the root. That check is defeated by ".." because it never resolves the path: "/work/project/../secrets.env" literally starts with "/work/project", so the naive check says "inside, allowed" — but that path resolves to "/work/secrets.env", outside the sandbox. This is the classic directory-traversal vulnerability, as exploitable in an agent's tool sandbox as in a web server.

The fix is to normalize the joined path first — collapse the ".." and "." segments to get the real target — and only then test containment. Normalization also stops over-blocking: "sub/../notes.txt" contains ".." but resolves back inside, so a guard that just bans the substring ".." wrongly rejects a legitimate path. This module runs both checks over a set of proposed paths.

**To confine a tool's path argument to a sandbox, resolve the path (join to the root and normalize away ".."/"." segments) before testing containment, and allow it only if the resolved path is the root or sits under it — because a containment check on the un-normalized string is fooled by ".." into allowing an escape, and a substring ban on ".." is fooled into rejecting a safe path that merely passes through a parent.**

## Concepts

**The whole bug is one missing step:** the naive guard joins but does not normalize, so ".." survives in the string; the correct guard normalizes the join into the real target.

```python filename=modules/agent-harness/code/pathjail-inter-01/pathjail.py:55-62 COMPLETE
def naive_join(root, path):
    """Join without normalizing -- the '..' segments survive in the string."""
    return pp.join(root, path)


def resolved_target(root, path):
    """Join and normalize -- collapse '..'/'.' to the real target location."""
    return pp.normpath(pp.join(root, path))
```

**Both guards then run the same containment test** — the only difference is which string they feed it: the raw join or the resolved target.

```python filename=modules/agent-harness/code/pathjail-inter-01/pathjail.py:65-77 COMPLETE
def contains(root, candidate):
    """True if candidate is the root itself or sits under it."""
    return candidate == root or candidate.startswith(root + "/")


def naive_allows(root, path):
    """The BUGGY guard: containment test on the un-normalized join."""
    return contains(root, naive_join(root, path))


def correct_allows(root, path):
    """The correct guard: normalize first, then test containment."""
    return contains(root, resolved_target(root, path))
```

<svg role="img" aria-label="The path work/project/../secrets.env: the naive check reads the string left to right and sees it starts with the root so allows it; normalization first collapses the dot-dot to yield work/secrets.env, which is outside the root" viewBox="0 0 300 120" width="300" height="120">
  <text x="6" y="12" fill="var(--muted)" font-size="8">'..' means go up — a string check misses it, normalizing catches it</text>
  <text x="10" y="30" fill="var(--muted)" font-size="7">requested: ../secrets.env</text>
  <rect x="10" y="40" width="280" height="16" fill="none" stroke="var(--s2)"/>
  <text x="16" y="52" fill="var(--ink)" font-size="7">/work/project/../secrets.env</text>
  <text x="200" y="52" fill="var(--s2)" font-size="6">starts with root ✓ (naive: ALLOW)</text>
  <text x="130" y="72" fill="var(--muted)" font-size="8">↓ normalize (collapse ..)</text>
  <rect x="10" y="80" width="280" height="16" fill="none" stroke="var(--s1)"/>
  <text x="16" y="92" fill="var(--ink)" font-size="7">/work/secrets.env</text>
  <text x="150" y="92" fill="var(--s1)" font-size="6">under root? ✗ (correct: DENY)</text>
  <text x="10" y="112" fill="var(--muted)" font-size="6">the same request is 'inside' as a string and 'outside' once resolved</text>
</svg>
^ The requested "../secrets.env" glued to the root gives a string that starts with the root, so the naive check allows it; normalizing first collapses the ".." to yield /work/secrets.env, which is not under the root, so the correct check denies it — the same request reads as inside before resolution and outside after.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/pathjail-inter-01/pathjail.py

The fixture is the sandbox root and six proposed paths: two plainly inside, one safe path that passes through a parent, two traversal escapes, and one absolute path.

```json filename=modules/agent-harness/code/pathjail-inter-01/pathjail.json:4-11 COMPLETE
  "requests": [
    "notes.txt",
    "sub/data.csv",
    "sub/../notes.txt",
    "../secrets.env",
    "../../etc/passwd",
    "/etc/shadow"
  ]
```

Run `--paths`.

```text filename=--paths
PATHS — confining tool paths to sandbox root /work/project
------------------------------------------------------------------------------------------------
  requested path       naive join                     resolved target        naive  correct
  notes.txt            /work/project/notes.txt        /work/project/notes.txt ALLOW  ALLOW
  sub/data.csv         /work/project/sub/data.csv     /work/project/sub/data.csv ALLOW  ALLOW
  sub/../notes.txt     /work/project/sub/../notes.txt /work/project/notes.txt ALLOW  ALLOW
  ../secrets.env       /work/project/../secrets.env   /work/secrets.env      ALLOW  DENY
  ../../etc/passwd     /work/project/../../etc/passwd /etc/passwd            ALLOW  DENY
  /etc/shadow          /etc/shadow                    /etc/shadow            deny   DENY
```

Read the two verdict columns. On the first three paths, the checks agree and allow — including "sub/../notes.txt", whose resolved target is /work/project/notes.txt, safely inside, even though it contains a "..". That row is important: it is why you cannot just ban the substring "..", because a legitimate path can pass through a parent and come back. The two escape rows are where the guards split. For "../secrets.env", the naive join is /work/project/../secrets.env, which starts with the root, so naive says ALLOW — but the resolved target is /work/secrets.env, outside the root, so correct says DENY. Same for "../../etc/passwd", which resolves to /etc/passwd. The naive guard would have let the tool read a credentials file and a system password file, on nothing more than a string prefix that a ".." made meaningless. The absolute /etc/shadow is denied by both (the join discards the root when the argument is absolute), which is a reminder that absolute paths are a second escape route the containment test must also cover — which, done on the resolved target, it does.

## Build

Walk the exploit on its own to see exactly where the naive check is fooled.

```text filename=--exploit
EXPLOIT — the traversal '../secrets.env' against root /work/project
--------------------------------------------------------------------
  naive join      = /work/project/../secrets.env
    starts with '/work/project' ? True -> naive verdict: ALLOW (wrong!)
  resolved target = /work/secrets.env
    under '/work/project' ? False -> correct verdict: DENY (right)
```

The naive check performs a real, passing string test: /work/project/../secrets.env does start with /work/project, so `startswith` returns True and the guard allows the access. The check is not buggy in its own terms — it correctly evaluated the string prefix. It is asking the wrong question. "Does the path string start with the root?" is not the same question as "does the file this path refers to live under the root?", and the ".." is exactly the operator that pries those two questions apart: it lets a string that begins inside the root refer to a file outside it. Normalization closes the gap by turning the path into its canonical target — the actual location the OS would open — before the containment test, so the test is finally asking about the real file. This is the general lesson of path security: never make a trust decision on an unresolved path, because any path feature that means "somewhere else" (".." here, and symlinks in the boss fight) makes the surface string an unreliable witness to the real target.

<svg role="img" aria-label="A sandbox box labeled work/project containing notes.txt; the requested path enters the box then a dot-dot arrow walks back out and up to secrets.env, which sits outside the box" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the '..' walks the request back out of the sandbox box</text>
  <rect x="60" y="30" width="120" height="56" fill="none" stroke="var(--s1)"/>
  <text x="66" y="42" fill="var(--s1)" font-size="7">/work/project (sandbox)</text>
  <text x="72" y="66" fill="var(--muted)" font-size="7">notes.txt ✓</text>
  <circle cx="120" cy="76" r="3" fill="var(--s1)"/><text x="82" y="82" fill="var(--muted)" font-size="6">enters here</text>
  <path d="M120 76 L120 96 L250 96 L250 60" fill="none" stroke="var(--s2)"/>
  <text x="150" y="106" fill="var(--s2)" font-size="6">.. steps up and out →</text>
  <text x="220" y="52" fill="var(--s2)" font-size="7">secrets.env</text>
  <circle cx="250" cy="58" r="3" fill="var(--s2)"/>
  <text x="200" y="42" fill="var(--muted)" font-size="6">/work (outside)</text>
</svg>
^ The requested path enters the sandbox box, but its ".." segment walks back out and up to /work/secrets.env, which sits outside the /work/project boundary — the naive check watched only the entry point, not where the path finally lands.

```python filename=modules/agent-harness/code/pathjail-inter-01/pathjail.py:116-122 COMPLETE
    escapes = ["../secrets.env", "../../etc/passwd"]
    naive_allows_escape = all(naive_allows(root, p) for p in escapes)
    print("  naive check ALLOWS the escaping paths %s = %s" % (escapes, naive_allows_escape))

    correct_denies_escape = all(not correct_allows(root, p) for p in escapes)
    print("  correct check denies the escaping paths = %s (resolve to %s)"
          % (correct_denies_escape, [resolved_target(root, p) for p in escapes]))
```

## Definition of done

The self-test pins the naive escape, the correct denial, and — crucially — that the correct guard still allows the safe path that passes through a parent.

```python filename=modules/agent-harness/code/pathjail-inter-01/pathjail.py:124-131 COMPLETE
    safe_dotdot = "sub/../notes.txt"
    correct_allows_safe_dotdot = correct_allows(root, safe_dotdot)
    print("  correct check allows the safe '..' path %r = %s (resolves to %s)"
          % (safe_dotdot, correct_allows_safe_dotdot, resolved_target(root, safe_dotdot)))

    inside = ["notes.txt", "sub/data.csv"]
    both_allow_inside = all(naive_allows(root, p) and correct_allows(root, p) for p in inside)
    print("  both checks allow the plainly-inside paths %s = %s" % (inside, both_allow_inside))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the naive check allows sandbox escapes; the correct check allows exactly the paths that resolve inside
------------------------------------------------------------------------------------------------------------------
  naive check ALLOWS the escaping paths ['../secrets.env', '../../etc/passwd'] = True
  correct check denies the escaping paths = True (resolve to ['/work/secrets.env', '/etc/passwd'])
  correct check allows the safe '..' path 'sub/../notes.txt' = True (resolves to /work/project/notes.txt)
  both checks allow the plainly-inside paths ['notes.txt', 'sub/data.csv'] = True
  the two checks disagree on at least one path = True
```

<svg role="img" aria-label="A verdict table for four path kinds: plainly inside — both allow; safe dot-dot — both allow; traversal escape — naive allows but correct denies; absolute outside — both deny" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">correct = allow iff resolved target is inside; naive is fooled by '..'</text>
  <text x="130" y="28" fill="var(--muted)" font-size="6">naive</text><text x="210" y="28" fill="var(--muted)" font-size="6">correct</text>
  <text x="10" y="44" fill="var(--muted)" font-size="7">inside</text><text x="130" y="44" fill="var(--s1)" font-size="7">allow</text><text x="210" y="44" fill="var(--s1)" font-size="7">allow</text>
  <text x="10" y="62" fill="var(--muted)" font-size="7">safe ..</text><text x="130" y="62" fill="var(--s1)" font-size="7">allow</text><text x="210" y="62" fill="var(--s1)" font-size="7">allow</text>
  <text x="10" y="80" fill="var(--muted)" font-size="7">.. escape</text><text x="130" y="80" fill="var(--s2)" font-size="7">ALLOW ✗</text><text x="210" y="80" fill="var(--s1)" font-size="7">DENY ✓</text>
  <text x="10" y="98" fill="var(--muted)" font-size="7">absolute out</text><text x="130" y="98" fill="var(--s1)" font-size="7">deny</text><text x="210" y="98" fill="var(--s1)" font-size="7">deny</text>
  <line x1="120" y1="34" x2="120" y2="104" stroke="var(--grid)"/>
  <text x="10" y="112" fill="var(--muted)" font-size="6">the two disagree exactly on the traversal escape — the security hole</text>
</svg>
^ Across the four path kinds the two guards agree except on the traversal escape, where the naive guard wrongly allows and the correct guard denies — and the correct guard allows the safe ".." path, so it is not merely stricter, it is right in both directions.

**Done means the vulnerability and its fix are proven on real paths: the naive check allows "../secrets.env" and "../../etc/passwd" because their un-normalized joins start with the root, while the correct check resolves them to /work/secrets.env and /etc/passwd and denies both, and still allows "sub/../notes.txt" which resolves back inside — so a tool's path must be resolved (normalized) before the containment test, never string-matched raw.**

## Boss fight

Predict two ways this containment check is still incomplete, because normalizing the string is necessary but the real filesystem has more ways to point "somewhere else" than "..".

The first trap is symlinks — a normalized path can still resolve, at the OS level, to a target outside the root, because a symbolic link inside the sandbox can point anywhere. `normpath` collapses ".." lexically, but it does not follow links: if /work/project/data is a symlink to /etc, then "data/passwd" normalizes to /work/project/data/passwd, which passes the containment test, yet opening it reads /etc/passwd. Lexical normalization trusts the string; symlinks make the string lie about the real target. The robust fix resolves links too — `realpath` (or `os.path.realpath`, or opening with `O_NOFOLLOW` / `openat` with resolve flags) to get the fully-resolved physical path — and then tests containment on *that*. And even a fully-resolved check has a time-of-check-to-time-of-use race: if you resolve, approve, and then open as separate steps, an attacker who can create symlinks in the sandbox can swap a component between the check and the open. Truly hardened sandboxes therefore resolve and open atomically, or confine at the OS level (a chroot, a mount namespace, a container) rather than trusting any userspace path check. Lexical containment stops "..", but symlinks need physical resolution and the check-then-open gap needs care.

The second trap is that path normalization is platform- and encoding-dependent, so a check that is correct on one system is wrong on another. On Windows the separator is backslash, paths are case-insensitive (so a case-varied path can dodge a case-sensitive prefix test), and there are alternate forms — 8.3 short names, device paths like \\?\, trailing dots and spaces, drive-relative paths — that all resolve to files a naive normalizer misses; this module used posixpath precisely to keep the demo deterministic, but a real cross-platform guard must normalize in the target OS's rules, not assume POSIX. There are also Unicode tricks: two different byte sequences can normalize (via NFC/NFD) to the same filename on some filesystems, so a containment check comparing raw bytes can be evaded, and percent-encoding or overlong UTF-8 in a path that arrives from a URL adds another decode step that must happen *before* normalization, or the ".." reappears after you have already checked. The safe posture is to canonicalize completely — decode, Unicode-normalize, resolve links, apply the platform's own path semantics — before a single trust decision, and, wherever possible, to back the userspace check with an OS-level jail so a missed canonicalization is not a full escape.

**Lexical normalization stops "..", but the filesystem has other ways out: resolve symlinks to the physical target (realpath / O_NOFOLLOW) before checking, and close the check-then-open race by resolving and opening atomically or confining at the OS level (chroot, namespace, container); and canonicalize completely for the actual platform — decode any percent/UTF-8 encoding and Unicode-normalize first, honor Windows' case-insensitivity, separators, and device/short-name forms — because a containment check made on anything short of the fully-resolved physical path is a check on a string that can still be lying about the file.**

## External resources

The OWASP Path Traversal guidance and CWE-22 — the canonical description of the directory-traversal vulnerability, why un-resolved containment checks fail, and the canonicalize-then-validate remedy, all directly applicable to an agent's file-tool sandbox.

Documentation for `os.path.realpath`, `os.path.commonpath`, `pathlib.Path.resolve`, and `openat`/`O_NOFOLLOW` — the standard tools for resolving a path to its physical target and testing containment safely, plus the symlink and race caveats.

The companion tool-argument-validation and gate-irreversible-tools modules in this topic — path containment is argument validation specialized to the filesystem's trust boundary, and it pairs with confirmation gating for the writes and deletes a contained-but-powerful file tool can still perform inside the sandbox.
