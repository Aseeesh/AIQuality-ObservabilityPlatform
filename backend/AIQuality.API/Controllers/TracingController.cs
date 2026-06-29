using Microsoft.AspNetCore.Mvc;

namespace AIQuality.API.Controllers;

// Ingest and query distributed traces/spans for AI requests.
[ApiController]
[Route("api/tracing")]
public class TracingController : ControllerBase
{
    [HttpGet]
    public IActionResult Get() => Ok(new { message = "Tracing endpoint — TODO" });
}
