# Cyber Mzazi

Cyber Mzazi is a consent-led family safety platform built for parent/guardian visibility, child-safe workflows, and linked Android companion support.

It currently includes:

- A Flask web platform with separate `Parent/Guardian` and `Child` experiences
- Family registration, role-based login, and parent email verification
- Parent alerts, logout approval or denial, activity logs, and safety-resource uploads
- Child-side message safety checks and guided reporting flows
- Android companion infrastructure, branding, QR/device-link flows, and signed APK release setup
- Expanded safety classification labels with a lightweight production-safe heuristic mode
- Optional Hugging Face Space integration for DistilBERT-based inference experiments

## Current project status

### Web platform

Implemented:

- Public landing page at `/`
- Parent/guardian login and child login
- Family account registration
- Parent email verification and resend flow
- Parent dashboard, alerts, settings, logs, safety resources, and family hub
- Child dashboard, `My Safety`, settings, and safety-check reporting
- Parent approval-based child logout workflow
- Popup, browser, sound, and email alert support for parents
- Mobile sidebar toggle for parent and child dashboard pages

### AI classification

Current production-safe path:

- `MODEL_PROVIDER=heuristic`
- free-tier-friendly deployment without loading a large transformer in the main Render service

Available but optional:

- DistilBERT/Hugging Face Space flow for heavier inference experiments

Expanded label coverage includes:

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

### Android app

Already in place:

- Android companion project and Gradle setup
- Cyber Mzazi branding and app logo
- QR/device-link flow
- notification access flow
- offline queue and retry actions
- test payload and recent-log/status actions
- signed release APK workflow

Current product direction:

- **one Android app with role selection**
- role choices:
  - `Parent/Guardian`
  - `Child`

Still remaining on Android:

- first-launch role selection screen
- parent/guardian mobile flow
- child mobile flow
- role-based permissions and routing inside one APK
- end-to-end testing on both devices

## Important safety scope

Cyber Mzazi does **not** implement covert spying, forced account access, hidden persistence, or secret scraping of private content.

It is designed around:

- family-linked accounts
- consent-led monitoring workflows
- parent visibility into flagged content
- child-safe reporting and session controls
- approved Android notification ingestion where configured

## Repository guides

See these project docs for deeper setup details:

- [TECHNICAL_PROJECT_DOCUMENTATION.md](TECHNICAL_PROJECT_DOCUMENTATION.md)
- [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)
- [ANDROID_COMPANION.md](ANDROID_COMPANION.md)
- [ANDROID_DEVICE_SETUP.md](ANDROID_DEVICE_SETUP.md)
- [HF_SPACE_DEPLOYMENT.md](HF_SPACE_DEPLOYMENT.md)
- [FRONTEND_API.md](FRONTEND_API.md)

## Project structure

```text
app.py
config.py
scripts/
artifacts/
android-companion/
hf_space/
ml/
webapp/
```

## Local setup

### 1. Install dependencies

For the full local development stack:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

For slim Render-style runtime installs, the repo also includes:

```text
requirements-render.txt
```

### 2. Configure environment variables

Copy:

```text
.env.example -> .env
```

Important variables commonly used in this project:

- `DATABASE_URL`
- `MYSQL_SSL_CA_PATH`
- `SECRET_KEY`
- `APP_BASE_URL`
- `FRONTEND_ORIGIN`
- `MAIL_SERVER`
- `MAIL_PORT`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_USE_TLS`
- `MAIL_USE_SSL`
- `MAIL_DEFAULT_SENDER`
- `EMAIL_VERIFICATION_MAX_AGE`
- `ANDROID_COMPANION_DOWNLOAD_URL`
- `MODEL_PROVIDER`
- `ENABLE_HEURISTIC_FALLBACK`
- `FORCE_MODEL_RETRAIN`

### 3. Initialize the database

If needed, run the SQL bootstrap in:

- [database/mysql_bootstrap.sql](database/mysql_bootstrap.sql)

Then initialize tables:

```powershell
python scripts\init_db.py
```

The app also includes runtime schema repair logic for older deployments.

### 4. Run the web app locally

```powershell
python app.py
```

Then open:

- [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Training and model work

The repository supports broader training workflows beyond the original CSV-only setup.

Notes:

- production currently favors heuristic mode for free-tier stability
- DistilBERT experiments and staged artifacts are supported separately
- reviewed parent labels can still be used for retraining workflows

If you want to trigger training locally:

```powershell
$env:FLASK_APP = "app.py"
flask train-models
```

## Android companion flow

Cyber Mzazi supports Android-ready notification ingestion:

- parent generates an Android device link for a selected child
- the generated token is copied into the Android app
- the Android client sends notification payloads to:
  - `POST /api/device-ingest/android-notifications`
- the backend classifies the content and stores it as a `MessageRecord`

Typical payload fields:

- `app_name` or `source_platform`
- `app_package`
- `sender_handle`
- `notification_title`
- `notification_text` or `message_text`
- `deep_link` or `browser_origin`

## Render deployment

The repo includes:

- [render.yaml](render.yaml)
- [Procfile](Procfile)
- [wsgi.py](wsgi.py)

Current recommended free-tier-safe setup:

- `MODEL_PROVIDER=heuristic`
- `ENABLE_HEURISTIC_FALLBACK=true`
- `FORCE_MODEL_RETRAIN=false`

Do **not** load the large transformer artifact directly in the main free Render service.

Typical startup command:

```text
python scripts/bootstrap.py && gunicorn --bind 0.0.0.0:$PORT wsgi:app
```

Useful production variables:

- `APP_BASE_URL=https://cyber-mzazi.onrender.com`
- `FRONTEND_ORIGIN=https://cyber-mzazi.onrender.com`
- `SESSION_COOKIE_SECURE=true`
- `SESSION_COOKIE_SAMESITE=Lax`
- `ANDROID_COMPANION_DOWNLOAD_URL=<release apk url>`

## Gmail email verification setup

For real parent email verification with Gmail:

- `MAIL_SERVER=smtp.gmail.com`
- `MAIL_PORT=587`
- `MAIL_USE_TLS=true`
- `MAIL_USE_SSL=false`
- `MAIL_USERNAME=<your gmail>`
- `MAIL_PASSWORD=<gmail app password>`
- `MAIL_DEFAULT_SENDER=<your gmail>`

Use a Gmail **App Password**, not your normal Gmail password.

## Hugging Face Space

The repo includes a Hugging Face Space package in:

- [hf_space](hf_space)

This is for optional external inference experiments, not the required free-tier production path.

Publish helper:

- [tools/publish-hf-space.ps1](tools/publish-hf-space.ps1)

## What is still remaining

Main unfinished product work:

- complete the **one Android app with role selection** experience
- finish parent/guardian Android screens
- finish child Android screens
- apply role-based routing and permissions inside the Android app
- do full end-to-end multi-device testing:
  - parent web
  - parent phone
  - child phone
  - Android companion flow

Other remaining polish:

- more mobile UX refinement across the web app
- full production verification of all alert flows
- final decision on long-term transformer inference strategy

## License / usage note

This repository is structured as an educational and product-development project around family safety workflows. Any deployment or real-world use should remain transparent, consent-based, and aligned with local law, child protection guidance, and platform policies.
