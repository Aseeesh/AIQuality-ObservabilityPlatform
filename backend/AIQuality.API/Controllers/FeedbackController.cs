using Microsoft.AspNetCore.Mvc;

namespace AIQuality.API.Controllers;

// Collect and surface user/automated feedback signals.
[ApiController]
[Route("api/feedback")]
public class FeedbackController : ControllerBase
{
    [HttpGet]
    public IActionResult Get() => Ok(new { message = "Feedback endpoint — TODO" });
}
