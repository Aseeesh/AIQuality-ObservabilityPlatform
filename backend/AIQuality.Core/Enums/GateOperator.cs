namespace AIQuality.Core.Enums;

// Comparison applied by a quality gate: the actual metric value must satisfy
//   Gte: actual >= threshold   (higher-is-better metrics, e.g. accuracy)
//   Lte: actual <= threshold   (lower-is-better metrics, e.g. latency, cost)
public enum GateOperator
{
    Gte,
    Lte
}
