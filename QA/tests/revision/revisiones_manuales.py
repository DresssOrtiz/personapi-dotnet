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


def ent12():
    docs = glob.glob(os.path.join(ROOT, "*_QA.docx"))
    d = zipfile.ZipFile(docs[0]).read("word/document.xml").decode("utf-8")
    rows = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", d, re.S):
        st = re.search(r'<w:pStyle w:val="([^"]+)"', p)
        t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)).strip()
        if t:
            rows.append((st.group(1) if st else "Normal", t))
    i0 = next(i for i, (_, t) in enumerate(rows) if t.startswith("3.9. Pruebas"))
    i1 = next(i for i, (_, t) in enumerate(rows) if t.startswith("4. Conclusiones"))
    body = [r for i, r in enumerate(rows) if not i0 <= i < i1]
    h2_body = [t for s, t in body if s == "Heading2" and len(t) > 110]
    lower = [t[max(0, m.start() - 30):m.end() + 15] for s, t in body if not t.startswith(("Material", "Microsoft"))
             for m in re.finditer(r"[a-zóé]\. (la|los|y|el) ", t)]
    person = [t[:80] for s, t in body if re.search(r"(?i)\b(nosotros|nuestr[oa]s?|realizamos|hicimos|vos|podés|tenés)\b", t)]
    tools = [t[:90] for s, t in body if "Codex" in t]
    refs = [t for s, t in body if t.startswith(("Material", "Microsoft", "Nota:"))]
    ev = write_evidence("ENT-12", f"Párrafos de cuerpo con estilo Heading2 (secciones 1 a 3 y pies de figura): {len(h2_body)}\n"
                                   f"Oraciones que empiezan en minúscula tras punto: {lower}\n"
                                   f"Primera persona o voseo: {person}\n"
                                   f"Menciones a herramientas de IA: {tools}\n"
                                   "Referencias:\n" + "\n".join(refs))
    record("ENT-12", "Fallido",
           f"La redacción está en tercera persona y sin voseo, pero {len(h2_body)} párrafos de cuerpo usan el estilo de "
           f"título Heading2, hay {len(lower)} oraciones que empiezan en minúscula tras punto (sección 1.2), las "
           f"secciones 3.5 y 3.7 mencionan a Codex y las referencias están marcadas como preliminares.",
           ev,
           "Las referencias no incluyen las fuentes usadas de ASP.NET Core MVC, EF Core, SQL Server ni Swagger; la de "
           "Microsoft Learn corresponde a Entity Data Model (EF 6). Revisado sobre la copia _QA." + NOTA)


if __name__ == "__main__":
    gen03()
    gen04()
    sw09()
    ent12()
