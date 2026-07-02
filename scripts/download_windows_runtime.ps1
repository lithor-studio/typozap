$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $root "runtime"
$engine = Join-Path $runtime "typozap-engine.exe"

if (Test-Path $engine) {
    Write-Host "Runtime llama.cpp deja present."
    exit 0
}

Write-Host "Telechargement du runtime llama.cpp Windows..."
$release = Invoke-RestMethod "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
$asset = $release.assets | Where-Object { $_.name -match "bin-win-cpu-x64\.zip$" } | Select-Object -First 1
if (-not $asset) {
    throw "Runtime llama.cpp Windows x64 introuvable dans la derniere release."
}

$archive = Join-Path $env:TEMP "typozap-llama-runtime.zip"
$expanded = Join-Path $env:TEMP "typozap-llama-runtime"
Invoke-WebRequest $asset.browser_download_url -OutFile $archive
if (Test-Path $expanded) { Remove-Item -LiteralPath $expanded -Recurse -Force }
Expand-Archive $archive -DestinationPath $expanded
$server = Get-ChildItem $expanded -Recurse -Filter "llama-server.exe" | Select-Object -First 1
if (-not $server) { throw "llama-server.exe absent de l'archive." }

New-Item $runtime -ItemType Directory -Force | Out-Null
Copy-Item (Join-Path $server.Directory.FullName "*") $runtime -Recurse -Force
Move-Item (Join-Path $runtime "llama-server.exe") $engine -Force
Write-Host "Runtime installe dans $runtime"
