param(
    [Parameter(Mandatory=$true)][int]$CoordinatorId,
    [Parameter(Mandatory=$true)][string]$LibraryDir,
    [Parameter(Mandatory=$true)][string]$ReportRoot,
    [Parameter(Mandatory=$true)][string]$RunRoot,
    [int]$TimeoutSeconds = 3600,
    [ValidateSet('interleaved', 'export_only')][string]$Schedule
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$script = Join-Path $PSScriptRoot 'run_wardrobe_library_v1.py'
$run = (Resolve-Path -LiteralPath $RunRoot).Path
$library = (Resolve-Path -LiteralPath $LibraryDir).Path
$reports = (Resolve-Path -LiteralPath $ReportRoot).Path
$statePath = Join-Path $run 'state.json'
$initial = Get-CimInstance Win32_Process -Filter "ProcessId=$CoordinatorId"
if (-not $initial -or $initial.Name -notmatch '^python(w)?\.exe$' -or
    $initial.CommandLine -notlike '*run_wardrobe_library_v1.py*' -or
    $initial.CommandLine -notlike "*$([IO.Path]::GetFileName($run))*") {
    throw 'The target is not the expected wardrobe coordinator; no process was stopped.'
}
$python = $initial.ExecutablePath
$created = $initial.CreationDate
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$checkpoint = $null
while ((Get-Date) -lt $deadline) {
    $state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($state.pid -ne $CoordinatorId) { throw 'Coordinator identity changed.' }
    if ($state.status -in @('blocked', 'transfer_complete', 'export_complete')) { throw "Coordinator is $($state.status); inspect it first." }
    if ($state.operation -eq 'ue_normal_exit' -and $state.status -eq 'running' -and
        -not (Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue)) {
        try {
            $log = Get-Content -LiteralPath $state.log -Raw -Encoding UTF8
            $envelope = $log.Substring($log.IndexOf("`n") + 1) | ConvertFrom-Json
            if ($envelope.command_result.success -eq $true) {
                $checkpoint = $state
                break
            }
        } catch {
            # The remote command may still be flushing its completed JSON envelope.
        }
    }
    Start-Sleep -Milliseconds 200
}
if (-not $checkpoint) { throw 'No clean UE-exit checkpoint was reached; nothing stopped.' }
$target = Get-CimInstance Win32_Process -Filter "ProcessId=$CoordinatorId"
if (-not $target -or $target.CreationDate -ne $created -or $target.CommandLine -ne $initial.CommandLine) {
    throw 'Target process changed before handoff.'
}
$children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$CoordinatorId" | Select-Object -ExpandProperty ProcessId)
# Only the verified Python coordinator is stopped. UE already saved and exited;
# CC and any finishing remote-command child are never terminated here.
Stop-Process -Id $CoordinatorId
Wait-Process -Id $CoordinatorId -Timeout 30 -ErrorAction SilentlyContinue
foreach ($child in $children) {
    if (Get-Process -Id $child -ErrorAction SilentlyContinue) {
        try {
            Wait-Process -Id $child -Timeout 180 -ErrorAction Stop
        } catch {
            # A finishing child can disappear between Get-Process and Wait-Process.
            if ($_.FullyQualifiedErrorId -notlike 'NoProcessFoundForGivenId,*') { throw }
        }
    }
}
# The old coordinator may have started the next UE process just as the handoff
# checkpoint was observed. Await readiness instead of launching another editor.
if (Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue) {
    & $python (Join-Path $PSScriptRoot 'ue_remote_exec.py') --project datatry_02 --discovery-timeout 180 `
        --command "import unreal; print('HANDOFF_EDITOR_READY')"
    if ($LASTEXITCODE -ne 0) { throw 'Existing editor is not ready after handoff.' }
}
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$out = Join-Path $run "background_${stamp}_stdout.log"
$err = Join-Path $run "background_${stamp}_stderr.log"
function Quote-Argument([string]$Value) {
    if ($Value.Contains('"')) { throw 'Quote in argument path is unsupported.' }
    return '"' + $Value + '"'
}
$arguments = @((Quote-Argument $script), '--library-dir', (Quote-Argument $library),
               '--report-root', (Quote-Argument $reports), '--run-root', (Quote-Argument $run), '--execute') -join ' '
if ($Schedule) { $arguments += ' --schedule ' + $Schedule }
$background = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $repo `
    -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
$record = [ordered]@{
    schema_version = 1
    handed_off_at = (Get-Date).ToString('o')
    checkpoint = $checkpoint
    previous_coordinator_pid = $CoordinatorId
    new_coordinator_pid = $background.Id
    stdout = $out
    stderr = $err
    ue_forced_stop = $false
    cc_lifecycle_changed = $false
    transfer_complete = $false
    requested_schedule = $Schedule
}
[IO.File]::WriteAllText((Join-Path $run "background_handoff_${stamp}.json"),
    ($record | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
$record | ConvertTo-Json -Depth 10
