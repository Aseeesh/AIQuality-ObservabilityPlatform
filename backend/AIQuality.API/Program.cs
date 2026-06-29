// API host bootstrap: DI registration and middleware pipeline.
using AIQuality.Core.Interfaces;
using AIQuality.Infrastructure.Data;
using AIQuality.Infrastructure.Services;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();

// Persistence: in-memory EF Core provider for local/dev runs.
// Swap UseInMemoryDatabase for UseNpgsql(connectionString) in production.
builder.Services.AddDbContext<ApplicationDbContext>(opt => opt.UseInMemoryDatabase("aiquality"));

// Application/infrastructure services.
builder.Services.AddScoped<ITracingService, TracingService>();

// Allow the Vite dev server to call the API.
builder.Services.AddCors(o => o.AddDefaultPolicy(p =>
    p.WithOrigins("http://localhost:5173").AllowAnyHeader().AllowAnyMethod()));

var app = builder.Build();

app.UseCors();
app.MapControllers();
app.MapGet("/health", () => Results.Ok(new { status = "healthy" }));
app.Run();
