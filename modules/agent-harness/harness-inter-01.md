---
id: harness-inter-01
title: The kernel rule — an architecture test the compiler won't run for you
topic: agent-harness
level: intermediate
status: ready
eli5: The core of an agent must plug into a socket, never be soldered to one charger. Adding the solder still runs fine — only a little import-checker notices.
time: 8-10h
summary: Add one line to the agent kernel — import a concrete provider — and it runs byte-for-byte identically, passing every test; then a 40-line AST guard reads the imports, flags the forbidden one, and exits 1, because the damage was never a crash, it was a coupling only a reader can see.
---

## Why this module

harness-basic-01 built the loop and gave it two seams — a `Provider` and a `Tool` it only ever talked to through their interfaces. This module is about why that indirection is load-bearing, and how you keep it from rotting. The labs' harness is built on four abstract seams — provider, tool, sandbox, engine — and it enforces one rule the language cannot: the kernel may import only those abstractions and the standard library, never a concrete implementation. It backs the rule with a failing test, an AST scan that reads the kernel's imports. `CURRICULUM.md`'s Track 2.2 is exactly this: "break the kernel import rule on purpose, watch the test fail, and write up why the rule exists."

This module builds that guard at `intermediate`. A tiny package — the seams, the kernel loop, some concrete providers — plus the AST checker that guards the kernel, and a second kernel with the rule deliberately broken. What it omits: no package-walking, no CI wiring, no real providers — the check is a few lines and everything runs offline. You need harness-basic-01's loop and to know what an `import` statement is. Stdlib Python 3, offline, $0.00, under a second a run, one sitting. The hard part is one uncomfortable fact: the broken version works perfectly, and that is exactly why you need a guard.

By the end, one command tells two identical-behaving kernels apart. Skipping ahead:

```
# modules/agent-harness/code/harness-inter-01/ — COMPLETE, run from that directory
$ python3 guard.py --all

KERNEL IMPORT CHECK: kernel_loop.py
--------------------------------------------------------
  PASS — imports only stdlib and the seams

KERNEL IMPORT CHECK: kernel_loop_broken.py
--------------------------------------------------------
  FORBIDDEN import in the kernel: 'impls' (a concrete detail)
  FAIL — the kernel must not depend on a concrete implementation

both loops RUN identically; only the guard tells them apart:
assembled agent (echo + kernel): The answer is 15.  in 3 steps
```

run: 2026-08-22 · guard is a deterministic AST scan, no model call · `python3 guard.py --all`

Two kernels. One passes, one fails. And the last line is the whole point: both of them, wired to the same provider, return the same answer in the same three steps. Nothing you can *run* separates the good architecture from the bad one. This module is about the test that does, and why an agent harness lives or dies by it.

## Concepts

Named here so you can find them again; each is built, and one is broken, below.

- **Seam** — an abstract interface (an ABC): provider, tool, sandbox, engine. What the kernel depends on.
- **The kernel** — the loop, the core; it imports only seams and the standard library.
- **Dependency inversion** — the core depends on abstractions; the details depend on the core, never the reverse.
- **Composition** — wiring a concrete provider to the kernel, done outside the kernel.
- **The import guard** — an AST scan that reads a kernel file's imports and fails on a forbidden one.
- **Kernel coupling** — a concrete import inside the kernel. The planted break: it runs, and it rots the core.

## Worked example

Source: faisalmahdy/agent — `agent/providers/base.py` and the sibling tool/sandbox/engine base classes (the four seams), and `tools/check_stdlib_only.py` (the AST guard enforced in CI). De-personalized; the toy here is the same shape at a fraction of the size.

Script and fixtures: `modules/agent-harness/code/harness-inter-01/` — `guard.py` (114 lines), `seams.py`, `kernel_loop.py` (19 lines), a broken twin, and `impls.py` / `agent.py`. Every command runs from there.

### Install the frame: the kernel plugs into a socket, never a charger

In my opinion, the best way to think of a seam is as a wall socket, not a wire.

The kernel is an appliance's motor. A seam is the socket standard — a shape a plug must fit. A concrete provider is a particular power source: the wall grid, a generator, a test-bench battery. The rule is that the motor is wired to the *socket*, so any source that fits the plug can drive it. Solder the motor straight to the city grid instead and it runs today — but you can never run it off a generator, and you have dragged the grid's whole supply into the motor. The import guard is the electrical inspector: it does not test whether the appliance turns on, it checks that nothing got soldered past the socket.

Three jobs, one line each: the seam says "what shape must a provider be?", the kernel says "hand me any provider of that shape", and the guard says "did anyone solder a specific provider into the kernel?"

### The four seams, and the kernel that depends only on them

The seams are abstract base classes — a shape, no behavior. Four of them: the provider (a model), the tool (a capability), the sandbox (where side effects run), the engine (the loop itself, so even it can be swapped).

```
# seams.py:28-54 — COMPLETE (the four abstract seams; no concrete anything)
class Provider(ABC):
    """A model, behind one method. A real one calls an API; a fake one is scripted."""
    @abstractmethod
    def respond(self, messages):
        ...


class Tool(ABC):
    """A named capability the model can call."""
    name = "?"

    @abstractmethod
    def run(self, args):
        ...


class Sandbox(ABC):
    """Where a tool's side effects run — a subprocess, a container, a fake."""
    @abstractmethod
    def exec(self, command):
        ...


class Engine(ABC):
    """The loop itself, behind a seam, so it too can be swapped (e.g. for an SDK)."""
    @abstractmethod
    def drive(self, provider, tools, task):
        ...
```

<svg viewBox="0 0 680 220" role="img" aria-label="The kernel at the top depends on four abstract seams — provider, tool, sandbox, engine — drawn in a row below it; concrete implementations below each seam implement it, their arrows pointing up at the abstraction.">
  <g font-family="var(--mono)">
    <rect x="280" y="22" width="120" height="38" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect>
    <text x="340" y="45" font-size="11" text-anchor="middle" fill="var(--ink)">the kernel</text>
    <g font-size="10" text-anchor="middle">
      <rect x="34" y="104" width="130" height="34" rx="7" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="99" y="125" fill="var(--acc-ink)">Provider</text>
      <rect x="194" y="104" width="130" height="34" rx="7" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="259" y="125" fill="var(--acc-ink)">Tool</text>
      <rect x="356" y="104" width="130" height="34" rx="7" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="421" y="125" fill="var(--acc-ink)">Sandbox</text>
      <rect x="516" y="104" width="130" height="34" rx="7" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="581" y="125" fill="var(--acc-ink)">Engine</text>
    </g>
    <g stroke="var(--s1)" stroke-width="1.5" fill="none">
      <line x1="300" y1="60" x2="118" y2="104" marker-end="url(#s)"></line>
      <line x1="322" y1="60" x2="266" y2="104" marker-end="url(#s)"></line>
      <line x1="358" y1="60" x2="414" y2="104" marker-end="url(#s)"></line>
      <line x1="380" y1="60" x2="562" y2="104" marker-end="url(#s)"></line>
    </g>
    <text x="340" y="86" font-size="9" text-anchor="middle" fill="var(--muted)">depends only on these four shapes</text>
    <g font-size="9" text-anchor="middle" fill="var(--muted)">
      <rect x="34" y="176" width="130" height="30" rx="6" fill="var(--panel)" stroke="var(--grid)"></rect><text x="99" y="195">EchoProvider</text>
      <rect x="194" y="176" width="130" height="30" rx="6" fill="var(--panel)" stroke="var(--grid)"></rect><text x="259" y="195">AddTool</text>
      <rect x="356" y="176" width="130" height="30" rx="6" fill="var(--panel)" stroke="var(--grid)"></rect><text x="421" y="195">DockerSandbox</text>
      <rect x="516" y="176" width="130" height="30" rx="6" fill="var(--panel)" stroke="var(--grid)"></rect><text x="581" y="195">SdkEngine</text>
    </g>
    <g stroke="var(--line)" stroke-width="1.4" fill="none">
      <line x1="99" y1="176" x2="99" y2="142" marker-end="url(#s2)"></line>
      <line x1="259" y1="176" x2="259" y2="142" marker-end="url(#s2)"></line>
      <line x1="421" y1="176" x2="421" y2="142" marker-end="url(#s2)"></line>
      <line x1="581" y1="176" x2="581" y2="142" marker-end="url(#s2)"></line>
    </g>
    <defs>
      <marker id="s" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 z" fill="var(--s1)"></path></marker>
      <marker id="s2" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 z" fill="var(--line)"></path></marker>
    </defs>
  </g>
</svg>
^ The four seams the kernel depends on, and the concrete implementations that plug into each. Every arrow points at an abstraction, never away from one.

How to read this: the kernel touches only the middle row; the bottom row can be replaced wholesale — a real API provider, a container sandbox — without the kernel noticing.

The kernel is the loop from harness-basic-01, and here is its entire import list: `from seams import Msg`. Nothing else local. It receives its provider and tools as arguments, so it never has to *name* a concrete one.

```
# kernel_loop.py:1-19 — COMPLETE (the whole kernel; note the single local import)
from seams import Msg


def run(provider, tools, task, max_steps=8):
    """Drive whatever provider and tools it is handed. Returns (answer, steps)."""
    messages = [Msg("user", task)]
    for step in range(1, max_steps + 1):
        reply = provider.respond(messages)
        if reply.final is not None:
            return reply.final, step
        tool = tools.get(reply.tool)
        result = tool.run(reply.args) if tool else "ERROR: no tool " + reply.tool
        messages.append(Msg("assistant", "", tool=reply.tool, args=reply.args))
        messages.append(Msg("tool", result))
    return None, max_steps
```

This is called **dependency inversion**, and the acronym people wave at it — the "D" in SOLID — makes it sound like a doctrine. It is one arrow: the kernel points at the seam, and every concrete provider points at the seam too, so no arrow ever runs *from* the kernel *to* a detail. Read the import line and you have verified it: `seams` is the only thing the core knows.

<svg viewBox="0 0 680 210" role="img" aria-label="Two rows. Top: kernel and concrete both point their dependency arrows inward at the seam abstraction. Bottom, the broken case: the kernel's arrow points outward directly at the concrete provider.">
  <g font-family="var(--mono)">
    <text x="40" y="24" font-size="10.5" fill="var(--muted)">wired right — both depend on the abstraction</text>
    <rect x="40" y="44" width="120" height="40" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect><text x="100" y="68" font-size="11" text-anchor="middle" fill="var(--ink)">kernel</text>
    <rect x="280" y="44" width="120" height="40" rx="8" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="340" y="68" font-size="11" text-anchor="middle" fill="var(--acc-ink)">seam (ABC)</text>
    <rect x="520" y="44" width="120" height="40" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect><text x="580" y="68" font-size="11" text-anchor="middle" fill="var(--ink)">concrete</text>
    <line x1="160" y1="64" x2="278" y2="64" stroke="var(--s1)" stroke-width="1.8" marker-end="url(#g)"></line>
    <line x1="520" y1="64" x2="402" y2="64" stroke="var(--s1)" stroke-width="1.8" marker-end="url(#g)"></line>
    <text x="40" y="132" font-size="10.5" fill="var(--muted)">broken — kernel depends on a detail (inverted)</text>
    <rect x="40" y="150" width="120" height="40" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect><text x="100" y="174" font-size="11" text-anchor="middle" fill="var(--ink)">kernel</text>
    <rect x="280" y="150" width="120" height="40" rx="8" fill="var(--panel)" stroke="var(--acc)"></rect><text x="340" y="174" font-size="11" text-anchor="middle" fill="var(--acc-ink)">concrete</text>
    <line x1="160" y1="170" x2="278" y2="170" stroke="var(--acc)" stroke-width="1.8" marker-end="url(#gb)"></line>
    <defs>
      <marker id="g" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 z" fill="var(--s1)"></path></marker>
      <marker id="gb" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 z" fill="var(--acc)"></path></marker>
    </defs>
  </g>
</svg>
^ The rule as one arrow. Wired right, the kernel and the concrete both point at the seam. Broken, the kernel's arrow lands on the concrete — the dependency inverted.

How to read this: the failure signature is an arrow leaving the kernel box and landing on anything but a seam. Every other test in your suite is blind to arrow direction; this is the one thing to look at.

### Strategy #1 — trust that it runs. It does, and that is the trap.

Now the prediction — commit before the next section. Add one line to the kernel: `from impls import EchoProvider`, a concrete provider. Then run the assembled agent. What breaks? Write it down. Most people say "nothing, it is a harmless convenience import" — and they are right that it runs. The answer to *what it costs* is at the top of the next section.

Here is the break, the whole diff against the clean kernel:

```
# kernel_loop_broken.py:5 — DELTA against kernel_loop.py (one added import)
from impls import EchoProvider   # <- FORBIDDEN: the kernel now names a concrete provider
```

Run it. It returns the same answer as the clean kernel, in the same three steps:

```
# $ python3 -c "import kernel_loop_broken, impls; print(kernel_loop_broken.run(impls.EchoProvider(), {'add': impls.AddTool()}, 'x'))"
# ('The answer is 15.', 3)
```

run: 2026-08-22 · deterministic, no model call · `python3 -c "..."`

Byte for byte as correct as the clean kernel. Every functional test passes, the type checker is happy, `import` executed without complaint. Strategy #1 — "if it runs, the architecture is fine" — has no way to see the problem, because the problem is not behavior. It is that the kernel now *names* `impls`: to import the kernel you must import `impls`, which in the real harness drags in an API client and its network dependency; you can no longer test the kernel in isolation, and you can no longer swap the provider without editing the core. The damage is a coupling, and a coupling is not something you run into. It is something you read.

**A concrete import in the kernel is not a bug you can run into — it is a coupling you can only read.**

### Strategy #2 — read the imports. The guard that sees what running can't.

If the damage is in the imports, read the imports — without running the file. Python hands you its own parser: `ast.parse` turns source into a tree, and every `import` is a node you can walk to.

```
# guard.py:19-20, 28-50 — COMPLETE (the whole check: parse, collect, classify)
STDLIB = set(sys.stdlib_module_names)   # every stdlib top-level name, from Python itself
ALLOWED_LOCAL = {"seams"}               # the ONE local module the kernel may import


def imports_of(path):
    """Every top-level module name imported by the file, via its AST."""
    tree = ast.parse(open(path, encoding="utf-8").read(), path)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append(top_level(alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(top_level(node.module))
    return found


def classify(name):
    if name in STDLIB:
        return "stdlib"
    if name in ALLOWED_LOCAL:
        return "seam"
    return "FORBIDDEN"


def bad_imports(path):
    """The kernel rule: anything that is neither stdlib nor a seam is forbidden."""
    return [m for m in imports_of(path) if classify(m) == "FORBIDDEN"]
```

<svg viewBox="0 0 680 150" role="img" aria-label="A left-to-right pipeline: the broken kernel file is parsed to an AST, its import nodes are collected — seams and impls — and each is classified: seams is a seam, impls is forbidden, yielding a FAIL verdict, all without running the file.">
  <g font-family="var(--mono)">
    <text x="340" y="22" font-size="10.5" text-anchor="middle" fill="var(--muted)">the guard reads the file's imports without running it</text>
    <rect x="20" y="52" width="150" height="46" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect>
    <text x="95" y="72" font-size="9.5" text-anchor="middle" fill="var(--ink)">kernel_loop</text>
    <text x="95" y="86" font-size="9.5" text-anchor="middle" fill="var(--ink)">_broken.py</text>
    <line x1="170" y1="75" x2="210" y2="75" stroke="var(--line)" stroke-width="1.5" marker-end="url(#p)"></line>
    <rect x="212" y="52" width="132" height="46" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect>
    <text x="278" y="72" font-size="9.5" text-anchor="middle" fill="var(--muted)">ast.parse</text>
    <text x="278" y="86" font-size="9.5" text-anchor="middle" fill="var(--muted)">walk imports</text>
    <line x1="344" y1="75" x2="384" y2="75" stroke="var(--line)" stroke-width="1.5" marker-end="url(#p)"></line>
    <rect x="386" y="40" width="176" height="70" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect>
    <text x="402" y="66" font-size="10" fill="var(--muted)">seams</text><text x="546" y="66" font-size="10" text-anchor="end" fill="var(--s1)">seam</text>
    <text x="402" y="92" font-size="10" fill="var(--muted)">impls</text><text x="546" y="92" font-size="10" text-anchor="end" fill="var(--acc)">FORBIDDEN</text>
    <line x1="562" y1="75" x2="600" y2="75" stroke="var(--line)" stroke-width="1.5" marker-end="url(#p)"></line>
    <rect x="602" y="58" width="66" height="34" rx="8" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="635" y="80" font-size="11" text-anchor="middle" fill="var(--acc-ink)">FAIL</text>
    <defs><marker id="p" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 z" fill="var(--line)"></path></marker></defs>
  </g>
</svg>
^ The guard's pipeline: parse the kernel to a tree, collect its imports, classify each, and one forbidden name is a FAIL — all without importing the file.

How to read this: the whole check runs on the parse tree, so the file is never executed — a kernel that imports a network client is caught before it ever opens a socket.

Reading the symbols: an `import` statement is a node in the parse tree, so walking the tree and collecting the module names gives you every dependency the file *declares* — no execution, no side effects, no network. `STDLIB` comes from Python itself, `sys.stdlib_module_names`, so the allowlist is the standard library plus exactly one local name, `seams`. Point it at the two kernels:

```
# $ python3 guard.py --imports kernel_loop.py
#   seams          seam

# $ python3 guard.py --imports kernel_loop_broken.py
#   seams          seam
#   impls          FORBIDDEN
```

run: 2026-08-22 · deterministic AST scan · `python3 guard.py --imports ...`

The clean kernel imports one thing, a seam. The broken one imports a seam and `impls`, a concrete detail, flagged. Turn that into a pass/fail and the guard fails the broken kernel with the reason, and an exit code CI can act on:

```
# $ python3 guard.py --check kernel_loop_broken.py ; echo "exit=$?"
# KERNEL IMPORT CHECK: kernel_loop_broken.py
#   FORBIDDEN import in the kernel: 'impls' (a concrete detail)
#   FAIL — the kernel must not depend on a concrete implementation
# exit=1
```

run: 2026-08-22 · deterministic · `python3 guard.py --check kernel_loop_broken.py`

*"But hold on,"* you say, *"this is just a linter, and my code works."* Good question. Yes, it is a lint. No, "it works" is not a defense — it is the exact condition the guard exists for. The type checker proves the code is type-consistent and passes it; the tests prove it behaves and pass it; both are blind to the arrow direction, so the one automated thing that can catch an inverted dependency is a check that reads imports. Working code is not well-structured code, and nothing but this tells you the difference.

**The type checker proves your code is consistent; the guard proves your architecture is — different questions, and only one of them is automated for you by default.**

### The fix, and the running tally

The fix is not to delete the provider — the agent needs one — but to wire it in from *outside* the kernel. That is what `agent.py` does, and why the clean kernel never needed the import:

```
# agent.py — COMPLETE (composition lives here, outside the kernel)
from kernel_loop import run
from impls import EchoProvider, AddTool

answer, steps = run(EchoProvider(), {"add": AddTool()},
                    "What is 2 + 3, then add 10 to that?")
# assembled agent (echo + kernel): The answer is 15.  in 3 steps
```

The concrete provider and the kernel meet exactly once, in the composition file, where importing both is not only allowed but the whole job. The kernel stays ignorant of both.

| kernel file | forbidden imports | runs? | guard verdict |
|---|---|---|---|
| kernel_loop.py | 0 | yes → "The answer is 15." | PASS (exit 0) |
| kernel_loop_broken.py | 1 (`impls`) | yes → "The answer is 15." | FAIL (exit 1) |

The two rows differ in nothing you can run — same answer, same three steps — and everything you can read. And yet — the guard only knows the names on the allowlist; it cannot see a dependency smuggled in dynamically, which is the next seam in the armor.

### Bridge to the standard names

Nobody outside this module calls it a socket. The rule is **dependency inversion** (the D in SOLID) and the layout is a **hexagonal / ports-and-adapters** architecture — the seams are ports, the concrete providers adapters. The guard is a **fitness function** or an **architecture test**; tools like `import-linter` do this for real Python packages, and Santara's `check_stdlib_only.py` is the same AST walk with a package crawl and a CI hook. The abstract base classes are just Python's `abc`; the ellipsis body is a stated "no default".

### What we did not settle

The guard reads static imports only. A kernel that does `importlib.import_module("impls")` from a string, or reaches a concrete class through a registry, sneaks past — catching that needs either a runtime check or a ban on dynamic import in the kernel, and both are more than this module builds. The allowlist is also hand-kept: add a new legitimate seam module and you must add it to `ALLOWED_LOCAL`, or the guard cries wolf. And the four seams here are a shape, not a full contract — a real provider seam pins the message and reply formats too, which is its own module. If the "it runs, so why does the import matter" feeling has not fully dissolved, that is the honest sticking point, and the tally is the answer to keep: same behavior, opposite structure.

## Build

The pipeline in one paragraph: define your seams as abstract base classes; write the kernel to import only those and the standard library; put every concrete provider, tool, and sandbox outside the kernel and wire them in a composition file; then guard the kernel with an AST scan that fails the build on any forbidden import, and run it in CI.

We opened on one command that tells two identical-behaving kernels apart. The payoff block (again):

```
# modules/agent-harness/code/harness-inter-01/ — COMPLETE, run from that directory
$ python3 guard.py --all
  ...
  PASS — imports only stdlib and the seams
  ...
  FORBIDDEN import in the kernel: 'impls' (a concrete detail)
  FAIL — the kernel must not depend on a concrete implementation
  both loops RUN identically; only the guard tells them apart:
  assembled agent (echo + kernel): The answer is 15.  in 3 steps
```

Now point it at your own kernel. The one dial is `ALLOWED_LOCAL`: list the seam modules your kernel may import, and let the AST scan flag everything else. Mark which of your files are the kernel, run `guard.py --check` over each, and wire it into CI so a forbidden import fails the build, not the code review three weeks later.

Your number to beat is not a score — it is that a deliberately broken kernel **fails your guard while still passing every other test**. Add a concrete import to your kernel on purpose, confirm the suite stays green and the type checker stays quiet, then watch only the guard go red. If everything stays green, your guard is not reading the imports; fix the guard. Bring back the exit code. Good luck.

### FAQ

**Isn't this over-engineering a 19-line loop?** At this size, yes — you could hold the rule in your head. The guard earns its keep the moment the kernel is 384 lines and five people touch it; the labs enforce it precisely because a rule no test checks is a rule that decays.

**Why not let the type checker catch it?** Because there is nothing to catch: importing a concrete provider is perfectly well-typed. The violation is structural, and structure is not in the type system.

**The broken kernel ran fine — is the rule just taste?** No. Try to unit-test the broken kernel without a network, or swap the provider without editing the core, and the coupling bites. It runs today and costs you the day you need to test or swap — which for a harness is every day.

**Why is mine slow?** This isn't — it parses a few files. A real guard walking a large package is still milliseconds, because it reads ASTs and never imports the code it checks.

### Errata

Version one, dated 2026-08-22. The broken kernel adds a `provider = EchoProvider()` default alongside the import, to make the coupling look like the "convenience" it usually disguises itself as; the import alone is the violation, and the guard flags it whether or not the class is used. One soft spot left in: `sys.stdlib_module_names` is Python 3.10+, so the guard as written assumes a recent interpreter; older ones need a vendored stdlib list.

## Definition of done

- [ ] Seams defined as abstract base classes, and a kernel that imports only them plus stdlib
- [ ] Every concrete provider/tool/sandbox outside the kernel, wired in a composition file
- [ ] An AST guard that lists a kernel file's imports and fails on any that is not stdlib or a seam
- [ ] A deliberately broken kernel, committed, that the guard fails while the suite stays green
- [ ] `python3 guard.py --check <kernel>` exits 0 on the clean kernel and 1 on the broken one
- [ ] The guard wired into CI so a forbidden import fails the build
- [ ] A short written note — the one another person can follow — on why the rule exists
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. State the kernel import rule in one sentence, and the one arrow that dependency inversion is about.
2. The broken kernel runs identically to the clean one. Say what actually went wrong, and why no test or type checker catches it.
3. Explain how the guard finds a forbidden import without running the file, and the two AST node types it looks for.
4. Give the fix for a kernel that needs a provider but may not import one, and name where the wiring goes instead.
5. Your own run printed an exit code for the broken kernel's check. What was it, and what would a green result there have told you about your guard?

## External resources

- Alistair Cockburn, *Hexagonal architecture (Ports and Adapters)* — https://alistair.cockburn.us/hexagonal-architecture/ — my summary: the ports-and-adapters framing this module's seams implement; read it for why the core owns the interfaces and the adapters depend inward.
- `import-linter` documentation — https://import-linter.readthedocs.io/ — my summary: the production version of guard.py — declare layer and independence contracts over a real package and enforce them in CI; the AST walk is the same idea, industrialized.
- Robert C. Martin, *The Dependency Inversion Principle* — https://en.wikipedia.org/wiki/Dependency_inversion_principle — my summary: the "D" in SOLID stated plainly; the one line worth keeping is that abstractions must not depend on details, which is the arrow the guard checks.
