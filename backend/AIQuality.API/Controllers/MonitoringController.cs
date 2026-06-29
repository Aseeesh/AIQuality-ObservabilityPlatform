using Microsoft.AspNetCore.Mvc;

namespace AIQuality.API.Controllers;

// Expose live metrics, health, and anomaly signals.
[ApiController]
[Route("api/monitoring")]
public class MonitoringController : ControllerBase
{
    [HttpGet]
    public IActionResult Get() => Ok(new { message = "Monitoring endpoint — TODO" });
}
