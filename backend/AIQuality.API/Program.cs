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
// Evaluation: default heuristic scorer (swap for the Python LLM judge in prod); the service
// keeps an in-memory run history for regression detection, so it is a singleton.
builder.Services.AddSingleton<IOutputEvaluator, AIQuality.API.Services.HeuristicOutputEvaluator>();
builder.Services.AddSingleton<IEvaluationService, AIQuality.API.Services.EvaluationService>();
// Improvement pipeline reads the evaluation history (singleton) to plan changes.
builder.Services.AddSingleton<IImprovementService, AIQuality.API.Services.ImprovementService>();

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

// Allow the Vite dev server to call the API.
builder.Services.AddCors(o => o.AddDefaultPolicy(p =>
    p.WithOrigins("http://localhost:5173").AllowAnyHeader().AllowAnyMethod()));

var app = builder.Build();

app.UseCors();
app.MapControllers();
app.MapGet("/health", () => Results.Ok(new { status = "healthy" }));
app.Run();
