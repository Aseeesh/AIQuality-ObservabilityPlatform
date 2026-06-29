// API host bootstrap: DI registration, middleware pipeline, and OpenTelemetry wiring.
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
// TODO: register application/infrastructure services (tracing, evaluation, SLO, incidents).

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

// TODO: app.UseMiddleware<TracingMiddleware>(); etc.
app.UseHttpsRedirection();
app.MapControllers();
app.Run();
