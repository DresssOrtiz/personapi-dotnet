using Microsoft.EntityFrameworkCore;
using personapi_dotnet.Interfaces;
using personapi_dotnet.Models.Entities;

namespace personapi_dotnet.Repositories
{
    public class PersonaRepository : IPersonaRepository
    {
        private readonly persona_dbContext _context;

        public PersonaRepository(persona_dbContext context)
        {
            _context = context;
        }

        public async Task<IEnumerable<Persona>> GetAllAsync()
        {
            return await _context.Personas.AsNoTracking().OrderBy(p => p.Cc).ToListAsync();
        }

        public async Task<Persona?> GetByIdAsync(int cc)
        {
            return await _context.Personas.AsNoTracking().FirstOrDefaultAsync(p => p.Cc == cc);
        }

        public async Task<bool> ExistsAsync(int cc)
        {
            return await _context.Personas.AnyAsync(p => p.Cc == cc);
        }

        public async Task AddAsync(Persona persona)
        {
            _context.Personas.Add(persona);
            await _context.SaveChangesAsync();
        }

        public async Task UpdateAsync(Persona persona)
        {
            _context.Personas.Update(persona);
            await _context.SaveChangesAsync();
        }

        public async Task DeleteAsync(int cc)
        {
            var persona = await _context.Personas.FindAsync(cc);
            if (persona == null) return;
            _context.Personas.Remove(persona);
            await _context.SaveChangesAsync();
        }
    }
}
