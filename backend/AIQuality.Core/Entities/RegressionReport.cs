namespace AIQuality.Core.Entities;

// Result of comparing a run against its baseline (the previous run on the same
// dataset+environment). Degradation requires both a meaningful drop AND statistical
// significance, so normal run-to-run noise doesn't raise false alarms.
public class RegressionReport
{
    public bool HasBaseline { get; set; }
    public Guid? BaselineRunId { get; set; }

    public double BaselineMean { get; set; }
    public double CurrentMean { get; set; }
    public double ScoreDelta { get; set; }       // current - baseline (negative = worse)
    public double LatencyDeltaMs { get; set; }   // current - baseline

    public double TStatistic { get; set; }       // Welch's t over per-item scores
    public bool Significant { get; set; }         // |t| > ~2 (p < 0.05)
    public bool Degraded { get; set; }            // significant AND ScoreDelta below tolerance

    public List<string> Alerts { get; set; } = new();
    public string Summary { get; set; } = string.Empty;
}
