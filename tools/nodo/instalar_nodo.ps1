# =============================================================================
# ZGC - Instalador del NODO DE SUCURSAL (F13-LAN N1) para Windows.
#
# Se corre EN LA PC SERVIDOR de la sucursal (PowerShell como Administrador),
# desde un checkout del repo ZGC. Requisitos previos en la PC:
#   - Python 3.10+ en el PATH        (python --version)
#   - PostgreSQL 14+ instalado       (instalador oficial de postgresql.org)
#   - Node.js 20+ en el PATH         (solo si se sirve el POS web: npm run build)
#
# El NODO_ID y el NODO_TOKEN salen de la suite: Configuracion -> Nodos de
# sucursal -> "+ Agregar nodo" (el token se muestra UNA sola vez).
#
# Uso:
#   .\instalar_nodo.ps1 -NodoId <uuid> -NodoToken <token> `
#       -NubeUrl https://zaris-zgc-api.vercel.app -PgPassword <clave postgres> `
#       [-Puerto 8021] [-SinWeb]
#
# Idempotente: re-correrlo actualiza dependencias, re-aplica migraciones
# (aditivas) y reescribe la tarea programada. Los datos locales no se tocan.
# =============================================================================
param(
    [Parameter(Mandatory = $true)][string]$NodoId,
    [Parameter(Mandatory = $true)][string]$NodoToken,
    [string]$NubeUrl = "https://zaris-zgc-api.vercel.app",
    [Parameter(Mandatory = $true)][string]$PgPassword,
    [int]$Puerto = 8021,
    [string]$DbNombre = "zgc_nodo",
    [switch]$SinWeb
)

$ErrorActionPreference = "Stop"
$RAIZ = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$BACKEND = Join-Path $RAIZ "backend"
Write-Host "== ZGC nodo de sucursal: instalacion en $RAIZ =="

# --- 1. psql -----------------------------------------------------------------
$psql = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\psql.exe" |
    Sort-Object FullName -Descending | Select-Object -First 1
if (-not $psql) { throw "No se encontro PostgreSQL en C:\Program Files\PostgreSQL" }
$env:PGPASSWORD = $PgPassword
Write-Host "-- psql: $($psql.FullName)"

# --- 2. base local + migraciones ----------------------------------------------
$existe = & $psql.FullName -h 127.0.0.1 -U postgres -d postgres -t -A `
    -c "select 1 from pg_database where datname='$DbNombre'"
if ($existe -ne "1") {
    & $psql.FullName -h 127.0.0.1 -U postgres -d postgres -c "create database $DbNombre"
    Write-Host "-- base $DbNombre creada"
}
Get-ChildItem (Join-Path $RAIZ "sql\0*.sql") | Sort-Object Name | ForEach-Object {
    & $psql.FullName -h 127.0.0.1 -U postgres -d $DbNombre -v ON_ERROR_STOP=1 -q -f $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "Fallo la migracion $($_.Name)" }
}
Write-Host "-- migraciones aplicadas"

# --- 3. entorno Python ---------------------------------------------------------
if (-not (Test-Path (Join-Path $BACKEND ".venv"))) {
    python -m venv (Join-Path $BACKEND ".venv")
}
& (Join-Path $BACKEND ".venv\Scripts\python.exe") -m pip install -q --upgrade pip
& (Join-Path $BACKEND ".venv\Scripts\python.exe") -m pip install -q `
    -r (Join-Path $BACKEND "requirements.txt")
Write-Host "-- dependencias Python instaladas"

# --- 4. build del POS web (mismo build de siempre: base /, API same-origin) ---
$webDir = ""
if (-not $SinWeb) {
    Push-Location (Join-Path $RAIZ "web-app")
    npm install --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { Pop-Location; throw "npm install fallo" }
    Remove-Item Env:\VITE_API_URL -ErrorAction SilentlyContinue
    Remove-Item Env:\VITE_BASE -ErrorAction SilentlyContinue
    npm run build
    if ($LASTEXITCODE -ne 0) { Pop-Location; throw "npm run build fallo" }
    Pop-Location
    $webDir = (Join-Path $RAIZ "web-app\dist") -replace "\\", "/"
    Write-Host "-- POS web compilado en $webDir"
}

# --- 5. configuracion del nodo (.env.nodo) ------------------------------------
$jwt = -join ((1..48) | ForEach-Object { "{0:x}" -f (Get-Random -Maximum 16) })
$passEnc = [uri]::EscapeDataString($PgPassword)
@(
    "ENV=nodo",
    "PERFIL=nodo",
    "DATABASE_URL=postgresql+asyncpg://postgres:$passEnc@127.0.0.1:5432/$DbNombre",
    "JWT_SECRET=$jwt",
    "NUBE_URL=$NubeUrl",
    "NODO_ID=$NodoId",
    "NODO_TOKEN=$NodoToken",
    "SYNC_INTERVALO_SEG=60",
    "NODO_WEB_DIR=$webDir",
    "CORS_ORIGINS=http://localhost:5173"
) | Out-File -FilePath (Join-Path $BACKEND ".env.nodo") -Encoding ascii
Write-Host "-- .env.nodo escrito"

# --- 6. lanzador + tarea programada (arranque automatico) ----------------------
$cmd = Join-Path $RAIZ "tools\nodo\iniciar_nodo.cmd"
@(
    "@echo off",
    "cd /d `"$BACKEND`"",
    "set ENV_FILE=.env.nodo",
    ".venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port $Puerto"
) | Out-File -FilePath $cmd -Encoding ascii

schtasks /Create /F /TN "ZGC Nodo Sucursal" /SC ONSTART /RU SYSTEM /RL HIGHEST `
    /TR "`"$cmd`"" | Out-Null
Write-Host "-- tarea programada 'ZGC Nodo Sucursal' registrada (arranque automatico)"

# --- 7. firewall (las cajas de la LAN entran por este puerto) -------------------
netsh advfirewall firewall delete rule name="ZGC Nodo Sucursal" | Out-Null
netsh advfirewall firewall add rule name="ZGC Nodo Sucursal" dir=in action=allow `
    protocol=TCP localport=$Puerto | Out-Null
Write-Host "-- firewall: puerto $Puerto abierto para la LAN"

# --- 8. arrancar ahora y verificar ----------------------------------------------
schtasks /Run /TN "ZGC Nodo Sucursal" | Out-Null
Start-Sleep -Seconds 6
try {
    $salud = Invoke-RestMethod "http://127.0.0.1:$Puerto/health"
    Write-Host "== NODO OPERATIVO: perfil=$($salud.perfil) =="
    Write-Host "   Cajas de la LAN: http://<IP-de-esta-PC>:$Puerto/pos/login"
    Write-Host "   (la primera replica de maestros tarda unos segundos; ver /api/v1/nodo/estado)"
} catch {
    Write-Warning "El nodo no respondio todavia: revisar con 'schtasks /Query /TN `"ZGC Nodo Sucursal`"' y el log de uvicorn."
}
