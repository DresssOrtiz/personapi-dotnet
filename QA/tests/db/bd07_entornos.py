"""Caso BD-07: el mismo DDL en mas de un entorno.

En macOS solo esta disponible SQL Server 2022 en Docker (Express y LocalDB son
exclusivos de Windows). Como aproximacion, se ejecuta el DDL sin cambios con un
login sin rol sysadmin (solo dbcreator), situacion en la que ALTER AUTHORIZATION
... TO sa requiere permisos adicionales. Al final se recrea persona_db como sa y
se carga el DML.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib import REPO, SQL_CONTAINER, record, sqlcmd, write_evidence  # noqa: E402

DDL = os.path.join(REPO, "db", "01_ddl.sql")
DML = os.path.join(REPO, "db", "02_dml.sql")
LOGIN, LOGIN_PWD = "qa_dbcreator", "Qa_Dbcreator#2026"


def run_as_login(script):
    cmd = ["docker", "exec", "-i", SQL_CONTAINER, "/opt/mssql-tools18/bin/sqlcmd", "-S", "localhost",
           "-U", LOGIN, "-P", LOGIN_PWD, "-C", "-b", "-i", "/dev/stdin"]
    with open(script, "rb") as f:
        p = subprocess.run(cmd, input=f.read(), capture_output=True)
    return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")


def main():
    log = []
    _, out = sqlcmd("IF DB_ID('persona_db') IS NOT NULL BEGIN ALTER DATABASE persona_db SET SINGLE_USER "
                    "WITH ROLLBACK IMMEDIATE; DROP DATABASE persona_db; END; "
                    f"IF SUSER_ID('{LOGIN}') IS NULL CREATE LOGIN {LOGIN} WITH PASSWORD = '{LOGIN_PWD}', "
                    f"CHECK_POLICY = OFF; ALTER SERVER ROLE dbcreator ADD MEMBER {LOGIN};")
    log.append("Preparacion (sa): base eliminada y login qa_dbcreator con rol dbcreator.\n" + out)

    rc, out = run_as_login(DDL)
    log.append(f"Entorno 2 - DDL sin cambios con login no sysadmin -> codigo {rc}\n{out}")
    auth_error = "ALTER AUTHORIZATION" in out or "Cannot find the principal" in out or "permission" in out.lower()

    _, out = sqlcmd("IF DB_ID('persona_db') IS NOT NULL BEGIN ALTER DATABASE persona_db SET SINGLE_USER "
                    "WITH ROLLBACK IMMEDIATE; DROP DATABASE persona_db; END; "
                    f"DROP LOGIN {LOGIN};")
    rc1, out1 = sqlcmd(script=DDL)
    rc2, out2 = sqlcmd(script=DML)
    log.append(f"Entorno 1 - DDL como sa -> codigo {rc1}\n{out1}\nDML como sa -> codigo {rc2}\n{out2}")

    ev = write_evidence("BD-07", "\n".join(log))
    record("BD-07", "Bloqueado",
           f"Docker (sa): DDL sin cambios, codigo {rc1}. Login sin sysadmin: codigo {rc}"
           f"{', falla en ALTER AUTHORIZATION' if auth_error else ''}. Express y LocalDB no disponibles en macOS.",
           ev,
           "Solo se pudo usar un entorno real (Docker). El documento (sec. 3.2) indica que en LocalDB se ejecuto "
           "el DDL quitando ALTER AUTHORIZATION ... TO sa, y el README no documenta ese ajuste. "
           "Falta repetirlo en Windows con LocalDB o Express.")


if __name__ == "__main__":
    main()
