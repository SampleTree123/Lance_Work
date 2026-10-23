[CmdletBinding()]
param(
    [string]$RunId = 'run_20260829_v1',
    [int]$TimeoutSeconds = 21600
)

$ErrorActionPreference = 'Stop'
# RETIRED_EXECUTION_ENTRY_20261001: retained historical 14-case execution entry.
throw 'Retired 14-case modular outfit export entry. Its 12 outfit cases were replaced by the formal wardrobe library. Use the formal wardrobe export workflow with an explicit current export manifest; retain M_BASE/F_BASE and historical work orders.'

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LanceRoot = (Resolve-Path (Join-Path $ScriptRoot '..\..\..')).Path
$BridgeClient = Join-Path $LanceRoot '00_engine\character_creator_bridge\cc_bridge_client.py'
$Builder = Join-Path $ScriptRoot 'cc_build_modular_outfit_pilot_v1.py'
$Finalizer = Join-Path $ScriptRoot 'cc_finalize_modular_outfit_pilot_v1.py'
$Manifest = Join-Path $ScriptRoot 'cc_modular_outfit_pilot_20260829_v1.json'
$RuntimeManifest = Join-Path $LanceRoot (
    '00_engine\scripts\unreal\ue_modular_outfit_pilot_manifest_20260829_v1.json'
)
$OutputDir = Join-Path $LanceRoot (
    '00_engine\outputs\character_creator_bridge\artifacts' +
    '\modular_outfit_pilot\' + $RunId
)

if (Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue) {
    throw 'UnrealEditor must be closed before the modular outfit CC export.'
}
if (-not (Get-Process -Name CharacterCreator -ErrorAction SilentlyContinue)) {
    throw 'Character Creator is not running.'
}
if (Test-Path -LiteralPath $OutputDir) {
    throw "Run output already exists; choose a new RunId: $OutputDir"
}

& python $Builder
if ($LASTEXITCODE -ne 0) {
    throw "Modular pilot manifest build failed with exit code $LASTEXITCODE"
}

$health = & python $BridgeClient health | ConvertFrom-Json
if (-not $health.healthy -or $health.heartbeat.busy) {
    throw "CC Bridge is not idle and healthy: $($health | ConvertTo-Json -Compress)"
}

Write-Host "Starting modular outfit pilot export: $RunId"
Write-Host "Manifest: $Manifest"
Write-Host "Evidence: $OutputDir"

& python $BridgeClient validate-bodies `
    --library-file $Manifest `
    --output-dir $OutputDir `
    --confirm-scene-replace `
    --auto-dismiss-undo-warning `
    --job-id "modular-outfit-$RunId" `
    --timeout $TimeoutSeconds

if ($LASTEXITCODE -ne 0) {
    throw "Modular outfit export failed with exit code $LASTEXITCODE"
}

$ResultPath = Join-Path $OutputDir 'validation_result.json'
if (-not (Test-Path -LiteralPath $ResultPath -PathType Leaf)) {
    throw "Bridge completed without a validation result: $ResultPath"
}
$result = Get-Content -Raw -LiteralPath $ResultPath | ConvertFrom-Json
if (-not $result.success -or $result.success_count -ne 14 -or $result.failure_count -ne 0) {
    throw "Modular outfit export did not pass 14/14: $($result | ConvertTo-Json -Compress -Depth 4)"
}

$FinalizedEvidence = Join-Path $OutputDir 'finalized_ue_runtime_manifest.json'
& python $Finalizer `
    --validation-result $ResultPath `
    --cc-manifest $Manifest `
    --runtime-manifest $RuntimeManifest `
    --output $RuntimeManifest `
    --evidence-output $FinalizedEvidence
if ($LASTEXITCODE -ne 0) {
    throw "Modular outfit runtime manifest finalization failed with exit code $LASTEXITCODE"
}

[pscustomobject]@{
    success = $true
    run_id = $RunId
    requested = $result.requested_count
    passed = $result.success_count
    failed = $result.failure_count
    result = $ResultPath
    runtime_manifest = $RuntimeManifest
    finalized_evidence = $FinalizedEvidence
} | ConvertTo-Json -Depth 3
