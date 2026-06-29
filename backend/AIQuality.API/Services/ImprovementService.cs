using AIQuality.Core.Entities;
using AIQuality.Core.Enums;
using AIQuality.Core.Interfaces;

namespace AIQuality.API.Services;

// =============================================================================
// Model Improvement Pipeline
// =============================================================================
//
// Turns evaluation history into a prioritised improvement plan:
//   1. Quality analysis  — trend (latest vs baseline run), per-rubric gaps, cost & latency,
//      and (optional) user satisfaction from the feedback service.
//   2. Improvement generation — opportunities mapped to the right lever (prompt, model,
//      knowledge base, config, cost), each with concrete suggested actions and an expected
//      impact; prioritised by impact / effort.
//   3. Automated testing — an A/B + canary experiment to validate the top opportunity before
//      full rollout, with guardrail metrics and validation steps.
//
// Reads evaluation runs via IEvaluationService (the same in-memory history the batch evaluator
// populates), so the pipeline is grounded in real measured quality rather than guesswork.
// =============================================================================
public class ImprovementService : IImprovementService
{
    private readonly IEvaluationService _eval;

    public ImprovementService(IEvaluationService eval) => _eval = eval;

    public Task<ImprovementPlan> GenerateImprovementPlanAsync(ImprovementRequest request, CancellationToken ct = default)
    {
        var analysis = AnalyzeQuality(request);
        var opportunities = BuildOpportunities(analysis, request)
            .OrderByDescending(o => o.Priority)
            .ToList();
        var experiment = opportunities.Count > 0 ? DesignExperiment(opportunities[0], request) : null;

        var plan = new ImprovementPlan
        {
            Dataset = request.Dataset,
            Environment = request.Environment,
            Analysis = analysis,
            Opportunities = opportunities,
            Experiment = experiment,
            Summary = Summarize(analysis, opportunities),
        };
        return Task.FromResult(plan);
    }

    // -------------------------------------------------------------------------
    // 1. Quality analysis
    // -------------------------------------------------------------------------
    public QualityAnalysis AnalyzeQuality(ImprovementRequest request)
    {
        var runs = _eval.History(request.Dataset)
            .Where(r => r.Environment == request.Environment)
            .ToList(); // newest first

        if (runs.Count == 0)
            return new QualityAnalysis { HasData = false, UserSatisfaction = request.UserSatisfaction };

        var latest = runs[0];
        var detail = _eval.GetResult(latest.Id);
        var perRubric = detail?.PerRubric ?? new Dictionary<string, double>();

        // Trend: latest vs the previous run on the same dataset/environment.
        var baseline = runs.Skip(1).FirstOrDefault();
        var delta = baseline is null ? 0.0 : latest.CalibratedOverall - baseline.CalibratedOverall;
        var trend = baseline is null ? "unknown"
            : delta > 0.02 ? "improving" : delta < -0.02 ? "declining" : "stable";

        // Gaps: rubrics (or overall) below target.
        var gaps = perRubric.Where(kv => kv.Value < request.TargetQuality).Select(kv => kv.Key).ToList();
        if (perRubric.Count == 0 && latest.CalibratedOverall < request.TargetQuality)
            gaps.Add("overall");

        return new QualityAnalysis
        {
            HasData = true,
            Trend = trend,
            TrendDelta = Math.Round(delta, 4),
            CurrentOverall = latest.CalibratedOverall,
            PerRubric = perRubric,
            QualityGaps = gaps,
            CostPerItemUsd = latest.ItemCount > 0 ? (double)latest.TotalCostUsd / latest.ItemCount : 0,
            LatencyP95Ms = latest.P95LatencyMs,
            UserSatisfaction = request.UserSatisfaction,
        };
    }

    // -------------------------------------------------------------------------
    // 2. Improvement generation
    // -------------------------------------------------------------------------
    private static List<ImprovementOpportunity> BuildOpportunities(QualityAnalysis a, ImprovementRequest req)
    {
        var ops = new List<ImprovementOpportunity>();
        if (!a.HasData)
            return ops;

        // Per-rubric quality gaps -> the lever that best closes them.
        foreach (var rubric in a.QualityGaps)
        {
            var current = a.PerRubric.TryGetValue(rubric, out var v) ? v : a.CurrentOverall;
            var (area, actions) = LeverForRubric(rubric);
            ops.Add(MakeOpportunity(
                area, $"Close {rubric} gap", $"{rubric} is {current:0.##} vs target {req.TargetQuality:0.##}.",
                rubric, current, req.TargetQuality, impact: req.TargetQuality - current,
                effort: area == ImprovementArea.Model ? Effort.High : Effort.Medium, actions));
        }

        // Persistent/large accuracy gap also justifies a fine-tuning recommendation.
        if (a.PerRubric.TryGetValue("accuracy", out var acc) && acc < req.TargetQuality - 0.1)
            ops.Add(MakeOpportunity(
                ImprovementArea.Model, "Fine-tune for accuracy",
                "Accuracy is well below target; prompt-only fixes are unlikely to close it.",
                "accuracy", acc, req.TargetQuality, impact: (req.TargetQuality - acc) * 0.8, Effort.High,
                new() { "Curate a fine-tuning set from failing eval cases and feedback.",
                        "Fine-tune (or distil) and re-run quality gates before rollout." }));

        // Declining trend -> investigate/rollback the regression.
        if (a.Trend == "declining")
            ops.Add(MakeOpportunity(
                ImprovementArea.Configuration, "Investigate quality regression",
                $"Overall quality dropped {Math.Abs(a.TrendDelta):0.###} vs the previous run.",
                "overall", a.CurrentOverall, a.CurrentOverall - a.TrendDelta, impact: Math.Abs(a.TrendDelta) + 0.1,
                Effort.Low, new() { "Diff config/prompt/model vs the last good run.", "Roll back the regressing change." }));

        // Cost opportunity.
        if (a.CostPerItemUsd > req.MaxCostPerItemUsd)
            ops.Add(MakeOpportunity(
                ImprovementArea.Cost, "Reduce cost per request",
                $"Cost/item ${a.CostPerItemUsd:0.####} exceeds budget ${req.MaxCostPerItemUsd:0.####}.",
                "cost_per_item", a.CostPerItemUsd, req.MaxCostPerItemUsd, impact: 0.3, Effort.Medium,
                new() { "Route simple queries to a smaller/cheaper model.",
                        "Trim prompt size and cache repeated context." }));

        // Latency opportunity.
        if (a.LatencyP95Ms > req.LatencyBudgetMs)
            ops.Add(MakeOpportunity(
                ImprovementArea.Configuration, "Cut p95 latency",
                $"p95 latency {a.LatencyP95Ms} ms exceeds budget {req.LatencyBudgetMs} ms.",
                "latency_p95_ms", a.LatencyP95Ms, req.LatencyBudgetMs, impact: 0.25, Effort.Medium,
                new() { "Enable streaming and shorten prompts.", "Scale out inference / raise concurrency." }));

        // Low user satisfaction -> prompt/tone work.
        if (a.UserSatisfaction is { } sat && sat < 0.7)
            ops.Add(MakeOpportunity(
                ImprovementArea.Prompt, "Improve user satisfaction",
                $"User satisfaction {sat:0.##} is below 0.70.",
                "user_satisfaction", sat, 0.8, impact: 0.8 - sat, Effort.Low,
                new() { "Refine tone/format guidance in the system prompt.",
                        "Mine negative feedback themes and address the top complaint." }));

        return ops;
    }

    private static (ImprovementArea, List<string>) LeverForRubric(string rubric) => rubric switch
    {
        "accuracy" or "faithfulness" or "groundedness" => (ImprovementArea.KnowledgeBase, new()
        {
            "Improve retrieval coverage/quality for this domain.",
            "Add grounding instructions and require citations.",
        }),
        "safety" => (ImprovementArea.Configuration, new()
        {
            "Tighten safety guardrails and add a safety rubric gate.",
        }),
        "citation" => (ImprovementArea.Prompt, new() { "Require inline citations in the prompt." }),
        _ => (ImprovementArea.Prompt, new()
        {
            $"Add explicit instructions targeting '{rubric}' in the system prompt.",
            "A/B test the prompt change against the current baseline.",
        }),
    };

    private static ImprovementOpportunity MakeOpportunity(
        ImprovementArea area, string title, string rationale, string metric,
        double current, double target, double impact, Effort effort, List<string> actions)
    {
        var clampedImpact = Math.Clamp(impact, 0.01, 1.0);
        var effortWeight = effort switch { Effort.Low => 1.0, Effort.Medium => 2.0, _ => 3.0 };
        return new ImprovementOpportunity
        {
            Area = area, Title = title, Rationale = rationale, Metric = metric,
            CurrentValue = Math.Round(current, 4), TargetValue = Math.Round(target, 4),
            ExpectedImpact = Math.Round(clampedImpact, 4), Effort = effort,
            Priority = Math.Round(clampedImpact / effortWeight, 4), SuggestedActions = actions,
        };
    }

    // -------------------------------------------------------------------------
    // 3. Automated testing (A/B + canary)
    // -------------------------------------------------------------------------
    private static ExperimentDesign DesignExperiment(ImprovementOpportunity top, ImprovementRequest req)
    {
        // Sample size ~ 16·σ²/δ² (σ≈0.25 assumed), clamped to a practical range.
        var delta = Math.Max(0.01, top.ExpectedImpact);
        var n = (int)Math.Ceiling(16 * 0.0625 / (delta * delta));
        n = Math.Clamp(n, 50, 5000);

        return new ExperimentDesign
        {
            Name = $"exp-{top.Area}-{top.Metric}".ToLowerInvariant(),
            Hypothesis = $"{top.Title} raises {top.Metric} from {top.CurrentValue:0.###} toward {top.TargetValue:0.###}.",
            Variant = string.Join(" ", top.SuggestedActions),
            PrimaryMetric = top.Metric,
            GuardrailMetrics = new() { "latency_p95_ms", "cost_per_item", "safety" },
            MinSamplesPerArm = n,
            CanaryStages = new()
            {
                new() { TrafficPercent = 5, Guardrail = "no safety/latency regression" },
                new() { TrafficPercent = 25, Guardrail = $"{top.Metric} not worse than control" },
                new() { TrafficPercent = 50, Guardrail = $"{top.Metric} improving, guardrails green" },
                new() { TrafficPercent = 100, Guardrail = "primary metric significantly better" },
            },
            ValidationSteps = new()
            {
                "Run the batch evaluation quality gates on the variant.",
                "Performance test: confirm p95 latency within budget.",
                $"Require statistical significance on {top.Metric} before 100% rollout.",
            },
        };
    }

    private static string Summarize(QualityAnalysis a, List<ImprovementOpportunity> ops)
    {
        if (!a.HasData)
            return "No evaluation runs for this dataset/environment yet — run a batch evaluation first.";
        if (ops.Count == 0)
            return $"Quality is at/above target (overall {a.CurrentOverall:0.###}, trend {a.Trend}). No action needed.";
        var top = ops[0];
        return $"{ops.Count} opportunities (trend {a.Trend}). Top: {top.Title} " +
               $"[{top.Area}] — expected impact {top.ExpectedImpact:0.##}, effort {top.Effort}.";
    }
}
