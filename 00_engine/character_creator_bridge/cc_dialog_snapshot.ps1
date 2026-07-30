param(
    [Parameter(Mandatory = $true)]
    [int]$TargetProcessId,

    [string]$OutputPath
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName UIAutomationClient
Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public sealed class CcNativeWindowSnapshot
{
    public long HandleValue;
    public long ParentHandle;
    public long OwnerHandle;
    public string Title;
    public string ClassName;
    public bool Visible;
    public bool Enabled;
}

public static class CcNativeWindowSnapshotter
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

    [DllImport("user32.dll")]
    private static extern bool IsWindowEnabled(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(
        IntPtr hWnd,
        StringBuilder text,
        int maximum
    );

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetClassName(
        IntPtr hWnd,
        StringBuilder text,
        int maximum
    );

    [DllImport("user32.dll")]
    private static extern IntPtr GetParent(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern IntPtr GetWindow(IntPtr hWnd, uint command);

    private static CcNativeWindowSnapshot Capture(IntPtr hWnd)
    {
        var title = new StringBuilder(512);
        var className = new StringBuilder(256);
        GetWindowText(hWnd, title, title.Capacity);
        GetClassName(hWnd, className, className.Capacity);
        return new CcNativeWindowSnapshot
        {
            HandleValue = hWnd.ToInt64(),
            ParentHandle = GetParent(hWnd).ToInt64(),
            OwnerHandle = GetWindow(hWnd, 4).ToInt64(),
            Title = title.ToString(),
            ClassName = className.ToString(),
            Visible = IsWindowVisible(hWnd),
            Enabled = IsWindowEnabled(hWnd)
        };
    }

    public static CcNativeWindowSnapshot[] GetAll(int targetProcessId)
    {
        var snapshots = new Dictionary<long, CcNativeWindowSnapshot>();
        EnumWindows(
            delegate(IntPtr hWnd, IntPtr lParam)
            {
                uint processId;
                GetWindowThreadProcessId(hWnd, out processId);
                if (processId != (uint)targetProcessId)
                {
                    return true;
                }
                snapshots[hWnd.ToInt64()] = Capture(hWnd);
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
                            snapshots[child.ToInt64()] = Capture(child);
                        }
                        return true;
                    },
                    IntPtr.Zero
                );
                return true;
            },
            IntPtr.Zero
        );
        var result = new CcNativeWindowSnapshot[snapshots.Count];
        snapshots.Values.CopyTo(result, 0);
        return result;
    }
}
"@

function Get-AutomationSnapshot {
    param(
        [Parameter(Mandatory = $true)]
        [long]$HandleValue
    )

    try {
        $element = (
            [System.Windows.Automation.AutomationElement]::FromHandle(
                [IntPtr]::new($HandleValue)
            )
        )
        if (-not $element) {
            return $null
        }
        $controls = @()
        $descendants = $element.FindAll(
            [System.Windows.Automation.TreeScope]::Descendants,
            [System.Windows.Automation.Condition]::TrueCondition
        )
        foreach ($descendant in $descendants) {
            if ($controls.Count -ge 128) {
                break
            }
            $current = $descendant.Current
            if (
                -not $current.Name -and
                -not $current.AutomationId -and
                -not $current.ClassName
            ) {
                continue
            }
            $controls += [ordered]@{
                name = $current.Name
                control_type = $current.ControlType.ProgrammaticName
                class_name = $current.ClassName
                automation_id = $current.AutomationId
                enabled = $current.IsEnabled
                offscreen = $current.IsOffscreen
            }
        }
        return [ordered]@{
            name = $element.Current.Name
            control_type = (
                $element.Current.ControlType.ProgrammaticName
            )
            class_name = $element.Current.ClassName
            automation_id = $element.Current.AutomationId
            enabled = $element.Current.IsEnabled
            offscreen = $element.Current.IsOffscreen
            controls = $controls
        }
    }
    catch {
        return [ordered]@{
            error_type = $_.Exception.GetType().FullName
            error_message = $_.Exception.Message
        }
    }
}

$windows = @()
foreach (
    $native in
    [CcNativeWindowSnapshotter]::GetAll($TargetProcessId)
) {
    if (
        -not $native.Visible -and
        -not $native.Title -and
        $native.ClassName -notin @(
            "QDialog",
            "QMessageBox",
            "QProgressDialog"
        )
    ) {
        continue
    }
    $windows += [ordered]@{
        handle = $native.HandleValue
        parent_handle = $native.ParentHandle
        owner_handle = $native.OwnerHandle
        title = $native.Title
        class_name = $native.ClassName
        visible = $native.Visible
        enabled = $native.Enabled
        automation = Get-AutomationSnapshot -HandleValue (
            $native.HandleValue
        )
    }
}

$result = [ordered]@{
    schema_version = 1
    captured_at = (Get-Date).ToString("o")
    target_process_id = $TargetProcessId
    window_count = $windows.Count
    windows = $windows
}
$json = $result | ConvertTo-Json -Depth 12
if ($OutputPath) {
    $parent = Split-Path -Parent $OutputPath
    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force |
            Out-Null
    }
    $json | Set-Content -LiteralPath $OutputPath -Encoding UTF8
}
$json
