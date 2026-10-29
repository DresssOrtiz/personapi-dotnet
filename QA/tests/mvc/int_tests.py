"""Casos INT-01 a INT-08 y BK-09: integracion entre vistas MVC, API REST y SQL Server.

Uso: python QA/tests/mvc/int_tests.py
Requiere la rama feature/frontend-mvc en ejecucion en el puerto 5025 (dotnet run,
entorno Development como indica el README) y el contenedor persona-sql.
INT-07 reinicia la aplicacion; BK-09 e INT-08 detienen y vuelven a iniciar el
contenedor de SQL Server.
Claves de prueba: personas 2401-2499, telefonos 39900040xx, profesiones 991-999.
"""
import os
import re
import signal
import subprocess
import sys
import time
from html import unescape

import requests
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib import BASE_URL, EVID, REPO_FRONTEND, RESULTS, SQL_CONTAINER, record, scalar, sqlcmd, write_evidence  # noqa: E402

PR_PROJ = os.path.join(REPO_FRONTEND, "personapi-dotnet")
DOTNET = os.environ.get("DOTNET6", os.path.expanduser("~/.dotnet6/dotnet"))
ENV = {**os.environ, "DOTNET_ROOT": os.path.dirname(DOTNET), "DOTNET_CLI_TELEMETRY_OPTOUT": "1"}
API = BASE_URL + "/api"


def cleanup():
    sqlcmd("DELETE FROM dbo.estudios WHERE cc_per BETWEEN 2401 AND 2499 OR id_prof BETWEEN 991 AND 999; "
           "DELETE FROM dbo.telefono WHERE num LIKE '39900040%' OR duenio BETWEEN 2401 AND 2499; "
           "DELETE FROM dbo.persona WHERE cc BETWEEN 2401 AND 2499; "
           "DELETE FROM dbo.profesion WHERE id BETWEEN 991 AND 999", db="persona_db")


def form(page, ctrl, data, url=None):
    page.goto(BASE_URL + (url or f"/{ctrl}/Create"))
    for k, v in data.items():
        loc = page.locator(f"form.record-form [name='{k}']:not([type='hidden'])").first
        if not loc.count():
            continue
        if loc.evaluate("e => e.tagName") == "SELECT":
            loc.select_option(v)
        else:
            loc.fill(v)
    page.locator("form.record-form button[type='submit']").click()
    page.wait_for_load_state()
    return " ".join(page.locator(".validation-summary-errors, .field-validation-error").all_inner_texts()).strip()


def delete_view(page, url):
    page.goto(BASE_URL + url)
    page.locator("button", has_text="Sí, eliminar").click()
    page.wait_for_load_state()
    return " ".join(page.locator(".validation-summary-errors").all_inner_texts()).strip()


def listed(page, ctrl, text):
    page.goto(BASE_URL + f"/{ctrl}")
    return page.locator("tbody tr", has_text=text).count() > 0


def wait_http(url, seconds=60):
    for _ in range(seconds):
        try:
            return requests.get(url, timeout=5)
        except requests.ConnectionError:
            time.sleep(1)
    return None


def restart_app():
    out = subprocess.run("lsof -ti tcp:5025 -sTCP:LISTEN", shell=True, capture_output=True, text=True).stdout
    for pid in out.split():
        os.kill(int(pid), signal.SIGTERM)
    time.sleep(3)
    down = wait_http(BASE_URL + "/", 2) is None
    log = open(os.path.join(RESULTS, "app-frontend-restart.log"), "w")
    subprocess.Popen([DOTNET, "run", "--urls", "http://localhost:5025"], cwd=PR_PROJ, env=ENV, stdout=log,
                     stderr=subprocess.STDOUT, start_new_session=True)
    wait_http(BASE_URL + "/Personas")
    return down


def main():
    cleanup()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})

        # INT-01 vista -> API
        form(page, "Personas", {"Cc": "2401", "Nombre": "Desde", "Apellido": "Vista", "Genero": "F", "Edad": "31"})
        g = requests.get(API + "/personas/2401", timeout=10)
        ev = write_evidence("INT-01", f"Creada en /Personas/Create: 2401 Desde Vista F 31\nGET /api/personas/2401 -> "
                                      f"{g.status_code} {g.text}")
        ok = g.status_code == 200 and g.json() == {"cc": 2401, "nombre": "Desde", "apellido": "Vista", "genero": "F",
                                                   "edad": 31}
        record("INT-01", "Aprobado" if ok else "Fallido",
               f"Persona creada en la vista; GET /api/personas/2401 responde {g.status_code} con los mismos datos.", ev)

        # INT-02 API -> vista
        c = requests.post(API + "/personas", json={"cc": 2402, "nombre": "Desde", "apellido": "Api", "genero": "M",
                                                   "edad": 45}, timeout=10).status_code
        seen = listed(page, "Personas", "2402")
        shot = "EV-INT-02.png"
        page.screenshot(path=os.path.join(EVID, shot), full_page=True)
        ev = write_evidence("INT-02", f"POST /api/personas 2402 -> {c}\nListado /Personas contiene 2402: {seen}")
        record("INT-02", "Aprobado" if c == 201 and seen else "Fallido",
               f"POST {c}; la persona 2402 aparece en el listado de la vista.", f"{shot}, {ev}")

        # INT-03 edicion en ambos sentidos
        form(page, "Personas", {"Nombre": "EditadaVista"}, url="/Personas/Edit?cc=2401")
        a = requests.get(API + "/personas/2401", timeout=10).json()["nombre"]
        p = requests.put(API + "/personas/2401", json={"cc": 2401, "nombre": "EditadaApi", "apellido": "Vista",
                                                       "genero": "F", "edad": 31}, timeout=10).status_code
        page.goto(BASE_URL + "/Personas/Details?cc=2401")
        v = "EditadaApi" in page.locator("main").inner_text()
        ev = write_evidence("INT-03", f"Edicion en vista -> API muestra nombre '{a}'\nPUT /api/personas/2401 -> {p}\n"
                                      f"Detalle en la vista muestra 'EditadaApi': {v}")
        record("INT-03", "Aprobado" if a == "EditadaVista" and p == 204 and v else "Fallido",
               f"La edicion en la vista se ve en la API ('{a}'); el PUT ({p}) se ve en el detalle de la vista.", ev)

        # INT-04 eliminacion en ambos sentidos
        msg = delete_view(page, "/Personas/Delete?cc=2401")
        g1 = requests.get(API + "/personas/2401", timeout=10).status_code
        d = requests.delete(API + "/personas/2402", timeout=10).status_code
        v = listed(page, "Personas", "2402")
        ev = write_evidence("INT-04", f"Eliminada 2401 en la vista ({msg or 'sin error'}) -> GET API {g1}\n"
                                      f"DELETE /api/personas/2402 -> {d}; aparece en el listado: {v}")
        record("INT-04", "Aprobado" if g1 == 404 and d == 204 and not v else "Fallido",
               f"Eliminada en la vista: la API responde {g1}. Eliminada con la API ({d}): desaparece del listado.", ev)

        # INT-05 reglas coherentes
        rows = []
        m_dup = form(page, "Personas", {"Cc": "1001", "Nombre": "D", "Apellido": "D", "Genero": "M"})
        a_dup = requests.post(API + "/personas", json={"cc": 1001, "nombre": "D", "apellido": "D", "genero": "M"},
                              timeout=10).status_code
        rows.append(("clave duplicada (persona 1001)", m_dup, a_dup))
        s = requests.Session()
        html = s.get(BASE_URL + "/Telefonos/Create", timeout=10).text
        tok = re.search(r'name="__RequestVerificationToken" type="hidden" value="([^"]+)"', html).group(1)
        r = s.post(BASE_URL + "/Telefonos/Create", data={"Num": "3990004005", "Oper": "Claro", "Duenio": "999999",
                                                         "__RequestVerificationToken": tok}, timeout=10)
        m_ref = " ".join(unescape(x) for x in re.findall(r'field-validation-error[^>]*>(.*?)</span>', r.text))
        a_ref = requests.post(API + "/telefonos", json={"num": "3990004005", "oper": "Claro", "duenio": 999999},
                              timeout=10).status_code
        rows.append(("referencia inexistente (duenio 999999)", m_ref, a_ref))
        m_dep = delete_view(page, "/Profesiones/Delete/1")
        a_dep = requests.delete(API + "/profesiones/1", timeout=10).status_code
        rows.append(("eliminacion con dependientes (profesion 1)", m_dep, a_dep))
        ev = write_evidence("INT-05", "\n".join(f"{n}: vista '{m}' | API {c}" for n, m, c in rows))
        ok = all(m for _, m, _ in rows) and [c for *_, c in rows] == [409, 400, 409]
        record("INT-05", "Aprobado" if ok else "Fallido",
               "Ambos canales rechazan los 3 casos: duplicado (vista con mensaje, API 409), referencia inexistente "
               "(vista con mensaje, API 400) y eliminacion con dependientes (vista con mensaje, API 409).", ev)

        # INT-06 flujo completo por la vista
        steps = []
        steps.append(("crear persona", form(page, "Personas", {"Cc": "2410", "Nombre": "Flujo", "Apellido": "Completo",
                                                               "Genero": "M", "Edad": "29"})))
        steps.append(("crear telefono", form(page, "Telefonos", {"Num": "3990004010", "Oper": "WOM", "Duenio": "2410"})))
        steps.append(("crear profesion", form(page, "Profesiones", {"Id": "991", "Nom": "Profesion Flujo", "Des": "E2E"})))
        steps.append(("crear estudio", form(page, "Estudios", {"IdProf": "991", "CcPer": "2410", "Fecha": "2025-07-01",
                                                               "Univer": "Universidad Flujo"})))
        page.goto(BASE_URL + "/Estudios")
        page.screenshot(path=os.path.join(EVID, "EV-INT-06.png"), full_page=True)
        consult = [requests.get(API + u, timeout=10).status_code
                   for u in ("/personas/2410", "/telefonos/3990004010", "/profesiones/991", "/estudios/991/2410")]
        steps.append(("eliminar estudio", delete_view(page, "/Estudios/Delete?idProf=991&ccPer=2410")))
        steps.append(("eliminar telefono", delete_view(page, "/Telefonos/Delete?num=3990004010")))
        steps.append(("eliminar profesion", delete_view(page, "/Profesiones/Delete/991")))
        steps.append(("eliminar persona", delete_view(page, "/Personas/Delete?cc=2410")))
        left = scalar("SELECT (SELECT COUNT(*) FROM dbo.persona WHERE cc = 2410) + (SELECT COUNT(*) FROM dbo.telefono "
                      "WHERE num = '3990004010') + (SELECT COUNT(*) FROM dbo.profesion WHERE id = 991) + "
                      "(SELECT COUNT(*) FROM dbo.estudios WHERE id_prof = 991)")
        ev = write_evidence("INT-06", "\n".join(f"{n}: {m or 'sin errores'}" for n, m in steps) +
                            f"\nConsulta por la API: {consult}\nRegistros restantes: {left}")
        ok = all(not m for _, m in steps) and consult == [200] * 4 and left == "0"
        record("INT-06", "Aprobado" if ok else "Fallido",
               "Persona, telefono, profesion y estudio creados desde las vistas, consultados por la API (4 x 200) y "
               "eliminados en orden inverso sin errores; no quedan registros.", f"EV-INT-06.png, {ev}")

        # INT-07 persistencia tras reiniciar
        form(page, "Personas", {"Cc": "2420", "Nombre": "Persiste", "Apellido": "Vista", "Genero": "F"})
        requests.post(API + "/personas", json={"cc": 2421, "nombre": "Persiste", "apellido": "Api", "genero": "M"},
                      timeout=10)
        browser.close()
    down = restart_app()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        both = listed(page, "Personas", "2420") and listed(page, "Personas", "2421")
        ev = write_evidence("INT-07", f"Aplicacion detenida (puerto libre: {down}) y reiniciada con dotnet run\n"
                                      f"Listado contiene 2420 (vista) y 2421 (API): {both}")
        record("INT-07", "Aprobado" if down and both else "Fallido",
               "Tras detener y reiniciar la aplicacion, los registros creados desde la vista (2420) y la API (2421) "
               "siguen en el listado.", ev)

        # BK-09 e INT-08 caida de SQL Server
        subprocess.run(["docker", "stop", SQL_CONTAINER], capture_output=True)
        t0 = time.time()
        resp = page.goto(BASE_URL + "/Personas")
        view_txt = page.locator("main").inner_text()
        page.screenshot(path=os.path.join(EVID, "EV-BK-09-vista.png"), full_page=True)
        api_r = requests.get(API + "/personas", timeout=60)
        api_txt = api_r.text
        elapsed = time.time() - t0
        leaks = [w for w in ("Password", "User Id", "Persona_Lab1", "SqlException", "   at ") if w in api_txt]
        view_leaks = [w for w in ("Password", "SqlException", "   at ") if w in page.content()]
        subprocess.run(["docker", "start", SQL_CONTAINER], capture_output=True)
        for _ in range(60):
            if sqlcmd("SELECT 1")[0] == 0 and "Msg" not in sqlcmd("SELECT COUNT(*) FROM persona_db.dbo.persona")[1]:
                break
            time.sleep(2)
        time.sleep(3)
        resp2 = page.goto(BASE_URL + "/Personas")
        rows_after = page.locator("tbody tr").count()
        api2 = requests.get(API + "/personas", timeout=30).status_code
        page.screenshot(path=os.path.join(EVID, "EV-INT-08-recuperacion.png"), full_page=True)
        ev = write_evidence("BK-09", f"docker stop {SQL_CONTAINER}\nGET /Personas -> {resp.status}\n{view_txt[:400]}\n"
                                     f"Detalles internos en la vista: {view_leaks}\n\nGET /api/personas -> "
                                     f"{api_r.status_code} {api_r.headers.get('Content-Type')}\n{api_txt[:1500]}\n"
                                     f"Detalles internos en la API: {leaks}\nTiempo de ambas solicitudes: {elapsed:.1f} s")
        record("BK-09", "Fallido" if leaks or view_leaks else "Aprobado",
               f"La vista responde {resp.status} con la pagina 'No se pudo acceder a los registros' sin detalles. "
               f"La API responde {api_r.status_code} ({api_r.headers.get('Content-Type')}) " + (
                   f"con la traza de la excepcion ({', '.join(leaks)}); no expone credenciales." if leaks else
                   "con un mensaje controlado, sin traza ni credenciales."),
               f"EV-BK-09-vista.png, {ev}",
               "Ejecutado como indica el README (dotnet run, entorno Development, pagina de excepciones del "
               "desarrollador). En Production la API devolveria la vista HTML /Home/Error. Propuesta: manejar el error "
               "en la API con ProblemDetails (503) en todos los entornos.")
        ev = write_evidence("INT-08", f"Durante la caida: vista {resp.status}, API {api_r.status_code}\n"
                                      f"docker start {SQL_CONTAINER}\nSin reiniciar la aplicacion: vista {resp2.status} "
                                      f"con {rows_after} filas, API {api2}")
        record("INT-08", "Aprobado" if resp.status == 503 and resp2.status == 200 and api2 == 200 else "Fallido",
               f"Durante la caida la vista muestra un error controlado ({resp.status}); al volver SQL Server la vista "
               f"({resp2.status}, {rows_after} filas) y la API ({api2}) funcionan sin reiniciar la aplicacion.",
               f"EV-BK-09-vista.png, EV-INT-08-recuperacion.png, {ev}",
               f"La API durante la caida responde {api_r.status_code} " + (
                   "con la traza (ver BK-09)." if leaks else "con un mensaje controlado (ver BK-09)."))
        browser.close()
    cleanup()


if __name__ == "__main__":
    main()
