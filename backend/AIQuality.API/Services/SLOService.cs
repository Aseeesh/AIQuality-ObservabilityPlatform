using System.Collections.Concurrent;
using System.Text;
using AIQuality.Core.Entities;
using AIQuality.Core.Enums;
using AIQuality.Core.Interfaces;

namespace AIQuality.API.Services;

// =============================================================================
// SLO Definition & Tracking Service
// =============================================================================
//
//   1. SLO definitions — registered with a target, a per-event "good" boundary, and an
//      error-budget policy. Four SLI families are supported via SLOMetricType: performance
//      (latency), quality (accuracy/quality-score), availability, and business.
//   2. SLI collection — a bounded rolling window of good/bad events per SLO; raw observations
//      are converted to good/bad by the definition's GoodThreshold/Comparison.
//   3. Error budget — budget = 1 - Target; consumed = (1 - SLI)/budget; burn rate normalises
//      consumption by how much of the window has elapsed, so fast burns alert (page) early.
//   4. Reporting — compliance snapshot + an executive summary.
//
// Held in-memory (singleton) so it is runnable without a DB; swap the event windows for a
// time-series store (TimescaleDB) to persist across restarts.
// =============================================================================
public class SLOService : ISLOService
{
    private readonly ConcurrentDictionary<string, SLODefinition> _defs = new();
    private readonly ConcurrentDictionary<string, Queue<bool>> _events = new();

    public SLOService() => SeedDefaults();

    // -------------------------------------------------------------------------
    // SLO definitions
    // -------------------------------------------------------------------------
    public SLODefinition Define(SLODefinition definition)
    {
        _defs[definition.SLOName] = definition;
        _events.TryAdd(definition.SLOName, new Queue<bool>());
        return definition;
    }

    public IReadOnlyList<SLODefinition> Definitions() => _defs.Values.ToList();

    private void SeedDefaults()
    {
        Define(new SLODefinition
        {
            SLOName = "api-availability", MetricType = SLOMetricType.Availability,
            Target = 0.999, WarningThreshold = 0.9995, GoodThreshold = 1, Comparison = GateOperator.Gte,
        });
        Define(new SLODefinition
        {
            SLOName = "eval-latency", MetricType = SLOMetricType.Latency,
            Target = 0.99, WarningThreshold = 0.995, GoodThreshold = 2000, Comparison = GateOperator.Lte,
        });
        Define(new SLODefinition
        {
            SLOName = "quality-score", MetricType = SLOMetricType.Quality,
            Target = 0.95, WarningThreshold = 0.97, GoodThreshold = 0.8, Comparison = GateOperator.Gte,
        });
    }

    // -------------------------------------------------------------------------
    // SLI collection
    // -------------------------------------------------------------------------
    public void RecordEvent(string sloName, bool good)
    {
        if (!_defs.TryGetValue(sloName, out var def)) return;
        var window = _events.GetOrAdd(sloName, _ => new Queue<bool>());
        lock (window)
        {
            window.Enqueue(good);
            while (window.Count > def.ErrorBudget.WindowEvents) window.Dequeue();
        }
    }

    public void RecordObservation(string sloName, double value)
    {
        if (!_defs.TryGetValue(sloName, out var def)) return;
        var good = def.Comparison == GateOperator.Lte ? value <= def.GoodThreshold : value >= def.GoodThreshold;
        RecordEvent(sloName, good);
    }

    // -------------------------------------------------------------------------
    // Evaluation + error budget
    // -------------------------------------------------------------------------
    public SLOComplianceResult? Evaluate(string sloName)
    {
        if (!_defs.TryGetValue(sloName, out var def)) return null;
        var (sli, sampled) = Sli(sloName);

        var status = sli >= def.Target ? SLIStatus.Healthy
            : sli >= def.WarningThreshold ? SLIStatus.AtRisk
            : SLIStatus.Breached;

        return new SLOComplianceResult
        {
            SLOName = def.SLOName, ServiceId = def.ServiceId, MetricType = def.MetricType,
            Sli = Math.Round(sli, 5), Target = def.Target, WarningThreshold = def.WarningThreshold,
            Sampled = sampled, Status = status, ErrorBudget = ErrorBudgetFor(def, sli, sampled),
        };
    }

    public ErrorBudgetStatus? GetErrorBudget(string sloName)
    {
        if (!_defs.TryGetValue(sloName, out var def)) return null;
        var (sli, sampled) = Sli(sloName);
        return ErrorBudgetFor(def, sli, sampled);
    }

    private static ErrorBudgetStatus ErrorBudgetFor(SLODefinition def, double sli, int sampled)
    {
        var budget = Math.Max(1e-9, 1.0 - def.Target);   // allowed bad fraction
        var badFraction = 1.0 - sli;
        var consumed = badFraction / budget;             // >1 => over budget
        var windowFraction = def.ErrorBudget.WindowEvents > 0
            ? (double)sampled / def.ErrorBudget.WindowEvents : 1.0;
        var burnRate = windowFraction > 0 ? consumed / windowFraction : 0.0;

        var status = new ErrorBudgetStatus
        {
            SLOName = def.SLOName, Objective = def.Target,
            Consumed = Math.Round(consumed, 4), Remaining = Math.Round(Math.Max(0, 1 - consumed), 4),
            BurnRate = Math.Round(burnRate, 3),
        };
        // Budget policy: alert on fast/slow burn.
        if (burnRate >= def.ErrorBudget.FastBurnRate)
            status.Alerts.Add($"FAST burn ({burnRate:0.#}x >= {def.ErrorBudget.FastBurnRate}) — page on-call.");
        else if (burnRate >= def.ErrorBudget.SlowBurnRate)
            status.Alerts.Add($"SLOW burn ({burnRate:0.#}x >= {def.ErrorBudget.SlowBurnRate}) — open a ticket.");
        if (consumed >= 1)
            status.Alerts.Add("Error budget exhausted — freeze risky changes.");
        return status;
    }

    private (double sli, int sampled) Sli(string sloName)
    {
        var window = _events.GetOrAdd(sloName, _ => new Queue<bool>());
        lock (window)
        {
            if (window.Count == 0) return (1.0, 0);     // no data => assume healthy
            return ((double)window.Count(g => g) / window.Count, window.Count);
        }
    }

    // -------------------------------------------------------------------------
    // Tracking + reporting
    // -------------------------------------------------------------------------
    public Task<SLOMetrics> TrackSLOMetricsAsync(CancellationToken ct = default)
    {
        var results = _defs.Keys.Select(Evaluate).Where(r => r is not null).Cast<SLOComplianceResult>().ToList();
        var metrics = new SLOMetrics
        {
            Results = results,
            Total = results.Count,
            Compliant = results.Count(r => r.Status == SLIStatus.Healthy),
        };
        return Task.FromResult(metrics);
    }

    public SLOReport GenerateReport()
    {
        var metrics = TrackSLOMetricsAsync().GetAwaiter().GetResult();
        var sb = new StringBuilder();
        sb.AppendLine($"# SLO Compliance — {metrics.GeneratedAt:u}");
        sb.AppendLine($"- Compliant: {metrics.Compliant}/{metrics.Total}");
        foreach (var r in metrics.Results)
        {
            sb.AppendLine($"- {r.SLOName} [{r.MetricType}]: SLI {r.Sli:P2} vs target {r.Target:P1} " +
                          $"=> {r.Status}; budget {r.ErrorBudget.Remaining:P0} left (burn {r.ErrorBudget.BurnRate:0.#}x)" +
                          (r.ErrorBudget.Alerts.Count > 0 ? $" [{string.Join("; ", r.ErrorBudget.Alerts)}]" : ""));
        }
        return new SLOReport { Metrics = metrics, ExecutiveSummary = sb.ToString().TrimEnd() };
    }
}
