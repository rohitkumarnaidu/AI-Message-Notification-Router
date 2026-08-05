---
layout: default
title: Home
nav_order: 1
permalink: /
---

# AI Message Notification Router
{: .fs-9 }

An enterprise-grade AI system that intelligently routes WhatsApp messages using multimodal analysis, deterministic safety guarantees, and personalized user context.
{: .fs-6 .fw-300 }

[Get Started]({{ site.baseurl }}/getting-started){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View on GitHub](https://github.com/rohitkumarnaidu/AI-Message-Notification-Router){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## The Problem

Modern messaging platforms deliver every message with the same priority — a bank OTP, a spam forward, and a friend's wedding invite all produce the same buzz. This creates **notification fatigue**, where users either miss critical messages or disable notifications entirely.

## Our Solution

We built an AI-powered notification intelligence system that analyzes every incoming message across **text**, **images**, and **voice notes** — then makes a smart routing decision:

| Action | When to Use | User Experience |
|:-------|:------------|:----------------|
| **`notify`** | Urgent, time-sensitive, personally relevant | 🔔 Phone buzzes immediately |
| **`digest`** | Useful but not urgent | 📋 Batched into a daily summary |
| **`mute`** | Spam, scam, or irrelevant | 🔇 Silently suppressed |

---

## Key Highlights

- **36 Python modules** orchestrating a complete AI pipeline
- **7 deterministic safety detectors** with 11 risk categories
- **40+ features** extracted per message using regex-based signal detection
- **118 deterministic tests** with 100% CI reliability
- **Multimodal:** Text + Image (Gemini Vision OCR) + Voice (Groq Whisper ASR)
- **Multilingual:** English, Hindi (transliterated), and Hinglish
- **Zero unsafe notifications** — scam + notify is architecturally impossible

---

## Tech Stack

| Layer | Technology |
|:------|:----------|
| **AI Pipeline** | Python 3.10, 36 modules |
| **Vision AI** | Google Gemini 2.5 Flash |
| **Speech AI** | Groq Whisper Large v3 Turbo |
| **Frontend** | Next.js 15, TailwindCSS, Framer Motion |
| **Backend** | FastAPI (async, auto-documented) |
| **Deployment** | Docker Compose |
| **CI/CD** | GitHub Actions (118 tests) |

---

## Enterprise Use Cases

| Industry | Application |
|:---------|:------------|
| **Banking / Fintech** | Flag OTP phishing, payment scams, impersonation |
| **E-Commerce** | Route order updates vs promotions vs spam |
| **Healthcare** | Triage patient messages by urgency |
| **Enterprise IT** | Internal Slack/Teams notification routing |
| **Social Media** | Reduce group chat notification fatigue |
| **Compliance** | Full audit trail with source provenance |
