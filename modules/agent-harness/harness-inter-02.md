---
id: harness-inter-02
title: Govern the agent by the menu — an MCP server with no write tool
topic: agent-harness
level: intermediate
status: ready
eli5: The agent can hand in a deposit slip but was never given a key to the vault. It proposes; a different person approves; you can't call a tool that isn't on your menu.
time: 8-10h
summary: Build a tiny MCP client and a memory server that hands the agent a menu with 'propose' but no 'write' and no 'approve', so a proposed fact stays absent from the store until a separate reviewer commits it — then watch a one-line slip turn the governance into theater by writing the proposal through.
---

## Why this module

harness-inter-01 kept concrete details out of the kernel. This module keeps a dangerous *capability* out of the agent. The way an agent reaches the outside world is MCP — a client/server protocol where a server exposes a menu of tools and the agent (the client) calls them. The default move is to expose a `write` tool and trust the model; the labs' move, in second-brain's memory server and operator's gateway, is a governed surface where the agent can *propose* a change but the store only mutates when a different principal approves, deny-by-default. `CURRICULUM.md`'s Track 2.3 asks for exactly that: "one governed MCP server — no raw write; a proposal/review surface — with fake-transport tests."

This module builds it at `intermediate`. A minimal MCP client, a raw server that lists a `write` tool, and a governed server that does not — all over a fake in-memory transport, so it runs offline and deterministically. What it omits: no stdio pipes, no JSON-RPC wire format, no auth tokens — the governance idea is independent of all three. You need harness-inter-01's seams and to know what a dict is. Stdlib Python 3, offline, $0.00, under a second a run, one sitting. The hard part is one inversion of instinct: you do not make the write safe, you take the write away.

By the end, one command shows the agent unable to commit its own change. Skipping ahead:

```
# modules/agent-harness/code/harness-inter-02/ — COMPLETE, run from that directory
$ python3 mcp.py --governed

agent's menu   : ['get', 'propose', 'list_proposals']
reviewer's menu: ['get', 'list_proposals', 'approve', 'deny']
agent proposes memory[fact] = 'sky is green' ...
  proposal 1 staged (pending review)
store after propose (no approval yet): fact = (absent)
agent tries to approve its own proposal ...
  no tool 'approve' on the agent menu
reviewer approves proposal 1 ...
  approved 1 -> committed
store after approval: fact = sky is green
```

run: 2026-08-22 · in-memory transport, no model call · `python3 mcp.py --governed`

Read the two menus. The agent has `propose`; it does not have `write`, and it does not have `approve`. So it proposes a fact, and the store still reads `(absent)` — nothing changed. It tries to approve its own proposal and the server does not refuse so much as fail to understand: there is no such tool on its menu. Only the reviewer, a different principal with a different menu, can commit. This module is about why that shape — governance by menu, not by permission check — is the one that holds.

## Concepts

Named here so you can find them again; each is built, and one is broken, below.

- **MCP** — a client/server protocol: the client asks a server for its tool menu (`tools/list`) and calls them (`tools/call`).
- **The menu** — the tools a server lists for a given caller. Governance lives here.
- **Principal** — who the caller is (agent vs reviewer); it decides which menu they get.
- **Governed surface** — no `write`; the agent `propose`s, a reviewer `approve`s.
- **Proposer ≠ approver** — the agent cannot approve its own proposal, because `approve` is not on its menu.
- **Propose-through** — a proposal that writes to the store immediately. The planted bug: governance theater.

## Worked example

Source: faisalmahdy/agent — `agent/mcp/*` (a dependency-free stdio JSON-RPC client and its `tests/fake_mcp_server.py`) and faisalmahdy/second-brain-through-agents — `nusa-memory-mcp` (a governed proposal/review surface with no raw `memory.write`), plus operator's proposer-≠-checker gateway. De-personalized; the toy keeps the governance shape and drops the wire format.

Script and fixtures: `modules/agent-harness/code/harness-inter-02/` — `mcp.py`, 220 lines, no fixtures (the servers are the fixtures). Every command runs from there.

### Install the frame: the menu is the governance

In my opinion, the best way to think of a governed tool server is as a restaurant menu, not a locked door with a bouncer.

A bouncer on a locked door checks every person who reaches for the handle — and a check is code you can get wrong, forget on one path, or bypass. A menu is different: you cannot order what is not printed on it. The governed server hands the agent a menu with `propose` and no `write`; the agent could hallucinate a `write` call all day and the server would simply answer "that is not on your menu." The safety is not a guard that runs when the agent writes — it is that the agent has no way to name the write at all. A separate menu, handed only to the reviewer, is the one with `approve` on it.

Three jobs, one line each: the client says "what is on my menu?", the server says "here is your menu, and only these", and the store says "I change only when an `approve` is posted."

### The client and the transport

MCP is a request and a response. The client, bound to a principal, asks for its menu or calls a tool; the transport carries the request to the server. Ours is in-memory — the fake transport a real MCP test uses in place of a stdio pipe — so nothing here touches a network.

```
# mcp.py:25-49 — COMPLETE (the transport and the client; a real transport serializes over a pipe)
class Transport:
    """Stands in for stdio JSON-RPC: it just hands a request to the server with
    the caller's principal attached. A real one serializes over a pipe; the shape
    the client and server see is identical, which is why this fakes cleanly."""
    def __init__(self, server):
        self.server = server

    def send(self, principal, request):
        return self.server.handle(principal, request)


class Client:
    """Bound to one principal (who it is), talking to one transport."""
    def __init__(self, transport, principal):
        self.transport = transport
        self.principal = principal

    def menu(self):
        return self.transport.send(self.principal, {"method": "tools/list"})["tools"]

    def call(self, name, **args):
        return self.transport.send(
            self.principal, {"method": "tools/call", "name": name, "args": args})
```

### The server routes by the menu

The one rule that makes governance work is in the router: a `tools/call` is dispatched only if the tool is on the caller's menu. Everything else is which menu each principal gets.

```
# mcp.py:52-71 — COMPLETE (route a request, but only to tools on the caller's menu)
class Server:
    """Routes a request, but only to tools on the caller's menu."""
    def __init__(self):
        self.store = {}

    def menu(self, principal):
        raise NotImplementedError

    def dispatch(self, name, args, principal):
        raise NotImplementedError

    def handle(self, principal, request):
        if request["method"] == "tools/list":
            return {"tools": self.menu(principal)}
        if request["method"] == "tools/call":
            name = request["name"]
            if name not in self.menu(principal):
                return {"error": "no tool '%s' on the %s menu" % (name, principal)}
            return self.dispatch(name, request.get("args", {}), principal)
        return {"error": "unknown method"}
```

The check `name not in self.menu(principal)` is the whole enforcement, and notice what it is *not*: it is not a rule inside `write` about who may write. There is no `write`. The governed menu simply never lists it.

```
# mcp.py:94-116 — COMPLETE (the governed server: two menus, and the only write is in approve)
    def menu(self, principal):
        if principal == "reviewer":
            return ["get", "list_proposals", "approve", "deny"]
        return ["get", "propose", "list_proposals"]      # the agent's menu

    def dispatch(self, name, args, principal):
        if name == "get":
            return {"result": self.store.get(args["key"], "(absent)")}
        if name == "propose":
            pid = len(self.proposals) + 1
            self.proposals.append({"id": pid, "key": args["key"],
                                   "value": args["value"], "status": "pending"})
            return {"result": "proposal " + str(pid) + " staged (pending review)"}
        if name == "list_proposals":
            pending = [p for p in self.proposals if p["status"] == "pending"]
            return {"result": pending}
        if name == "approve":
            for p in self.proposals:
                if p["id"] == args["id"] and p["status"] == "pending":
                    self.store[p["key"]] = p["value"]     # the ONLY write in the file
                    p["status"] = "approved"
                    return {"result": "approved " + str(p["id"]) + " -> committed"}
            return {"error": "no pending proposal " + str(args["id"])}
```

<svg viewBox="0 0 680 220" role="img" aria-label="Two tool menus side by side. The agent's menu lists get, propose, list_proposals, with write and approve shown struck through as not listed. The reviewer's menu lists get, list_proposals, approve, deny.">
  <g font-family="var(--mono)">
    <text x="180" y="24" font-size="11" text-anchor="middle" fill="var(--ink)">AGENT menu</text>
    <text x="500" y="24" font-size="11" text-anchor="middle" fill="var(--ink)">REVIEWER menu</text>
    <rect x="40" y="34" width="280" height="172" rx="10" fill="var(--panel)" stroke="var(--grid)"></rect>
    <rect x="360" y="34" width="280" height="172" rx="10" fill="var(--panel)" stroke="var(--grid)"></rect>
    <g font-size="12">
      <text x="64" y="66" fill="var(--ink)">get</text>
      <text x="64" y="92" fill="var(--acc-ink)">propose</text>
      <text x="64" y="118" fill="var(--ink)">list_proposals</text>
      <text x="64" y="150" fill="var(--muted)" text-decoration="line-through">write</text>
      <text x="150" y="150" font-size="9" fill="var(--acc)">not on the menu</text>
      <text x="64" y="176" fill="var(--muted)" text-decoration="line-through">approve</text>
      <text x="150" y="176" font-size="9" fill="var(--acc)">not on the menu</text>
      <text x="384" y="66" fill="var(--ink)">get</text>
      <text x="384" y="92" fill="var(--ink)">list_proposals</text>
      <text x="384" y="118" fill="var(--acc-ink)">approve</text>
      <text x="384" y="144" fill="var(--ink)">deny</text>
    </g>
  </g>
</svg>
^ The two menus the server hands out. The agent's has no `write` and no `approve`; the reviewer's is the only one with `approve`.

How to read this: the safety is what is *missing* from the left column, not a rule guarding it. The failure signature is a `write` or `approve` appearing on the agent's menu — then the governance is gone whatever the code says.

### Strategy #1 — the raw server. One call, and memory is whatever the model said.

The default is a server that lists `write`. Then the agent's menu is `['get', 'write']`, and the store is whatever the model last called:

```
# $ python3 mcp.py --raw
#   agent's menu: ['get', 'write']
#   agent calls write(api_key='leaked') ...
#   store now says api_key = leaked
#   -> one call, memory mutated. The write tool was on the menu.
```

run: 2026-08-22 · in-memory transport, no model call · `python3 mcp.py --raw`

That is the whole risk in one line: a single tool call, from a model that can be prompted, confused, or hijacked, and the store is mutated with no second pair of eyes.

<svg viewBox="0 0 680 160" role="img" aria-label="Two paths from the agent to the store. Raw: the agent calls write and the store changes directly, no gate. Governed: the agent calls propose, which stops at a review gate, and only a reviewer's approve continues to the store.">
  <g font-family="var(--mono)">
    <text x="40" y="28" font-size="10.5" fill="var(--muted)">raw — the agent reaches the store directly</text>
    <rect x="40" y="38" width="90" height="32" rx="7" fill="var(--panel)" stroke="var(--grid)"></rect><text x="85" y="58" font-size="10" text-anchor="middle" fill="var(--ink)">agent</text>
    <line x1="130" y1="54" x2="250" y2="54" stroke="var(--acc)" stroke-width="1.8" marker-end="url(#r)"></line>
    <text x="190" y="46" font-size="9" text-anchor="middle" fill="var(--acc)">write</text>
    <rect x="252" y="38" width="90" height="32" rx="7" fill="var(--panel)" stroke="var(--grid)"></rect><text x="297" y="58" font-size="10" text-anchor="middle" fill="var(--ink)">store</text>
    <text x="40" y="106" font-size="10.5" fill="var(--muted)">governed — a review gate stands between them</text>
    <rect x="40" y="116" width="90" height="32" rx="7" fill="var(--panel)" stroke="var(--grid)"></rect><text x="85" y="136" font-size="10" text-anchor="middle" fill="var(--ink)">agent</text>
    <line x1="130" y1="132" x2="240" y2="132" stroke="var(--line)" stroke-width="1.5" marker-end="url(#r2)"></line>
    <text x="185" y="124" font-size="9" text-anchor="middle" fill="var(--muted)">propose</text>
    <rect x="242" y="114" width="120" height="36" rx="7" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="302" y="130" font-size="9.5" text-anchor="middle" fill="var(--acc-ink)">review gate</text><text x="302" y="143" font-size="8" text-anchor="middle" fill="var(--acc-ink)">reviewer only</text>
    <line x1="362" y1="132" x2="472" y2="132" stroke="var(--s1)" stroke-width="1.6" marker-end="url(#rs)"></line>
    <text x="417" y="124" font-size="9" text-anchor="middle" fill="var(--s1)">approve</text>
    <rect x="474" y="116" width="90" height="32" rx="7" fill="var(--panel)" stroke="var(--grid)"></rect><text x="519" y="136" font-size="10" text-anchor="middle" fill="var(--ink)">store</text>
    <defs>
      <marker id="r" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 z" fill="var(--acc)"></path></marker>
      <marker id="r2" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 z" fill="var(--line)"></path></marker>
      <marker id="rs" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 z" fill="var(--s1)"></path></marker>
    </defs>
  </g>
</svg>
^ Two paths to the store. Raw: the agent's write lands directly. Governed: the agent's propose stops at a gate only the reviewer can pass.

How to read this: count the boxes between the agent and the store — raw has none, governed has a gate the agent's menu cannot reach.

Now the prediction — commit before the next section. On the *governed* server the agent has no `write`. So when it needs to save a fact, it calls `propose` — and after that call, is the fact in the store, waiting to be "confirmed", or not there at all? Write it down. Most people expect it staged-but-present. The answer is at the top of the next section.

### Strategy #2 — the governed server. The agent cannot commit its own change.

The answer is at the top of `--governed`, and it is: not there at all. `store after propose ... fact = (absent)`. The proposal is recorded, the store is untouched, and the agent's attempt to approve its own proposal returns `no tool 'approve' on the agent menu`. Only the reviewer's `approve` runs the one `self.store[...] = ...` in the whole file.

<svg viewBox="0 0 680 210" role="img" aria-label="A two-lane flow. In the agent lane, propose creates a pending proposal but the store stays absent. In the reviewer lane, approve commits the proposal into the store. The only arrow that reaches the store comes from the reviewer.">
  <g font-family="var(--mono)">
    <text x="40" y="40" font-size="10" fill="var(--muted)">agent (proposer)</text>
    <rect x="40" y="50" width="120" height="36" rx="7" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="100" y="72" font-size="10.5" text-anchor="middle" fill="var(--acc-ink)">propose(fact)</text>
    <line x1="160" y1="68" x2="248" y2="68" stroke="var(--line)" stroke-width="1.5" marker-end="url(#m)"></line>
    <rect x="250" y="50" width="150" height="36" rx="7" fill="var(--panel)" stroke="var(--grid)"></rect><text x="325" y="72" font-size="10" text-anchor="middle" fill="var(--muted)">proposal #1 pending</text>
    <rect x="470" y="86" width="170" height="40" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect><text x="555" y="103" font-size="10.5" text-anchor="middle" fill="var(--ink)">the store</text><text x="555" y="118" font-size="9" text-anchor="middle" fill="var(--muted)">unchanged until approve</text>
    <text x="40" y="160" font-size="10" fill="var(--muted)">reviewer (approver)</text>
    <rect x="40" y="170" width="120" height="34" rx="7" fill="var(--panel)" stroke="var(--grid)"></rect><text x="100" y="191" font-size="10.5" text-anchor="middle" fill="var(--ink)">approve(1)</text>
    <path d="M250 78 q40 30 75 40" fill="none" stroke="var(--line)" stroke-width="1.3" stroke-dasharray="3 3"></path>
    <path d="M160 187 q200 0 310 -70" fill="none" stroke="var(--s1)" stroke-width="1.8" marker-end="url(#ms)"></path>
    <text x="360" y="150" font-size="9" text-anchor="middle" fill="var(--s1)">the only path to the store</text>
    <defs>
      <marker id="m" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 z" fill="var(--line)"></path></marker>
      <marker id="ms" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 z" fill="var(--s1)"></path></marker>
    </defs>
  </g>
</svg>
^ The proposer stages; the store does not move. The only arrow that reaches the store is the reviewer's `approve`.

How to read this: two lanes, two principals, and a single path into the store — from the reviewer, never the agent. If a second arrow ever reaches the store from the agent lane, governance is broken, which is the next section.

**You do not make the write safe. You make the write unnameable — it is not a tool the agent has.**

### The planted bug: a proposal that writes through

Governance this clean is one line from theater. Here is a governed server whose `propose` stages the proposal *and* writes it straight to the store:

```
# mcp.py:125-132 — COMPLETE (the bug: propose writes through before anyone approves)
class BrokenGovernedServer(GovernedServer):
    """THE BUG: propose stages a proposal AND writes it through immediately, so
    the review surface is theater — the store changed before anyone approved."""
    def dispatch(self, name, args, principal):
        if name == "propose":
            self.store[args["key"]] = args["value"]        # <- writes through, ungoverned
            return super().dispatch(name, args, principal)
        return super().dispatch(name, args, principal)
```

Stop here. Run it and the menus are identical, the proposal is staged, the reviewer still approves at the end — every visible step of the governed flow happens. So why is it broken? Because the store changed at `propose`, before the review:

```
# $ python3 mcp.py --bug
#   agent proposes memory[fact] = 'sky is green' ...
#     proposal 1 staged (pending review)
#   store after propose (no approval yet): fact = sky is green
#   ...
```

run: 2026-08-22 · in-memory transport, no model call · `python3 mcp.py --bug`

`fact = sky is green`, with zero approvals. The correct server printed `(absent)` at this exact line. The bug is invisible in the demo's shape — the proposal list, the reviewer, the "approved -> committed" message all still appear — which is why it is dangerous: the governance *looks* present while the agent's word has already become truth. Named: **propose-through**. It hides because the review UI is untouched; only a test that reads the store *between* propose and approve catches it. The one-line assertion: after a propose and before any approve, the store must be unchanged. `--check` runs it:

```
# $ python3 mcp.py --check
#   governed run twice, identical = True
#   governed: after propose, get returns '(absent)', store has '(absent)'
#   broken:   after propose, get returns 'v', store has 'v'
#   agent menu = ['get', 'propose', 'list_proposals'] -> no write, no approve = True
# SELF-TEST PASS  (deterministic, governed holds, bug detectable, menu clean)
```

run: 2026-08-22 · in-memory transport, deterministic · `python3 mcp.py --check`

The governed store is `(absent)` after propose; the broken one already holds `v`; the agent's menu has neither `write` nor `approve`; and two runs are identical because the fake transport has no clock and no network. That determinism is the reason a real MCP suite ships a fake server — you test the governance, not the pipe.

### The three servers, side by side

| server | agent's menu | store after `propose`/`write` | who can commit |
|---|---|---|---|
| raw | get, **write** | mutated immediately | the agent itself |
| governed | get, propose | `(absent)` — unchanged | the reviewer only |
| broken governed | get, propose | `sky is green` — written through | nominally reviewer, really the agent |

The raw and broken rows end in the same place — the agent's word is law — by opposite routes: the raw server admits it with a `write` tool, the broken one hides it behind a review surface that does nothing. And yet — even the correct server trusts that the reviewer is a different principal, which the transport here asserts but a real deployment must actually authenticate.

**A review surface you do not test between propose and approve is decoration; the store's state in that gap is the only thing that proves governance.**

### Bridge to the standard names

Nobody outside this module calls it a menu. It is **MCP** — Model Context Protocol — and `tools/list` / `tools/call` are its real method names; the fake `Transport` stands in for a stdio or HTTP one. The two-principal shape is **proposer-≠-approver** or **separation of duties**, and starting from an empty menu is **deny-by-default** and **least privilege** — the store grants nothing until a capability is added. second-brain's memory server calls the staged records a proposal queue with a curator; operator calls the reviewer a gateway with an owner gate. All of it is one idea: the dangerous verb belongs to a different principal than the one you do not fully trust.

### What we did not settle

The reviewer here is a string, `"reviewer"`, and the transport simply believes the client's principal — a real server authenticates it, or the whole scheme is a costume. We also never rate-limit proposals or bound the queue, so a stuck agent can flood the reviewer; and `approve` here is all-or-nothing, where a real surface shows a diff and lets the reviewer edit. The point the module makes is narrower and solid: the write is off the agent's menu, and the store proves it. If the "but a check inside write could do the same" itch remains, that is the honest disagreement — a check can, until the day someone adds a second write path and forgets the check; a missing tool has no second path.

## Build

The pipeline in one paragraph: give each principal a menu; route a tool call only if it is on the caller's menu; expose `propose` to the agent and `approve` to the reviewer, with the store's single write living inside `approve`; then test the store's state in the gap between propose and approve, over a fake transport, with no network.

We opened on the agent unable to commit its own change. The payoff block (again):

```
# modules/agent-harness/code/harness-inter-02/ — COMPLETE, run from that directory
$ python3 mcp.py --governed
  agent's menu   : ['get', 'propose', 'list_proposals']
  store after propose (no approval yet): fact = (absent)
  agent tries to approve its own proposal ...
    no tool 'approve' on the agent menu
  reviewer approves proposal 1 ...
  store after approval: fact = sky is green
```

Now govern your own server. The one dial is `menu(principal)`: decide, per principal, exactly which tools appear — and put every mutating verb on a menu the untrusted agent never sees. Move each raw `write` behind a `propose`/`approve` pair, and keep the store's only assignment inside `approve`.

Your number to beat is not a score — it is the store's value **in the gap**: after the agent proposes and before anyone approves, `get` must return `(absent)`. Add the propose-through bug on purpose and confirm your test goes red while the demo still looks governed; if the demo passing is enough to fool your suite, your suite is testing the menu, not the store. Bring back the assertion. Good luck.

### FAQ

**Why not just check the agent's identity inside `write`?** Because a check is one code path you can forget on the next `write` someone adds; a missing tool has no path to forget. Least privilege beats a guard you have to remember.

**Isn't propose/approve just slower?** For low-stakes writes, yes, and you would not bother. For memory an agent will later treat as truth, the reviewer is the difference between one bad tool call and a corrupted knowledge base.

**Can the agent flood the reviewer with proposals?** Yes — this toy does not rate-limit, and a real one must. Governance stops the agent from committing; it does not stop it from being annoying.

**Why is mine slow?** This isn't — it is dicts and an in-memory transport. A real MCP server is slow at the pipe and the model, which is exactly why you test the governance behind a fake transport first.

### Errata

Version one, dated 2026-08-22. The broken server keeps a `super().dispatch` call after writing through, so the proposal is *also* staged — that is deliberate, because the realistic bug is not "propose does the wrong thing" but "propose does the right thing plus one extra line", which is how it survives review. One soft spot left in: the transport trusts the principal string it is handed, so this module demonstrates the shape of governance and explicitly not its authentication.

## Definition of done

- [ ] An MCP-style client and server over a fake in-memory transport, no network
- [ ] Per-principal menus, and a router that dispatches only tools on the caller's menu
- [ ] A governed surface: the agent has `propose`, not `write` and not `approve`; the store's only write is inside `approve`
- [ ] A raw server kept for contrast, so the danger of a listed `write` is visible
- [ ] A test that reads the store in the gap between propose and approve and requires `(absent)`
- [ ] A committed propose-through bug that fails that test while the demo still looks governed
- [ ] `python3 mcp.py --check` printing SELF-TEST PASS
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. State the difference between governing a write with a permission check and governing it by the menu, and which one this module argues for and why.
2. The agent proposes a fact. Say what is in the store immediately after, and what the agent gets if it calls `approve`.
3. Name the two principals and the one tool that separates them, and why the agent literally cannot commit its own proposal.
4. The propose-through bug leaves every visible step of the governed flow intact. Say what it changed, and the one assertion that catches it.
5. Your own run printed the store's value right after a propose on the governed server. What was it, and what did the broken server print at the same line?

## External resources

- Model Context Protocol specification — https://modelcontextprotocol.io/ — my summary: the real `tools/list` / `tools/call` methods and transports this module miniaturizes; read the tools section and notice the protocol says nothing about governance — that is yours to design.
- Saltzer & Schroeder, *The Protection of Information in Computer Systems* (least privilege, separation of duties) — https://www.cs.virginia.edu/~evans/cs551/saltzer/ — my summary: the 1975 source of "least privilege" and "separation of privilege"; the propose/approve split is separation of duties, fifty years old and still the answer.
- Anthropic, MCP documentation — https://docs.claude.com/en/docs/agents-and-tools/mcp — my summary: how a client discovers and calls MCP servers in practice; read against the corpus-bias rule as the vendor's client-side view of the same protocol.
