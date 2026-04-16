# Separate Frontend API Guide

This backend now exposes a JSON API for a separate web frontend.

## Base URL

- local: `http://127.0.0.1:5000/api`
- production: `https://your-backend-domain/api`

## CORS and cookies

Set these environment variables on the backend:

- `FRONTEND_ORIGIN=https://your-frontend-domain`
- `SESSION_COOKIE_SECURE=true` in production
- `SESSION_COOKIE_SAMESITE=None` when frontend and backend are on different domains

Frontend requests should include credentials:

```js
fetch("https://your-backend-domain/api/me", {
  credentials: "include"
});
```

## Main endpoints

### Register family

`POST /auth/register`

```json
{
  "family_name": "Mwangi family",
  "parent_name": "Jane Mwangi",
  "parent_contact": "jane@example.com",
  "parent_password": "secret123",
  "child_name": "Kevin",
  "child_username": "kevin-home",
  "child_password": "secret123"
}
```

### Parent login

`POST /auth/login`

```json
{
  "portal": "parent",
  "identifier": "jane@example.com",
  "password": "secret123"
}
```

### Child login

`POST /auth/login`

```json
{
  "portal": "child",
  "parent_contact": "jane@example.com",
  "child_username": "kevin-home",
  "password": "secret123"
}
```

### Parent dashboard data

`GET /parent/dashboard`

### Child dashboard data

`GET /child/dashboard`

### Submit child message

`POST /child/messages`

```json
{
  "source_platform": "WhatsApp",
  "sender_handle": "@sender",
  "browser_origin": "manual",
  "message_text": "Karibu 100 awin, pesa halaisi, instant payout"
}
```

### Review a message

`POST /parent/messages/:messageId/review`

```json
{
  "reviewed_label": "betting"
}
```

### Request child logout

`POST /child/logout-request`

### Approve child logout

`POST /parent/logout-requests/:requestId/approve`

### Activity feed

`GET /activity`
