[CmdletBinding()]
param(
    [string]$HostAddress = '127.0.0.1',
    [int]$Port = 8765,
    [string]$Root = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
    [switch]$Restart
)

$ErrorActionPreference = 'Stop'
$portalRoot = $PSScriptRoot
$pidPath = Join-Path $portalRoot '.portal_server.pid'
$stdoutPath = Join-Path $portalRoot 'serve_8765.log'
$stderrPath = Join-Path $portalRoot 'serve_8765.err.log'
$healthUrl = "http://${HostAddress}:${Port}/00_engine/visualization_portal/index.html"

function Test-PortalHealth {
    try {
        $response = Invoke-WebRequest `
            -Uri $healthUrl `
            -TimeoutSec 3 `
            -UseBasicParsing
        return [int]$response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

if (-not $Restart -and (Test-PortalHealth)) {
    Write-Output "Portal already healthy: $healthUrl"
    exit 0
}

if (Test-Path -LiteralPath $pidPath) {
    $trackedPid = [int](Get-Content -LiteralPath $pidPath -Raw).Trim()
    $trackedProcess = Get-Process -Id $trackedPid -ErrorAction SilentlyContinue
    if ($null -ne $trackedProcess -and $trackedProcess.ProcessName -like 'python*') {
        Stop-Process -Id $trackedPid -Force
        $null = $trackedProcess.WaitForExit(5000)
    }
    Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
}

$python = (Get-Command python -ErrorAction Stop).Source
$arguments = @(
    (Join-Path $portalRoot 'serve.py'),
    '--host', $HostAddress,
    '--port', $Port,
    '--root', $Root
)
$quotedArguments = $arguments | ForEach-Object {
    '"' + ([string]$_).Replace('"', '\"') + '"'
}
$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $python
$startInfo.Arguments = $quotedArguments -join ' '
$startInfo.WorkingDirectory = $portalRoot
$startInfo.UseShellExecute = $true
$startInfo.CreateNoWindow = $false
$startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$process = [System.Diagnostics.Process]::Start($startInfo)
if ($null -eq $process) {
    throw 'Could not start the portal process.'
}
Set-Content -LiteralPath $pidPath -Value $process.Id -Encoding ascii

$deadline = (Get-Date).AddSeconds(20)
do {
    Start-Sleep -Milliseconds 250
    if (Test-PortalHealth) {
        Write-Output "Portal started (PID $($process.Id)): $healthUrl"
        exit 0
    }
    if ($process.HasExited) {
        $errorText = Get-Content -LiteralPath $stderrPath -Raw -ErrorAction SilentlyContinue
        throw "Portal process exited before becoming healthy. $errorText"
    }
} while ((Get-Date) -lt $deadline)

Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
throw "Portal did not become healthy within 20 seconds: $healthUrl"
