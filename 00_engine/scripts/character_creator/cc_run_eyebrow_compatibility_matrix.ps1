param(
    [string]$RunDate = "20260725",
    [int]$ChunkSize = 4,
    [int]$ChunkTimeoutSeconds = 900
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$engineRoot = Split-Path -Parent (Split-Path -Parent $scriptRoot)
$bridgeRoot = Join-Path $engineRoot "character_creator_bridge"
$runtimeRoot = Join-Path $engineRoot "outputs\character_creator_bridge"
$artifactRoot = Join-Path $runtimeRoot "artifacts"
$batchPath = Join-Path $scriptRoot "cc_eyebrow_compatibility_batch_v1.json"
$clientPath = Join-Path $bridgeRoot "cc_bridge_client.py"
$runRoot = Join-Path $runtimeRoot ("eyebrow_matrix_runner_" + $RunDate)
$statusPath = Join-Path $runRoot "runner_status.json"
$logPath = Join-Path $runRoot "runner.log"
$pythonPath = (Get-Command python -ErrorAction Stop).Source

New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

function Write-RunnerLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format o), $Message
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
}

function Write-RunnerStatus {
    param(
        [string]$State,
        [int]$CompletedChunks,
        [int]$TotalChunks,
        [string]$ActiveJobId,
        [string]$Message
    )
    $document = [ordered]@{
        schema_version = 1
        state = $State
        updated_at = (Get-Date -Format o)
        process_id = $PID
        completed_chunks = $CompletedChunks
        total_chunks = $TotalChunks
        active_job_id = $ActiveJobId
        message = $Message
        log_path = $logPath
    }
    $temporary = $statusPath + ".tmp"
    $document | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $statusPath -Force
}

try {
    if (-not (Test-Path -LiteralPath $batchPath -PathType Leaf)) {
        throw "Batch file is missing: $batchPath"
    }
    if (-not (Test-Path -LiteralPath $clientPath -PathType Leaf)) {
        throw "Bridge client is missing: $clientPath"
    }
    if ($ChunkSize -lt 1) {
        throw "ChunkSize must be positive"
    }

    $batch = Get-Content -LiteralPath $batchPath -Raw | ConvertFrom-Json
    $presetIds = @($batch.presets | ForEach-Object { [string]$_.preset_id })
    if ($presetIds.Count -eq 0) {
        throw "Batch has no presets"
    }
    $totalChunks = [int][Math]::Ceiling($presetIds.Count / [double]$ChunkSize)
    Write-RunnerLog "Starting $($presetIds.Count) presets in $totalChunks chunks"
    Write-RunnerStatus "running" 0 $totalChunks $null "Starting matrix"

    for ($chunkIndex = 0; $chunkIndex -lt $totalChunks; $chunkIndex++) {
        $start = $chunkIndex * $ChunkSize
        $end = [Math]::Min($start + $ChunkSize - 1, $presetIds.Count - 1)
        $chunkIds = @($presetIds[$start..$end])
        $chunkNumber = $chunkIndex + 1
        $chunkLabel = "{0:D2}" -f $chunkNumber
        $jobId = "eyebrow-compatibility-matrix-v1-chunk-$chunkLabel-$RunDate"
        $outputDir = Join-Path $artifactRoot (
            "eyebrow_compatibility_matrix_v1_chunk_" + $chunkLabel + "_" + $RunDate
        )
        $resultPath = Join-Path $runtimeRoot ("results\" + $jobId + ".json")

        if (Test-Path -LiteralPath $resultPath -PathType Leaf) {
            $existing = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
            if ($existing.status -eq "succeeded") {
                Write-RunnerLog "Skipping completed $jobId"
                Write-RunnerStatus "running" $chunkNumber $totalChunks $null (
                    "Skipped completed chunk $chunkLabel"
                )
                continue
            }
            throw "Existing result is not successful: $resultPath"
        }

        $arguments = @(
            "-B",
            $clientPath,
            "validate-bodies",
            "--library-file",
            $batchPath,
            "--output-dir",
            $outputDir,
            "--confirm-scene-replace",
            "--job-id",
            $jobId,
            "--no-wait"
        )
        foreach ($presetId in $chunkIds) {
            $arguments += @("--preset-id", $presetId)
        }

        Write-RunnerLog "Submitting ${jobId}: $($chunkIds -join ', ')"
        Write-RunnerStatus "running" $chunkIndex $totalChunks $jobId (
            "Submitting chunk $chunkLabel"
        )
        & $pythonPath @arguments | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Bridge client rejected $jobId with exit code $LASTEXITCODE"
        }

        $deadline = (Get-Date).AddSeconds($ChunkTimeoutSeconds)
        while (-not (Test-Path -LiteralPath $resultPath -PathType Leaf)) {
            if ((Get-Date) -gt $deadline) {
                throw "Timed out waiting for $jobId"
            }
            Start-Sleep -Seconds 5
        }
        $result = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
        if ($result.status -ne "succeeded") {
            $errorMessage = if ($result.error) {
                [string]$result.error.message
            } else {
                "unknown error"
            }
            throw "${jobId} failed: $errorMessage"
        }
        Write-RunnerLog "Completed $jobId"
        Write-RunnerStatus "running" $chunkNumber $totalChunks $null (
            "Completed chunk $chunkLabel"
        )
        Start-Sleep -Seconds 3
    }

    Write-RunnerLog "Matrix completed successfully"
    Write-RunnerStatus "completed" $totalChunks $totalChunks $null (
        "All eyebrow matrix chunks completed"
    )
    exit 0
}
catch {
    $message = [string]$_.Exception.Message
    Write-RunnerLog "FAILED: $message"
    $completed = 0
    $total = 0
    if (Test-Path -LiteralPath $statusPath -PathType Leaf) {
        $previous = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
        $completed = [int]$previous.completed_chunks
        $total = [int]$previous.total_chunks
    }
    Write-RunnerStatus "failed" $completed $total $null $message
    exit 1
}
