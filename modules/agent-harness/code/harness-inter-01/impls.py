"""Concrete implementations of the seams. These live OUTSIDE the kernel: they may
import whatever they need (an API client, a container SDK), because the guard
only constrains the kernel."""
from seams import Provider, Reply, Tool


class AddTool(Tool):
    name = "add"

    def run(self, args):
        return str(args["a"] + args["b"])


class EchoProvider(Provider):
    """A scripted stand-in for a model doing '2+3, then add 10'."""
    def respond(self, messages):
        results = [m for m in messages if m.role == "tool"]
        if len(results) == 0:
            return Reply(tool="add", args={"a": 2, "b": 3})
        if len(results) == 1:
            return Reply(tool="add", args={"a": int(results[-1].content), "b": 10})
        return Reply(final="The answer is " + results[-1].content + ".")
