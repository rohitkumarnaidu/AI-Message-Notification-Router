# Phase 14 Schema Reliability & Bounded Repair

- **Canonical Schemas**: `RouterInput`, `RouterProposal`, `FinalRouterDecision`, `ExecutionMode`.
- **Validation**: Strict checks on allowed enums (`notify`, `digest`, `mute`), confidence ranges `[0.0, 1.0]`, valid evidence IDs inside allowlist.
- **Bounded Repair**: Maximum 1 local schema repair (whitespace strip, markdown fence removal, float parsing). If local repair fails, deterministic fallback is executed safely.
