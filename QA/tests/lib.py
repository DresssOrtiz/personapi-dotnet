"""Utilidades comunes para la ejecucion automatizada de la matriz de QA.

Cada caso registra su resultado en QA/tests/results/<ID>.json y guarda la
evidencia en QA/evidencias/ con el ID del caso en el nombre del archivo.
QA_REPO apunta al repositorio que se prueba (por defecto, el que contiene QA/) y
QA_REPO_FRONTEND a un clon con la rama del frontend (por defecto, el mismo).
"""
import datetime
import json
import os
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EVID = os.path.join(ROOT, "evidencias")
RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
REPO = os.path.abspath(os.environ.get("QA_REPO", os.path.join(ROOT, "..")))
REPO_FRONTEND = os.path.abspath(os.environ.get("QA_REPO_FRONTEND", REPO))

SQL_CONTAINER = os.environ.get("QA_SQL_CONTAINER", "persona-sql")
SQL_PASSWORD = os.environ.get("QA_SQL_PASSWORD", "Persona_Lab1#2026")
BASE_URL = os.environ.get("QA_BASE_URL", "http://localhost:5025")

os.makedirs(EVID, exist_ok=True)
os.makedirs(RESULTS, exist_ok=True)


def sqlcmd(query=None, script=None, db="master", extra=None):
    """Ejecuta sqlcmd dentro del contenedor. Devuelve (codigo, salida)."""
    cmd = ["docker", "exec", "-i", SQL_CONTAINER, "/opt/mssql-tools18/bin/sqlcmd",
           "-S", "localhost", "-U", "sa", "-P", SQL_PASSWORD, "-C", "-d", db, "-W", "-s", "|"]
    if extra:
        cmd += extra
    stdin = None
    if script is not None:
        cmd += ["-b", "-i", "/dev/stdin"]
        with open(script, "rb") as f:
            stdin = f.read()
    else:
        cmd += ["-Q", query]
    p = subprocess.run(cmd, input=stdin, capture_output=True)
    out = (p.stdout + p.stderr).decode("utf-8", "replace")
    return p.returncode, out


def scalar(query, db="persona_db"):
    """Devuelve el primer valor de una consulta como texto."""
    _, out = sqlcmd("SET NOCOUNT ON; " + query, db=db, extra=["-h", "-1"])
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    return lines[0] if lines else ""


def write_evidence(case_id, text, suffix=".txt"):
    name = f"EV-{case_id}{suffix}"
    with open(os.path.join(EVID, name), "w", encoding="utf-8") as f:
        f.write(f"Caso: {case_id}\nFecha: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
        f.write(text)
    return name


def record(case_id, estado, obtenido, evidencia="", observaciones="", responsable="Automatizado"):
    data = {
        "id": case_id,
        "estado": estado,
        "obtenido": obtenido,
        "evidencia": evidencia,
        "fecha": datetime.date.today().isoformat(),
        "responsable": responsable,
        "observaciones": observaciones,
    }
    with open(os.path.join(RESULTS, f"{case_id}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[{estado:9}] {case_id}: {obtenido}")
    return data
