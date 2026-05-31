param(
  [string]$Version = 'v0.2.0'
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$asset = Join-Path $root 'dist\quiet-progress.exe'
$notes = Join-Path $root "release\release-notes-$Version.md"

if ($Version -notmatch '^v\d+\.\d+\.\d+$') {
  throw 'Version must use semantic versioning, for example: v0.2.0'
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  throw 'GitHub CLI is missing. Install it from https://cli.github.com/ and run gh auth login.'
}

if (-not (Test-Path -LiteralPath (Join-Path $root '.git'))) {
  throw 'This folder is not a Git repository yet. Create the GitHub repo, then initialize and push this folder first.'
}

if (-not (Test-Path -LiteralPath $asset)) {
  throw 'Release asset is missing. Run tools\build_windows.ps1 first.'
}

if (-not (Test-Path -LiteralPath $notes)) {
  throw "Release notes are missing: $notes"
}

Push-Location $root
try {
  gh release view $Version *> $null
  if ($LASTEXITCODE -eq 0) {
    gh release upload $Version $asset --clobber
    gh release edit $Version `
      --title "quiet-progress $Version" `
      --notes-file $notes
  } else {
    gh release create $Version $asset `
      --title "quiet-progress $Version" `
      --notes-file $notes
  }
} finally {
  Pop-Location
}
