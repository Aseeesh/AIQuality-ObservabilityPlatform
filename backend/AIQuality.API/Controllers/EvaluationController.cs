using Microsoft.AspNetCore.Mvc;

namespace AIQuality.API.Controllers;

// Trigger and query LLM-as-judge evaluation runs.
[ApiController]
[Route("api/evaluation")]
public class EvaluationController : ControllerBase
{
    [HttpGet]
    public IActionResult Get() => Ok(new { message = "Evaluation endpoint — TODO" });
}
