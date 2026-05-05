# Cyber Mzazi Chat Progress Record

This document records the main work completed in this conversation history so far. It is a project-progress summary, not a raw verbatim chat transcript.

It captures:

1. What was built or changed
2. Key decisions made
3. AI and deployment outcomes
4. Android companion direction
5. Current status and next steps

## 1. Project Direction

Cyber Mzazi is being built as a family safety platform with:

- a web platform for parent/guardian and child workflows
- AI-supported message classification
- parent alerts and review workflows
- a companion Android app

A major product decision was made for Android:

- use **one Android app with role selection**
- roles:
  - `Parent/Guardian`
  - `Child`

Another important device-safety rule was confirmed:

- **only the child phone should capture third-party notifications**
- parent/guardian phones must not run message capture

## 2. Web Platform Progress

### Public homepage and auth

Completed:

- replaced the old `/login` entry flow with a public homepage at:
  - `https://cyber-mzazi.onrender.com`
- added direct actions from the homepage to:
  - parent/guardian login
  - child login
  - family registration
- removed the need for users to stop at a separate login chooser page
- redesigned the homepage several times for a cleaner phone layout
- updated the parent and child authentication pages with a cyber-style design

Files involved included:

- [webapp/auth.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\auth.py)
- [webapp/templates/landing.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\landing.html)
- [webapp/templates/parent_login.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\parent_login.html)
- [webapp/templates/child_login.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\child_login.html)
- [webapp/templates/register.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\register.html)
- [webapp/static/style.css](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\static\style.css)

### Parent dashboard and workflows

Completed:

- parent dashboard and navigation
- alerts page
- child profile view
- activity log
- family hub
- safety resources area
- alert settings
- notification log
- trusted contacts
- language settings
- system status and insights sections

Completed parent-side behaviors:

- review flagged messages
- approve child logout requests
- deny child logout requests
- attach and download safety resource files
- create and disable Android ingestion devices

Files involved included:

- [webapp/parent.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\parent.py)
- [webapp/templates/parent_page.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\parent_page.html)
- [webapp/templates/parent_dashboard.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\parent_dashboard.html)

### Child dashboard and workflows

Completed:

- child dashboard
- my safety view
- safety check/report flow
- settings view
- request sign-out flow

UI clean-up completed:

- removed `Talk`
- removed `Help`
- removed long sign-out explanatory text from the child request sign-out interface
- made child info/flash notices auto-dismiss after 15 seconds instead of staying as permanent-looking banners
- added a show/hide toggle for recent safety summaries
- persisted summary toggle state on the device using local storage

Files involved included:

- [webapp/child.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\child.py)
- [webapp/templates/child_page.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\child_page.html)

### Mobile usability changes

Completed:

- added a mobile sidebar toggle for parent and child pages
- sidebar now hides by default on phones and opens via a menu button
- improved homepage phone layout across multiple iterations

Files involved included:

- [webapp/templates/base.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\base.html)
- [webapp/templates/parent_page.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\parent_page.html)
- [webapp/templates/child_page.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\child_page.html)
- [webapp/static/style.css](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\static\style.css)

## 3. Parent Alerts and Notifications

Completed:

- parent browser popup-style alerts
- parent browser Web Notifications API support
- parent alert sound
- parent email alerts
- mobile-friendly bottom-sheet style alert behavior

Usability fixes completed:

- enabling popup notifications hides the enable button after permission is granted
- opening the alerts page clears the unread alert count
- reviewed alerts stop hanging on the alerts list
- alerts now behave like read/unread items instead of permanent counters

Files involved included:

- [webapp/services/parent_alerts.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\services\parent_alerts.py)
- [webapp/parent.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\parent.py)
- [webapp/templates/parent_page.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\parent_page.html)

## 4. Logout Approval / Denial Flow

Completed:

- child can request sign-out
- parent receives the sign-out request
- parent can approve logout
- parent can deny logout
- denied requests are reflected back on the child side
- denied requests stop staying as pending on the parent side
- child can request sign-out again later after a denial

Files involved included:

- [webapp/parent.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\parent.py)
- [webapp/child.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\child.py)
- [webapp/api.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\api.py)
- [webapp/templates/child_page.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\child_page.html)

## 5. AI / DistilBERT Work

### Training and label expansion

Completed:

- retrained the AI using DistilBERT locally
- used the datasets from:
  - `C:\Users\Admin\Downloads\datasets`
- expanded the classification labels
- changed dataset handling so the model does not overfit to one platform name

Expanded label set:

- `safe`
- `grooming`
- `sexual_content`
- `sextortion`
- `betting`
- `phishing`
- `scam`
- `financial_fraud`
- `malware`
- `cyberbullying`
- `violence`
- `hate_speech`
- `bot_activity`
- `misinformation`

Model and training files involved:

- [ml/train.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\ml\train.py)
- [ml/labels.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\ml\labels.py)
- [ml/artifacts.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\ml\artifacts.py)

### DistilBERT deployment outcome

Important result:

- DistilBERT training worked locally
- but full DistilBERT deployment on free hosting was not reliable

What happened:

- free Render ran into RAM and storage limits
- direct model artifact bootstrap caused startup failures and memory issues
- Hugging Face Space setup was prepared and published, but the free path was not stable enough for the current project setup

Therefore:

- DistilBERT is **not** the active live production classifier right now
- production uses heuristic mode for stability

Current live production classifier:

- `MODEL_PROVIDER=heuristic`

### Review-feedback learning

Completed:

- parent-reviewed labels are now reused for future matching or very similar messages
- this works live even while the production system is using heuristics
- this is not full automatic DistilBERT fine-tuning
- it is a live feedback-matching layer

Files involved included:

- [webapp/services/review_feedback.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\services\review_feedback.py)
- [webapp/services/prediction_service.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\services\prediction_service.py)
- [webapp/models.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\models.py)

## 6. Dataset Work

Completed:

- compiled full merged dataset
- compiled cleaned training dataset
- created quality reports
- generated a 5,000-row CSV
- filtered it so it contains only:
  - English
  - Swahili
  - Sheng

Files created in artifacts included:

- [compiled_training_dataset_full.csv](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\artifacts\compiled_training_dataset_full.csv)
- [compiled_training_dataset_clean.csv](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\artifacts\compiled_training_dataset_clean.csv)
- [compiled_training_dataset_5000.csv](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\artifacts\compiled_training_dataset_5000.csv)
- [dataset_quality_report.md](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\artifacts\dataset_quality_report.md)
- [dataset_quality_report.json](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\artifacts\dataset_quality_report.json)

Important finding:

- some raw data contained encoding corruption (mojibake)
- the cleaned pipeline removed or repaired usable rows before training/export

## 7. Database and Backend Structure Work

Completed:

- clarified where frontend, backend, AI, and database code live
- documented the main folders and modules
- fixed runtime schema issues for live review-feedback matching and uploads
- successfully initialized the database schema using the Aiven connection locally

Files involved included:

- [config.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\config.py)
- [webapp/models.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\models.py)
- [webapp/services/schema.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\services\schema.py)
- [scripts/init_db.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\scripts\init_db.py)
- [database/mysql_bootstrap.sql](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\database\mysql_bootstrap.sql)

## 8. Safety Resource Uploads

Completed:

- fixed attachment upload/download behavior in safety resources
- widened binary attachment storage for MySQL
- added graceful rejection for files above the allowed limit

Files involved included:

- [webapp/models.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\models.py)
- [webapp/services/schema.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\services\schema.py)
- [webapp/parent.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\parent.py)
- [webapp/api.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\api.py)

## 9. Android Companion App Progress

### Earlier Android work already completed

Completed before the latest role-selection pass:

- Android companion project setup
- branding/logo update
- QR pairing flow
- notification access flow
- save settings flow
- manual test payload flow
- offline retry queue
- recent status/log refresh
- signed APK workflow
- Android release/setup documentation

Main Android code location:

- [android-companion](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion)

### Current Android product decision

Confirmed direction:

- one Android app
- two roles inside it:
  - `Parent/Guardian`
  - `Child`

### Latest Android implementation pass

Completed in the current pass:

- persisted device role in shared preferences
- added role-selection controls to the Android UI
- added a visible role badge in the top bar
- parent mode now hides capture/filter nav items
- parent mode blocks notification capture actions
- the notification listener now exits unless the phone is set to child role
- QR pairing can optionally apply a role from the QR payload

Files changed:

- [android-companion/app/src/main/java/com/cybermzazi/companion/Prefs.kt](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\java\com\cybermzazi\companion\Prefs.kt)
- [android-companion/app/src/main/java/com/cybermzazi/companion/CyberMzaziNotificationListener.kt](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\java\com\cybermzazi\companion\CyberMzaziNotificationListener.kt)
- [android-companion/app/src/main/java/com/cybermzazi/companion/MainActivity.kt](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\java\com\cybermzazi\companion\MainActivity.kt)
- [android-companion/app/src/main/res/layout/activity_main.xml](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\res\layout\activity_main.xml)
- [android-companion/app/src/main/res/values/strings.xml](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\res\values\strings.xml)

Current Android rule now enforced:

- **child role = allowed to capture notifications**
- **parent role = no third-party notification capture**

## 10. Documentation Created During This Work

Created documentation includes:

- [README.md](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\README.md)
  - updated to reflect the current real project state
- [CYBER_MZAZI_CODE_REFERENCE.md](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\CYBER_MZAZI_CODE_REFERENCE.md)
  - project code map with links to source files
- [CYBER_MZAZI_DETAILED_CODE_EXPLANATION.md](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\CYBER_MZAZI_DETAILED_CODE_EXPLANATION.md)
  - deeper teaching-style explanation of the source code

Project/proposal document work also included:

- creating a Cyber Mzazi project proposal document
- adding system diagrams into the proposal

## 11. Current Live State

Current practical status:

- the website is live
- parent and child web workflows are largely built
- parent alerts and logout approval/denial are in place
- review-feedback matching is active in the live logic after deployment
- production AI is currently heuristic-based for deployment stability
- Android companion exists and now has the beginning of role-based behavior

## 12. What Is Still Remaining

### Highest-priority remaining Android work

Still to build:

1. clearer parent mobile home vs child mobile home
2. full role-based routing and UX polish
3. parent-specific phone experience for alert review
4. child-specific phone experience for safety/capture tasks
5. end-to-end testing on:
   - parent phone
   - child phone

### Other remaining work

- more mobile homepage polish if desired
- full production AI hosting decision if DistilBERT is to be used live later
- end-to-end testing across web, Android, alerts, uploads, and logout workflows

## 13. Current Recommended Next Step

The best next step after this record is:

- continue the Android app build from the new role-selection foundation

Recommended immediate Android sequence:

1. separate parent home and child home sections more clearly
2. connect parent role to parent-safe actions only
3. connect child role to capture and monitoring actions only
4. test notification capture on a child phone and confirm parent phone capture stays disabled

## 14. Short Summary

In simple terms:

- Cyber Mzazi web is mostly built
- production AI currently uses heuristics, while DistilBERT work succeeded locally
- parent review feedback now influences future live predictions through matching
- datasets were cleaned, compiled, and filtered
- Android now has the first implementation of one-app-two-roles
- and only the child phone is now allowed to capture third-party notifications
