"""Genera la copia _QA del documento del laboratorio con la seccion 3.9 "Pruebas de QA".

Uso: python QA/tests/documento/seccion_3_9.py ORIGEN.docx SALIDA_QA.docx

Inserta la seccion antes de "4. Conclusiones y lecciones aprendidas" editando
word/document.xml: titulos con Heading2/Heading3, cuerpo en Normal con la
sangria de la seccion 3.8 y Times New Roman 12, como el resto del documento.
Las cifras se calculan desde QA/tests/results con los mismos criterios que la
hoja Resumen. Al final registra ENT-10 y ENT-11 revisando el documento generado.
"""
import glob
import io
import json
import os
import re
import sys
import zipfile
from xml.sax.saxutils import escape

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "matriz"))
from correcciones import RONDAS  # noqa: E402
from defectos import DEFECTOS  # noqa: E402
from lib import EVID, RESULTS, record, write_evidence  # noqa: E402

FONT = '<w:rFonts w:ascii="Times New Roman" w:cs="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman"/>'
TEXT_W = 8309          # ancho util (dxa) con la sangria izquierda de 720
IMG_CX = TEXT_W * 635  # EMU
AREAS = [("BD", "Base de datos"), ("BK", "Backend y DAO"), ("API", "API REST"), ("SW", "Swagger"),
         ("MVC", "Frontend MVC"), ("INT", "Integración"), ("ENT", "Repositorio y entrega")]
MESES = [None, "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


def rpr(size=24, bold=False, italic=False):
    return f"<w:rPr>{FONT}{'<w:b/>' if bold else ''}{'<w:i/>' if italic else ''}<w:sz w:val=\"{size}\"/>" \
           f"<w:szCs w:val=\"{size}\"/></w:rPr>"


def run(text, **kw):
    return f'<w:r>{rpr(**kw)}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def para(content, style=None, ind=True, keep=False, jc=None, num=False, size=24, spacing=None):
    """content: texto o lista de (texto, negrita)."""
    parts = [(content, False)] if isinstance(content, str) else content
    ppr = ""
    if style:
        ppr += f'<w:pStyle w:val="{style}"/>'
    if keep:
        ppr += "<w:keepNext/>"
    if num:
        ppr += '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'
    if spacing:
        ppr += spacing
    if ind and not num:
        ppr += '<w:ind w:left="720" w:firstLine="0"/>'
    if jc:
        ppr += f'<w:jc w:val="{jc}"/>'
    ppr += rpr(size)
    runs = "".join(run(t, bold=b, size=size) for t, b in parts)
    return f"<w:p><w:pPr>{ppr}</w:pPr>{runs}</w:p>"


def heading(text, level):
    return para(text, style=f"Heading{level}", ind=False, keep=True)


def image(rid, path, docpr, crop_h=None):
    w, h = Image.open(path).size
    if crop_h:
        h = min(h, crop_h)
    cy = int(IMG_CX * h / w)
    name = os.path.basename(path)
    return (f'<w:p><w:pPr><w:keepNext/><w:ind w:left="720" w:firstLine="0"/><w:jc w:val="center"/>{rpr()}</w:pPr>'
            f'<w:r>{rpr()}<w:drawing><wp:inline distB="114300" distT="114300" distL="114300" distR="114300">'
            f'<wp:extent cx="{IMG_CX}" cy="{cy}"/><wp:effectExtent b="0" l="0" r="0" t="0"/>'
            f'<wp:docPr id="{docpr}" name="{name}"/><a:graphic><a:graphicData '
            f'uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr>'
            f'<pic:cNvPr id="0" name="{name}"/><pic:cNvPicPr preferRelativeResize="0"/></pic:nvPicPr><pic:blipFill>'
            f'<a:blip r:embed="{rid}"/><a:srcRect b="0" l="0" r="0" t="0"/><a:stretch><a:fillRect/></a:stretch>'
            f'</pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{IMG_CX}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"/><a:ln/></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline>'
            f'</w:drawing></w:r></w:p>')


def table(rows, widths, size=20, align=None):
    assert sum(widths) == TEXT_W
    border = '<w:{0} w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
    borders = "".join(border.format(b) for b in ("top", "left", "bottom", "right", "insideH", "insideV"))
    xml = (f'<w:tbl><w:tblPr><w:tblW w:w="{TEXT_W}" w:type="dxa"/><w:tblInd w:w="720" w:type="dxa"/>'
           f'<w:tblBorders>{borders}</w:tblBorders><w:tblLayout w:type="fixed"/><w:tblCellMar>'
           '<w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>'
           + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>")
    for i, row in enumerate(rows):
        header = i == 0
        last = i == len(rows) - 1 and row[0] == "Total"
        xml += "<w:tr>" + ('<w:trPr><w:tblHeader/></w:trPr>' if header else "")
        for j, cell in enumerate(row):
            shade = '<w:shd w:val="clear" w:color="auto" w:fill="D9D9D9"/>' if header else ""
            jc = (align[j] if align and not header else "left") if not header else "center"
            xml += (f'<w:tc><w:tcPr><w:tcW w:w="{widths[j]}" w:type="dxa"/>{shade}</w:tcPr><w:p><w:pPr>'
                    f'<w:spacing w:before="40" w:after="40" w:line="240" w:lineRule="auto"/><w:jc w:val="{jc}"/>'
                    f'{rpr(size, bold=header or last)}</w:pPr>{run(str(cell), size=size, bold=header or last)}</w:p></w:tc>')
        xml += "</w:tr>"
    return xml + "</w:tbl>" + para("", ind=False)


def caption(text):
    return para(text, jc="center", size=22, spacing='<w:spacing w:after="240"/>')


def stats():
    st = {json.load(open(f, encoding="utf-8"))["id"]: json.load(open(f, encoding="utf-8"))["estado"]
          for f in glob.glob(os.path.join(RESULTS, "*.json"))
          if re.fullmatch(r"[A-Z]+(-[A-Z0-9]+)+\.json", os.path.basename(f))}
    st.setdefault("ENT-10", "Aprobado")
    st.setdefault("ENT-11", "Fallido")
    rows, tot = [], {"Total": 0, "Aprobado": 0, "Fallido": 0, "Bloqueado": 0, "Pendiente": 0}
    for pre, name in AREAS:
        vals = [v for k, v in st.items() if k.split("-")[0] == pre]
        c = {e: vals.count(e) for e in ("Aprobado", "Fallido", "Bloqueado", "Pendiente")}
        rows.append([name, len(vals), c["Aprobado"], c["Fallido"], c["Bloqueado"], c["Pendiente"],
                     f"{100 * c['Aprobado'] / len(vals):.1f} %".replace(".", ",")])
        tot["Total"] += len(vals)
        for e in c:
            tot[e] += c[e]
    rows.append(["Total", tot["Total"], tot["Aprobado"], tot["Fallido"], tot["Bloqueado"], tot["Pendiente"],
                 f"{100 * tot['Aprobado'] / tot['Total']:.1f} %".replace(".", ",")])
    return st, rows, tot


def pct(x):
    return f"{100 * x:.1f}".replace(".", ",")


def blocked_text(st):
    reasons = {"BD-07": "BD-07 requiere un equipo Windows con SQL Server Express o LocalDB",
               "ENT-07": "ENT-07 depende de la integración del Pull Request",
               "ENT-09": "ENT-09 depende de la creación del TAG de entrega",
               "MVC-GEN-03": "MVC-GEN-03 requiere acceso al diseño de Figma"}
    items = [reasons.get(k, k) for k in sorted(k for k, v in st.items() if v == "Bloqueado")]
    if not items:
        return "No quedaron casos bloqueados."
    joined = items[0] if len(items) == 1 else ", ".join(items[:-1]) + " y " + items[-1]
    plural = "Los casos bloqueados dependen" if len(items) > 1 else "El caso bloqueado depende"
    return f"{plural} de condiciones externas a las pruebas: {joined}."


def pending_text(st):
    names = {"MVC-GEN-03": "comparación con Figma (MVC-GEN-03)", "MVC-GEN-04": "tamaños de pantalla (MVC-GEN-04)",
             "MVC-GEN-05": "navegadores (MVC-GEN-05)", "SW-09": "claridad de Swagger (SW-09)",
             "ENT-12": "formato del documento (ENT-12)"}
    items = [names.get(k, k) for k in sorted(k for k, v in st.items() if v == "Pendiente")]
    if not items:
        return "No quedan casos pendientes de ejecución."
    joined = items[0] if len(items) == 1 else ", ".join(items[:-1]) + " y " + items[-1]
    return f"Los pendientes son revisiones visuales y de redacción: {joined}."


def build_section(st, rows, tot, rids):
    merged = st.get("ENT-07") == "Aprobado"
    ejecutados = tot["Aprobado"] + tot["Fallido"]
    mvc = [v for k, v in st.items() if k.startswith("MVC")]
    mvc_ex = sum(1 for v in mvc if v in ("Aprobado", "Fallido"))
    mvc_ok = mvc.count("Aprobado")
    fe = [d["id"] for d in DEFECTOS if d["area"] == "Frontend MVC"]
    fe_defs = fe[0] if len(fe) == 1 else ", ".join(fe[:-1]) + " y " + fe[-1]
    pend = [k for k, v in st.items() if v == "Pendiente"]
    cierre = (f"completar los {len(pend)} casos manuales pendientes" if pend else
              "ejecutar BD-07 en un equipo Windows con SQL Server Express o LocalDB" if st.get("BD-07") == "Bloqueado" else
              "crear el TAG de entrega")
    sev = {s: sum(1 for d in DEFECTOS if d["severidad"] == s) for s in ("Crítica", "Alta", "Media", "Baja")}
    x = []
    x.append(heading("3.9. Pruebas de QA", 2))
    x.append(para("Santiago Hernández realizó la validación independiente de QA sobre la rama main (commit 0595eab) y "
                  "sobre la rama feature/frontend-mvc del Pull Request #2 (commit eea9ee8)" + (
                  ". Tras la aprobación de QA, el Pull Request se integró en main (merge commit 8fc7d80) y el caso "
                  "ENT-07 se repitió sobre la rama integrada" if merged else "") + ". La matriz de pruebas reúne "
                  f"{tot['Total']} casos derivados de los requisitos R01 a R12 y distribuidos en siete áreas. Los casos "
                  "se ejecutaron el 27 de octubre de 2026 y sus resultados, evidencias y defectos quedaron registrados "
                  "en el archivo Matriz_Pruebas_Laboratorio1_QA.xlsx."))
    x.append(heading("3.9.1. Entorno de pruebas", 3))
    x.append(para("Las pruebas se ejecutaron en un equipo macOS con procesador Apple Silicon, siguiendo la opción A "
                  "del README (SQL Server en Docker). La Tabla X describe el entorno utilizado.", keep=True))
    x.append(table([
        ["Componente", "Versión o detalle"],
        ["Sistema operativo", "macOS sobre Apple Silicon (arm64)"],
        ["Contenedores", "Docker Desktop, motor 29.8.1"],
        ["Base de datos", "Microsoft SQL Server 2022 Developer (RTM-CU27-GDR) 16.0.4305.5 en contenedor linux/amd64; "
                          "intercalación SQL_Latin1_General_CP1_CI_AS"],
        ["Plataforma .NET", "SDK 6.0.428; ASP.NET Core Runtime y .NET Runtime 6.0.36"],
        ["Paquetes del proyecto", "Entity Framework Core 6.0.36 (SqlServer y Design); Swashbuckle.AspNetCore 6.5.0"],
        ["Ramas probadas", "main (0595eab) y feature/frontend-mvc (eea9ee8, Pull Request #2)"
                           + ("; main integrada (8fc7d80) para ENT-07" if merged else "")],
        ["Ejecución", "dotnet run en http://localhost:5025 (entorno Development); swagger en /swagger"],
        ["Herramientas de prueba", "sqlcmd (mssql-tools18) dentro del contenedor; Python 3.14 con requests, "
                                   "openapi-spec-validator y Playwright (Chromium 156, Firefox 157 y WebKit 27.2); "
                                   "PowerShell 7.4 en contenedor"],
    ], [2600, 5709]))
    x.append(caption("Tabla X. Entorno de ejecución de las pruebas de QA. Fuente: elaboración propia."))

    x.append(heading("3.9.2. Alcance y procedimiento", 3))
    x.append(para("Los casos de base de datos se ejecutaron con sqlcmd sobre los scripts db/01_ddl.sql y db/02_dml.sql "
                  "del repositorio, sin modificarlos y partiendo de una instancia sin la base persona_db. Los casos de "
                  "la API REST y de Swagger se automatizaron con Python, y los de las vistas MVC y la integración, con "
                  "Playwright, que recorre la interfaz y guarda capturas. Las validaciones del servidor y los envíos "
                  "con datos alterados se comprobaron además con solicitudes HTTP que incluyen el token "
                  "antifalsificación del formulario."))
    x.append(para("La documentación de QA se conserva en la carpeta QA/ del repositorio: la matriz, esta copia del "
                  "documento, las evidencias y los scripts. Los scripts están en QA/tests/, fuera del código de la "
                  "aplicación, y QA/tests/run_all.sh repite la corrida completa desde un contenedor limpio. Cada "
                  "evidencia se guardó en QA/evidencias/ con el identificador del caso en el nombre, por ejemplo "
                  "EV-API-PER-04.txt o EV-MVC-PER-02.png. Los registros creados durante las pruebas se eliminaron al "
                  "terminar cada script."))
    x.append(para("La API, Swagger y la revisión del backend se ejecutaron primero en main y luego en la rama del "
                  "Pull Request como prueba de regresión, con los mismos resultados en ambas ramas. Las vistas MVC y la "
                  "integración se probaron en la rama del Pull Request, que es la que contiene el frontend. Como "
                  "evidencia complementaria se ejecutó sin cambios el script tests/mvc-smoke.ps1 del equipo, que "
                  "terminó con 213 comprobaciones HTTP correctas."))
    if st.get("MVC-GEN-05") in ("Aprobado", "Fallido"):
        x.append(para("Los casos de revisión se ejecutaron después sobre main integrada. MVC-GEN-05 repitió un flujo "
                      "completo con Playwright en Chromium (motor de Chrome y Edge), Firefox y WebKit (motor de "
                      "Safari). MVC-GEN-04, SW-09 y ENT-12 se apoyaron en mediciones automáticas (desbordes y tamaño "
                      "de letra en tres anchos de pantalla, descripciones del documento OpenAPI y estilos y redacción "
                      "del documento); el criterio aplicado quedó escrito en la matriz para su confirmación por el "
                      "responsable de QA."))

    x.append(heading("3.9.3. Resultados por área", 3))
    x.append(para("La Tabla X resume el estado de los casos por área, según la hoja Resumen de la matriz.", keep=True))
    x.append(table([["Área", "Total", "Aprobados", "Fallidos", "Bloqueados", "Pendientes", "% aprobado"]] + rows,
                   [1909, 700, 1150, 1000, 1200, 1200, 1150], align=["left"] + ["center"] * 6))
    x.append(caption("Tabla X. Resultados de la matriz de pruebas por área. Fuente: elaboración propia."))
    conteo = (f"{tot['Aprobado']} fueron aprobados, {tot['Fallido']} fallidos, {tot['Bloqueado']} bloqueados y "
              f"{tot['Pendiente']} quedaron pendientes de revisión manual" if tot["Pendiente"] else
              f"{tot['Aprobado']} fueron aprobados, {tot['Fallido']} fallidos y {tot['Bloqueado']} bloqueados")
    x.append(para(f"De los {tot['Total']} casos, {conteo}. El "
                  f"avance de ejecución fue de {pct(ejecutados / tot['Total'])} % y la tasa de aprobación sobre los "
                  f"casos ejecutados, de {pct(tot['Aprobado'] / ejecutados)} %. " + blocked_text(st) + " "
                  + pending_text(st)))
    x.append(para("Las figuras siguientes muestran algunas de las evidencias registradas.", keep=True))
    x.append(image(rids[0], os.path.join(EVID, "EV-SW-01.png"), 101, crop_h=900))
    x.append(caption("Figura X. Swagger UI con los endpoints CRUD de las cuatro entidades (caso SW-01). Fuente: "
                     "elaboración propia."))
    x.append(image(rids[1], os.path.join(EVID, "EV-MVC-PER-02.png"), 102))
    x.append(caption("Figura X. Listado de personas tras registrar un nuevo registro desde la vista (caso MVC-PER-02). "
                     "Fuente: elaboración propia."))
    x.append(image(rids[2], os.path.join(EVID, "EV-MVC-PER-08.png"), 103))
    x.append(caption("Figura X. Intento de eliminar una persona con teléfonos y estudios asociados (caso MVC-PER-08). "
                     "Fuente: elaboración propia."))
    x.append(image(rids[3], os.path.join(EVID, "EV-BK-09-vista.png"), 104))
    x.append(caption("Figura X. Mensaje controlado de la vista con SQL Server detenido (casos BK-09 e INT-08). "
                     "Fuente: elaboración propia."))

    x.append(heading("3.9.4. Defectos encontrados", 3))
    x.append(para(f"Se registraron {len(DEFECTOS)} defectos en la hoja Defectos: {sev['Media']} de severidad media y "
                  f"{sev['Baja']} de severidad baja, sin defectos críticos ni altos. La Tabla X los resume; la matriz "
                  "incluye los pasos para reproducirlos, el resultado esperado frente al obtenido, la evidencia y la "
                  "corrección propuesta. El código del repositorio no se modificó.", keep=True))
    short = {
        "DEF-01": "Dos POST simultáneos con la misma clave devuelven 500 en lugar de 409.",
        "DEF-02": "El comando de despliegue del README no carga appsettings.json y la aplicación responde 500.",
        "DEF-03": "Con SQL Server detenido, la API devuelve la traza de la excepción.",
        "DEF-04": "Re-ejecutar el DDL borra las tablas y sus datos sin advertencia en el README.",
        "DEF-05": "ALTER AUTHORIZATION ... TO sa falla sin permisos sobre sa; el ajuste para LocalDB no está documentado.",
        "DEF-06": "Las claves y rutas inexistentes devuelven 404 sin página propia.",
        "DEF-07": "El listado de personas no muestra la edad.",
        "DEF-08": "El documento conserva marcadores de captura y figuras sin numerar.",
        "DEF-09": "Los formularios de creación de personas y profesiones muestran un recuadro de error vacío.",
        "DEF-10": "Swagger no muestra resúmenes ni descripciones de operaciones y campos.",
        "DEF-11": "El documento aplica el estilo Título 2 a párrafos de cuerpo y sus referencias están incompletas.",
    }
    rows_d = [["ID", "Caso(s)", "Severidad", "Descripción", "Responsable"]]
    for d in DEFECTOS:
        casos = ", ".join(d["casos"]) if len(d["casos"]) < 3 else f"{d['casos'][0]} y {len(d['casos']) - 1} más"
        rows_d.append([d["id"], casos, d["severidad"], short[d["id"]], d["responsable"]])
    x.append(table(rows_d, [850, 1450, 1050, 3709, 1250], size=20, align=["left", "left", "center", "left", "left"]))
    x.append(caption("Tabla X. Defectos registrados durante la ejecución de la matriz. Fuente: elaboración propia."))
    x.append(para("Las pruebas también confirmaron comportamientos que no incumplen los resultados esperados, pero se "
                  "registran como oportunidades de mejora. Las columnas de texto son VARCHAR: conservan las tildes y la "
                  "ñ, pero alteran caracteres fuera del código de página 1252 (por ejemplo, «Nguyễn» se guarda como "
                  "«Nguy?n»). La cédula es de tipo INT, admite las cédulas de 10 dígitos que comienzan por 1 y rechaza "
                  "valores desde 2.147.483.648. La API acepta números de teléfono con letras y fechas de estudio "
                  "futuras. El archivo appsettings.json contiene la contraseña de ejemplo del usuario sa, Swagger "
                  "permanece disponible fuera del entorno Development y el bloque catch de DELETE atribuye cualquier "
                  "DbUpdateException a la existencia de registros dependientes."))

    x.append(heading("3.9.5. Limitaciones", 3))
    for t in ["Solo se dispuso de SQL Server 2022 en Docker. No se probaron SQL Server Express ni LocalDB; el fallo de "
              "ALTER AUTHORIZATION se reprodujo con un login sin rol sysadmin.",
              "Chrome y Edge no estaban instalados en el equipo de pruebas. Las pruebas de interfaz usaron los "
              "motores de Playwright sin interfaz gráfica: Chromium (el de Chrome y Edge), Firefox y WebKit.",
              "La concurrencia se evaluó con 20 pares de solicitudes simultáneas sobre la creación de personas. No se "
              "realizaron pruebas de rendimiento, carga ni seguridad más allá de la protección antifalsificación, la "
              "exposición de errores y las credenciales versionadas.",
              "La comparación con el diseño de Figma (MVC-GEN-03) se hizo con el enlace compartido, sin sesión, a "
              "partir de capturas de cada marco. Las revisiones de MVC-GEN-03, MVC-GEN-04, SW-09 y ENT-12 aplican criterios escritos en la matriz que el responsable "
              "de QA debe confirmar."]:
        x.append(para(t, num=True))

    x.append(heading("3.9.6. Conclusión de QA sobre el Pull Request #2", 3))
    x.append(para("La rama feature/frontend-mvc compila sin errores ni advertencias con el SDK 6.0.428, no modifica la "
                  "API REST ni los scripts de base de datos y mantiene los resultados de main en la API, Swagger y el "
                  f"backend. En el frontend se aprobaron {mvc_ok} de los {mvc_ex} casos MVC ejecutados y los 8 casos de "
                  f"integración. Los defectos del frontend ({fe_defs}) son de severidad baja y no impiden el uso "
                  "de las operaciones CRUD."))
    if merged:
        x.append(para("Por lo anterior, QA aprobó el Pull Request #2, que se integró en main el 27 de octubre de 2026 "
                      "mediante el merge commit 8fc7d80. El caso ENT-07 se repitió sobre un clon limpio de main: la "
                      "rama integrada compila sin errores ni advertencias y la aplicación responde correctamente en "
                      "las vistas MVC, la API REST y Swagger. Antes de crear el TAG de entrega conviene corregir los "
                      "defectos de severidad media DEF-01 y DEF-02, que corresponden al backend y al README, repetir "
                      f"ENT-08 y ENT-09 y {cierre}."))
    else:
        x.append(para("Por lo anterior, QA recomienda aprobar e integrar el Pull Request #2 en main. Antes de crear el "
                      "TAG de entrega conviene corregir los defectos de severidad media DEF-01 y DEF-02, que "
                      "corresponden al backend y al README, repetir ENT-07, ENT-08 y ENT-09 sobre main con el "
                      f"frontend integrado y {cierre}."))
    x += correcciones_section()
    return "".join(x)


def correcciones_section():
    """Seccion 3.9.7: rondas de correccion posteriores; lo anterior queda como primera ejecucion."""
    x = [heading("3.9.7. Correcciones y re-pruebas", 3)]
    x.append(para("Los resultados de las secciones 3.9.3 a 3.9.6 corresponden a la primera ejecución de la matriz y "
                  "se conservan sin cambios. Después de esa ejecución, los responsables de cada defecto realizaron "
                  "correcciones en rondas, y QA repitió los casos afectados y la suite completa como regresión. En "
                  "la matriz, cada caso repetido conserva su estado original y suma una nota de re-prueba en "
                  "Observaciones, y cada defecto verificado pasa al estado Verificado. Las evidencias de cada ronda "
                  "están en QA/evidencias/reprueba/."))
    for r in RONDAS:
        if r["estado"] == "Pendiente":
            defs = ", ".join(r["defectos"][:-1]) + " y " + r["defectos"][-1]
            x.append(para([(f"Ronda {r['ronda']}. Correcciones de {r['responsable']}", True)], keep=True))
            x.append(para(f"Pendiente. Esta ronda corresponde a los defectos asignados a {r['responsable']} "
                          f"({defs}). Se completará cuando se integren sus correcciones y QA repita los casos "
                          "afectados."))
            continue
        f = r["fecha"].split("-")
        fecha = f"{int(f[2])} de {MESES[int(f[1])]} de {f[0]}"
        defs = [d for d, _, _ in r["cambios"]]
        n_casos = sum(len(c) for _, _, c in r["cambios"])
        x.append(para([(f"Ronda {r['ronda']}. Correcciones de {r['responsable']} (Pull Request #{r['pr']})", True)],
                      keep=True))
        x.append(para(f"{r['responsable']} corrigió {', '.join(defs[:-1])} y {defs[-1]} en la rama {r['rama']} "
                      f"(commit {r['commit']}). El {fecha}, QA repitió sobre esa rama la suite completa desde un "
                      f"contenedor limpio y los casos de revisión. Los {n_casos} casos asociados a los defectos "
                      f"quedaron aprobados. {r['regresion']} La Tabla X resume los cambios y su verificación.",
                      keep=True))
        rows = [["Defecto", "Corrección", "Casos repetidos", "Resultado"]]
        for d, cambio, casos in r["cambios"]:
            rows.append([d, cambio, ", ".join(casos), "Aprobado; defecto verificado"])
        x.append(table(rows, [1000, 3909, 2000, 1400], size=20, align=["left", "left", "left", "left"]))
        x.append(caption(f"Tabla X. Defectos corregidos en la ronda {r['ronda']} y casos repetidos. Fuente: "
                         "elaboración propia."))
        x.append(para(f"Por lo anterior, QA aprobó el Pull Request #{r['pr']}. Los defectos del documento asignados "
                      f"al mismo responsable (DEF-08 y DEF-11) siguen abiertos."))
    return x


def check_document(path):
    z = zipfile.ZipFile(path)
    doc = z.read("word/document.xml").decode("utf-8")
    paras = ["".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)) for p in re.findall(r"<w:p[ >].*?</w:p>", doc, re.S)]
    want = ["1. Marco conceptual", "2. Diseño", "3. Procedimiento", "3.9. Pruebas de QA", "4. Conclusiones",
            "5. Referencias"]
    found = {w: any(p.strip().startswith(w) for p in paras) for w in want}
    markers = [p for p in paras if p.strip().startswith("*[")]
    fig_x = sum(p.count("Figura X") for p in paras)
    tab_x = sum(p.count("Tabla X") for p in paras)
    prelim = any("referencias preliminares" in p for p in paras)
    images = doc.count("<w:drawing>")
    ev10 = write_evidence("ENT-10", "\n".join(f"{k}: {'presente' if v else 'ausente'}" for k, v in found.items()) +
                          f"\nImagenes en el documento: {images}\nNota de referencias preliminares: {prelim}")
    record("ENT-10", "Aprobado" if all(found.values()) else "Fallido",
           "La copia _QA incluye marco conceptual, diseño, procedimiento, pruebas con evidencias (3.9), conclusiones y "
           "referencias.", ev10,
           "Las referencias están marcadas como preliminares. Sin el enunciado oficial, la lista de secciones exigidas "
           "se tomó de R11.")
    ev11 = write_evidence("ENT-11", "Marcadores sin completar:\n" + "\n".join(markers) +
                          f"\n\nPies con 'Figura X': {fig_x}\nPies con 'Tabla X': {tab_x}")
    record("ENT-11", "Fallido" if markers or fig_x else "Aprobado",
           f"Quedan {len(markers)} marcadores de captura sin completar fuera de la sección 3.9 y {fig_x} pies de "
           "figura con 'Figura X'.", ev11,
           "La sección 3.9 incluye sus capturas, que corresponden a pruebas ejecutadas.")
    return found, markers, fig_x


def main(src, dst):
    st, rows, tot = stats()
    zin = zipfile.ZipFile(src)
    parts = {i.filename: zin.read(i.filename) for i in zin.infolist()}
    doc = parts["word/document.xml"].decode("utf-8")
    rels = parts["word/_rels/document.xml.rels"].decode("utf-8")
    imgs = [("EV-SW-01.png", 900), ("EV-MVC-PER-02.png", None), ("EV-MVC-PER-08.png", None),
            ("EV-BK-09-vista.png", None)]
    rids = []
    for i, (name, crop) in enumerate(imgs, 1):
        im = Image.open(os.path.join(EVID, name)).convert("RGB")
        if crop:
            im = im.crop((0, 0, im.width, min(crop, im.height)))
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
        parts[f"word/media/imageQA{i}.png"] = buf.getvalue()
        rid = f"rIdQA{i}"
        rels = rels.replace("</Relationships>", f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
                            f'officeDocument/2006/relationships/image" Target="media/imageQA{i}.png"/></Relationships>')
        rids.append(rid)
    parts["word/_rels/document.xml.rels"] = rels.encode()
    ct = parts["[Content_Types].xml"].decode("utf-8")
    if 'Extension="png"' not in ct:
        ct = ct.replace("<Default ", '<Default Extension="png" ContentType="image/png"/><Default ', 1)
        parts["[Content_Types].xml"] = ct.encode()

    anchor = re.search(r'<w:p [^>]*>(?:(?!</w:p>).)*?4\. Conclusiones y lecciones aprendidas.*?</w:p>', doc, re.S)
    start = doc.rfind("<w:p ", 0, anchor.end() - len(anchor.group(0)) + anchor.group(0).rfind("<w:p "))
    start = anchor.start() + anchor.group(0).rfind("<w:p ")
    doc = doc[:start] + build_section(st, rows, tot, rids) + doc[start:]
    parts["word/document.xml"] = doc.encode()

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    found, markers, fig_x = check_document(dst)
    print("Tabla por area:", rows)
    print("Secciones:", found, "| marcadores:", len(markers), "| Figura X:", fig_x)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
