"""PlutusData / Transaction roundtrip benchmark + profiler.

Measures the real cost of decode (from_cbor), encode (to_cbor), and to_json for
both typed PlutusData and untyped RawPlutusData, across synthetic complexity
sweeps, plus Transaction fixtures. Designed to locate the indexing bottleneck.
"""

import cProfile
import io
import pstats
import sys
import time
from dataclasses import dataclass
from typing import Dict, List

from pycardano.cbor import cbor2
from pycardano.plutus import PlutusData, RawPlutusData
from pycardano.serialization import IndefiniteList, default_encoder

try:
    from importlib.metadata import version

    BACKEND = f"{cbor2.__name__} {version('cbor2pure') if cbor2.__name__=='cbor2pure' else version('cbor2')}"
except Exception:
    BACKEND = cbor2.__name__


def best_us(fn, iters, repeats=5):
    for _ in range(min(50, iters)):
        fn()
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        for _ in range(iters):
            fn()
        best = min(best, time.perf_counter() - t0)
    return best / iters * 1e6


def make_constr(cid, fields):
    return cbor2.CBORTag(121 + cid if cid < 7 else 1280 + (cid - 7), fields)


def gen_deep(depth):
    node = make_constr(0, [0])
    for _ in range(depth):
        node = make_constr(1, [node])
    return node


def gen_wide(n):
    return make_constr(0, [i if i % 2 else b"\x01\x02\x03\x04" for i in range(n)])


def gen_list(n):
    return make_constr(0, [IndefiniteList(list(range(n)))])


def gen_map(n):
    return make_constr(0, [{i: bytes([i % 256]) * 8 for i in range(n)}])


def gen_realistic(depth, width):
    def build(d):
        fields = [d, b"\xde\xad\xbe\xef" * 4, IndefiniteList(list(range(width)))]
        if d > 0:
            fields.append(build(d - 1))
            fields.append({j: build(0) for j in range(2)})
        return make_constr(d % 6, fields)

    return build(depth)


SYNTH = {
    "deep(d=40)": gen_deep(40),
    "wide(n=200)": gen_wide(200),
    "list(n=500)": gen_list(500),
    "map(n=200)": gen_map(200),
    "realistic(d=6,w=10)": gen_realistic(6, 10),
}


def encode_datum(obj):
    return cbor2.dumps(obj, default=default_encoder)


def run_section(title, items, iters):
    print(f"\n=== {title} ===")
    print(
        f"  {'case':24} {'bytes':>7} {'decode us':>11} {'encode us':>11} {'to_json us':>11}"
    )
    for name, raw in items:
        dec = best_us(lambda r=raw: RawPlutusData.from_cbor(r), iters)
        obj = RawPlutusData.from_cbor(raw)
        enc = best_us(lambda o=obj: o.to_cbor(), iters)
        try:
            tj = best_us(lambda o=obj: o.to_json(), iters)
        except Exception:
            tj = float("nan")
        print(f"  {name:24} {len(raw):>7} {dec:>11.1f} {enc:>11.1f} {tj:>11.1f}")


@dataclass
class Inner(PlutusData):
    CONSTR_ID = 0
    a: int
    b: bytes


@dataclass
class Mid(PlutusData):
    CONSTR_ID = 1
    x: int
    items: List[Inner]
    mapping: Dict[int, Inner]


@dataclass
class Outer(PlutusData):
    CONSTR_ID = 2
    a: bytes
    mid: Mid
    leaves: List[Inner]


def build_typed(n):
    inners = [Inner(a=i, b=bytes([i % 256]) * 8) for i in range(n)]
    mid = Mid(x=7, items=inners, mapping={i: inners[i] for i in range(min(n, 20))})
    return Outer(a=b"\xab" * 28, mid=mid, leaves=inners)


def run_typed(iters):
    print("\n=== Typed PlutusData decode vs untyped on the SAME bytes ===")
    print(
        f"  {'n_inner':>8} {'bytes':>7} {'typed dec us':>13} {'raw dec us':>11} {'typed/raw':>10}"
    )
    for n in (10, 50, 200):
        obj = build_typed(n)
        raw = obj.to_cbor()
        td = best_us(lambda r=raw: Outer.from_cbor(r), iters)
        rd = best_us(lambda r=raw: RawPlutusData.from_cbor(r), iters)
        print(f"  {n:>8} {len(raw):>7} {td:>13.1f} {rd:>11.1f} {td/rd:>9.1f}x")


def main():
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    print(
        f"### backend={BACKEND} | python {sys.version.split()[0]} | iters={iters} ###"
    )

    synth_items = [(n, encode_datum(o)) for n, o in SYNTH.items()]
    run_section("RawPlutusData (untyped - typical indexer path)", synth_items, iters)
    run_typed(iters)

    heaviest = max(synth_items, key=lambda kv: len(kv[1]))
    print(
        f"\n=== cProfile: RawPlutusData.from_cbor on '{heaviest[0]}' ({len(heaviest[1])}B) ==="
    )
    pr = cProfile.Profile()
    pr.enable()
    for _ in range(2000):
        RawPlutusData.from_cbor(heaviest[1])
    pr.disable()
    s = io.StringIO()
    pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(16)
    for line in s.getvalue().splitlines():
        if (
            "pycardano" in line
            or "cbor2" in line
            or "function calls" in line
            or "{" in line
        ):
            print("   " + line.strip()[:115])


if __name__ == "__main__":
    main()
