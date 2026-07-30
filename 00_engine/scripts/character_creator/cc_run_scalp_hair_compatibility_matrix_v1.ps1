param(
    [string]$RunTag = "20260727_01",
    [int]$StartChunk = 1,
    [int]$EndChunk = 0,
    [int]$ChunkSize = 4,
    [int]$ChunkTimeoutSeconds = 1800,
    [int]$NonResponsiveTimeoutSeconds = 480,
    [int]$InterChunkDelaySeconds = 10,
    [double]$MemoryCeilingGB = 24.0,
    [int]$MaxDismissalsPerChunk = 120,
    [string]$BatchFileName = "cc_scalp_hair_compatibility_batch_v1.json",
    [int]$ExpectedPresetCount = 120,
    [string]$ArtifactName = "scalp_hair_compatibility_matrix_v1",
    [string]$GuardName = "scalp_hair_compatibility_matrix_v1",
    [string]$RunnerName = "scalp_hair_matrix_runner",
    [string]$JobPrefix = "scalp-hair-matrix-v1"
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$engineRoot = Split-Path -Parent (Split-Path -Parent $scriptRoot)
$bridgeRoot = Join-Path $engineRoot "character_creator_bridge"
$runtimeRoot = Join-Path $engineRoot "outputs\character_creator_bridge"
$artifactRoot = Join-Path $runtimeRoot (
    "artifacts\" + $ArtifactName + "_" + $RunTag
)
$guardLogRoot = Join-Path $runtimeRoot (
    "dialog_guard\" + $GuardName + "_" + $RunTag
)
$runRoot = Join-Path $runtimeRoot (
    $RunnerName + "_" + $RunTag
)
$batchPath = Join-Path $scriptRoot $BatchFileName
$clientPath = Join-Path $bridgeRoot "cc_bridge_client.py"
$guardPath = Join-Path $bridgeRoot "cc_undo_dialog_guard.ps1"
$statusPath = Join-Path $runRoot "runner_status.json"
$logPath = Join-Path $runRoot "runner.log"
$pythonPath = (Get-Command python -ErrorAction Stop).Source
$powershellPath = (Get-Command powershell.exe -ErrorAction Stop).Source

New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
New-Item -ItemType Directory -Force -Path $guardLogRoot | Out-Null

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
        [string]$Message,
        [double]$PrivateMemoryGB
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
        cc_private_memory_gb = $PrivateMemoryGB
        memory_ceiling_gb = $MemoryCeilingGB
        artifact_root = $artifactRoot
        guard_log_root = $guardLogRoot
        log_path = $logPath
    }
    $temporary = $statusPath + ".tmp"
    $document |
        ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $statusPath -Force
}

function Get-CharacterCreatorProcess {
    $processes = @(Get-Process -Name "CharacterCreator" -ErrorAction SilentlyContinue)
    if ($processes.Count -ne 1) {
        throw "Expected exactly one CharacterCreator process; found $($processes.Count)"
    }
    return $processes[0]
}

function Get-PrivateMemoryGB {
    param([System.Diagnostics.Process]$Process)
    $Process.Refresh()
    return [Math]::Round($Process.PrivateMemorySize64 / 1GB, 3)
}

function Assert-GuardLog {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Guard log is missing: $Path"
    }
    $events = @(
        Get-Content -LiteralPath $Path |
            Where-Object { $_.Trim() } |
            ForEach-Object { $_ | ConvertFrom-Json }
    )
    $fatalEvents = @(
        $events |
            Where-Object {
                $_.event -in @(
                    "unmatched_cc_dialog",
                    "dismissal_limit_reached",
                    "timeout",
                    "guard_error",
                    "target_process_exited"
                )
            }
    )
    if ($fatalEvents.Count -gt 0) {
        $names = @($fatalEvents | ForEach-Object { $_.event }) -join ", "
        throw "Dialog guard reported unsafe event(s): $names"
    }
    if (-not ($events | Where-Object { $_.event -eq "stopped" })) {
        throw "Dialog guard did not stop cleanly: $Path"
    }
    return @($events | Where-Object { $_.event -eq "dismissed_undo_warning" }).Count
}

try {
    foreach ($requiredPath in @($batchPath, $clientPath, $guardPath)) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            throw "Required file is missing: $requiredPath"
        }
    }
    if ($ChunkSize -lt 1) {
        throw "ChunkSize must be positive"
    }
    if ($ChunkTimeoutSeconds -lt 60) {
        throw "ChunkTimeoutSeconds must be at least 60"
    }
    if ($NonResponsiveTimeoutSeconds -lt 60) {
        throw "NonResponsiveTimeoutSeconds must be at least 60"
    }
    if ($InterChunkDelaySeconds -lt 0 -or $InterChunkDelaySeconds -gt 300) {
        throw "InterChunkDelaySeconds must be between 0 and 300"
    }
    if ($MemoryCeilingGB -le 0) {
        throw "MemoryCeilingGB must be positive"
    }
    if ($ExpectedPresetCount -lt 1) {
        throw "ExpectedPresetCount must be positive"
    }
    foreach ($name in @(
        $ArtifactName,
        $GuardName,
        $RunnerName,
        $JobPrefix
    )) {
        if ($name -notmatch "^[A-Za-z0-9][A-Za-z0-9_-]*$") {
            throw "Run names may contain only letters, numbers, _ and -"
        }
    }

    $ccProcess = Get-CharacterCreatorProcess
    $initialCcProcessId = $ccProcess.Id
    $batch = Get-Content -LiteralPath $batchPath -Raw | ConvertFrom-Json
    $presetIds = @($batch.presets | ForEach-Object { [string]$_.preset_id })
    if ($presetIds.Count -ne $ExpectedPresetCount) {
        throw (
            "Expected $ExpectedPresetCount presets; " +
            "found $($presetIds.Count)"
        )
    }
    if (@($presetIds | Select-Object -Unique).Count -ne $presetIds.Count) {
        throw "Scalp-hair preset IDs are not unique"
    }

    $totalChunks = [int][Math]::Ceiling(
        $presetIds.Count / [double]$ChunkSize
    )
    if ($StartChunk -lt 1 -or $StartChunk -gt $totalChunks) {
        throw "StartChunk must be between 1 and $totalChunks"
    }
    $resolvedEndChunk = if ($EndChunk -eq 0) {
        $totalChunks
    }
    else {
        $EndChunk
    }
    if (
        $resolvedEndChunk -lt $StartChunk -or
        $resolvedEndChunk -gt $totalChunks
    ) {
        throw (
            "EndChunk must be 0 or between StartChunk and " +
            "$totalChunks"
        )
    }
    $initialMemory = Get-PrivateMemoryGB -Process $ccProcess
    Write-RunnerLog (
        "Running chunks $StartChunk-$resolvedEndChunk of $totalChunks; " +
        "$($presetIds.Count) total presets; " +
        "CC PID=$($ccProcess.Id), private memory=${initialMemory}GB"
    )
    Write-RunnerStatus `
        -State "running" `
        -CompletedChunks ($StartChunk - 1) `
        -TotalChunks $totalChunks `
        -ActiveJobId $null `
        -Message "Starting scalp-hair compatibility matrix" `
        -PrivateMemoryGB $initialMemory

    for (
        $chunkIndex = $StartChunk - 1;
        $chunkIndex -lt $resolvedEndChunk;
        $chunkIndex++
    ) {
        $ccProcess = Get-CharacterCreatorProcess
        if ($ccProcess.Id -ne $initialCcProcessId) {
            throw "Character Creator process changed during the matrix"
        }
        $memoryBefore = Get-PrivateMemoryGB -Process $ccProcess
        if ($memoryBefore -ge $MemoryCeilingGB) {
            Write-RunnerLog (
                "Stopping before chunk $($chunkIndex + 1): private memory " +
                "${memoryBefore}GB reached the ${MemoryCeilingGB}GB ceiling"
            )
            Write-RunnerStatus `
                -State "memory_ceiling_reached" `
                -CompletedChunks $chunkIndex `
                -TotalChunks $totalChunks `
                -ActiveJobId $null `
                -Message "Stopped safely at a chunk boundary" `
                -PrivateMemoryGB $memoryBefore
            exit 2
        }

        $start = $chunkIndex * $ChunkSize
        $end = [Math]::Min(
            $start + $ChunkSize - 1,
            $presetIds.Count - 1
        )
        $chunkIds = @($presetIds[$start..$end])
        $chunkNumber = $chunkIndex + 1
        $chunkLabel = "{0:D2}" -f $chunkNumber
        $jobId = (
            $JobPrefix + "-" + $RunTag + "-chunk-" + $chunkLabel
        )
        $outputDir = Join-Path $artifactRoot ("chunk_" + $chunkLabel)
        $validationResultPath = Join-Path $outputDir "validation_result.json"
        $bridgeResultPath = Join-Path $runtimeRoot (
            "results\" + $jobId + ".json"
        )
        $guardLogPath = Join-Path $guardLogRoot (
            "chunk_" + $chunkLabel + ".jsonl"
        )

        if (Test-Path -LiteralPath $bridgeResultPath -PathType Leaf) {
            $existingBridgeResult = (
                Get-Content -LiteralPath $bridgeResultPath -Raw |
                    ConvertFrom-Json
            )
            if (
                $existingBridgeResult.status -eq "succeeded" -and
                (Test-Path -LiteralPath $validationResultPath -PathType Leaf)
            ) {
                $existingValidation = (
                    Get-Content -LiteralPath $validationResultPath -Raw |
                        ConvertFrom-Json
                )
                if ($existingValidation.success -eq $true) {
                    Write-RunnerLog "Skipping completed $jobId"
                    $resumeMemory = Get-PrivateMemoryGB -Process $ccProcess
                    Write-RunnerStatus `
                        -State "running" `
                        -CompletedChunks $chunkNumber `
                        -TotalChunks $totalChunks `
                        -ActiveJobId $null `
                        -Message "Skipped completed chunk $chunkLabel" `
                        -PrivateMemoryGB $resumeMemory
                    continue
                }
            }
            throw "Existing job is not a successful resumable chunk: $jobId"
        }
        if (
            (Test-Path -LiteralPath $outputDir) -and
            @(Get-ChildItem -LiteralPath $outputDir -Force).Count -gt 0
        ) {
            throw "Chunk output exists and is non-empty: $outputDir"
        }

        $clientArguments = @(
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
            "--no-wait",
            "--timeout",
            [string]$ChunkTimeoutSeconds
        )
        foreach ($presetId in $chunkIds) {
            $clientArguments += @("--preset-id", $presetId)
        }

        Write-RunnerLog (
            "Submitting ${jobId}: $($chunkIds -join ', '); " +
            "private memory=${memoryBefore}GB"
        )
        Write-RunnerStatus `
            -State "running" `
            -CompletedChunks $chunkIndex `
            -TotalChunks $totalChunks `
            -ActiveJobId $jobId `
            -Message "Submitting chunk $chunkLabel" `
            -PrivateMemoryGB $memoryBefore
        & $pythonPath @clientArguments | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Bridge client rejected $jobId with exit code $LASTEXITCODE"
        }

        $guardArguments = @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            $guardPath,
            "-TargetProcessId",
            [string]$ccProcess.Id,
            "-ResultPath",
            $validationResultPath,
            "-LogPath",
            $guardLogPath,
            "-ProgressRoot",
            $outputDir,
            "-TimeoutSeconds",
            [string]$ChunkTimeoutSeconds,
            "-PollMilliseconds",
            "150",
            "-MaxDismissals",
            [string]$MaxDismissalsPerChunk
        )
        $guardProcess = Start-Process `
            -FilePath $powershellPath `
            -ArgumentList $guardArguments `
            -WindowStyle Hidden `
            -PassThru
        Write-RunnerLog (
            "Started dialog guard PID=$($guardProcess.Id) for $jobId"
        )

        $deadline = (Get-Date).AddSeconds($ChunkTimeoutSeconds)
        $nonResponsiveSince = $null
        while (
            -not (Test-Path -LiteralPath $bridgeResultPath -PathType Leaf)
        ) {
            if ((Get-Date) -gt $deadline) {
                throw "Timed out waiting for $jobId"
            }
            $ccProcess = Get-CharacterCreatorProcess
            if ($ccProcess.Responding) {
                $nonResponsiveSince = $null
            }
            elseif ($null -eq $nonResponsiveSince) {
                $nonResponsiveSince = Get-Date
            }
            elseif (
                ((Get-Date) - $nonResponsiveSince).TotalSeconds -gt
                    $NonResponsiveTimeoutSeconds
            ) {
                throw (
                    "Character Creator was unresponsive for over " +
                    "$NonResponsiveTimeoutSeconds seconds"
                )
            }
            Start-Sleep -Seconds 5
        }

        $bridgeResult = (
            Get-Content -LiteralPath $bridgeResultPath -Raw |
                ConvertFrom-Json
        )
        if ($bridgeResult.status -ne "succeeded") {
            $errorMessage = if ($bridgeResult.error) {
                [string]$bridgeResult.error.message
            }
            else {
                "unknown bridge error"
            }
            throw "${jobId} failed: $errorMessage"
        }
        if (-not (Test-Path -LiteralPath $validationResultPath -PathType Leaf)) {
            throw "Validation summary is missing: $validationResultPath"
        }
        $validation = (
            Get-Content -LiteralPath $validationResultPath -Raw |
                ConvertFrom-Json
        )
        if (
            $validation.success -ne $true -or
            [int]$validation.success_count -ne $chunkIds.Count
        ) {
            throw (
                "${jobId} contains validation failures; inspect " +
                $validationResultPath
            )
        }

        $guardProcess.WaitForExit(30000) | Out-Null
        if (-not $guardProcess.HasExited) {
            throw "Dialog guard did not exit after $jobId completed"
        }
        $dismissalCount = Assert-GuardLog -Path $guardLogPath
        $memoryAfter = Get-PrivateMemoryGB -Process $ccProcess
        Write-RunnerLog (
            "Completed $jobId; dismissed $dismissalCount known warning(s); " +
            "private memory=${memoryAfter}GB"
        )
        Write-RunnerStatus `
            -State "running" `
            -CompletedChunks $chunkNumber `
            -TotalChunks $totalChunks `
            -ActiveJobId $null `
            -Message "Completed chunk $chunkLabel" `
            -PrivateMemoryGB $memoryAfter

        if ($memoryAfter -ge $MemoryCeilingGB) {
            Write-RunnerLog (
                "Stopping after chunk ${chunkLabel}: private memory " +
                "${memoryAfter}GB reached the ${MemoryCeilingGB}GB ceiling"
            )
            Write-RunnerStatus `
                -State "memory_ceiling_reached" `
                -CompletedChunks $chunkNumber `
                -TotalChunks $totalChunks `
                -ActiveJobId $null `
                -Message "Stopped safely after a completed chunk" `
                -PrivateMemoryGB $memoryAfter
            exit 2
        }
        if ($InterChunkDelaySeconds -gt 0) {
            Start-Sleep -Seconds $InterChunkDelaySeconds
        }
    }

    $finalMemory = Get-PrivateMemoryGB -Process $ccProcess
    $finalState = if ($resolvedEndChunk -eq $totalChunks) {
        "completed"
    }
    else {
        "range_completed"
    }
    $finalMessage = if ($resolvedEndChunk -eq $totalChunks) {
        "All scalp-hair matrix chunks completed"
    }
    else {
        "Requested scalp-hair chunk range completed"
    }
    Write-RunnerLog (
        "Chunk range $StartChunk-$resolvedEndChunk completed successfully"
    )
    Write-RunnerStatus `
        -State $finalState `
        -CompletedChunks $resolvedEndChunk `
        -TotalChunks $totalChunks `
        -ActiveJobId $null `
        -Message $finalMessage `
        -PrivateMemoryGB $finalMemory
    exit 0
}
catch {
    $message = [string]$_.Exception.Message
    Write-RunnerLog "FAILED: $message"
    $completed = 0
    $total = 0
    $memory = 0.0
    if (Test-Path -LiteralPath $statusPath -PathType Leaf) {
        $previous = (
            Get-Content -LiteralPath $statusPath -Raw |
                ConvertFrom-Json
        )
        $completed = [int]$previous.completed_chunks
        $total = [int]$previous.total_chunks
        $memory = [double]$previous.cc_private_memory_gb
    }
    Write-RunnerStatus `
        -State "failed" `
        -CompletedChunks $completed `
        -TotalChunks $total `
        -ActiveJobId $null `
        -Message $message `
        -PrivateMemoryGB $memory
    exit 1
}
