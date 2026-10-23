param([ValidateRange(1, 40)][int]$HairIndex = 1)
$ErrorActionPreference = 'Stop'
$taskPython = 'C:\ProgramData\anaconda3\python.exe'
$taskPythonWindow = 'C:\ProgramData\anaconda3\pythonw.exe'
$taskRunner = Join-Path $PSScriptRoot 'run_fixed_head_hair_manual_review_v1.py'
$taskRepo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
if (-not (Test-Path -LiteralPath $taskPythonWindow)) {
    throw "Review Python runtime not found: $taskPythonWindow"
}
$taskOutput = & $taskPython $taskRunner --action show --hair-index $HairIndex --view front --sex both
if ($LASTEXITCODE -ne 0) {
    Write-Output $taskOutput
    throw 'Could not prepare the UE hairstyle review. Keep datatry_02 open.'
}
Start-Process -FilePath $taskPythonWindow -ArgumentList @($taskRunner, '--action', 'panel', '--hair-index', "$HairIndex") -WorkingDirectory $taskRepo -WindowStyle Normal
Write-Output 'UE review ready. The hairstyle control panel is open.'
