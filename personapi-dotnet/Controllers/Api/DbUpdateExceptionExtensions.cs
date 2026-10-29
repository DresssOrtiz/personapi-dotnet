using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;

namespace personapi_dotnet.Controllers.Api
{
    public static class DbUpdateExceptionExtensions
    {
        // 2601: índice único duplicado; 2627: clave primaria o restricción única duplicada.
        public static bool IsDuplicateKey(this DbUpdateException ex) =>
            ex.GetBaseException() is SqlException { Number: 2601 or 2627 };
    }
}
