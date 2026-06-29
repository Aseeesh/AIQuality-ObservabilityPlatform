namespace AIQuality.Core.Entities;

// A batch evaluation of model outputs by an LLM judge.
public class EvaluationRun
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Dataset { get; set; } = string.Empty;
    public double Score { get; set; }
    public DateTimeOffset RunAt { get; set; }
}
