using AIQuality.Infrastructure.Data;

namespace AIQuality.Infrastructure.Repositories;

// Persistence for traces/spans.
public class TraceRepository
{
    private readonly ApplicationDbContext _db;
    public TraceRepository(ApplicationDbContext db) => _db = db;
    // TODO: CRUD/query methods for Trace.
}
