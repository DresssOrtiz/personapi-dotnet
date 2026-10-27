using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;

namespace personapi_dotnet.Controllers;

[AutoValidateAntiforgeryToken]
public abstract class MvcControllerBase : Controller
{
    protected async Task<bool> SaveAsync(Func<Task> save)
    {
        try { await save(); return true; }
        catch (DbUpdateConcurrencyException ex)
        {
            Log(ex);
            ModelState.AddModelError("", "El registro fue modificado o eliminado. Vuelve al listado e inténtalo de nuevo.");
        }
        catch (DbUpdateException ex)
        {
            Log(ex);
            var sql = ex.GetBaseException() as SqlException;
            ModelState.AddModelError("", sql?.Number switch
            {
                2601 or 2627 => "Ya existe un registro con ese identificador.",
                547 => "No se pudo guardar: hay registros relacionados o una referencia que ya no existe.",
                _ => "No se pudo guardar el cambio. Comprueba los datos e inténtalo de nuevo."
            });
        }
        return false;
    }

    public override async Task OnActionExecutionAsync(ActionExecutingContext context, ActionExecutionDelegate next)
    {
        var result = await next();
        // Localiza los mensajes de los DTO solo al presentarlos en MVC.
        // La validación de la API REST permanece intacta.
        foreach (var entry in ModelState.Values)
        {
            for (var i = 0; i < entry.Errors.Count; i++)
            {
                var message = entry.Errors[i].ErrorMessage;
                var translated = message.Contains("is required")
                    ? "Este campo es obligatorio."
                    : message.Contains("must be between")
                        ? "Introduce un valor dentro del rango permitido."
                        : message.Contains("maximum length")
                            ? "El texto supera la longitud permitida."
                            : message.Contains("is not valid") || message.Contains("is invalid")
                                ? "Introduce un valor válido para este campo."
                                : null;
                if (translated != null)
                    entry.Errors[i] = new Microsoft.AspNetCore.Mvc.ModelBinding.ModelError(translated);
            }
        }
        if (result.Exception is SqlException or DbUpdateException && !result.ExceptionHandled)
        {
            Log(result.Exception);
            Response.StatusCode = StatusCodes.Status503ServiceUnavailable;
            result.Result = View("DatabaseError");
            result.ExceptionHandled = true;
        }
    }

    private void Log(Exception ex) => HttpContext.RequestServices
        .GetRequiredService<ILogger<MvcControllerBase>>().LogError(ex, "Error de acceso a datos en MVC");
}
