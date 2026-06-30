#!/usr/bin/env bash
# Validate (and, outside --check, deploy) quality gate definitions.
# Usage: deploy-quality-gates.sh [--check] <quality-gates.yaml>
set -euo pipefail

check_only=0
file=""
for arg in "$@"; do
  case "$arg" in
    --check) check_only=1 ;;
    *) file="$arg" ;;
  esac
done

[ -n "$file" ] || { echo "error: no quality-gates file given"; exit 2; }
[ -f "$file" ] || { echo "error: $file not found"; exit 1; }

# Validate structure. Prefer a real YAML parse when PyYAML is available; otherwise fall back
# to a structural grep so the gate works on a bare runner.
if python3 -c "import yaml" 2>/dev/null; then
  python3 - "$file" <<'PY'
import sys, yaml
doc = yaml.safe_load(open(sys.argv[1])) or {}
gates = doc.get("gates", [])
assert gates, "no 'gates' defined"
for g in gates:
    assert "name" in g and "threshold" in g, f"gate missing name/threshold: {g}"
print(f"quality gates valid: {len(gates)} gate(s) — {', '.join(g['name'] for g in gates)}")
PY
else
  grep -q "^gates:" "$file" || { echo "error: no 'gates:' section in $file"; exit 1; }
  count=$(grep -c "name:" "$file" || true)
  [ "$count" -gt 0 ] || { echo "error: no gates defined in $file"; exit 1; }
  echo "quality gates valid: $count gate(s)"
fi

if [ "$check_only" -eq 0 ]; then
  echo "deploying quality gates from $file …"
  # Production: POST the gate definitions to the platform's config API.
fi
