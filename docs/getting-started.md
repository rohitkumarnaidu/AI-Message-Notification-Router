---
layout: default
title: Getting Started
---

# 🚀 Getting Started

This guide walks you through setting up the AI Message Notification Router for local development, running the AI pipeline, and launching the web application.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | AI pipeline and backend |
| Node.js | 18+ | Next.js frontend |
| Docker | Latest | Containerized deployment (optional) |
| Git | Latest | Version control |

---

## 1. Clone the Repository

```bash
git clone https://github.com/rohitkumarnaidu/AI-Message-Notification-Router.git
cd AI-Message-Notification-Router
```

---

## 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs all core dependencies: `pandas`, `httpx`, `google-genai`, `openai`, `Pillow`, `fastapi`, `uvicorn`, and testing tools.

---

## 3. Configure API Keys (Optional)

The pipeline can run in **fully deterministic mode** without any API keys. To enable multimodal processing (image OCR and voice transcription), set environment variables:

```bash
# For image analysis (Gemini Vision)
export GEMINI_API_KEY="your-google-ai-studio-key"

# For voice transcription (Groq Whisper)
export GROQ_API_KEY="your-groq-cloud-key"
```

> **Note:** Without API keys, the pipeline still processes all 110 messages using text-based features and deterministic safety detectors. Media files will be marked as `failure=True` with graceful degradation.

---

## 4. Run the AI Pipeline

```bash
python code/run_phase15.py
```

This processes all 110 messages and generates:
- `outputs/phase15_release_candidate.csv` — All routing decisions
- `artifacts/phase15_release_manifest.json` — Release metadata with checksums

---

## 5. Start the Web Application

### Option A: Manual (Two Terminals)

**Terminal 1 — FastAPI Backend:**
```bash
uvicorn api:app --reload --port 8000
```

**Terminal 2 — Next.js Frontend:**
```bash
cd frontend
npm install
npm run dev
```

- Backend: [http://localhost:8000](http://localhost:8000)
- Frontend: [http://localhost:3000](http://localhost:3000)
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Option B: Docker Compose (One Command)

```bash
docker-compose up --build
```

---

## 6. Run the Test Suite

```bash
python -m pytest tests/
```

All 118 tests should pass in approximately 5 seconds. Tests are fully deterministic — no API keys or network access required.

---

## Project Structure

```
AI-Message-Notification-Router/
├── code/                    # 36 Python modules (AI pipeline)
├── dataset/                 # 13 CSV files + media assets
├── tests/                   # 118 deterministic tests
├── frontend/                # Next.js enterprise dashboard
├── docs/                    # GitHub Pages documentation
├── evidence/                # Phase audit documents
├── api.py                   # FastAPI REST backend
├── Dockerfile               # Backend container
├── docker-compose.yml       # Multi-service orchestration
├── requirements.txt         # Python dependencies
├── README.md                # Project homepage
└── TECHNICAL_DOCUMENTATION.md  # 860+ line design document
```

---

[← Back to Home](index)
