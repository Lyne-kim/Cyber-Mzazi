param(
    [string]$GradleVersion = "8.9",
    [string]$GradleHomePath = "",
    [string]$GradleExePath = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ToolsRoot = Join-Path $ProjectRoot ".tools"
$GradleZip = Join-Path $ToolsRoot "gradle-$GradleVersion-bin.zip"
$BundledGradleHome = Join-Path $ToolsRoot "gradle-$GradleVersion"
$BundledGradleExe = Join-Path $BundledGradleHome "bin\gradle.bat"
$CacheRoot = Join-Path $env:LOCALAPPDATA "CyberMzaziAndroid"
$GradleUserHome = Join-Path $CacheRoot "gradle-user-home"
$ProjectCacheDir = Join-Path $CacheRoot "project-cache"
$ProjectBuildDir = Join-Path $CacheRoot "project-build"
$ExternalApkPath = Join-Path $ProjectBuildDir "app\outputs\apk\debug\app-debug.apk"

if (-not (Test-Path $ToolsRoot)) {
    New-Item -ItemType Directory -Path $ToolsRoot | Out-Null
}
foreach ($Path in @($CacheRoot, $GradleUserHome, $ProjectCacheDir, $ProjectBuildDir)) {
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

if (-not $env:ANDROID_SDK_ROOT -and -not $env:ANDROID_HOME) {
    throw "Set ANDROID_SDK_ROOT or ANDROID_HOME before building. Install Android SDK command-line tools first."
}

if ($GradleExePath) {
    $GradleExe = $GradleExePath
}
elseif ($GradleHomePath) {
    $GradleExe = Join-Path $GradleHomePath "bin\gradle.bat"
}
else {
    $GradleExe = $BundledGradleExe
}

$SdkRoot = if ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } else { $env:ANDROID_HOME }
$LocalProperties = Join-Path $ProjectRoot "local.properties"
if (-not (Test-Path $LocalProperties)) {
    $EscapedSdk = $SdkRoot -replace "\\", "\\\\"
    "sdk.dir=$EscapedSdk" | Set-Content -Path $LocalProperties -Encoding ASCII
}

if (($GradleExe -eq $BundledGradleExe) -and -not (Test-Path $GradleExe)) {
    Write-Host "Downloading Gradle $GradleVersion..."
    Invoke-WebRequest -Uri "https://services.gradle.org/distributions/gradle-$GradleVersion-bin.zip" -OutFile $GradleZip
    Expand-Archive -Path $GradleZip -DestinationPath $ToolsRoot -Force
}

if (-not (Test-Path $GradleExe)) {
    throw "Gradle executable not found at $GradleExe"
}

Push-Location $ProjectRoot
try {
    $env:GRADLE_USER_HOME = $GradleUserHome
    & $GradleExe "--project-cache-dir" $ProjectCacheDir "assembleDebug"
    if (Test-Path $ExternalApkPath) {
        Write-Host "APK ready at $ExternalApkPath"
    }
}
finally {
    Pop-Location
}
