# Phase 14 Decision Boundary & Preclassification

- **Deterministic Direct (`DETERMINISTIC_DIRECT`)**:
  - Grounded credential / OTP / PIN requests -> `mute` / `scam`
  - Prompt injection attempts -> `mute` / `scam`
  - Phishing / Impersonation threats -> `mute` / `scam`
  - Obvious spam -> `mute` / `spam`
  - Simple greetings -> `digest` / `greeting`
  - Verified payment reminders -> `digest` or `notify` / `payment`
  - Clear events / webinars -> `digest` or `notify` / `event`
  - Concrete delivery / waiting outside -> `notify` / `urgent`

- **Model Escalation (`NVIDIA_LIVE` / `GROQ_LIVE`)**:
  - Ambiguous multi-signal messages requiring complex semantic reasoning.
