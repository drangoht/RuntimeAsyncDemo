# Lance la démo rapide dans les deux modes, l'un après l'autre (environ 30 s).
#   .\comparer.ps1
# Pour les mesures rigoureuses (15-20 min) :
#   dotnet run -c Release --project src/RuntimeAsyncDemo.Benchmarks -- --filter *

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

foreach ($mode in 'compiler', 'runtime') {
    Write-Host ''
    Write-Host "==================== AsyncMode=$mode ====================" -ForegroundColor Cyan
    dotnet run -c Release --project src/RuntimeAsyncDemo.Demo -p:AsyncMode=$mode
    if ($LASTEXITCODE -ne 0) { throw "La démo a échoué en mode $mode" }
}
