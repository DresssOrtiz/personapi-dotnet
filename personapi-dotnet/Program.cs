using System.Reflection;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;
using personapi_dotnet.Interfaces;
using personapi_dotnet.Models.Entities;
using personapi_dotnet.Repositories;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddControllersWithViews();

builder.Services.AddDbContext<persona_dbContext>(options =>
    options.UseSqlServer(builder.Configuration.GetConnectionString("PersonaDb")));

builder.Services.AddScoped<IPersonaRepository, PersonaRepository>();
builder.Services.AddScoped<ITelefonoRepository, TelefonoRepository>();
builder.Services.AddScoped<IProfesionRepository, ProfesionRepository>();
builder.Services.AddScoped<IEstudioRepository, EstudioRepository>();

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    // Solo documenta la API REST; las acciones MVC que devuelven vistas quedan fuera.
    options.DocInclusionPredicate((_, api) => api.RelativePath?.StartsWith("api/") == true);

    // Resúmenes y descripciones tomados de los comentarios /// de controladores y DTO.
    var xmlPath = Path.Combine(AppContext.BaseDirectory, $"{Assembly.GetExecutingAssembly().GetName().Name}.xml");
    if (File.Exists(xmlPath)) options.IncludeXmlComments(xmlPath);
});

var app = builder.Build();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
}

app.UseSwagger();
app.UseSwaggerUI();

// La API responde 503 con un mensaje controlado si no hay conexión con la base de datos;
// la traza queda solo en el registro del servidor.
app.UseWhen(context => context.Request.Path.StartsWithSegments("/api"), api =>
{
    api.Use(async (context, next) =>
    {
        try
        {
            await next();
        }
        catch (SqlException ex) when (!context.Response.HasStarted)
        {
            context.RequestServices.GetRequiredService<ILoggerFactory>()
                .CreateLogger("Api").LogError(ex, "Error de acceso a datos en la API");
            context.Response.StatusCode = StatusCodes.Status503ServiceUnavailable;
            await context.Response.WriteAsJsonAsync(new ProblemDetails
            {
                Status = StatusCodes.Status503ServiceUnavailable,
                Title = "La base de datos no está disponible en este momento. Inténtalo de nuevo más tarde."
            }, options: null, contentType: "application/problem+json");
        }
    });
});

app.UseWhen(context => !context.Request.Path.StartsWithSegments("/api"), mvc =>
{
    mvc.UseStatusCodePagesWithReExecute("/Home/PageNotFound");
    mvc.Use(async (context, next) =>
    {
        await next();
        if (context.Response.StatusCode != StatusCodes.Status404NotFound)
        {
            var statusPages = context.Features.Get<Microsoft.AspNetCore.Diagnostics.IStatusCodePagesFeature>();
            if (statusPages != null) statusPages.Enabled = false;
        }
    });
});

app.UseStaticFiles();

app.UseRouting();

app.UseAuthorization();

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

app.Run();
