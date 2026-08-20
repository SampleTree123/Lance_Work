param(
    [Parameter(Mandatory = $true)]
    [int]$TargetProcessId,

    [Parameter(Mandatory = $true)]
    [string]$ResultPath,

    [Parameter(Mandatory = $true)]
    [string]$LogPath,

    [string]$ProgressRoot,

    [string]$StopPath,

    [int]$TimeoutSeconds = 1800,

    [int]$PollMilliseconds = 150,

    [int]$MaxDismissals = 100
)

$ErrorActionPreference = "Stop"
$expectedWindowTitle = "Character Creator 5"
$expectedMessage = "Failed to record undo/redo step. Undo manager will restart."
$fatalExportLicenseMessage = (
    "You must first purchase the content licenses in order to export FBX files."
)
$dismissalCount = 0
$fatalDialogCount = 0
$startedAt = Get-Date
$deadline = $startedAt.AddSeconds($TimeoutSeconds)
$observedUnmatchedWindows = @{}
$consecutiveAutomationErrors = 0
$scanCount = 0

Add-Type -AssemblyName UIAutomationClient
Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

public static class CcProcessWindowEnumerator
{
    public delegate bool EnumWindowProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(
        EnumWindowProc callback,
        IntPtr lParam
    );

    [DllImport("user32.dll")]
    private static extern bool EnumChildWindows(
        IntPtr parent,
        EnumWindowProc callback,
        IntPtr lParam
    );

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(
        IntPtr hWnd,
        out uint processId
    );

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr hWnd);

    public static IntPtr[] GetAll(int targetProcessId)
    {
        var handles = new HashSet<IntPtr>();
        EnumWindows(
            delegate(IntPtr hWnd, IntPtr lParam)
            {
                uint processId;
                GetWindowThreadProcessId(hWnd, out processId);
                if (processId != (uint)targetProcessId)
                {
                    return true;
                }
                if (IsWindowVisible(hWnd))
                {
                    handles.Add(hWnd);
                }
                EnumChildWindows(
                    hWnd,
                    delegate(IntPtr child, IntPtr childParam)
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
                    },
                    IntPtr.Zero
                );
                return true;
            },
            IntPtr.Zero
        );
        var result = new IntPtr[handles.Count];
        handles.CopyTo(result);
        return result;
    }
}
"@

$logDirectory = Split-Path -Parent $LogPath
if ($logDirectory) {
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
}

function Write-GuardEvent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Event,

        [hashtable]$Data = @{}
    )

    $record = [ordered]@{
        schema_version = 1
        recorded_at = (Get-Date).ToString("o")
        event = $Event
        target_process_id = $TargetProcessId
    }
    foreach ($key in $Data.Keys) {
        $record[$key] = $Data[$key]
    }
    $record | ConvertTo-Json -Compress -Depth 8 |
        Add-Content -LiteralPath $LogPath -Encoding UTF8
}

function Read-CurrentProgress {
    if (-not $ProgressRoot -or -not (Test-Path -LiteralPath $ProgressRoot)) {
        return $null
    }
    $progressFile = Get-ChildItem -LiteralPath $ProgressRoot -Filter progress.json -File -Recurse |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $progressFile) {
        return $null
    }
    try {
        return Get-Content -LiteralPath $progressFile.FullName -Raw |
            ConvertFrom-Json
    }
    catch {
        return @{
            read_error = $_.Exception.Message
            path = $progressFile.FullName
        }
    }
}

function Write-FatalDialog {
    param(
        [Parameter(Mandatory = $true)]
        [System.Collections.IDictionary]$Record
    )

    if (-not $ProgressRoot) {
        return $null
    }
    New-Item -ItemType Directory -Path $ProgressRoot -Force | Out-Null
    $fatalPath = Join-Path $ProgressRoot "fatal_dialog.json"
    $temporaryPath = "$fatalPath.tmp.$PID"
    $Record | ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath $temporaryPath -Encoding UTF8
    Move-Item -LiteralPath $temporaryPath -Destination $fatalPath -Force
    return $fatalPath
}

function Test-ResultTerminal {
    if (-not (Test-Path -LiteralPath $ResultPath -PathType Leaf)) {
        return $false
    }
    try {
        $result = Get-Content -LiteralPath $ResultPath -Raw -Encoding UTF8 |
            ConvertFrom-Json
        $status = [string]$result.status
        if (
            $status.ToLowerInvariant() -in @(
                "succeeded",
                "failed",
                "rejected",
                "cancelled",
                "canceled"
            )
        ) {
            return $true
        }
        $phase = [string]$result.phase
        return $phase.ToLowerInvariant() -in @("complete", "blocked", "failed")
    }
    catch {
        return $false
    }
}

function Get-Descendants {
    param(
        [Parameter(Mandatory = $true)]
        [System.Windows.Automation.AutomationElement]$Window
    )

    return $Window.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        [System.Windows.Automation.Condition]::TrueCondition
    )
}

Write-GuardEvent -Event "started" -Data @{
    result_path = $ResultPath
    progress_root = $ProgressRoot
    timeout_seconds = $TimeoutSeconds
    poll_milliseconds = $PollMilliseconds
    expected_window_title = $expectedWindowTitle
    expected_message = $expectedMessage
    fatal_export_license_message = $fatalExportLicenseMessage
}

try {
    while ((Get-Date) -lt $deadline) {
        if ($StopPath -and (Test-Path -LiteralPath $StopPath)) {
            Write-GuardEvent -Event "stop_signal_observed" -Data @{
                dismissal_count = $dismissalCount
                stop_path = $StopPath
            }
            break
        }
        if (Test-ResultTerminal) {
            Write-GuardEvent -Event "terminal_result_observed" -Data @{
                dismissal_count = $dismissalCount
            }
            break
        }
        if (-not (Get-Process -Id $TargetProcessId -ErrorAction SilentlyContinue)) {
            Write-GuardEvent -Event "target_process_exited" -Data @{
                dismissal_count = $dismissalCount
            }
            break
        }

        try {
            $scanCount += 1
            $dialogs = @()
            $seenDialogHandles = @{}
            $initialWindowSnapshot = @()
            foreach (
                $nativeHandle in
                [CcProcessWindowEnumerator]::GetAll($TargetProcessId)
            ) {
                if ($nativeHandle -eq [IntPtr]::Zero) {
                    continue
                }
                try {
                    $element = (
                        [System.Windows.Automation.AutomationElement]::FromHandle(
                            $nativeHandle
                        )
                    )
                    if (
                        $scanCount -eq 1 -and
                        $element -and
                        $element.Current.ControlType -eq
                            [System.Windows.Automation.ControlType]::Window
                    ) {
                        $initialWindowSnapshot += [ordered]@{
                            native_window_handle = (
                                $nativeHandle.ToInt64()
                            )
                            name = $element.Current.Name
                            class_name = $element.Current.ClassName
                            enabled = $element.Current.IsEnabled
                            offscreen = $element.Current.IsOffscreen
                        }
                    }
                    if (
                        $element -and
                        $element.Current.ControlType -eq
                            [System.Windows.Automation.ControlType]::Window -and
                        $element.Current.Name -eq $expectedWindowTitle
                    ) {
                        $handleKey = [string]$nativeHandle.ToInt64()
                        if (-not $seenDialogHandles.ContainsKey($handleKey)) {
                            $seenDialogHandles[$handleKey] = $true
                            $dialogs += $element
                        }
                    }
                }
                catch {
                    continue
                }
            }
            if ($scanCount -eq 1) {
                Write-GuardEvent -Event "initial_visible_windows" -Data @{
                    window_count = $initialWindowSnapshot.Count
                    windows = $initialWindowSnapshot
                }
            }

            foreach ($window in $dialogs) {
                $nativeHandle = [int]$window.Current.NativeWindowHandle
                $descendants = Get-Descendants -Window $window
                $messageMatches = @()
                $fatalExportLicenseMatches = @()
                $actionButtons = @()
                $controlSnapshot = @()
                foreach ($element in $descendants) {
                    $name = $element.Current.Name
                    $controlType = $element.Current.ControlType
                    if (
                        $name -eq $expectedMessage -and
                        $controlType -eq
                            [System.Windows.Automation.ControlType]::Text
                    ) {
                        $messageMatches += $element
                    }
                    if (
                        $name -eq $fatalExportLicenseMessage -and
                        $controlType -eq
                            [System.Windows.Automation.ControlType]::Text
                    ) {
                        $fatalExportLicenseMatches += $element
                    }
                    if (
                        $controlType -eq
                            [System.Windows.Automation.ControlType]::Button -and
                        $element.Current.IsEnabled -and
                        -not $element.Current.IsOffscreen
                    ) {
                        $actionButtons += $element
                    }
                    if ($controlSnapshot.Count -lt 64 -and $name) {
                        $controlSnapshot += [ordered]@{
                            name = $name
                            control_type = $controlType.ProgrammaticName
                            class_name = $element.Current.ClassName
                            automation_id = $element.Current.AutomationId
                        }
                    }
                }

                $exactUndoWarning = (
                    $window.Current.Name -eq $expectedWindowTitle -and
                    $messageMatches.Count -eq 1 -and
                    $actionButtons.Count -eq 1 -and
                    $actionButtons[0].Current.Name -eq "OK"
                )
                $buttonNames = @(
                    $actionButtons | ForEach-Object { $_.Current.Name }
                )
                $exactFatalExportLicenseDialog = (
                    $window.Current.Name -eq $expectedWindowTitle -and
                    $window.Current.ClassName -eq "QMessageBox" -and
                    $fatalExportLicenseMatches.Count -eq 1 -and
                    $actionButtons.Count -eq 2 -and
                    $buttonNames -contains "OK" -and
                    $buttonNames -contains "Buy"
                )
                if ($exactFatalExportLicenseDialog) {
                    $okButton = $actionButtons |
                        Where-Object { $_.Current.Name -eq "OK" } |
                        Select-Object -First 1
                    $progress = Read-CurrentProgress
                    $fatalDialogCount += 1
                    $fatalRecord = [ordered]@{
                        schema_version = 1
                        recorded_at = (Get-Date).ToString("o")
                        event = "export_license_blocker"
                        message = $fatalExportLicenseMessage
                        target_process_id = $TargetProcessId
                        native_window_handle = $nativeHandle
                        window_title = $window.Current.Name
                        window_class_name = $window.Current.ClassName
                        action_button_names = $buttonNames
                        progress = $progress
                    }
                    $fatalPath = Write-FatalDialog -Record $fatalRecord
                    $invokePattern = $okButton.GetCurrentPattern(
                        [System.Windows.Automation.InvokePattern]::Pattern
                    )
                    $invokePattern.Invoke()
                    Write-GuardEvent -Event "dismissed_fatal_export_license_dialog" -Data @{
                        fatal_dialog_count = $fatalDialogCount
                        fatal_dialog_path = $fatalPath
                        native_window_handle = $nativeHandle
                        progress = $progress
                    }
                    Start-Sleep -Milliseconds 300
                    continue
                }
                if (-not $exactUndoWarning) {
                    $snapshotKey = [string]$nativeHandle
                    if (-not $observedUnmatchedWindows.ContainsKey($snapshotKey)) {
                        $observedUnmatchedWindows[$snapshotKey] = $true
                        Write-GuardEvent -Event "unmatched_cc_dialog" -Data @{
                            native_window_handle = $nativeHandle
                            window_title = $window.Current.Name
                            window_class_name = $window.Current.ClassName
                            exact_message_count = $messageMatches.Count
                            action_button_count = $actionButtons.Count
                            action_button_names = $buttonNames
                            controls = $controlSnapshot
                        }
                    }
                    continue
                }

                if ($dismissalCount -ge $MaxDismissals) {
                    Write-GuardEvent -Event "dismissal_limit_reached" -Data @{
                        dismissal_count = $dismissalCount
                        native_window_handle = $nativeHandle
                    }
                    exit 4
                }

                $progress = Read-CurrentProgress
                $invokePattern = $actionButtons[0].GetCurrentPattern(
                    [System.Windows.Automation.InvokePattern]::Pattern
                )
                $invokePattern.Invoke()
                $dismissalCount += 1
                Write-GuardEvent -Event "dismissed_undo_warning" -Data @{
                    dismissal_index = $dismissalCount
                    native_window_handle = $nativeHandle
                    progress = $progress
                }
                Start-Sleep -Milliseconds 300
            }
            $consecutiveAutomationErrors = 0
        }
        catch {
            $consecutiveAutomationErrors += 1
            if (
                $consecutiveAutomationErrors -le 5 -or
                $consecutiveAutomationErrors % 20 -eq 0
            ) {
                Write-GuardEvent -Event "transient_automation_error" -Data @{
                    consecutive_count = $consecutiveAutomationErrors
                    error_type = $_.Exception.GetType().FullName
                    error_message = $_.Exception.Message
                }
            }
            Start-Sleep -Milliseconds $PollMilliseconds
            continue
        }

        Start-Sleep -Milliseconds $PollMilliseconds
    }

    if ((Get-Date) -ge $deadline) {
        Write-GuardEvent -Event "timeout" -Data @{
            dismissal_count = $dismissalCount
        }
        exit 3
    }
}
catch {
    Write-GuardEvent -Event "guard_error" -Data @{
        dismissal_count = $dismissalCount
        error_type = $_.Exception.GetType().FullName
        error_message = $_.Exception.Message
    }
    exit 2
}

Write-GuardEvent -Event "stopped" -Data @{
    dismissal_count = $dismissalCount
}
