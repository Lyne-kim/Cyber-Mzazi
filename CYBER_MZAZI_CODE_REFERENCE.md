# Cyber Mzazi Code Reference

This document explains the main source code that makes up Cyber Mzazi and shows where each part lives in the repository.

The goal of this guide is to help you answer three questions quickly:

1. What part of the system does this file control?
2. What are the important functions, classes, templates, or resources inside it?
3. Where do I click to open that code?

## 1. High-Level Architecture

Cyber Mzazi is made of four main technical layers:

1. Web application
   - Flask backend for authentication, dashboards, alerts, family workflows, uploads, and APIs.
2. Frontend templates and styling
   - Jinja HTML templates plus shared CSS for the public site, parent pages, and child pages.
3. AI and message classification
   - DistilBERT training code, model artifact management, heuristic fallback logic, and live prediction routing.
4. Android companion app
   - Kotlin Android app that captures notification data on a child device and sends it to the backend.

## 2. Main Source Folders

- Web backend and frontend:
  - [webapp](webapp)
- AI training and artifacts logic:
  - [ml](ml)
- Database bootstrap SQL:
  - [database](database)
- Android companion app:
  - [android-companion](android-companion)
- Runtime and setup scripts:
  - [scripts](scripts)
- Hugging Face Space deployment code:
  - [hf_space](hf_space)

## 3. Application Entry Points

### [app.py](app.py)
Purpose:
- Main local entry point for the Flask web app.

Main parts:
- `load_dotenv()` loads environment variables from `.env`.
- `create_app()` builds the Flask app from the `webapp` package.
- `app.run(debug=True)` starts the local development server.

Why it matters:
- This is the simplest file to run if you want the main Cyber Mzazi web app locally.

### [wsgi.py](wsgi.py)
Purpose:
- WSGI entry point for the main web service in deployment.

Main parts:
- Imports `app` from `app.py`.

Why it matters:
- Gunicorn uses this file in production for the main website.

### [ml_inference_app.py](ml_inference_app.py)
Purpose:
- Builds the separate ML inference service when Cyber Mzazi is deployed with a dedicated prediction API.

Main parts:
- `create_ml_inference_app()`
- `/health` endpoint
- `/predict` endpoint
- bearer-token check using `MODEL_INFERENCE_TOKEN`

Why it matters:
- This is the service used when the project wants model inference outside the main web app.

### [wsgi_ml.py](wsgi_ml.py)
Purpose:
- WSGI entry point for the separate ML inference service.

Main parts:
- Loads `.env`
- Creates the ML inference app via `create_ml_inference_app()`

Why it matters:
- Gunicorn uses this file when deploying a separate `cyber-mzazi-ml` style service.

## 4. Configuration and Environment

### [config.py](config.py)
Purpose:
- Central configuration file for the whole project.

Main parts:
- `_default_dataset_path()`
  - Chooses the training dataset location.
- `_default_model_artifact_path()`
  - Selects the newest local transformer artifact folder.
- `_normalize_database_url()`
  - Converts MySQL URLs into the SQLAlchemy format used by PyMySQL.
- `Config`
  - Stores application settings and environment variable bindings.

Important configuration groups:
- Database:
  - `SQLALCHEMY_DATABASE_URI`
  - `MYSQL_SSL_CA_PATH`
- AI:
  - `MODEL_ARTIFACT_PATH`
  - `MODEL_API_URL`
  - `MODEL_PROVIDER`
  - `ENABLE_HEURISTIC_FALLBACK`
  - `ENABLE_REVIEW_FEEDBACK_MATCHING`
- Training:
  - `TRANSFORMER_MODEL_NAME`
  - `TRANSFORMER_EPOCHS`
  - `TRAINING_MAX_ROWS_PER_LABEL`
- Web:
  - `APP_BASE_URL`
  - `FRONTEND_ORIGIN`
  - `SESSION_COOKIE_SECURE`
- Email:
  - `MAIL_SERVER`
  - `MAIL_USERNAME`
  - `MAIL_PASSWORD`
  - `ALERT_EMAIL_ENABLED`

Why it matters:
- If Cyber Mzazi behaves differently in local and production environments, this file is usually the first place to inspect.

## 5. Web Application Factory and Shared Extensions

### [webapp/__init__.py](webapp/__init__.py)
Purpose:
- Creates and configures the Flask web app.

Main parts:
- `create_app()`
  - loads config
  - enables CORS
  - initializes database and login manager
  - registers blueprints
  - injects shared UI helper functions into templates
  - defines the `train-models` Flask CLI command

Why it matters:
- This is the central assembly point for the web system.

### [webapp/extensions.py](webapp/extensions.py)
Purpose:
- Defines reusable Flask extensions.

Main parts:
- `db = SQLAlchemy()`
- `login_manager = LoginManager()`

Why it matters:
- Keeps the database and authentication setup reusable across all modules.

## 6. Database Models

### [webapp/models.py](webapp/models.py)
Purpose:
- Defines the database schema through SQLAlchemy models.

Main classes:

#### `TimestampMixin`
Adds:
- `created_at`
- `updated_at`

#### `Family`
Stores:
- family name
- parent contact
- child display name

Relationships:
- users
- message records
- activity logs
- logout requests
- safety resources
- notification devices

#### `User`
Stores:
- role
- name
- email
- phone
- username
- password hash
- language
- verification state

Key methods and properties:
- `set_password()`
- `check_password()`
- `requires_email_verification`
- `can_log_in`
- `display_identifier`

#### `MessageRecord`
Stores:
- submitted message text
- source platform
- prediction result
- verification result
- review feedback

Important fields:
- `predicted_label`
- `predicted_confidence`
- `review_signature`
- `reviewed_label`

#### `ActivityLog`
Stores:
- who did what
- to whom
- details of the action

#### `LogoutRequest`
Stores:
- child logout request
- note
- approval or denial status
- resolution metadata

#### `SafetyResourceDocument`
Stores:
- uploaded parent documents and binary file data

#### `NotificationIngestionDevice`
Stores:
- Android companion device link
- token hash
- last seen / ingestion activity

Key method:
- `hash_token()`

Why it matters:
- This file defines the business entities of the entire platform.

## 7. Authentication and Session Flow

### [webapp/auth.py](webapp/auth.py)
Purpose:
- Handles landing-page auth actions, registration, login, verification, and logout.

Main functions:
- `load_user()`
  - reloads the current user from session data
- `unauthorized()`
  - controls what happens if a protected page is accessed without login
- `index()`
  - public homepage
- `_login_user_by_portal()`
  - shared login logic
- `register()`
  - family registration
- `login()`
  - old route now redirected or simplified around homepage flows
- `parent_login()`
- `child_login()`
- `verify_email()`
- `resend_verification()`
- `request_logout()`
- `logout()`

Why it matters:
- All user entry into the system begins here.

## 8. API and Page-Oriented Backend Routes

### [webapp/api.py](webapp/api.py)
Purpose:
- Exposes JSON APIs and page-backed route handlers used across parent, child, Android, and system health workflows.

Helper payload builders:
- `_error()`
- `_user_payload()`
- `_message_payload()`
- `_notification_device_payload()`
- `_log_payload()`
- `_document_payload()`
- `_logout_request_payload()`
- `_parent_page_payload()`
- `_child_page_payload()`

Core endpoints:
- `health()`
- `register_family()`
- `login()`
- `logout()`
- `resend_verification()`
- `verify_email()`
- `current_session()`

Parent-related endpoints:
- `parent_dashboard()`
- `parent_alerts()`
- `parent_child_profile()`
- `parent_activity_log()`
- `parent_alert_settings()`
- `parent_family_hub()`
- `parent_safety_resources()`
- `parent_help_support()`
- `parent_privacy_center()`
- `parent_system_status()`
- `parent_insights()`
- `parent_language_settings()`
- `parent_notification_log()`
- `parent_trusted_contacts()`
- `review_message()`
- `approve_logout()`
- `deny_logout()`
- `parent_select_child()`
- `parent_add_child()`
- `parent_upload_resource_documents()`
- `parent_create_android_device()`
- `parent_disable_android_device()`

Android ingestion endpoint:
- `ingest_android_notification()`

Child-related endpoints:
- `child_dashboard()`
- `child_home()`
- `child_report()`
- `child_my_safety()`
- `child_talk()`
- `child_help()`
- `child_settings()`
- `submit_message()`
- `request_logout()`
- `set_ui_language()`
- `activity()`

Why it matters:
- This file is the broadest request/response layer for the product.

## 9. Parent Experience Code

### [webapp/parent.py](webapp/parent.py)
Purpose:
- Implements the parent/guardian dashboard and parent-specific workflows.

Alert-state helpers:
- `_alert_session_key()`
- `_latest_alert_key()`
- `_mark_alerts_seen()`
- `_unread_alert_count()`
- `_build_notification_items()`

Security and page-building:
- `require_parent()`
- `_parent_data()`
- `_render_parent_page()`

Main parent pages:
- `dashboard()`
- `alerts()`
- `child_profile()`
- `activity_log()`
- `alert_settings()`
- `family_hub()`
- `safety_resources()`
- `help_support()`
- `privacy_center()`
- `system_status()`
- `insights()`
- `language_settings()`
- `notification_log()`
- `trusted_contacts()`

Parent actions:
- `notification_feed()`
- `mark_alerts_seen()`
- `select_child()`
- `add_child()`
- `set_language()`
- `attach_resource_documents()`
- `create_android_device()`
- `disable_android_device()`
- `download_resource_document()`
- `review_message()`
- `approve_logout()`
- `deny_logout()`

Why it matters:
- This file drives most of the guardian-side monitoring and control features.

## 10. Child Experience Code

### [webapp/child.py](webapp/child.py)
Purpose:
- Implements child-facing pages and child-side reporting/submission flows.

Main parts:
- `require_child()`
  - protects child-only pages
- `_child_data()`
  - collects child dashboard data
- `_render_child_page()`
  - shared child page renderer

Child pages:
- `dashboard()`
- `my_safety()`
- `talk()`
- `help_questions()`
- `settings()`
- `report()`

Child actions:
- `set_language()`
- `submit_message()`

Why it matters:
- This file is the child-side experience layer for web workflows.

## 11. Shared UI Text

### [webapp/ui_text.py](webapp/ui_text.py)
Purpose:
- Centralizes multilingual UI strings and language selection.

Main functions:
- `get_language()`
- `t()`

Why it matters:
- Templates rely on this file to translate labels and headings.

## 12. Service Layer

Service modules hold reusable business logic so routes stay smaller and easier to maintain.

### [webapp/services/audit.py](webapp/services/audit.py)
Purpose:
- Saves audit entries into the activity log.

Main function:
- `log_event()`

### [webapp/services/email_verification.py](webapp/services/email_verification.py)
Purpose:
- Manages email verification token generation and sending.

Main parts:
- `_serializer()`
- `is_mail_configured()`
- `generate_email_verification_token()`
- `verify_email_token()`
- `build_email_verification_link()`
- `send_verification_email()`

### [webapp/services/family_context.py](webapp/services/family_context.py)
Purpose:
- Tracks which child is currently selected in a parent session.

Main parts:
- `_selected_child_key()`
- `get_family_children()`
- `get_selected_child()`
- `set_selected_child()`

### [webapp/services/ml_service.py](webapp/services/ml_service.py)
Purpose:
- Loads and runs the local message classifier.

Main classes:
- `MessageClassifier`
  - transformer or legacy classifier wrapper
- `HeuristicMessageClassifier`
  - rule-based fallback classifier

Main function:
- `get_classifier()`

Why it matters:
- This is the core local ML/heuristic inference engine.

### [webapp/services/notification_devices.py](webapp/services/notification_devices.py)
Purpose:
- Manages Android device ingestion tokens and last-seen activity.

Main functions:
- `issue_ingestion_token()`
- `verify_ingestion_token()`
- `touch_ingestion_device()`

### [webapp/services/parent_alerts.py](webapp/services/parent_alerts.py)
Purpose:
- Sends parent alerts by email and prepares alert links.

Main functions:
- `_can_send_parent_alerts()`
- `_alerts_url()`
- `_send_email()`
- `send_high_risk_message_alert()`
- `send_logout_request_alert()`

### [webapp/services/prediction_service.py](webapp/services/prediction_service.py)
Purpose:
- Chooses between local classifier, remote ML API, and fallback behavior.

Main classes:
- `PredictionResult`
- `PredictionUnavailable`

Main functions:
- `prediction_backend_status()`
- `predict_message()`

Why it matters:
- This is the bridge between the web app and whichever prediction backend is active.

### [webapp/services/review_feedback.py](webapp/services/review_feedback.py)
Purpose:
- Reuses reviewed labels for similar future messages.

Main functions:
- `normalize_review_text()`
- `build_review_signature()`
- `find_review_feedback()`

Why it matters:
- This is the “live learning from parent review” layer currently active in production.

### [webapp/services/schema.py](webapp/services/schema.py)
Purpose:
- Repairs and expands runtime database schema automatically.

Main parts:
- `_column_exists()`
- `ensure_runtime_schema()`

Why it matters:
- Helps new columns and attachment changes reach live environments without manual migration tools.

### [webapp/services/verification.py](webapp/services/verification.py)
Purpose:
- Adds a verification pass on submitted messages.

Main function:
- `verify_message()`

## 13. Frontend Templates

These HTML files define the user-visible interface.

### [webapp/templates/base.html](webapp/templates/base.html)
Purpose:
- Shared base layout, header logic, scripts, and global template blocks.

### [webapp/templates/landing.html](webapp/templates/landing.html)
Purpose:
- Public homepage shown at the root URL.

### [webapp/templates/register.html](webapp/templates/register.html)
Purpose:
- Family account registration page.

### [webapp/templates/parent_login.html](webapp/templates/parent_login.html)
Purpose:
- Parent/guardian sign-in page.

### [webapp/templates/child_login.html](webapp/templates/child_login.html)
Purpose:
- Child sign-in page.

### [webapp/templates/login.html](webapp/templates/login.html)
Purpose:
- Legacy chooser/login page kept for compatibility.

### [webapp/templates/parent_page.html](webapp/templates/parent_page.html)
Purpose:
- Main parent app shell with sidebar, content panes, alerts, and mobile sidebar toggle.

### [webapp/templates/parent_dashboard.html](webapp/templates/parent_dashboard.html)
Purpose:
- Parent dashboard summary view.

### [webapp/templates/child_page.html](webapp/templates/child_page.html)
Purpose:
- Main child app shell, including safety summary, request sign-out UI, and auto-dismissing notices.

### [webapp/templates/child_dashboard.html](webapp/templates/child_dashboard.html)
Purpose:
- Child dashboard summary view.

## 14. Frontend Static Assets

### [webapp/static/style.css](webapp/static/style.css)
Purpose:
- Main CSS file for the homepage, auth pages, parent pages, child pages, alerts, cards, mobile sidebar, and responsive behavior.

Why it matters:
- Almost every visible visual adjustment eventually lands here.

### [webapp/static/cyber_mzazi_logo.png](webapp/static/cyber_mzazi_logo.png)
Purpose:
- Shared logo used by the web frontend.

## 15. AI and Training Code

### [ml/train.py](ml/train.py)
Purpose:
- Main training pipeline for the Cyber Mzazi text classifier.

Main class:
- `TextDataset`

Training and evaluation flow:
- `seed_everything()`
- `train_one_epoch()`
- `evaluate()`
- `train_and_save()`

Data cleaning and balancing:
- `_clean_text()`
- `_clean_language()`
- `_join_indicators()`
- `_make_row()`
- `_sample_frame()`
- `_cap_by_group()`

Dataset loaders:
- `_load_normalized_csv()`
- `_load_bongo_scam()`
- `_load_grooming_swahili()`
- `_load_multilabel_cyberbully()`
- `_load_fact_dataset()`
- `_load_dataset_xlsx()`
- `_load_common_malware()`
- `_load_romance_scam()`
- `_load_mobile_threats()`
- `_load_phishing_email()`
- `_load_ransomware()`
- `_load_bot_detection()`
- `_load_malicious_phish()`
- `_load_original_toxicity()`
- `_load_feedback_rows()`
- `_collect_rows_from_path()`
- `build_training_frame()`

Why it matters:
- This is where datasets are normalized, balanced, and converted into a model-ready training frame.

### [ml/labels.py](ml/labels.py)
Purpose:
- Defines the supported classification labels and how they are presented in the UI.

Main functions:
- `label_title()`
- `label_tone()`
- `label_summary_rows()`

Why it matters:
- Keeps AI labels readable for parents and dashboards.

### [ml/artifacts.py](ml/artifacts.py)
Purpose:
- Handles transformer artifact location and ZIP download/extraction.

Main functions:
- `resolve_transformer_artifact_dir()`
- `resolve_legacy_artifact_file()`
- `transformer_artifact_exists()`
- `ensure_parent_dir()`
- `download_and_extract_transformer_artifact()`

Why it matters:
- This file controls how trained model folders are discovered or downloaded.

## 16. Database Bootstrap

### [database/mysql_bootstrap.sql](database/mysql_bootstrap.sql)
Purpose:
- Manual MySQL bootstrap script for first-time database setup.

Main parts:
- creates the `cyber_mzazi` database
- creates the `cyber_mzazi` MySQL user
- grants privileges

Why it matters:
- Useful for local setup when you want a dedicated database user.

## 17. Setup and Maintenance Scripts

### [scripts/bootstrap.py](scripts/bootstrap.py)
Purpose:
- Startup helper that prepares schema and optionally handles model/bootstrap tasks.

Main parts:
- `collect_feedback_rows()`
- `main()`

Why it matters:
- This script is used in deployment before Gunicorn starts.

### [scripts/init_db.py](scripts/init_db.py)
Purpose:
- Simple script to create/repair tables and apply runtime schema changes.

Why it matters:
- Useful when you need the current database to pick up new fields like review feedback signatures.

## 18. Android Companion Application

The Android source code lives under:
- [android-companion/app/src/main](android-companion/app/src/main)

### Build and project configuration

#### [android-companion/build.gradle.kts](android-companion/build.gradle.kts)
Purpose:
- Top-level Gradle build configuration.

#### [android-companion/settings.gradle.kts](android-companion/settings.gradle.kts)
Purpose:
- Declares the Android project modules.

#### [android-companion/gradle.properties](android-companion/gradle.properties)
Purpose:
- Shared Gradle properties.

#### [android-companion/keystore.properties.example](android-companion/keystore.properties.example)
Purpose:
- Example signing configuration for release builds.

#### [android-companion/local.properties.example](android-companion/local.properties.example)
Purpose:
- Example local Android SDK path configuration.

### Android manifest

#### [android-companion/app/src/main/AndroidManifest.xml](android-companion/app/src/main/AndroidManifest.xml)
Purpose:
- Declares app permissions, service registration, and Android components.

Why it matters:
- Notification listener capability is wired here.

### Android Kotlin source files

#### [android-companion/app/src/main/java/com/cybermzazi/companion/MainActivity.kt](android-companion/app/src/main/java/com/cybermzazi/companion/MainActivity.kt)
Purpose:
- Main Android screen and user workflow controller.

What it handles:
- form inputs
- pairing/setup actions
- manual payload sending
- retry queue
- recent log display

#### [android-companion/app/src/main/java/com/cybermzazi/companion/CyberMzaziNotificationListener.kt](android-companion/app/src/main/java/com/cybermzazi/companion/CyberMzaziNotificationListener.kt)
Purpose:
- Background listener that captures posted Android notifications.

Why it matters:
- This is how the child device can forward third-party message content into Cyber Mzazi.

#### [android-companion/app/src/main/java/com/cybermzazi/companion/IngestionClient.kt](android-companion/app/src/main/java/com/cybermzazi/companion/IngestionClient.kt)
Purpose:
- Sends captured notification payloads to the backend.

#### [android-companion/app/src/main/java/com/cybermzazi/companion/NotificationPayload.kt](android-companion/app/src/main/java/com/cybermzazi/companion/NotificationPayload.kt)
Purpose:
- Data model for notification payloads sent from Android to the backend.

#### [android-companion/app/src/main/java/com/cybermzazi/companion/NotificationQueueStore.kt](android-companion/app/src/main/java/com/cybermzazi/companion/NotificationQueueStore.kt)
Purpose:
- Stores payloads locally when sending fails, so they can be retried later.

#### [android-companion/app/src/main/java/com/cybermzazi/companion/RecentNotificationLog.kt](android-companion/app/src/main/java/com/cybermzazi/companion/RecentNotificationLog.kt)
Purpose:
- Builds and formats the recent-notification history shown in the Android UI.

#### [android-companion/app/src/main/java/com/cybermzazi/companion/Prefs.kt](android-companion/app/src/main/java/com/cybermzazi/companion/Prefs.kt)
Purpose:
- Shared preferences helper for app settings and saved values.

#### [android-companion/app/src/main/java/com/cybermzazi/companion/FilterRules.kt](android-companion/app/src/main/java/com/cybermzazi/companion/FilterRules.kt)
Purpose:
- Holds filtering logic for which notifications should be processed.

### Android layout and resources

#### [android-companion/app/src/main/res/layout/activity_main.xml](android-companion/app/src/main/res/layout/activity_main.xml)
Purpose:
- Main Android screen layout.

#### [android-companion/app/src/main/res/values/strings.xml](android-companion/app/src/main/res/values/strings.xml)
Purpose:
- User-facing text strings.

#### [android-companion/app/src/main/res/values/colors.xml](android-companion/app/src/main/res/values/colors.xml)
Purpose:
- Core Android color tokens.

#### [android-companion/app/src/main/res/values/styles.xml](android-companion/app/src/main/res/values/styles.xml)
Purpose:
- Shared Android styles.

#### [android-companion/app/src/main/res/values/themes.xml](android-companion/app/src/main/res/values/themes.xml)
Purpose:
- Android app theme definitions.

#### Android drawables
Purpose:
- Visual surfaces, cards, hero backgrounds, nav states, and buttons.

Files:
- [android-companion/app/src/main/res/drawable/bg_bottom_nav.xml](android-companion/app/src/main/res/drawable/bg_bottom_nav.xml)
- [android-companion/app/src/main/res/drawable/bg_card.xml](android-companion/app/src/main/res/drawable/bg_card.xml)
- [android-companion/app/src/main/res/drawable/bg_hero.xml](android-companion/app/src/main/res/drawable/bg_hero.xml)
- [android-companion/app/src/main/res/drawable/bg_input.xml](android-companion/app/src/main/res/drawable/bg_input.xml)
- [android-companion/app/src/main/res/drawable/bg_menu_button.xml](android-companion/app/src/main/res/drawable/bg_menu_button.xml)
- [android-companion/app/src/main/res/drawable/bg_nav_active.xml](android-companion/app/src/main/res/drawable/bg_nav_active.xml)
- [android-companion/app/src/main/res/drawable/bg_screen.xml](android-companion/app/src/main/res/drawable/bg_screen.xml)
- [android-companion/app/src/main/res/drawable/bg_status.xml](android-companion/app/src/main/res/drawable/bg_status.xml)
- [android-companion/app/src/main/res/drawable/bg_surface_shell.xml](android-companion/app/src/main/res/drawable/bg_surface_shell.xml)
- [android-companion/app/src/main/res/drawable/cyber_mzazi_logo.png](android-companion/app/src/main/res/drawable/cyber_mzazi_logo.png)

### Android build tools

#### [android-companion/tools/build-debug.ps1](android-companion/tools/build-debug.ps1)
Purpose:
- Builds a debug APK.

#### [android-companion/tools/build-release.ps1](android-companion/tools/build-release.ps1)
Purpose:
- Builds a release APK.

#### [android-companion/tools/install-debug.ps1](android-companion/tools/install-debug.ps1)
Purpose:
- Installs a debug APK to a connected device.

#### [android-companion/tools/install-release.ps1](android-companion/tools/install-release.ps1)
Purpose:
- Installs a release APK to a connected device.

#### [android-companion/tools/setup-android-sdk.md](android-companion/tools/setup-android-sdk.md)
Purpose:
- Setup instructions for the Android SDK environment.

## 19. Hugging Face Space Files

These files support the optional external DistilBERT hosting path.

- [hf_space/app.py](hf_space/app.py)
- [hf_space/Dockerfile](hf_space/Dockerfile)
- [hf_space/README.md](hf_space/README.md)

Purpose:
- package the inference service for a Hugging Face Space deployment

## 20. Existing Project Documentation

These are already in the repository and complement this code-reference guide:

- [README.md](README.md)
- [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)
- [ANDROID_COMPANION.md](ANDROID_COMPANION.md)
- [ANDROID_DEVICE_SETUP.md](ANDROID_DEVICE_SETUP.md)
- [FRONTEND_API.md](FRONTEND_API.md)
- [HF_SPACE_DEPLOYMENT.md](HF_SPACE_DEPLOYMENT.md)

## 21. Files That Are Not Core Source Code

These folders are usually not where you edit product logic:

- `artifacts`
  - trained model outputs and compiled datasets
- `instance`
  - Flask instance/runtime data
- `__pycache__`
  - Python bytecode cache
- `android-companion/build`
  - generated Android build outputs
- `android-companion/.gradle`
  - Gradle cache/build state
- `android-companion/.tools/gradle-*`
  - bundled Gradle distribution files

## 22. Recommended Reading Order

If you want to understand Cyber Mzazi from top to bottom, read in this order:

1. [README.md](README.md)
2. [app.py](app.py)
3. [webapp/__init__.py](webapp/__init__.py)
4. [config.py](config.py)
5. [webapp/models.py](webapp/models.py)
6. [webapp/auth.py](webapp/auth.py)
7. [webapp/parent.py](webapp/parent.py)
8. [webapp/child.py](webapp/child.py)
9. [webapp/api.py](webapp/api.py)
10. [webapp/services/prediction_service.py](webapp/services/prediction_service.py)
11. [webapp/services/ml_service.py](webapp/services/ml_service.py)
12. [ml/train.py](ml/train.py)
13. [android-companion/app/src/main/java/com/cybermzazi/companion/MainActivity.kt](android-companion/app/src/main/java/com/cybermzazi/companion/MainActivity.kt)
14. [android-companion/app/src/main/java/com/cybermzazi/companion/CyberMzaziNotificationListener.kt](android-companion/app/src/main/java/com/cybermzazi/companion/CyberMzaziNotificationListener.kt)

## 23. Short Summary

If you want to remember Cyber Mzazi in one sentence:

- `webapp` contains the live web product,
- `ml` contains the training and model logic,
- `database` contains bootstrap SQL,
- `android-companion` contains the child-device companion app,
- and `config.py` plus the WSGI entry points decide how everything is wired together in deployment.
