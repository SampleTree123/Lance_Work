param(
    [ValidatePattern('^[A-Za-z0-9_.:-]+$')][string]$NodeId = ''
)
$ErrorActionPreference = 'Stop'
$taskPythonWindow = 'C:\ProgramData\anaconda3\pythonw.exe'
$taskRunner = Join-Path $PSScriptRoot 'run_complete_character_wardrobe_hair_review_v1.py'
$taskRepo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
if (-not (Test-Path -LiteralPath $taskPythonWindow)) {
    throw "Review Python runtime not found: $taskPythonWindow"
}
if (-not (Test-Path -LiteralPath $taskRunner)) {
    throw "Review controller not found: $taskRunner"
}
$taskArguments = @(('"' + $taskRunner + '"'), '--action', 'panel')
if ($NodeId) {
    $taskArguments += @('--node-id', $NodeId)
}
# This visible window is the interactive review panel explicitly requested by the user.
Start-Process -FilePath $taskPythonWindow -ArgumentList $taskArguments -WorkingDirectory $taskRepo -WindowStyle Normal
Write-Output 'The clothing and hairstyle review panel is opening. Keep the existing UE editor open.'
