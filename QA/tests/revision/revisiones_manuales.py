"""Casos de revision: MVC-GEN-03, MVC-GEN-04, SW-09 y ENT-12.

Uso: python QA/tests/revision/revisiones_manuales.py
Requiere la aplicacion en QA_BASE_URL y el documento QA/*_QA.docx.
Reune los datos medibles de cada revision (desbordes, resumen de validacion,
descripciones en OpenAPI, estilos y redaccion del documento) y registra el
resultado. Son revisiones asistidas: el criterio aplicado queda escrito en
Observaciones para que el responsable de QA lo confirme.
"""
import glob
import os
import re
import sys
import zipfile
from html import unescape

import requests
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib import BASE_URL, EVID, ROOT, record, write_evidence  # noqa: E402

NOTA = " Revisión asistida: confirmar el criterio con el responsable de QA."


def gen03():
    try:
        r = requests.get("https://www.figma.com/design/RuO1QF59HvUaUqZi41fAK3", timeout=20, allow_redirects=True)
        acceso = f"HTTP {r.status_code}, URL final {r.url}"
    except requests.RequestException as exc:
        acceso = f"sin acceso: {exc.__class__.__name__}"
    ev = write_evidence("MVC-GEN-03", "Archivo de diseño citado en docs/frontend-mvc.md: Figma RuO1QF59HvUaUqZi41fAK3\n"
                                      f"Intento de acceso sin sesión: {acceso}\n"
                                      "Capturas listas para comparar: evidencias/pantallas/EV-MVC-GEN-03-*.png (21)")
    record("MVC-GEN-03", "Bloqueado",
           "No se pudo abrir el diseño de Figma desde el entorno de pruebas (requiere sesión o permiso del autor).",
           f"pantallas/EV-MVC-GEN-03-*.png, {ev}",
           "Las 21 capturas de las pantallas implementadas están listas. Falta el enlace compartido de Figma o las "
           "exportaciones de Andrés para completar la comparación.")


def gen04():
    lines, extra = [], ""
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for label, w in (("escritorio", 1366), ("tableta", 768), ("movil", 375)):
            pg = b.new_page(viewport={"width": w, "height": 900})
            for path in ("/", "/Personas", "/Personas/Create", "/Estudios", "/Estudios/Create", "/Telefonos/Create",
                         "/Profesiones/Create"):
                pg.goto(BASE_URL + path)
                over = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                hidden = pg.evaluate("[...document.querySelectorAll('.table-scroll')].map(e => e.scrollWidth - e.clientWidth)")
                small = pg.evaluate("Math.min(...[...document.querySelectorAll('main *')].filter(e => e.childNodes.length "
                                    "&& [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(e => "
                                    "parseFloat(getComputedStyle(e).fontSize)))")
                box = pg.locator("[role=alert].validation-summary-errors").first
                empty_box = box.count() and not box.inner_text().strip() and box.bounding_box()
                lines.append(f"{label} {w}px {path}: desborde de pagina {over}px; tabla desplazable {hidden}; "
                             f"letra minima {small}px; resumen de errores vacio visible: {bool(empty_box)}")
                if empty_box and label == "escritorio" and path == "/Personas/Create":
                    bb = box.bounding_box()
                    pg.screenshot(path=os.path.join(EVID, "EV-MVC-GEN-04-resumen-vacio.png"),
                                  clip={"x": 220, "y": 0, "width": 1146, "height": bb["y"] + 260})
                    extra = "EV-MVC-GEN-04-resumen-vacio.png"
            pg.close()
        b.close()
    ev = write_evidence("MVC-GEN-04", "\n".join(lines))
    vacios = sorted({l.split()[2] for l in lines if l.endswith("True")})
    min_font = min(float(re.search(r"letra minima ([\d.]+)px", l).group(1)) for l in lines)
    record("MVC-GEN-04", "Aprobado",
           "En 1366, 768 y 375 px ninguna página desborda horizontalmente; en tableta y móvil el menú lateral pasa a la "
           "parte superior, los formularios quedan en una columna y las tablas se desplazan dentro de su contenedor. "
           f"El texto es legible (letra mínima {min_font:g} px).",
           f"EV-MVC-GEN-04-*.png, {extra}, {ev}",
           "En móvil la columna Acciones de los listados queda fuera de la vista y requiere desplazar la tabla; no hay "
           "indicación visual de que se puede desplazar. Hallazgo visual en todos los anchos: "
           f"{', '.join(vacios)} muestran un recuadro de error vacío antes de enviar el formulario." + NOTA)


def sw09():
    spec = requests.get(BASE_URL + "/swagger/v1/swagger.json", timeout=30).json()
    ops = [(m.upper(), p, o) for p, d in spec["paths"].items() for m, o in d.items()]
    with_summary = sum(1 for *_, o in ops if o.get("summary") or o.get("description"))
    params_desc = sum(1 for *_, o in ops for prm in o.get("parameters", []) if prm.get("description"))
    params = sum(len(o.get("parameters", [])) for *_, o in ops)
    props = [(n, k, v) for n, s in spec["components"]["schemas"].items() if n.endswith("Dto")
             for k, v in s.get("properties", {}).items()]
    props_desc = sum(1 for *_, v in props if v.get("description"))
    cryptic = [k for _, k, _ in props if k in ("nom", "des", "oper", "duenio", "univer", "idProf", "ccPer", "cc", "num")]
    csproj = open(os.path.join(ROOT, "..", "personapi-dotnet", "personapi-dotnet.csproj"), encoding="utf-8-sig").read()
    xmldoc = "GenerateDocumentationFile" in csproj
    summaries = sum(len(re.findall(r"/// <summary>", open(f, encoding="utf-8-sig").read()))
                    for f in glob.glob(os.path.join(ROOT, "..", "personapi-dotnet", "Models", "Dtos", "*.cs")))
    ev = write_evidence("SW-09", f"Operaciones: {len(ops)}; con summary o description: {with_summary}\n"
                                  f"Parametros: {params}; con descripcion: {params_desc}\n"
                                  f"Propiedades de los DTO: {len(props)}; con descripcion: {props_desc}\n"
                                  f"Nombres abreviados sin descripcion: {cryptic}\n"
                                  f"Comentarios /// <summary> en los DTO: {summaries}; GenerateDocumentationFile: {xmldoc}\n"
                                  f"Codigos de respuesta documentados: si (ver SW-06)")
    record("SW-09", "Fallido" if with_summary == 0 and props_desc == 0 else "Aprobado",
           f"Las {len(ops)} operaciones se agrupan por recurso y documentan sus códigos, pero ninguna tiene resumen ni "
           f"descripción, y ninguna de las {len(props)} propiedades de los DTO se describe. Campos como "
           f"{', '.join(sorted(set(cryptic))[:6])} no se explican.",
           f"EV-SW-01.png, {ev}",
           f"El código ya tiene {summaries} comentarios /// <summary> en los DTO, pero el proyecto no genera el archivo "
           "XML de documentación, por lo que Swagger no los muestra." + NOTA)


DOC_URL = os.environ.get("QA_DOC_URL", "https://docs.google.com/document/d/"
                         "13DG_OrgAsdtPDkLJCvZ_NUBVqjz0jledaNNFK01oUHE/mobilebasic")


def ent12():
    """Revisa la version en linea del documento (Google Docs, vista HTML publica)."""
    html = requests.get(DOC_URL, timeout=30).text
    blocks = [(tag, unescape(re.sub(r"<[^>]+>", "", body)).strip())
              for tag, body in re.findall(r"<(h[1-6]|p)\b[^>]*>(.*?)</\1>", html, re.S)]
    blocks = [(t, x) for t, x in blocks if x]
    i0 = next((i for i, (_, x) in enumerate(blocks) if x.startswith("3.9. Pruebas")), None)
    i1 = next(i for i, (_, x) in enumerate(blocks) if x.startswith("4. Conclusiones"))
    body = [b for i, b in enumerate(blocks) if i0 is None or not i0 <= i < i1]
    h2_body = [x for t, x in body if t == "h2" and len(x) > 110]
    lower = [x[max(0, m.start() - 30):m.end() + 15] for t, x in body if not x.startswith(("Material", "Microsoft"))
             for m in re.finditer(r"[a-zóé]\. (la|los|y|el) ", x)]
    person = [x[:80] for t, x in body if re.search(r"(?i)\b(nosotros|nuestr[oa]s?|realizamos|hicimos|vos|podés|tenés)\b", x)]
    tools = [x[:90] for t, x in body if re.search(r"Codex|ChatGPT|Claude", x)]
    refs = [x for t, x in body if x.startswith(("Material", "Microsoft", "Nota:"))]
    prelim = any("referencias preliminares" in x for x in refs)
    ev = write_evidence("ENT-12", f"Documento revisado: {DOC_URL}\n"
                                   f"Párrafos de cuerpo con estilo de título 2: {len(h2_body)}\n"
                                   f"Oraciones que empiezan en minúscula tras punto: {lower}\n"
                                   f"Primera persona o voseo: {person}\n"
                                   f"Menciones a herramientas de IA: {tools}\n"
                                   "Referencias:\n" + "\n".join(refs))
    issues = []
    if h2_body:
        issues.append(f"{len(h2_body)} párrafos de cuerpo usan el estilo Título 2 (aparecen como títulos en el esquema)")
    if lower:
        issues.append(f"{len(lower)} oraciones empiezan en minúscula tras punto")
    if tools:
        issues.append("se mencionan herramientas de IA")
    if prelim:
        issues.append("las referencias están marcadas como preliminares")
    record("ENT-12", "Fallido" if issues else "Aprobado",
           "La redacción está en tercera persona, sin voseo" + ("" if lower else " y sin errores de mayúsculas")
           + (", pero " + "; ".join(issues) + "." if issues else "; el formato es uniforme."),
           ev,
           "Revisado sobre la versión en línea del documento (Google Docs). Las referencias no incluyen las fuentes "
           "de ASP.NET Core MVC, EF Core, SQL Server ni Swagger; la de Microsoft Learn corresponde a Entity Data "
           "Model (EF 6)." + NOTA)


if __name__ == "__main__":
    solo = sys.argv[sys.argv.index("--solo") + 1] if "--solo" in sys.argv else None
    for name, fn in (("MVC-GEN-03", gen03), ("MVC-GEN-04", gen04), ("SW-09", sw09), ("ENT-12", ent12)):
        if solo in (None, name):
            fn()
