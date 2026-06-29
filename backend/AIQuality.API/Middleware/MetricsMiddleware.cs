namespace AIQuality.API.Middleware;

// Record latency, throughput, and error metrics per request.
public class MetricsMiddleware
{
    private readonly RequestDelegate _next;
    public MetricsMiddleware(RequestDelegate next) => _next = next;

    public async Task InvokeAsync(HttpContext context)
    {
        // TODO: Record latency, throughput, and error metrics per request.
        await _next(context);
    }
}
