# Frontend MVC del laboratorio

Implementación local en ASP.NET Core MVC / .NET 6, con vistas Razor y C#.
La referencia visual es el archivo Figma RuO1QF59HvUaUqZi41fAK3 y las capturas proporcionadas para las pantallas que el límite del conector impidió leer.

## Alcance

- Inicio y cinco vistas por módulo: listado, crear, detalles, editar y confirmar eliminación.
- Personas, Teléfonos, Profesiones y Estudios.
- Navegación lateral con módulo activo, tarjetas de inicio, formularios en dos columnas, tablas alternadas, botones y confirmaciones del diseño.
- Diseño adaptable; las tablas se desplazan horizontalmente en pantallas estrechas.
- Los datos de las tablas provienen de la base SQL Server configurada; no se muestran los registros ilustrativos de Figma. Las pruebas locales se realizaron con LocalDB.
- Tipografía Inter con alternativas locales Segoe UI y Arial si Inter no está instalada.

## Arquitectura

Los cuatro controladores MVC están en Controllers/, fuera de Controllers/Api/.
Usan las interfaces DAO y sus implementaciones existentes. Reutilizan los DTO existentes para la validación y conversión a entidades. Las vistas compartidas por cada módulo contienen campos y detalles, evitando duplicar sus definiciones.

Los enlaces y formularios especifican la ruta convencional "default" para evitar que la generación de URLs escoja una acción REST homónima.
Los controladores REST, Swagger, entidades, interfaces, repositorios, Program.cs y scripts SQL no se modificaron durante esta implementación. Se conservaron las modificaciones locales previas de configuración, proyecto y SQL.

## Validación y errores

- Anotaciones existentes de los DTO, en cliente y servidor.
- Mensajes de validación MVC en español.
- Selectores de personas y profesiones alimentados por los DAO.
- Comprobación de referencias y claves duplicadas antes de guardar.
- Claves inmutables en edición; Estudios conserva conjuntamente id_prof y cc_per.
- Confirmación por GET; eliminación únicamente por POST con token antifalsificación.
- Tokens antifalsificación también en altas y ediciones.
- Errores de integridad y concurrencia se presentan en el formulario.
- Una indisponibilidad de SQL presenta una página de servicio no disponible (HTTP 503).
- Registros inexistentes devuelven 404 y claves manipuladas devuelven 400.

## Ejecución

Se necesita una instancia SQL Server accesible con la base `persona_db` y las cuatro tablas preparadas. La aplicación no crea ni migra automáticamente la base. El script DDL recrea tablas: no ejecutarlo sobre datos que se deban conservar.

Configura la conexión mediante `ConnectionStrings__PersonaDb` en la misma sesión de PowerShell desde la que iniciarás la aplicación. Esta variable sobrescribe `ConnectionStrings:PersonaDb` de los archivos de configuración; no es necesario editar ni publicar `appsettings.Development.json`.

Desde la raíz, este ejemplo utiliza SQL Server LocalDB y autenticación integrada de Windows:

```powershell
dotnet build personapi-dotnet.sln
$env:ASPNETCORE_ENVIRONMENT = "Development"
$env:ConnectionStrings__PersonaDb = 'Server=(localdb)\MSSQLLocalDB;Database=persona_db;Trusted_Connection=True;TrustServerCertificate=True'
dotnet run --project personapi-dotnet --no-launch-profile --urls http://127.0.0.1:5025
```

Para otra instancia SQL Server, adapta el servidor y el método de autenticación. Por ejemplo, para SQL Server Express con autenticación de Windows, establece antes de ejecutar la aplicación:

```powershell
$env:ConnectionStrings__PersonaDb = 'Server=localhost\SQLEXPRESS;Database=persona_db;Trusted_Connection=True;TrustServerCertificate=True'
```

Los ejemplos con `TrustServerCertificate=True` son para desarrollo local. No publiques credenciales reales en el repositorio. La variable de este ejemplo se aplica al proceso y a sus hijos durante la sesión; debes configurarla nuevamente en una terminal nueva. El frontend no depende de la configuración personal del autor.

La interfaz está en http://127.0.0.1:5025 y Swagger en /swagger.

## Comprobación funcional reproducible

Con la aplicación en ejecución y PowerShell 7:

```powershell
./tests/mvc-smoke.ps1
# Otro puerto:
./tests/mvc-smoke.ps1 -BaseUrl http://127.0.0.1:5026
```

El script crea registros temporales identificados aleatoriamente, ejecuta los cuatro CRUD por formularios MVC y verifica la persistencia mediante GET de la API. Comprueba las acciones reales de los formularios Razor, duplicados, referencias inexistentes, campos inválidos, campos opcionales, tokens antifalsificación, bloqueo de cambios de claves, restricciones al eliminar y disponibilidad de Swagger.

La limpieza se ejecuta en finally, exclusivamente sobre los registros creados durante la prueba. Al terminar compara las respuestas originales de los cuatro listados REST para comprobar que los datos iniciales se conservaron. No ejecutar concurrentemente con otras escrituras sobre la misma base.

La compilación mantiene la advertencia NETSDK1138 del proyecto por utilizar net6.0. No se migró la versión del laboratorio.

## Resultado comprobado en el entorno local

- Compilación: 0 errores; advertencia NETSDK1138 existente.
- Prueba funcional final: 213 comprobaciones correctas contra SQL Server LocalDB.
- Inicio, las 20 vistas CRUD, API GET y Swagger respondieron correctamente durante la prueba.
- Indisponibilidad SQL simulada en otro proceso: HTTP 503 y página amigable correctos, sin modificar archivos de configuración.
- Revisión visual de inicio y pantallas representativas de listado, formularios, detalles y eliminación en el navegador.
- Pendiente: revisión visual del usuario y comprobación en otros navegadores y tamaños móviles.
