param(
    [Parameter(Mandatory = $true)]
    [string[]]$PresetIds,

    [string]$LibraryFile = (
        "D:\UE\Lance_Work\00_engine\scripts\character_creator" +
        "\cc_head_bodyfit_scale_pilot_v1.json"
    ),

    [string]$OutputRoot = (
        "D:\UE\Lance_Work\00_engine\outputs" +
        "\character_creator_bridge\artifacts" +
        "\head_bodyfit_scale_coarse_v1_20260731_01"
    ),

    [int]$TimeoutSeconds = 900
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

function Read-BridgeHealth {
    for ($attempt = 1; $attempt -le 20; $attempt++) {
        $healthText = & python $client health 2>$null
        $health = $healthText | Out-String | ConvertFrom-Json
        if ($health.healthy) {
            return $health
        }
        Start-Sleep -Milliseconds 500
    }
    throw "Character Creator bridge did not become healthy."
}

foreach ($presetId in $PresetIds) {
    $health = Read-BridgeHealth
    $processId = [int]$health.heartbeat.pid
    $chunkName = "chunk_" + $presetId.ToLowerInvariant()
    $outputDir = Join-Path $OutputRoot $chunkName

    $submissionText = & python $client validate-bodies `
        --library-file $LibraryFile `
        --preset-id $presetId `
        --output-dir $outputDir `
        --confirm-scene-replace `
        --no-wait `
        --timeout $TimeoutSeconds
    if ($LASTEXITCODE -ne 0) {
        throw "Submission failed for $presetId."
    }
    $submission = $submissionText | Out-String | ConvertFrom-Json
    $jobId = $submission.job_id
    $guardLog = Join-Path (
        Join-Path $runtimeRoot "dialog_guard"
    ) ($jobId + "_manual.jsonl")
    $guardArguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $guard,
        "-TargetProcessId", [string]$processId,
        "-ResultPath", $submission.result_path,
        "-LogPath", $guardLog,
        "-ProgressRoot", $outputDir,
        "-TimeoutSeconds", [string]$TimeoutSeconds,
        "-PollMilliseconds", "150",
        "-MaxDismissals", "100"
    )
    $guardProcess = Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList $guardArguments `
        -WindowStyle Hidden `
        -PassThru

    Write-Output ("SUBMITTED {0} {1}" -f $presetId, $jobId)
    $resultText = & python $client wait $jobId --timeout $TimeoutSeconds
    if ($LASTEXITCODE -ne 0) {
        throw "Character Creator job failed for $presetId."
    }
    $result = $resultText | Out-String | ConvertFrom-Json
    $validation = $result.result.validation
    $guardProcess.WaitForExit()
    Write-Output (
        "COMPLETED {0} status={1} success={2} failures={3}" -f `
            $presetId,
            $result.status,
            $validation.success,
            $validation.failure_count
    )
    Start-Sleep -Seconds 2
}
