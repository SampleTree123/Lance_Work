param(
    [Parameter(Mandatory = $true)]
    [int]$TargetProcessId,

    [Parameter(Mandatory = $true)]
    [string]$ReadyPath,

    [Parameter(Mandatory = $true)]
    [string]$LogPath,

    [int]$TimeoutSeconds = 90,

    [int]$PollMilliseconds = 75
)

$ErrorActionPreference = "Stop"
$expectedTitle = "Character Creator 5"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)

Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public sealed class CCDialogWindowInfo
{
    public long HandleValue;
    public string Title;
    public string ClassName;
    public long OwnerHandle;
    public int Width;
    public int Height;
}

public static class CCDialogNative
{
    private delegate bool EnumWindowsProc(IntPtr handle, IntPtr parameter);

    [StructLayout(LayoutKind.Sequential)]
    private struct Rect
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(
        EnumWindowsProc callback,
        IntPtr parameter
    );

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(
        IntPtr handle,
        out uint processId
    );

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr handle);

    [DllImport("user32.dll")]
    private static extern bool IsWindow(IntPtr handle);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(
        IntPtr handle,
        StringBuilder text,
        int maximum
    );

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetClassName(
        IntPtr handle,
        StringBuilder text,
        int maximum
    );

    [DllImport("user32.dll")]
    private static extern bool GetWindowRect(
        IntPtr handle,
        out Rect rectangle
    );

    [DllImport("user32.dll")]
    private static extern IntPtr GetWindow(IntPtr handle, uint command);

    [DllImport("user32.dll")]
    private static extern bool PostMessage(
        IntPtr handle,
        uint message,
        IntPtr wParam,
        IntPtr lParam
    );

    public static CCDialogWindowInfo[] Snapshot(int targetProcessId)
    {
        var windows = new List<CCDialogWindowInfo>();
        EnumWindows(delegate(IntPtr handle, IntPtr parameter)
        {
            uint processId;
            GetWindowThreadProcessId(handle, out processId);
            if (
                processId != (uint)targetProcessId ||
                !IsWindowVisible(handle)
            )
            {
                return true;
            }

            var title = new StringBuilder(512);
            var className = new StringBuilder(256);
            Rect rectangle;
            GetWindowText(handle, title, title.Capacity);
            GetClassName(handle, className, className.Capacity);
            GetWindowRect(handle, out rectangle);
            windows.Add(new CCDialogWindowInfo
            {
                HandleValue = handle.ToInt64(),
                Title = title.ToString(),
                ClassName = className.ToString(),
                OwnerHandle = GetWindow(handle, 4).ToInt64(),
                Width = rectangle.Right - rectangle.Left,
                Height = rectangle.Bottom - rectangle.Top
            });
            return true;
        }, IntPtr.Zero);
        return windows.ToArray();
    }

    public static bool ConfirmDefault(long handleValue)
    {
        var handle = new IntPtr(handleValue);
        var down = PostMessage(
            handle,
            0x0100,
            new IntPtr(13),
            IntPtr.Zero
        );
        var up = PostMessage(
            handle,
            0x0101,
            new IntPtr(13),
            IntPtr.Zero
        );
        return down && up;
    }

    public static bool IsVisible(long handleValue)
    {
        var handle = new IntPtr(handleValue);
        return IsWindow(handle) && IsWindowVisible(handle);
    }
}
"@

$logDirectory = Split-Path -Parent $LogPath
$readyDirectory = Split-Path -Parent $ReadyPath
if ($logDirectory) {
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
}
if ($readyDirectory) {
    New-Item -ItemType Directory -Path $readyDirectory -Force | Out-Null
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

try {
    $baseline = @(
        [CCDialogNative]::Snapshot($TargetProcessId) |
            ForEach-Object { $_.HandleValue }
    )
    Write-GuardEvent -Event "ready" -Data @{
        baseline_handle_count = $baseline.Count
        baseline_handles = $baseline
        expected_title = $expectedTitle
    }
    [ordered]@{
        schema_version = 1
        ready_at = (Get-Date).ToString("o")
        target_process_id = $TargetProcessId
    } | ConvertTo-Json -Depth 4 |
        Set-Content -LiteralPath $ReadyPath -Encoding UTF8

    while ((Get-Date) -lt $deadline) {
        $newWindows = @(
            [CCDialogNative]::Snapshot($TargetProcessId) |
                Where-Object {
                    $baseline -notcontains $_.HandleValue
                }
        )
        $matches = @(
            $newWindows |
                Where-Object {
                    $_.Title -eq $expectedTitle -and
                    $_.Width -ge 500 -and
                    $_.Width -le 1600 -and
                    $_.Height -ge 160 -and
                    $_.Height -le 800
                }
        )
        if ($matches.Count -gt 1) {
            Write-GuardEvent -Event "ambiguous_dialogs" -Data @{
                matches = $matches
                new_windows = $newWindows
            }
            exit 3
        }
        if ($matches.Count -eq 1) {
            $window = $matches[0]
            Start-Sleep -Milliseconds 250
            $posted = [CCDialogNative]::ConfirmDefault(
                $window.HandleValue
            )
            Write-GuardEvent -Event "default_confirmation_sent" -Data @{
                posted = $posted
                window = $window
                new_windows = $newWindows
            }
            if (-not $posted) {
                exit 4
            }

            $closeDeadline = (Get-Date).AddSeconds(5)
            while (
                (Get-Date) -lt $closeDeadline -and
                [CCDialogNative]::IsVisible($window.HandleValue)
            ) {
                Start-Sleep -Milliseconds 75
            }
            if ([CCDialogNative]::IsVisible($window.HandleValue)) {
                Write-GuardEvent -Event "dialog_did_not_close" -Data @{
                    window = $window
                }
                exit 5
            }
            Write-GuardEvent -Event "confirmed" -Data @{
                window = $window
            }
            exit 0
        }
        Start-Sleep -Milliseconds $PollMilliseconds
    }

    Write-GuardEvent -Event "timeout" -Data @{
        final_windows = [CCDialogNative]::Snapshot($TargetProcessId)
    }
    exit 6
}
catch {
    Write-GuardEvent -Event "guard_error" -Data @{
        error_type = $_.Exception.GetType().FullName
        error_message = $_.Exception.Message
    }
    exit 7
}
