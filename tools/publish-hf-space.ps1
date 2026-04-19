param(
    [Parameter(Mandatory = $true)]
    [string]$SpaceId
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$spacePath = Join-Path $projectRoot "hf_space"
$spaceRepoId = if ($SpaceId.StartsWith("spaces/")) { $SpaceId } else { "spaces/$SpaceId" }

if (-not (Test-Path -LiteralPath $spacePath -PathType Container)) {
    throw "hf_space folder not found at $spacePath"
}

function Invoke-Hf {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    & hf @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "hf $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

Invoke-Hf auth whoami | Out-Null
Invoke-Hf repos create $spaceRepoId --type space --space-sdk docker --exist-ok
Invoke-Hf upload-large-folder $spaceRepoId $spacePath --type space

Write-Host "Hugging Face Space uploaded successfully: $spaceRepoId"
