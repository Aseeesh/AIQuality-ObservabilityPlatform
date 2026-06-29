using AIQuality.Infrastructure.Data;

namespace AIQuality.Infrastructure.Repositories;

// Persistence for incidents.
public class IncidentRepository
{
    private readonly ApplicationDbContext _db;
    public IncidentRepository(ApplicationDbContext db) => _db = db;
    // TODO: CRUD/query methods for Incident.
}
