param([switch]$Telefon)
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$env:PYTHONUTF8='1'
$pythonExe=Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (!(Test-Path $pythonExe)) {
    $bundled=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Test-Path $bundled) { $pythonExe=$bundled }
    else { $pythonExe=(Get-Command python -ErrorAction Stop).Source }
}
Write-Host 'Uygulama: http://127.0.0.1:8767'
Write-Host 'Fiyat yonetimi: http://127.0.0.1:8767/admin'
Write-Host 'Durdurmak icin Ctrl+C. Ayni anda yalnizca bir sunucu calistirin.'
if ($Telefon) { & $pythonExe 'server/app.py' --lan } else { & $pythonExe 'server/app.py' }
exit $LASTEXITCODE
