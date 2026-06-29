using Microsoft.AspNetCore.Mvc;

namespace AIQuality.API.Controllers;

// Manage SLO definitions and report error-budget burn.
[ApiController]
[Route("api/slo")]
public class SLOController : ControllerBase
{
    [HttpGet]
    public IActionResult Get() => Ok(new { message = "SLO endpoint — TODO" });
}
