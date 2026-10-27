#!/usr/bin/env bash
# Corrida completa de los casos automatizados de la matriz de QA.
# Uso, desde la raiz del repositorio: PY=python3 bash QA/tests/run_all.sh
# Requisitos: Docker, SDK de .NET 6 en ~/.dotnet6 (o DOTNET6), Python con
# QA/tests/requirements.txt y Chromium de Playwright, gh autenticado.
# QA_REPO_FRONTEND (opcional): clon con una rama de frontend distinta de la actual;
# si se define, la API, Swagger y el backend se repiten alli como regresion.
# ATENCION: elimina y recrea el contenedor persona-sql.
set -u
cd "$(dirname "$0")/../.."
ROOT="$PWD"
FRONT="${QA_REPO_FRONTEND:-$ROOT}"
PY="${PY:-python3}"
DOTNET="${DOTNET6:-$HOME/.dotnet6/dotnet}"
export DOTNET_ROOT="$(dirname "$DOTNET")" DOTNET_CLI_TELEMETRY_OPTOUT=1
RES="$ROOT/QA/tests/results"
LOGS="$RES/logs"
rm -rf "$RES" && mkdir -p "$LOGS"

wait_url() { for _ in $(seq 1 90); do curl -s -o /dev/null "$1" && return 0; sleep 2; done; return 1; }
stop_app() { kill $(lsof -ti tcp:5025 -sTCP:LISTEN) 2>/dev/null; sleep 3; }
start_app() {
  (cd "$1/personapi-dotnet" && nohup "$DOTNET" run --urls http://localhost:5025 > "$2" 2>&1 &)
  wait_url http://localhost:5025/
}

echo "== SQL Server (comando del README)"
docker rm -f persona-sql >/dev/null 2>&1
docker run -d --name persona-sql --platform linux/amd64 \
  -e ACCEPT_EULA=Y -e 'MSSQL_SA_PASSWORD=Persona_Lab1#2026' \
  -p 1433:1433 mcr.microsoft.com/mssql/server:2022-latest >/dev/null
for _ in $(seq 1 60); do
  docker exec persona-sql /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P 'Persona_Lab1#2026' -C -Q "SELECT 1" >/dev/null 2>&1 && break
  sleep 3
done

echo "== Base de datos"
"$PY" QA/tests/db/db_tests.py
"$PY" QA/tests/db/bd07_entornos.py

echo "== Repositorio actual"
stop_app
"$DOTNET" build personapi-dotnet.sln -nologo -v q >/dev/null
start_app "$ROOT" "$LOGS/app-main.log"
"$PY" QA/tests/api/api_tests.py
"$PY" QA/tests/api/swagger_tests.py
"$PY" QA/tests/backend/backend_checks.py
"$PY" QA/tests/entrega/entrega_checks.py
stop_app

echo "== Frontend MVC e integracion ($FRONT)"
"$DOTNET" build "$FRONT/personapi-dotnet.sln" -nologo -v q >/dev/null
start_app "$FRONT" "$LOGS/app-frontend.log"
if [ "$FRONT" != "$ROOT" ]; then
  {
    "$PY" QA/tests/api/api_tests.py --tag frontend
    "$PY" QA/tests/api/swagger_tests.py --tag frontend
    "$PY" QA/tests/backend/backend_checks.py --tag frontend --repo "$FRONT"
  } 2>&1 | tee "$RES/regresion-frontend.txt"
fi
"$PY" QA/tests/mvc/mvc_tests.py
"$PY" QA/tests/mvc/int_tests.py
"$PY" QA/tests/mvc/manual_apoyo.py
stop_app

"$PY" QA/tests/casos_derivados.py
echo "== Resultados en $RES"
