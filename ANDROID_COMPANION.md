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

## Open in Android Studio

1. Open Android Studio.
2. Choose `Open`.
3. Select:

```text
android-companion
```

4. Let Gradle sync.
5. Connect a real Android device.
6. Run the `app` module.

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

## Current limits

- this uses Android notification access, not direct in-app message database access
- only message content exposed through notifications can be captured automatically
- deep links are not resolved yet
- pairing QR currently uses a generated web QR image
- token rotation is still parent-managed from the dashboard

## Next refinements

- add background retry and offline queueing
- add allow/block lists per app package
- add on-device preview of the last captured notification
- add token QR pairing instead of manual copy/paste
