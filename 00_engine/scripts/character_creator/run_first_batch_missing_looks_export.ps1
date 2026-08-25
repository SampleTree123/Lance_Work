[CmdletBinding()]
param(
    [string]$RunId = 'run_20260822_missing16_v1',
    [int]$TimeoutSeconds = 18000
)

$ErrorActionPreference = 'Stop'
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LanceRoot = (Resolve-Path (Join-Path $ScriptRoot '..\..\..')).Path
$BridgeClient = Join-Path $LanceRoot '00_engine\character_creator_bridge\cc_bridge_client.py'
$Manifest = Join-Path $ScriptRoot 'cc_first_batch_full_reference_missing_looks_20260822_v1.json'
$OutputDir = Join-Path $LanceRoot (
    '00_engine\outputs\character_creator_bridge\artifacts' +
    '\first_batch_full_reference_expansion\' + $RunId
)

if (Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue) {
    throw 'UnrealEditor must be closed before the missing-16 CC export.'
}
if (-not (Get-Process -Name CharacterCreator -ErrorAction SilentlyContinue)) {
    throw 'Character Creator is not running.'
}
if (-not (Test-Path -LiteralPath $Manifest -PathType Leaf)) {
    throw "Missing Look manifest does not exist: $Manifest"
}
if (Test-Path -LiteralPath $OutputDir) {
    throw "Run output already exists; choose a new RunId: $OutputDir"
}

$health = & python $BridgeClient health | ConvertFrom-Json
if (-not $health.healthy -or $health.heartbeat.busy) {
    throw "CC Bridge is not idle and healthy: $($health | ConvertTo-Json -Compress)"
}

Write-Host "Starting missing-16 Look export: $RunId"
Write-Host "Manifest: $Manifest"
Write-Host "Evidence: $OutputDir"

& python $BridgeClient validate-bodies `
    --library-file $Manifest `
    --output-dir $OutputDir `
    --confirm-scene-replace `
    --auto-dismiss-undo-warning `
    --job-id "first-batch-missing16-$RunId" `
    --timeout $TimeoutSeconds

if ($LASTEXITCODE -ne 0) {
    throw "Missing-16 Look export failed with exit code $LASTEXITCODE"
}

$ResultPath = Join-Path $OutputDir 'validation_result.json'
if (-not (Test-Path -LiteralPath $ResultPath -PathType Leaf)) {
    throw "Bridge completed without a validation result: $ResultPath"
}
$result = Get-Content -Raw -LiteralPath $ResultPath | ConvertFrom-Json
if (-not $result.success -or $result.success_count -ne 16 -or $result.failure_count -ne 0) {
    throw "Missing-16 export did not pass 16/16: $($result | ConvertTo-Json -Compress -Depth 4)"
}

[pscustomobject]@{
    success = $true
    run_id = $RunId
    requested = $result.requested_count
    passed = $result.success_count
    failed = $result.failure_count
    result = $ResultPath
} | ConvertTo-Json -Depth 3
