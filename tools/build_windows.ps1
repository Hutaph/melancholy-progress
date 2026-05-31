$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root 'dist'
$build = Join-Path $root 'build'
$icon = Join-Path $root 'docs\assets\app.ico'
$spec = Join-Path $root 'quiet-progress.spec'
$builder = Join-Path $root '.build-venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $builder)) {
  throw 'Build environment is missing. Run: py -3.14 -m venv .build-venv'
}

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

Write-Host "Executable: $(Join-Path $dist 'quiet-progress.exe')"
