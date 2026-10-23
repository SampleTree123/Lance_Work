param([ValidatePattern('^[A-Za-z0-9_.:-]+$')][string]$NodeId = '')
$ErrorActionPreference = 'Stop'
$taskPythonWindow = 'C:\ProgramData\anaconda3\pythonw.exe'
$taskRunner = Join-Path $PSScriptRoot 'pair_scene_review_20261019_v1.py'
$taskRepo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$taskArguments = @(('"' + $taskRunner + '"'))
if ($NodeId) { $taskArguments += @('--node-id', $NodeId) }
# User explicitly requests this interactive review panel.
Start-Process -FilePath $taskPythonWindow -ArgumentList $taskArguments -WorkingDirectory $taskRepo -WindowStyle Normal
Write-Output 'Opening full scene review with all 40 imported characters.'
