"""Caso MVC-GEN-05: el mismo flujo completo en varios navegadores.

Uso: python QA/tests/mvc/navegadores.py
Motores de Playwright: Chromium (motor de Chrome y Edge), Firefox y WebKit (motor
de Safari). Requiere `python -m playwright install chromium firefox webkit`.
Flujo por navegador: inicio, validacion en el navegador, crear persona, crear
telefono (selector), crear estudio (campo fecha), editar, ver detalle y eliminar
los tres registros con confirmacion. Claves de prueba: 2501-2503, 39900050xx.
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib import BASE_URL, EVID, record, scalar, sqlcmd, write_evidence  # noqa: E402

ENGINES = [("chromium", "Chromium (Chrome/Edge)"), ("firefox", "Firefox"), ("webkit", "WebKit (Safari)")]


def cleanup():
    sqlcmd("DELETE FROM dbo.estudios WHERE cc_per BETWEEN 2501 AND 2503; "
           "DELETE FROM dbo.telefono WHERE num LIKE '39900050%'; "
           "DELETE FROM dbo.persona WHERE cc BETWEEN 2501 AND 2503", db="persona_db")


def submit(page):
    page.locator("form.record-form button[type='submit']").click()
    page.wait_for_load_state()


def fill(page, data):
    for k, v in data.items():
        loc = page.locator(f"form.record-form [name='{k}']:not([type='hidden'])").first
        if loc.evaluate("e => e.tagName") == "SELECT":
            loc.select_option(v)
        else:
            loc.fill(v)


def confirm_delete(page, url):
    page.goto(BASE_URL + url)
    page.locator("button", has_text="Sí, eliminar").click()
    page.wait_for_load_state()


def flow(pw, engine, idx):
    cc = str(2500 + idx)
    num = f"399000500{idx}"
    steps, errors = [], []
    browser = getattr(pw, engine).launch()
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

    def step(name, ok, detail=""):
        steps.append((name, bool(ok), detail))

    try:
        r = page.goto(BASE_URL + "/")
        step("inicio", r.status == 200 and page.locator(".module-card").count() == 4, f"HTTP {r.status}")
        page.locator("nav a", has_text="Personas").click(); page.wait_for_load_state()
        step("menu personas", page.locator("tbody tr").count() >= 5)

        page.goto(BASE_URL + "/Personas/Create")
        page.locator("form.record-form button[type='submit']").click()
        page.wait_for_timeout(600)
        msgs = page.locator(".field-validation-error").all_inner_texts()
        step("validacion en el navegador", len(msgs) >= 3 and page.url.endswith("/Personas/Create"),
             f"{len(msgs)} mensajes")
        page.screenshot(path=os.path.join(EVID, f"EV-MVC-GEN-05-{engine}-validacion.png"), full_page=True)

        fill(page, {"Cc": cc, "Nombre": "Navegador", "Apellido": engine.capitalize(), "Genero": "F", "Edad": "33"})
        submit(page)
        step("crear persona", scalar(f"SELECT COUNT(*) FROM dbo.persona WHERE cc = {cc}") == "1")

        page.goto(BASE_URL + "/Telefonos/Create")
        fill(page, {"Num": num, "Oper": "Claro", "Duenio": cc})
        submit(page)
        step("crear telefono con selector", scalar(f"SELECT duenio FROM dbo.telefono WHERE num = '{num}'") == cc)

        page.goto(BASE_URL + "/Estudios/Create")
        fill(page, {"IdProf": "2", "CcPer": cc, "Fecha": "2024-11-20", "Univer": "Universidad Navegador"})
        submit(page)
        fecha = scalar(f"SELECT CONVERT(VARCHAR(10), fecha, 23) FROM dbo.estudios WHERE id_prof = 2 AND cc_per = {cc}")
        step("crear estudio con fecha", fecha == "2024-11-20", f"fecha guardada {fecha}")

        page.goto(BASE_URL + f"/Personas/Edit?cc={cc}")
        ro = page.locator("input[name='Cc']").get_attribute("readonly") is not None
        page.locator("input[name='Nombre']").fill("NavegadorEditado")
        submit(page)
        step("editar persona", ro and scalar(f"SELECT nombre FROM dbo.persona WHERE cc = {cc}") == "NavegadorEditado")

        page.goto(BASE_URL + f"/Personas/Details?cc={cc}")
        step("detalle", "NavegadorEditado" in page.locator("main").inner_text())
        page.screenshot(path=os.path.join(EVID, f"EV-MVC-GEN-05-{engine}-detalle.png"), full_page=True)

        confirm_delete(page, f"/Personas/Delete?cc={cc}")
        blocked = page.locator(".validation-summary-errors").count() > 0
        step("eliminar persona con dependientes es rechazado", blocked)
        confirm_delete(page, f"/Estudios/Delete?idProf=2&ccPer={cc}")
        confirm_delete(page, f"/Telefonos/Delete?num={num}")
        confirm_delete(page, f"/Personas/Delete?cc={cc}")
        left = scalar(f"SELECT (SELECT COUNT(*) FROM dbo.persona WHERE cc = {cc}) + "
                      f"(SELECT COUNT(*) FROM dbo.telefono WHERE num = '{num}') + "
                      f"(SELECT COUNT(*) FROM dbo.estudios WHERE cc_per = {cc})")
        step("eliminar en orden inverso", left == "0")
        page.screenshot(path=os.path.join(EVID, f"EV-MVC-GEN-05-{engine}-final.png"), full_page=True)
        version = browser.version
    finally:
        browser.close()
    return steps, errors, version


def main():
    cleanup()
    log, summary, all_ok = [], [], True
    with sync_playwright() as pw:
        for i, (engine, label) in enumerate(ENGINES, 1):
            steps, errors, version = flow(pw, engine, i)
            ok = all(s[1] for s in steps) and not errors
            all_ok &= ok
            summary.append(f"{label} {version}: {sum(s[1] for s in steps)}/{len(steps)} pasos")
            log.append(f"== {label} {version}\n" + "\n".join(f"[{'OK' if o else 'FALLA'}] {n} {d}" for n, o, d in steps)
                       + f"\nErrores de consola o de pagina: {errors}\n")
    cleanup()
    ev = write_evidence("MVC-GEN-05", "\n".join(log))
    record("MVC-GEN-05", "Aprobado" if all_ok else "Fallido",
           "El flujo completo (inicio, validacion, alta con selectores y fecha, edicion, detalle, rechazo por "
           "dependientes y eliminacion) se comporta igual en: " + "; ".join(summary) + ". Sin errores de consola.",
           f"EV-MVC-GEN-05-*.png, {ev}",
           "Chrome y Edge no estan instalados en el equipo de pruebas; se usaron los motores de Playwright: "
           "Chromium (el de Chrome y Edge), Firefox y WebKit (el de Safari), sin interfaz grafica.")


if __name__ == "__main__":
    main()
