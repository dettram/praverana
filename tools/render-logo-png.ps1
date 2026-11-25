param(
  [string]$Edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)

# Показ логотипов в 3× растре: при 100 % масштабе вектор даёт лесенку на краях,
# уменьшенный 3× PNG выглядит гладко. Исходник остаётся SVG; PNG — только для экрана.

$ErrorActionPreference = "Continue"
if (-not (Test-Path $Edge)) { $Edge = "C:\Program Files\Microsoft\Edge\Application\msedge.exe" }
if (-not (Test-Path $Edge)) { throw "Edge не найден: $Edge" }

$root = Split-Path -Parent $PSScriptRoot
$logo = Join-Path $root "app\ui\assets\logo"
$out = Join-Path $logo "png"
$tmp = Join-Path $env:LOCALAPPDATA "Temp\logo-png"
New-Item -ItemType Directory -Force -Path $out, $tmp | Out-Null

$jobs = @(
  @{ svg = "mark.svg"; w = 64; h = 64 },
  @{ svg = "mark-inverse.svg"; w = 64; h = 64 },
  @{ svg = "logo-horizontal.svg"; w = 372; h = 64 },
  @{ svg = "logo-horizontal-inverse.svg"; w = 372; h = 64 },
  @{ svg = "logo-stacked.svg"; w = 192; h = 128 },
  @{ svg = "logo-mono.svg"; w = 64; h = 64 }
)

foreach ($job in $jobs) {
  $scale = 3
  $w = $job.w * $scale
  $h = $job.h * $scale
  $name = [IO.Path]::GetFileNameWithoutExtension($job.svg)
  $html = Join-Path $tmp "$name.html"
  $shot = Join-Path $tmp "$name.png"
  $src = (Join-Path $logo $job.svg) -replace '\\', '/'
  @"
<!DOCTYPE html><html><head><meta charset="utf-8"><style>
html,body{margin:0;background:transparent}img{display:block}
</style></head><body>
<img src="file:///$src" width="$w" height="$h">
</body></html>
"@ | Set-Content -Path $html -Encoding UTF8

  & $Edge --headless=new --disable-gpu --hide-scrollbars --default-background-color=00000000 `
    --force-device-scale-factor=1 --window-size=$w,$h --virtual-time-budget=4000 `
    --screenshot="$shot" "file:///$($html -replace '\\','/')" 2>$null | Out-Null

  Copy-Item $shot (Join-Path $out "$name.png") -Force
  "$name.png : $w x $h"
}
