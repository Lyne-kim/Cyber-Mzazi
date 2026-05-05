# Cyber Mzazi Detailed Code Explanation

This document explains Cyber Mzazi in a teaching style similar to the example you shared.

It focuses on:

1. Imports and what they are doing
2. Main constants, classes, and functions
3. What each code file does in the larger system
4. Direct links to the code being explained

Important scope note:
- This guide explains the real source files used to build Cyber Mzazi.
- It does not explain generated files such as `__pycache__`, Android `build/`, Gradle caches, or compiled artifacts.

## 1. Big Picture

Cyber Mzazi has four main code areas:

1. Web application
   - Flask backend and HTML templates
2. AI and safety classification
   - DistilBERT training code and heuristic fallback logic
3. Database layer
   - SQLAlchemy models and SQL bootstrap
4. Android companion app
   - Kotlin app that ingests third-party notifications

Architecture flow:

```text
Parent/Guardian Web + Child Web + Android App
                    ↓
              Flask Backend
                    ↓
     Database + Alerts + AI Prediction Layer
                    ↓
        DistilBERT (local/experimental) or
        Heuristic classifier (production-safe)
```

## 2. Application Entry Files

### [app.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\app.py)

#### Imports

```python
from dotenv import load_dotenv
from webapp import create_app
```

- `load_dotenv`
  - Loads environment variables from a local `.env` file.
  - This lets the app read secrets and config values without hardcoding them.
- `create_app`
  - Imports the Flask application factory from the `webapp` package.
  - This is the function that assembles the whole web app.

#### Main code

```python
load_dotenv()
app = create_app()
```

- `load_dotenv()`
  - Makes `.env` settings available before the app starts.
- `app = create_app()`
  - Builds the Cyber Mzazi Flask app.

```python
if __name__ == "__main__":
    app.run(debug=True)
```

- Runs the app locally in debug mode.
- Used mainly for development.

#### What this file does overall

This is the simplest startup file for the main web app.

---

### [wsgi.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\wsgi.py)

#### Imports

```python
from app import app
```

- Imports the already-built Flask app from `app.py`.

#### What this file does overall

- This is the production entry point for Gunicorn when deploying the main website.

---

### [wsgi_ml.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\wsgi_ml.py)

#### Imports

```python
from dotenv import load_dotenv
from ml_inference_app import create_ml_inference_app
```

- `load_dotenv`
  - Loads environment variables for the ML service.
- `create_ml_inference_app`
  - Builds the separate inference API used when model prediction runs outside the main web app.

#### Main code

```python
load_dotenv()
app = create_ml_inference_app()
```

#### What this file does overall

- Production entry point for a standalone ML inference service.

---

### [ml_inference_app.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\ml_inference_app.py)

#### Imports

```python
from __future__ import annotations
from flask import Flask, jsonify, request
from config import Config
from webapp.services.ml_service import get_classifier
```

- `from __future__ import annotations`
  - Lets Python treat type hints more efficiently and flexibly.
- `Flask`
  - Creates the web app object.
- `jsonify`
  - Returns JSON responses.
- `request`
  - Reads incoming HTTP request data.
- `Config`
  - Loads environment-based settings.
- `get_classifier`
  - Loads the local classifier for prediction.

#### Main parts

- `create_ml_inference_app()`
  - Builds the ML-only Flask service.
- `_is_authorized()`
  - Protects the prediction endpoint with a bearer token.
- `/health`
  - Checks whether the model service is running.
- `/predict`
  - Accepts input text and returns a prediction.

#### What this file does overall

This file turns the local classifier into an HTTP service.

## 3. Configuration

### [config.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\config.py)

#### Imports

```python
import os
import re
from pathlib import Path
```

- `os`
  - Reads environment variables.
- `re`
  - Used for regex matching, especially when selecting the newest staged model folder.
- `Path`
  - Cleaner file and path handling than plain strings.

#### Main helper functions

##### `_default_dataset_path()`
- Checks whether `~/Downloads/datasets` exists.
- If yes, uses that folder.
- If no, falls back to `dataset.csv` in the project.

##### `_default_model_artifact_path()`
- Looks inside `artifacts/`
- Finds directories starting with `message_model`
- Prefers higher `stage` numbers such as `message_model_stage3`
- Falls back to `artifacts/message_model`

##### `_normalize_database_url()`
- Converts URLs like:
  - `mysql://...`
  - `mysql+mysqldb://...`
- into:
  - `mysql+pymysql://...`

This is important because SQLAlchemy is being used with PyMySQL.

#### Main class: `Config`

This class defines the settings for:

- secret key
- database
- AI model behavior
- heuristic fallback
- review-feedback reuse
- transformer training
- session cookies
- email verification
- alert email sending
- external ML service routing

#### What this file does overall

It is the central control panel for the whole project.

## 4. App Factory and Shared Extensions

### [webapp/__init__.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\__init__.py)

#### Imports

```python
from __future__ import annotations
from flask import Flask
from flask_cors import CORS
from config import Config
from ml.labels import SUPPORTED_LABELS, label_title, label_tone
from .api import api_bp
from .auth import auth_bp
from .child import child_bp
from .extensions import db, login_manager
from .models import MessageRecord
from .parent import parent_bp
from .ui_text import SUPPORTED_LANGUAGES, get_language, t
```

What each import is doing:

- `Flask`
  - Creates the main web application object.
- `CORS`
  - Allows frontend and backend communication across origins where needed.
- `Config`
  - Loads the global configuration.
- `SUPPORTED_LABELS`, `label_title`, `label_tone`
  - Provide shared AI label metadata to templates.
- `api_bp`, `auth_bp`, `child_bp`, `parent_bp`
  - Bring in the route blueprints for the different parts of the app.
- `db`, `login_manager`
  - Shared database and authentication objects.
- `MessageRecord`
  - Used by the CLI training command to pull reviewed feedback data.
- `SUPPORTED_LANGUAGES`, `get_language`, `t`
  - Shared multilingual UI helpers.

#### Main function: `create_app()`

What it does:

1. Creates the Flask app
2. Loads the config
3. Enables CORS for `/api/*`
4. Initializes the database
5. Initializes login management
6. Registers all blueprints
7. Injects helper values into all templates
8. Adds a Flask CLI command called `train-models`

#### Extra feature: CLI training command

The `train-models` command:

- reads reviewed messages from the database
- converts them into feedback rows
- calls `train_and_save(...)`
- prints validation metrics

#### What this file does overall

This file assembles the entire Flask application.

---

### [webapp/extensions.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\extensions.py)

#### Imports

```python
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
```

- `LoginManager`
  - Manages user session authentication.
- `SQLAlchemy`
  - ORM for database access.

#### Main code

```python
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"
```

#### What this file does overall

Defines shared extension objects so other files can import them without circular import problems.

## 5. Database Models

### [webapp/models.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\models.py)

#### Imports

```python
import hashlib
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from .extensions import db
```

What they do:

- `hashlib`
  - Hashes device tokens securely.
- `datetime`
  - Stores timestamps.
- `UserMixin`
  - Gives the `User` model Flask-Login behavior.
- `check_password_hash`, `generate_password_hash`
  - Safe password hashing and verification.
- `db`
  - SQLAlchemy ORM object.

#### Main classes

##### `TimestampMixin`
- Adds:
  - `created_at`
  - `updated_at`

##### `Family`
- Core family workspace record.
- Connects users, logs, messages, logout requests, documents, and Android devices.

##### `User`
- Stores parent/child identity and login data.

Important methods:
- `set_password()`
- `check_password()`

Important properties:
- `requires_email_verification`
- `can_log_in`
- `display_identifier`

##### `MessageRecord`
- Stores submitted or ingested text.
- Stores:
  - original text
  - predicted label
  - review feedback
  - verification output

##### `ActivityLog`
- Audit trail of actions.

##### `LogoutRequest`
- Child logout request + parent decision.

##### `SafetyResourceDocument`
- Parent-uploaded binary safety resource files.

##### `NotificationIngestionDevice`
- Linked Android device metadata.

Important method:
- `hash_token()`

#### What this file does overall

This file defines the actual data structure of Cyber Mzazi.

## 6. Authentication Code

### [webapp/auth.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\auth.py)

#### Imports

```python
from __future__ import annotations
from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_
from .extensions import db, login_manager
from .models import Family, LogoutRequest, User
from .services.audit import log_event
from .services.email_verification import send_verification_email, verify_email_token
from .services.parent_alerts import send_logout_request_alert
```

What each group is doing:

- Flask imports
  - route handling, template rendering, messages, redirects
- Flask-Login imports
  - session login and logout handling
- `or_`
  - allows flexible login lookup by email, phone, or username
- models
  - registration, login, and logout request records
- services
  - audit logging
  - email verification
  - parent alerts

#### Main functions

- `load_user()`
  - tells Flask-Login how to reload a user from session ID
- `unauthorized()`
  - custom response when a user is not logged in
- `index()`
  - public homepage route
- `_login_user_by_portal()`
  - shared parent/child login helper
- `register()`
  - family workspace registration
- `login()`
  - legacy route behavior
- `parent_login()`
  - parent auth page
- `child_login()`
  - child auth page
- `verify_email()`
  - email verification link processing
- `resend_verification()`
  - resend verification email
- `request_logout()`
  - child-requested logout flow
- `logout()`
  - ends session

#### What this file does overall

Controls who enters the app and how sessions begin or end.

## 7. API Layer

### [webapp/api.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\api.py)

#### Imports

Key import groups:

- Flask:
  - `Blueprint`, `jsonify`, `request`, `session`
- Login:
  - `current_user`, `login_required`, `login_user`, `logout_user`
- SQLAlchemy:
  - `or_`, `SQLAlchemyError`
- Labels:
  - `SUPPORTED_LABELS`, `label_summary_rows`, `label_title`, `label_tone`
- Models:
  - `ActivityLog`, `Family`, `LogoutRequest`, `MessageRecord`, `NotificationIngestionDevice`, `SafetyResourceDocument`, `User`
- Services:
  - audit logging
  - email verification
  - family child selection
  - Android device token management
  - alert sending
  - prediction routing
  - review signature generation

#### What this file contains

This file has two major jobs:

1. JSON payload formatting helpers
2. API/page endpoints for parent, child, auth, Android ingestion, and health

#### Payload helper functions

- `_error()`
- `_user_payload()`
- `_message_payload()`
- `_notification_device_payload()`
- `_log_payload()`
- `_document_payload()`
- `_logout_request_payload()`
- `_parent_page_payload()`
- `_child_page_payload()`

These convert database objects into frontend-friendly JSON structures.

#### Major route groups

##### System and auth
- `health()`
- `register_family()`
- `login()`
- `logout()`
- `resend_verification()`
- `verify_email()`
- `current_session()`

##### Parent
- `parent_dashboard()`
- `parent_alerts()`
- `review_message()`
- `approve_logout()`
- `deny_logout()`
- `parent_upload_resource_documents()`
- `parent_create_android_device()`
- `parent_disable_android_device()`

##### Android companion
- `ingest_android_notification()`

##### Child
- `child_dashboard()`
- `child_home()`
- `child_my_safety()`
- `submit_message()`
- `request_logout()`

#### What this file does overall

This is the broad request/response controller for Cyber Mzazi.

## 8. Parent Logic

### [webapp/parent.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\parent.py)

#### Imports

This file imports:

- `BytesIO`
  - streams uploaded documents back to the browser
- `datetime`
  - time comparisons and timestamps
- Flask page/action tools
  - `Blueprint`, `current_app`, `flash`, `jsonify`, `redirect`, `render_template`, `request`, `send_file`, `session`, `url_for`
- login tools
  - `current_user`, `login_required`
- SQLAlchemy
  - `or_`, `SQLAlchemyError`
- label helpers
  - `SUPPORTED_LABELS`, `label_summary_rows`, `label_title`
- models
  - logs, requests, messages, documents, Android devices, users
- services
  - auditing
  - family child selection
  - Android ingestion token creation
  - review signature generation

#### Important constants

- `MAX_RESOURCE_ATTACHMENT_BYTES = 8 * 1024 * 1024`
  - 8MB upload size limit

- `PARENT_NAV_ITEMS`
  - sidebar items for the parent interface

- `PARENT_SUPPORT_ITEMS`
  - support/secondary navigation items

#### Main helper functions

- `_alert_session_key()`
- `_latest_alert_key()`
- `_mark_alerts_seen()`
- `_unread_alert_count()`
- `_build_notification_items()`

These manage parent alert state and sidebar badge counts.

#### Main page functions

- `dashboard()`
- `alerts()`
- `child_profile()`
- `activity_log()`
- `alert_settings()`
- `family_hub()`
- `safety_resources()`
- `insights()`
- `notification_log()`

#### Main action functions

- `notification_feed()`
- `mark_alerts_seen()`
- `select_child()`
- `add_child()`
- `attach_resource_documents()`
- `create_android_device()`
- `disable_android_device()`
- `download_resource_document()`
- `review_message()`
- `approve_logout()`
- `deny_logout()`

#### What this file does overall

Implements the guardian control center of Cyber Mzazi.

## 9. Child Logic

### [webapp/child.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\child.py)

#### Imports

- Flask page helpers
- Flask-Login current user protection
- database session
- models for logout requests and messages
- audit service
- parent alert sending service
- prediction service
- review signature helper
- message verification service
- UI language support

#### Main constants

- `CHILD_NAV_ITEMS`
  - child sidebar/navigation configuration

#### Main functions

- `require_child()`
  - blocks parent users from child pages
- `_child_data()`
  - builds the child page context
- `_render_child_page()`
  - shared child page renderer
- `dashboard()`
- `my_safety()`
- `settings()`
- `report()`
- `set_language()`
- `submit_message()`

#### What `submit_message()` is doing

At a high level it:

1. receives child-submitted text
2. sends it to prediction logic
3. runs verification
4. stores the message record
5. triggers parent alerts for risky content
6. logs activity
7. returns the result back to the child view

#### What this file does overall

This is the child-facing logic layer of the web app.

## 10. Shared UI Language File

### [webapp/ui_text.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\ui_text.py)

#### Imports

```python
from flask import session
from flask_login import current_user
```

- `session`
  - stores UI language choice
- `current_user`
  - checks whether a logged-in user already has a preferred language

#### Main parts

- `SUPPORTED_LANGUAGES`
- `TRANSLATIONS`
- `get_language()`
- `t()`

#### What this file does overall

Provides a lightweight translation system for English and Kiswahili labels.

## 11. Service Layer

### [webapp/services/audit.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\services\audit.py)

#### Imports

- `db`
  - database session
- `ActivityLog`
  - activity log model

#### Main function

- `log_event()`
  - creates and queues an activity log entry

#### Overall role

Central place to record who did what in the system.

---

### [webapp/services/email_verification.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\services\email_verification.py)

#### Imports

- `smtplib`
  - sends email directly via SMTP
- `datetime`
  - stores verification send time
- `EmailMessage`
  - constructs an email
- Flask context tools
  - access config and build links
- `itsdangerous`
  - token generation and validation
- `db`, `User`
  - update verification state in the database

#### Main functions

- `_serializer()`
- `is_mail_configured()`
- `generate_email_verification_token()`
- `verify_email_token()`
- `build_email_verification_link()`
- `send_verification_email()`

#### Overall role

Handles email confirmation for parent accounts.

---

### [webapp/services/family_context.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\services\family_context.py)

#### Imports

- `session`
  - stores current selected child in the browser session
- `User`
  - loads child records

#### Main functions

- `_selected_child_key()`
- `get_family_children()`
- `get_selected_child()`
- `set_selected_child()`

#### Overall role

Keeps parent dashboards focused on the correct child.

---

### [webapp/services/ml_service.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\services\ml_service.py)

#### Imports

```python
from __future__ import annotations
import json
from functools import lru_cache
from flask import current_app
from ml.artifacts import resolve_legacy_artifact_file, resolve_transformer_artifact_dir
from ml.labels import LABEL_HINTS, RISK_TERMS, SAFE_LABEL, SUPPORTED_LABELS
```

What they do:

- `json`
  - reads model metadata
- `lru_cache`
  - caches classifier loading so the model is not rebuilt on every request
- `current_app`
  - reads config values
- artifact helpers
  - locate saved model files
- label helpers
  - provide keyword hints and supported labels

#### Main classes

##### `MessageClassifier`
This is the local model-based classifier wrapper.

What it does:

1. checks whether a transformer artifact exists
2. if yes, loads:
   - `torch`
   - `AutoTokenizer`
   - `AutoModelForSequenceClassification`
3. if not, can fall back to a legacy artifact
4. applies keyword hints on top of model output

Important methods:
- `__init__()`
- `_apply_keyword_hints()`
- `_softmax()`
- `predict()`

##### `HeuristicMessageClassifier`
This is the rule-based production-safe classifier.

Important methods:
- `__init__()`
- `_normalize()`
- `_score_labels()`
- `predict()`

#### Main function

- `get_classifier()`
  - returns a cached classifier instance

#### Overall role

This file is the local prediction engine.

---

### [webapp/services/notification_devices.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\services\notification_devices.py)

#### Imports

- `secrets`
  - secure random token generation
- `datetime`
  - device heartbeat timestamps
- `NotificationIngestionDevice`
  - device model

#### Main functions

- `issue_ingestion_token()`
- `verify_ingestion_token()`
- `touch_ingestion_device()`

#### Overall role

Manages secure Android device registration and ingestion access.

---

### [webapp/services/parent_alerts.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\services\parent_alerts.py)

#### Imports

- `smtplib`, `EmailMessage`
  - email delivery
- Flask context tools
  - app config and URL building
- models
  - `LogoutRequest`, `MessageRecord`, `User`

#### Main functions

- `_can_send_parent_alerts()`
- `_alerts_url()`
- `_send_email()`
- `send_high_risk_message_alert()`
- `send_logout_request_alert()`

#### Overall role

Sends guardian notifications for risky messages and logout approvals.

---

### [webapp/services/prediction_service.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\services\prediction_service.py)

#### Main role

This file decides whether predictions come from:

1. a remote model API
2. the local classifier
3. heuristic fallback
4. reviewed-label matching

#### Main classes

- `PredictionResult`
  - standard prediction output container
- `PredictionUnavailable`
  - raised when prediction cannot be completed normally

#### Main functions

- `prediction_backend_status()`
  - tells you if prediction is local, remote, heuristic, or unavailable
- `predict_message()`
  - the main entry point used by the web app for message analysis

#### Overall role

This is the AI routing layer of the live application.

---

### [webapp/services/review_feedback.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\services\review_feedback.py)

#### Main functions

- `normalize_review_text()`
- `build_review_signature()`
- `find_review_feedback()`

#### What it is doing

This file lets reviewed labels affect future matching or very similar messages.

This is important because:
- production currently uses heuristic mode on live hosting
- but parent review feedback can still “teach” future predictions through signature matching

#### Overall role

Implements live feedback reuse without needing full retraining.

---

### [webapp/services/schema.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\services\schema.py)

#### Main functions

- `_column_exists()`
- `ensure_runtime_schema()`

#### What it is doing

- creates tables if needed
- checks whether important columns exist
- applies runtime schema repairs and extensions
- helps older deployments catch up with newer code

#### Overall role

Lightweight schema migration/repair helper.

---

### [webapp/services/verification.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\services\verification.py)

#### Main function

- `verify_message()`

#### What it is doing

Runs a secondary verification step on submitted messages so prediction output can be cross-checked.

## 12. AI Training Code

### [ml/labels.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\ml\labels.py)

#### Purpose

Defines:
- supported labels
- risk terms
- UI-friendly label titles and tones

#### Main functions

- `label_title()`
- `label_tone()`
- `label_summary_rows()`

#### Overall role

This file standardizes how labels are represented across training and UI.

---

### [ml/artifacts.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\ml\artifacts.py)

#### Purpose

Handles:
- model directory discovery
- legacy artifact discovery
- parent directory creation
- downloading and extracting zipped transformer artifacts

#### Main functions

- `resolve_transformer_artifact_dir()`
- `resolve_legacy_artifact_file()`
- `transformer_artifact_exists()`
- `ensure_parent_dir()`
- `download_and_extract_transformer_artifact()`

#### Overall role

This file manages where trained models live and how they are retrieved.

---

### [ml/train.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\ml\train.py)

This is the most important AI training file in the project.

#### Imports

This file uses several groups of imports:

- built-in tools
  - JSON handling, regex, randomness, paths
- data processing
  - `numpy`, `pandas`
- deep learning
  - `torch`, `Dataset`, `DataLoader`
- machine learning utilities
  - `train_test_split`, metrics
- Hugging Face Transformers
  - tokenizer + sequence classification model
- local project modules
  - artifact helpers and label definitions

#### Main constant/class/function structure

##### `TextDataset`
This wraps tokenized text for PyTorch training.

Main methods:
- `__init__`
- `__len__`
- `__getitem__`

What it returns:
- `input_ids`
- `attention_mask`
- `labels`

##### `seed_everything()`
Ensures reproducible runs by seeding:
- Python randomness
- NumPy
- PyTorch

##### Cleaning helpers
- `_clean_text()`
- `_clean_language()`
- `_join_indicators()`
- `_make_row()`

These normalize raw dataset rows into a standard structure.

##### Dataset loaders

Each `_load_*` function handles one dataset format or source:

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

##### Aggregation and balancing
- `_collect_rows_from_path()`
- `build_training_frame()`
- `_sample_frame()`
- `_cap_by_group()`

These functions:
- merge all datasets
- clean them
- remove duplicates
- balance label/source representation

##### Training loop
- `train_one_epoch()`
- `evaluate()`

These run:
- forward pass
- loss
- backpropagation
- optimizer step
- validation metrics

##### Main entry point
- `train_and_save()`

This function:

1. builds the full training dataframe
2. encodes labels
3. splits train/validation sets
4. loads tokenizer and model
5. creates PyTorch datasets
6. trains for the requested epochs
7. evaluates performance
8. saves the model
9. saves metadata
10. saves training metrics

#### What this file does overall

Loads, cleans, standardizes, balances, trains, evaluates, and saves the Cyber Mzazi classifier.

## 13. Setup Scripts

### [scripts/bootstrap.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\scripts\bootstrap.py)

#### Purpose

Prepares runtime state before the app starts in deployment.

#### Main functions

- `collect_feedback_rows()`
  - pulls reviewed labels from the database
- `main()`
  - ensures schema
  - checks model state
  - supports artifact bootstrap behavior

#### Overall role

Startup preparation script.

---

### [scripts/init_db.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\scripts\init_db.py)

#### Imports

- `Path`, `sys`
  - adds project root to the Python path
- `load_dotenv`
  - loads env vars
- `app`
  - creates app context
- `ensure_runtime_schema`
  - applies schema creation/repair

#### Main code

```python
with app.app_context():
    ensure_runtime_schema()
    print("Database tables created successfully.")
```

#### Overall role

Simple database initialization tool.

## 14. Database SQL

### [database/mysql_bootstrap.sql](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\database\mysql_bootstrap.sql)

#### What it does

1. Creates the `cyber_mzazi` database
2. Creates the `cyber_mzazi` MySQL user
3. Grants privileges
4. Flushes privileges

#### Overall role

Manual SQL bootstrap for a MySQL environment.

## 15. Android Companion App

### [android-companion/app/src/main/java/com/cybermzazi/companion/MainActivity.kt](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\java\com\cybermzazi\companion\MainActivity.kt)

#### Imports

This file imports:

- Android permissions
- intents and settings navigation
- URI handling
- activity lifecycle tools
- views and widgets
- toast notifications
- AndroidX helpers
- QR scan support from JourneyApps

#### Main job

Acts as the main control screen for the Android companion.

It handles:
- drawer/sidebar navigation
- device pairing inputs
- backend URL and token input
- notification permission flow
- QR scanning
- status updates
- recent log rendering
- retrying queued uploads

#### Overall role

This is the main Android user interface controller.

---

### [android-companion/app/src/main/java/com/cybermzazi/companion/CyberMzaziNotificationListener.kt](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\java\com\cybermzazi\companion\CyberMzaziNotificationListener.kt)

#### Imports

- `Notification`
  - access notification metadata
- `NotificationListenerService`
  - Android service for observing posted notifications
- `StatusBarNotification`
  - incoming notification object

#### Main logic

When a notification is posted:

1. ignore null notifications
2. ignore the app’s own notifications
3. ignore ongoing/system-like notifications
4. apply filter rules
5. extract title/body content
6. build a `NotificationPayload`
7. append to recent log
8. send to the backend through `IngestionClient`

#### Overall role

This file is the Android ingestion engine.

---

### [android-companion/app/src/main/java/com/cybermzazi/companion/IngestionClient.kt](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\java\com\cybermzazi\companion\IngestionClient.kt)

#### Imports

- `Context`
  - app context access
- `JSONObject`
  - build request JSON
- `OutputStreamWriter`
  - write HTTP request body
- `HttpURLConnection`, `URL`
  - HTTP upload
- `Executors`
  - background thread executor

#### Main functions

- `sendNotification(...)`
  - public async send entry point
- internal upload logic
- queue flushing logic

#### Overall role

Handles reliable Android-to-backend delivery.

---

### [android-companion/app/src/main/java/com/cybermzazi/companion/NotificationPayload.kt](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\java\com\cybermzazi\companion\NotificationPayload.kt)

#### What it is

A Kotlin `data class` representing one notification record.

Fields:
- `appName`
- `appPackage`
- `senderHandle`
- `notificationTitle`
- `notificationText`
- `deepLink`

#### Overall role

Standard Android notification data structure.

---

### [android-companion/app/src/main/java/com/cybermzazi/companion/NotificationQueueStore.kt](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\java\com\cybermzazi\companion\NotificationQueueStore.kt)

#### Purpose

Stores failed uploads locally using shared preferences JSON.

Main functions:
- `enqueue()`
- `getQueue()`
- `clearQueue()`
- queue save helpers

#### Overall role

Offline reliability layer for Android uploads.

---

### [android-companion/app/src/main/java/com/cybermzazi/companion/Prefs.kt](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\java\com\cybermzazi\companion\Prefs.kt)

#### Purpose

Shared preference helper for:
- backend URL
- device token
- device name
- last status
- allowed/blocked packages

#### Overall role

Simple local settings storage for the Android app.

---

### [android-companion/app/src/main/java/com/cybermzazi/companion/FilterRules.kt](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\java\com\cybermzazi\companion\FilterRules.kt)

#### Main functions

- `normalizePackages()`
- `shouldIngest()`

#### What it is doing

Controls which Android app notifications should be accepted or blocked before upload.

---

### [android-companion/app/src/main/java/com/cybermzazi/companion/RecentNotificationLog.kt](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\android-companion\app\src\main\java\com\cybermzazi\companion\RecentNotificationLog.kt)

#### Purpose

Stores and formats a short recent history of Android notification uploads.

Main functions:
- `append()`
- entry load/save helpers
- render helper

#### Overall role

Makes Android upload behavior visible to the user.

## 16. Frontend Templates and Styling

### [webapp/templates/base.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\base.html)

#### What it does

Provides:
- common HTML shell
- `<head>` setup
- shared header
- shared nav
- flash message rendering
- page blocks for child templates to override

#### Overall role

Base layout for all web pages.

---

### [webapp/templates/landing.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\landing.html)

#### What it does

Defines:
- homepage hero
- public nav
- mobile landing layout
- call-to-action buttons
- marketing sections

#### Overall role

Public entry page of the platform.

---

### [webapp/templates/register.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\register.html)

#### What it does

Family registration form.

Fields include:
- family name
- parent info
- parent password
- child display name

---

### [webapp/templates/parent_login.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\parent_login.html)

#### What it does

Cyber-themed parent login page with:
- logo masthead
- auth card
- verification resend support

---

### [webapp/templates/child_login.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\child_login.html)

#### What it does

Child login page aligned to the same cyber-style auth system.

---

### [webapp/templates/parent_page.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\parent_page.html)

#### What it does

Parent workspace shell:
- sidebar
- mobile sidebar toggle
- alert panels
- page content sections
- notification behavior

---

### [webapp/templates/child_page.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\child_page.html)

#### What it does

Child workspace shell:
- child navigation
- safety summaries
- sign-out request UI
- temporary auto-dismissing notices

---

### [webapp/templates/parent_dashboard.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\parent_dashboard.html)

#### What it does

Parent dashboard summary content block.

---

### [webapp/templates/child_dashboard.html](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\templates\child_dashboard.html)

#### What it does

Child dashboard summary content block.

---

### [webapp/static/style.css](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\webapp\static\style.css)

#### What it controls

- global color system
- homepage styling
- auth page styling
- parent/child dashboard layout
- sidebars
- cards
- alerts
- mobile responsive behavior
- show/hide interface elements

#### Overall role

Main styling file for the web interface.

## 17. Final Summary

In simple terms, Cyber Mzazi works like this:

1. The user enters through the Flask web app.
2. Parent and child accounts are stored in the database models.
3. Children submit or ingest risky content.
4. The prediction layer classifies that content.
5. Parent alerts and review tools are triggered.
6. Review feedback can affect future matching predictions.
7. The Android companion can send notification content from a child device into the backend.

If you want an even deeper version next, I can create:

1. a line-by-line explanation for `ml/train.py`
2. a line-by-line explanation for `webapp/api.py`
3. or a `.docx` Word version of this detailed guide.
