param(
    [string]$Root = 'D:\BaiduNetdiskDownload\iclone动作',
    [switch]$Apply,
    [string]$EvidencePath = 'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\animation_pack_organization\run_20260817_v1\result.json'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$tierDefinitions = [ordered]@{
    P0_Core_Everyday = [ordered]@{
        description = 'High-value everyday source packs to inspect first. Individual prop-bound clips may later move to P2.'
        entries = @(
            'Audience Motion Pack vfxMed.rar'
            'City Life.zip'
            'Conversation.zip'
            'Female Casual Moves.zip'
            'Hand Signals.zip'
            'Home Life.zip'
            'Office Work-Meeting.zip'
            'Office Work-Working.zip'
            'Shopping.zip'
            'Social Hangout.zip'
            '旅行通勤组合'
        )
    }
    P1_Extended_Realistic = [ordered]@{
        description = 'Realistic secondary domains, demographics, or presentation styles for later expansion.'
        entries = @(
            'Athletic Run.rar'
            'Emotes.rar'
            'Glamorous Moves.zip'
            "Kids' Adventure.zip"
            "Kids n' Friends.zip"
            'Mixed Animations.zip'
            'Platform & Carriage.rar'
            'Sports Mocap.rar'
            'Spunky Moves.zip'
            'Station Terminal.rar'
        )
    }
    P2_Locked_Props_Interactions = [ordered]@{
        description = 'Packs dominated by partner, prop, or scene-locked motions that require paired configuration.'
        entries = @(
            'Bros & Pals.zip'
            'Construction Pack.rar'
            'Construction.rar'
            'iclone RPG动作格斗动画文件RPG Crafting Animation Suite – Persona_WorkinG'
            'Injury & Rescue vfxMed.zip'
            'Motions for Lovers.rar'
        )
    }
    P3_Special_Stylized = [ordered]@{
        description = 'Combat, stunt, fantasy, cartoon, dance, performance, or other specialized packs deferred from the first production pool.'
        entries = @(
            'Aerial Fighter vfxMed.zip'
            'Assassin Moves.rar'
            'Bank Heist.rar'
            'Cartoon Expressions_Basic50.zip'
            'Cartoon male female Act and Move Combo.rar'
            "Cartoon-Kids' Moves.rar"
            "Cartoon-Sit n' Talk-Female.zip"
            "Cartoon-Sit n' Talk-Interaction.zip"
            "Cartoon-Sit n' Talk-Male.zip"
            'Cartoon-Talk&Listen.zip'
            'Classical Cartoon Moves - Cowardly Moves vfxMed.rar'
            'Clumsy Moves Vol_1 vfxMed.rar'
            'Explosion Stunts vfxMed.rar'
            'Girl Dance.zip'
            'Hand-to-Hand Combat.zip'
            'Hero Moves.zip'
            'iclone动作文件Act and Move Combo'
            'Magical Moves.zip'
            'MD Rock Singer.rar'
            'Parkour.rar'
            'Pistol Moves.zip'
            'Pistol Stunts.zip'
            'Raging Orc vfxMed.zip'
            'Rifle Combat Combo.zip'
            'Riot iClone 8.52 vfxMed.zip'
            'Rock Singer.zip'
            'Run For Your Life.rar'
            'Shuffle Dance - Cleaned - Full Zonegfx.zip'
            'Skateboard vfxMed.rar'
            'Sword and Shield Moves.zip'
        )
    }
}

function Resolve-UnderRoot {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$ResolvedRoot
    )

    $full = [IO.Path]::GetFullPath($Path)
    $prefix = $ResolvedRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path escapes animation root: $full"
    }
    return $full
}

$resolvedRoot = [IO.Path]::GetFullPath($Root).TrimEnd([IO.Path]::DirectorySeparatorChar)
if (-not (Test-Path -LiteralPath $resolvedRoot -PathType Container)) {
    throw "Animation root does not exist: $resolvedRoot"
}

$allExpected = @(
    foreach ($tier in $tierDefinitions.Keys) {
        foreach ($entry in $tierDefinitions[$tier].entries) {
            $entry
        }
    }
)
$duplicates = @($allExpected | Group-Object | Where-Object Count -gt 1)
if ($duplicates.Count -gt 0) {
    throw "Classification contains duplicate entries: $($duplicates.Name -join ', ')"
}

$controlNames = @($tierDefinitions.Keys) + @('_animation_pack_tier_manifest_v1.json')
$actual = @(
    Get-ChildItem -LiteralPath $resolvedRoot -Force |
        Where-Object Name -notin $controlNames |
        Select-Object -ExpandProperty Name
)
$missing = @($allExpected | Where-Object { $_ -notin $actual })
$unexpected = @($actual | Where-Object { $_ -notin $allExpected })
if ($missing.Count -gt 0 -or $unexpected.Count -gt 0) {
    throw "Source inventory mismatch. Missing=[$($missing -join '; ')] Unexpected=[$($unexpected -join '; ')]"
}

$items = @()
foreach ($tier in $tierDefinitions.Keys) {
    $tierRoot = Resolve-UnderRoot -Path (Join-Path $resolvedRoot $tier) -ResolvedRoot $resolvedRoot
    foreach ($entry in $tierDefinitions[$tier].entries) {
        $source = Resolve-UnderRoot -Path (Join-Path $resolvedRoot $entry) -ResolvedRoot $resolvedRoot
        $target = Resolve-UnderRoot -Path (Join-Path $tierRoot $entry) -ResolvedRoot $resolvedRoot
        if (-not (Test-Path -LiteralPath $source)) {
            throw "Missing source item: $source"
        }
        if (Test-Path -LiteralPath $target) {
            throw "Target collision: $target"
        }
        $sourceItem = Get-Item -LiteralPath $source
        $items += [ordered]@{
            name = $entry
            tier = $tier
            item_type = if ($sourceItem.PSIsContainer) { 'directory' } else { 'archive' }
            original_path = $source
            target_path = $target
        }
    }
}

$manifest = [ordered]@{
    schema_version = 1
    manifest_id = 'cc_animation_pack_tier_manifest_20260817_v1'
    created_at = (Get-Date).ToString('o')
    root = $resolvedRoot
    classification_level = 'source_package_candidate_priority'
    final_motion_approval = $false
    mode = if ($Apply) { 'applied' } else { 'dry_run' }
    tier_definitions = $tierDefinitions
    counts = [ordered]@{
        total = $items.Count
        P0_Core_Everyday = @($items | Where-Object tier -eq 'P0_Core_Everyday').Count
        P1_Extended_Realistic = @($items | Where-Object tier -eq 'P1_Extended_Realistic').Count
        P2_Locked_Props_Interactions = @($items | Where-Object tier -eq 'P2_Locked_Props_Interactions').Count
        P3_Special_Stylized = @($items | Where-Object tier -eq 'P3_Special_Stylized').Count
    }
    boundaries = @(
        'A package tier controls review order; it does not approve every motion inside the package.'
        'After extraction, individual motions must be reclassified by semantics, prop dependency, partner dependency, facial channels, and technical validation.'
        'No source package is deleted or unpacked by this operation.'
    )
    items = $items
}

if ($Apply) {
    foreach ($tier in $tierDefinitions.Keys) {
        $tierRoot = Resolve-UnderRoot -Path (Join-Path $resolvedRoot $tier) -ResolvedRoot $resolvedRoot
        New-Item -ItemType Directory -Path $tierRoot -Force | Out-Null
    }
    foreach ($item in $items) {
        Move-Item -LiteralPath $item.original_path -Destination $item.target_path
    }
    foreach ($item in $items) {
        if (Test-Path -LiteralPath $item.original_path) {
            throw "Source still exists after move: $($item.original_path)"
        }
        if (-not (Test-Path -LiteralPath $item.target_path)) {
            throw "Target missing after move: $($item.target_path)"
        }
    }

    $sourceManifest = Join-Path $resolvedRoot '_animation_pack_tier_manifest_v1.json'
    $manifestJson = $manifest | ConvertTo-Json -Depth 10
    Set-Content -LiteralPath $sourceManifest -Value $manifestJson -Encoding utf8
    $evidenceDirectory = Split-Path -Parent $EvidencePath
    New-Item -ItemType Directory -Path $evidenceDirectory -Force | Out-Null
    Set-Content -LiteralPath $EvidencePath -Value $manifestJson -Encoding utf8
}

[pscustomobject]@{
    mode = $manifest.mode
    root = $manifest.root
    counts = $manifest.counts
    evidence_path = if ($Apply) { $EvidencePath } else { $null }
}
