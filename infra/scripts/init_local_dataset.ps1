$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$images = Join-Path $root "data\raw\local_yolo\images"
$labels = Join-Path $root "data\raw\local_yolo\labels"

New-Item -ItemType Directory -Force -Path $images | Out-Null
New-Item -ItemType Directory -Force -Path $labels | Out-Null

Write-Host "Created:"
Write-Host " - $images"
Write-Host " - $labels"
Write-Host ""
Write-Host "Next:"
Write-Host " - Copy images into data\raw\local_yolo\images"
Write-Host " - Copy YOLO label .txt files into data\raw\local_yolo\labels"

