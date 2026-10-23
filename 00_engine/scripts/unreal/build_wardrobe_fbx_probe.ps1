param(
    [string]$EngineRoot = 'D:\UE\UE_5.8',
    [string]$OutputDirectory = 'D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\wardrobe_average_20260906_v1\optimization_20260907\bin'
)
$ErrorActionPreference = 'Stop'
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'MSVC x64 tools are required' }
$vc = (Get-ChildItem (Join-Path $vs 'VC\Tools\MSVC') -Directory | Sort-Object Name -Descending | Select-Object -First 1).FullName
$kits = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10'
$sdk = (Get-ChildItem (Join-Path $kits 'Include') -Directory | Sort-Object Name -Descending | Select-Object -First 1).Name
$fbx = Join-Path $EngineRoot 'Engine\Source\ThirdParty\FBX\2020.2'
$boost = Join-Path $EngineRoot 'Engine\Source\ThirdParty\Boost\Deploy\boost-1.88.0\include'
$bin = Join-Path $vc 'bin\Hostx64\x64'
$oldPath = $env:PATH
$oldLib = $env:LIB
try {
    $env:PATH = "$bin;$env:PATH"
    $env:LIB = "$vc\lib\x64;$kits\Lib\$sdk\ucrt\x64;$kits\Lib\$sdk\um\x64"
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
    $arguments = @('/nologo', '/utf-8', '/std:c++17', '/EHsc', '/MD', '/O2', '/DFBXSDK_SHARED', '/DBOOST_ALL_NO_LIB',
        "/I$vc\include", "/I$kits\Include\$sdk\ucrt", "/I$kits\Include\$sdk\shared",
        "/I$kits\Include\$sdk\um", "/I$fbx\include", "/I$boost",
        "$PSScriptRoot\wardrobe_fbx_geometry_probe.cpp", "$fbx\lib\vs2017\x64\release\libfbxsdk.lib",
        "/Fo$OutputDirectory\wardrobe_fbx_geometry_probe.obj", "/Fe$OutputDirectory\wardrobe_fbx_geometry_probe.exe")
    & "$bin\cl.exe" @arguments
    if ($LASTEXITCODE -ne 0) { throw "Compiler failed: $LASTEXITCODE" }
    Copy-Item -LiteralPath "$EngineRoot\Engine\Binaries\ThirdParty\FBX\2020.2\Win64\libfbxsdk.dll" -Destination $OutputDirectory
} finally {
    $env:PATH = $oldPath
    $env:LIB = $oldLib
}
