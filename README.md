# Cyber Mzazi

Cyber Mzazi is a consent-based family safety MVP built around the provided `dataset.csv`. It includes:

- A Flask web app with separate parent and child dashboards.
- A REST API for a separate frontend application.
- MySQL-backed authentication, message records, logout approvals, and audit logs.
- A training pipeline that uses both `LinearRegression` and `RandomForestClassifier`.
- A pluggable external verification hook for message confirmation.

## Important safety scope

This project does **not** implement covert browser-history scraping, forced access to private social-media accounts, or hidden device persistence. Instead, it supports:

- Message submission through the child portal or approved integrations.
- Shared family audit logs.
- Parent approval for child sign-out **inside this app**.
- Optional external verification through a configured API endpoint.

## Project structure

```text
app.py
config.py
dataset.csv
ml/train.py
webapp/
```

## 1. Install dependencies

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Configure MySQL

Run the bootstrap SQL in [database/mysql_bootstrap.sql](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\database\mysql_bootstrap.sql), then copy `.env.example` to `.env` and update the credentials.

Initialize the application tables:

```powershell
python scripts\init_db.py
```

## 3. Train the model

```powershell
$env:FLASK_APP = "app.py"
flask train-models
```

This will:

- read `dataset.csv`
- train a linear-regression-based scorer
- train a random forest classifier
- blend both outputs for prediction
- save the artifact in `artifacts/message_model.joblib`

## 4. Run the app

```powershell
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

## 5. Git deployment flow

```powershell
git add .
git commit -m "Initial Cyber Mzazi MVP"
git remote add origin <your-repository-url>
git push -u origin main
```

This repository is already initialized with Git locally.

## 6. Separate frontend connection

Use the REST API documented in [FRONTEND_API.md](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\FRONTEND_API.md).

Important backend env vars for a separate frontend:

- `FRONTEND_ORIGIN`
- `SESSION_COOKIE_SECURE`
- `SESSION_COOKIE_SAMESITE`

The backend uses session cookies, so frontend requests should send credentials.

## 7. Render deployment

The project includes [render.yaml](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\render.yaml) and [Procfile](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\Procfile).

For Render, point your host to:

- app entry: `app:app`
- Python version: 3.11+
- MySQL connection string in environment variables
- `SECRET_KEY`, `FRONTEND_ORIGIN`, and cookie settings in environment variables

After the first deploy shell opens, run:

```bash
python scripts/init_db.py
flask train-models
```

## 8. Railway deployment

The project also includes [railway.json](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\railway.json) and [wsgi.py](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\wsgi.py).

Set Railway variables:

- `DATABASE_URL`
- `SECRET_KEY`
- `FRONTEND_ORIGIN`
- `SESSION_COOKIE_SECURE=true`
- `SESSION_COOKIE_SAMESITE=None`

Then run once after deployment:

```bash
python scripts/init_db.py
flask train-models
```

## External verification hook

If you want the app to confirm message type through a web service, set:

- `WEB_VERIFIER_URL`
- `WEB_VERIFIER_TOKEN` if your service requires bearer auth

The endpoint is expected to accept JSON like:

```json
{
  "text": "message body",
  "predicted_label": "grooming"
}
```

and return:

```json
{
  "label": "grooming",
  "confidence": 0.92,
  "notes": "Matched provider policy rules."
}
```

## Retraining loop

Parents can review model outputs in the dashboard. Reviewed labels are included the next time `flask train-models` runs, which gives you a controlled human-in-the-loop learning workflow instead of unsafe autonomous monitoring.
