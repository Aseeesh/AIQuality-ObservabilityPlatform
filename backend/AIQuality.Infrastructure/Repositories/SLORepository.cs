using AIQuality.Infrastructure.Data;

namespace AIQuality.Infrastructure.Repositories;

// Persistence for SLO definitions and budgets.
public class SLORepository
{
    private readonly ApplicationDbContext _db;
    public SLORepository(ApplicationDbContext db) => _db = db;
    // TODO: CRUD/query methods for SLO.
}
