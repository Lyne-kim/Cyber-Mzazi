# Android SDK Setup Without Android Studio

Use the Android SDK command-line tools plus VS Code.

## Required components

- JDK 17
- Android SDK Command-line Tools
- Android Platform Tools
- Android Platform 35
- Android Build Tools 34.0.0
- `keytool` from your JDK installation for signed release APKs

## Suggested setup on Windows

1. Download Android SDK command-line tools from the official Android Developers site:
   [Android command-line tools](https://developer.android.com/studio#command-tools)
2. Extract them under a folder such as:

```text
C:\Android\Sdk\cmdline-tools\latest
```

3. Set environment variables:

```powershell
setx ANDROID_SDK_ROOT "C:\Android\Sdk"
setx PATH "%PATH%;C:\Android\Sdk\platform-tools;C:\Android\Sdk\cmdline-tools\latest\bin"
```

4. Open a new terminal and install packages:

```powershell
sdkmanager "platform-tools" "platforms;android-35" "build-tools;34.0.0"
sdkmanager --licenses
```

5. Copy `local.properties.example` to `local.properties` if needed and update the SDK path.
