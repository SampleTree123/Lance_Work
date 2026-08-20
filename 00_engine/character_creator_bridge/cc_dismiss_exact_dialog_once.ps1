param(
    [Parameter(Mandatory = $true)]
    [int]$TargetProcessId,

    [Parameter(Mandatory = $true)]
    [string]$ExpectedMessage,

    [Parameter(Mandatory = $true)]
    [string]$ButtonName,

    [Parameter(Mandatory = $true)]
    [string]$ResultPath,

    [int]$TimeoutSeconds = 30,

    [int]$PollMilliseconds = 100
)

$ErrorActionPreference = "Stop"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)

Add-Type -AssemblyName UIAutomationClient
Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

public static class CcExactDialogWindowEnumerator
{
    public delegate bool EnumWindowProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowProc callback, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern bool EnumChildWindows(IntPtr parent, EnumWindowProc callback, IntPtr lParam);

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
                EnumChildWindows(hWnd, delegate(IntPtr child, IntPtr childParam)
                {
                    uint childProcessId;
                    GetWindowThreadProcessId(child, out childProcessId);
                    if (
                        childProcessId == (uint)targetProcessId &&
                        IsWindowVisible(child)
                    )
                    {
                        handles.Add(child);
                    }
                    return true;
                }, IntPtr.Zero);
            }
            return true;
        }, IntPtr.Zero);
        return handles.ToArray();
    }
}
"@

$resultDirectory = Split-Path -Parent $ResultPath
if ($resultDirectory) {
    New-Item -ItemType Directory -Path $resultDirectory -Force | Out-Null
}

$result = [ordered]@{
    schema_version = 1
    target_process_id = $TargetProcessId
    expected_message = $ExpectedMessage
    button_name = $ButtonName
    started_at = (Get-Date).ToString("o")
    matched = $false
    clicked = $false
    observed_windows = @()
}

try {
    while ((Get-Date) -lt $deadline) {
        if (-not (Get-Process -Id $TargetProcessId -ErrorAction SilentlyContinue)) {
            $result.error = "Target process exited"
            break
        }
        foreach ($nativeHandle in [CcExactDialogWindowEnumerator]::GetTopLevel($TargetProcessId)) {
            $window = [System.Windows.Automation.AutomationElement]::FromHandle($nativeHandle)
            if (-not $window) {
                continue
            }
            $descendants = $window.FindAll(
                [System.Windows.Automation.TreeScope]::Descendants,
                [System.Windows.Automation.Condition]::TrueCondition
            )
            $messageCount = 0
            $buttons = @()
            $textNames = @()
            foreach ($element in $descendants) {
                if ($element.Current.Name -eq $ExpectedMessage) {
                    $messageCount += 1
                }
                if (
                    $element.Current.Name -and
                    $textNames.Count -lt 20
                ) {
                    $textNames += [string]$element.Current.Name
                }
                if (
                    $element.Current.ControlType -eq
                        [System.Windows.Automation.ControlType]::Button
                ) {
                    $buttons += $element
                }
            }
            if ($result.observed_windows.Count -lt 30) {
                $result.observed_windows += [ordered]@{
                    native_window_handle = $nativeHandle.ToInt64()
                    name = $window.Current.Name
                    class_name = $window.Current.ClassName
                    message_match_count = $messageCount
                    button_names = @($buttons | ForEach-Object { $_.Current.Name })
                    descendant_names = $textNames
                }
            }
            $matches = @($buttons | Where-Object { $_.Current.Name -eq $ButtonName })
            if ($messageCount -ne 1 -or $matches.Count -ne 1) {
                continue
            }
            $result.matched = $true
            $result.window_title = $window.Current.Name
            $result.window_class_name = $window.Current.ClassName
            $result.native_window_handle = $nativeHandle.ToInt64()
            $pattern = $matches[0].GetCurrentPattern(
                [System.Windows.Automation.InvokePattern]::Pattern
            )
            $pattern.Invoke()
            $result.clicked = $true
            break
        }
        if ($result.clicked) {
            break
        }
        Start-Sleep -Milliseconds $PollMilliseconds
    }
}
catch {
    $result.error = $_.Exception.Message
}

$result.finished_at = (Get-Date).ToString("o")
$result.success = [bool]$result.clicked
$result | ConvertTo-Json -Depth 6 |
    Set-Content -LiteralPath $ResultPath -Encoding UTF8
if (-not $result.success) {
    exit 1
}
