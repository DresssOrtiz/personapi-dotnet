using Microsoft.EntityFrameworkCore;
using personapi_dotnet.Interfaces;
using personapi_dotnet.Models.Entities;

namespace personapi_dotnet.Repositories
{
    public class TelefonoRepository : ITelefonoRepository
    {
        private readonly persona_dbContext _context;

        public TelefonoRepository(persona_dbContext context)
        {
            _context = context;
        }

        public async Task<IEnumerable<Telefono>> GetAllAsync()
        {
            return await _context.Telefonos.AsNoTracking().OrderBy(t => t.Num).ToListAsync();
        }

        public async Task<Telefono?> GetByIdAsync(string num)
        {
            return await _context.Telefonos.AsNoTracking().FirstOrDefaultAsync(t => t.Num == num);
        }

        public async Task<bool> ExistsAsync(string num)
        {
            return await _context.Telefonos.AnyAsync(t => t.Num == num);
        }

        public async Task AddAsync(Telefono telefono)
        {
            _context.Telefonos.Add(telefono);
            await _context.SaveChangesAsync();
        }

        public async Task UpdateAsync(Telefono telefono)
        {
            _context.Telefonos.Update(telefono);
            await _context.SaveChangesAsync();
        }

        public async Task DeleteAsync(string num)
        {
            var telefono = await _context.Telefonos.FindAsync(num);
            if (telefono == null) return;
            _context.Telefonos.Remove(telefono);
            await _context.SaveChangesAsync();
        }
    }
}
