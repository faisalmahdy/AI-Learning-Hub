"""A DELIBERATELY BROKEN kernel — same loop, one extra import. It runs perfectly;
the only thing that objects is guard.py. Kept committed so the failure is
reproducible; nothing imports this file at runtime."""
from seams import Msg
from impls import EchoProvider   # <- FORBIDDEN: the kernel now names a concrete provider


def run(provider, tools, task, max_steps=8):
    messages = [Msg("user", task)]
    if provider is None:                 # "convenience": default to a concrete provider
        provider = EchoProvider()
    for step in range(1, max_steps + 1):
        reply = provider.respond(messages)
        if reply.final is not None:
            return reply.final, step
        tool = tools.get(reply.tool)
        result = tool.run(reply.args) if tool else "ERROR: no tool " + reply.tool
        messages.append(Msg("assistant", "", tool=reply.tool, args=reply.args))
        messages.append(Msg("tool", result))
    return None, max_steps
