param(
  [Parameter(Mandatory = $true)][string]$Path,
  [string]$Repo = "dettram/praverana"
)

# Репозиторий приватный: raw.githubusercontent.com отдаёт 404, поэтому картинки для issue/PR
# загружаются как вложения GitHub (user-attachments) и вставляются готовым URL.
# Требуется авторизованный gh; корпоративный TLS — curl --ssl-no-revoke.

$ErrorActionPreference = "Stop"
if (-not (Test-Path $Path)) { throw "файл не найден: $Path" }

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
if (-not $json.url) { throw "загрузка не удалась: $response" }
$json.url
