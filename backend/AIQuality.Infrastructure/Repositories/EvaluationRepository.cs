using AIQuality.Infrastructure.Data;

namespace AIQuality.Infrastructure.Repositories;

// Persistence for evaluation runs.
public class EvaluationRepository
{
    private readonly ApplicationDbContext _db;
    public EvaluationRepository(ApplicationDbContext db) => _db = db;
    // TODO: CRUD/query methods for EvaluationRun.
}
