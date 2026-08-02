# Phase 14 Router Policy Ablation

- **Configuration A**: Pure Model Escalation (High rate limit risk, 429 errors).
- **Configuration B**: Baseline Heuristic Rules only (Low message-type taxonomy coverage).
- **Configuration C (Selected)**: Selective Hybrid v14 (Preclassifier + Phase 12 Safety + Phase 13 Interruption Policy + Deterministic Fallback). Provides best safety, speed, and accuracy.
