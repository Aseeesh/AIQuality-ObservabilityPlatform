using System.Diagnostics;
using System.Net.Http.Json;
using AIQuality.Core.Entities;
using AIQuality.Core.Enums;
using AIQuality.Core.Interfaces;

namespace AIQuality.API.Services;

// IOutputEvaluator backed by the Python quality-evaluator service (a calibrated LLM-as-Judge
// that uses a local Ollama model). Selected when EVALUATOR_URL is configured; falls back to the
// local heuristic evaluator if the service is unreachable, so the API never hard-fails on a
// judge outage. This is what makes the .NET quality gates run against the real Ollama judge.
public class OllamaOutputEvaluator : IOutputEvaluator
{
    private readonly HttpClient _http;
    private readonly HeuristicOutputEvaluator _fallback;
    private readonly string _url;

    public OllamaOutputEvaluator(HttpClient http, HeuristicOutputEvaluator fallback, string evaluatorUrl)
    {
        _http = http;
        _fallback = fallback;
        _url = evaluatorUrl.TrimEnd('/');
    }

    // Rubric names come from the same source as the heuristic so aggregation lines up.
    public IReadOnlyList<string> RubricsFor(string rubricSet) => _fallback.RubricsFor(rubricSet);

    public async Task<EvaluationItemResult> EvaluateAsync(EvaluationItem item, string rubricSet, CancellationToken ct = default)
    {
        var sw = Stopwatch.StartNew();
        try
        {
            var response = await _http.PostAsJsonAsync($"{_url}/evaluate", new
            {
                prompt = item.Prompt, output = item.Output, context = item.Context,
                references = item.References, rubric_set = rubricSet,
            }, ct);
            response.EnsureSuccessStatusCode();
            var body = await response.Content.ReadFromJsonAsync<EvalResponse>(cancellationToken: ct)
                       ?? throw new InvalidOperationException("empty evaluator response");
            sw.Stop();

            return new EvaluationItemResult
            {
                ItemId = item.Id,
                Scores = body.Scores ?? new(),
                Overall = body.Overall,
                Verdict = ParseVerdict(body.Verdict),
                LatencyMs = sw.ElapsedMilliseconds,
                CostUsd = 0m,               // local model — no per-call cost
                Safe = body.Safe,
            };
        }
        catch
        {
            // Judge unreachable → degrade to the local heuristic rather than failing the run.
            return await _fallback.EvaluateAsync(item, rubricSet, ct);
        }
    }

    private static QualityGateStatus ParseVerdict(string? verdict) => verdict switch
    {
        "Passed" => QualityGateStatus.Passed,
        "Warning" => QualityGateStatus.Warning,
        _ => QualityGateStatus.Failed,
    };

    private sealed class EvalResponse
    {
        public Dictionary<string, double>? Scores { get; set; }
        public double Overall { get; set; }
        public string? Verdict { get; set; }
        public bool Safe { get; set; }
    }
}
