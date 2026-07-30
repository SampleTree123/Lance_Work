param(
    [string]$CharacterCreatorRoot = 'D:\CharacterCreator\Character Creator 5'
)

$ErrorActionPreference = 'Stop'

$sourceDirectory = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'plugin'))
$sourceMain = Join-Path $sourceDirectory 'main.py'
$ccRoot = [System.IO.Path]::GetFullPath($CharacterCreatorRoot)
$executable = Join-Path $ccRoot 'Bin64\CharacterCreator.exe'
$openPluginRoot = [System.IO.Path]::GetFullPath((Join-Path $ccRoot 'Bin64\OpenPlugin'))
$targetDirectory = [System.IO.Path]::GetFullPath((Join-Path $openPluginRoot 'LanceCCBridge'))
$targetMain = Join-Path $targetDirectory 'main.py'

if (-not (Test-Path -LiteralPath $sourceMain -PathType Leaf)) {
    throw "Bridge source is missing: $sourceMain"
}
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "Character Creator executable is missing: $executable"
}
if (-not $targetDirectory.StartsWith($openPluginRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing target outside OpenPlugin: $targetDirectory"
}

New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null
$temporaryMain = Join-Path $targetDirectory ('.main.py.' + [Guid]::NewGuid().ToString('N') + '.tmp')

try {
    Copy-Item -LiteralPath $sourceMain -Destination $temporaryMain
    Move-Item -LiteralPath $temporaryMain -Destination $targetMain -Force
}
finally {
    if (Test-Path -LiteralPath $temporaryMain) {
        Remove-Item -LiteralPath $temporaryMain -Force
    }
}

$sourceHash = (Get-FileHash -LiteralPath $sourceMain -Algorithm SHA256).Hash.ToLowerInvariant()
$installedHash = (Get-FileHash -LiteralPath $targetMain -Algorithm SHA256).Hash.ToLowerInvariant()
if ($sourceHash -ne $installedHash) {
    throw "Installed plugin hash does not match the source"
}

$manifest = [ordered]@{
    schema_version = 1
    plugin = 'LanceCCBridge'
    installed_at = [DateTimeOffset]::Now.ToString('o')
    source = $sourceMain
    target = $targetMain
    sha256 = $installedHash
}
$manifestPath = Join-Path $targetDirectory 'install_manifest.json'
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

[ordered]@{
    success = $true
    target = $targetMain
    manifest = $manifestPath
    sha256 = $installedHash
    restart_required = $true
} | ConvertTo-Json -Depth 4
