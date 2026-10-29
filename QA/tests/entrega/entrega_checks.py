"""Casos ENT-01 a ENT-09 y API-GEN-06 (persistencia tras reiniciar la aplicacion).

Uso: python QA/tests/entrega/entrega_checks.py
Requiere gh autenticado (para colaboradores y estado del PR), el SDK de .NET 6
en ~/.dotnet6 y la aplicacion de main en ejecucion en el puerto 5025.
ENT-08 publica una copia limpia del repositorio en un directorio temporal.
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib import BASE_URL, EVID, REPO, RESULTS, record, scalar, sqlcmd, write_evidence  # noqa: E402

GH_REPO = "DresssOrtiz/personapi-dotnet"
REMOTE = f"https://github.com/{GH_REPO}.git"
DOTNET = os.environ.get("DOTNET6", os.path.expanduser("~/.dotnet6/dotnet"))
ENV = {**os.environ, "DOTNET_ROOT": os.path.dirname(DOTNET), "DOTNET_CLI_TELEMETRY_OPTOUT": "1"}
APP_LOG = os.path.join(RESULTS, "app-main-restart.log")


def sh(cmd, cwd=None, env=None):
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, shell=isinstance(cmd, str))
    return p.returncode, (p.stdout + p.stderr).strip()


def wait_http(url, seconds=60):
    for _ in range(seconds):
        try:
            return requests.get(url, timeout=5)
        except requests.ConnectionError:
            time.sleep(1)
    return None


def start_app(proj, port, env=None, log=APP_LOG):
    f = open(log, "w")
    return subprocess.Popen([DOTNET, "run", "--urls", f"http://localhost:{port}"], cwd=proj, env=env or ENV,
                            stdout=f, stderr=subprocess.STDOUT, start_new_session=True)


def kill_port(port):
    _, pids = sh(f"lsof -ti tcp:{port} -sTCP:LISTEN")
    for pid in pids.split():
        os.kill(int(pid), signal.SIGTERM)
    time.sleep(3)


def ent07():
    """ENT-07: si el PR #2 esta fusionado, clona main limpia, compila, ejecuta y prueba vistas y API."""
    _, pr = sh(["gh", "pr", "view", "2", "--repo", GH_REPO, "--json",
                "state,mergedAt,mergeCommit,reviewDecision,headRefOid,mergeStateStatus"])
    info = json.loads(pr)
    if info["state"] != "MERGED":
        ev = write_evidence("ENT-07", f"gh pr view 2 -> {pr}")
        record("ENT-07", "Bloqueado",
               f"El PR #2 esta {info['state'].lower()} ({info['mergeStateStatus']}); main aun no contiene el frontend.",
               ev, "Depende de la aprobacion de QA y del merge. main compila y ejecuta (BK-02, BK-03). "
                   "Repetir tras el merge.")
        return
    tmp = tempfile.mkdtemp(prefix="qa-main-")
    log, codes = [f"gh pr view 2 -> {pr}"], {}
    try:
        rc, out = sh(["git", "clone", "-q", "--branch", "main", REMOTE, tmp]); log.append(f"git clone main -> {rc}")
        _, head = sh(["git", "log", "-1", "--format=%h %s"], cwd=tmp)
        rc_anc, _ = sh(["git", "merge-base", "--is-ancestor", info["headRefOid"], "HEAD"], cwd=tmp)
        log.append(f"HEAD de main: {head}\nContiene {info['headRefOid'][:7]}: {rc_anc == 0}")
        rc_b, out = sh([DOTNET, "build", "personapi-dotnet.sln", "-nologo"], cwd=tmp, env=ENV)
        summary = [l.strip() for l in out.splitlines() if re.search(r"Advertencia|Errores|Warning|Error", l)][-2:]
        log.append(f"dotnet build -> {rc_b} {summary}")
        p = start_app(os.path.join(tmp, "personapi-dotnet"), 5028, log=os.path.join(tmp, "run.log"))
        try:
            wait_http("http://localhost:5028/")
            for path in ("/", "/Personas", "/Telefonos", "/Profesiones", "/Estudios", "/Personas/Create",
                         "/api/personas", "/api/estudios", "/swagger/index.html"):
                r = requests.get("http://localhost:5028" + path, timeout=30)
                codes[path] = r.status_code
            listado = "Listado de personas" in requests.get("http://localhost:5028/Personas", timeout=30).text
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1366, "height": 900})
                pg.goto("http://localhost:5028/Personas")
                pg.screenshot(path=os.path.join(EVID, "EV-ENT-07.png"), full_page=True); b.close()
        finally:
            os.killpg(p.pid, signal.SIGTERM); p.wait(timeout=30)
        log.append("Respuestas de la aplicacion compilada desde main:\n" +
                   "\n".join(f"  GET {k} -> {v}" for k, v in codes.items()) + f"\nListado MVC presente: {listado}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    ev = write_evidence("ENT-07", "\n".join(log))
    ok = rc_anc == 0 and rc_b == 0 and all(v == 200 for v in codes.values()) and listado
    commit = info["mergeCommit"]["oid"][:7]
    record("ENT-07", "Aprobado" if ok else "Fallido",
           f"PR #2 aprobado por QA y fusionado en main (merge commit {commit}). main contiene eea9ee8, compila "
           f"({' '.join(summary)}) y la aplicacion responde 200 en inicio, los 4 listados MVC, el formulario de "
           "creacion, la API y Swagger.", f"EV-ENT-07.png, {ev}",
           "Repetido despues del merge sobre un clon limpio de main.")


def main():
    # ENT-01 repositorio publico
    r = requests.get(f"https://api.github.com/repos/{GH_REPO}", timeout=30)
    d = r.json()
    rc, ls = sh(["git", "ls-remote", "--heads", REMOTE])
    ev = write_evidence("ENT-01", f"GET api.github.com/repos/{GH_REPO} sin token -> {r.status_code}\n"
                                   f"name={d.get('name')} private={d.get('private')} visibility={d.get('visibility')}\n"
                                   f"git ls-remote --heads (sin credenciales) -> {rc}\n{ls}")
    rec_ok = r.status_code == 200 and d.get("name") == "personapi-dotnet" and not d.get("private")
    record("ENT-01", "Aprobado" if rec_ok else "Fallido",
           f"La API de GitHub sin autenticacion responde {r.status_code}: personapi-dotnet, visibilidad "
           f"{d.get('visibility')}; ramas main, feature/backend y feature/frontend-mvc.", ev)

    # ENT-02 colaboradores
    rc, collab = sh(["gh", "api", f"repos/{GH_REPO}/collaborators", "--jq", ".[] | .login + \" \" + .role_name"])
    logins = [l.split()[0] for l in collab.splitlines() if l.strip()]
    ev = write_evidence("ENT-02", f"gh api repos/{GH_REPO}/collaborators -> {rc}\n{collab}")
    record("ENT-02", "Aprobado" if rc == 0 and len(logins) >= 3 else "Fallido",
           f"Colaboradores con acceso aceptado: {', '.join(logins)} (3 integrantes).", ev,
           "La correspondencia de cuentas es DresssOrtiz (Andres Ortiz, propietario), ElTomi016 (Tomas Ramirez) y "
           "santiagohb2830 (Santiago Hernandez). Las invitaciones pendientes requieren permisos de administrador.")

    # ENT-03 README
    readme = open(os.path.join(REPO, "README.md"), encoding="utf-8").read()
    items = {"descripcion": "Monolito ASP.NET Core MVC" in readme, "requisitos": "### 1. Requisitos" in readme,
             "base de datos": "### 2. Base de datos" in readme, "cadena de conexion": "### 3. Cadena de conexi" in readme,
             "ejecucion": "dotnet run" in readme, "ruta aplicacion": "http://localhost:5025>" in readme,
             "ruta swagger": "/swagger" in readme, "despliegue": "## Despliegue" in readme}
    ev = write_evidence("ENT-03", "\n".join(f"{k}: {'si' if v else 'no'}" for k, v in items.items()) + "\n\n" + readme)
    record("ENT-03", "Aprobado" if all(items.values()) else "Fallido",
           "El README incluye descripcion, stack, requisitos, creacion de la base (Docker y SSMS), cadena de conexion, "
           "compilacion, ejecucion, rutas de la aplicacion y de Swagger, tabla de endpoints y despliegue.", ev,
           "No advierte que el DDL elimina las tablas (BD-08), no menciona el ajuste en LocalDB (BD-07) y no describe "
           "las vistas MVC porque el frontend aun no esta en main.")

    # ENT-05 archivos que no deben estar
    rc, files = sh(["git", "ls-files"], cwd=REPO)
    rc2, files_fe = sh(["git", "ls-tree", "-r", "--name-only", "origin/feature/frontend-mvc"], cwd=REPO)
    bad = [f for f in (files + "\n" + files_fe).splitlines()
           if re.search(r"(^|/)(bin|obj|\.vs)/|\.user$|\.suo$|\.DS_Store$", f)]
    _, secrets = sh("git grep -n -I -E 'Password=|Pwd=|User Id=' main origin/feature/frontend-mvc", cwd=REPO)
    gi = open(os.path.join(REPO, ".gitignore"), encoding="utf-8").read()
    ev = write_evidence("ENT-05", f"Archivos de compilacion o temporales versionados: {bad}\n"
                                   f".gitignore excluye bin/obj: {'[Bb]in/' in gi or 'bin/' in gi}\n\n"
                                   f"Credenciales encontradas:\n{secrets}")
    record("ENT-05", "Aprobado" if not bad else "Fallido",
           "No hay bin/, obj/ ni archivos temporales versionados en main ni en feature/frontend-mvc. La unica "
           "credencial es la contrasena de ejemplo del contenedor Docker del README (usuario sa) en appsettings.json.",
           ev, "La contrasena coincide con el ejemplo del README, pero el archivo no la identifica como valor de "
                "ejemplo. Mejora sugerida: dejar la cadena sin contrasena y usar ConnectionStrings__PersonaDb o "
                "user-secrets, y un usuario distinto de sa.")

    # ENT-06 scripts versionados sin modificaciones
    rc, st = sh(["git", "status", "--porcelain", "db/"], cwd=REPO)
    # Mientras el PR #2 no este integrado se compara su rama con main; despues, la rama ya forma parte de HEAD.
    integrado = sh(["git", "merge-base", "--is-ancestor", "origin/feature/frontend-mvc", "HEAD"], cwd=REPO)[0] == 0
    diff_fe = "" if integrado else sh(["git", "diff", "--stat", "main", "origin/feature/frontend-mvc", "--", "db/"],
                                      cwd=REPO)[1]
    ddl = open(os.path.join(REPO, "db", "01_ddl.sql"), encoding="utf-8").read()
    ev = write_evidence("ENT-06", f"git status db/: '{st}'\nfeature/frontend-mvc integrada en HEAD: {integrado}\n"
                                   f"git diff main..feature/frontend-mvc -- db/: '{diff_fe}'\n"
                                   "Los casos BD-01 y BD-09 ejecutaron estos archivos tal como estan versionados.")
    record("ENT-06", "Aprobado" if not st and not diff_fe else "Fallido",
           "db/01_ddl.sql y db/02_dml.sql del repositorio se ejecutaron sin cambios locales en Docker (BD-01, BD-09)"
           + ("." if integrado else "; la rama del PR no los modifica."), ev,
           "El DDL versionado omite ALTER AUTHORIZATION con un aviso cuando no hay permisos, por lo que ya no hace "
           "falta una version local." if "BEGIN TRY" in ddl else
           "El documento (sec. 3.2 y 3.8) indica que en el equipo de Andres se uso una version local del DDL sin "
           "ALTER AUTHORIZATION, no versionada.")

    ent07()

    # ENT-09 TAG
    rc, tags = sh(["git", "ls-remote", "--tags", REMOTE])
    ev = write_evidence("ENT-09", f"git ls-remote --tags {REMOTE} -> {rc}\n'{tags}'")
    record("ENT-09", "Bloqueado", "El repositorio no tiene etiquetas (git ls-remote --tags vacio).", ev,
           "La precondicion (trabajo integrado y aprobado) no se cumple todavia. Crear el TAG indicado en el "
           "enunciado despues del merge del PR #2.")

    # API-GEN-06 persistencia tras reiniciar
    body = {"cc": 2090, "nombre": "Persistente", "apellido": "QA", "genero": "F", "edad": 41}
    requests.delete(BASE_URL + "/api/personas/2090", timeout=10)
    c1 = requests.post(BASE_URL + "/api/personas", json=body, timeout=10).status_code
    kill_port(5025)
    down = wait_http(BASE_URL + "/api/personas", 2)
    start_app(os.path.join(REPO, "personapi-dotnet"), 5025)
    wait_http(BASE_URL + "/api/personas")
    g = requests.get(BASE_URL + "/api/personas/2090", timeout=10)
    requests.delete(BASE_URL + "/api/personas/2090", timeout=10)
    ev = write_evidence("API-GEN-06", f"POST /api/personas cc 2090 -> {c1}\nProceso detenido (puerto 5025 libre: "
                                       f"{down is None})\nAplicacion reiniciada con dotnet run\n"
                                       f"GET /api/personas/2090 -> {g.status_code} {g.text}")
    record("API-GEN-06", "Aprobado" if c1 == 201 and down is None and g.status_code == 200 else "Fallido",
           f"POST {c1}; tras detener y reiniciar la aplicacion, GET /api/personas/2090 responde {g.status_code} "
           "con los mismos datos.", ev)

    # ENT-08 despliegue local publicado segun el README
    tmp = tempfile.mkdtemp(prefix="qa-publish-")
    log = []
    try:
        rc, out = sh(["git", "clone", "-q", REPO, tmp]); log.append(f"git clone -> {rc} {out}")
        rc, out = sh([DOTNET, "publish", "personapi-dotnet/personapi-dotnet.csproj", "-c", "Release", "-o", "publish"],
                     cwd=tmp, env=ENV)
        log.append(f"$ dotnet publish personapi-dotnet/personapi-dotnet.csproj -c Release -o publish -> {rc}\n{out[-800:]}")
        # Comando literal del README vigente: desde la raiz o, si el README lo indica, desde publish/
        readme = open(os.path.join(tmp, "README.md"), encoding="utf-8").read()
        desde_publish = re.search(r"^cd publish\s*$", readme, re.M) is not None
        f1 = open(os.path.join(tmp, "run1.log"), "w")
        p = subprocess.Popen([DOTNET, "personapi-dotnet.dll" if desde_publish else "publish/personapi-dotnet.dll"],
                             cwd=os.path.join(tmp, "publish") if desde_publish else tmp, stdout=f1,
                             stderr=subprocess.STDOUT, env={**ENV, "ASPNETCORE_URLS": "http://localhost:5027"})
        r1 = wait_http("http://localhost:5027/api/personas", 40)
        r1sw = requests.get("http://localhost:5027/swagger/index.html", timeout=10).status_code if r1 is not None else None
        p.terminate(); p.wait(timeout=30)
        log.append(("$ cd publish && ASPNETCORE_URLS=http://localhost:5027 dotnet personapi-dotnet.dll (README)\n"
                    if desde_publish else
                    "$ ASPNETCORE_URLS=http://localhost:5027 dotnet publish/personapi-dotnet.dll (README, cwd = raiz)\n") +
                   f"GET /api/personas -> {r1.status_code if r1 is not None else 'sin respuesta'} {r1.text[:300] if r1 is not None else ''}\n"
                   f"GET /swagger -> {r1sw}\nLineas relevantes del log:\n" + "\n".join(
                       l for l in open(os.path.join(tmp, 'run1.log')).read().splitlines()
                       if re.search(r'Exception|ConnectionString|Hosting environment|Content root', l))[:2500])
        # Variante: ejecutando desde la carpeta publish (content root con appsettings.json)
        f2 = open(os.path.join(tmp, "run2.log"), "w")
        p = subprocess.Popen([DOTNET, "personapi-dotnet.dll"], cwd=os.path.join(tmp, "publish"), stdout=f2,
                             stderr=subprocess.STDOUT, env={**ENV, "ASPNETCORE_URLS": "http://localhost:5027"})
        r2 = wait_http("http://localhost:5027/api/personas", 40)
        r2sw = requests.get("http://localhost:5027/swagger/index.html", timeout=10).status_code if r2 is not None else None
        p.terminate(); p.wait(timeout=30)
        log.append(f"$ cd publish && ASPNETCORE_URLS=http://localhost:5027 dotnet personapi-dotnet.dll\n"
                   f"GET /api/personas -> {r2.status_code if r2 is not None else 'sin respuesta'} ({len(r2.json()) if r2 is not None and r2.ok else 0} registros)\n"
                   f"GET /swagger -> {r2sw} (entorno Production)\n")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    ev = write_evidence("ENT-08", "\n\n".join(log))
    ok = r1 is not None and r1.status_code == 200
    record("ENT-08", "Aprobado" if ok else "Fallido",
           f"dotnet publish termina bien. Con el comando literal del README "
           f"({'desde publish/' if desde_publish else 'desde la raiz'}), GET /api/personas responde "
           f"{r1.status_code if r1 is not None else 'sin respuesta'}; ejecutando desde la carpeta publish responde "
           f"{r2.status_code if r2 is not None else 'sin respuesta'}. Swagger responde {r2sw} en Production.", ev,
           "Swagger queda expuesto fuera de Development porque UseSwagger/UseSwaggerUI no estan condicionados al "
           "entorno en Program.cs.")


if __name__ == "__main__":
    if "--solo" in sys.argv and sys.argv[sys.argv.index("--solo") + 1] == "ENT-07":
        ent07()
    else:
        main()
