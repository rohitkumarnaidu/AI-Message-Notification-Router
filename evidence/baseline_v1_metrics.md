# Baseline v1 Metrics

**Evaluation Version**: `baseline_v1`
**Sample Count**: 30 (Solved Dataset)

## High-Level Summary

| Metric | Score |
| :--- | :--- |
| **Action Accuracy** | **70.00%** |
| **Action Macro F1** | **69.34%** |
| **Type Accuracy** | 43.33% |
| **Type Macro F1** | 38.76% |
| **Output Integrity** | 100% Valid |

## Action-Level Performance

| Class | Precision | Recall | F1 Score | Support |
| :--- | :--- | :--- | :--- | :--- |
| `digest` | 0.5625 | 0.8182 | 0.6667 | 11 |
| `mute` | 0.8889 | 0.8000 | 0.8421 | 10 |
| `notify` | 0.8000 | 0.4444 | 0.5714 | 9 |

### Action Confusion Matrix

*(Rows: True Class, Columns: Predicted Class)*

| | `digest` (Pred) | `mute` (Pred) | `notify` (Pred) |
| :--- | :--- | :--- | :--- |
| **`digest` (True)** | **9** | 1 | 1 |
| **`mute` (True)** | 2 | **8** | 0 |
| **`notify` (True)** | 5 | 0 | **4** |

### Key Takeaways (Action)
1. **High Recall on Digest**: The baseline aggressively routes messages to `digest` (recall 81.8%), which causes lower precision (56.25%).
2. **Low Recall on Notify**: Only 44.4% of true `notify` messages are correctly flagged, missing 5 out of 9 (which end up in `digest`). Deterministic rules are too strict to capture all urgent notifications.
3. **Mute is Strong**: Safety gates and opt-out rules are effective at capturing spam/scams (88.8% precision, 80% recall).

## Type-Level Performance (Selected Classes)

*Note: Type classification is a secondary objective, but highlights the limitations of regex/rule-based matching.*

| Class | Precision | Recall | F1 Score |
| :--- | :--- | :--- | :--- |
| `urgent` | 0.6667 | 0.5000 | 0.5714 |
| `scam` | 1.0000 | 0.5000 | 0.6667 |
| `promotion` | 0.6667 | 0.3333 | 0.4444 |
| `event` | 0.2857 | 0.5000 | 0.3636 |
| `personal` | 0.2857 | 0.5000 | 0.3636 |
| `business_update` | 0.5000 | 0.3333 | 0.4000 |

*Note: The baseline struggles with semantic nuance (e.g., confusing `event` vs `urgent`, missing subtle `promotion` language).*
