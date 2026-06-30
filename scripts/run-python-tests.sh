#!/usr/bin/env bash
# Run every Python service's test suite.
#
# The suites are intentionally stdlib-only (model/HTTP backends are optional and guarded), so
# CI needs nothing beyond a Python interpreter — no pip install. Each test file is runnable
# directly (it puts its own service root on sys.path), so we invoke them by absolute path.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"
fail=0
total=0

for test in "$ROOT"/python-services/*/tests/test_*.py; do
  [ -e "$test" ] || continue
  total=$((total + 1))
  echo ""
  echo "=== ${test#"$ROOT"/} ==="
  if ! "$PY" "$test"; then
    echo "FAILED: $test"
    fail=1
  fi
done

echo ""
echo "----------------------------------------"
if [ "$fail" -eq 0 ]; then
  echo "All $total Python test suites passed."
else
  echo "Some Python test suites FAILED."
fi
exit $fail
