param(
    [string]$ModelArtifactPath = ".\artifacts\message_model_stage3",
    [string]$OutputArchivePath = ".\artifacts\message_model_stage3.zip"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$resolvedArtifactPath = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $ModelArtifactPath))
$resolvedArchivePath = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $OutputArchivePath))

if (-not (Test-Path -LiteralPath $resolvedArtifactPath -PathType Container)) {
    throw "Model artifact folder not found at $resolvedArtifactPath"
}

$configPath = Join-Path $resolvedArtifactPath "config.json"
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw "Model artifact folder at $resolvedArtifactPath does not look like a transformer artifact."
}

$archiveParent = Split-Path -Parent $resolvedArchivePath
if (-not (Test-Path -LiteralPath $archiveParent -PathType Container)) {
    New-Item -ItemType Directory -Path $archiveParent | Out-Null
}

if (Test-Path -LiteralPath $resolvedArchivePath) {
    Remove-Item -LiteralPath $resolvedArchivePath -Force
}

Compress-Archive -Path (Join-Path $resolvedArtifactPath "*") -DestinationPath $resolvedArchivePath -CompressionLevel Optimal

Write-Host "Model archive ready at $resolvedArchivePath"
