namespace AIQuality.API.Middleware;

// Apply inline quality gates / guardrails to responses.
public class QualityMiddleware
{
    private readonly RequestDelegate _next;
    public QualityMiddleware(RequestDelegate next) => _next = next;

    public async Task InvokeAsync(HttpContext context)
    {
        // TODO: Apply inline quality gates / guardrails to responses.
        await _next(context);
    }
}
