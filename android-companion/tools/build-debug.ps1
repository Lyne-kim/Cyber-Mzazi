param(
    [string]$GradleVersion = "8.7"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ToolsRoot = Join-Path $ProjectRoot ".tools"
$GradleZip = Join-Path $ToolsRoot "gradle-$GradleVersion-bin.zip"
$GradleHome = Join-Path $ToolsRoot "gradle-$GradleVersion"
$GradleExe = Join-Path $GradleHome "bin\gradle.bat"

if (-not (Test-Path $ToolsRoot)) {
    New-Item -ItemType Directory -Path $ToolsRoot | Out-Null
}

if (-not $env:ANDROID_SDK_ROOT -and -not $env:ANDROID_HOME) {
    throw "Set ANDROID_SDK_ROOT or ANDROID_HOME before building. Install Android SDK command-line tools first."
}

$SdkRoot = if ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } else { $env:ANDROID_HOME }
$LocalProperties = Join-Path $ProjectRoot "local.properties"
if (-not (Test-Path $LocalProperties)) {
    $EscapedSdk = $SdkRoot -replace "\\", "\\\\"
    "sdk.dir=$EscapedSdk" | Set-Content -Path $LocalProperties -Encoding ASCII
}

if (-not (Test-Path $GradleExe)) {
    Write-Host "Downloading Gradle $GradleVersion..."
    Invoke-WebRequest -Uri "https://services.gradle.org/distributions/gradle-$GradleVersion-bin.zip" -OutFile $GradleZip
    Expand-Archive -Path $GradleZip -DestinationPath $ToolsRoot -Force
}

Push-Location $ProjectRoot
try {
    & $GradleExe "assembleDebug"
}
finally {
    Pop-Location
}
