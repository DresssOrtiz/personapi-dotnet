# Scripts de QA

Scripts que ejecutan los casos automatizables de la matriz de pruebas. No forman parte del código de la
aplicación y no la modifican.

## Requisitos

- Docker (SQL Server 2022 según el README del repositorio).
- SDK de .NET 6 en `~/.dotnet6` (o la variable `DOTNET6` con la ruta del ejecutable).
- Python 3 con `pip install -r QA/tests/requirements.txt` y `python -m playwright install chromium`.
- `gh` autenticado (colaboradores y estado del Pull Request).
- LibreOffice (recálculo de la matriz).

## Ejecución (desde la raíz del repositorio)

```bash
PY=python3 bash QA/tests/run_all.sh
python3 QA/tests/documento/seccion_3_9.py "<documento original>.docx" "QA/<documento>_QA.docx"
python3 QA/tests/matriz/actualizar_matriz.py "<matriz original>.xlsx" QA/Matriz_Pruebas_Laboratorio1_QA.xlsx
```

`run_all.sh` elimina y recrea el contenedor `persona-sql`. Los resultados quedan en `QA/tests/results/`
(un JSON por caso) y las evidencias en `QA/evidencias/` con el ID del caso en el nombre.
Con `QA_REPO_FRONTEND=<clon>` se prueba el frontend de otro clon y se repiten allí la API, Swagger y el
backend como regresión.

| Carpeta | Casos |
|---|---|
| `db/` | BD-01 a BD-25 (sqlcmd dentro del contenedor) |
| `backend/` | BK-01 a BK-08 |
| `api/` | API-*, SW-01 a SW-08 (requests, openapi-spec-validator, Playwright) |
| `mvc/` | MVC-*, INT-01 a INT-08, BK-09 (Playwright), navegadores (MVC-GEN-05) y apoyo visual |
| `revision/` | MVC-GEN-03, MVC-GEN-04, SW-09 y ENT-12 (revisiones asistidas) |
| `entrega/` | ENT-01 a ENT-09, API-GEN-06 (`--solo ENT-07` repite solo ese caso) |
| `documento/` | Sección 3.9 del documento, ENT-10 y ENT-11 |
| `matriz/` | Defectos y actualización de la matriz conservando validaciones y fórmulas |

Requiere además `python -m playwright install firefox webkit` para `mvc/navegadores.py`.
