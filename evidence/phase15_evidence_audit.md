# Phase 15 Evidence Selection Audit

- **Evidence Allowlist**: Strictly enforced. Cross-user, future, and duplicate evidence IDs rejected.
- **None Representation**: Uses `"none"` when no relevant evidence passes minimum threshold.
- **Padding Prevention**: No fixed top-k padding. Evidence selected strictly on relevance.
