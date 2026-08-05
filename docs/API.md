---
layout: default
title: API Reference
nav_order: 4
---

# API Reference
{: .no_toc }

REST API endpoints, output schema, and error handling documentation.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Base URL

```
http://localhost:8000
```

---

## Endpoints

### GET `/api/messages`

Returns all routed messages with their original text and routing decisions.

**Request:**
```bash
curl http://localhost:8000/api/messages
```

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "message_id": "MSG_001",
      "message_text": "Hey, are you coming to the meeting?",
      "action": "notify",
      "message_type": "urgent",
      "reason": "Trusted sender with immediate time reference",
      "confidence": 0.88,
      "evidence_message_ids": "HIS_042;HIS_039"
    }
  ]
}
```

---

### GET `/api/stats`

Returns aggregate routing statistics.

**Request:**
```bash
curl http://localhost:8000/api/stats
```

**Response:**
```json
{
  "status": "success",
  "stats": {
    "total": 110,
    "notify": 25,
    "digest": 28,
    "mute": 57
  }
}
```

---

### GET `/docs`

Auto-generated interactive Swagger UI documentation (provided by FastAPI).

### GET `/redoc`

Auto-generated ReDoc API documentation (provided by FastAPI).

---

## Output Schema

Every routed message produces exactly these 6 fields:

| Column | Type | Allowed Values |
|:-------|:-----|:---------------|
| `message_id` | string | `MSG_001` ... `MSG_110` |
| `action` | string | `notify`, `digest`, `mute` |
| `message_type` | string | `personal`, `urgent`, `event`, `payment`, `business_update`, `promotion`, `greeting`, `forward`, `spam`, `scam`, `unknown` |
| `reason` | string | Human-readable explanation |
| `confidence` | float | `0.0` — `1.0` |
| `evidence_message_ids` | string | Semicolon-separated IDs or `none` |

---

## Validation Rules

The output validator (`validators.py`) enforces:

| Rule | Check |
|:-----|:------|
| Row count | Must equal input row count (110) |
| ID integrity | Output IDs must match input IDs exactly |
| ID order | Output order must match input order |
| No duplicates | No duplicate message_ids |
| Valid actions | Only `notify`, `digest`, `mute` |
| Valid types | Only the 11 allowed message types |
| Confidence range | Between 0.0 and 1.0 |
| Non-empty reasons | Every row must have a reason |
| Evidence format | Semicolon-separated IDs or `none` |
| UTF-8 encoding | Valid UTF-8 output |
| No debug columns | No extra columns beyond 6 |

---

## Authentication

{: .warning }
The current API has **no authentication** — it is designed for internal/demo use only.

**Enterprise Recommendation:** Add JWT or OAuth2 authentication using FastAPI's built-in security middleware:

```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/api/messages")
async def get_messages(token: str = Depends(oauth2_scheme)):
    # Validate token
    ...
```

---

## Error Handling

The backend returns standard HTTP status codes:

| Code | Meaning |
|:-----|:--------|
| `200` | Success |
| `404` | Output file not found (pipeline hasn't been run) |
| `500` | Internal server error |
