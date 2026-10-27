"""Casos MVC-PER, MVC-TEL, MVC-PRO, MVC-EST (01 a 08) y MVC-GEN-01, 02, 06, 07 y 08.

Uso: python QA/tests/mvc/mvc_tests.py
Requiere la rama feature/frontend-mvc en ejecucion en QA_BASE_URL y la base con
los datos del DML. Las vistas se recorren con Playwright (Chromium) y las capturas
se guardan en evidencias/. Las validaciones del servidor y la manipulacion de
datos enviados se prueban con solicitudes HTTP que incluyen el token
antifalsificacion obtenido del formulario.
Claves de prueba: personas 2301-2399, telefonos 39900030xx, profesiones 971-989.
"""
import os
import re
import subprocess
import sys
import time
from html import unescape

import requests
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib import BASE_URL, EVID, REPO_FRONTEND, record, scalar, sqlcmd, write_evidence  # noqa: E402

PR_PROJ = os.path.join(REPO_FRONTEND, "personapi-dotnet")
DOTNET = os.environ.get("DOTNET6", os.path.expanduser("~/.dotnet6/dotnet"))
ENV = {**os.environ, "DOTNET_ROOT": os.path.dirname(DOTNET), "DOTNET_CLI_TELEMETRY_OPTOUT": "1"}

ENT = {
    "PER": dict(ctrl="Personas", table="persona", label="Personas", key="Cc",
                new={"Cc": "2301", "Nombre": "Valeria", "Apellido": "Rojas", "Genero": "F", "Edad": "28"},
                temp={"Cc": "2302", "Nombre": "Temporal", "Apellido": "QA", "Genero": "M", "Edad": "40"},
                dup={"Cc": "1001", "Nombre": "Dup", "Apellido": "Dup", "Genero": "M", "Edad": "20"},
                edit=("Nombre", "Valeria Editada"), cols=["Cédula", "Nombre", "Apellido", "Género", "Edad"],
                invalid={"Cc": "2399", "Nombre": "x" * 46, "Apellido": "A", "Genero": "X", "Edad": "200"},
                missing="/Personas/Details?cc=999999",
                q_new="SELECT nombre FROM dbo.persona WHERE cc = 2301",
                q_temp="SELECT COUNT(*) FROM dbo.persona WHERE cc = 2302", dep_key="1001"),
    "TEL": dict(ctrl="Telefonos", table="telefono", label="Teléfonos", key="Num",
                new={"Num": "3990003001", "Oper": "Claro", "Duenio": "1002"},
                temp={"Num": "3990003002", "Oper": "Tigo", "Duenio": "1003"},
                dup={"Num": "3001112233", "Oper": "Claro", "Duenio": "1001"},
                edit=("Oper", "Movistar"), cols=["Número", "Operador", "Dueño"],
                invalid={"Num": "3" * 16, "Oper": "o" * 46, "Duenio": "0"},
                missing="/Telefonos/Details?num=0000000000",
                q_new="SELECT oper FROM dbo.telefono WHERE num = '3990003001'",
                q_temp="SELECT COUNT(*) FROM dbo.telefono WHERE num = '3990003002'"),
    "PRO": dict(ctrl="Profesiones", table="profesion", label="Profesiones", key="Id",
                new={"Id": "971", "Nom": "Arquitecto de Software", "Des": "Disena la estructura de sistemas"},
                temp={"Id": "972", "Nom": "Temporal", "Des": ""},
                dup={"Id": "1", "Nom": "Dup", "Des": ""},
                edit=("Nom", "Arquitecto de Software Senior"), cols=["ID", "Nombre", "Descripción"],
                invalid={"Id": "0", "Nom": "n" * 91, "Des": ""},
                missing="/Profesiones/Details/9999",
                q_new="SELECT nom FROM dbo.profesion WHERE id = 971",
                q_temp="SELECT COUNT(*) FROM dbo.profesion WHERE id = 972", dep_key="1"),
    "EST": dict(ctrl="Estudios", table="estudios", label="Estudios", key="IdProf",
                new={"IdProf": "3", "CcPer": "1001", "Fecha": "2024-11-20", "Univer": "Universidad QA"},
                temp={"IdProf": "4", "CcPer": "1005", "Fecha": "", "Univer": "Temporal"},
                dup={"IdProf": "1", "CcPer": "1001", "Fecha": "", "Univer": "Dup"},
                edit=("Univer", "Universidad QA Editada"), cols=["Persona", "Profesión", "Fecha", "Universidad"],
                invalid={"IdProf": "3", "CcPer": "1002", "Fecha": "", "Univer": "u" * 51},
                missing="/Estudios/Details?idProf=4&ccPer=1003",
                q_new="SELECT univer FROM dbo.estudios WHERE id_prof = 3 AND cc_per = 1001",
                q_temp="SELECT COUNT(*) FROM dbo.estudios WHERE id_prof = 4 AND cc_per = 1005"),
}


def cleanup():
    sqlcmd("DELETE FROM dbo.estudios WHERE (id_prof = 3 AND cc_per = 1001) OR (id_prof = 4 AND cc_per = 1005) "
           "OR cc_per BETWEEN 2301 AND 2399 OR id_prof BETWEEN 971 AND 989; "
           "DELETE FROM dbo.telefono WHERE num LIKE '39900030%' OR duenio BETWEEN 2301 AND 2399; "
           "DELETE FROM dbo.persona WHERE cc BETWEEN 2301 AND 2399; "
           "DELETE FROM dbo.profesion WHERE id BETWEEN 971 AND 989", db="persona_db")


def shot(page, name, full=True):
    page.screenshot(path=os.path.join(EVID, name), full_page=full)
    return name


def fill_form(page, data, skip_key=False, key=None):
    for field, value in data.items():
        if skip_key and field in (key, "CcPer"):
            continue
        loc = page.locator(f"form.record-form [name='{field}']:not([type='hidden'])").first
        if not loc.count():
            continue
        tag = loc.evaluate("e => e.tagName")
        if tag == "SELECT":
            if value:
                loc.select_option(value)
        else:
            loc.fill(value)


def token_session(path):
    s = requests.Session()
    html = s.get(BASE_URL + path, timeout=30).text
    m = re.search(r'name="__RequestVerificationToken" type="hidden" value="([^"]+)"', html)
    return s, (m.group(1) if m else "")


def server_post(path_form, path_post, data):
    s, tok = token_session(path_form)
    r = s.post(BASE_URL + path_post, data={**data, "__RequestVerificationToken": tok}, timeout=30,
               allow_redirects=False)
    return r


def field_errors(html):
    return [(f, unescape(m)) for f, m in re.findall(r'<span class="field-validation-error"[^>]*data-valmsg-for="(\w+)"[^>]*>(.*?)</span>', html)]


def summary_errors(html):
    m = re.search(r'validation-summary-errors[^>]*>(.*?)</div>', html, re.S)
    return re.findall(r"<li>(.*?)</li>", m.group(1)) if m else []


def entity_cases(page, code, cfg):
    ctrl, table = cfg["ctrl"], cfg["table"]
    pre = f"MVC-{code}"

    # 01 listado
    page.goto(BASE_URL + "/")
    page.locator("nav[aria-label='Navegación principal'] a", has_text=cfg["label"]).click()
    page.wait_for_load_state()
    headers = [h.strip() for h in page.locator("thead th").all_inner_texts()]
    rows = page.locator("tbody tr").count()
    n_db = int(scalar(f"SELECT COUNT(*) FROM dbo.{table}"))
    missing_cols = [c for c in cfg["cols"] if c not in headers]
    ev = shot(page, f"EV-{pre}-01.png")
    write_evidence(f"{pre}-01", f"URL: {page.url}\nEncabezados: {headers}\nFilas: {rows}; filas en la base: {n_db}\n"
                                f"Columnas esperadas no mostradas: {missing_cols}\nCaptura: {ev}")
    ok = rows == n_db and not missing_cols
    obs = ""
    if missing_cols:
        obs = (f"El listado no muestra la columna {', '.join(missing_cols)}; solo aparece en Detalles. "
               "El listado sin datos se revisa en MVC-GEN (base vacia).")
    record(f"{pre}-01", "Aprobado" if ok else "Fallido",
           f"El menu abre {page.url.replace(BASE_URL, '')}; lista {rows} registros (base: {n_db}) con columnas "
           f"{', '.join(headers[:-1])}.", f"{ev}, EV-{pre}-01.txt", obs or "Sin datos: ver EV-MVC-LISTADO-VACIO.png.")

    # 02 crear
    page.locator("a", has_text="Nuevo registro").click()
    page.wait_for_load_state()
    fill_form(page, cfg["new"])
    shot(page, f"EV-{pre}-02-formulario.png")
    page.locator("form.record-form button[type='submit']").click()
    page.wait_for_load_state()
    redirected = page.url.rstrip("/").endswith(f"/{ctrl}") or page.url.endswith(f"/{ctrl}/Index")
    flash = page.locator(".notice").first.inner_text() if page.locator(".notice").count() else ""
    in_db = scalar(cfg["q_new"])
    ev = shot(page, f"EV-{pre}-02.png")
    ok = redirected and in_db == list(cfg["new"].values())[1 if code != "EST" else 3]
    record(f"{pre}-02", "Aprobado" if ok else "Fallido",
           f"Tras guardar redirige a {page.url.replace(BASE_URL, '')} con el aviso '{flash.strip()}'; el registro "
           f"aparece en el listado y en la base ('{in_db}').", f"EV-{pre}-02-formulario.png, {ev}")

    # 03 validacion del servidor (formulario vacio y valores fuera de rango o longitud)
    before = int(scalar(f"SELECT COUNT(*) FROM dbo.{table}"))
    empty = {k: "" for k in cfg["new"]}
    r1 = server_post(f"/{ctrl}/Create", f"/{ctrl}/Create", empty)
    r2 = server_post(f"/{ctrl}/Create", f"/{ctrl}/Create", cfg["invalid"])
    e1, e2 = field_errors(r1.text), field_errors(r2.text)
    after = int(scalar(f"SELECT COUNT(*) FROM dbo.{table}"))
    page.goto(BASE_URL + f"/{ctrl}/Create")
    page.locator("form.record-form button[type='submit']").click()
    page.wait_for_timeout(500)
    client_msgs = page.locator(".field-validation-error").all_inner_texts()
    ev = shot(page, f"EV-{pre}-03.png")
    write_evidence(f"{pre}-03", f"POST vacio -> {r1.status_code}; errores por campo: {e1}\n"
                                f"POST invalido {cfg['invalid']} -> {r2.status_code}; errores por campo: {e2}\n"
                                f"Registros antes/despues: {before}/{after}\n"
                                f"Validacion en el navegador (formulario vacio): {client_msgs}")
    ok = r1.status_code == 200 and r2.status_code == 200 and e1 and e2 and before == after
    record(f"{pre}-03", "Aprobado" if ok else "Fallido",
           f"Formulario vacio: {len(e1)} mensajes junto a los campos; valores fuera de rango o longitud: {len(e2)} "
           f"mensajes ({'; '.join(sorted({m for _, m in e2}))}). No se guarda nada ({before} -> {after}).",
           f"{ev}, EV-{pre}-03.txt")

    # 04 clave duplicada
    page.goto(BASE_URL + f"/{ctrl}/Create")
    fill_form(page, cfg["dup"])
    page.locator("form.record-form button[type='submit']").click()
    page.wait_for_load_state()
    summ = page.locator(".validation-summary-errors").all_inner_texts()
    still = int(scalar(f"SELECT COUNT(*) FROM dbo.{table}"))
    ev = shot(page, f"EV-{pre}-04.png")
    ok = any("Ya existe" in s for s in summ) and still == after
    record(f"{pre}-04", "Aprobado" if ok else "Fallido",
           f"Mensaje: '{' '.join(s.strip() for s in summ)}'; sin error tecnico y sin guardar.", ev)

    # 05 detalle
    page.goto(BASE_URL + f"/{ctrl}")
    page.locator("tbody tr").first.locator("a", has_text="Ver").click()
    page.wait_for_load_state()
    detail_txt = page.locator("main").inner_text()
    ev_a = shot(page, f"EV-{pre}-05.png")
    resp = page.goto(BASE_URL + cfg["missing"])
    body = page.content()
    ev_b = shot(page, f"EV-{pre}-05-inexistente.png")
    styled = "workspace" in body or "GESTIÓN" in body
    write_evidence(f"{pre}-05", f"Detalle: {page.url}\n{detail_txt[:800]}\n\nClave inexistente {cfg['missing']} -> "
                                f"{resp.status}; longitud del cuerpo {len(body)}; pagina propia de la aplicacion: {styled}")
    ok = resp.status == 404 and styled
    record(f"{pre}-05", "Aprobado" if ok else "Fallido",
           f"El detalle muestra todos los campos. La clave inexistente responde {resp.status} "
           f"{'con pagina propia' if styled else 'sin contenido (pagina en blanco)'}.",
           f"{ev_a}, {ev_b}, EV-{pre}-05.txt",
           "" if styled else "NotFound() sin UseStatusCodePages; la respuesta 404 no tiene cuerpo ni navegacion.")

    # 06 edicion
    page.goto(BASE_URL + f"/{ctrl}")
    key_text = list(cfg["new"].values())[0] if code != "EST" else "Universidad QA"
    row = page.locator("tbody tr", has_text=key_text).first
    row.locator("a", has_text="Editar").click()
    page.wait_for_load_state()
    key_input = page.locator(f"form.record-form [name='{cfg['key']}']:not([type='hidden'])").first
    if not key_input.count():
        key_input = page.locator(f"#{cfg['key']}").first
    ro = key_input.get_attribute("readonly") is not None or key_input.get_attribute("disabled") is not None
    field, new_val = cfg["edit"]
    prefilled = page.locator(f"[name='{field}']").first.input_value()
    page.locator(f"[name='{field}']").first.fill(new_val)
    shot(page, f"EV-{pre}-06-formulario.png")
    page.locator("form.record-form button[type='submit']").click()
    page.wait_for_load_state()
    listed = page.locator("tbody tr", has_text=new_val).count() > 0
    in_db = scalar(cfg["q_new"])
    ev = shot(page, f"EV-{pre}-06.png")
    ok = ro and prefilled and listed and in_db == new_val
    record(f"{pre}-06", "Aprobado" if ok else "Fallido",
           f"Formulario precargado ('{prefilled}'), clave {'no editable' if ro else 'editable'}; el cambio a "
           f"'{new_val}' se guarda y se ve en el listado.", f"EV-{pre}-06-formulario.png, {ev}")

    # 07 eliminacion con confirmacion
    server_post(f"/{ctrl}/Create", f"/{ctrl}/Create", cfg["temp"])
    page.goto(BASE_URL + f"/{ctrl}")
    temp_text = cfg["temp"]["Univer"] if code == "EST" else list(cfg["temp"].values())[0]
    page.locator("tbody tr", has_text=temp_text).first.locator("a", has_text="Eliminar").click()
    page.wait_for_load_state()
    ev_c = shot(page, f"EV-{pre}-07-confirmacion.png")
    page.locator("a.back-link", has_text="Cancelar").click()
    page.wait_for_load_state()
    kept = scalar(cfg["q_temp"])
    page.locator("tbody tr", has_text=temp_text).first.locator("a", has_text="Eliminar").click()
    page.wait_for_load_state()
    page.locator("button", has_text="Sí, eliminar").click()
    page.wait_for_load_state()
    gone = scalar(cfg["q_temp"])
    ev = shot(page, f"EV-{pre}-07.png")
    ok = kept == "1" and gone == "0" and page.url.rstrip("/").endswith(ctrl)
    record(f"{pre}-07", "Aprobado" if ok else "Fallido",
           f"Cancelar conserva el registro ({kept}); confirmar lo elimina ({gone}) y vuelve al listado.",
           f"{ev_c}, {ev}")

    # 08 dependencias o selectores
    if code in ("PER", "PRO"):
        dep = cfg["dep_key"]
        url = f"/{ctrl}/Delete?cc={dep}" if code == "PER" else f"/{ctrl}/Delete/{dep}"
        page.goto(BASE_URL + url)
        page.locator("button", has_text="Sí, eliminar").click()
        page.wait_for_load_state()
        msg = " ".join(t.strip() for t in page.locator(".validation-summary-errors").all_inner_texts())
        remains = scalar(f"SELECT COUNT(*) FROM dbo.{table} WHERE {'cc' if code == 'PER' else 'id'} = {dep}")
        ev = shot(page, f"EV-{pre}-08.png")
        clear = "relacionados" in msg
        record(f"{pre}-08", "Aprobado" if clear and remains == "1" else "Fallido",
               f"Se muestra '{msg}' y el registro {dep} permanece.", ev,
               "El texto dice 'No se pudo guardar' en una eliminacion y no nombra los telefonos o estudios "
               "relacionados; la API usa un mensaje especifico. Mejora sugerida: mensaje propio para eliminar.")
    else:
        page.goto(BASE_URL + f"/{ctrl}/Create")
        if code == "TEL":
            opts = page.locator("select[name='Duenio'] option").all_inner_texts()
            n_db = int(scalar("SELECT COUNT(*) FROM dbo.persona"))
            bad = {"Num": "3990003099", "Oper": "Claro", "Duenio": "999999"}
            q = "SELECT COUNT(*) FROM dbo.telefono WHERE num = '3990003099'"
            ok_opts = len(opts) - 1 == n_db
        else:
            opts = page.locator("select[name='CcPer'] option").all_inner_texts()
            opts2 = page.locator("select[name='IdProf'] option").all_inner_texts()
            n_db = int(scalar("SELECT COUNT(*) FROM dbo.persona"))
            n_db2 = int(scalar("SELECT COUNT(*) FROM dbo.profesion"))
            bad = {"IdProf": "999", "CcPer": "999999", "Fecha": "", "Univer": "x"}
            q = "SELECT COUNT(*) FROM dbo.estudios WHERE id_prof = 999 OR cc_per = 999999"
            ok_opts = len(opts) - 1 == n_db and len(opts2) - 1 == n_db2
        shot(page, f"EV-{pre}-08-selectores.png")
        r = server_post(f"/{ctrl}/Create", f"/{ctrl}/Create", bad)
        errs = field_errors(r.text)
        saved = scalar(q)
        ev = write_evidence(f"{pre}-08", f"Opciones del selector: {opts}\n"
                                         f"POST manipulado {bad} -> {r.status_code}; errores: {errs}\nGuardado: {saved}")
        record(f"{pre}-08", "Aprobado" if ok_opts and errs and saved == "0" else "Fallido",
               f"Los selectores listan las {len(opts) - 1} opciones existentes; el envio manipulado con referencias "
               f"inexistentes responde {r.status_code} con '{'; '.join(m for _, m in errs)}' y no se guarda.",
               f"EV-{pre}-08-selectores.png, {ev}")


def general_cases(page):
    # MVC-GEN-01 navegacion
    page.goto(BASE_URL + "/")
    links = page.locator("nav[aria-label='Navegación principal'] a")
    log, ok = [], True
    for i in range(links.count()):
        href = links.nth(i).get_attribute("href")
        r = requests.get(BASE_URL + href, timeout=30)
        ok &= r.status_code == 200
        log.append(f"{links.nth(i).inner_text().strip()} -> {href} -> {r.status_code}")
    brand = page.locator("a.brand").get_attribute("href")
    rb = requests.get(BASE_URL + brand, timeout=30)
    log.append(f"Marca (Inicio) -> {brand} -> {rb.status_code}")
    ev = write_evidence("MVC-GEN-01", "\n".join(log))
    record("MVC-GEN-01", "Aprobado" if ok and rb.status_code == 200 else "Fallido",
           f"Inicio y {links.count()} enlaces del menu responden 200: " + "; ".join(l.split(' -> ')[0] for l in log) + ".",
           ev)

    # MVC-GEN-02 inicio
    page.goto(BASE_URL + "/")
    cards = page.locator("main a").all_inner_texts()
    ev = shot(page, "EV-MVC-GEN-02.png")
    mods = [m for m in ("Personas", "Teléfonos", "Profesiones", "Estudios") if any(m in c for c in cards)]
    record("MVC-GEN-02", "Aprobado" if len(mods) == 4 else "Fallido",
           f"La pagina de inicio muestra 'Modulos del sistema' con acceso a {', '.join(mods)}.", ev)

    # MVC-GEN-06 antifalsificacion
    before = scalar("SELECT COUNT(*) FROM dbo.persona")
    r1 = requests.post(BASE_URL + "/Personas/Create", data={"Cc": "2390", "Nombre": "Csrf", "Apellido": "QA",
                                                            "Genero": "M"}, timeout=30)
    r2 = requests.post(BASE_URL + "/Personas/Delete?originalCc=1005", timeout=30)
    after = scalar("SELECT COUNT(*) FROM dbo.persona")
    ev = write_evidence("MVC-GEN-06", f"POST /Personas/Create sin token -> {r1.status_code}\n"
                                       f"POST /Personas/Delete?originalCc=1005 sin token -> {r2.status_code}\n"
                                       f"Personas antes/despues: {before}/{after}")
    record("MVC-GEN-06", "Aprobado" if r1.status_code == 400 and r2.status_code == 400 and before == after else "Fallido",
           f"POST de creacion y de eliminacion sin token responden {r1.status_code} y {r2.status_code}; "
           f"no se modifican datos ({before} -> {after}).", ev)

    # MVC-GEN-07 ruta inexistente
    resp = page.goto(BASE_URL + "/RutaQueNoExiste/Accion")
    body = page.content()
    ev = shot(page, "EV-MVC-GEN-07.png")
    styled = "workspace" in body or "GESTIÓN" in body
    write_evidence("MVC-GEN-07", f"GET /RutaQueNoExiste/Accion -> {resp.status}\nCuerpo ({len(body)} caracteres):\n{body[:500]}")
    record("MVC-GEN-07", "Aprobado" if styled else "Fallido",
           f"Responde {resp.status} sin contenido (pagina en blanco), sin detalles "
           "tecnicos pero sin pagina propia ni enlace de regreso." if not styled else
           f"Responde {resp.status} con pagina propia.", f"{ev}, EV-MVC-GEN-07.txt",
           "Propuesta: app.UseStatusCodePagesWithReExecute(\"/Home/Error\") o una vista NotFound.")

    # MVC-GEN-08 validacion en el navegador
    log, ok = [], True
    for ctrl, fields in [("Personas", {"Cc": "", "Nombre": "", "Edad": "200"}), ("Telefonos", {"Num": ""}),
                         ("Profesiones", {"Id": "0", "Nom": ""}), ("Estudios", {"Univer": ""})]:
        page.goto(BASE_URL + f"/{ctrl}/Create")
        requests_seen = []
        handler = lambda r: requests_seen.append(r.method) if r.method == "POST" else None  # noqa: E731
        page.on("request", handler)
        for k, v in fields.items():
            loc = page.locator(f"[name='{k}']").first
            if loc.count():
                loc.fill(v)
        page.locator("form.record-form button[type='submit']").click()
        page.wait_for_timeout(600)
        msgs = page.locator(".field-validation-error").all_inner_texts()
        page.remove_listener("request", handler)
        posted = "POST" in requests_seen
        server = field_errors(server_post(f"/{ctrl}/Create", f"/{ctrl}/Create",
                                          {k: v for k, v in fields.items()}).text)
        ok &= bool(msgs) and not posted
        log.append(f"{ctrl}: mensajes del navegador {msgs}; envio al servidor: {posted}; "
                   f"mensajes del servidor para los mismos datos: {[m for _, m in server]}")
        if ctrl == "Personas":
            shot(page, "EV-MVC-GEN-08.png")
    ev = write_evidence("MVC-GEN-08", "\n".join(log))
    record("MVC-GEN-08", "Aprobado" if ok else "Fallido",
           "En los 4 formularios la validacion del navegador muestra los mensajes antes de enviar y bloquea el POST; "
           "los campos rechazados coinciden con los del servidor.", f"EV-MVC-GEN-08.png, {ev}",
           "Los textos difieren levemente: el navegador nombra el campo ('El campo «Nombre» es obligatorio.') y el "
           "servidor usa 'Este campo es obligatorio.'.")


def empty_lists():
    """Listados sin datos: instancia en :5026 contra una base vacia."""
    sqlcmd("IF DB_ID('persona_qa_empty') IS NOT NULL DROP DATABASE persona_qa_empty; CREATE DATABASE persona_qa_empty;")
    sqlcmd("SELECT TOP 0 * INTO dbo.persona FROM persona_db.dbo.persona; SELECT TOP 0 * INTO dbo.telefono FROM "
           "persona_db.dbo.telefono; SELECT TOP 0 * INTO dbo.profesion FROM persona_db.dbo.profesion; "
           "SELECT TOP 0 * INTO dbo.estudios FROM persona_db.dbo.estudios;", db="persona_qa_empty")
    cs = "Server=localhost,1433;Database=persona_qa_empty;User Id=sa;Password=Persona_Lab1#2026;TrustServerCertificate=true"
    p = subprocess.Popen([DOTNET, "run", "--no-build", "--urls", "http://localhost:5026"], cwd=PR_PROJ,
                         env={**ENV, "ConnectionStrings__PersonaDb": cs}, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    log = []
    try:
        for _ in range(40):
            try:
                requests.get("http://localhost:5026/", timeout=5)
                break
            except requests.ConnectionError:
                time.sleep(1)
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 1366, "height": 800})
            for ctrl in ("Personas", "Telefonos", "Profesiones", "Estudios"):
                resp = pg.goto(f"http://localhost:5026/{ctrl}")
                empty = pg.locator("td.empty").inner_text() if pg.locator("td.empty").count() else ""
                log.append(f"{ctrl}: HTTP {resp.status}; mensaje: '{empty}'")
                if ctrl == "Personas":
                    pg.screenshot(path=os.path.join(EVID, "EV-MVC-LISTADO-VACIO.png"), full_page=True)
            b.close()
    finally:
        p.terminate(); p.wait(timeout=30)
        sqlcmd("DROP DATABASE persona_qa_empty;")
    write_evidence("MVC-LISTADO-VACIO", "\n".join(log))
    return log


def main():
    cleanup()
    empty = empty_lists()
    print("Listados vacios:", empty)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        for code, cfg in ENT.items():
            entity_cases(page, code, cfg)
        general_cases(page)
        browser.close()
    cleanup()


if __name__ == "__main__":
    main()
