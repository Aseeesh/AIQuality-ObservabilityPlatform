using System.Collections.Concurrent;
using System.Text;
using AIQuality.Core.Entities;
using AIQuality.Core.Enums;
using AIQuality.Core.Interfaces;

namespace AIQuality.API.Services;

// =============================================================================
// Batch Evaluation & Quality Gates Service
// =============================================================================
//
// Responsibilities:
//   1. Batch evaluation pipeline — score a dataset's items in parallel (bounded), aggregate
//      into run-level metrics (per-rubric means, pass rate, latency p95, cost, safety).
//   2. Quality gates — assert run aggregates against per-environment thresholds; the run's
//      overall GateStatus is the worst gate outcome (a failed Failed-severity gate blocks).
//   3. Regression detection — compare against the baseline (previous run on the same
//      dataset+environment) using Welch's t-test over per-item scores, so only statistically
//      significant degradations raise alerts.
//   4. Reporting — evaluation report + executive summary.
//   5. Automation — RunCiCdGateAsync for CI/CD; trigger-based runs via the controller;
//      scheduled runs would call RunBatchEvaluationAsync from a hosted timer/cron.
//
// Items are scored by an injected IOutputEvaluator (default: local heuristic; production:
// the Python calibrated LLM-as-Judge). Run history is kept in-memory (singleton service);
// swap for a repository to persist across restarts.
// =============================================================================
public class EvaluationService : IEvaluationService
{
    private readonly IOutputEvaluator _evaluator;

    // Run history, newest last. Guards both the list and the id index.
    private readonly List<BatchEvaluationResult> _history = new();
    private readonly ConcurrentDictionary<Guid, BatchEvaluationResult> _byId = new();
    private readonly object _gate = new();

    // Minimum score drop (vs baseline) that counts as a regression once significant.
    private const double RegressionTolerance = 0.02;

    public EvaluationService(IOutputEvaluator evaluator) => _evaluator = evaluator;

    // -------------------------------------------------------------------------
    // 1. Batch evaluation pipeline
    // -------------------------------------------------------------------------
    public async Task<BatchEvaluationResult> RunBatchEvaluationAsync(
        BatchEvaluationRequest request, CancellationToken ct = default)
    {
        var startedAt = DateTimeOffset.UtcNow;
        var sw = System.Diagnostics.Stopwatch.StartNew();

        // Score items in parallel with a bounded degree of parallelism. Results land in a
        // concurrent bag, then are ordered deterministically for stable aggregation.
        var bag = new ConcurrentBag<EvaluationItemResult>();
        await Parallel.ForEachAsync(
            request.Items,
            new ParallelOptions { MaxDegreeOfParallelism = Math.Max(1, request.MaxDegreeOfParallelism), CancellationToken = ct },
            async (item, token) => bag.Add(await _evaluator.EvaluateAsync(item, request.RubricSet, token)));

        var items = bag.OrderBy(r => r.ItemId).ToList();
        sw.Stop();

        var perRubric = AggregatePerRubric(items, _evaluator.RubricsFor(request.RubricSet));
        var run = Aggregate(request, items, perRubric, startedAt, sw.ElapsedMilliseconds);

        // Quality gates.
        var gates = EvaluateGates(run, perRubric, request.Environment);
        run.GateStatus = WorstStatus(gates);

        var result = new BatchEvaluationResult { Run = run, PerRubric = perRubric, Gates = gates.ToList(), Items = items };

        // Regression vs baseline (computed before this run is added to history).
        result.Regression = DetectRegression(result);

        lock (_gate)
        {
            _history.Add(result);
            _byId[run.Id] = result;
        }
        return result;
    }

    private static Dictionary<string, double> AggregatePerRubric(List<EvaluationItemResult> items, IReadOnlyList<string> rubrics)
    {
        var perRubric = new Dictionary<string, double>();
        if (items.Count == 0) return perRubric;
        foreach (var rubric in rubrics)
        {
            var vals = items.Where(i => i.Scores.ContainsKey(rubric)).Select(i => i.Scores[rubric]).ToList();
            if (vals.Count > 0) perRubric[rubric] = vals.Average();
        }
        return perRubric;
    }

    private static EvaluationRun Aggregate(
        BatchEvaluationRequest request, List<EvaluationItemResult> items,
        Dictionary<string, double> perRubric, DateTimeOffset runAt, long durationMs)
    {
        var overall = items.Count > 0 ? items.Average(i => i.Overall) : 0.0;
        return new EvaluationRun
        {
            Dataset = request.Dataset,
            Environment = request.Environment,
            RubricSet = request.RubricSet,
            RunAt = runAt,
            DurationMs = durationMs,
            ItemCount = items.Count,
            Overall = overall,
            CalibratedOverall = overall, // calibration is applied upstream by the LLM judge
            PassRate = Fraction(items, i => i.Verdict == QualityGateStatus.Passed),
            SafetyRate = Fraction(items, i => i.Safe),
            MeanLatencyMs = items.Count > 0 ? items.Average(i => i.LatencyMs) : 0,
            P95LatencyMs = Percentile(items.Select(i => i.LatencyMs).ToList(), 0.95),
            TotalCostUsd = items.Sum(i => i.CostUsd),
        };
    }

    // -------------------------------------------------------------------------
    // 2. Quality gates
    // -------------------------------------------------------------------------
    public IReadOnlyList<QualityGateResult> EvaluateGates(
        EvaluationRun run, IReadOnlyDictionary<string, double> perRubric, string environment)
    {
        var results = new List<QualityGateResult>();
        foreach (var gate in QualityGatePolicies.ForEnvironment(environment))
        {
            var actual = ResolveMetric(gate.Metric, run, perRubric);
            var pass = gate.Operator == GateOperator.Gte ? actual >= gate.Threshold : actual <= gate.Threshold;
            results.Add(new QualityGateResult
            {
                Name = gate.Name,
                Metric = gate.Metric,
                Operator = gate.Operator,
                Threshold = gate.Threshold,
                Actual = Math.Round(actual, 4),
                Status = pass ? QualityGateStatus.Passed : gate.SeverityOnFail,
                Message = pass
                    ? $"{gate.Metric} {actual:0.###} {Sym(gate.Operator)} {gate.Threshold:0.###} ✓"
                    : $"{gate.Metric} {actual:0.###} violates {Sym(gate.Operator)} {gate.Threshold:0.###}",
            });
        }
        return results;
    }

    private static double ResolveMetric(GateMetric metric, EvaluationRun run, IReadOnlyDictionary<string, double> perRubric) => metric switch
    {
        GateMetric.Overall => run.CalibratedOverall,
        GateMetric.Accuracy => perRubric.TryGetValue("accuracy", out var a) ? a : run.CalibratedOverall,
        GateMetric.Safety => run.SafetyRate,
        GateMetric.PassRate => run.PassRate,
        GateMetric.MeanLatencyMs => run.MeanLatencyMs,
        GateMetric.P95LatencyMs => run.P95LatencyMs,
        GateMetric.MeanCostUsd => run.ItemCount > 0 ? (double)run.TotalCostUsd / run.ItemCount : 0,
        GateMetric.TotalCostUsd => (double)run.TotalCostUsd,
        _ => 0,
    };

    // -------------------------------------------------------------------------
    // 3. Regression detection (Welch's t-test over per-item scores)
    // -------------------------------------------------------------------------
    public RegressionReport DetectRegression(BatchEvaluationResult current)
    {
        var baseline = FindBaseline(current);
        if (baseline is null)
            return new RegressionReport { HasBaseline = false, Summary = "No baseline run for this dataset/environment yet." };

        var cur = current.Items.Select(i => i.Overall).ToList();
        var bas = baseline.Items.Select(i => i.Overall).ToList();
        var (t, significant) = WelchT(cur, bas);

        var report = new RegressionReport
        {
            HasBaseline = true,
            BaselineRunId = baseline.Run.Id,
            BaselineMean = bas.Count > 0 ? bas.Average() : 0,
            CurrentMean = cur.Count > 0 ? cur.Average() : 0,
            LatencyDeltaMs = current.Run.MeanLatencyMs - baseline.Run.MeanLatencyMs,
            TStatistic = Math.Round(t, 3),
            Significant = significant,
        };
        report.ScoreDelta = Math.Round(report.CurrentMean - report.BaselineMean, 4);
        report.Degraded = significant && report.ScoreDelta < -RegressionTolerance;

        if (report.Degraded)
            report.Alerts.Add($"Quality regression: score dropped {Math.Abs(report.ScoreDelta):0.###} " +
                              $"(t={report.TStatistic}) vs baseline {baseline.Run.Id.ToString()[..8]}.");
        if (report.LatencyDeltaMs > 0.25 * Math.Max(1, baseline.Run.MeanLatencyMs))
            report.Alerts.Add($"Latency regression: +{report.LatencyDeltaMs:0} ms mean vs baseline.");

        report.Summary = report.Degraded
            ? "Significant quality regression detected."
            : report.ScoreDelta >= RegressionTolerance && significant
                ? "Significant improvement vs baseline."
                : "No significant change vs baseline.";
        return report;
    }

    private BatchEvaluationResult? FindBaseline(BatchEvaluationResult current)
    {
        lock (_gate)
        {
            // Most recent prior run on the same dataset+environment with item-level scores.
            return _history
                .Where(r => r.Run.Id != current.Run.Id
                    && r.Run.Dataset == current.Run.Dataset
                    && r.Run.Environment == current.Run.Environment
                    && r.Items.Count > 0)
                .OrderByDescending(r => r.Run.RunAt)
                .FirstOrDefault();
        }
    }

    // Welch's unequal-variance t-test. Returns (t, significant). Significance uses |t| > 2
    // as a ~p<0.05 approximation (avoids shipping a full t-distribution table).
    private static (double t, bool significant) WelchT(List<double> a, List<double> b)
    {
        if (a.Count < 2 || b.Count < 2) return (0, false);
        double ma = a.Average(), mb = b.Average();
        double va = Variance(a, ma), vb = Variance(b, mb);
        double se = Math.Sqrt(va / a.Count + vb / b.Count);
        if (se == 0) return (ma == mb ? (0, false) : (Math.Sign(ma - mb) * 99.0, true));
        double t = (ma - mb) / se;
        return (t, Math.Abs(t) > 2.0);
    }

    private static double Variance(List<double> xs, double mean) =>
        xs.Count < 2 ? 0 : xs.Sum(x => (x - mean) * (x - mean)) / (xs.Count - 1);

    // -------------------------------------------------------------------------
    // 4. Reporting
    // -------------------------------------------------------------------------
    public EvaluationReport GenerateReport(BatchEvaluationResult result)
    {
        var run = result.Run;
        var sb = new StringBuilder();
        sb.AppendLine($"# Evaluation: {run.Dataset} ({run.Environment})");
        sb.AppendLine($"- Gate status: **{run.GateStatus}**");
        sb.AppendLine($"- Items: {run.ItemCount} · Pass rate: {run.PassRate:0%} · Overall: {run.CalibratedOverall:0.###}");
        sb.AppendLine($"- Latency p95: {run.P95LatencyMs} ms · Cost: ${run.TotalCostUsd:0.####} · Safety: {run.SafetyRate:0%}");
        var failed = result.Gates.Where(g => g.Status != QualityGateStatus.Passed).ToList();
        if (failed.Count > 0)
            sb.AppendLine($"- Failing gates: {string.Join(", ", failed.Select(g => g.Name))}");
        if (result.Regression is { Degraded: true })
            sb.AppendLine($"- ⚠ {result.Regression.Summary}");

        return new EvaluationReport
        {
            Run = run,
            PerRubric = result.PerRubric,
            Gates = result.Gates,
            Regression = result.Regression,
            ExecutiveSummary = sb.ToString().TrimEnd(),
        };
    }

    // -------------------------------------------------------------------------
    // 5. Automation
    // -------------------------------------------------------------------------
    // CI/CD gate: same as a batch run; callers inspect result.Run.GateStatus to set the build
    // result (Failed => fail the pipeline). Scheduled/trigger automation reuse this entry point.
    public Task<BatchEvaluationResult> RunCiCdGateAsync(BatchEvaluationRequest request, CancellationToken ct = default)
        => RunBatchEvaluationAsync(request, ct);

    // -------------------------------------------------------------------------
    // Query
    // -------------------------------------------------------------------------
    public IReadOnlyList<EvaluationRun> History(string? dataset = null)
    {
        lock (_gate)
        {
            return _history
                .Where(r => dataset == null || r.Run.Dataset == dataset)
                .OrderByDescending(r => r.Run.RunAt)
                .Select(r => r.Run)
                .ToList();
        }
    }

    public BatchEvaluationResult? GetResult(Guid runId) => _byId.TryGetValue(runId, out var r) ? r : null;

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------
    private static double Fraction(List<EvaluationItemResult> items, Func<EvaluationItemResult, bool> pred) =>
        items.Count == 0 ? 1.0 : items.Count(pred) / (double)items.Count;

    private static long Percentile(List<long> values, double p)
    {
        if (values.Count == 0) return 0;
        var sorted = values.OrderBy(v => v).ToList();
        var rank = (int)Math.Ceiling(p * sorted.Count) - 1;
        return sorted[Math.Clamp(rank, 0, sorted.Count - 1)];
    }

    private static QualityGateStatus WorstStatus(IEnumerable<QualityGateResult> gates)
    {
        var worst = QualityGateStatus.Passed;
        foreach (var g in gates) if (g.Status > worst) worst = g.Status; // Passed < Warning < Failed
        return worst;
    }

    private static string Sym(GateOperator op) => op == GateOperator.Gte ? "≥" : "≤";
}
