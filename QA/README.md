# QA - Laboratorio 1

Documentación de la validación independiente de QA del Laboratorio 1 (monolito ASP.NET Core MVC con
patrón DAO). Responsable de QA: Santiago Hernández. Fecha de ejecución: 27 de octubre de 2026.

## Contenido

| Archivo o carpeta | Descripción |
|---|---|
| `Matriz_Pruebas_Laboratorio1_QA.xlsx` | Matriz de 165 casos con estado, resultado obtenido, evidencia, fecha, responsable y observaciones; hoja Defectos con 8 defectos. |
| `Laboratorio 1 — ..._QA.docx` | Copia del documento del laboratorio con la sección 3.9 "Pruebas de QA" completa. |
| `evidencias/` | Salidas y capturas de cada caso (`EV-<ID>.txt` / `EV-<ID>.png`). `pantallas/` reúne las 21 vistas para comparar con Figma. |
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
| Swagger | 9 | 8 | 0 | 0 | 1 |
| Frontend MVC | 40 | 31 | 6 | 0 | 3 |
| Integración | 8 | 8 | 0 | 0 | 0 |
| Repositorio y entrega | 12 | 8 | 2 | 1 | 1 |
| **Total** | **165** | **147** | **11** | **2** | **5** |

Avance de ejecución: 95,8 %. Tasa de aprobación sobre ejecutados: 93,0 %.

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

Los pasos para reproducir, el resultado esperado frente al obtenido y la corrección propuesta de cada
defecto están en la hoja Defectos de la matriz.

## Pendientes

- Casos manuales: MVC-GEN-03 (comparación con Figma), MVC-GEN-04 (tamaños de pantalla), MVC-GEN-05
  (navegadores), SW-09 (claridad de Swagger) y ENT-12 (formato del documento).
- Casos bloqueados: BD-07 (requiere Windows con SQL Server Express o LocalDB) y ENT-09 (TAG de entrega).
- Antes del TAG: corregir DEF-01 y DEF-02 y repetir ENT-08 y ENT-09.
