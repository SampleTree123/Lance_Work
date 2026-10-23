param([switch]$Apply)

$ErrorActionPreference = 'Stop'
$reportRoot = 'D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\asset_restructure_full_20260929_v1'
$contentRoot = 'D:\UE\projects\datatry_02\Content'
$targets = @(
    'D:\UE\projects\datatry_02\Content\Vendor\Reallusion\CC5\Wardrobe',
    'D:\UE\projects\datatry_02\Content\Vendor\Reallusion\CC5\ScalpHairBatch'
)

$copy = Get-Content -LiteralPath (Join-Path $reportRoot 'copy_progress.json') -Raw | ConvertFrom-Json
$verify = Get-Content -LiteralPath (Join-Path $reportRoot 'fresh_load_verification.json') -Raw | ConvertFrom-Json
$assembly = Get-Content -LiteralPath (Join-Path $reportRoot 'assembly_verification.json') -Raw | ConvertFrom-Json
$scope = Get-Content -LiteralPath (Join-Path $reportRoot 'filesystem_scope_before_cleanup.json') -Raw | ConvertFrom-Json
$references = Get-Content -LiteralPath (Join-Path $reportRoot 'old_case_referencer_audit.json') -Raw | ConvertFrom-Json
$plans = Get-Content -LiteralPath (Join-Path $reportRoot 'review_plan_migration_report.json') -Raw | ConvertFrom-Json
$formalRegistry = 'D:\UE\Lance_Work\00_engine\assets\character_creator\wardrobe_registry_ue_v4_full_20260929.json'
if ($copy.completed.Count -ne 365 -or $null -ne $copy.failed) { throw 'Copy gate failed' }
if (-not $verify.success -or $verify.checked_cases -ne 365 -or $verify.checked_assets -ne 4732) { throw 'Fresh-load gate failed' }
if (-not $assembly.success -or $assembly.outfit_count -ne 173 -or $assembly.hair_count -ne 40) { throw 'Assembly gate failed' }
if (-not $scope.safe_scope -or $scope.old_case_count -ne 365 -or $scope.old_file_counts.'.uasset' -ne 30526) { throw 'Filesystem scope gate failed' }
if (-not (Test-Path -LiteralPath $formalRegistry -PathType Leaf)) { throw 'Formal UE registry missing' }
foreach ($name in @('modular_runtime_v2', 'wardrobe_coverage', 'hair_outfit_compatibility')) {
    $entry = $plans.$name
    if ($null -eq $entry -or @($entry.unresolved_old_path_prefixes).Count -ne 0 -or -not (Test-Path -LiteralPath $entry.path -PathType Leaf)) {
        throw "Migrated plan gate failed: $name"
    }
}
$oldPrefixes = @('/Game/Vendor/Reallusion/CC5/Wardrobe/', '/Game/Vendor/Reallusion/CC5/ScalpHairBatch/')
foreach ($property in $references.external_referencers.PSObject.Properties) {
    $insideOld = $false
    foreach ($prefix in $oldPrefixes) {
        if ($property.Name.StartsWith($prefix, [StringComparison]::Ordinal)) { $insideOld = $true }
    }
    if (-not $insideOld) { throw "External UE referencer still exists: $($property.Name)" }
}
if (Get-Process UnrealEditor, UnrealEditor-Cmd -ErrorAction SilentlyContinue) { throw 'UE is running; close it before cleanup' }

$resolvedContent = [IO.Path]::GetFullPath($contentRoot).TrimEnd('\')
$resolvedTargets = @()
foreach ($target in $targets) {
    $resolved = (Resolve-Path -LiteralPath $target).ProviderPath.TrimEnd('\')
    $full = [IO.Path]::GetFullPath($resolved).TrimEnd('\')
    if (-not $full.StartsWith($resolvedContent + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Target escaped project Content directory: $full"
    }
    if ($full -ne [IO.Path]::GetFullPath($target).TrimEnd('\')) { throw "Unexpected resolved target: $full" }
    $resolvedTargets += $full
}
if ($resolvedTargets.Count -ne 2 -or $resolvedTargets[0] -eq $resolvedTargets[1]) { throw 'Cleanup target list invalid' }

$drive = Get-PSDrive D
$report = [ordered]@{
    schema_version = 1
    applied = [bool]$Apply
    targets = $resolvedTargets
    old_bytes_before = [long]$scope.old_total_bytes
    drive_free_bytes_before = [long]$drive.Free
    drive_free_bytes_after = $null
    success = $false
}
if ($Apply) {
    foreach ($target in $resolvedTargets) {
        Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction Stop
        if (Test-Path -LiteralPath $target) { throw "Target still exists: $target" }
    }
    $report.drive_free_bytes_after = [long](Get-PSDrive D).Free
    $report.success = $true
} else {
    $report.success = $true
}
$name = if ($Apply) { 'cleanup_result.json' } else { 'cleanup_preflight.json' }
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $reportRoot $name) -Encoding UTF8
Write-Output ($report | ConvertTo-Json -Compress -Depth 8)
