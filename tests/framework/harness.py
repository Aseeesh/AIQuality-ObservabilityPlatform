"""A minimal test harness so the suites run with bare `python3` (no pytest required).

Each suite collects `test_*` functions and runs them, printing pass/fail. `timed` measures a
callable's average latency for the performance suites; `approx` is a float comparison helper.
"""
from __future__ import annotations

import time
import traceback
from typing import Callable


class Suite:
    def __init__(self, name: str):
        self.name = name

    def run(self, namespace: dict) -> int:
        fns = [(k, v) for k, v in sorted(namespace.items())
               if k.startswith("test_") and callable(v)]
        failed = 0
        print(f"\n[{self.name}]")
        for name, fn in fns:
            try:
                fn()
                print(f"  ok  {name}")
            except Exception:
                failed += 1
                print(f"  FAIL {name}")
                traceback.print_exc()
        print(f"  -> {len(fns) - failed}/{len(fns)} passed")
        return failed


def timed(fn: Callable[[], object], iterations: int = 100) -> float:
    """Return the average wall-clock latency of `fn` in milliseconds over `iterations`."""
    # Warm up once (JIT-free, but primes caches / lazy imports).
    fn()
    start = time.perf_counter()
    for _ in range(iterations):
        fn()
    return (time.perf_counter() - start) / iterations * 1000.0


def approx(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


def run_main(suite_name: str, namespace: dict) -> None:
    import sys
    raise SystemExit(0 if Suite(suite_name).run(namespace) == 0 else 1)
