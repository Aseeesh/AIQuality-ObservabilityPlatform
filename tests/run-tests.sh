#!/usr/bin/env bash
# Run the cross-cutting test framework: quality-validation, integration, performance, e2e.
#
# These exercise the real Python services in-process (the per-service unit suites are run by
# scripts/run-python-tests.sh). Stdlib-only, so no install needed.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-python3}"
fail=0
total=0

for category in quality-validation integration performance e2e; do
  for test in "$HERE/$category"/test_*.py; do
    [ -e "$test" ] || continue
    total=$((total + 1))
    if ! "$PY" "$test"; then
      echo "FAILED: ${test#"$HERE"/}"
      fail=1
    fi
  done
done

echo ""
echo "========================================"
[ "$fail" -eq 0 ] && echo "All $total framework suites passed." || echo "Some framework suites FAILED."
exit $fail
