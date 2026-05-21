param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]] $CommandArgs
)

$ErrorActionPreference = "Stop"
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = $Utf8NoBom
[Console]::OutputEncoding = $Utf8NoBom
[Console]::InputEncoding = $Utf8NoBom

$ApiBase = if ($env:AI_COMPANY_API) { $env:AI_COMPANY_API.TrimEnd("/") } else { "http://127.0.0.1:8787" }
$Command = if ($CommandArgs.Count -gt 0) { $CommandArgs[0] } else { "" }

if ($Command -ne "ai-company") {
  Write-Host "Usage: star ai-company [path]" -ForegroundColor Yellow
  exit 2
}

$WorkspacePath = if ($CommandArgs.Count -gt 1) {
  ($CommandArgs[1..($CommandArgs.Count - 1)] -join " ")
} else {
  (Get-Location).Path
}

$WorkspaceName = Split-Path -Leaf $WorkspacePath
if (-not $WorkspaceName) {
  $WorkspaceName = $WorkspacePath
}

$Payload = @{
  path = $WorkspacePath
  name = $WorkspaceName
  source = "star-cli"
} | ConvertTo-Json -Depth 4
$PayloadBytes = $Utf8NoBom.GetBytes($Payload)

try {
  $Result = Invoke-RestMethod `
    -Method Post `
    -Uri "$ApiBase/workspaces/activate" `
    -ContentType "application/json; charset=utf-8" `
    -Body $PayloadBytes

  Write-Host "AI Company workspace activated" -ForegroundColor Green
  Write-Host "Name : $($Result.name)"
  Write-Host "Path : $($Result.path)"
  Write-Host "API  : $ApiBase"
} catch {
  Write-Host "Failed to activate AI Company workspace." -ForegroundColor Red
  Write-Host "API: $ApiBase"
  Write-Host $_.Exception.Message
  Write-Host "Make sure the local API is running on port 8787."
  exit 1
}
