# Hugging Face Space Deployment

This project includes a ready-to-publish Hugging Face Space in [hf_space](C:\Users\Admin\OneDrive\Documents\Cyber Mzazi\hf_space) for free DistilBERT inference hosting.

## What it does

- exposes `GET /health`
- exposes `POST /predict`
- downloads the trained model artifact from:
  - `https://github.com/Lyne-kim/Cyber-Mzazi/releases/download/model-stage3/message_model_stage3.zip`
- supports bearer-token protection with `MODEL_INFERENCE_TOKEN`

## 1. Log in to Hugging Face

```powershell
hf auth login
```

Paste your Hugging Face token when prompted.

## 2. Create the Space

Example Space ID:

```text
your-hf-username/cyber-mzazi-distilbert
```

Create it:

```powershell
hf repos create your-hf-username/cyber-mzazi-distilbert --type space --space-sdk docker
```

## 3. Upload the included Space files

```powershell
hf upload-large-folder your-hf-username/cyber-mzazi-distilbert .\hf_space --type space
```

## 4. Add Space secret

In the Hugging Face Space settings, add:

- `MODEL_INFERENCE_TOKEN`

Use the same value you place in Render as `MODEL_API_TOKEN`.

## 5. Point Render to the Space

In the main `cyber-mzazi` Render service, set:

```text
MODEL_PROVIDER=auto
MODEL_API_URL=https://your-hf-username-cyber-mzazi-distilbert.hf.space/predict
MODEL_API_TOKEN=YOUR_SHARED_SECRET
ENABLE_HEURISTIC_FALLBACK=true
FORCE_MODEL_RETRAIN=false
```

Remove:

```text
MODEL_ARTIFACT_URL
```

## 6. Free fallback

If the Space sleeps or is unavailable, keep:

```text
ENABLE_HEURISTIC_FALLBACK=true
```

That allows Cyber Mzazi on Render to fall back to lightweight heuristic classification instead of failing completely.
