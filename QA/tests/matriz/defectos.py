"""Defectos encontrados durante la ejecucion de la matriz (hoja Defectos).

Cada defecto se asocia a uno o varios casos. La correccion se propone en
Observaciones; el codigo del repositorio no se modifica.
"""

DEFECTOS = [
    {
        "id": "DEF-01", "casos": ["API-GEN-05"], "req": "R09", "area": "API REST",
        "descripcion": "Dos POST simultaneos con la misma clave devuelven 500 en el segundo en lugar de 409.",
        "pasos": "1. Levantar main con dotnet run. 2. Enviar a la vez dos POST /api/personas con el mismo cc "
                 "(p. ej. 2050). 3. Repetir 20 veces con claves distintas (QA/tests/api/api_tests.py).",
        "esperado": "Esperado: 201 y 409, sin error 500. Obtenido: 201 y 500 en 20 de 20 pares; el 500 incluye la "
                    "traza DbUpdateException/SqlException 2627 (PK_persona). No se crean duplicados.",
        "severidad": "Media", "responsable": "Tomás", "evidencia": "EV-API-GEN-05.txt",
        "observaciones": "Causa: el controlador consulta ExistsAsync y luego inserta (condicion de carrera). Propuesta: "
                         "capturar DbUpdateException con SqlException.Number 2627/2601 en Create y responder 409 "
                         "(mismo patron que MvcControllerBase.SaveAsync). Aplica a los 4 controladores REST.",
    },
    {
        "id": "DEF-02", "casos": ["ENT-08"], "req": "R10", "area": "Repositorio y entrega",
        "descripcion": "El comando de despliegue del README inicia la aplicacion sin cadena de conexion y todas las "
                       "solicitudes a datos responden 500.",
        "pasos": "1. dotnet publish personapi-dotnet/personapi-dotnet.csproj -c Release -o publish. "
                 "2. Desde la raiz: ASPNETCORE_URLS=http://localhost:5025 dotnet publish/personapi-dotnet.dll. "
                 "3. GET /api/personas.",
        "esperado": "Esperado: la aplicacion publicada responde igual que en desarrollo. Obtenido: 500; log: "
                    "ArgumentNullException (Parameter 'connectionString'). El content root es la carpeta actual y "
                    "no carga publish/appsettings.json. Desde la carpeta publish responde 200.",
        "severidad": "Media", "responsable": "Tomás", "evidencia": "EV-ENT-08.txt",
        "observaciones": "Propuesta: cambiar el README a 'cd publish && ASPNETCORE_URLS=... dotnet personapi-dotnet.dll' "
                         "o agregar --contentRoot publish; alternativamente indicar ConnectionStrings__PersonaDb.",
    },
    {
        "id": "DEF-03", "casos": ["BK-09"], "req": "R03", "area": "Backend y DAO",
        "descripcion": "Con SQL Server detenido, la API responde 500 con la traza completa de la excepcion.",
        "pasos": "1. Ejecutar la rama feature/frontend-mvc con dotnet run (entorno Development segun el README). "
                 "2. docker stop persona-sql. 3. GET /api/personas.",
        "esperado": "Esperado: error controlado sin detalles internos. Obtenido: la vista responde 503 con mensaje "
                    "controlado, pero la API responde 500 text/plain con SqlException y la pila de llamadas. No se "
                    "exponen credenciales.",
        "severidad": "Baja", "responsable": "Tomás", "evidencia": "EV-BK-09.txt, EV-BK-09-vista.png",
        "observaciones": "Se presenta en Development (pagina de excepciones del desarrollador). Propuesta: filtro o "
                         "middleware para /api que devuelva ProblemDetails 503 ante SqlException en todos los "
                         "entornos, como ya hace MvcControllerBase para las vistas.",
    },
    {
        "id": "DEF-04", "casos": ["BD-08"], "req": "R01", "area": "Base de datos",
        "descripcion": "Re-ejecutar el DDL borra las 4 tablas y sus datos sin advertencia en el README ni en el script.",
        "pasos": "1. Ejecutar 01_ddl.sql y 02_dml.sql. 2. Ejecutar de nuevo 01_ddl.sql. 3. SELECT COUNT(*) de persona.",
        "esperado": "Esperado: comportamiento documentado. Obtenido: DROP TABLE de las 4 tablas, persona pasa de 5 a "
                    "0 registros; el DML restaura los datos, pero el README no lo advierte.",
        "severidad": "Baja", "responsable": "Tomás", "evidencia": "EV-BD-08.txt",
        "observaciones": "Propuesta: advertir en el README y en el encabezado de 01_ddl.sql que el script recrea las "
                         "tablas, o crear las tablas solo si no existen.",
    },
    {
        "id": "DEF-05", "casos": ["BD-07"], "req": "R01", "area": "Base de datos",
        "descripcion": "ALTER AUTHORIZATION ... TO sa hace fallar el DDL cuando el usuario no tiene permisos sobre "
                       "sa; el README no documenta el ajuste usado en LocalDB.",
        "pasos": "1. Crear un login con rol dbcreator (sin sysadmin). 2. Ejecutar 01_ddl.sql sin cambios con ese "
                 "login (QA/tests/db/bd07_entornos.py).",
        "esperado": "Esperado: el script corre sin cambios o el ajuste queda documentado. Obtenido: Msg 15151 "
                    "'Cannot find the principal sa...' y el DDL se detiene. El documento (sec. 3.2) indica que en "
                    "LocalDB se quito esa instruccion manualmente.",
        "severidad": "Baja", "responsable": "Tomás", "evidencia": "EV-BD-07.txt",
        "observaciones": "No se reprodujo en LocalDB (no disponible en macOS); el fallo se reprodujo con un login sin "
                         "sysadmin. Propuesta: quitar ALTER AUTHORIZATION o envolverlo en IF IS_SRVROLEMEMBER"
                         "('sysadmin') = 1, y documentar LocalDB en el README.",
    },
    {
        "id": "DEF-06", "casos": ["MVC-PER-05", "MVC-TEL-05", "MVC-PRO-05", "MVC-EST-05", "MVC-GEN-07"],
        "req": "R07", "area": "Frontend MVC",
        "descripcion": "Las claves y rutas inexistentes devuelven 404 sin contenido; el usuario ve una pagina en "
                       "blanco o la pagina generica del navegador.",
        "pasos": "1. Ejecutar feature/frontend-mvc. 2. Abrir /Personas/Details?cc=999999 o /RutaQueNoExiste/Accion.",
        "esperado": "Esperado: pagina de no encontrado controlada. Obtenido: HTTP 404 sin cuerpo, sin layout ni "
                    "enlace para volver.",
        "severidad": "Baja", "responsable": "Andrés", "evidencia": "EV-MVC-PER-05-inexistente.png, EV-MVC-GEN-07.png",
        "observaciones": "Propuesta: app.UseStatusCodePagesWithReExecute(\"/Home/Error\", \"?code={0}\") en Program.cs y "
                         "una vista de no encontrado con el layout de la aplicacion.",
    },
    {
        "id": "DEF-07", "casos": ["MVC-PER-01"], "req": "R07", "area": "Frontend MVC",
        "descripcion": "El listado de personas no muestra la columna edad.",
        "pasos": "1. Abrir /Personas desde el menu.",
        "esperado": "Esperado: columnas cc, nombre, apellido, genero y edad. Obtenido: Cedula, Nombre, Apellido, "
                    "Genero y Acciones; la edad solo aparece en Detalles.",
        "severidad": "Baja", "responsable": "Andrés", "evidencia": "EV-MVC-PER-01.png",
        "observaciones": "Propuesta: agregar <th>Edad</th> y <td>@item.Edad</td> en Views/Personas/Index.cshtml, o "
                         "ajustar el caso si la omision fue una decision de diseno (comparar con Figma).",
    },
    {
        "id": "DEF-08", "casos": ["ENT-11"], "req": "R11", "area": "Repositorio y entrega",
        "descripcion": "El documento conserva 8 marcadores de captura sin completar y las figuras no estan numeradas.",
        "pasos": "1. Abrir el documento del laboratorio. 2. Buscar el texto '*[' y 'Figura X'.",
        "esperado": "Esperado: ningun marcador pendiente y figuras numeradas. Obtenido: marcadores en las secciones "
                    "2.4, 2.5, 3.2, 3.3, 3.5, 3.6 y 3.7 (dos); los pies de figura usan 'Figura X'.",
        "severidad": "Baja", "responsable": "Andrés", "evidencia": "EV-ENT-11.txt",
        "observaciones": "La seccion 3.9 ya incluye sus capturas. Las capturas de QA en evidencias/ (p. ej. "
                         "EV-SW-01.png, EV-BD-09.txt, pantallas/EV-MVC-GEN-03-*.png) pueden usarse para los demas "
                         "marcadores. Numerar las figuras y tablas al cerrar el documento.",
    },
    {
        "id": "DEF-09", "casos": ["MVC-GEN-04"], "req": "R07", "area": "Frontend MVC",
        "descripcion": "Los formularios de creacion de personas y profesiones muestran un recuadro de error vacio "
                       "antes de enviar.",
        "pasos": "1. Abrir /Personas/Create o /Profesiones/Create sin enviar datos.",
        "esperado": "Esperado: sin resumen de errores hasta enviar. Obtenido: div de validacion con la clase "
                    "validation-summary-errors y un recuadro rojo vacio de 24 px en los tres anchos.",
        "severidad": "Baja", "responsable": "Andrés", "evidencia": "EV-MVC-GEN-04-resumen-vacio.png, EV-MVC-GEN-04.txt",
        "observaciones": "Hallazgo visual durante MVC-GEN-04; no impide usar el formulario. Causa probable: el GET de "
                         "Create llama a ModelState.SetModelValue para dejar la clave vacia y el estado queda sin "
                         "validar. Propuesta: quitar esa llamada (por ejemplo, mostrar la clave vacia con un DTO de "
                         "vista con clave nullable) o renderizar el resumen solo si hay errores.",
    },
    {
        "id": "DEF-10", "casos": ["SW-09"], "req": "R06", "area": "Swagger",
        "descripcion": "Swagger no muestra resumenes de las operaciones ni descripciones de parametros y campos.",
        "pasos": "1. Abrir /swagger. 2. Revisar operaciones y esquemas (o swagger.json).",
        "esperado": "Esperado: un tercero entiende y prueba la API sin explicacion adicional. Obtenido: 0 de 20 "
                    "operaciones con resumen y 0 de 15 propiedades con descripcion; campos como duenio, oper, nom o "
                    "univer no se explican.",
        "severidad": "Baja", "responsable": "Tomás", "evidencia": "EV-SW-09.txt, EV-SW-01.png",
        "observaciones": "Propuesta: <GenerateDocumentationFile>true</GenerateDocumentationFile> en el .csproj, "
                         "options.IncludeXmlComments(...) en AddSwaggerGen y comentarios /// en controladores y DTO "
                         "(ya existen 4 en los DTO).",
    },
    {
        "id": "DEF-11", "casos": ["ENT-12"], "req": "R11", "area": "Repositorio y entrega",
        "descripcion": "El documento aplica el estilo Titulo 2 a parrafos de cuerpo y sus referencias estan "
                       "incompletas.",
        "pasos": "1. Abrir el documento en Google Docs y revisar el esquema, los estilos de parrafo y las referencias.",
        "esperado": "Esperado: formato uniforme y referencias completas. Obtenido: 38 parrafos de cuerpo con estilo "
                    "Titulo 2 (aparecen en el esquema como titulos) y referencias marcadas como preliminares.",
        "severidad": "Baja", "responsable": "Andrés", "evidencia": "EV-ENT-12.txt",
        "observaciones": "La version en linea ya corrigio las mayusculas de 1.2 y no menciona a Codex. Propuesta: "
                         "aplicar Texto normal a los parrafos de cuerpo y un estilo de pie a las figuras, y completar "
                         "las referencias en APA (ASP.NET Core MVC, EF Core, SQL Server, Swashbuckle).",
    },
]
