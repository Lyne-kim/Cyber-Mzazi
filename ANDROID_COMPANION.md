# Android Companion

This folder contains the first Android companion app for Cyber Mzazi.

## What it does

- stores the backend URL and one-time device token from the parent dashboard
- scans a pairing QR instead of requiring manual token copy
- opens Android notification-listener settings
- listens for notification text from supported apps
- queues notifications locally if the network is down and retries later
- lets you define allow/block package filters per app
- shows a small recent log of captured notifications and upload status
- forwards notification payloads to:

```text
POST /api/device-ingest/android-notifications
```

## Use without Android Studio

Use VS Code plus Android command-line tools.

1. Install the Android SDK command-line tools using:

[C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\tools\setup-android-sdk.md](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\tools\setup-android-sdk.md)

2. Open this folder in VS Code:

```text
android-companion
```

3. Connect a real Android device with USB debugging enabled.
4. Build the debug APK:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build-debug.ps1
```

If you already have a compatible local Gradle installed, you can point the script to it:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build-debug.ps1 -GradleHomePath "C:\gradle\gradle-8.9"
```

Do not point this project at Gradle `9.x` unless you also upgrade the Android Gradle Plugin to a version that officially supports it.

The build now writes its main Android output to:

```text
%LOCALAPPDATA%\CyberMzaziAndroid\project-build\app\outputs\apk\debug\app-debug.apk
```

This avoids OneDrive locking issues inside the project folder during Kotlin compilation.

5. Install it on the phone:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\install-debug.ps1
```

6. You can also use the included VS Code tasks:
- `Android: Build Debug APK`
- `Android: Install Debug APK`

For phone setup across Samsung, Pixel, Xiaomi/Redmi/POCO, Infinix/Tecno, Oppo/Realme/Vivo, Huawei/Honor, and similar Android brands, use:

- [C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\ANDROID_DEVICE_SETUP.md](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\ANDROID_DEVICE_SETUP.md)

## Real-device test flow

1. In the parent dashboard, select a child.
2. Open `Child Profile`.
3. Create an `Android notification link`.
4. Copy the one-time token.
5. In the Android app:
   - scan the pairing QR from the parent dashboard, or paste the URL/token manually
   - review or update allow/block package filters
   - save settings
   - open notification access and enable Cyber Mzazi
6. Press `Send test payload` to confirm the backend receives data.
7. Send a real message notification to the device from another account and confirm it appears in the parent dashboard.

## Recommended install paths

- `USB debugging + ADB install`
  - best for phones where Developer Options are available and app installs over USB are allowed
- `Wireless debugging`
  - best when the phone supports developer mode but a cable is inconvenient
- `Manual APK install`
  - best when USB debugging is blocked but the phone still allows APK installation from the file manager, browser, Drive, or email

## Current limits

- this uses Android notification access, not direct in-app message database access
- only message content exposed through notifications can be captured automatically
- deep links are not resolved yet
- pairing QR currently uses a generated web QR image
- token rotation is still parent-managed from the dashboard

## Current refinements already included

- QR pairing from the parent dashboard
- offline queueing and retry
- per-app allow and block filters
- recent captured-notification log

## Good next refinements

- signed release APK pipeline
- background retry using WorkManager
- token rotation and revoke-all action from the parent dashboard
- optional per-app risk sensitivity settings
