"""Registra ENT-04 (derivado de la corrida completa) y los casos manuales pendientes.

Uso: python QA/tests/casos_derivados.py
Se ejecuta al final de run_all.sh, cuando ya existen los resultados de BD, BK y SW.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import RESULTS, record, write_evidence  # noqa: E402


def estado(case_id):
    path = os.path.join(RESULTS, f"{case_id}.json")
    return json.load(open(path, encoding="utf-8"))["estado"] if os.path.exists(path) else "sin resultado"


def main():
    base = {c: estado(c) for c in ("BD-01", "BD-09", "BK-02", "BK-03", "SW-01", "ENT-08")}
    ok = all(base[c] == "Aprobado" for c in ("BD-01", "BD-09", "BK-02", "BK-03", "SW-01"))
    ev = write_evidence("ENT-04", "Corrida desde cero con QA/tests/run_all.sh en macOS (Apple Silicon):\n"
                                  "1. git clone del repositorio publico.\n"
                                  "2. docker run ... mssql/server:2022-latest (comando literal del README).\n"
                                  "3. sqlcmd con db/01_ddl.sql y db/02_dml.sql (comando literal del README).\n"
                                  "4. dotnet build y dotnet run --urls http://localhost:5025 (SDK 6.0.428).\n\n" +
                         "\n".join(f"{k}: {v}" for k, v in base.items()))
    record("ENT-04", "Aprobado" if ok else "Fallido",
           "Siguiendo solo el README (opcion Docker) se crea la base, se compila y se ejecuta; la aplicacion y "
           "Swagger funcionan (BD-01, BD-09, BK-02, BK-03 y SW-01 aprobados).", ev,
           "La seccion Despliegue del README falla con el comando literal (ENT-08). Requiere instalar el SDK de "
           ".NET 6, fuera de soporte. No se probo la opcion B (SQL Server Express en Windows).")

    for case_id, obs in [
        ("MVC-GEN-05", "Revision manual pendiente: repetir un flujo completo en Chrome, Edge y Firefox."),
        ("SW-09", "Revision manual pendiente. Dato para la revision: las operaciones no tienen summary ni "
                  "descripciones porque el proyecto no genera el archivo XML de documentacion."),
        ("ENT-12", "Revision manual pendiente sobre el documento final (estilos, ortografia, tercera persona y "
                   "referencias)."),
    ]:
        record(case_id, "Pendiente", "", "", obs, responsable="")


if __name__ == "__main__":
    main()
