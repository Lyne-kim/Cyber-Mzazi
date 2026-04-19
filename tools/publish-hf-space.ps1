param(
    [Parameter(Mandatory = $true)]
    [string]$SpaceId
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$spacePath = Join-Path $projectRoot "hf_space"

if (-not (Test-Path -LiteralPath $spacePath -PathType Container)) {
    throw "hf_space folder not found at $spacePath"
}

hf auth whoami | Out-Null
hf repos create $SpaceId --type space --space-sdk docker --exist-ok
hf upload-large-folder $SpaceId $spacePath --type space

Write-Host "Hugging Face Space uploaded successfully: $SpaceId"
