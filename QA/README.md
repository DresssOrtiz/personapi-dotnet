# QA - Laboratorio 1

Documentación de la validación independiente de QA del Laboratorio 1 (monolito ASP.NET Core MVC con
patrón DAO). Responsable de QA: Santiago Hernández. Fecha de ejecución: 27 de octubre de 2026.

## Contenido

| Archivo o carpeta | Descripción |
|---|---|
| `Matriz_Pruebas_Laboratorio1_QA.xlsx` | Matriz de 165 casos con estado, resultado obtenido, evidencia, fecha, responsable y observaciones; hoja Defectos con 11 defectos. |
| `Laboratorio 1 — ..._QA.docx` | Copia del documento del laboratorio con la sección 3.9 "Pruebas de QA" completa. |
| `evidencias/` | Salidas y capturas de cada caso (`EV-<ID>.txt` / `EV-<ID>.png`). `pantallas/` reúne las 21 vistas implementadas y `figma/` los marcos del diseño con un comparativo por pantalla. |
| `tests/` | Scripts de pruebas automatizadas y resultados por caso. Ver `tests/README.md`. |

## Alcance

- `main` antes de la integración (0595eab), rama `feature/frontend-mvc` del Pull Request #2 (eea9ee8) y
  `main` integrada (8fc7d80) para ENT-07.
- Entorno: macOS (Apple Silicon), SQL Server 2022 Developer 16.0.4305.5 en Docker, .NET SDK 6.0.428
  (runtime 6.0.36), EF Core 6.0.36, Swashbuckle 6.5.0, Python 3.14 con Playwright (Chromium).

## Resultados

| Área | Total | Aprobados | Fallidos | Bloqueados | Pendientes |
|---|---|---|---|---|---|
| Base de datos | 25 | 23 | 1 | 1 | 0 |
| Backend y DAO | 9 | 8 | 1 | 0 | 0 |
| API REST | 62 | 61 | 1 | 0 | 0 |
| Swagger | 9 | 8 | 1 | 0 | 0 |
| Frontend MVC | 40 | 34 | 6 | 0 | 0 |
| Integración | 8 | 8 | 0 | 0 | 0 |
| Repositorio y entrega | 12 | 8 | 3 | 1 | 0 |
| **Total** | **165** | **150** | **13** | **2** | **0** |

Avance de ejecución: 98,8 %. Tasa de aprobación sobre ejecutados: 92,0 %.

Los casos de revisión (MVC-GEN-03, MVC-GEN-04, MVC-GEN-05, SW-09 y ENT-12) se ejecutaron sobre `main`
integrada: MVC-GEN-03 comparando las 21 pantallas con los marcos del diseño de Figma; MVC-GEN-05 con
Playwright en Chromium (motor de Chrome y Edge), Firefox y WebKit; MVC-GEN-04, SW-09 y ENT-12 con
mediciones automáticas. En las revisiones queda escrito en la matriz un criterio que el responsable de QA
debe confirmar.

## Defectos

| ID | Caso(s) | Severidad | Descripción | Responsable |
|---|---|---|---|---|
| DEF-01 | API-GEN-05 | Media | Dos POST simultáneos con la misma clave devuelven 500 en lugar de 409. | Tomás |
| DEF-02 | ENT-08 | Media | El comando de despliegue del README no carga `appsettings.json` y la aplicación responde 500. | Tomás |
| DEF-03 | BK-09 | Baja | Con SQL Server detenido, la API devuelve la traza de la excepción. | Tomás |
| DEF-04 | BD-08 | Baja | Re-ejecutar el DDL borra las tablas y sus datos sin advertencia en el README. | Tomás |
| DEF-05 | BD-07 | Baja | `ALTER AUTHORIZATION ... TO sa` falla sin permisos sobre `sa`; el ajuste para LocalDB no está documentado. | Tomás |
| DEF-06 | MVC-*-05, MVC-GEN-07 | Baja | Las claves y rutas inexistentes devuelven 404 sin página propia. | Andrés |
| DEF-07 | MVC-PER-01 | Baja | El listado de personas no muestra la edad. | Andrés |
| DEF-08 | ENT-11 | Baja | El documento conserva marcadores de captura y figuras sin numerar. | Andrés |
| DEF-09 | MVC-GEN-04 | Baja | Los formularios de creación de personas y profesiones muestran un recuadro de error vacío. | Andrés |
| DEF-10 | SW-09 | Baja | Swagger no muestra resúmenes ni descripciones de operaciones y campos. | Tomás |
| DEF-11 | ENT-12 | Baja | El documento aplica el estilo Título 2 a párrafos de cuerpo y sus referencias están incompletas. | Andrés |

Los pasos para reproducir, el resultado esperado frente al obtenido y la corrección propuesta de cada
defecto están en la hoja Defectos de la matriz.

## Correcciones y re-pruebas

Los resultados anteriores son los de la primera ejecución y no se modifican. Cada ronda de correcciones se
registra en `tests/matriz/correcciones.py`; en la matriz, los casos repetidos suman una nota de re-prueba en
Observaciones y los defectos verificados pasan a Verificado. Las evidencias están en `evidencias/reprueba/`.

| Ronda | Responsable | Pull Request | Defectos | Casos repetidos | Resultado |
|---|---|---|---|---|---|
| 1 (28/10/2026) | Andrés | #7 (6a0edac) | DEF-06, DEF-07, DEF-09 | MVC-PER-01, MVC-*-05, MVC-GEN-07, MVC-GEN-04 | Aprobados; defectos verificados, sin regresiones |
| 2 | Tomás | Pendiente | DEF-01, DEF-02, DEF-03, DEF-04, DEF-05, DEF-10 | Pendiente | Pendiente |

DEF-08 y DEF-11 (documento, Andrés) siguen abiertos.

## Pendientes

- Casos bloqueados: BD-07 (requiere Windows con SQL Server Express o LocalDB) y ENT-09 (TAG de entrega).
- Confirmar el criterio de las revisiones asistidas MVC-GEN-03, MVC-GEN-04, SW-09 y ENT-12.
- Ronda 2 (Tomás): corregir DEF-01 y DEF-02 y repetir ENT-08 y ENT-09.
