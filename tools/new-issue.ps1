param(
  [Parameter(Mandatory = $true)][string]$Title,
  [Parameter(Mandatory = $true)][string]$BodyFile,
  [string]$Labels = "",
  [string]$Repo = "dettram/praverana"
)

$ErrorActionPreference = "Stop"

$gh = Join-Path $env:LOCALAPPDATA "Programs\gh\gh.exe"
if (-not (Test-Path $gh)) {
  $gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
}
if (-not $gh) { throw "gh not found: install GitHub CLI or add it to PATH" }
if (-not (Test-Path $BodyFile)) { throw "body file not found: $BodyFile" }

$args = @("issue", "create", "--repo", $Repo, "--title", $Title, "--body-file", $BodyFile)
if ($Labels) {
  foreach ($l in ($Labels -split "[,;]\s*" | Where-Object { $_ })) {
    $args += @("--label", $l)
  }
}

& $gh @args
