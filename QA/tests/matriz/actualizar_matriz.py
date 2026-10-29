"""Actualiza la matriz de QA con los resultados de QA/tests/results sin perder validaciones ni formatos.

Uso: python QA/tests/matriz/actualizar_matriz.py ORIGEN.xlsx SALIDA_QA.xlsx

1. Edita directamente el XML de las hojas 'Casos de prueba' (solo columnas K a P)
   y 'Defectos', conservando el estilo de cada celda. El resto del paquete queda
   identico, incluidas las listas desplegables (tambien las x14 entre hojas) y el
   formato condicional.
2. Recalcula una copia con LibreOffice (perfil temporal con OOXMLRecalcMode=0).
3. Copia los valores calculados a las celdas con formula del archivo editado.
4. Verifica: formulas y validaciones identicas al original y cero errores.
"""
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from xml.sax.saxutils import escape

import openpyxl

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from correcciones import casos_reprobados, estados, prs_texto  # noqa: E402
from defectos import DEFECTOS  # noqa: E402
from lib import RESULTS  # noqa: E402

SOFFICE = os.environ.get("SOFFICE", "/Applications/LibreOffice.app/Contents/MacOS/soffice")
SHEET_CASES, SHEET_DEFECTS = "xl/worksheets/sheet3.xml", "xl/worksheets/sheet4.xml"
COLS = {"estado": "K", "obtenido": "L", "evidencia": "M", "fecha": "N", "responsable": "O", "observaciones": "P"}

# Tildes para los textos generados por los scripts (escritos en ASCII). Solo se
# aplican a palabras completas que no forman parte de identificadores.
ACCENTS = {
    "aplicacion": "aplicación", "pagina": "página", "paginas": "páginas", "codigo": "código",
    "validacion": "validación", "validaciones": "validaciones", "eliminacion": "eliminación",
    "creacion": "creación", "edicion": "edición", "conexion": "conexión", "ejecucion": "ejecución",
    "documentacion": "documentación", "descripcion": "descripción", "descripciones": "descripciones",
    "restriccion": "restricción", "excepcion": "excepción", "excepciones": "excepciones",
    "configuracion": "configuración", "navegacion": "navegación", "recreacion": "recreación",
    "operacion": "operación", "condicion": "condición", "correccion": "corrección", "seccion": "sección",
    "revision": "revisión", "version": "versión", "despues": "después", "tambien": "también",
    "numero": "número", "numeros": "números", "telefono": "teléfono", "telefonos": "teléfonos",
    "profesion": "profesión", "huerfanos": "huérfanos", "metodo": "método", "metodos": "métodos",
    "unica": "única", "unico": "único", "maximo": "máximo", "maxima": "máxima", "minimo": "mínimo",
    "vacio": "vacío", "vacia": "vacía", "caida": "caída", "cedula": "cédula", "cedulas": "cédulas",
    "digitos": "dígitos", "segun": "según", "aun": "aún", "decision": "decisión", "diseno": "diseño",
    "envio": "envío", "solo": "solo", "automatizado": "automatizado", "rapido": "rápido",
    "informacion": "información", "publicacion": "publicación", "comprobacion": "comprobación",
    "comprobaciones": "comprobaciones", "tecnico": "técnico", "tecnicos": "técnicos", "pagina,": "página,",
    "esta abierto": "está abierto", "estan": "están", "esta expuesto": "está expuesto",
    "esta fuera": "está fuera", "no esta": "no está", "Telefono, estudio, profesion y persona":
    "Teléfono, estudio, profesión y persona", "Pagina": "Página", "Codigo": "Código", "Cedula": "Cédula", "Genero,": "Género,",
    "Despues": "Después", "Formulario vacio": "Formulario vacío", "pila de llamadas": "pila de llamadas",
    "condicion de carrera": "condición de carrera", "modulos": "módulos", "Modulos": "Módulos",
    "menu": "menú", "electronico": "electrónico", "logica": "lógica", "titulo": "título",
    "dbcreator": "dbcreator", "Recalculo": "Recálculo", "busqueda": "búsqueda", "mas": "más",
    "Direccion": "Dirección", "accion": "acción", "alteracion": "alteración",
    "aprobacion": "aprobación", "autenticacion": "autenticación", "codigos": "códigos", "compilacion": "compilación",
    "contrasena": "contraseña", "conversion": "conversión", "especifico": "específico", "generica": "genérica",
    "instruccion": "instrucción", "ningun": "ningún", "omision": "omisión", "opcion": "opción",
    "pluralizacion": "pluralización", "precondicion": "precondición", "Revision": "Revisión",
    "simultaneos": "simultáneos", "simultaneas": "simultáneas", "todavia": "todavía", "valido": "válido",
    "Andres": "Andrés", "Tomas Ramirez": "Tomás Ramírez", "Santiago Hernandez": "Santiago Hernández",
    "integracion": "integración", "regresion": "regresión", "proteccion": "protección", "tamanos": "tamaños", "direccion": "dirección", "extension": "extensión", "region": "región",
}
_ACC_RE = re.compile(r"(?<![\w/_-])(?<!\w\.)(" + "|".join(sorted(map(re.escape, ACCENTS), key=len, reverse=True))
                     + r")(?![\w/_(-])(?!\.\w)")


def accent(text):
    """Agrega tildes fuera de las comillas dobles, que reproducen mensajes literales de la aplicacion."""
    parts = re.split(r'("[^"]*")', text or "")
    return "".join(p if p.startswith('"') else _ACC_RE.sub(lambda m: ACCENTS[m.group(1)], p) for p in parts)


def excel_serial(iso):
    d = datetime.date.fromisoformat(iso)
    return (d - datetime.date(1899, 12, 30)).days


def shared_strings(z):
    root = z.read("xl/sharedStrings.xml").decode("utf-8")
    items = re.findall(r"<si>(.*?)</si>", root, re.S)
    return ["".join(re.findall(r"<t[^>]*>(.*?)</t>", it, re.S)) for it in items]


def set_cell(row_xml, ref, value, kind="str"):
    """Reemplaza la celda ref conservando su atributo de estilo."""
    m = re.search(rf'<c r="{ref}"(?P<attrs>[^>]*?)(?:/>|>.*?</c>)', row_xml, re.S)
    if not m:
        raise KeyError(ref)
    style = re.search(r'\ss="(\d+)"', m.group("attrs"))
    s = f' s="{style.group(1)}"' if style else ""
    if value in (None, ""):
        new = f'<c r="{ref}"{s}/>'
    elif kind == "num":
        new = f'<c r="{ref}"{s}><v>{value}</v></c>'
    else:
        new = f'<c r="{ref}"{s} t="inlineStr"><is><t xml:space="preserve">{escape(str(value))}</t></is></c>'
    return row_xml[:m.start()] + new + row_xml[m.end():]


def set_style(row_xml, ref, style):
    return re.sub(rf'(<c r="{ref}") s="\d+"', rf'\1 s="{style}"', row_xml)


def load_results():
    res = {}
    for f in glob.glob(os.path.join(RESULTS, "*.json")):
        if not re.fullmatch(r"[A-Z]+(-[A-Z0-9]+)+\.json", os.path.basename(f)):
            continue  # ignora copias de sincronizacion como "BD-01 2.json"
        d = json.load(open(f, encoding="utf-8"))
        res[d["id"]] = d
    reg_path = os.path.join(RESULTS, "regresion-frontend.txt")
    reg = {}
    if os.path.exists(reg_path):
        for line in open(reg_path, encoding="utf-8"):
            m = re.match(r"\[(\w[\w ]*?)\s*\] ([A-Z]+-[A-Z0-9-]+) \(frontend\)", line)
            if m:
                reg[m.group(2)] = m.group(1)
    return res, reg


def build_rows(sheet_xml):
    return {int(m.group(1)): m for m in re.finditer(r'<row [^>]*r="(\d+)"[^>]*>(.*?)</row>', sheet_xml, re.S)}


def update_cases(sheet_xml, strings, res, reg):
    case_def = {c: d["id"] for d in DEFECTOS for c in d["casos"]}
    out, last, n = [], 0, 0
    for m in re.finditer(r'(<row [^>]*r="(\d+)"[^>]*>)(.*?)(</row>)', sheet_xml, re.S):
        out.append(sheet_xml[last:m.start()])
        head, rnum, body, tail = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        a = re.search(rf'<c r="A{rnum}"[^>]*t="s"[^>]*><v>(\d+)</v>', body)
        cid = strings[int(a.group(1))] if a and rnum > 1 else None
        if cid in res:
            r = res[cid]
            obs = r["observaciones"]
            if cid in reg:
                same = reg[cid] == r["estado"]
                obs = (obs + " " if obs else "") + (
                    "Regresión en feature/frontend-mvc (eea9ee8): mismo resultado." if same else
                    f"Regresión en feature/frontend-mvc (eea9ee8): {reg[cid]}.")
            if cid in case_def:
                obs = (obs + " " if obs else "") + f"Defecto {case_def[cid]}."
            if cid in casos_reprobados():
                obs += " " + nota_reprueba(cid, casos_reprobados()[cid])
            body = set_cell(body, f"K{rnum}", r["estado"])
            body = set_cell(body, f"L{rnum}", accent(r["obtenido"]))
            body = set_cell(body, f"M{rnum}", r["evidencia"])
            body = set_cell(body, f"N{rnum}", excel_serial(r["fecha"]) if r["estado"] != "Pendiente" else "", "num")
            body = set_cell(body, f"O{rnum}", r["responsable"])
            body = set_cell(body, f"P{rnum}", accent(obs))
            n += 1
        out.append(head + body + tail)
        last = m.end()
    out.append(sheet_xml[last:])
    return "".join(out), n


def nota_reprueba(cid, ronda):
    """Nota de re-prueba para Observaciones; el estado de la primera ejecucion no cambia."""
    f = os.path.join(RESULTS, "..", "reprueba", f"ronda-{ronda['ronda']}", f"{cid}.json")
    estado = json.load(open(f, encoding="utf-8"))["estado"]
    d = datetime.date.fromisoformat(ronda["fecha"])
    return (f"Re-prueba ronda {ronda['ronda']} ({d:%d/%m/%Y}, {prs_texto(ronda['prs'])}): {estado}. "
            f"Evidencia en reprueba/ronda-{ronda['ronda']}/EV-R{ronda['ronda']}-{cid}.*.")


def update_defects(sheet_xml, today):
    rows = build_rows(sheet_xml)
    normal = {c: re.search(rf'<c r="{c}3" s="(\d+)"', rows[3].group(2)).group(1) for c in "ABCDEFGHIJKLM"}
    out, last = [], 0
    for m in re.finditer(r'(<row [^>]*r="(\d+)"[^>]*>)(.*?)(</row>)', sheet_xml, re.S):
        out.append(sheet_xml[last:m.start()])
        head, rnum, body, tail = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        idx = rnum - 2
        if 0 <= idx < len(DEFECTOS):
            d = DEFECTOS[idx]
            estado, ver = estados().get(d["id"], ("Abierto", None))
            obs = accent(d["observaciones"])
            if ver:
                f = datetime.date.fromisoformat(ver["fecha"])
                obs += (f" Corregido por {ver['responsable']} ({prs_texto(ver['prs'])}) y " + (
                        f"verificado por QA el {f:%d/%m/%Y}" if estado == "Verificado" else
                        f"comprobado por QA el {f:%d/%m/%Y} solo en parte") + f" en la re-prueba ronda {ver['ronda']}.")
                if d["id"] == "DEF-05" and estado == "Corregido":
                    obs += " Falta ejecutar BD-07 en Windows con SQL Server Express o LocalDB."
            for c in "ABCDEFGHIJKLM":
                body = set_style(body, f"{c}{rnum}", normal[c])
            vals = {"A": d["id"], "C": ", ".join(d["casos"]), "D": d["req"], "E": d["area"],
                    "F": accent(d["descripcion"]), "G": accent(d["pasos"]), "H": accent(d["esperado"]),
                    "I": d["severidad"], "J": estado, "K": d["responsable"],
                    "L": d["evidencia"], "M": obs}
            body = set_cell(body, f"B{rnum}", excel_serial(today), "num")
            for c, v in vals.items():
                body = set_cell(body, f"{c}{rnum}", v)
        out.append(head + body + tail)
        last = m.end()
    out.append(sheet_xml[last:])
    return "".join(out)


def recalc_with_libreoffice(src, workdir):
    profile = os.path.join(workdir, "lo-profile")
    os.makedirs(os.path.join(profile, "user"), exist_ok=True)
    with open(os.path.join(profile, "user", "registrymodifications.xcu"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<oor:items xmlns:oor="http://openoffice.org/2001/registry" '
                'xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
                '<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="OOXMLRecalcMode" '
                'oor:op="fuse"><value>0</value></prop></item>\n</oor:items>\n')
    outdir = os.path.join(workdir, "lo-out")
    p = subprocess.run([SOFFICE, f"-env:UserInstallation=file://{profile}", "--headless", "--calc",
                        "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", outdir, src],
                       capture_output=True, text=True, timeout=300)
    out = os.path.join(outdir, os.path.basename(src))
    if not os.path.exists(out):
        raise RuntimeError(p.stdout + p.stderr)
    return out


def inject_cached(sheet_xml, values):
    """values: {ref: valor calculado}. Actualiza <v> y el tipo de las celdas con formula."""
    def repl(m):
        ref, attrs, f = m.group(1), m.group(2), m.group(3)
        if ref not in values:
            return m.group(0)
        v = values[ref]
        attrs = re.sub(r'\st="\w+"', "", attrs)
        if isinstance(v, str):
            return f'<c r="{ref}"{attrs} t="str">{f}<v>{escape(v)}</v></c>'
        if isinstance(v, bool):
            return f'<c r="{ref}"{attrs} t="b">{f}<v>{int(v)}</v></c>'
        return f'<c r="{ref}"{attrs}>{f}<v>{v}</v></c>'
    return re.sub(r'<c r="([A-Z]+\d+)"([^>]*)>(<f>.*?</f>|<f [^>]*/>|<f [^>]*>.*?</f>)(?:<v>.*?</v>)?</c>', repl,
                  sheet_xml, flags=re.S)


def formulas(xml):
    """Celdas con formula, incluidas las compartidas (<f t="shared" .../>)."""
    return re.findall(r'<c r="([A-Z]+\d+)"[^>]*>(<f>.*?</f>|<f [^>]*/>|<f [^>]*>.*?</f>)', xml, re.S)


def validations(xml):
    dv = re.findall(r"<dataValidations.*?</dataValidations>", xml, re.S)
    x14 = re.findall(r"<x14:dataValidations.*?</x14:dataValidations>", xml, re.S)
    cf = re.findall(r"<conditionalFormatting.*?</conditionalFormatting>", xml, re.S)
    return dv, x14, cf


def main(src, dst):
    today = datetime.date.today().isoformat()
    res, reg = load_results()
    work = tempfile.mkdtemp(prefix="qa-matriz-")
    zin = zipfile.ZipFile(src)
    parts = {n: zin.read(n) for n in zin.namelist()}
    strings = shared_strings(zin)

    cases_xml, n = update_cases(parts[SHEET_CASES].decode("utf-8"), strings, res, reg)
    defects_xml = update_defects(parts[SHEET_DEFECTS].decode("utf-8"), today)
    wb_xml = parts["xl/workbook.xml"].decode("utf-8")
    if "fullCalcOnLoad" not in wb_xml:
        wb_xml = wb_xml.replace("<calcPr ", '<calcPr fullCalcOnLoad="1" ', 1)
    edited = {**parts, SHEET_CASES: cases_xml.encode(), SHEET_DEFECTS: defects_xml.encode(),
              "xl/workbook.xml": wb_xml.encode()}

    def write(path, contents):
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for info in zin.infolist():
                z.writestr(info, contents[info.filename])

    stage = os.path.join(work, os.path.basename(dst))
    write(stage, edited)
    recalced = recalc_with_libreoffice(stage, work)

    wb_calc = openpyxl.load_workbook(recalced, data_only=True)
    errors = [f"{ws.title}!{c.coordinate}={c.value}" for ws in wb_calc for row in ws.iter_rows() for c in row
              if isinstance(c.value, str) and re.match(r"^#(REF!|VALUE!|DIV/0!|NAME\?|N/A|NUM!|NULL!)", c.value)]
    sheet_files = {"Resumen": "xl/worksheets/sheet1.xml", "Requisitos": "xl/worksheets/sheet2.xml",
                   "Casos de prueba": SHEET_CASES, "Defectos": SHEET_DEFECTS}
    for title, part in sheet_files.items():
        xml = edited[part].decode("utf-8")
        refs = [r for r, _ in formulas(xml)]
        values = {r: wb_calc[title][r].value for r in refs}
        edited[part] = inject_cached(xml, values).encode()
    write(dst, edited)

    # Verificacion contra el original
    report = []
    for part in sheet_files.values():
        o, e = parts[part].decode("utf-8"), edited[part].decode("utf-8")
        report.append(f"{part}: formulas iguales={formulas(o) == formulas(e)}, "
                      f"validaciones y formato condicional iguales={validations(o) == validations(e)}")
    unchanged = [n2 for n2 in parts if n2 not in sheet_files.values() and n2 != "xl/workbook.xml"
                 and parts[n2] != edited[n2]]
    wb_final = openpyxl.load_workbook(dst, data_only=True)
    summary = {wb_final["Resumen"][f"A{i}"].value: wb_final["Resumen"][f"B{i}"].value for i in range(6, 16)}
    areas = [[wb_final["Resumen"].cell(r, c).value for c in range(1, 8)] for r in range(20, 28)]
    shutil.rmtree(work, ignore_errors=True)
    print(f"Filas actualizadas: {n}; defectos: {len(DEFECTOS)}")
    print("\n".join(report))
    print(f"Otras partes modificadas: {unchanged or 'ninguna'}")
    print(f"Errores de formula tras recalcular: {errors or 'ninguno'}")
    print("Resumen:", json.dumps(summary, ensure_ascii=False, default=str))
    for a in areas:
        print("  ", a)
    return not errors and not unchanged


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1], sys.argv[2]) else 1)
