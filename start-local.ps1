# Lance MarketView SANS Docker (Windows) : API sur http://localhost:8000, site sur http://localhost:5173.
# Base SQLite locale (backend\marketview-local.db) ; sans Redis, pas de temps réel WebSocket ni de cache.
# Usage : clic droit > "Exécuter avec PowerShell", ou dans un terminal : powershell -ExecutionPolicy Bypass -File .\start-local.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Création de l'environnement Python..."
    py -3 -m venv (Join-Path $backend ".venv")
    & $python -m pip install -r (Join-Path $backend "requirements-dev.txt")
}
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Installation des dépendances du frontend..."
    Push-Location $frontend; npm ci; Pop-Location
}

# Reprend les clés API du fichier .env racine s'il existe (FINNHUB_API_KEY, FRED_API_KEY...).
$envFile = Join-Path $root ".env"
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^\s*([A-Z_]+_KEY)\s*=\s*(.+?)\s*$') { Set-Item "env:$($Matches[1])" $Matches[2] }
    }
}

$env:DATABASE_URL = "sqlite:///" + ((Join-Path $backend "marketview-local.db") -replace '\\', '/')
$env:REDIS_URL = "redis://127.0.0.1:6379/0"
$env:CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
$env:RUN_SCHEDULER = "true"
$env:VITE_API_URL = "http://localhost:8000"
$env:VITE_WS_URL = "ws://localhost:8000"

Write-Host "Migrations et chargement des paires..."
Push-Location $backend
& $python -m alembic upgrade head
& $python -m app.seed
Pop-Location

# Deux fenêtres : fermez-les pour arrêter l'application.
Start-Process powershell -WorkingDirectory $backend -ArgumentList "-NoExit", "-Command", "& '$python' -m uvicorn app.main:app --port 8000"
Start-Process powershell -WorkingDirectory $frontend -ArgumentList "-NoExit", "-Command", "npm run dev"

Write-Host ""
Write-Host "MarketView démarre : http://localhost:5173  (API : http://localhost:8000/docs)"
Write-Host "Base de données SQLite : $backend\marketview-local.db"
