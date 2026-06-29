namespace AIQuality.API.Middleware;

// Start a span per request and propagate trace context.
public class TracingMiddleware
{
    private readonly RequestDelegate _next;
    public TracingMiddleware(RequestDelegate next) => _next = next;

    public async Task InvokeAsync(HttpContext context)
    {
        // TODO: Start a span per request and propagate trace context.
        await _next(context);
    }
}
