# Android Device Setup Guide

This guide covers the three practical ways to install and test the Cyber Mzazi Android companion across common Android brands.

Use the method that fits your phone:

- `Method A`: USB debugging plus ADB install
- `Method B`: Wireless debugging plus ADB install
- `Method C`: Manual APK install with no USB debugging

The APK produced by this project is usually here:

- `%LOCALAPPDATA%\CyberMzaziAndroid\project-build\app\outputs\apk\debug\app-debug.apk`

Legacy path if you are using an older build flow:

- [android-companion/app/build/outputs/apk/debug/app-debug.apk](android-companion/app/build/outputs/apk/debug/app-debug.apk)

## Before You Start

Make sure you already have:

- `JDK 17`
- `Android SDK command-line tools`
- `platform-tools`
- `platforms;android-35`
- `build-tools;35.0.0`

If not, follow:

- [android-companion/tools/setup-android-sdk.md](android-companion/tools/setup-android-sdk.md)

Then build the APK:

```powershell
cd android-companion
powershell -ExecutionPolicy Bypass -File .\tools\build-debug.ps1
```

If you prefer to use an existing compatible Gradle installation instead of the script-managed download, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build-debug.ps1 -GradleHomePath "C:\gradle\gradle-8.9"
```

For the current Cyber Mzazi Android build, do not use Gradle `9.x` with AGP `8.7.3`.

## Method A: USB Debugging Plus ADB Install

This is the fastest path for:

- Samsung
- Google Pixel
- Motorola
- OnePlus
- Nothing
- many Xiaomi/Redmi/POCO phones
- many Infinix, Tecno, Oppo, Realme, Vivo phones

### 1. Enable Developer Options

On the phone:

1. Open `Settings`
2. Open `About phone`
3. Tap `Build number` 7 times
4. Go back to `Settings`
5. Open `Developer options`

### 2. Enable Debugging

Turn on:

- `USB debugging`

If your brand shows extra security prompts, also look for:

- `USB debugging (Security settings)`
- `Install via USB`
- `Verify apps over USB`
- `Allow USB debugging from this computer`

If `Verify apps over USB` is blocking installation, turn it off temporarily for testing.

### 3. Connect the Phone

1. Connect the phone with USB
2. Unlock the phone
3. Accept the RSA trust prompt if it appears
4. If asked for USB mode, choose `File transfer` or keep the default if debugging already works

### 4. Confirm the Device Is Detected

```powershell
adb devices
```

You want to see:

```text
<device-id>    device
```

If you see `unauthorized`, unlock the phone and approve the trust prompt.

### 5. Install the APK

```powershell
cd android-companion
powershell -ExecutionPolicy Bypass -File .\tools\install-debug.ps1
```

If installation is blocked:

- keep the phone unlocked
- watch for an on-device install confirmation
- allow `Install via USB` or similar brand-specific security toggles

## Method B: Wireless Debugging Plus ADB Install

Use this if:

- the phone supports Developer Options
- `Wireless debugging` is available
- you prefer not to use USB for the install step

### 1. Turn On Wireless Debugging

On the phone:

1. Open `Developer options`
2. Turn on `Wireless debugging`

### 2. Pair the Device

On the same Wi-Fi network:

1. Open the `Wireless debugging` screen on the phone
2. Choose `Pair device with pairing code`
3. Note the IP address, port, and pairing code

On the laptop:

```powershell
adb pair <phone-ip>:<pairing-port>
```

Enter the pairing code when prompted.

Then connect:

```powershell
adb connect <phone-ip>:<debug-port>
adb devices
```

### 3. Install the APK

```powershell
cd android-companion
powershell -ExecutionPolicy Bypass -File .\tools\install-debug.ps1
```

## Method C: Manual APK Install

Use this if:

- USB debugging is unavailable or blocked
- the phone still allows local APK installs

### 1. Copy the APK to the Phone

Use any of these:

- USB file transfer
- Google Drive
- OneDrive
- email
- a messaging app that allows APK attachments

Copy:

- `%LOCALAPPDATA%\CyberMzaziAndroid\project-build\app\outputs\apk\debug\app-debug.apk`

to the phone's `Download` folder if possible.

### 2. Allow Installation From the Source App

Open the APK from:

- `File Manager`
- `Files`
- `Chrome`
- `Drive`
- `OneDrive`

If Android blocks it:

1. Tap `Settings`
2. Enable `Allow from this source`
3. Return and tap the APK again

### 3. Install

Tap:

- `Install`
- then `Open`

If Play Protect blocks the APK, temporarily disable the scan, install the app, then turn Play Protect back on.

## Brand Notes

Menu names vary, but these patterns are the ones most people hit:

### Samsung and Pixel

- usually the simplest path
- `Developer options` and `USB debugging` are usually enough
- manual APK install is usually controlled by `Install unknown apps`

### Xiaomi, Redmi, and POCO

- may require both `USB debugging` and `USB debugging (Security settings)`
- may also require `Install via USB`

### Infinix and Tecno

- may allow manual APK install even when USB debugging is blocked
- check `Install unknown apps` for `File Manager` or the app source
- keep an eye out for extra XOS or HiOS security prompts

### Oppo, Realme, and Vivo

- often require confirming install permissions twice
- `Install unknown apps` and developer security prompts are the common blockers

### Huawei and Honor

- manual APK install is often the easiest path
- if Developer Options are available, USB debugging can still work
- some models show extra security dialogs before ADB install is allowed

## After the App Installs

Install the same APK on both phones if you want to test the full parent and child flow.

### 1. Set Up the Parent Phone

1. Open `Cyber Mzazi`.
2. Choose `Parent/Guardian`.
3. Confirm the parent capture safety panel says notification capture is off.
4. If it warns that notification access is enabled, tap `Open notification access settings` and disable Cyber Mzazi on the parent phone.
5. Enter the backend URL, for example `https://cyber-mzazi.onrender.com`.
6. Enter the parent email or phone and password.
7. Tap `Sign in for native alerts`.
8. Tap `Refresh native alert summary` to confirm the parent session works.
9. Enter a child phone name.
10. Tap `Create child pairing link`.
11. Copy or share the pairing link to the child phone.

The parent phone should not have Android notification access enabled. Parent mode is for viewing alerts, approving or denying child logout requests, reviewing flagged messages, and creating child pairing links.

### 2. Set Up the Child Phone

1. Open `Cyber Mzazi`.
2. Choose `Child`.
3. Use `Scan pairing QR`, or open or paste the pairing link from the parent phone.
4. Confirm the backend URL, device token, and device name are filled in.
5. Tap `Save settings`.
6. Tap `Open notification access`.
7. Enable `Cyber Mzazi notification listener`.
8. Return to Cyber Mzazi.
9. Confirm the child readiness panel shows the role, backend settings, and notification access are ready.
10. Optional: configure app filters.
11. Tap `Send test payload`.

Only the child phone should have Android notification access enabled.

### 3. Test the Connection

1. On the child phone, tap `Send test payload`.
2. On the parent phone, tap `Refresh native alert summary`.
3. Check the parent dashboard in:
   - `Alerts`
   - `Dashboard`
   - `Activity Log`
4. Send or receive a real notification on the child phone.
5. Refresh the parent phone again and confirm the real notification appears.

### 4. Web Fallback

If the parent phone is not available yet, you can still create the child device link from the web app:

1. Open [https://cyber-mzazi.onrender.com](https://cyber-mzazi.onrender.com).
2. Log in as parent.
3. Select a child.
4. Open `Child Profile`.
5. Create an `Android notification link`.
6. Pair the child phone with that link or QR code.

## Troubleshooting

### `adb devices` shows `unauthorized`

- unlock the phone
- accept the trust prompt
- disconnect and reconnect if needed

### ADB install fails with `INSTALL_FAILED_USER_RESTRICTED`

- keep the phone unlocked
- look for an install confirmation on the phone
- enable `Install via USB` or similar security settings
- retry the install

### The APK says `App not installed`

- allow `Install unknown apps` for the source app
- temporarily disable Play Protect if it is blocking the install
- retry from the file manager

### Notifications are not reaching Cyber Mzazi

- make sure the phone is in `Child` mode
- make sure the app is paired with a valid token
- confirm notification access is enabled on the child phone
- confirm notification access is disabled on the parent phone
- check allow/block package filters
- send a test payload first
- then test with a real incoming notification
