# Cyber Mzazi Handoff After Windows Reinstall

Use this file later to resume work exactly where we left off.

## Project

- Name: `Cyber Mzazi`
- Workspace path before reinstall:
  - `C:\Users\Admin\OneDrive\Documents\Cyber Mzazi`

## Current State

### Web app

Working areas already built:

- public homepage
- parent/guardian login
- child login
- family registration
- parent dashboard
- child dashboard
- parent alerts
- parent approve/deny child logout
- safety resource uploads
- mobile sidebar toggle
- child notice auto-dismiss

### AI

- DistilBERT training works **locally**
- live production does **not** run full DistilBERT right now
- live production uses:
  - `MODEL_PROVIDER=heuristic`
- reviewed parent labels now affect future similar live predictions through review-feedback matching

### Android companion

Important product decision:

- use **one Android app with role selection**
- roles:
  - `Parent/Guardian`
  - `Child`

Important safety rule:

- only the **child phone** should capture third-party notifications
- parent phone must **not** capture notifications

## Latest Android Changes Completed

Completed:

- added persisted device role in Android preferences
- added role selection UI
- added role badge
- parent mode hides capture/filter navigation
- parent mode blocks notification capture actions
- notification listener now only works when the phone role is `child`

Main Android files changed:

- [android-companion/app/src/main/java/com/cybermzazi/companion/MainActivity.kt](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\java\com\cybermzazi\companion\MainActivity.kt)
- [android-companion/app/src/main/java/com/cybermzazi/companion/Prefs.kt](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\java\com\cybermzazi\companion\Prefs.kt)
- [android-companion/app/src/main/java/com/cybermzazi/companion/CyberMzaziNotificationListener.kt](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\java\com\cybermzazi\companion\CyberMzaziNotificationListener.kt)
- [android-companion/app/src/main/res/layout/activity_main.xml](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\res\layout\activity_main.xml)
- [android-companion/app/src/main/res/values/strings.xml](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\res\values\strings.xml)

## Next Step We Were About To Do

Continue Android development from the new role-selection foundation.

Immediate next tasks:

1. make the Android parent home and child home more clearly different
2. keep parent role limited to parent-safe actions only
3. keep child role limited to capture/monitoring actions only
4. test on two phones:
   - parent phone
   - child phone
5. confirm only child phone captures notifications

## AI / Dataset Notes

- training datasets were compiled and cleaned
- a 5,000-row filtered CSV was created with only:
  - English
  - Swahili
  - Sheng

Useful files:

- [artifacts/compiled_training_dataset_5000.csv](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\artifacts\compiled_training_dataset_5000.csv)
- [artifacts/compiled_training_dataset_5000_report.txt](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\artifacts\compiled_training_dataset_5000_report.txt)

## Important Documentation Files

If you want to give full context later, send these too:

- [CHAT_PROGRESS_RECORD.md](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\CHAT_PROGRESS_RECORD.md)
- [CYBER_MZAZI_CODE_REFERENCE.md](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\CYBER_MZAZI_CODE_REFERENCE.md)
- [CYBER_MZAZI_DETAILED_CODE_EXPLANATION.md](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\CYBER_MZAZI_DETAILED_CODE_EXPLANATION.md)
- [README.md](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\README.md)

## Best Message To Send Later

When you come back after reinstalling Windows, send this:

```text
Resume Cyber Mzazi from the Android role-selection stage. The Android app is one app with Parent/Guardian and Child roles, and only the child phone should capture third-party notifications. Continue from WINDOWS_REINSTALL_HANDOFF.md and CHAT_PROGRESS_RECORD.md.
```

## Short Summary

- Web platform is largely built
- Live AI currently uses heuristics
- DistilBERT training worked locally
- Android role-selection foundation is now started
- Next focus is Android parent vs child role flows
