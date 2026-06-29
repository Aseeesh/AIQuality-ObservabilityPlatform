using Microsoft.EntityFrameworkCore;
using AIQuality.Core.Entities;

namespace AIQuality.Infrastructure.Data;

// EF Core DbContext mapping platform entities to Postgres.
public class ApplicationDbContext : DbContext
{
    public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options) : base(options) { }

    public DbSet<Trace> Traces => Set<Trace>();
    public DbSet<EvaluationRun> EvaluationRuns => Set<EvaluationRun>();
    public DbSet<SLO> SLOs => Set<SLO>();
    public DbSet<Incident> Incidents => Set<Incident>();
    public DbSet<Feedback> Feedback => Set<Feedback>();
}
