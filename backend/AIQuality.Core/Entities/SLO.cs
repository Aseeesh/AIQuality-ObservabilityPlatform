namespace AIQuality.Core.Entities;

// A service-level objective and its target.
public class SLO
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Name { get; set; } = string.Empty;
    public double Target { get; set; }
    public double ErrorBudget { get; set; }
}
