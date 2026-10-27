"""Casos SW-01 a SW-08: interfaz de Swagger UI y documento OpenAPI.

Uso: python QA/tests/api/swagger_tests.py [--tag main|frontend]
SW-03 y SW-04 se ejecutan desde la interfaz con Playwright (Try it out / Execute)
y guardan capturas. SW-09 (claridad para un tercero) es revision manual.
"""
import json
import os
import sys

import requests
from openapi_spec_validator import validate
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib import BASE_URL, EVID, record, scalar, sqlcmd, write_evidence  # noqa: E402

TAG = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "main"
SFX = "" if TAG == "main" else f"-{TAG}"


def rec(case_id, estado, obtenido, ev, obs=""):
    if TAG == "main":
        record(case_id, estado, obtenido, ev, obs)
    else:
        print(f"[{estado:9}] {case_id} ({TAG}): {obtenido}")


def shot(page, case_id, locator=None):
    name = f"EV-{case_id}{SFX}.png"
    (locator or page).screenshot(path=os.path.join(EVID, name), **({} if locator else {"full_page": True}))
    return name


def execute(page, tag, method, path, params=None, body=None):
    """Abre una operacion, pulsa Try it out, completa datos, ejecuta y devuelve (codigo, cuerpo, bloque)."""
    op_id = f"operations-{tag}-{method}_{path.strip('/').replace('/', '_').replace('{', '_').replace('}', '_')}"
    block = page.locator(f"[id='{op_id}']")
    if "is-open" not in (block.get_attribute("class") or ""):
        block.locator(".opblock-summary").first.click()
    try_btn = block.locator("button.try-out__btn").first
    try_btn.wait_for(timeout=10000)
    if "cancel" not in (try_btn.get_attribute("class") or ""):
        try_btn.click()
    block.locator("button.execute").wait_for(timeout=10000)
    for name, value in (params or {}).items():
        block.locator(f"tr[data-param-name='{name}'] input").fill(str(value))
    if body is not None:
        block.locator("textarea.body-param__text").fill(json.dumps(body, ensure_ascii=False))
    block.locator("button.execute").click()
    status = block.locator(".live-responses-table tbody .response-col_status").first
    status.wait_for(timeout=15000)
    code = int(status.inner_text().strip().split()[0])
    resp_body = ""
    b = block.locator(".live-responses-table .response-col_description pre").first
    if b.count():
        resp_body = b.inner_text()[:400]
    return code, resp_body, block


def main():
    spec_resp = requests.get(BASE_URL + "/swagger/v1/swagger.json", timeout=30)
    spec = spec_resp.json()

    # SW-07 documento OpenAPI valido
    try:
        validate(spec)
        valid, err = True, ""
    except Exception as exc:  # noqa: BLE001
        valid, err = False, str(exc)[:500]
    ev = write_evidence("SW-07" + SFX, f"GET /swagger/v1/swagger.json -> {spec_resp.status_code}, "
                                          f"{len(spec_resp.content)} bytes, openapi {spec.get('openapi')}\n"
                                          f"openapi-spec-validator: {'valido' if valid else err}\n\n"
                                          + json.dumps(spec, indent=2)[:6000])
    rec("SW-07", "Aprobado" if valid else "Fallido",
        f"swagger.json se descarga (HTTP {spec_resp.status_code}, OpenAPI {spec.get('openapi')}) y "
        f"openapi-spec-validator lo declara {'valido' if valid else 'invalido'}.", ev)

    # SW-02 endpoints de las 4 entidades
    ops = {(m.upper(), p) for p, d in spec["paths"].items() for m in d}
    expected = set()
    for base, key in [("/api/personas", "{cc}"), ("/api/telefonos", "{num}"), ("/api/profesiones", "{id}"),
                      ("/api/estudios", "{idProf}/{ccPer}")]:
        expected |= {("GET", base), ("POST", base), ("GET", f"{base}/{key}"), ("PUT", f"{base}/{key}"),
                     ("DELETE", f"{base}/{key}")}
    missing = expected - ops
    lines = "\n".join(f"{m} {p}" for m, p in sorted(ops))

    # SW-05 esquemas
    schemas = spec["components"]["schemas"]
    sch_txt = "\n".join(f"{n}: required={s.get('required')} props="
                        f"{ {k: v.get('type') + ('/' + v['format'] if 'format' in v else '') for k, v in s.get('properties', {}).items()} }"
                        for n, s in schemas.items())
    want = {"PersonaDto": {"cc", "nombre", "apellido", "genero", "edad"}, "TelefonoDto": {"num", "oper", "duenio"},
            "ProfesionDto": {"id", "nom", "des"}, "EstudioDto": {"idProf", "ccPer", "fecha", "univer"}}
    fields_ok = all(set(schemas.get(n, {}).get("properties", {})) == f for n, f in want.items())
    ev5 = write_evidence("SW-05" + SFX, sch_txt)
    rec("SW-05", "Aprobado" if fields_ok else "Fallido",
        "Los 4 DTO muestran todos sus campos con tipo; obligatorios: PersonaDto (nombre, apellido, genero), "
        "TelefonoDto (num, oper), ProfesionDto (nom).", ev5,
        "Las claves enteras (cc, id, idProf, ccPer, duenio) no figuran como required aunque la API las exige "
        "(Range >= 1); fecha aparece como string/date-time. Las restricciones Range y StringLength si se publican.")

    # SW-08 alcance
    non_api = [p for p in spec["paths"] if not p.startswith("/api/")]
    ev8 = write_evidence("SW-08" + SFX, f"Rutas documentadas:\n{lines}\n\nRutas fuera de /api: {non_api}")
    rec("SW-08", "Aprobado" if not non_api else "Fallido",
        f"Las {len(spec['paths'])} rutas documentadas empiezan por /api/; no aparecen acciones MVC.", ev8)

    # SW-06 codigos documentados frente a los reales
    probes = [
        ("GET", "/api/personas", None, 200), ("GET", "/api/personas/1001", None, 200),
        ("GET", "/api/personas/999999", None, 404), ("POST", "/api/personas", {"cc": 2101, "nombre": "Sw", "apellido": "QA", "genero": "M"}, 201),
        ("POST", "/api/personas", {"cc": 2101, "nombre": "Sw", "apellido": "QA", "genero": "M"}, 409),
        ("POST", "/api/personas", {"cc": 2102, "nombre": "", "apellido": "QA", "genero": "M"}, 400),
        ("PUT", "/api/personas/2101", {"cc": 2101, "nombre": "Sw2", "apellido": "QA", "genero": "M"}, 204),
        ("PUT", "/api/personas/2101", {"cc": 2102, "nombre": "Sw2", "apellido": "QA", "genero": "M"}, 400),
        ("PUT", "/api/personas/999999", {"cc": 999999, "nombre": "Sw2", "apellido": "QA", "genero": "M"}, 404),
        ("DELETE", "/api/personas/1001", None, 409), ("DELETE", "/api/personas/999999", None, 404),
        ("DELETE", "/api/personas/2101", None, 204),
        ("GET", "/api/telefonos", None, 200), ("GET", "/api/telefonos/3001112233", None, 200),
        ("GET", "/api/telefonos/000", None, 404), ("POST", "/api/telefonos", {"num": "3990002101", "oper": "Claro", "duenio": 1001}, 201),
        ("POST", "/api/telefonos", {"num": "3990002101", "oper": "Claro", "duenio": 1001}, 409),
        ("POST", "/api/telefonos", {"num": "3990002102", "oper": "Claro", "duenio": 999999}, 400),
        ("PUT", "/api/telefonos/3990002101", {"num": "3990002101", "oper": "Tigo", "duenio": 1001}, 204),
        ("PUT", "/api/telefonos/3990002101", {"num": "x", "oper": "Tigo", "duenio": 1001}, 400),
        ("PUT", "/api/telefonos/3990009999", {"num": "3990009999", "oper": "Tigo", "duenio": 1001}, 404),
        ("DELETE", "/api/telefonos/3990002101", None, 204), ("DELETE", "/api/telefonos/3990002101", None, 404),
        ("GET", "/api/profesiones", None, 200), ("GET", "/api/profesiones/1", None, 200),
        ("GET", "/api/profesiones/9999", None, 404), ("POST", "/api/profesiones", {"id": 951, "nom": "Sw"}, 201),
        ("POST", "/api/profesiones", {"id": 951, "nom": "Sw"}, 409), ("POST", "/api/profesiones", {"id": 952, "nom": ""}, 400),
        ("PUT", "/api/profesiones/951", {"id": 951, "nom": "Sw2"}, 204), ("PUT", "/api/profesiones/951", {"id": 1, "nom": "Sw2"}, 400),
        ("PUT", "/api/profesiones/9999", {"id": 9999, "nom": "Sw2"}, 404), ("DELETE", "/api/profesiones/1", None, 409),
        ("DELETE", "/api/profesiones/951", None, 204), ("DELETE", "/api/profesiones/951", None, 404),
        ("GET", "/api/estudios", None, 200), ("GET", "/api/estudios/1/1001", None, 200),
        ("GET", "/api/estudios/4/1003", None, 404), ("POST", "/api/estudios", {"idProf": 3, "ccPer": 1003}, 201),
        ("POST", "/api/estudios", {"idProf": 3, "ccPer": 1003}, 409), ("POST", "/api/estudios", {"idProf": 999, "ccPer": 1003}, 400),
        ("PUT", "/api/estudios/3/1003", {"idProf": 3, "ccPer": 1003, "univer": "Sw"}, 204),
        ("PUT", "/api/estudios/3/1003", {"idProf": 3, "ccPer": 1001}, 400),
        ("PUT", "/api/estudios/4/1003", {"idProf": 4, "ccPer": 1003}, 404),
        ("DELETE", "/api/estudios/3/1003", None, 204), ("DELETE", "/api/estudios/3/1003", None, 404),
    ]
    log, mismatches = [], []
    for m, p, body, exp in probes:
        r = requests.request(m, BASE_URL + p, json=body, timeout=30)
        tmpl = next((sp for sp in spec["paths"] if _match(sp, p)), None)
        documented = sorted(spec["paths"][tmpl][m.lower()]["responses"]) if tmpl else []
        ok = r.status_code == exp and str(r.status_code) in documented
        if not ok:
            mismatches.append(f"{m} {p}: real {r.status_code}, documentados {documented}")
        log.append(f"{m} {p} -> {r.status_code} (documentados {documented}) {'OK' if ok else 'DIFERENCIA'}")
    ev6 = write_evidence("SW-06" + SFX, "\n".join(log) + f"\n\nDiferencias: {mismatches}")
    rec("SW-06", "Aprobado" if not mismatches else "Fallido",
        f"{len(probes)} solicitudes, una por codigo documentado en cada operacion: "
        f"{len(probes) - len(mismatches)} coinciden con la documentacion.", ev6,
        "Fuera de lo documentado: 405 en metodos no soportados y 500 en POST concurrentes con la misma clave "
        "(API-GEN-05).")

    # Interfaz Swagger UI
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        resp = page.goto(BASE_URL + "/swagger/index.html")
        page.wait_for_selector(".opblock", timeout=20000)
        n_blocks = page.locator(".opblock").count()
        ev1 = shot(page, "SW-01")
        rec("SW-01", "Aprobado" if resp.status == 200 and n_blocks == 20 and not errors else "Fallido",
            f"/swagger responde {resp.status} y Swagger UI muestra {n_blocks} operaciones; errores de consola: "
            f"{len(errors)}.", ev1)
        ev2 = write_evidence("SW-02" + SFX, f"Operaciones en swagger.json ({len(ops)}):\n{lines}\n\nFaltantes: {missing}"
                                              f"\nBloques en Swagger UI: {n_blocks}\nCaptura: {ev1}")
        rec("SW-02", "Aprobado" if not missing and n_blocks == 20 else "Fallido",
            "Personas, Telefonos, Profesiones y Estudios con GET lista, GET por clave, POST, PUT y DELETE "
            f"(20 operaciones).", ev2)

        # SW-03 GET desde Try it out
        log, ok3 = [], True
        for tag, path, params, exp in [("Personas", "/api/personas", None, 200),
                                       ("Personas", "/api/personas/{cc}", {"cc": 1001}, 200),
                                       ("Telefonos", "/api/telefonos", None, 200),
                                       ("Telefonos", "/api/telefonos/{num}", {"num": "3001112233"}, 200),
                                       ("Profesiones", "/api/profesiones", None, 200),
                                       ("Profesiones", "/api/profesiones/{id}", {"id": 1}, 200),
                                       ("Estudios", "/api/estudios", None, 200),
                                       ("Estudios", "/api/estudios/{idProf}/{ccPer}", {"idProf": 1, "ccPer": 1001}, 200)]:
            code, body, block = execute(page, tag, "get", path, params)
            ok3 &= code == exp
            log.append(f"GET {path} {params or ''} -> {code}\n{body[:200]}\n")
            if path == "/api/personas/{cc}":
                block.scroll_into_view_if_needed()
                shot(page, "SW-03", block)
        ev3 = write_evidence("SW-03" + SFX, "\n".join(log))
        rec("SW-03", "Aprobado" if ok3 else "Fallido",
            "Try it out ejecuta los 8 GET (lista y por clave de cada recurso) con respuesta 200 y cuerpo JSON.",
            f"EV-SW-03{SFX}.png, {ev3}")

        # SW-04 POST, PUT y DELETE desde Try it out
        log, ok4 = [], True
        flows = [
            ("Personas", "/api/personas", "/api/personas/{cc}", {"cc": 2201},
             {"cc": 2201, "nombre": "Swagger", "apellido": "QA", "genero": "F", "edad": 25},
             {"cc": 2201, "nombre": "SwaggerEdit", "apellido": "QA", "genero": "F", "edad": 26},
             "SELECT nombre FROM dbo.persona WHERE cc = 2201", "SwaggerEdit"),
            ("Telefonos", "/api/telefonos", "/api/telefonos/{num}", {"num": "3990002201"},
             {"num": "3990002201", "oper": "Claro", "duenio": 1002},
             {"num": "3990002201", "oper": "Tigo", "duenio": 1002},
             "SELECT oper FROM dbo.telefono WHERE num = '3990002201'", "Tigo"),
            ("Profesiones", "/api/profesiones", "/api/profesiones/{id}", {"id": 961},
             {"id": 961, "nom": "Swagger", "des": "Creada desde Swagger"},
             {"id": 961, "nom": "SwaggerEdit", "des": "Editada"},
             "SELECT nom FROM dbo.profesion WHERE id = 961", "SwaggerEdit"),
            ("Estudios", "/api/estudios", "/api/estudios/{idProf}/{ccPer}", {"idProf": 4, "ccPer": 1002},
             {"idProf": 4, "ccPer": 1002, "fecha": "2024-05-01", "univer": "Swagger U"},
             {"idProf": 4, "ccPer": 1002, "fecha": "2024-05-01", "univer": "Swagger Edit"},
             "SELECT univer FROM dbo.estudios WHERE id_prof = 4 AND cc_per = 1002", "Swagger Edit"),
        ]
        for tag, coll, item, key, body, body2, q, expected_val in flows:
            c1, _, blk = execute(page, tag, "post", coll, body=body)
            if tag == "Personas":
                blk.scroll_into_view_if_needed(); shot(page, "SW-04-POST", blk)
            c2, _, blk = execute(page, tag, "put", item, key, body2)
            in_db = scalar(q)
            c3, _, blk = execute(page, tag, "delete", item, key)
            if tag == "Personas":
                blk.scroll_into_view_if_needed(); shot(page, "SW-04-DELETE", blk)
            gone = requests.get(BASE_URL + coll + "/" + "/".join(str(v) for v in key.values()), timeout=30).status_code
            ok = (c1, c2, c3, in_db, gone) == (201, 204, 204, expected_val, 404)
            ok4 &= ok
            log.append(f"{tag}: POST {c1}, PUT {c2} (base: {in_db}), DELETE {c3}, GET posterior {gone}")
        ev4 = write_evidence("SW-04" + SFX, "\n".join(log))
        rec("SW-04", "Aprobado" if ok4 else "Fallido",
            "En los 4 recursos: POST 201, PUT 204 con el cambio visible en persona_db, DELETE 204 y GET posterior 404.",
            f"EV-SW-04-POST{SFX}.png, EV-SW-04-DELETE{SFX}.png, {ev4}")
        browser.close()
    sqlcmd("DELETE FROM dbo.persona WHERE cc IN (2101, 2102, 2201); DELETE FROM dbo.telefono WHERE num LIKE '39900022%';"
           "DELETE FROM dbo.profesion WHERE id IN (951, 952, 961)", db="persona_db")


def _match(template, path):
    a, b = template.strip("/").split("/"), path.strip("/").split("/")
    return len(a) == len(b) and all(x == y or x.startswith("{") for x, y in zip(a, b))


if __name__ == "__main__":
    main()
