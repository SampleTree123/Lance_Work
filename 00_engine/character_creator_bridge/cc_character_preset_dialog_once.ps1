param(
    [Parameter(Mandatory = $true)]
    [int]$TargetProcessId,

    [Parameter(Mandatory = $true)]
    [string]$LogPath,

    [int]$TimeoutSeconds = 30,

    [int]$PollMilliseconds = 100
)

$ErrorActionPreference = "Stop"
$expectedWindowTitle = "Apply Character Preset"
$expectedWindowClass = (
    "IC::CApplyNailOrEyelashAavatarPresetDialog"
)
$requiredCheckboxes = @(
    "Apply Morph",
    "Apply Textures",
    "Restore neutral lash strip before application."
)
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)

Add-Type -AssemblyName UIAutomationClient
Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

public static class CcCharacterPresetWindowEnumerator
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
                handles.Add(hWnd);
                EnumChildWindows(
                    hWnd,
                    delegate(IntPtr child, IntPtr childParam)
                    {
                        uint childProcessId;
                        GetWindowThreadProcessId(
                            child,
                            out childProcessId
                        );
                        if (childProcessId == (uint)targetProcessId)
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
    New-Item -ItemType Directory -Path $logDirectory -Force |
        Out-Null
}

function Write-Result {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Status,

        [hashtable]$Data = @{}
    )

    $record = [ordered]@{
        schema_version = 1
        recorded_at = (Get-Date).ToString("o")
        status = $Status
        target_process_id = $TargetProcessId
        expected_window_title = $expectedWindowTitle
        expected_window_class = $expectedWindowClass
        required_checkboxes = $requiredCheckboxes
    }
    foreach ($key in $Data.Keys) {
        $record[$key] = $Data[$key]
    }
    $record | ConvertTo-Json -Depth 10 |
        Set-Content -LiteralPath $LogPath -Encoding UTF8
    $record
}

function Get-CurrentToggleState {
    param(
        [Parameter(Mandatory = $true)]
        [System.Windows.Automation.AutomationElement]$Element
    )

    $pattern = $Element.GetCurrentPattern(
        [System.Windows.Automation.TogglePattern]::Pattern
    )
    return $pattern.Current.ToggleState
}

try {
    while ((Get-Date) -lt $deadline) {
        $matches = @()
        foreach (
            $handle in
            [CcCharacterPresetWindowEnumerator]::GetAll(
                $TargetProcessId
            )
        ) {
            try {
                $element = (
                    [System.Windows.Automation.AutomationElement]::FromHandle(
                        $handle
                    )
                )
                if (
                    $element -and
                    $element.Current.ControlType -eq
                        [System.Windows.Automation.ControlType]::Window -and
                    $element.Current.Name -eq $expectedWindowTitle -and
                    $element.Current.ClassName -eq $expectedWindowClass -and
                    $element.Current.IsEnabled -and
                    -not $element.Current.IsOffscreen
                ) {
                    $matches += $element
                }
            }
            catch {
                continue
            }
        }
        if ($matches.Count -gt 1) {
            Write-Result -Status "ambiguous_dialogs" -Data @{
                match_count = $matches.Count
            } | Out-Null
            exit 3
        }
        if ($matches.Count -eq 0) {
            Start-Sleep -Milliseconds $PollMilliseconds
            continue
        }

        $window = $matches[0]
        $descendants = $window.FindAll(
            [System.Windows.Automation.TreeScope]::Descendants,
            [System.Windows.Automation.Condition]::TrueCondition
        )
        $checkboxes = @{}
        $applyButtons = @()
        $cancelButtons = @()
        foreach ($element in $descendants) {
            if (
                $element.Current.ControlType -eq
                    [System.Windows.Automation.ControlType]::CheckBox -and
                $requiredCheckboxes -contains $element.Current.Name
            ) {
                if (-not $checkboxes.ContainsKey($element.Current.Name)) {
                    $checkboxes[$element.Current.Name] = @()
                }
                $checkboxes[$element.Current.Name] += $element
            }
            if (
                $element.Current.ControlType -eq
                    [System.Windows.Automation.ControlType]::Button -and
                $element.Current.Name -eq "Apply"
            ) {
                $applyButtons += $element
            }
            if (
                $element.Current.ControlType -eq
                    [System.Windows.Automation.ControlType]::Button -and
                $element.Current.Name -eq "Cancel"
            ) {
                $cancelButtons += $element
            }
        }

        $invalidCheckboxes = @(
            $requiredCheckboxes |
                Where-Object {
                    -not $checkboxes.ContainsKey($_) -or
                    $checkboxes[$_].Count -ne 1
                }
        )
        if (
            $invalidCheckboxes.Count -gt 0 -or
            $applyButtons.Count -ne 1 -or
            $cancelButtons.Count -ne 1
        ) {
            Write-Result -Status "control_mismatch" -Data @{
                invalid_checkboxes = $invalidCheckboxes
                apply_button_count = $applyButtons.Count
                cancel_button_count = $cancelButtons.Count
            } | Out-Null
            exit 4
        }

        $before = [ordered]@{}
        foreach ($name in $requiredCheckboxes) {
            $checkbox = $checkboxes[$name][0]
            $before[$name] = [string](
                Get-CurrentToggleState -Element $checkbox
            )
            if (
                (Get-CurrentToggleState -Element $checkbox) -ne
                [System.Windows.Automation.ToggleState]::On
            ) {
                $toggle = $checkbox.GetCurrentPattern(
                    [System.Windows.Automation.TogglePattern]::Pattern
                )
                $toggle.Toggle()
            }
        }
        Start-Sleep -Milliseconds 100
        $after = [ordered]@{}
        foreach ($name in $requiredCheckboxes) {
            $after[$name] = [string](
                Get-CurrentToggleState -Element (
                    $checkboxes[$name][0]
                )
            )
        }
        if (
            @(
                $after.Values |
                    Where-Object {
                        $_ -ne [string](
                            [System.Windows.Automation.ToggleState]::On
                        )
                    }
            ).Count -gt 0
        ) {
            Write-Result -Status "checkbox_configuration_failed" -Data @{
                checkbox_state_before = $before
                checkbox_state_after = $after
            } | Out-Null
            exit 5
        }

        $invoke = $applyButtons[0].GetCurrentPattern(
            [System.Windows.Automation.InvokePattern]::Pattern
        )
        $invoke.Invoke()
        Write-Result -Status "applied" -Data @{
            native_window_handle = (
                $window.Current.NativeWindowHandle
            )
            checkbox_state_before = $before
            checkbox_state_after = $after
        } | Out-Null
        exit 0
    }

    Write-Result -Status "timeout" | Out-Null
    exit 6
}
catch {
    Write-Result -Status "error" -Data @{
        error_type = $_.Exception.GetType().FullName
        error_message = $_.Exception.Message
    } | Out-Null
    exit 7
}
