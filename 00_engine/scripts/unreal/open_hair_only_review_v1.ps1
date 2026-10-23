param(
    [ValidatePattern('^[A-Za-z0-9_.:-]+$')][string]$NodeId = ''
)
$ErrorActionPreference = 'Stop'
$taskPythonWindow = 'C:\ProgramData\anaconda3\pythonw.exe'
$taskRunner = Join-Path $PSScriptRoot 'run_hair_only_review_v1.py'
$taskRepo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
if (-not (Test-Path -LiteralPath $taskPythonWindow)) { throw "Python runtime not found: $taskPythonWindow" }
if (-not (Test-Path -LiteralPath $taskRunner)) { throw "Hair review panel not found: $taskRunner" }
$taskArguments = @(('"' + $taskRunner + '"'), '--action', 'panel')
if ($NodeId) { $taskArguments += @('--node-id', $NodeId) }
# This visible window is the interactive panel requested by the user.
Start-Process -FilePath $taskPythonWindow -ArgumentList $taskArguments -WorkingDirectory $taskRepo -WindowStyle Normal
Write-Output 'Opening the independent character and hair review panel. Keep the existing UE editor open.'
