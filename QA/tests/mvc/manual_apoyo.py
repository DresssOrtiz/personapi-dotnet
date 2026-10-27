"""Material de apoyo para los casos manuales (quedan en estado Pendiente).

Uso: python QA/tests/mvc/manual_apoyo.py
- MVC-GEN-04: capturas de listados y formularios en escritorio (1366), tableta (768)
  y movil (375), con la medicion del desborde horizontal de cada pagina.
- MVC-GEN-03: capturas de las 21 pantallas para compararlas con el diseno de Figma.
No decide el resultado: la revision visual la hace el responsable de QA.
"""
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib import BASE_URL, EVID, record, write_evidence  # noqa: E402

PAGES = {"inicio": "/", "personas-listado": "/Personas", "personas-crear": "/Personas/Create",
         "estudios-listado": "/Estudios", "estudios-crear": "/Estudios/Create"}
SCREENS = {"Inicio": "/"}
for ctrl, det in [("Personas", "?cc=1001"), ("Telefonos", "?num=3001112233"), ("Profesiones", "/1"),
                  ("Estudios", "?idProf=1&ccPer=1001")]:
    SCREENS.update({f"{ctrl}-Index": f"/{ctrl}", f"{ctrl}-Create": f"/{ctrl}/Create",
                    f"{ctrl}-Details": f"/{ctrl}/Details{det}", f"{ctrl}-Edit": f"/{ctrl}/Edit{det}",
                    f"{ctrl}-Delete": f"/{ctrl}/Delete{det}"})


def main():
    os.makedirs(os.path.join(EVID, "pantallas"), exist_ok=True)
    log = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for label, width in [("escritorio", 1366), ("tableta", 768), ("movil", 375)]:
            pg = b.new_page(viewport={"width": width, "height": 900})
            for name, path in PAGES.items():
                pg.goto(BASE_URL + path)
                over = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                tables = pg.evaluate("[...document.querySelectorAll('.table-scroll')].map(e => e.scrollWidth > e.clientWidth)")
                pg.screenshot(path=os.path.join(EVID, f"EV-MVC-GEN-04-{label}-{name}.png"), full_page=True)
                log.append(f"{label} ({width}px) {name}: desborde horizontal de la pagina {over}px; "
                           f"tabla con desplazamiento interno: {tables}")
            pg.close()
        pg = b.new_page(viewport={"width": 1366, "height": 900})
        for name, path in SCREENS.items():
            pg.goto(BASE_URL + path)
            pg.screenshot(path=os.path.join(EVID, "pantallas", f"EV-MVC-GEN-03-{name}.png"), full_page=True)
        b.close()
    ev = write_evidence("MVC-GEN-04-apoyo", "\n".join(log))
    record("MVC-GEN-04", "Pendiente", "", "", f"Revision manual pendiente. Apoyo automatizado en {ev} y capturas "
           "EV-MVC-GEN-04-*.png: " + "; ".join(l for l in log if "movil" in l), responsable="")
    record("MVC-GEN-03", "Pendiente", "", "", f"Revision manual pendiente: comparar con Figma las {len(SCREENS)} "
           "capturas de evidencias/pantallas/EV-MVC-GEN-03-*.png.", responsable="")
    print("\n".join(log))


if __name__ == "__main__":
    main()
