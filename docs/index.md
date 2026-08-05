---
layout: default
title: Home
---

# AI Message Notification Router

**An enterprise-grade AI system for intelligent WhatsApp message routing.**

---

## What Is This?

Modern messaging platforms deliver every message with the same priority — a bank OTP, a spam forward, and a friend's wedding invite all produce the same buzz. This system solves that by intelligently routing every message into one of three actions:

- **🔔 Notify** — Urgent, time-sensitive, personally relevant → Phone buzzes immediately
- **📋 Digest** — Useful but not urgent → Batched into a daily summary
- **🔇 Mute** — Spam, scam, or irrelevant → Silently suppressed

---

## Documentation

| Page | Description |
|------|-------------|
| [📖 Technical Documentation](technical-documentation) | Complete 19-section design document with architecture diagrams |
| [🔌 API Reference](API) | REST API endpoints, schemas, and error handling |
| [🚀 Getting Started](getting-started) | Installation, setup, and quick start guide |
| [🛡️ Safety Architecture](safety) | Security model, trust hierarchy, and threat defense |
| [📊 Performance](performance) | Benchmarks, scaling strategy, and bottleneck analysis |

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/rohitkumarnaidu/AI-Message-Notification-Router.git
cd AI-Message-Notification-Router
pip install -r requirements.txt

# Run the AI pipeline
python code/run_phase15.py

# Start the backend + frontend
docker-compose up --build
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Pipeline | Python 3.10, 36 modules |
| Vision AI | Google Gemini 2.5 Flash |
| Speech AI | Groq Whisper Large v3 Turbo |
| Frontend | Next.js 15, TailwindCSS, Framer Motion |
| Backend | FastAPI |
| CI/CD | GitHub Actions (118 tests) |
| Deployment | Docker Compose |

---

## Links

- [GitHub Repository](https://github.com/rohitkumarnaidu/AI-Message-Notification-Router)
- [Problem Statement](https://github.com/rohitkumarnaidu/AI-Message-Notification-Router/blob/main/problem_statement.md)
- [Changelog](https://github.com/rohitkumarnaidu/AI-Message-Notification-Router/blob/main/CHANGELOG.md)

---

*Built with ❤️ by [Rohit Kumar Naidu](https://github.com/rohitkumarnaidu)*
