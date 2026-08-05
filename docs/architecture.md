---
layout: default
title: Architecture
nav_order: 3
has_children: true
---

# System Architecture
{: .no_toc }

A comprehensive overview of how the AI Message Notification Router is designed, built, and deployed.
{: .fs-6 .fw-300 }

---

## High-Level Overview

The system is a **multi-stage AI pipeline** that processes incoming WhatsApp messages through feature extraction, safety detection, policy evaluation, and confidence calibration to produce intelligent routing decisions.

### Core Components

| Component | Module | Purpose |
|:----------|:-------|:--------|
| Data Loader | `loaders.py` | Loads 13 CSV files into unified context |
| Context Builder | `context_builder.py` | Assembles user, sender, group, business context |
| User Profile | `user_profile.py` | Builds preferences, quiet hours, trust levels |
| Feature Extractor | `feature_extractor.py` | Extracts 40+ deterministic features |
| Media Processor | `media_processor.py` | Image OCR (Gemini) + Voice ASR (Groq) |
| Safety Detectors | `safety_detectors.py` | 7 detectors, 11 risk categories |
| Multilingual | `multilingual_safety.py` | English + Hindi + Hinglish normalization |
| Policy Engine | `baseline_policy.py` | 27-rule tiered deterministic policy |
| Router | `router.py` | Central orchestrator |
| Evidence Retriever | `retriever.py` | Historical message evidence |
| Confidence | `confidence.py` | Multi-factor calibration |
| Validators | `validators.py` | Output schema enforcement |

### Processing Pipeline

Every message flows through these stages in order:

1. **Load** — Read message and all context CSVs
2. **Enrich** — Build user profile, sender context, group context, business context
3. **Extract Media** — OCR images, transcribe voice notes
4. **Extract Features** — 40+ boolean/numeric features via regex
5. **Safety Scan** — 7 detectors check for scam, phishing, injection
6. **Policy Evaluate** — 27 rules applied in priority order
7. **Calibrate Confidence** — Multi-factor adjustment
8. **Validate** — Schema enforcement, unsafe-notify prevention
9. **Output** — Write final routing decision

---

## Dataset Structure

The system operates on **13 CSV files** containing rich contextual data:

| File | Purpose |
|:-----|:--------|
| `messages.csv` | 110 incoming messages to route |
| `users.csv` | User preferences and quiet hours |
| `groups.csv` | Group metadata and admin lists |
| `group_members.csv` | Group membership and roles |
| `business_accounts.csv` | Business verification status |
| `message_history.csv` | Past messages for evidence retrieval |
| `message_events.csv` | User interactions (reply, dismiss, report, mute) |
| `daily_notification_summary.csv` | Notification load tracking |
| `user_business_history.csv` | Transaction and opt-in history |
| `images.csv` | Image file metadata |
| `voice_notes.csv` | Voice note file metadata |
| `sample_messages.csv` | 30 labeled training samples |
| `output.csv` | Ground truth for labeled samples |
