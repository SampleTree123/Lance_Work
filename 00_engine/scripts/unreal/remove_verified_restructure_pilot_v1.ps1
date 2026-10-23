$ErrorActionPreference = 'Stop'
$reportRoot = 'D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\asset_restructure_full_20260929_v1'
$audit = Get-Content -LiteralPath (Join-Path $reportRoot 'pilot_cleanup_audit.json') -Raw | ConvertFrom-Json
if (-not $audit.success -or $audit.pilot_package_count -ne 35 -or @($audit.external_referencers.PSObject.Properties).Count -ne 0) {
    throw 'Pilot cleanup audit did not pass'
}
if (Get-Process UnrealEditor, UnrealEditor-Cmd -ErrorAction SilentlyContinue) { throw 'UE is running' }
$content = [IO.Path]::GetFullPath('D:\UE\projects\datatry_02\Content').TrimEnd('\')
$expected = [IO.Path]::GetFullPath('D:\UE\projects\datatry_02\Content\DataMake\CharacterFactory\RestructurePilot').TrimEnd('\')
$target = (Resolve-Path -LiteralPath $expected).ProviderPath.TrimEnd('\')
if ($target -ne $expected -or -not $target.StartsWith($content + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw "Unexpected pilot target: $target"
}
$files = @(Get-ChildItem -LiteralPath $target -File -Recurse)
if ($files.Count -ne 35 -or @($files | Where-Object Extension -ne '.uasset').Count -ne 0) {
    throw 'Pilot directory contains unexpected files'
}
$bytes = [long](($files | Measure-Object Length -Sum).Sum)
Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction Stop
if (Test-Path -LiteralPath $target) { throw 'Pilot target remains after cleanup' }
$report = @{ success = $true; removed_packages = 35; removed_bytes = $bytes; target = $target }
$report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $reportRoot 'pilot_cleanup_result.json') -Encoding UTF8
Write-Output ($report | ConvertTo-Json -Compress)
