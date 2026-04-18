param(
    [string]$ApkPath = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ApkPath) {
    $CacheRoot = Join-Path $env:LOCALAPPDATA "CyberMzaziAndroid"
    $ExternalApkPath = Join-Path $CacheRoot "project-build\app\outputs\apk\release\app-release.apk"
    $LegacyApkPath = Join-Path $ProjectRoot "app\build\outputs\apk\release\app-release.apk"
    if (Test-Path $ExternalApkPath) {
        $ApkPath = $ExternalApkPath
    }
    else {
        $ApkPath = $LegacyApkPath
    }
}

if (-not (Test-Path $ApkPath)) {
    throw "Release APK not found at $ApkPath. Run tools\\build-release.ps1 first."
}

$AdbExe = $null
if ($env:ANDROID_SDK_ROOT) {
    $Candidate = Join-Path $env:ANDROID_SDK_ROOT "platform-tools\adb.exe"
    if (Test-Path $Candidate) {
        $AdbExe = $Candidate
    }
}
if (-not $AdbExe -and $env:ANDROID_HOME) {
    $Candidate = Join-Path $env:ANDROID_HOME "platform-tools\adb.exe"
    if (Test-Path $Candidate) {
        $AdbExe = $Candidate
    }
}
if (-not $AdbExe) {
    $AdbExe = "adb"
}

& $AdbExe "devices"
& $AdbExe "install" "-r" $ApkPath
