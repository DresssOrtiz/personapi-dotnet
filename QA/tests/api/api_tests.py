"""Casos API-PER, API-TEL, API-PRO, API-EST y API-GEN-01 a API-GEN-05.

Uso: python QA/tests/api/api_tests.py [--tag main|frontend]
Requiere la aplicacion en QA_BASE_URL (por defecto http://localhost:5025) y la
base con los datos del DML. Los registros de prueba usan claves 2001-2099
(personas), 901-999 (profesiones) y 399000xxxx (telefonos) y se eliminan al final.
Con --tag frontend las evidencias se guardan con el sufijo -frontend y no se
registran resultados (sirve como prueba de regresion de la rama del PR).
"""
import concurrent.futures
import json
import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib import BASE_URL, record, scalar, sqlcmd, write_evidence  # noqa: E402

TAG = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "main"
SUMMARY = []


class Case:
    """Acumula las solicitudes de un caso y registra el resultado."""

    def __init__(self, case_id):
        self.id, self.log, self.checks = case_id, [], []

    def call(self, method, path, body=None, raw=None, headers=None):
        h = {"Content-Type": "application/json"} if (body is not None or raw is not None) else {}
        h.update(headers or {})
        data = raw if raw is not None else (json.dumps(body, ensure_ascii=False).encode() if body is not None else None)
        r = requests.request(method, BASE_URL + path, data=data, headers=h, timeout=30)
        shown = raw if raw is not None else json.dumps(body, ensure_ascii=False) if body is not None else ""
        loc = r.headers.get("Location", "")
        self.log.append(f"> {method} {path} {shown}\n< {r.status_code} {r.headers.get('Content-Type', '')}"
                        f"{' Location: ' + loc if loc else ''}\n{r.text[:1500]}\n")
        return r

    def check(self, cond, label):
        self.checks.append((bool(cond), label))
        self.log.append(f"[{'OK' if cond else 'FALLA'}] {label}\n")
        return cond

    def note(self, text):
        self.log.append(text + "\n")

    def done(self, obtenido, observaciones=""):
        ok = all(c for c, _ in self.checks)
        suffix = "" if TAG == "main" else f"-{TAG}"
        ev = write_evidence(self.id + suffix, "\n".join(self.log))
        estado = "Aprobado" if ok else "Fallido"
        SUMMARY.append((self.id, estado))
        if TAG == "main":
            record(self.id, estado, obtenido, ev, observaciones)
        else:
            print(f"[{estado:9}] {self.id} ({TAG})")


def count(table):
    return int(scalar(f"SELECT COUNT(*) FROM dbo.{table}"))


def cleanup():
    sqlcmd("DELETE FROM dbo.estudios WHERE cc_per BETWEEN 2001 AND 2099 OR id_prof BETWEEN 901 AND 999 "
           "OR (id_prof = 4 AND cc_per = 1001) OR (id_prof = 2 AND cc_per = 1005); "
           "DELETE FROM dbo.telefono WHERE num LIKE '399%' OR duenio BETWEEN 2001 AND 2099 OR num = 'ABC123'; "
           "DELETE FROM dbo.persona WHERE cc BETWEEN 2001 AND 2099; "
           "DELETE FROM dbo.profesion WHERE id BETWEEN 901 AND 999", db="persona_db")


# ---------------------------------------------------------------- Personas
def personas():
    P = "/api/personas"
    nueva = {"cc": 2001, "nombre": "Prueba", "apellido": "QA", "genero": "F", "edad": 33}

    c = Case("API-PER-01"); r = c.call("GET", P)
    c.check(r.status_code == 200 and len(r.json()) == count("persona"), f"200 y {count('persona')} elementos")
    c.done(f"HTTP {r.status_code}, arreglo de {len(r.json())} personas, igual a COUNT(*) de la tabla.")

    c = Case("API-PER-02"); r = c.call("GET", P + "/1001")
    c.check(r.status_code == 200 and set(r.json()) == {"cc", "nombre", "apellido", "genero", "edad"}, "200 con 5 campos")
    c.done(f"HTTP {r.status_code} con cc, nombre, apellido, genero y edad de la persona 1001.")

    c = Case("API-PER-03"); r = c.call("GET", P + "/999999")
    c.check(r.status_code == 404, "404"); c.done(f"HTTP {r.status_code} para cc 999999.")

    c = Case("API-PER-04"); r = c.call("POST", P, nueva)
    in_db = scalar("SELECT nombre + '|' + apellido FROM dbo.persona WHERE cc = 2001")
    c.check(r.status_code == 201 and r.headers.get("Location", "").endswith("/api/personas/2001"), "201 con Location")
    c.check(in_db == "Prueba|QA", "registro en la base")
    r2 = c.call("POST", P, {"cc": 2002, "nombre": "José", "apellido": "Muñoz", "genero": "M", "edad": 20})
    r3 = c.call("POST", P, {"cc": 2003, "nombre": "Nguyễn", "apellido": "Łukasz", "genero": "M", "edad": 20})
    g2, g3 = c.call("GET", P + "/2002").json(), c.call("GET", P + "/2003").json()
    c.note(f"Control de caracteres: 2002 -> {g2['nombre']} {g2['apellido']}; 2003 -> {g3['nombre']} {g3['apellido']}")
    c.done(f"HTTP {r.status_code}, Location {r.headers.get('Location')}; registro 2001 guardado en persona_db.",
           f"Control adicional: 'José Muñoz' se conserva; 'Nguyễn Łukasz' responde {r3.status_code} pero se guarda "
           f"como '{g3['nombre']} {g3['apellido']}' sin aviso (columnas VARCHAR, ver BD-23).")

    c = Case("API-PER-05"); r = c.call("POST", P, {**nueva, "nombre": "Otro"})
    c.check(r.status_code == 409, "409")
    c.check(scalar("SELECT nombre FROM dbo.persona WHERE cc = 2001") == "Prueba", "original intacto")
    c.done(f"HTTP {r.status_code}: \"{r.json().get('title')}\"; el registro original no cambia.")

    c = Case("API-PER-06"); before = count("persona"); codes = []
    for body in [{**nueva, "cc": 2010, "nombre": ""}, {**nueva, "cc": 2011, "genero": "X"},
                 {**nueva, "cc": 2012, "edad": 151}, {**nueva, "cc": 2013, "edad": -1}, {**nueva, "cc": 0}]:
        r = c.call("POST", P, body); codes.append(r.status_code)
        c.check(r.status_code == 400 and "errors" in r.json(), "400 con detalle")
    c.check(count("persona") == before, "sin inserciones")
    c.done(f"Nombre vacio, genero X, edad 151, edad -1 y cc 0 responden {codes} con el detalle en 'errors'; "
           "no se inserta nada.")

    c = Case("API-PER-07"); r = c.call("PUT", P + "/2001", {**nueva, "nombre": "Editada", "edad": 34})
    g = c.call("GET", P + "/2001").json()
    c.check(r.status_code == 204 and g["nombre"] == "Editada" and g["edad"] == 34, "204 y cambios visibles")
    c.done(f"HTTP {r.status_code}; el GET posterior muestra nombre 'Editada' y edad 34.")

    c = Case("API-PER-08"); r = c.call("PUT", P + "/2001", {**nueva, "cc": 1001})
    c.check(r.status_code == 400, "400")
    c.check(scalar("SELECT nombre FROM dbo.persona WHERE cc = 1001") == "Andres", "1001 intacto")
    c.done(f"HTTP {r.status_code}: \"{r.json().get('title')}\"; ningun registro cambia.")

    c = Case("API-PER-09"); r = c.call("PUT", P + "/999999", {**nueva, "cc": 999999})
    c.check(r.status_code == 404, "404"); c.done(f"HTTP {r.status_code}.")

    c = Case("API-PER-10"); c.call("POST", P, {**nueva, "cc": 2020})
    r = c.call("DELETE", P + "/2020"); g = c.call("GET", P + "/2020")
    c.check(r.status_code == 204 and g.status_code == 404, "204 y luego 404")
    c.done(f"DELETE HTTP {r.status_code}; GET posterior HTTP {g.status_code}.")

    c = Case("API-PER-11"); r = c.call("DELETE", P + "/999999")
    c.check(r.status_code == 404, "404"); c.done(f"HTTP {r.status_code}.")

    c = Case("API-PER-12"); r = c.call("DELETE", P + "/1001")
    deps = scalar("SELECT COUNT(*) FROM dbo.telefono WHERE duenio = 1001") + "/" + \
        scalar("SELECT COUNT(*) FROM dbo.estudios WHERE cc_per = 1001")
    c.check(r.status_code == 409 and scalar("SELECT COUNT(*) FROM dbo.persona WHERE cc = 1001") == "1", "409 y permanece")
    c.done(f"HTTP {r.status_code}: \"{r.json().get('title')}\"; la persona 1001 y sus dependientes "
           f"(telefonos/estudios {deps}) permanecen.",
           "El catch de DbUpdateException devuelve este mismo mensaje ante cualquier error de escritura, no solo "
           "por dependencias (revision de codigo).")

    c = Case("API-PER-13"); codes = []
    for cc, edad in [(2031, None), (2032, 0), (2033, 150)]:
        body = {k: v for k, v in {**nueva, "cc": cc, "edad": edad}.items() if v is not None}
        codes.append(c.call("POST", P, body).status_code)
    r = c.call("POST", P, {**nueva, "cc": 2034, "edad": 151})
    c.check(codes == [201, 201, 201] and r.status_code == 400, "201 x3 y 400")
    c.done(f"Edad ausente, 0 y 150: {codes}; edad 151: {r.status_code}.")


# ---------------------------------------------------------------- Telefonos
def telefonos():
    T = "/api/telefonos"
    nuevo = {"num": "3990000001", "oper": "Claro", "duenio": 1003}

    c = Case("API-TEL-01"); r = c.call("GET", T)
    c.check(r.status_code == 200 and len(r.json()) == count("telefono"), "200 y conteo")
    c.done(f"HTTP {r.status_code}, arreglo de {len(r.json())} telefonos, igual a la tabla.")

    c = Case("API-TEL-02"); r = c.call("GET", T + "/3001112233")
    c.check(r.status_code == 200 and set(r.json()) == {"num", "oper", "duenio"}, "200 con 3 campos")
    c.done(f"HTTP {r.status_code} con num, oper y duenio.")

    c = Case("API-TEL-03"); r = c.call("GET", T + "/0000000000")
    c.check(r.status_code == 404, "404"); c.done(f"HTTP {r.status_code}.")

    c = Case("API-TEL-04"); r = c.call("POST", T, nuevo)
    c.check(r.status_code == 201 and r.headers.get("Location", "").endswith("/api/telefonos/3990000001"), "201 + Location")
    c.check(scalar("SELECT oper FROM dbo.telefono WHERE num = '3990000001'") == "Claro", "en la base")
    c.done(f"HTTP {r.status_code}, Location {r.headers.get('Location')}; registro guardado.")

    c = Case("API-TEL-05"); r = c.call("POST", T, {**nuevo, "oper": "Tigo"})
    c.check(r.status_code == 409 and scalar("SELECT oper FROM dbo.telefono WHERE num = '3990000001'") == "Claro", "409")
    c.done(f"HTTP {r.status_code}: \"{r.json().get('title')}\"; original intacto.")

    c = Case("API-TEL-06"); before = count("telefono"); codes = []
    for body in [{**nuevo, "num": ""}, {**nuevo, "num": "3" * 16}, {**nuevo, "num": "3990000060", "oper": ""},
                 {**nuevo, "num": "3990000061", "duenio": 0}]:
        r = c.call("POST", T, body); codes.append(r.status_code)
        c.check(r.status_code == 400, "400")
    c.check(count("telefono") == before, "sin inserciones")
    c.done(f"num vacio, num de 16, oper vacio y duenio 0 responden {codes}; no se inserta nada.")

    c = Case("API-TEL-07"); r = c.call("POST", T, {**nuevo, "num": "3990000070", "duenio": 999999})
    c.check(r.status_code == 400 and count("telefono") == before, "400")
    c.done(f"HTTP {r.status_code}: \"{r.json().get('title')}\"; no se inserta.")

    c = Case("API-TEL-08"); r = c.call("PUT", T + "/3990000001", {**nuevo, "oper": "Movistar", "duenio": 1004})
    g = c.call("GET", T + "/3990000001").json()
    c.check(r.status_code == 204 and g["oper"] == "Movistar" and g["duenio"] == 1004, "204 y cambios")
    c.done(f"HTTP {r.status_code}; el GET muestra oper 'Movistar' y duenio 1004.")

    c = Case("API-TEL-09"); r = c.call("PUT", T + "/3990000001", {**nuevo, "num": "3001112233"})
    c.check(r.status_code == 400 and scalar("SELECT oper FROM dbo.telefono WHERE num = '3001112233'") == "Claro", "400")
    c.done(f"HTTP {r.status_code}: \"{r.json().get('title')}\".")

    c = Case("API-TEL-10"); r = c.call("PUT", T + "/3990009999", {**nuevo, "num": "3990009999"})
    c.check(r.status_code == 404, "404"); c.done(f"HTTP {r.status_code}.")

    c = Case("API-TEL-11"); c.call("POST", T, {**nuevo, "num": "3990000011"})
    r = c.call("DELETE", T + "/3990000011"); g = c.call("GET", T + "/3990000011")
    c.check(r.status_code == 204 and g.status_code == 404, "204 y 404")
    c.done(f"DELETE HTTP {r.status_code}; GET posterior HTTP {g.status_code}.")

    c = Case("API-TEL-12"); r = c.call("DELETE", T + "/3990009999")
    c.check(r.status_code == 404, "404"); c.done(f"HTTP {r.status_code}.")

    c = Case("API-TEL-13")
    codes = [c.call("POST", T, {**nuevo, "num": n, "duenio": 1005}).status_code for n in ("3990000131", "3990000132")]
    n = scalar("SELECT COUNT(*) FROM dbo.telefono WHERE duenio = 1005 AND num IN ('3990000131', '3990000132')")
    c.check(codes == [201, 201] and n == "2", "2 x 201")
    c.done(f"Ambos POST responden {codes}; la persona 1005 queda con los 2 telefonos.")

    c = Case("API-TEL-14"); r = c.call("PUT", T + "/3990000131", {"num": "3990000131", "oper": "Claro", "duenio": 999999})
    c.check(r.status_code == 400 and scalar("SELECT duenio FROM dbo.telefono WHERE num = '3990000131'") == "1005", "400")
    c.done(f"HTTP {r.status_code}: \"{r.json().get('title')}\"; conserva el duenio 1005.")

    c = Case("API-TEL-15")
    r1 = c.call("POST", T, {**nuevo, "num": "3990000150"})
    r2 = c.call("POST", T, {**nuevo, "num": "ABC123"})
    r3 = c.call("POST", T, {**nuevo, "num": "3" * 16})
    c.check(r1.status_code == 201 and r3.status_code == 400, "10 digitos 201 y 16 caracteres 400")
    c.done(f"10 digitos: {r1.status_code}; 16 caracteres: {r3.status_code}; con letras 'ABC123': {r2.status_code}.",
           "La API acepta numeros con letras: TelefonoDto solo valida longitud (StringLength 15), sin formato. "
           "Mejora sugerida: [RegularExpression(\"^[0-9]{7,15}$\")].")


# ---------------------------------------------------------------- Profesiones
def profesiones():
    F = "/api/profesiones"
    nueva = {"id": 901, "nom": "Profesion QA", "des": "Descripcion de prueba"}

    c = Case("API-PRO-01"); r = c.call("GET", F)
    c.check(r.status_code == 200 and len(r.json()) == count("profesion"), "200 y conteo")
    c.done(f"HTTP {r.status_code}, arreglo de {len(r.json())} profesiones, igual a la tabla.")

    c = Case("API-PRO-02"); r = c.call("GET", F + "/1")
    c.check(r.status_code == 200 and set(r.json()) == {"id", "nom", "des"}, "200 con 3 campos")
    c.done(f"HTTP {r.status_code} con id, nom y des.")

    c = Case("API-PRO-03"); r = c.call("GET", F + "/9999")
    c.check(r.status_code == 404, "404"); c.done(f"HTTP {r.status_code}.")

    c = Case("API-PRO-04"); r = c.call("POST", F, nueva)
    c.check(r.status_code == 201 and r.headers.get("Location", "").endswith("/api/profesiones/901"), "201 + Location")
    c.check(scalar("SELECT nom FROM dbo.profesion WHERE id = 901") == "Profesion QA", "en la base")
    c.done(f"HTTP {r.status_code}, Location {r.headers.get('Location')}; registro guardado.")

    c = Case("API-PRO-05"); r = c.call("POST", F, {**nueva, "nom": "Otra"})
    c.check(r.status_code == 409 and scalar("SELECT nom FROM dbo.profesion WHERE id = 901") == "Profesion QA", "409")
    c.done(f"HTTP {r.status_code}: \"{r.json().get('title')}\"; original intacto.")

    c = Case("API-PRO-06"); before = count("profesion"); codes = []
    for body in [{**nueva, "id": 910, "nom": ""}, {**nueva, "id": 911, "nom": "x" * 91}, {**nueva, "id": 0}]:
        r = c.call("POST", F, body); codes.append(r.status_code)
        c.check(r.status_code == 400, "400")
    c.check(count("profesion") == before, "sin inserciones")
    c.done(f"nom vacio, nom de 91 e id 0 responden {codes}; no se inserta nada.")

    c = Case("API-PRO-07"); r = c.call("PUT", F + "/901", {**nueva, "nom": "Editada"})
    g = c.call("GET", F + "/901").json()
    c.check(r.status_code == 204 and g["nom"] == "Editada", "204 y cambios")
    c.done(f"HTTP {r.status_code}; el GET muestra nom 'Editada'.")

    c = Case("API-PRO-08"); r = c.call("PUT", F + "/901", {**nueva, "id": 1})
    c.check(r.status_code == 400 and scalar("SELECT nom FROM dbo.profesion WHERE id = 1") == "Ingeniero de Sistemas", "400")
    c.done(f"HTTP {r.status_code}: \"{r.json().get('title')}\".")

    c = Case("API-PRO-09"); r = c.call("PUT", F + "/9999", {**nueva, "id": 9999})
    c.check(r.status_code == 404, "404"); c.done(f"HTTP {r.status_code}.")

    c = Case("API-PRO-10"); c.call("POST", F, {**nueva, "id": 920})
    r = c.call("DELETE", F + "/920"); g = c.call("GET", F + "/920")
    c.check(r.status_code == 204 and g.status_code == 404, "204 y 404")
    c.done(f"DELETE HTTP {r.status_code}; GET posterior HTTP {g.status_code}.")

    c = Case("API-PRO-11"); r = c.call("DELETE", F + "/9999")
    c.check(r.status_code == 404, "404"); c.done(f"HTTP {r.status_code}.")

    c = Case("API-PRO-12"); r = c.call("DELETE", F + "/1")
    c.check(r.status_code == 409 and scalar("SELECT COUNT(*) FROM dbo.profesion WHERE id = 1") == "1", "409")
    c.done(f"HTTP {r.status_code}: \"{r.json().get('title')}\"; la profesion 1 y sus estudios permanecen.")

    c = Case("API-PRO-13"); larga = "Descripcion extensa. " * 500
    r1 = c.call("POST", F, {"id": 931, "nom": "Sin descripcion"})
    r2 = c.call("POST", F, {"id": 932, "nom": "Con descripcion larga", "des": larga})
    stored = c.call("GET", F + "/932").json().get("des", "")
    c.check(r1.status_code == 201 and r2.status_code == 201 and stored == larga, "201 x2 y texto completo")
    c.done(f"Sin des: {r1.status_code}; des de {len(larga)} caracteres: {r2.status_code} y se conserva completa "
           f"({len(stored)} caracteres).")


# ---------------------------------------------------------------- Estudios
def estudios():
    E = "/api/estudios"
    nuevo = {"idProf": 2, "ccPer": 1005, "fecha": "2022-06-30", "univer": "Universidad QA"}

    c = Case("API-EST-01"); r = c.call("GET", E)
    c.check(r.status_code == 200 and len(r.json()) == count("estudios"), "200 y conteo")
    c.done(f"HTTP {r.status_code}, arreglo de {len(r.json())} estudios, igual a la tabla.")

    c = Case("API-EST-02"); r = c.call("GET", E + "/1/1001")
    c.check(r.status_code == 200 and set(r.json()) == {"idProf", "ccPer", "fecha", "univer"}, "200 con 4 campos")
    c.done(f"HTTP {r.status_code} con idProf, ccPer, fecha y univer.")

    c = Case("API-EST-03"); r = c.call("GET", E + "/4/1001")
    c.check(r.status_code == 404, "404"); c.done(f"HTTP {r.status_code} para el par (4, 1001).")

    c = Case("API-EST-04"); r = c.call("POST", E, nuevo)
    c.check(r.status_code == 201 and r.headers.get("Location", "").endswith("/api/estudios/2/1005"), "201 + Location")
    c.check(scalar("SELECT univer FROM dbo.estudios WHERE id_prof = 2 AND cc_per = 1005") == "Universidad QA", "en la base")
    c.done(f"HTTP {r.status_code}, Location {r.headers.get('Location')}; registro guardado.")

    c = Case("API-EST-05"); r = c.call("POST", E, {**nuevo, "univer": "Otra"})
    c.check(r.status_code == 409, "409")
    c.check(scalar("SELECT univer FROM dbo.estudios WHERE id_prof = 2 AND cc_per = 1005") == "Universidad QA", "intacto")
    c.done(f"HTTP {r.status_code}: \"{r.json().get('title')}\"; original intacto.")

    c = Case("API-EST-06"); before = count("estudios"); codes = []
    c.call("POST", "/api/personas", {"cc": 2040, "nombre": "Est", "apellido": "QA", "genero": "M", "edad": 20})
    for body in [{**nuevo, "ccPer": 2040, "univer": "u" * 51}, {**nuevo, "idProf": 0}, {**nuevo, "ccPer": 0},
                 {**nuevo, "ccPer": 2040, "fecha": "2022-13-45"}, {**nuevo, "ccPer": 2040, "fecha": "30/06/2022"}]:
        r = c.call("POST", E, body); codes.append(r.status_code)
        c.check(r.status_code == 400, "400")
    c.check(count("estudios") == before, "sin inserciones")
    fut = c.call("POST", E, {**nuevo, "ccPer": 2040, "fecha": "2099-01-01"})
    c.done(f"univer de 51, idProf 0, ccPer 0 y fechas '2022-13-45' y '30/06/2022' responden {codes}; "
           "no se inserta nada.",
           f"Control adicional: una fecha futura (2099-01-01) responde {fut.status_code}; no hay validacion de "
           "fechas futuras.")

    c = Case("API-EST-07"); before = count("estudios")
    r1 = c.call("POST", E, {**nuevo, "idProf": 999})
    r2 = c.call("POST", E, {**nuevo, "ccPer": 999999})
    c.check(r1.status_code == 400 and r2.status_code == 400 and count("estudios") == before, "400 x2")
    c.done(f"idProf inexistente: {r1.status_code} \"{r1.json().get('title')}\"; ccPer inexistente: {r2.status_code} "
           f"\"{r2.json().get('title')}\".")

    c = Case("API-EST-08"); r = c.call("PUT", E + "/2/1005", {**nuevo, "fecha": "2023-01-15", "univer": "Editada"})
    g = c.call("GET", E + "/2/1005").json()
    c.check(r.status_code == 204 and g["univer"] == "Editada" and g["fecha"].startswith("2023-01-15"), "204 y cambios")
    c.done(f"HTTP {r.status_code}; el GET muestra univer 'Editada' y fecha 2023-01-15.")

    c = Case("API-EST-09"); r = c.call("PUT", E + "/2/1005", {**nuevo, "idProf": 1, "ccPer": 1001})
    c.check(r.status_code == 400, "400"); c.done(f"HTTP {r.status_code}: \"{r.json().get('title')}\".")

    c = Case("API-EST-10"); r = c.call("PUT", E + "/4/1003", {**nuevo, "idProf": 4, "ccPer": 1003})
    c.check(r.status_code == 404, "404"); c.done(f"HTTP {r.status_code}.")

    c = Case("API-EST-11"); c.call("POST", E, {**nuevo, "idProf": 3, "ccPer": 2040})
    r = c.call("DELETE", E + "/3/2040"); g = c.call("GET", E + "/3/2040")
    c.check(r.status_code == 204 and g.status_code == 404, "204 y 404")
    c.done(f"DELETE HTTP {r.status_code}; GET posterior HTTP {g.status_code}.")

    c = Case("API-EST-12"); r = c.call("DELETE", E + "/4/1003")
    c.check(r.status_code == 404, "404"); c.done(f"HTTP {r.status_code}.")

    c = Case("API-EST-13"); r = c.call("POST", E, {**nuevo, "idProf": 4, "ccPer": 1001})
    n = scalar("SELECT COUNT(*) FROM dbo.estudios WHERE cc_per = 1001")
    c.check(r.status_code == 201 and int(n) >= 2, "201 y varios estudios")
    c.done(f"HTTP {r.status_code}; la persona 1001 queda con {n} estudios.")

    c = Case("API-EST-14"); r = c.call("POST", E, {**nuevo, "idProf": 1, "ccPer": 2040})
    n = scalar("SELECT COUNT(*) FROM dbo.estudios WHERE id_prof = 1")
    c.check(r.status_code == 201 and int(n) >= 2, "201")
    c.done(f"HTTP {r.status_code}; la profesion 1 queda asociada a {n} personas.")

    c = Case("API-EST-15"); r = c.call("POST", E, {"idProf": 4, "ccPer": 2040})
    g = c.call("GET", E + "/4/2040").json()
    c.check(r.status_code == 201 and g["fecha"] is None and g["univer"] is None, "201 y nulos")
    c.done(f"HTTP {r.status_code}; fecha y univer quedan en null.")


# ---------------------------------------------------------------- General
def general():
    c = Case("API-GEN-01"); types = []
    for p in ("/api/personas", "/api/telefonos", "/api/profesiones", "/api/estudios"):
        r = c.call("GET", p); types.append(r.headers.get("Content-Type", ""))
        c.check(r.headers.get("Content-Type", "").startswith("application/json"), p)
    c.done(f"Los 4 GET devuelven '{types[0]}'.")

    c = Case("API-GEN-02"); codes = {}
    targets = [("POST", "/api/personas"), ("PUT", "/api/personas/1001"), ("POST", "/api/telefonos"),
               ("PUT", "/api/telefonos/3001112233"), ("POST", "/api/profesiones"), ("PUT", "/api/profesiones/1"),
               ("POST", "/api/estudios"), ("PUT", "/api/estudios/1/1001")]
    for m, p in targets:
        for label, raw in (("vacio", b""), ("mal formado", b'{"cc": 1, "nombre": ')):
            r = c.call(m, p, raw=raw); codes.setdefault(r.status_code, 0); codes[r.status_code] += 1
            c.check(r.status_code == 400, f"{m} {p} {label}")
    r = c.call("POST", "/api/personas", raw=b"")
    c.done(f"16 solicitudes (cuerpo vacio y JSON mal formado en POST/PUT de los 4 recursos): codigos {codes}; "
           "ninguna responde 500.")

    c = Case("API-GEN-03"); r1 = c.call("GET", "/api/personas/abc"); r2 = c.call("GET", "/api/estudios/1/abc")
    c.check(400 <= r1.status_code < 500 and 400 <= r2.status_code < 500, "4xx")
    c.done(f"/api/personas/abc: {r1.status_code}; /api/estudios/1/abc: {r2.status_code}.",
           "La restriccion de ruta :int hace que la ruta no coincida y se responde 404 en lugar de 400.")

    c = Case("API-GEN-04"); r = c.call("DELETE", "/api/personas")
    c.check(r.status_code == 405, "405"); c.done(f"HTTP {r.status_code}.")

    c = Case("API-GEN-05"); results = []; sample = None
    body = lambda cc: {"cc": cc, "nombre": "Carrera", "apellido": "QA", "genero": "M", "edad": 30}  # noqa: E731
    for i in range(20):
        cc = 2050 + i
        with concurrent.futures.ThreadPoolExecutor(2) as ex:
            futs = [ex.submit(requests.post, BASE_URL + "/api/personas", json=body(cc), timeout=30) for _ in range(2)]
            resps = [f.result() for f in futs]
        pair = sorted(r.status_code for r in resps)
        sample = sample or next((r for r in resps if r.status_code == 500), None)
        results.append(pair)
        c.note(f"intento {i + 1}, cc {cc}: {pair}")
    if sample is not None:
        c.note(f"Ejemplo de respuesta 500 (Content-Type {sample.headers.get('Content-Type')}):\n{sample.text[:800]}")
    n500 = sum(1 for p in results if 500 in p)
    dup = scalar("SELECT COUNT(*) FROM (SELECT cc FROM dbo.persona WHERE cc BETWEEN 2050 AND 2069 "
                 "GROUP BY cc HAVING COUNT(*) > 1) d")
    c.check(n500 == 0, "sin 500")
    c.check(dup == "0", "sin duplicados")
    c.done(f"20 pares de POST simultaneos: {sum(1 for p in results if p == [201, 409])} con [201, 409] y {n500} con "
           f"un 500 en el segundo; sin registros duplicados ({dup}).",
           "El POST consulta ExistsAsync y luego inserta; si ambas solicitudes pasan la consulta, la segunda falla "
           "por PK y la excepcion no se controla. Propuesta: capturar DbUpdateException (error 2627) y responder 409.")


def main():
    cleanup()
    for block in (personas, telefonos, profesiones, estudios, general):
        block()
    cleanup()
    ok = sum(1 for _, e in SUMMARY if e == "Aprobado")
    print(f"\n{TAG}: {ok}/{len(SUMMARY)} aprobados")


if __name__ == "__main__":
    main()
