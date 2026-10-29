"""Rondas de correccion y re-prueba posteriores a la primera ejecucion de la matriz.

La primera ejecucion (QA/tests/results) no se modifica: cada ronda agrega una nota
en Observaciones de los casos y defectos afectados, cambia el Estado del defecto
y alimenta la seccion 3.9.7 del documento. Las evidencias de cada ronda estan en
QA/evidencias/reprueba/ronda-N/ y los resultados en QA/tests/reprueba/ronda-N/.
Cada cambio es (defecto, correccion, casos repetidos, estado del defecto); el
estado es "Verificado" o "Corregido" cuando la re-prueba no cubre todos los entornos.
Una ronda con "estado": "Pendiente" deja el espacio reservado en el documento.
"""

RONDAS = [
    {
        "ronda": 1, "estado": "Verificada", "fecha": "2026-10-28", "responsable": "Andrés Ortiz",
        "prs": [7], "origen": "en la rama fix/def-06-07-09 (commit 6a0edac)", "probado": "sobre esa rama",
        "cambios": [
            ("DEF-06", "Página 404 propia con el layout y enlace al inicio (Program.cs, HomeController.cs, "
                       "Views/Home/PageNotFound.cshtml); las rutas /api conservan su 404.",
             ["MVC-PER-05", "MVC-TEL-05", "MVC-PRO-05", "MVC-EST-05", "MVC-GEN-07"], "Verificado"),
            ("DEF-07", "Columna Edad en el listado de personas, con «—» para edades nulas.", ["MVC-PER-01"],
             "Verificado"),
            ("DEF-09", "Las claves vacías de los formularios de creación de personas y profesiones se marcan "
                       "como válidas al abrirlos.", ["MVC-GEN-04"], "Verificado"),
        ],
        "regresion": "Los demás casos mantuvieron su resultado, sin regresiones, y los scripts del equipo "
                     "tests/mvc-defects.ps1 y tests/mvc-smoke.ps1 terminaron con 62 y 215 comprobaciones correctas.",
        "veredicto": "Por lo anterior, QA aprobó el Pull Request #7. Los defectos del documento asignados al mismo "
                     "responsable (DEF-08 y DEF-11) siguen abiertos.",
    },
    {
        "ronda": 2, "estado": "Verificada", "fecha": "2026-10-28", "responsable": "Tomás Ramírez",
        "prs": [9, 10, 11], "origen": "en tres Pull Request que se integraron en main antes de la revisión de QA",
        "probado": "sobre main integrada (merge commit a05612c)",
        "cambios": [
            ("DEF-01", "Los POST de la API capturan la clave duplicada de SQL Server (errores 2601 y 2627) y "
                       "responden 409 (Pull Request #9).", ["API-GEN-05"], "Verificado"),
            ("DEF-02", "El README ejecuta la aplicación publicada desde la carpeta publish/ (Pull Request #9).",
             ["ENT-08"], "Verificado"),
            ("DEF-03", "Middleware para /api que responde 503 con ProblemDetails, sin traza, ante SqlException "
                       "(Pull Request #10).", ["BK-09", "INT-08"], "Verificado"),
            ("DEF-04", "Advertencia en el README y en el encabezado del DDL de que el script borra los datos "
                       "(Pull Request #10).", ["BD-08"], "Verificado"),
            ("DEF-05", "ALTER AUTHORIZATION dentro de TRY/CATCH con aviso y opción C del README para LocalDB "
                       "(Pull Request #11).", ["BD-07"], "Corregido"),
            ("DEF-10", "Comentarios XML en controladores y DTO y archivo de documentación incluido en Swagger "
                       "(Pull Request #11).", ["SW-09"], "Verificado"),
        ],
        "regresion": "Los demás casos mantuvieron su resultado, sin regresiones, y los scripts del equipo "
                     "terminaron con 62 y 215 comprobaciones correctas. Como prueba adicional de DEF-03, con SQL "
                     "Server detenido, ocho operaciones de lectura y escritura de la API respondieron 503 sin traza.",
        "veredicto": "Por lo anterior, QA aprueba las correcciones de los Pull Request #9, #10 y #11. DEF-05 queda "
                     "en estado Corregido: con un login sin rol sysadmin el DDL termina sin error y muestra el "
                     "aviso, pero BD-07 sigue bloqueado hasta ejecutarlo en Windows con SQL Server Express o "
                     "LocalDB.",
    },
]


def estados():
    """{defecto: (estado, ronda)} de los defectos tratados en rondas verificadas."""
    return {d: (e, r) for r in RONDAS if r["estado"] == "Verificada" for d, _, _, e in r["cambios"]}


def casos_reprobados():
    """{caso: ronda} de los casos repetidos en una ronda verificada (la ultima gana)."""
    return {c: r for r in RONDAS if r["estado"] == "Verificada" for _, _, cs, _ in r["cambios"] for c in cs}


def prs_texto(prs):
    nums = [f"#{n}" for n in prs]
    return "Pull Request " + (nums[0] if len(nums) == 1 else ", ".join(nums[:-1]) + " y " + nums[-1])
