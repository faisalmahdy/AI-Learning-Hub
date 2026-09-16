"""Reuse the connection (keep-alive) -- opening a fresh TCP+TLS connection per request pays the handshake every time.

Before a client can send a single byte of a request to a server, the connection between them has to be established, and
establishing it is not free: a TCP three-way handshake, and then -- for anything over HTTPS -- a TLS handshake to negotiate
encryption. Together that is several network round-trips of pure setup, paid before the actual request even starts, plus
CPU on both ends for the TLS cryptography. For ONE request that overhead is unavoidable. The waste appears when a client
makes MANY requests to the same server and opens a NEW connection for each one: every request repeats the entire handshake,
so the client pays the setup cost over and over for a server it is already talking to. On a burst of ten requests, that is
ten handshakes when one would do.

Connection reuse -- HTTP keep-alive, and the connection POOLING that libraries build on it -- fixes this by keeping the
connection open after a response and sending the next request over the SAME connection. The handshake is paid once, when the
connection is first established, and then every subsequent request skips straight to the request/response exchange. The
per-request cost drops from 'handshake + request' to just 'request,' so the total for N requests falls from N handshakes to
one. The savings grow with the number of requests: the more you talk to a server, the more the one-time setup is amortized,
and the fixed handshake cost becomes negligible against the stream of requests.

The stakes are both latency and load. Latency: every avoided handshake is round-trips removed from the critical path, which
on a high-latency link (a distant server, a mobile network) dominates the time of a small request. Load: TLS handshakes are
CPU-expensive on the server, so a client that reconnects per request multiplies the server's cryptographic work and can
exhaust its connection-accept capacity -- a self-inflicted load amplifier that looks like the server being slow. Reusing
connections is one of the highest-leverage, lowest-effort performance wins there is, which is why keep-alive is the default
in HTTP and why every serious HTTP client pools connections; opening a fresh connection per request is the anti-pattern.

The rule: reuse connections (keep-alive / a connection pool) for repeated requests to the same server, because establishing
a connection costs a TCP + TLS handshake of several round-trips (and server CPU) that is paid ONCE per connection -- so a new
connection per request repeats that handshake N times, while a reused connection pays it once and amortizes it over all the
requests.

On this fixture 10 requests are made, each handshake costs 3 round-trips and each request 1. Without keep-alive the total is
10 * (3 + 1) = 40 round-trips and 10 handshakes. With keep-alive it is 3 + 10 * 1 = 13 round-trips and 1 handshake. This
computes both.

  --latency     total round-trips without keep-alive (a handshake per request) vs with keep-alive (one handshake), and per-request
  --handshakes  the handshake count and the per-request handshake tax each way, and how the saving grows with request count
  --check       a new connection per request repeats the handshake N times; keep-alive pays it once and amortizes it

num_requests, handshake_round_trips, and request_round_trips are the fixture; every total, count, and saving is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "keepalive.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def total_without_keepalive(n, handshake, request):
    """A fresh connection per request: every request pays handshake + request."""
    return n * (handshake + request)


def total_with_keepalive(n, handshake, request):
    """One reused connection: pay the handshake once, then request per request."""
    return handshake + n * request


def handshakes_without(n):
    return n


def handshakes_with(n):
    return 1


# ----------------------------------------------------------------- printing

def latency_view(data):
    n, h, r = data["num_requests"], data["handshake_round_trips"], data["request_round_trips"]
    wo = total_without_keepalive(n, h, r)
    wk = total_with_keepalive(n, h, r)
    print("LATENCY — total round-trips for %d requests (handshake %d, request %d)" % (n, h, r))
    print("-" * 66)
    print("  no keep-alive: %d x (%d + %d) = %d round-trips  (handshake every request)" % (n, h, r, wo))
    print("  keep-alive:    %d + %d x %d   = %d round-trips  (handshake once)" % (h, n, r, wk))
    print("-" * 66)
    print("  keep-alive saves %d round-trips (%.0f%%) on this burst." % (wo - wk, (wo - wk) / wo * 100))


def handshakes_view(data):
    n, h, r = data["num_requests"], data["handshake_round_trips"], data["request_round_trips"]
    print("HANDSHAKES — how many times the handshake is paid, and the per-request tax")
    print("-" * 62)
    print("  no keep-alive: %d handshakes  (%d round-trips of setup, %d per request)" % (handshakes_without(n), handshakes_without(n) * h, h))
    print("  keep-alive:    %d handshake   (%d round-trips of setup, %.1f per request)" % (handshakes_with(n), handshakes_with(n) * h, h / n))
    print("-" * 62)
    for k in (1, 5, 10, 100):
        saved = total_without_keepalive(k, h, r) - total_with_keepalive(k, h, r)
        print("    at %-3d requests, keep-alive saves %d round-trips" % (k, saved))
    print("  the saving is (N-1) x handshake -- it grows with every extra request.")


def check(data):
    print("SELF-TEST — a new connection per request repeats the handshake N times; keep-alive pays it once and amortizes it")
    print("-" * 116)
    n, h, r = data["num_requests"], data["handshake_round_trips"], data["request_round_trips"]
    wo = total_without_keepalive(n, h, r)
    wk = total_with_keepalive(n, h, r)

    without_pays_per_request = wo == n * (h + r)
    print("  without keep-alive: total = N x (handshake + request) = %s (%d)" % (without_pays_per_request, wo))

    with_amortizes = wk == h + n * r
    print("  with keep-alive: total = handshake + N x request = %s (%d)" % (with_amortizes, wk))

    handshake_paid_once = handshakes_with(n) == 1 and handshakes_without(n) == n
    print("  keep-alive pays the handshake once, not N times = %s (1 vs %d)" % (handshake_paid_once, n))

    keepalive_fewer = wk < wo
    print("  keep-alive uses fewer round-trips = %s (%d < %d)" % (keepalive_fewer, wk, wo))

    saving_is_n_minus_1_handshakes = (wo - wk) == (n - 1) * h
    print("  the saving equals (N-1) handshakes = %s (%d = %d x %d)" % (saving_is_n_minus_1_handshakes, wo - wk, n - 1, h))

    ok = without_pays_per_request and with_amortizes and handshake_paid_once and keepalive_fewer and saving_is_n_minus_1_handshakes
    print("-" * 116)
    print("SELF-TEST %s  without_pays_per_request=%s  with_amortizes=%s  handshake_paid_once=%s  keepalive_fewer=%s  saving_is_n_minus_1_handshakes=%s"
          % ("PASS" if ok else "FAIL", without_pays_per_request, with_amortizes, handshake_paid_once, keepalive_fewer, saving_is_n_minus_1_handshakes))
    return ok


def main():
    p = argparse.ArgumentParser(description="Connection reuse: reuse connections (keep-alive / a connection pool) for repeated requests to the same server, because establishing a connection costs a TCP + TLS handshake of several round-trips (and server CPU) that is paid once per connection -- so a new connection per request repeats that handshake N times, while a reused connection pays it once and amortizes it over all the requests.")
    p.add_argument("--latency", action="store_true")
    p.add_argument("--handshakes", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("num_requests=%d  handshake_round_trips=%d  request_round_trips=%d  file=%s  (the request burst and costs are a fixture)"
          % (data["num_requests"], data["handshake_round_trips"], data["request_round_trips"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.latency:
        latency_view(data)
    elif args.handshakes:
        handshakes_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
