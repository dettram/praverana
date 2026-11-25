param(
  [Parameter(Mandatory = $true)][string]$Path,
  [string]$Repo = "dettram/praverana"
)

# Private repo: raw.githubusercontent.com returns 404, so issue/PR images are uploaded
# as GitHub user attachments and pasted as the returned URL.
# Requires an authenticated gh; corporate TLS -> curl --ssl-no-revoke.

$ErrorActionPreference = "Stop"
if (-not (Test-Path $Path)) { throw "file not found: $Path" }

$gh = Join-Path $env:LOCALAPPDATA "Programs\gh\gh.exe"
if (-not (Test-Path $gh)) { $gh = "gh" }

$token = (& $gh auth token).Trim()
$repoId = (& $gh api "repos/$Repo" --jq ".id").Trim()

$file = Get-Item $Path
$name = $file.Name
$type = switch ($file.Extension.ToLower()) {
  ".png"  { "image/png" }
  ".jpg"  { "image/jpeg" }
  ".jpeg" { "image/jpeg" }
  ".gif"  { "image/gif" }
  ".webp" { "image/webp" }
  ".svg"  { "image/svg+xml" }
  default { "application/octet-stream" }
}

$url = "https://uploads.github.com/user-attachments/assets?repository_id=$repoId&name=$([uri]::EscapeDataString($name))"
$response = curl.exe -sS --ssl-no-revoke -X POST `
  -H "Authorization: Bearer $token" `
  -H "Accept: application/vnd.github+json" `
  -H "Content-Type: $type" `
  --data-binary "@$($file.FullName)" $url

$json = $response | ConvertFrom-Json
if (-not $json.url) { throw "upload failed: $response" }
$json.url
