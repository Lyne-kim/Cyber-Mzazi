param(
    [Parameter(Mandatory = $true)]
    [string]$SpaceId
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$spacePath = Join-Path $projectRoot "hf_space"
$spaceCreateId = if ($SpaceId.StartsWith("spaces/")) { $SpaceId.Substring(7) } else { $SpaceId }

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
Invoke-Hf repos create $spaceCreateId --type space --space-sdk docker --exist-ok
Invoke-Hf upload $spaceCreateId $spacePath . --type space --commit-message "Update Cyber Mzazi HF Space"

Write-Host "Hugging Face Space uploaded successfully: $spaceCreateId"
