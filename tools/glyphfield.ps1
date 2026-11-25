param(
  [ValidateSet("start", "stop", "status")][string]$Action = "status"
)

$ErrorActionPreference = "Stop"

$Clone = Join-Path $env:LOCALAPPDATA "design-tools\glyphfield"
if (-not (Test-Path $Clone)) { $Clone = Join-Path $env:LOCALAPPDATA "Temp\harvest\glyphfield" }
$Node = Join-Path $env:LOCALAPPDATA "node22\node.exe"
$Out = Join-Path $env:LOCALAPPDATA "Temp\harvest\gf-dev.log"
$Err = Join-Path $env:LOCALAPPDATA "Temp\harvest\gf-dev.err.log"
$Port = 3013

function Get-PortPid([int]$port) {
  $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if ($conn) { return $conn.OwningProcess }
  return $null
}

switch ($Action) {
  "status" {
    $pid3012 = Get-PortPid $Port
    if ($pid3012) { "glyphfield: up on $Port (pid $pid3012)" } else { "glyphfield: down" }
  }
  "stop" {
    $procId = Get-PortPid $Port
    if ($procId) { Stop-Process -Id $procId -Force; "glyphfield: stopped (pid $procId)" }
    else { "glyphfield: already down" }
  }
  "start" {
    if (Get-PortPid $Port) { "glyphfield: already up on $Port"; break }
    if (-not (Test-Path $Node)) { throw "node not found: $Node" }
    if (-not (Test-Path (Join-Path $Clone "node_modules"))) {
      throw "dependencies missing: run pnpm install in $Clone"
    }
    $env:NODE_OPTIONS = "--use-system-ca"
    Start-Process -FilePath $Node -WorkingDirectory $Clone -WindowStyle Hidden `
      -ArgumentList "node_modules/next/dist/bin/next", "dev", "--turbopack", "--port", "$Port" `
      -RedirectStandardOutput $Out -RedirectStandardError $Err
    for ($i = 0; $i -lt 60; $i++) {
      Start-Sleep -Seconds 2
      try {
        $r = Invoke-WebRequest -Uri "http://localhost:$Port/api/brand/kit" -UseBasicParsing -TimeoutSec 10
        if ($r.StatusCode -eq 200) { "glyphfield: up on http://localhost:$Port/studio"; break }
      } catch { }
    }
  }
}
