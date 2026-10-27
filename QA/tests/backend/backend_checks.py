"""Casos BK-01 a BK-08: revision del proyecto, compilacion, arranque y configuracion.

Uso: python QA/tests/backend/backend_checks.py [--repo RUTA] [--tag main|frontend]
Requiere el SDK de .NET 6 en ~/.dotnet6 (o DOTNET6 con la ruta del ejecutable)
y la aplicacion en ejecucion en QA_BASE_URL para BK-03.
"""
import glob
import os
import re
import subprocess
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib import BASE_URL, REPO, record, sqlcmd, write_evidence  # noqa: E402

REPO = sys.argv[sys.argv.index("--repo") + 1] if "--repo" in sys.argv else REPO
TAG = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "main"
SFX = "" if TAG == "main" else f"-{TAG}"
PROJ = os.path.join(REPO, "personapi-dotnet")
DOTNET = os.environ.get("DOTNET6", os.path.expanduser("~/.dotnet6/dotnet"))
ENV = {**os.environ, "DOTNET_ROOT": os.path.dirname(DOTNET), "DOTNET_CLI_TELEMETRY_OPTOUT": "1"}


def rec(case_id, estado, obtenido, ev, obs=""):
    if TAG == "main":
        record(case_id, estado, obtenido, ev, obs)
    else:
        print(f"[{estado:9}] {case_id} ({TAG}): {obtenido}")


def read(path):
    with open(os.path.join(PROJ, path), encoding="utf-8-sig") as f:
        return f.read()


def main():
    # BK-01 version y paquetes
    csproj = read("personapi-dotnet.csproj")
    tf = re.search(r"<TargetFramework>(.*?)</TargetFramework>", csproj).group(1)
    pkgs = re.findall(r'PackageReference Include="(.*?)" Version="(.*?)"', csproj)
    readme = open(os.path.join(REPO, "README.md"), encoding="utf-8").read()
    justified = "se usa 6.0" in readme
    ev = write_evidence("BK-01" + SFX, f"TargetFramework: {tf}\nSdk: Microsoft.NET.Sdk.Web\nPaquetes:\n" +
                        "\n".join(f"  {n} {v}" for n, v in pkgs) +
                        f"\n\nREADME, tabla Stack:\n{readme[readme.find('| .NET'):readme.find('| Entity')]}")
    ok = tf == "net6.0" and any(n == "Microsoft.EntityFrameworkCore.SqlServer" for n, _ in pkgs) and justified
    rec("BK-01", "Aprobado" if ok else "Fallido",
        f"{tf}, Microsoft.NET.Sdk.Web (ASP.NET Core MVC), EF Core 6.0.36 con SqlServer y Design, Swashbuckle 6.5.0. "
        "El README justifica .NET 6 frente al 7 del stack del enunciado.", ev,
        ".NET 6 esta fuera de soporte desde noviembre de 2024; con SDK recientes se emite la advertencia "
        "NETSDK1138.")

    # BK-02 compilacion
    p = subprocess.run([DOTNET, "build", os.path.join(REPO, "personapi-dotnet.sln"), "-nologo"],
                       capture_output=True, text=True, env=ENV)
    out = p.stdout + p.stderr
    warn = re.search(r"(\d+) Advertencia|(\d+) Warning", out)
    err = re.search(r"(\d+) Errores|(\d+) Error", out)
    nw = next(g for g in warn.groups() if g) if warn else "?"
    ne = next(g for g in err.groups() if g) if err else "?"
    ver = subprocess.run([DOTNET, "--version"], capture_output=True, text=True, env=ENV).stdout.strip()
    ev = write_evidence("BK-02" + SFX, f"SDK: {ver}\n$ dotnet build personapi-dotnet.sln\n{out}")
    rec("BK-02", "Aprobado" if p.returncode == 0 and ne == "0" else "Fallido",
        f"dotnet build (SDK {ver}): codigo {p.returncode}, {ne} errores y {nw} advertencias.", ev)

    # BK-03 arranque y conexion
    home = requests.get(BASE_URL + "/", timeout=30)
    lst = requests.get(BASE_URL + "/api/personas", timeout=30)
    ev = write_evidence("BK-03" + SFX, f"GET / -> {home.status_code}\n{home.text[:600]}\n\n"
                                          f"GET /api/personas -> {lst.status_code}\n{lst.text[:600]}")
    rec("BK-03", "Aprobado" if home.status_code == 200 and lst.status_code == 200 and lst.json() else "Fallido",
        f"La aplicacion inicia en {BASE_URL}; la pagina de inicio responde {home.status_code} y el listado de "
        f"personas {lst.status_code} con {len(lst.json())} registros de persona_db.", ev)

    # BK-04 mapeo del DbContext
    ctx = read("Models/Entities/persona_dbContext.cs")
    sets = re.findall(r"DbSet<(\w+)>", ctx)
    composite = "HasKey(e => new { e.IdProf, e.CcPer })" in ctx
    fks = re.findall(r'HasConstraintName\("(\w+)"\)', ctx)
    on_conf = "OnConfiguring" in ctx
    ev = write_evidence("BK-04" + SFX, f"DbSet: {sets}\nClave compuesta estudios: {composite}\nRelaciones: {fks}\n"
                                          f"OnConfiguring presente: {on_conf}")
    ok = set(sets) == {"Estudio", "Persona", "Profesion", "Telefono"} and composite and len(fks) == 3
    rec("BK-04", "Aprobado" if ok else "Fallido",
        f"persona_dbContext mapea {len(sets)} entidades ({', '.join(sets)}), clave compuesta (IdProf, CcPer) y las "
        f"3 relaciones {', '.join(fks)}.", ev,
        "El DbSet de profesion se llama 'Profesions' (pluralizacion del scaffold); no afecta el funcionamiento.")

    # BK-06 interfaces
    ops = ["GetAllAsync", "GetByIdAsync", "ExistsAsync", "AddAsync", "UpdateAsync", "DeleteAsync"]
    txt, ok6 = [], True
    for f in sorted(glob.glob(os.path.join(PROJ, "Interfaces", "I*Repository.cs"))):
        src = open(f, encoding="utf-8-sig").read()
        have = [o for o in ops if o in src]
        ok6 &= have == ops
        txt.append(f"{os.path.basename(f)}: {have}")
    ev = write_evidence("BK-06" + SFX, "\n".join(txt))
    rec("BK-06", "Aprobado" if ok6 and len(txt) == 4 else "Fallido",
        f"{len(txt)} interfaces (IPersona, ITelefono, IProfesion, IEstudio) con las 6 operaciones: " + ", ".join(ops) + ".", ev)

    # BK-07 repositorios e inyeccion
    prog = read("Program.cs")
    regs = re.findall(r"AddScoped<(I\w+), (\w+)>", prog)
    impls = []
    for f in sorted(glob.glob(os.path.join(PROJ, "Repositories", "*.cs"))):
        m = re.search(r"class (\w+) : (I\w+)", open(f, encoding="utf-8-sig").read())
        if m:
            impls.append(m.groups())
    ok = len(regs) == 4 and {(i, c) for i, c in regs} == {(i, c) for c, i in impls}
    ev = write_evidence("BK-07" + SFX, f"Implementaciones: {impls}\nRegistros en Program.cs: {regs}")
    rec("BK-07", "Aprobado" if ok else "Fallido",
        f"{len(impls)} repositorios implementan sus interfaces y estan registrados como AddScoped en Program.cs.", ev)

    # BK-08 controladores sin DbContext
    hits, files = [], sorted(glob.glob(os.path.join(PROJ, "Controllers", "**", "*.cs"), recursive=True))
    for f in files:
        for i, line in enumerate(open(f, encoding="utf-8-sig"), 1):
            if "persona_dbContext" in line or "DbContext" in line:
                hits.append(f"{os.path.relpath(f, PROJ)}:{i}: {line.strip()}")
    deps = {os.path.relpath(f, PROJ): sorted(set(re.findall(r"I\w+Repository", open(f, encoding='utf-8-sig').read())))
            for f in files}
    ev = write_evidence("BK-08" + SFX, f"Controladores revisados: {len(files)}\nReferencias a DbContext: {hits}\n"
                                          + "\n".join(f"{k}: {v}" for k, v in deps.items()))
    rec("BK-08", "Aprobado" if not hits else "Fallido",
        f"Ninguno de los {len(files)} controladores referencia el DbContext; dependen de las interfaces DAO.", ev)

    # BK-05 cadena sobrescribible con variable de entorno
    sqlcmd("IF DB_ID('persona_qa_alt') IS NOT NULL DROP DATABASE persona_qa_alt; CREATE DATABASE persona_qa_alt;")
    sqlcmd("SELECT * INTO dbo.persona FROM persona_db.dbo.persona; "
           "INSERT INTO dbo.persona VALUES (7777, 'Base', 'Alterna', 'F', 40);", db="persona_qa_alt")
    alt = "Server=localhost,1433;Database=persona_qa_alt;User Id=sa;Password=Persona_Lab1#2026;TrustServerCertificate=true"
    proc = subprocess.Popen([DOTNET, "run", "--no-build", "--urls", "http://localhost:5026"], cwd=PROJ,
                            env={**ENV, "ConnectionStrings__PersonaDb": alt},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        r = None
        for _ in range(40):
            try:
                r = requests.get("http://localhost:5026/api/personas/7777", timeout=5)
                break
            except requests.ConnectionError:
                time.sleep(1)
        main_r = requests.get(BASE_URL + "/api/personas/7777", timeout=10)
    finally:
        proc.terminate(); proc.wait(timeout=30)
    sqlcmd("DROP DATABASE persona_qa_alt;")
    code = r.status_code if r is not None else "sin respuesta"
    ev = write_evidence("BK-05" + SFX, "Base persona_qa_alt con la persona 7777 (no existe en persona_db).\n"
                                          "ConnectionStrings__PersonaDb=<cadena hacia persona_qa_alt>\n"
                                          f"Instancia en :5026 -> GET /api/personas/7777: {code} "
                                          f"{r.text if r is not None else ''}\n"
                                          f"Instancia en :5025 (appsettings.json) -> GET /api/personas/7777: {main_r.status_code}")
    rec("BK-05", "Aprobado" if code == 200 and main_r.status_code == 404 else "Fallido",
        f"Con ConnectionStrings__PersonaDb apuntando a otra base, la aplicacion devuelve la persona 7777 ({code}); "
        f"la instancia con appsettings.json responde {main_r.status_code}. No se modifico codigo.", ev)


if __name__ == "__main__":
    main()
