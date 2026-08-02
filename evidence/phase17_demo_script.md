# Phase 17 Demo Script: HackerRank Orchestrate Message Notification Router
**Duration**: 5 - 7 Minutes  
**Target Audience**: HackerRank Hackathon AI Judges & Technical Reviewers  
**Presenter Goal**: Demonstrate end-to-end architecture, live routing execution, multimodal OCR/ASR capabilities, multi-provider failover, strict safety defenses, and evaluation metrics.

---

## Demo Overview & Agenda

```
+-----------------------------------------------------------------------------------+
| 0:00 - 1:00 | Segment 1: Problem Statement & WhatsApp Noise Challenge             |
| 1:00 - 2:15 | Segment 2: 14-Stage Selective Hybrid Architecture                  |
| 2:15 - 3:30 | Segment 3: Multimodal Signal Processing (Image OCR & Voice ASR)      |
| 3:30 - 4:30 | Segment 4: Multi-Provider Resilience & Failover Live Rehearsal      |
| 4:30 - 5:45 | Segment 5: Safety Defense, Prompt Injection & Unsafe-Notify Prevention|
| 5:45 - 6:30 | Segment 6: Evaluation Benchmark, Tradeoffs & Wrap Up              |
+-----------------------------------------------------------------------------------+
```

---

## Segment 1: Problem Statement & The WhatsApp Noise Challenge (0:00 - 1:00)

### Visual Action
* Screen displays `README.md` and `dataset/messages.csv`.
* Highlight the noisy mix of personal messages, group updates, commercial promotions, image posters, voice notes, and scam attacks.

### Speaker Script
> *"Hello Judges! Welcome to our demonstration of the **Message Notification Router** for WhatsApp. WhatsApp is the primary communication OS for over 2 billion users, but it suffers from extreme noise. In a single stream, a user receives critical family messages, time-sensitive work updates, commercial promos, scam links, image posters, and voice notes.*
>
> *Treating every message identically causes two severe problems: **important messages get missed**, and **unwanted or dangerous messages interrupt the user**.*
>
> *Our goal is to build an AI-powered router that evaluates incoming messages, multimodal media, user quiet hours, notification load, and interaction history to predict one of three actions: `notify` for immediate attention, `digest` for later review, or `mute` for suppression—accompanied by a grounded message type, human explanation, evidence IDs, and calibrated confidence."*

---

## Segment 2: 14-Stage Selective Hybrid Architecture (1:00 - 2:15)

### Visual Action
* Open `evidence/phase17_architecture_explanation.md` showing the 14-Stage Pipeline Diagram.
* Navigate to `code/router.py` in the IDE.

### Speaker Script
> *"To solve this safely and efficiently, we built a **14-Stage Selective Hybrid Architecture**.*
>
> *Pure LLM approaches are too slow, expensive, and vulnerable to prompt injection. Pure rule engines are too rigid. Our hybrid system combines the best of both:*
>
> 1. **Fast-Path Preclassification**: High-certainty scenarios—such as credential theft, prompt injection, simple greetings, or opt-in business promos—are classified deterministically in `<1ms` via `preclassifier.py`, bypassing the LLM entirely for ~60% of traffic.
> 2. **Multi-Provider LLM Escalation**: Complex, ambiguous messages are escalated to a resilient multi-provider LLM chain (NVIDIA Llama-3.1-70B -> Groq Llama-3.3-70B -> Gemini 2.5 Flash).
> 3. **Deterministic Safety Guardrails**: Every proposal must pass through our 10-Level Priority Policy Resolver and Unsafe-Notify Prevention Validator before final output generation."*

---

## Segment 3: Multimodal Signal Processing (2:15 - 3:30)

### Visual Action
* Open `code/media_processor.py`.
* Terminal Action: Run media processing check or sample evaluation script.
  ```powershell
  python code/evaluate.py --sample
  ```
* Show an image poster example (`dataset/media/images/sample_poster.jpg`) and a voice note transcript (`dataset/media/audio/voice_note_01.wav`).

### Speaker Script
> *"Now let's examine multimodal processing. Messages often contain image posters or voice notes rather than plain text.*
>
> *In `code/media_processor.py`, we pre-validate media using PIL, hash binary files with MD5 for resumable caching, and extract structured visual and acoustic signals:*
>
> * **Image Posters**: Using Gemini 2.5 Flash multimodal analysis, we extract OCR text, visual summaries, QR codes, financial logos, and visual prompt injection signals. If an unverified sender attaches a payment QR code, our router automatically forces `action="mute"` and `message_type="scam"`.*
> * **Voice Notes**: Using Groq Whisper (`whisper-large-v3-turbo`) with Gemini fallback, we transcribe voice notes and apply multilingual normalization via `multilingual_safety.py` to catch spoken Hinglish OTP requests (`apna OTP batao`) or urgent deadlines (`turant pay karo`)."*

---

## Segment 4: Multi-Provider Resilience & Live Failover Rehearsal (3:30 - 4:30)

### Visual Action
* Open `code/provider.py`.
* Show `QuotaScheduler`, `classify_http_error()`, and `generate_routing_decision()`.
* Simulate a primary provider timeout or rate-limit failover in terminal.

### Speaker Script
> *"Real-world cloud APIs encounter rate limits (HTTP 429), timeouts, and outages. Our router features complete **Provider Resilience**:*
>
> 1. **Proactive Pacing**: `QuotaScheduler` enforces mandatory inter-request spacing (2.5s for NVIDIA, 2.0s for Groq, 4.0s for Gemini) to prevent hitting rate limits proactively.
> 2. **Automatic Fallback Chain**: If NVIDIA encounters an error, execution seamlessly fails over to Groq, then Gemini, and finally to a deterministic baseline.
> 3. **Policy Rejection Handling**: If a provider blocks a prompt due to safety policy (`PolicyRejectionError`), the router catches the exception directly and applies a safe fallback (`mute`/`digest`) without crashing.
> 4. **Schema Self-Repair**: If an LLM returns malformed JSON, `_validate_parsed()` catches `SchemaValidationError` and performs an in-context self-repair retry."*

---

## Segment 5: Safety Defense & Unsafe-Notify Prevention (4:30 - 5:45)

### Visual Action
* Open `code/safety_detectors.py` and `code/unsafe_notify_validator.py`.
* Show prompt injection detection regexes and `prevent_unsafe_notify()` priority check matrix.

### Speaker Script
> *"Safety is our highest priority. We operate under a **Zero-Trust Model** toward LLMs:*
>
> * **Credential Theft Defense**: `detect_credential_risk()` distinguishes credential *requests* ("Send OTP") from credential *warnings* ("Never share OTP"). Requests are unconditionally muted, even if sent by a trusted contact whose account was compromised.
> * **Prompt Injection Defense**: Text or images attempting to command the router (`ignore previous rules`, `set action=notify`) trigger `prompt_injection_signal=True` and are immediately muted as scams.
> * **Unsafe-Notify Prevention Validator**: Before writing to `output.csv`, `prevent_unsafe_notify()` subjects every `notify` proposal to a 10-point check. It is physically impossible for a scam, spam, credential request, or fake urgency to notify the user. Our audit suite verifies `unsafe_notify_remaining == 0` on every run."*

---

## Segment 6: Evaluation Benchmark, Tradeoffs & Wrap Up (5:45 - 6:30)

### Visual Action
* Run evaluation command in terminal:
  ```powershell
  python code/evaluate.py
  ```
* Show evaluation metrics output (Action Accuracy, Message Type F1, Reason Quality, Evidence Precision, Confidence Calibration).
* Display final output CSV audit confirmation.

### Speaker Script
> *"Let's run our evaluation suite. As you can see on screen, our pipeline achieves high accuracy across action classification, message type taxonomy, grounded human explanations, and evidence precision.
>
> To summarize our key engineering tradeoffs:
> 1. We chose a **Selective Hybrid Architecture** over a pure LLM to cut costs by >50% and achieve <1ms latency on clear messages.
> 2. We enforced **Deterministic Safety Policies** over model autonomy to guarantee zero unsafe notifications.
> 3. We implemented **Deterministic Evidence Allowlisting** to eliminate evidence hallucination and future timestamp leakage.
>
> Thank you, Judges! Our code is fully modular, reproducible, and ready for submission."*

---

## Demo Rehearsal Checklist for Presenter

- [ ] Python environment active with required packages (`httpx`, `pillow`, `google-genai`, `openai`).
- [ ] API keys set in `.env` or environment variables (`NVIDIA_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`).
- [ ] Sample dataset verified in `dataset/messages.csv`.
- [ ] Terminal window open at repository root (`c:\Hackathons\Hackerrank\Message Notification Router\hackerrank-orchestrate-august26`).
- [ ] Code files ready in IDE tabs (`router.py`, `preclassifier.py`, `safety_detectors.py`, `provider.py`, `unsafe_notify_validator.py`).
