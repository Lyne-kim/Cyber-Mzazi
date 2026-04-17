param(
    [string]$ApkPath = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ApkPath) {
    $ApkPath = Join-Path $ProjectRoot "app\build\outputs\apk\debug\app-debug.apk"
}

if (-not (Test-Path $ApkPath)) {
    throw "APK not found at $ApkPath. Run tools\\build-debug.ps1 first."
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
