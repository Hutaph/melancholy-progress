$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root 'dist'
$build = Join-Path $root 'build'
$release = Join-Path $root 'release'
$icon = Join-Path $root 'docs\assets\app.ico'
$spec = Join-Path $root 'quiet-progress.spec'
$builder = Join-Path $root '.build-venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $builder)) {
  throw 'Build environment is missing. Run: py -3.14 -m venv .build-venv'
}

New-Item -ItemType Directory -Force -Path $release | Out-Null

& $builder -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name quiet-progress `
  --icon $icon `
  --hidden-import PIL.Image `
  --hidden-import PIL.ImageDraw `
  (Join-Path $root 'app.py')

$zip = Join-Path $release 'quiet-progress-windows.zip'
if (Test-Path -LiteralPath $zip) {
  Remove-Item -LiteralPath $zip -Force
}

Compress-Archive `
  -LiteralPath (Join-Path $dist 'quiet-progress.exe') `
  -DestinationPath $zip `
  -CompressionLevel Optimal

Write-Host "Executable: $(Join-Path $dist 'quiet-progress.exe')"
Write-Host "Release zip: $zip"
