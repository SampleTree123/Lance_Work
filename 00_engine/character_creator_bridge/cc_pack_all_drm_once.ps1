param(
    [Parameter(Mandatory = $true)]
    [int]$TargetProcessId,

    [Parameter(Mandatory = $true)]
    [string]$ResultPath,

    [int]$TimeoutSeconds = 1800,

    [int]$PollMilliseconds = 150
)

$ErrorActionPreference = "Stop"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)

Add-Type -AssemblyName UIAutomationClient
Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

public static class CcDrmWindowEnumerator
{
    public delegate bool EnumWindowProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowProc callback, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr hWnd);

    public static IntPtr[] GetTopLevel(int targetProcessId)
    {
        var handles = new List<IntPtr>();
        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam)
        {
            uint processId;
            GetWindowThreadProcessId(hWnd, out processId);
            if (processId == (uint)targetProcessId && IsWindowVisible(hWnd))
            {
                handles.Add(hWnd);
            }
            return true;
        }, IntPtr.Zero);
        return handles.ToArray();
    }
}
"@

function Get-DrmWindow {
    foreach ($handle in [CcDrmWindowEnumerator]::GetTopLevel($TargetProcessId)) {
        try {
            $window = [System.Windows.Automation.AutomationElement]::FromHandle($handle)
            if ($window -and $window.Current.ClassName -eq "IC::CPluginDockWidget") {
                return $window
            }
        }
        catch {
        }
    }
    return $null
}

function Get-Controls($window) {
    if (-not $window) { return @() }
    return @($window.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        [System.Windows.Automation.Condition]::TrueCondition
    ))
}

function Invoke-Button($window, $name) {
    $matches = @(Get-Controls $window | Where-Object {
        $_.Current.ControlType -eq [System.Windows.Automation.ControlType]::Button -and
        $_.Current.Name -eq $name -and
        $_.Current.IsEnabled
    })
    if ($matches.Count -ne 1) { return $false }
    $pattern = $matches[0].GetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern
    )
    $pattern.Invoke()
    return $true
}

$result = [ordered]@{
    schema_version = 1
    target_process_id = $TargetProcessId
    started_at = (Get-Date).ToString("o")
    pack_all_clicked = $false
    close_clicked = $false
    observed_need_pack_counts = @()
}

try {
    while ((Get-Date) -lt $deadline) {
        if (-not (Get-Process -Id $TargetProcessId -ErrorAction SilentlyContinue)) {
            break
        }
        $window = Get-DrmWindow
        if (-not $window) {
            Start-Sleep -Milliseconds $PollMilliseconds
            continue
        }
        $controls = Get-Controls $window
        $needPackCount = @($controls | Where-Object { $_.Current.Name -eq "Need Pack" }).Count
        $result.observed_need_pack_counts += $needPackCount
        if (-not $result.pack_all_clicked) {
            if (Invoke-Button $window "Pack All") {
                $result.pack_all_clicked = $true
                $result.pack_all_clicked_at = (Get-Date).ToString("o")
                Start-Sleep -Seconds 2
            }
            continue
        }
        if ($needPackCount -eq 0 -and (Invoke-Button $window "Close")) {
            $result.close_clicked = $true
            $result.close_clicked_at = (Get-Date).ToString("o")
            break
        }
        Start-Sleep -Milliseconds $PollMilliseconds
    }
}
catch {
    $result.error = $_.Exception.Message
}

$result.finished_at = (Get-Date).ToString("o")
$result.success = [bool]($result.pack_all_clicked -and $result.close_clicked)
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ResultPath -Encoding UTF8
if (-not $result.success) { exit 1 }
