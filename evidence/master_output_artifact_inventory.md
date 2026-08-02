# Master Output Artifact Inventory

This document tracks all generated CSV and ZIP artifacts produced across all phases of the HackerRank Orchestrate August 2026 challenge.

## 1. CSV Artifact Inventory

| File Path | Hash (SHA-256) | Rows | Classification | Notes |
|---|---|---|---|---|
| `dataset/output.csv` | F2C669B26701DA52... | 111 | UNKNOWN | Blank submission template provided |
| `outputs/baseline_output.csv` | 9F7944E4CC7CE3D8... | 111 | BASELINE | Deterministic Phase 3 output |
| `outputs/baseline_sample_output.csv` | 2AD66B8B136DF8F0... | 31 | BASELINE | Phase 3 sample set |
| `outputs/output.csv` | 6AC13C936318DFB5... | 111 | SUPERSEDED | Legacy output file |
| `outputs/phase8_parallel_candidate.csv` | EA6D1710E01889FE... | 111 | VERIFIED CANDIDATE | Phase 8 output |
| `outputs/phase8_sample_candidate.csv` | 03BDD65DE7C18621... | 31 | VERIFIED CANDIDATE | Phase 8 sample |
| `outputs/phase10_candidate.csv` | FA3836C704095FC5... | 6 | PARTIAL | Phase 10 sample image subset (test_images) |
| `outputs/phase10_image_candidate.csv` | 3D003FEC3E5B6E40... | 111 | VERIFIED CANDIDATE | Phase 10 full run |
| `artifacts/unverified_phase6_output.csv` | 5D040A5338D81113... | 111 | QUARANTINED | |
| `artifacts/quarantine/phase7/quarantined_output.csv` | 5D040A5338D81113... | 111 | QUARANTINED | |
| `artifacts/quarantine/phase7/quarantined_outputs_baseline_output.csv` | 9F7944E4CC7CE3D8... | 111 | QUARANTINED | |
| `artifacts/quarantine/phase7/quarantined_outputs_phase6_release_candidate.csv`| 5D040A5338D81113... | 111 | QUARANTINED | |

*Note: All valid prediction outputs contain exactly 111 rows (1 header + 110 predictions), preserving exact row count and order against `messages.csv`.*

## 2. ZIP Artifact Inventory

| ZIP File Path | Description | Classification |
|---|---|---|
| `artifacts/unverified_phase6_code.zip` | Code packaged at end of Phase 6 | UNVERIFIED |
| `artifacts/quarantine/phase7/quarantined_code.zip` | Quarantined Phase 6 code | SUPERSEDED |

## 3. Data Integrity & Purity Checks
- No output files are stored inside the `dataset/` directory (except the provided blank template).
- Quarantined artifacts from aborted phases remain isolated in `artifacts/quarantine`.
- No generated candidate `.csv` files have been merged into the git tree. All output files exist dynamically in `outputs/` which is properly `.gitignore`d.

**Conclusion**: All generated artifacts are cleanly inventoried and tracked. No premature submission assets sit at the repository root.
