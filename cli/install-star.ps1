$ErrorActionPreference = "Stop"

$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDir = Join-Path $env:USERPROFILE ".ai-company\bin"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Force -Path (Join-Path $SourceDir "star.ps1") -Destination (Join-Path $InstallDir "star.ps1")
Copy-Item -Force -Path (Join-Path $SourceDir "star.cmd") -Destination (Join-Path $InstallDir "star.cmd")

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$PathItems = @()
if ($UserPath) {
  $PathItems = $UserPath -split ";"
}

if ($PathItems -notcontains $InstallDir) {
  $NextPath = if ($UserPath) { "$UserPath;$InstallDir" } else { $InstallDir }
  [Environment]::SetEnvironmentVariable("Path", $NextPath, "User")
  $env:Path = "$env:Path;$InstallDir"
  Write-Host "Installed star command and added it to the user PATH." -ForegroundColor Green
  Write-Host "Open a new terminal, then run: star ai-company"
} else {
  Write-Host "star command is already installed." -ForegroundColor Green
}

Write-Host "Install dir: $InstallDir"
