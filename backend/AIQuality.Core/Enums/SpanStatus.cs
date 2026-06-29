namespace AIQuality.Core.Enums;

// Status of a span, mirroring the OpenTelemetry status code semantics.
//   Unset = no explicit status was set (the default).
//   Ok    = the operation completed successfully.
//   Error = the operation failed; pair with an error event/attribute for detail.
public enum SpanStatus
{
    Unset,
    Ok,
    Error
}
