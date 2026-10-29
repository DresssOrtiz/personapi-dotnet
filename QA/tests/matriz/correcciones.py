"""Rondas de correccion y re-prueba posteriores a la primera ejecucion de la matriz.

La primera ejecucion (QA/tests/results) no se modifica: cada ronda agrega una nota
en Observaciones de los casos y defectos afectados, cambia el Estado del defecto
verificado y alimenta la seccion 3.9.7 del documento. Las evidencias de cada ronda
estan en QA/evidencias/reprueba/ronda-N/ y los resultados en QA/tests/reprueba/ronda-N/.
Una ronda con "estado": "Pendiente" deja el espacio reservado en el documento.
"""

RONDAS = [
    {
        "ronda": 1, "estado": "Verificada", "fecha": "2026-10-28", "responsable": "Andrés Ortiz",
        "pr": 7, "rama": "fix/def-06-07-09", "commit": "6a0edac",
        "cambios": [
            ("DEF-06", "Página 404 propia con el layout y enlace al inicio (Program.cs, HomeController.cs, "
                       "Views/Home/PageNotFound.cshtml); las rutas /api conservan su 404.",
             ["MVC-PER-05", "MVC-TEL-05", "MVC-PRO-05", "MVC-EST-05", "MVC-GEN-07"]),
            ("DEF-07", "Columna Edad en el listado de personas, con «—» para edades nulas.", ["MVC-PER-01"]),
            ("DEF-09", "Las claves vacías de los formularios de creación de personas y profesiones se marcan "
                       "como válidas al abrirlos.", ["MVC-GEN-04"]),
        ],
        "regresion": "Los demás casos mantuvieron su resultado, sin regresiones, y los scripts del equipo "
                     "tests/mvc-defects.ps1 y tests/mvc-smoke.ps1 terminaron con 62 y 215 comprobaciones correctas.",
    },
    {
        "ronda": 2, "estado": "Pendiente", "responsable": "Tomás Ramírez",
        "defectos": ["DEF-01", "DEF-02", "DEF-03", "DEF-04", "DEF-05", "DEF-10"],
    },
]


def verificados():
    """{defecto: ronda} de los defectos corregidos y verificados."""
    return {d: r for r in RONDAS if r["estado"] == "Verificada" for d, _, _ in r["cambios"]}


def casos_reprobados():
    """{caso: ronda} de los casos repetidos en una ronda verificada."""
    return {c: r for r in RONDAS if r["estado"] == "Verificada" for _, _, cs in r["cambios"] for c in cs}
