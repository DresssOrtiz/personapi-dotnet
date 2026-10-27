"""Casos BD-01 a BD-25: ejecucion de DDL/DML y restricciones en SQL Server.

Uso: python QA/tests/db/db_tests.py
Requiere el contenedor persona-sql levantado segun el README y sin persona_db.
Las inserciones de prueba se ejecutan dentro de transacciones con ROLLBACK
para no alterar los datos del DML.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib import REPO, record, scalar, sqlcmd, write_evidence  # noqa: E402

DDL = os.path.join(REPO, "db", "01_ddl.sql")
DML = os.path.join(REPO, "db", "02_dml.sql")


def attempt(stmt):
    """Ejecuta stmt dentro de una transaccion revertida. Devuelve (aceptado, salida)."""
    _, out = sqlcmd(f"SET NOCOUNT OFF; BEGIN TRAN; {stmt}; IF @@TRANCOUNT > 0 ROLLBACK;", db="persona_db")
    return ("Msg " not in out), out.strip()


def run_attempts(case_id, items):
    """items: lista de (descripcion, sentencia, esperado_aceptado)."""
    log, ok_all, detail = [], True, []
    for desc, stmt, expected in items:
        accepted, out = attempt(stmt)
        ok = accepted == expected
        ok_all &= ok
        log.append(f"-- {desc}\n{stmt}\n=> {'aceptado' if accepted else 'rechazado'} "
                   f"(esperado: {'aceptado' if expected else 'rechazado'})\n{out}\n")
        detail.append(f"{desc}: {'aceptado' if accepted else 'rechazado'}")
    ev = write_evidence(f"BD-{case_id}", "\n".join(log))
    return ok_all, "; ".join(detail), ev


def main():
    # BD-01 DDL en instancia limpia
    pre = scalar("SELECT ISNULL(CAST(DB_ID('persona_db') AS VARCHAR), 'NULL')", db="master")
    rc, out = sqlcmd(script=DDL)
    created = scalar("SELECT ISNULL(CAST(DB_ID('persona_db') AS VARCHAR), 'NULL')", db="master")
    owner = scalar("SELECT SUSER_SNAME(owner_sid) FROM sys.databases WHERE name = 'persona_db'", db="master")
    ev = write_evidence("BD-01", f"DB_ID antes: {pre}\nsqlcmd -b -i db/01_ddl.sql -> codigo {rc}\n{out}\n"
                                  f"DB_ID despues: {created}\nPropietario: {owner}\n")
    ok = rc == 0 and pre == "NULL" and created != "NULL"
    record("BD-01", "Aprobado" if ok else "Fallido",
           f"DDL ejecutado con codigo {rc}, sin mensajes de error; persona_db creada (propietario {owner}).",
           ev, "Ejecutado en SQL Server 2022 en Docker con el usuario sa, segun la opcion A del README.")

    # BD-02 tablas
    _, out = sqlcmd("SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES ORDER BY TABLE_NAME", db="persona_db")
    tables = {t for t in ("persona", "telefono", "profesion", "estudios") if f"|{t}" in out}
    ev = write_evidence("BD-02", out)
    record("BD-02", "Aprobado" if len(tables) == 4 else "Fallido",
           f"INFORMATION_SCHEMA.TABLES lista {len(tables)} de 4 tablas en dbo: {', '.join(sorted(tables))}.", ev)

    # BD-03 columnas y tipos
    _, cols = sqlcmd("SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE "
                     "FROM INFORMATION_SCHEMA.COLUMNS ORDER BY TABLE_NAME, ORDINAL_POSITION", db="persona_db")
    _, checks = sqlcmd("SELECT name, definition FROM sys.check_constraints", db="persona_db")
    expected = ["persona|cc|int", "persona|nombre|varchar|45", "persona|apellido|varchar|45",
                "persona|genero|char|1", "persona|edad|int", "telefono|num|varchar|15",
                "telefono|oper|varchar|45", "telefono|duenio|int", "profesion|id|int",
                "profesion|nom|varchar|90", "profesion|des|varchar|-1", "estudios|id_prof|int",
                "estudios|cc_per|int", "estudios|fecha|date", "estudios|univer|varchar|50"]
    missing = [e for e in expected if e not in cols]
    ok = not missing and "genero" in checks and "'M'" in checks
    ev = write_evidence("BD-03", f"{cols}\n\nCHECK:\n{checks}\n\nFaltantes respecto al modelo: {missing}")
    record("BD-03", "Aprobado" if ok else "Fallido",
           "15 columnas equivalentes al modelo MySQL: INT para cc/id/duenio/cc_per, VARCHAR con las mismas "
           "longitudes, genero CHAR(1) con CHECK ('M','F'), des VARCHAR(MAX), fecha DATE.", ev,
           "ENUM de MySQL reemplazado por CHAR(1) + CHECK y TEXT por VARCHAR(MAX). Las columnas de texto son "
           "VARCHAR (no Unicode); ver BD-23.")

    # BD-04 claves primarias
    _, pks = sqlcmd("SELECT tc.TABLE_NAME, tc.CONSTRAINT_NAME, kcu.COLUMN_NAME, kcu.ORDINAL_POSITION "
                    "FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu "
                    "ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY' "
                    "ORDER BY tc.TABLE_NAME, kcu.ORDINAL_POSITION", db="persona_db")
    ok = all(x in pks for x in ["persona|PK_persona|cc", "profesion|PK_profesion|id", "telefono|PK_telefono|num",
                                "estudios|PK_estudios|id_prof|1", "estudios|PK_estudios|cc_per|2"])
    ev = write_evidence("BD-04", pks)
    record("BD-04", "Aprobado" if ok else "Fallido",
           "PK_persona(cc), PK_profesion(id), PK_telefono(num) y PK_estudios(id_prof, cc_per) compuesta.", ev)

    # BD-05 y BD-06 claves foraneas
    fk_q = ("SELECT fk.name, OBJECT_NAME(fk.parent_object_id) AS tabla, cp.name AS columna, "
            "OBJECT_NAME(fk.referenced_object_id) AS ref_tabla, cr.name AS ref_columna "
            "FROM sys.foreign_keys fk JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id "
            "JOIN sys.columns cp ON cp.object_id = fkc.parent_object_id AND cp.column_id = fkc.parent_column_id "
            "JOIN sys.columns cr ON cr.object_id = fkc.referenced_object_id AND cr.column_id = fkc.referenced_column_id "
            "ORDER BY 1")
    _, fks = sqlcmd(fk_q, db="persona_db")
    ev5 = write_evidence("BD-05", fks)
    record("BD-05", "Aprobado" if "FK_telefono_persona|telefono|duenio|persona|cc" in fks else "Fallido",
           "FK_telefono_persona: telefono.duenio -> persona.cc.", ev5)
    ok = ("FK_estudios_persona|estudios|cc_per|persona|cc" in fks
          and "FK_estudios_profesion|estudios|id_prof|profesion|id" in fks)
    ev6 = write_evidence("BD-06", fks)
    record("BD-06", "Aprobado" if ok else "Fallido",
           "FK_estudios_persona: estudios.cc_per -> persona.cc; FK_estudios_profesion: estudios.id_prof -> profesion.id.", ev6)

    # BD-09 DML
    rc, out = sqlcmd(script=DML)
    ev = write_evidence("BD-09", f"sqlcmd -b -i db/02_dml.sql -> codigo {rc}\n{out}")
    record("BD-09", "Aprobado" if rc == 0 and "Msg " not in out else "Fallido",
           f"DML ejecutado con codigo {rc}, sin violaciones de restricciones.", ev)

    # BD-10 conteos
    counts = {t: scalar(f"SELECT COUNT(*) FROM dbo.{t}") for t in ("persona", "profesion", "telefono", "estudios")}
    ok = counts == {"persona": "5", "profesion": "4", "telefono": "5", "estudios": "6"}
    ev = write_evidence("BD-10", "\n".join(f"{k}: {v}" for k, v in counts.items()) +
                        "\nEsperado segun 02_dml.sql: persona 5, profesion 4, telefono 5, estudios 6")
    record("BD-10", "Aprobado" if ok else "Fallido",
           f"persona {counts['persona']}, profesion {counts['profesion']}, telefono {counts['telefono']}, "
           f"estudios {counts['estudios']} (20 registros), igual al DML.", ev)

    # BD-11 huerfanos
    q = ("SELECT 'telefono' AS t, COUNT(*) FROM dbo.telefono t LEFT JOIN dbo.persona p ON p.cc = t.duenio WHERE p.cc IS NULL "
         "UNION ALL SELECT 'estudios-persona', COUNT(*) FROM dbo.estudios e LEFT JOIN dbo.persona p ON p.cc = e.cc_per WHERE p.cc IS NULL "
         "UNION ALL SELECT 'estudios-profesion', COUNT(*) FROM dbo.estudios e LEFT JOIN dbo.profesion f ON f.id = e.id_prof WHERE f.id IS NULL")
    _, out = sqlcmd(q, db="persona_db")
    ok = all(l.endswith("|0") for l in out.splitlines() if l.startswith(("telefono", "estudios")))
    ev = write_evidence("BD-11", f"{q}\n\n{out}")
    record("BD-11", "Aprobado" if ok else "Fallido", "0 telefonos y 0 estudios huerfanos.", ev)

    # BD-12 obligatorios
    ok, det, ev = run_attempts("12", [
        ("sin nombre", "INSERT INTO dbo.persona (cc, apellido, genero) VALUES (9001, 'Prueba', 'M')", False),
        ("sin apellido", "INSERT INTO dbo.persona (cc, nombre, genero) VALUES (9001, 'Prueba', 'M')", False),
        ("sin genero", "INSERT INTO dbo.persona (cc, nombre, apellido) VALUES (9001, 'Prueba', 'Prueba')", False),
    ])
    record("BD-12", "Aprobado" if ok else "Fallido", det + " (Msg 515, NOT NULL).", ev)

    # BD-13 genero
    ok, det, ev = run_attempts("13", [
        ("genero X", "INSERT INTO dbo.persona VALUES (9001, 'Prueba', 'Prueba', 'X', 20)", False),
        ("genero M", "INSERT INTO dbo.persona VALUES (9001, 'Prueba', 'Prueba', 'M', 20)", True),
        ("genero F", "INSERT INTO dbo.persona VALUES (9002, 'Prueba', 'Prueba', 'F', 20)", True),
    ])
    record("BD-13", "Aprobado" if ok else "Fallido", det + " (Msg 547, CK_persona_genero).", ev)

    # BD-14 edad
    ok, det, ev = run_attempts("14", [
        ("edad NULL", "INSERT INTO dbo.persona VALUES (9001, 'Prueba', 'Prueba', 'M', NULL)", True),
        ("edad -1", "INSERT INTO dbo.persona VALUES (9002, 'Prueba', 'Prueba', 'M', -1)", False),
    ])
    record("BD-14", "Aprobado" if ok else "Fallido", det + " (CK_persona_edad).", ev,
           "La base no limita la edad maxima; el limite 0-150 solo existe en el DTO de la API.")

    # BD-15 PK duplicadas
    ok, det, ev = run_attempts("15", [
        ("persona 1001", "INSERT INTO dbo.persona VALUES (1001, 'Dup', 'Dup', 'M', 20)", False),
        ("telefono 3001112233", "INSERT INTO dbo.telefono VALUES ('3001112233', 'Claro', 1002)", False),
        ("profesion 1", "INSERT INTO dbo.profesion VALUES (1, 'Dup', NULL)", False),
    ])
    record("BD-15", "Aprobado" if ok else "Fallido", det + " (Msg 2627, PRIMARY KEY).", ev)

    # BD-16 FK telefono
    ok, det, ev = run_attempts("16", [
        ("duenio 999999", "INSERT INTO dbo.telefono VALUES ('3999999999', 'Claro', 999999)", False),
    ])
    record("BD-16", "Aprobado" if ok else "Fallido", det + " (Msg 547, FK_telefono_persona).", ev)

    # BD-17 FK estudios
    ok, det, ev = run_attempts("17", [
        ("cc_per inexistente", "INSERT INTO dbo.estudios VALUES (1, 999999, '2020-01-01', 'U')", False),
        ("id_prof inexistente", "INSERT INTO dbo.estudios VALUES (999, 1001, '2020-01-01', 'U')", False),
    ])
    record("BD-17", "Aprobado" if ok else "Fallido", det + " (Msg 547, FK de estudios).", ev)

    # BD-18 PK compuesta
    ok, det, ev = run_attempts("18", [
        ("par (1,1001) duplicado", "INSERT INTO dbo.estudios VALUES (1, 1001, '2020-01-01', 'U')", False),
        ("persona 1001 con profesion 2", "INSERT INTO dbo.estudios VALUES (2, 1001, '2020-01-01', 'U')", True),
        ("profesion 1 con persona 1005", "INSERT INTO dbo.estudios VALUES (1, 1005, '2020-01-01', 'U')", True),
    ])
    record("BD-18", "Aprobado" if ok else "Fallido", det + ".", ev)

    # BD-19 / BD-20 eliminacion con dependientes
    ok, det, ev = run_attempts("19", [("DELETE persona 1001", "DELETE FROM dbo.persona WHERE cc = 1001", False)])
    remain = scalar("SELECT COUNT(*) FROM dbo.persona WHERE cc = 1001")
    record("BD-19", "Aprobado" if ok and remain == "1" else "Fallido",
           det + f" (Msg 547); la persona 1001 permanece ({remain} fila).", ev)
    ok, det, ev = run_attempts("20", [("DELETE profesion 1", "DELETE FROM dbo.profesion WHERE id = 1", False)])
    record("BD-20", "Aprobado" if ok else "Fallido", det + " (Msg 547, FK_estudios_profesion).", ev)

    # BD-21 eliminacion sin dependientes
    stmt = ("INSERT INTO dbo.persona VALUES (9001, 'Temp', 'Temp', 'F', 30); "
            "INSERT INTO dbo.profesion VALUES (901, 'Temp', NULL); "
            "INSERT INTO dbo.telefono VALUES ('3990000001', 'Claro', 9001); "
            "INSERT INTO dbo.estudios VALUES (901, 9001, NULL, NULL); "
            "DELETE FROM dbo.telefono WHERE num = '3990000001'; "
            "DELETE FROM dbo.estudios WHERE id_prof = 901 AND cc_per = 9001; "
            "DELETE FROM dbo.profesion WHERE id = 901; DELETE FROM dbo.persona WHERE cc = 9001")
    ok, det, ev = run_attempts("21", [("crear y eliminar registros sin dependientes", stmt, True)])
    record("BD-21", "Aprobado" if ok else "Fallido",
           "Telefono, estudio, profesion y persona temporales creados y eliminados sin errores.", ev)

    # BD-22 longitudes
    items = []
    for desc, tmpl, n in [("nombre", "INSERT INTO dbo.persona VALUES (9001, '{v}', 'A', 'M', 1)", 45),
                          ("apellido", "INSERT INTO dbo.persona VALUES (9001, 'A', '{v}', 'M', 1)", 45),
                          ("nom", "INSERT INTO dbo.profesion VALUES (901, '{v}', NULL)", 90),
                          ("univer", "INSERT INTO dbo.estudios VALUES (1, 1005, NULL, '{v}')", 50),
                          ("num", "INSERT INTO dbo.telefono VALUES ('{v}', 'Claro', 1001)", 15),
                          ("oper", "INSERT INTO dbo.telefono VALUES ('3990000002', '{v}', 1001)", 45)]:
        items.append((f"{desc} {n}", tmpl.format(v="9" * n), True))
        items.append((f"{desc} {n + 1}", tmpl.format(v="9" * (n + 1)), False))
    ok, det, ev = run_attempts("22", items)
    record("BD-22", "Aprobado" if ok else "Fallido",
           "Longitud maxima aceptada y maxima + 1 rechazada (Msg 2628, truncamiento) en los 6 campos.", ev)

    # BD-23 tildes y enie
    log = []
    for cc, nom, ape in [(9101, "José", "Muñoz"), (9102, "Ángela", "Peña")]:
        _, out = sqlcmd(f"INSERT INTO dbo.persona VALUES ({cc}, '{nom}', '{ape}', 'F', 20); "
                        f"SELECT nombre, apellido, CAST(nombre AS VARBINARY(20)) FROM dbo.persona WHERE cc = {cc}",
                        db="persona_db")
        log.append(out)
    read = scalar("SELECT nombre + ' ' + apellido FROM dbo.persona WHERE cc = 9101") + " / " + \
        scalar("SELECT nombre + ' ' + apellido FROM dbo.persona WHERE cc = 9102")
    _, out = sqlcmd("INSERT INTO dbo.persona VALUES (9103, N'Nguyễn', N'Łukasz', 'M', 20); "
                    "SELECT nombre, apellido FROM dbo.persona WHERE cc = 9103", db="persona_db")
    log.append("Control fuera del codigo de pagina 1252:\n" + out)
    sqlcmd("DELETE FROM dbo.persona WHERE cc IN (9101, 9102, 9103)", db="persona_db")
    ok = read == "José Muñoz / Ángela Peña"
    ev = write_evidence("BD-23", "\n".join(log) + f"\nLeido: {read}")
    record("BD-23", "Aprobado" if ok else "Fallido",
           f"Se guardan y leen sin alteracion: {read}.", ev,
           "Columnas VARCHAR con collation SQL_Latin1_General_CP1_CI_AS (codigo de pagina 1252): tildes y ñ se "
           "conservan; caracteres fuera de 1252 se alteran ('Nguyễn' -> 'Nguy?n', 'Łukasz' -> 'Lukasz'). "
           "Mejora sugerida: NVARCHAR.")

    # BD-24 rango cc
    ok, det, ev = run_attempts("24", [
        ("cc 2147483647", "INSERT INTO dbo.persona VALUES (2147483647, 'Max', 'Max', 'M', 1)", True),
        ("cc 2147483648", "INSERT INTO dbo.persona VALUES (2147483648, 'Max', 'Max', 'M', 1)", False),
        ("cc 1014857924 (10 digitos)", "INSERT INTO dbo.persona VALUES (1014857924, 'Diez', 'Digitos', 'M', 1)", True),
    ])
    record("BD-24", "Aprobado" if ok else "Fallido",
           det + ". Tipo INT (maximo 2.147.483.647).", ev,
           "El INT cubre las cedulas de 10 digitos vigentes que empiezan por 1 (hasta 1.999.999.999) y equivale al "
           "INT(15) del modelo MySQL, que tambien es de 32 bits. No admite valores desde 2.147.483.648; si se "
           "requieren, conviene BIGINT o VARCHAR.")

    # BD-25 fechas
    ok, det, ev = run_attempts("25", [
        ("fecha 2020-02-29", "INSERT INTO dbo.estudios VALUES (2, 1001, '2020-02-29', 'U')", True),
        ("fecha NULL", "INSERT INTO dbo.estudios VALUES (2, 1001, NULL, 'U')", True),
        ("fecha 2026-02-31", "INSERT INTO dbo.estudios VALUES (2, 1001, '2026-02-31', 'U')", False),
    ])
    future, _ = attempt("INSERT INTO dbo.estudios VALUES (2, 1001, '2099-01-01', 'U')")
    record("BD-25", "Aprobado" if ok else "Fallido", det + " (Msg 241, conversion de fecha).", ev,
           f"Control adicional: la fecha futura 2099-01-01 es {'aceptada' if future else 'rechazada'}; "
           "no hay CHECK sobre fecha.")

    # BD-08 re-ejecucion del DDL con datos cargados
    before = scalar("SELECT COUNT(*) FROM dbo.persona")
    rc1, out1 = sqlcmd(script=DDL)
    after = {t: scalar(f"SELECT COUNT(*) FROM dbo.{t}") for t in ("persona", "profesion", "telefono", "estudios")}
    rc2, out2 = sqlcmd(script=DML)
    restored = {t: scalar(f"SELECT COUNT(*) FROM dbo.{t}") for t in ("persona", "profesion", "telefono", "estudios")}
    with open(DDL, encoding="utf-8") as f:
        ddl_txt = f.read()
    with open(os.path.join(REPO, "README.md"), encoding="utf-8") as f:
        readme = f.read()
    documented = any(w in readme.lower() for w in ("drop table", "elimina las tablas", "recrea", "borra"))
    ev = write_evidence("BD-08", f"persona antes: {before}\nDDL re-ejecutado -> codigo {rc1}\n{out1}\n"
                                  f"Conteos tras DDL: {after}\nDML -> codigo {rc2}\n{out2}\nConteos tras DML: {restored}\n"
                                  f"DROP TABLE en el DDL: {'DROP TABLE' in ddl_txt}\n"
                                  f"README documenta la recreacion: {documented}\n")
    ok_restore = rc2 == 0 and restored == {"persona": "5", "profesion": "4", "telefono": "5", "estudios": "6"}
    record("BD-08", "Aprobado" if (ok_restore and documented) else "Fallido",
           f"El DDL termina con codigo {rc1}, hace DROP TABLE de las 4 tablas y deja 0 registros (persona {before} -> "
           f"{after['persona']}). El DML restaura los 20 registros. El README no advierte que se borran los datos.",
           ev, "Propuesta: advertir en el README y en el encabezado del DDL que "
               "re-ejecutarlo elimina los datos, o usar IF OBJECT_ID(...) IS NULL CREATE TABLE.")


if __name__ == "__main__":
    main()
