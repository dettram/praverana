param(
  [Parameter(Mandatory = $true)][string]$SkillPath
)

$ErrorActionPreference = "Stop"

$src = Join-Path $SkillPath "assets"
if (-not (Test-Path (Join-Path $src "system.css"))) {
  throw "system.css not found in $src - pass the design-taste-frontend folder"
}

$dst = Join-Path $PSScriptRoot "..\app\ui\assets"
New-Item -ItemType Directory -Force -Path $dst | Out-Null

foreach ($item in @("system.css", "system.js", "ui", "motion", "backgrounds", "layout", "icons", "moments", "diagrams")) {
  $from = Join-Path $src $item
  if (Test-Path $from) {
    Copy-Item $from (Join-Path $dst $item) -Recurse -Force
    Write-Output "copied $item"
  }
}

Write-Output "kit assets ready: $dst"
