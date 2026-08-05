---
layout: default
title: Getting Started
nav_order: 2
---

# Getting Started
{: .no_toc }

This guide walks you through setting up the AI Message Notification Router for local development.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Prerequisites

| Tool | Version | Purpose |
|:-----|:--------|:--------|
| Python | 3.10+ | AI pipeline and backend |
| Node.js | 18+ | Next.js frontend |
| Docker | Latest | Containerized deployment (optional) |
| Git | Latest | Version control |

---

## Clone the Repository

```bash
git clone https://github.com/rohitkumarnaidu/AI-Message-Notification-Router.git
cd AI-Message-Notification-Router
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

This installs: `pandas`, `httpx`, `google-genai`, `openai`, `Pillow`, `fastapi`, `uvicorn`, and testing tools.

---

## Configure API Keys (Optional)

The pipeline runs in **fully deterministic mode** without any API keys. To enable multimodal processing:

```bash
# For image analysis (Gemini Vision)
export GEMINI_API_KEY="your-google-ai-studio-key"

# For voice transcription (Groq Whisper)
export GROQ_API_KEY="your-groq-cloud-key"
```

{: .note }
Without API keys, the pipeline still processes all 110 messages using text-based features. Media files will be marked as `failure=True` with graceful degradation.

---

## Run the AI Pipeline

```bash
python code/run_phase15.py
```

**Output:**
- `outputs/phase15_release_candidate.csv` — All 110 routing decisions
- `artifacts/phase15_release_manifest.json` — Release metadata with SHA-256 checksums

---

## Start the Web Application

### Option A: Manual Setup

**Terminal 1 — FastAPI Backend:**
```bash
uvicorn api:app --reload --port 8000
```

**Terminal 2 — Next.js Frontend:**
```bash
cd frontend && npm install && npm run dev
```

| Service | URL |
|:--------|:----|
| Backend API | [http://localhost:8000](http://localhost:8000) |
| Frontend Dashboard | [http://localhost:3000](http://localhost:3000) |
| API Docs (Swagger) | [http://localhost:8000/docs](http://localhost:8000/docs) |

### Option B: Docker Compose

```bash
docker-compose up --build
```

---

## Run Tests

```bash
python -m pytest tests/   # 118 tests, ~5 seconds
```

{: .important }
All tests are **deterministic** — no API keys, no network calls, no randomness. The CI pipeline is 100% reliable.

---

## Project Structure

```
AI-Message-Notification-Router/
├── code/                    # 36 Python modules (AI pipeline)
├── dataset/                 # 13 CSV files + media assets
├── tests/                   # 118 deterministic tests
├── frontend/                # Next.js enterprise dashboard
├── docs/                    # GitHub Pages documentation
├── api.py                   # FastAPI REST backend
├── Dockerfile               # Backend container
├── docker-compose.yml       # Multi-service orchestration
└── TECHNICAL_DOCUMENTATION.md  # 860+ line design document
```
