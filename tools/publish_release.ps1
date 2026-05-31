$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$asset = Join-Path $root 'release\quiet-progress-windows.zip'
$notes = Join-Path $root 'release\release-notes-v0.1.0.md'

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  throw 'GitHub CLI is missing. Install it from https://cli.github.com/ and run gh auth login.'
}

if (-not (Test-Path -LiteralPath (Join-Path $root '.git'))) {
  throw 'This folder is not a Git repository yet. Create the GitHub repo, then initialize and push this folder first.'
}

if (-not (Test-Path -LiteralPath $asset)) {
  throw 'Release asset is missing. Run tools\build_windows.ps1 first.'
}

Push-Location $root
try {
  gh release create v0.1.0 $asset `
    --title 'quiet-progress v0.1.0' `
    --notes-file $notes
} finally {
  Pop-Location
}
