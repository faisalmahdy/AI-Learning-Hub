#!/usr/bin/env python3
"""A tiny MCP client and two servers — one that hands the agent a write tool, and
one that governs by never listing it.

MCP is a client/server protocol: the client asks a server for its menu of tools
(tools/list) and calls them (tools/call). Governance is not a check inside the
write; it is the menu the server hands each caller. The agent's menu has
'propose'; it has no 'write' and no 'approve'. You cannot call what is not on
your menu, so the store changes only when a separate reviewer approves.

  --raw        the agent uses a server that lists 'write': one call mutates memory
  --governed   the agent proposes; the store stays empty until a reviewer approves
  --bug        a governed server whose propose writes through (governance theater)
  --check      fake transport is deterministic; the governance property holds

Stdlib only. No network, no subprocess — the transport is in-memory (the fake
transport a real MCP test uses in place of stdio). Deterministic.
"""
import argparse
import sys


# ------------------------------------------------------------- the transport

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


# ---------------------------------------------------------------- the servers

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


class RawServer(Server):
    """Hands the agent a write tool. Whatever the model calls, the store obeys."""
    def menu(self, principal):
        return ["get", "write"]

    def dispatch(self, name, args, principal):
        if name == "get":
            return {"result": self.store.get(args["key"], "(absent)")}
        if name == "write":
            self.store[args["key"]] = args["value"]
            return {"result": "wrote " + args["key"]}


class GovernedServer(Server):
    """No write tool exists for the agent. It proposes; a reviewer approves; only
    then does the store change. proposer != approver, by menu."""
    def __init__(self):
        super().__init__()
        self.proposals = []

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
        if name == "deny":
            for p in self.proposals:
                if p["id"] == args["id"]:
                    p["status"] = "denied"
                    return {"result": "denied " + str(p["id"])}
            return {"error": "no proposal " + str(args["id"])}


class BrokenGovernedServer(GovernedServer):
    """THE BUG: propose stages a proposal AND writes it through immediately, so
    the review surface is theater — the store changed before anyone approved."""
    def dispatch(self, name, args, principal):
        if name == "propose":
            self.store[args["key"]] = args["value"]        # <- writes through, ungoverned
            return super().dispatch(name, args, principal)
        return super().dispatch(name, args, principal)


# ------------------------------------------------------------------- scenarios

def raw_demo():
    agent = Client(Transport(RawServer()), "agent")
    print("agent's menu: %s" % agent.menu())
    print("agent calls write(api_key='leaked') ...")
    agent.call("write", key="api_key", value="leaked")
    print("store now says api_key = %s" % agent.call("get", key="api_key")["result"])
    print("-> one call, memory mutated. The write tool was on the menu.")


def governed_demo(server_cls=GovernedServer):
    server = server_cls()
    agent = Client(Transport(server), "agent")
    reviewer = Client(Transport(server), "reviewer")
    print("agent's menu   : %s" % agent.menu())
    print("reviewer's menu: %s" % reviewer.menu())
    print("agent proposes memory[fact] = 'sky is green' ...")
    print("  %s" % agent.call("propose", key="fact", value="sky is green")["result"])
    print("store after propose (no approval yet): fact = %s"
          % agent.call("get", key="fact")["result"])
    print("agent tries to approve its own proposal ...")
    print("  %s" % agent.call("approve", id=1).get("error", "approved (should not happen)"))
    print("reviewer approves proposal 1 ...")
    print("  %s" % reviewer.call("approve", id=1)["result"])
    print("store after approval: fact = %s" % agent.call("get", key="fact")["result"])


def check():
    print("SELF-TEST — the transport is deterministic and governance holds")
    print("-" * 62)
    # determinism: same calls, same answers, twice.
    def scripted(cls):
        s = cls()
        a = Client(Transport(s), "agent")
        a.call("propose", key="k", value="v")
        return a.call("get", key="k")["result"], s.store.get("k", "(absent)")
    r1 = scripted(GovernedServer)
    r2 = scripted(GovernedServer)
    print("  governed run twice, identical = %s" % (r1 == r2))

    # governance: after propose, before approve, the store is unchanged.
    got_before, store_before = scripted(GovernedServer)
    print("  governed: after propose, get returns %r, store has %r" % (got_before, store_before))
    governed_ok = got_before == "(absent)" and store_before == "(absent)"

    # the bug: propose wrote through.
    got_bug, store_bug = scripted(BrokenGovernedServer)
    print("  broken:   after propose, get returns %r, store has %r" % (got_bug, store_bug))
    bug_shows = store_bug == "v"

    # capability removal: the agent's menu has neither write nor approve.
    agent_menu = Client(Transport(GovernedServer()), "agent").menu()
    no_write = "write" not in agent_menu and "approve" not in agent_menu
    print("  agent menu = %s -> no write, no approve = %s" % (agent_menu, no_write))

    ok = (r1 == r2) and governed_ok and bug_shows and no_write
    print("-" * 62)
    print("SELF-TEST %s  (deterministic, governed holds, bug detectable, menu clean)"
          % ("PASS" if ok else "FAIL"))
    return ok


def main():
    p = argparse.ArgumentParser(description="A governed MCP server, over a fake transport.")
    for flag in ("raw", "governed", "bug", "check"):
        p.add_argument("--" + flag, action="store_true")
    args = p.parse_args()

    if args.check:
        return 0 if check() else 1
    if args.raw:
        raw_demo()
    elif args.governed:
        governed_demo(GovernedServer)
    elif args.bug:
        print("(governed server with the propose-through bug)")
        governed_demo(BrokenGovernedServer)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
