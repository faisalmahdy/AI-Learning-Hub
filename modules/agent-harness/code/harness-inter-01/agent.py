"""Composition — OUTSIDE the kernel. This is the only place a concrete provider
and the kernel loop meet: they are wired together here, so the kernel stays
ignorant of both. Run it to see the assembled agent work."""
from kernel_loop import run
from impls import EchoProvider, AddTool


def main():
    answer, steps = run(EchoProvider(), {"add": AddTool()},
                        "What is 2 + 3, then add 10 to that?")
    print("assembled agent (echo + kernel): %s  in %d steps" % (answer, steps))


if __name__ == "__main__":
    main()
