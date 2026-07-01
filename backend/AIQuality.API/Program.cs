// API host bootstrap: DI registration, OpenTelemetry tracing, and middleware pipeline.
using AIQuality.API.Services;
using AIQuality.Core.Interfaces;
using AIQuality.Infrastructure.Data;
using AIQuality.Infrastructure.Services;
using Microsoft.EntityFrameworkCore;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();

// Persistence: in-memory EF Core provider for local/dev runs.
// Swap UseInMemoryDatabase for UseNpgsql(connectionString) in production.
builder.Services.AddDbContext<ApplicationDbContext>(opt => opt.UseInMemoryDatabase("aiquality"));

// Application/infrastructure services.
builder.Services.AddScoped<ITracingService, AIQuality.Infrastructure.Services.TracingService>();  // coarse trace records (EF)
// Span-level distributed tracing holds an in-memory query store, so it must be a singleton.
builder.Services.AddSingleton<IDistributedTracingService, AIQuality.API.Services.TracingService>();
// Evaluation scorer. When EVALUATOR_URL is set, use the Python quality-evaluator (Ollama-backed
// LLM-as-Judge) over HTTP, with the local heuristic as an automatic fallback; otherwise use the
// heuristic directly. The evaluation service keeps an in-memory run history, so it is a singleton.
builder.Services.AddSingleton<AIQuality.API.Services.HeuristicOutputEvaluator>();
var evaluatorUrl = builder.Configuration["EVALUATOR_URL"] ?? Environment.GetEnvironmentVariable("EVALUATOR_URL");
if (!string.IsNullOrWhiteSpace(evaluatorUrl))
{
    builder.Services.AddSingleton<IOutputEvaluator>(sp => new AIQuality.API.Services.OllamaOutputEvaluator(
        new HttpClient { Timeout = TimeSpan.FromSeconds(120) },  // LLM calls can be slow locally
        sp.GetRequiredService<AIQuality.API.Services.HeuristicOutputEvaluator>(),
        evaluatorUrl));
}
else
{
    builder.Services.AddSingleton<IOutputEvaluator>(sp =>
        sp.GetRequiredService<AIQuality.API.Services.HeuristicOutputEvaluator>());
}
builder.Services.AddSingleton<IEvaluationService, AIQuality.API.Services.EvaluationService>();
// Improvement pipeline reads the evaluation history (singleton) to plan changes.
builder.Services.AddSingleton<IImprovementService, AIQuality.API.Services.ImprovementService>();
// SLO tracking keeps rolling SLI windows in memory, so it is a singleton.
builder.Services.AddSingleton<ISLOService, AIQuality.API.Services.SLOService>();
// Incident management: notification channels (fanned out by severity) + the service (singleton,
// in-memory incident store; uses the tracing analyzer for automated RCA).
builder.Services.AddSingleton<INotificationChannel, AIQuality.API.Services.Notifications.PagerDutyChannel>();
builder.Services.AddSingleton<INotificationChannel, AIQuality.API.Services.Notifications.OpsGenieChannel>();
builder.Services.AddSingleton<INotificationChannel, AIQuality.API.Services.Notifications.SlackChannel>();
builder.Services.AddSingleton<INotificationChannel, AIQuality.API.Services.Notifications.EmailChannel>();
builder.Services.AddSingleton<IIncidentService, AIQuality.API.Services.IncidentService>();

// ---- OpenTelemetry tracing ----
// Head-based sampling is configured here (ParentBased + TraceIdRatioBased). The span query
// store inside TracingService applies its own tail-sampling, so dropping a span for export
// never drops it from the dashboard.
var otlpEndpoint = builder.Configuration["OpenTelemetry:Endpoint"] ?? "http://localhost:4317";
var samplingRatio = builder.Configuration.GetValue("OpenTelemetry:SamplingRatio", 1.0);
builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService(serviceName: "aiquality-api", serviceVersion: "1.0.0"))
    .WithTracing(t => t
        .SetSampler(new ParentBasedSampler(new TraceIdRatioBasedSampler(samplingRatio)))
        .AddSource(AIQuality.API.Services.TracingService.ActivitySource.Name)
        .AddAspNetCoreInstrumentation()
        // Exports OTLP/gRPC to the Jaeger collector (jaeger all-in-one exposes 4317).
        .AddOtlpExporter(o => o.Endpoint = new Uri(otlpEndpoint)));

// Allow the dashboard to call the API: the nginx-served bundle (Docker, :3000) and the Vite dev
// server (:5173). Override with CORS_ORIGINS (comma-separated) if you host it elsewhere.
var corsOrigins = (builder.Configuration["CORS_ORIGINS"] ?? "http://localhost:3000,http://localhost:5173")
    .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
builder.Services.AddCors(o => o.AddDefaultPolicy(p =>
    p.WithOrigins(corsOrigins).AllowAnyHeader().AllowAnyMethod()));

var app = builder.Build();

app.UseCors();
app.MapControllers();
app.MapGet("/health", () => Results.Ok(new { status = "healthy" }));
app.Run();
