# personapi-dotnet

Laboratorio 1 - Arquitectura de Software (Pontificia Universidad Javeriana).
Monolito ASP.NET Core MVC con patrón DAO/Repository, SQL Server y API REST documentada con Swagger.

## Stack

| Componente | Versión |
|---|---|
| .NET / ASP.NET Core | 6.0 (el enunciado menciona 7 en el stack y 6 en el procedimiento; se usa 6.0) |
| Entity Framework Core | 6.0.36 (Database First) |
| Base de datos | Microsoft SQL Server 2022 |
| Documentación API | Swagger / OpenAPI (Swashbuckle.AspNetCore 6.5.0) |

## Estructura

```
db/01_ddl.sql                 Script DDL (base persona_db y tablas)
db/02_dml.sql                 Script DML (datos de prueba)
personapi-dotnet/
  Models/Entities/            Entidades y DbContext generados con scaffold
  Models/Dtos/                DTOs de la API REST
  Interfaces/                 Contratos DAO (IPersonaRepository, ...)
  Repositories/               Implementaciones con EF Core
  Controllers/Api/            Controladores REST (/api/...)
  Controllers/                Controladores MVC (vistas)
```

## Configuración del ambiente

### 1. Requisitos

- [.NET SDK 6.0](https://dotnet.microsoft.com/download/dotnet/6.0)
- SQL Server 2022 (Windows: SQL Server Express + SSMS; macOS/Linux: Docker)
- Herramienta `dotnet-ef`: `dotnet tool install --global dotnet-ef --version 6.0.36`

### 2. Base de datos

**Opción A - Docker (macOS/Linux/Windows):**

```bash
docker run -d --name persona-sql --platform linux/amd64 \
  -e ACCEPT_EULA=Y -e 'MSSQL_SA_PASSWORD=Persona_Lab1#2026' \
  -p 1433:1433 mcr.microsoft.com/mssql/server:2022-latest

docker exec -i persona-sql /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P 'Persona_Lab1#2026' -C -b -i /dev/stdin < db/01_ddl.sql
docker exec -i persona-sql /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P 'Persona_Lab1#2026' -C -b -i /dev/stdin < db/02_dml.sql
```

**Opción B - SQL Server Express + SSMS (Windows):** abrir `db/01_ddl.sql` y luego `db/02_dml.sql`
en SSMS conectado a `localhost\SQLEXPRESS` y ejecutarlos en ese orden. El DDL crea `persona_db`
y le asigna la propiedad al usuario `sa`.

### 3. Cadena de conexión

Está en `personapi-dotnet/appsettings.json` (clave `ConnectionStrings:PersonaDb`). Por defecto apunta
al contenedor Docker de arriba:

```
Server=localhost,1433;Database=persona_db;User Id=sa;Password=Persona_Lab1#2026;TrustServerCertificate=true
```

Con SQL Server Express en Windows usar, por ejemplo:
`Server=localhost\SQLEXPRESS;Database=persona_db;Trusted_Connection=True;TrustServerCertificate=true`.
También se puede sobrescribir sin editar el archivo con la variable de entorno
`ConnectionStrings__PersonaDb`.

### 4. Entidades (ya generadas)

Las entidades se generaron con Database First. Para regenerarlas:

```bash
# Consola del Administrador de paquetes (Visual Studio)
Scaffold-DbContext "Server=localhost\SQLEXPRESS;Database=persona_db;Trusted_Connection=True;TrustServerCertificate=true" Microsoft.EntityFrameworkCore.SqlServer -OutputDir Models/Entities -Force

# Equivalente con la CLI (macOS/Linux/Windows), desde la carpeta personapi-dotnet/personapi-dotnet
dotnet ef dbcontext scaffold "<cadena de conexión>" Microsoft.EntityFrameworkCore.SqlServer -o Models/Entities --context-dir Models/Entities --force
```

Tras regenerar, eliminar el método `OnConfiguring` del `persona_dbContext` para no dejar la
cadena de conexión en el código.

## Compilación y ejecución

```bash
dotnet build
cd personapi-dotnet
dotnet run --urls http://localhost:5025
```

- Aplicación MVC: <http://localhost:5025>
- Swagger UI: <http://localhost:5025/swagger>

## API REST

| Recurso | Rutas |
|---|---|
| Personas | `GET/POST /api/personas`, `GET/PUT/DELETE /api/personas/{cc}` |
| Teléfonos | `GET/POST /api/telefonos`, `GET/PUT/DELETE /api/telefonos/{num}` |
| Profesiones | `GET/POST /api/profesiones`, `GET/PUT/DELETE /api/profesiones/{id}` |
| Estudios | `GET/POST /api/estudios`, `GET/PUT/DELETE /api/estudios/{idProf}/{ccPer}` |

Códigos de respuesta: `200` consulta, `201` creado, `204` actualizado/eliminado, `400` solicitud
inválida (validación, clave de ruta distinta a la del cuerpo, persona o profesión inexistente),
`404` no encontrado y `409` conflicto (clave duplicada o registro con dependencias, p. ej. eliminar una
persona con teléfonos o estudios).

## Despliegue

Publicación local de la aplicación:

```bash
dotnet publish personapi-dotnet/personapi-dotnet.csproj -c Release -o publish
ASPNETCORE_URLS=http://localhost:5025 dotnet publish/personapi-dotnet.dll
```

La base de datos debe estar disponible con la cadena de conexión configurada.
