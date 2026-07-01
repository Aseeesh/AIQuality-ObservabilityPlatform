#!/usr/bin/env bash
# Smoke-test the running stack: waits for services, then exercises the full functionality
# (Ollama judge, tracing, evaluation+gates, monitoring, incident+RCA, SLO, feedback).
#
# Assumes `make up` (and, for a real LLM judge, `make ollama-pull`) have been run.
set -uo pipefail

API="${API:-http://localhost:8080}"
EVAL="${EVAL:-http://localhost:8001}"
ANOMALY="${ANOMALY:-http://localhost:8002}"
RCA="${RCA:-http://localhost:8003}"
FEEDBACK="${FEEDBACK:-http://localhost:8004}"

pass=0; fail=0
ok()   { echo "  ✅ $1"; pass=$((pass+1)); }
bad()  { echo "  ❌ $1"; fail=$((fail+1)); }
j()    { python3 -c "import sys,json;d=json.load(sys.stdin);print($1)" 2>/dev/null; }

wait_for() {  # name url
  printf "waiting for %s " "$1"
  for _ in $(seq 1 60); do
    if curl -sf "$2" >/dev/null 2>&1; then echo "up"; return 0; fi
    printf "."; sleep 2
  done
  echo " TIMEOUT"; return 1
}

echo "== health =="
wait_for "api" "$API/health"                 && ok "API healthy"          || bad "API not responding"
wait_for "quality-evaluator" "$EVAL/health"  && ok "evaluator healthy"    || bad "evaluator not responding"
curl -sf "$ANOMALY/health"  >/dev/null && ok "anomaly-detector healthy"   || bad "anomaly-detector down"
curl -sf "$RCA/health"      >/dev/null && ok "automated-rca healthy"      || bad "automated-rca down"
curl -sf "$FEEDBACK/health" >/dev/null && ok "feedback-processor healthy" || bad "feedback-processor down"

echo ""; echo "== judge backend (Ollama?) =="
HEALTH=$(curl -s "$EVAL/health")
BACKEND=$(echo "$HEALTH" | j "d['backend']"); MODEL=$(echo "$HEALTH" | j "d.get('model')")
echo "  backend=$BACKEND model=$MODEL"
[ "$BACKEND" = "ollama" ] && ok "judge is using Ollama ($MODEL)" \
  || bad "judge is '$BACKEND' (run 'make ollama-pull' for a real LLM judge; heuristic still works)"

echo ""; echo "== evaluate one output through the judge =="
EVOUT=$(curl -s -X POST "$EVAL/evaluate" -H 'Content-Type: application/json' -d \
  '{"prompt":"What is the availability SLO?","context":"availability target is 99.9 percent over 30 days","output":"The availability target is 99.9 percent over a 30 day window."}')
echo "  -> verdict=$(echo "$EVOUT" | j "d['verdict']") overall=$(echo "$EVOUT" | j "d['overall']") backend=$(echo "$EVOUT" | j "d['backend']")"
[ -n "$EVOUT" ] && ok "evaluate returned a judgement" || bad "evaluate failed"

echo ""; echo "== tracing (.NET) =="
SPANS=$(curl -s -X POST "$API/api/spans/demo")
echo "  seeded traces: $(echo "$SPANS" | j "len(d['seeded'])")"
curl -sf "$API/api/spans/profile" >/dev/null && ok "spans + profile OK" || bad "spans failed"

echo ""; echo "== evaluation + quality gates (uses the Ollama judge) =="
EVAL_DEMO=$(curl -s -X POST "$API/api/evaluation/demo")
echo "  regressed gate: $(echo "$EVAL_DEMO" | j "d['regressedGateStatus']"), scoreDelta=$(echo "$EVAL_DEMO" | j "d['regression']['scoreDelta']")"
[ -n "$EVAL_DEMO" ] && ok "batch eval + regression detection OK" || bad "evaluation demo failed"

echo ""; echo "== incident + automated RCA =="
INC=$(curl -s -X POST "$API/api/incidents/demo")
echo "  RCA: $(echo "$INC" | j "d['rca']['rootCause'][:70]") (conf $(echo "$INC" | j "d['rca']['confidence']"))"
[ -n "$INC" ] && ok "incident created with automated RCA" || bad "incident demo failed"

echo ""; echo "== SLO tracking =="
SLO=$(curl -s -X POST "$API/api/slo/demo")
echo "  SLOs: $(echo "$SLO" | j "', '.join(r['sloName']+'='+str(r['status']) for r in d['results'])")"
[ -n "$SLO" ] && ok "SLO metrics + error budgets OK" || bad "SLO demo failed"

echo ""; echo "== feedback (Python) =="
FB=$(curl -s -X POST "$FEEDBACK/feedback" -H 'Content-Type: application/json' -d \
  '{"prompt":"q","response":"wrong answer","rating":1,"text":"completely wrong and inaccurate"}')
echo "  sentiment=$(echo "$FB" | j "d['sentiment']") eval_case=$(echo "$FB" | j "(d.get('eval_case') or {}).get('label')")"
[ -n "$FB" ] && ok "feedback processed + eval case generated" || bad "feedback failed"

echo ""; echo "========================================"
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] && echo "  Stack is fully functional. 🎉" || echo "  Some checks failed (see above)."
exit $fail
