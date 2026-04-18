param(
    [string]$GradleVersion = "8.9",
    [string]$GradleHomePath = "",
    [string]$GradleExePath = "",
    [string]$KeystorePropertiesPath = ""
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
$TempRoot = Join-Path $CacheRoot "tmp"
$ReleaseApkPath = Join-Path $ProjectBuildDir "app\outputs\apk\release\app-release.apk"

if (-not (Test-Path $ToolsRoot)) {
    New-Item -ItemType Directory -Path $ToolsRoot | Out-Null
}
foreach ($Path in @($CacheRoot, $GradleUserHome, $ProjectCacheDir, $ProjectBuildDir, $TempRoot)) {
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

if (-not $env:ANDROID_SDK_ROOT -and -not $env:ANDROID_HOME) {
    throw "Set ANDROID_SDK_ROOT or ANDROID_HOME before building. Install Android SDK command-line tools first."
}

if (-not $KeystorePropertiesPath) {
    $KeystorePropertiesPath = Join-Path $ProjectRoot "keystore.properties"
}

if (-not (Test-Path $KeystorePropertiesPath)) {
    throw "Keystore properties file not found at $KeystorePropertiesPath. Copy keystore.properties.example to keystore.properties and update it first."
}

$KeystoreProps = @{}
Get-Content $KeystorePropertiesPath | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) {
        return
    }
    $parts = $line -split "=", 2
    if ($parts.Length -eq 2) {
        $KeystoreProps[$parts[0].Trim()] = $parts[1].Trim()
    }
}

foreach ($RequiredKey in @("storeFile", "storePassword", "keyAlias", "keyPassword")) {
    if (-not $KeystoreProps.ContainsKey($RequiredKey) -or [string]::IsNullOrWhiteSpace($KeystoreProps[$RequiredKey])) {
        throw "Missing '$RequiredKey' in $KeystorePropertiesPath"
    }
}

$StoreFilePath = $KeystoreProps["storeFile"]
if (-not (Test-Path $StoreFilePath)) {
    throw "Release keystore not found at $StoreFilePath"
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
    $env:TEMP = $TempRoot
    $env:TMP = $TempRoot
    $env:JAVA_TOOL_OPTIONS = "-Djava.io.tmpdir=$TempRoot"
    & $GradleExe "--no-daemon" "--project-cache-dir" $ProjectCacheDir "assembleRelease"
    if ($LASTEXITCODE -ne 0) {
        throw "Gradle release build failed with exit code $LASTEXITCODE."
    }
    if (-not (Test-Path $ReleaseApkPath)) {
        throw "Release APK not found at $ReleaseApkPath"
    }
    Write-Host "Signed release APK ready at $ReleaseApkPath"
}
finally {
    Pop-Location
}
