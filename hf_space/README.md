---
title: Cyber Mzazi DistilBERT API
emoji: shield
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
license: mit
short_description: DistilBERT inference API for Cyber Mzazi
---

# Cyber Mzazi DistilBERT API

This Hugging Face Space serves Cyber Mzazi's DistilBERT classifier as a small HTTP API.

## Endpoints

- `GET /health`
- `POST /predict`

## Request format

```json
{
  "text": "Click this link to verify your account now"
}
```

## Response format

```json
{
  "ok": true,
  "prediction": {
    "label": "phishing",
    "confidence": 0.81,
    "risk_indicators": "credential_theft,fake_link,impersonation"
  }
}
```

## Secrets / Variables

Add these in the Space settings if needed:

- `MODEL_ARTIFACT_URL`
- `MODEL_INFERENCE_TOKEN`

If `MODEL_INFERENCE_TOKEN` is set, callers must send:

```text
Authorization: Bearer <token>
```
