# Builds the Flutter drag-and-drop island and copies it into the static
# frontend so the HTML dashboard can embed it at /us017/flutter/index.html.
#
# Usage (from anywhere):  ./scripts/build-flutter-dnd.ps1
# Requires the Flutter SDK on PATH (verify with `flutter --version`).

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$flutterDir = Join-Path $root "flutter_rule_config"
$dest = Join-Path $root "frontend\us017\flutter"

Write-Host "Building Flutter web (base-href /us017/flutter/)..."
Push-Location $flutterDir
try {
    & flutter build web --base-href /us017/flutter/
    if ($LASTEXITCODE -ne 0) { throw "flutter build web failed (exit $LASTEXITCODE)" }
}
finally {
    Pop-Location
}

Write-Host "Copying build output to $dest ..."
New-Item -ItemType Directory -Force -Path $dest | Out-Null
# Clear previous build output but keep the README/.gitkeep.
Get-ChildItem -Path $dest -Force |
    Where-Object { $_.Name -notin @("README.md", ".gitkeep") } |
    Remove-Item -Recurse -Force
Copy-Item -Path (Join-Path $flutterDir "build\web\*") -Destination $dest -Recurse -Force

Write-Host "Done. Open the dashboard and the drag-and-drop island will load from ./flutter/."
