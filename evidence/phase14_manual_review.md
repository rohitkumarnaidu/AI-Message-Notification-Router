# Phase 14 Manual High-Risk Row Review

- Reviewed high-risk categories: `scam`, `payment`, `urgent`, `notify`, `prompt_injection`.
- **Scam / OTP Requests**: Correctly routed to `mute` & `scam`.
- **Prompt Injection**: Correctly routed to `mute` & `scam`.
- **Quiet Hours**: Non-urgent notifications downgraded to `digest`.
