"""Convierte la seccion 3.9 de la copia _QA.docx en HTML para pegarla en Google Docs.

Uso: python QA/tests/documento/seccion_3_9_gdocs.py "QA/<documento>_QA.docx" RAMA
Requiere pandoc. Escribe QA/tests/documento/seccion_3_9_gdocs.html y las figuras en
QA/evidencias/figuras/. Las imagenes se referencian con su URL de GitHub en la rama
indicada, para que Google Docs las descargue al pegar.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
QA = os.path.abspath(os.path.join(HERE, "..", ".."))
FIGS = os.path.join(QA, "evidencias", "figuras")
RAW = "https://raw.githubusercontent.com/DresssOrtiz/personapi-dotnet/{branch}/QA/evidencias/figuras/{name}"
FONT = "font-family:'Times New Roman',serif;"
NAMES = {"imageQA1.png": "FIG-3.9-1-SW-01.png", "imageQA2.png": "FIG-3.9-2-MVC-PER-02.png",
         "imageQA3.png": "FIG-3.9-3-MVC-PER-08.png", "imageQA4.png": "FIG-3.9-4-BK-09.png"}


def main(docx, branch):
    tmp = tempfile.mkdtemp(prefix="qa-gdocs-")
    try:
        subprocess.run(["pandoc", docx, "-t", "html", f"--extract-media={tmp}", "-o", os.path.join(tmp, "full.html")],
                       check=True)
        html = open(os.path.join(tmp, "full.html"), encoding="utf-8").read()
        a = html.rfind("<", 0, html.index("3.9. Pruebas de QA"))
        b = html.rfind("<h", 0, html.index("4. Conclusiones y lecciones"))
        s = html[a:b]
        os.makedirs(FIGS, exist_ok=True)
        for src, dst in NAMES.items():
            shutil.copy(os.path.join(tmp, "media", src), os.path.join(FIGS, dst))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    s = re.sub(r"\s+id=\"[^\"]*\"", "", s)
    s = s.replace("<blockquote>", "").replace("</blockquote>", "")
    s = re.sub(r"<img\s+src=\"[^\"]*/(imageQA\d\.png)\"[^>]*>",
               lambda m: f'<img src="{RAW.format(branch=branch, name=NAMES[m.group(1)])}" '
                         f'style="width:430pt;height:auto">', s)
    s = re.sub(r"<p>\s*(<img [^>]+>)\s*</p>", r'<p style="text-align:center;margin-left:36pt">\1</p>', s)
    # Pies de figura y de tabla centrados; cuerpo con la sangria de la seccion 3.8.
    s = re.sub(r"<p>((?:Figura|Tabla) X\..*?)</p>",
               lambda m: f'<p style="{FONT}font-size:11pt;text-align:center">{m.group(1)}</p>', s, flags=re.S)
    s = re.sub(r"<p>", f'<p style="{FONT}font-size:12pt;margin-left:36pt">', s)
    s = re.sub(r"<li>", f'<li style="{FONT}font-size:12pt">', s)
    s = re.sub(r"<h([23])>", lambda m: f'<h{m.group(1)} style="{FONT}font-size:12pt">', s)
    s = re.sub(r"<table[^>]*>", '<table style="border-collapse:collapse;width:430pt">', s)
    s = re.sub(r"<colgroup>.*?</colgroup>", "", s, flags=re.S)
    cell = f"border:1px solid #808080;padding:2pt 4pt;{FONT}font-size:10pt;"
    s = re.sub(r"</?(thead|tbody)>", "", s)
    s = re.sub(r"<th(\s[^>]*)?>", f'<th style="{cell}background-color:#d9d9d9;text-align:center">', s)
    s = re.sub(r"<td style=\"text-align: center;\">", f'<td style="{cell}text-align:center">', s)
    s = re.sub(r"<td>", f'<td style="{cell}">', s)
    s = s.replace("<td style=\"text-align: left;\">", f'<td style="{cell}">')
    # Anchos fijos por columna (pt); el ancho util con la sangria de 36 pt es de unos 415 pt.
    widths = iter([[130, 285], [105, 40, 55, 50, 60, 60, 45], [45, 75, 50, 185, 60], [50, 195, 100, 70], [50, 195, 100, 70], [50, 195, 100, 70]])

    def size_table(m):
        cols = next(widths)
        table = m.group(0).replace("width:430pt", f"width:{sum(cols)}pt;table-layout:fixed")

        def size_row(r):
            k = iter(range(len(cols)))
            return re.sub(r"<(t[hd]) style=\"",
                          lambda c: (lambda i: f'<{c.group(1)} width="{round(cols[i] * 4 / 3)}" '
                                               f'style="width:{cols[i]}pt;')(next(k)), r.group(0))
        return re.sub(r"<tr[^>]*>.*?</tr>", size_row, table, flags=re.S)
    s = re.sub(r"<table.*?</table>", size_table, s, flags=re.S)
    s = re.sub(r"</?(thead|tbody)>", "", s)
    # Cada celda en un parrafo propio sin sangria: Google Docs aplica a las celdas la sangria del
    # parrafo anterior si el contenido no trae la suya.
    s = re.sub(r"(<t[hd] [^>]*?text-align:(\w+)[^>]*>|<t[hd] [^>]*>)(.*?)(</t[hd]>)",
               lambda m: f'{m.group(1)}<p style="margin:0;text-indent:0;{FONT}font-size:10pt;'
                         f'text-align:{m.group(2) or "left"}">{m.group(3).strip()}</p>{m.group(4)}', s, flags=re.S)
    out = os.path.join(HERE, "seccion_3_9_gdocs.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write("<meta charset=\"utf-8\">" + s)
    print(out, len(s), "caracteres;", len(re.findall(r"<img ", s)), "imágenes;", len(re.findall(r"<table", s)), "tablas")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
