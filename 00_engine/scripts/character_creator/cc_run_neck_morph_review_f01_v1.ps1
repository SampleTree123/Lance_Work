param(
    [string]$LibraryFile = (
        "D:\UE\Lance_Work\00_engine\scripts\character_creator" +
        "\cc_neck_morph_review_f01_v1.json"
    ),

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [int]$TimeoutSeconds = 3600,

    [int]$MaxDismissals = 300
)

$ErrorActionPreference = "Stop"
$client = (
    "D:\UE\Lance_Work\00_engine\character_creator_bridge" +
    "\cc_bridge_client.py"
)
$guard = (
    "D:\UE\Lance_Work\00_engine\character_creator_bridge" +
    "\cc_undo_dialog_guard.ps1"
)
$runtimeRoot = (
    "D:\UE\Lance_Work\00_engine\outputs" +
    "\character_creator_bridge"
)

$healthText = & python $client health
$health = $healthText | Out-String | ConvertFrom-Json
if (-not $health.healthy) {
    throw "Character Creator bridge is not healthy."
}
$processId = [int]$health.heartbeat.pid

$clientArguments = @(
    $client,
    "validate-bodies",
    "--library-file", $LibraryFile,
    "--output-dir", $OutputDir,
    "--confirm-scene-replace",
    "--no-wait",
    "--timeout", [string]$TimeoutSeconds
)
$submissionText = & python @clientArguments
if ($LASTEXITCODE -ne 0) {
    throw "F01 Neck Morph review submission failed."
}
$submission = $submissionText | Out-String | ConvertFrom-Json
$jobId = $submission.job_id
$guardLog = Join-Path (
    Join-Path $runtimeRoot "dialog_guard"
) ($jobId + "_neck_morph_review.jsonl")
$guardArguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $guard,
    "-TargetProcessId", [string]$processId,
    "-ResultPath", $submission.result_path,
    "-LogPath", $guardLog,
    "-ProgressRoot", $OutputDir,
    "-TimeoutSeconds", [string]$TimeoutSeconds,
    "-PollMilliseconds", "150",
    "-MaxDismissals", [string]$MaxDismissals
)
$guardProcess = Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList $guardArguments `
    -WindowStyle Hidden `
    -PassThru

Write-Output ("SUBMITTED neck review job={0}" -f $jobId)
try {
    $resultText = & python $client wait $jobId --timeout $TimeoutSeconds
    if ($LASTEXITCODE -ne 0) {
        throw "F01 Neck Morph review job failed."
    }
    $result = $resultText | Out-String | ConvertFrom-Json
}
finally {
    $guardProcess.WaitForExit(30000) | Out-Null
    if (-not $guardProcess.HasExited) {
        $guardProcess.Kill()
        $guardProcess.WaitForExit()
    }
}

$validation = $result.result.validation
Write-Output (
    "COMPLETED status={0} success={1} cases={2} failures={3}" -f `
        $result.status,
        $validation.success,
        $validation.requested_count,
        $validation.failure_count
)
Write-Output ("SUMMARY {0}" -f $validation.summary_path)
Write-Output ("GUARD {0}" -f $guardLog)
