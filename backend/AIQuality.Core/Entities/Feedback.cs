namespace AIQuality.Core.Entities;

// A unit of user or automated feedback on an AI response.
public class Feedback
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Source { get; set; } = string.Empty;
    public int Rating { get; set; }
    public string Comment { get; set; } = string.Empty;
}
