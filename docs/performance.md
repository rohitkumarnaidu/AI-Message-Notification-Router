---
layout: default
title: Performance
parent: Architecture
nav_order: 3
---

# Performance & Scalability
{: .no_toc }

Benchmarks, bottleneck analysis, and the scaling roadmap from single-process to microservices.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Current Benchmarks

| Metric | Value | Notes |
|:-------|:------|:------|
| Pipeline throughput | 110 messages in ~8s | With cached media results |
| Cold start (no cache) | ~45s for 110 messages | Rate-limited by Gemini/Groq APIs |
| Test suite execution | 118 tests in ~5s | Fully deterministic, no network |
| Feature extraction | < 2ms per message | Pure Python regex |
| Safety detection | < 5ms per message | 7 detectors sequentially |
| API response time | < 50ms | Serving pre-computed results |

---

## Bottleneck Analysis

| Component | Bottleneck | Solution |
|:----------|:----------|:---------|
| Media Processing | Rate-limited APIs (Gemini: 15 RPM, Groq: 30 RPM) | MD5 caching + ThreadPoolExecutor |
| Feature Extraction | None (< 2ms) | Already 10K+/sec capable |
| Evidence Retrieval | Linear scan over history | Vector DB (Pinecone/Weaviate) |
| Output I/O | CSV file write | PostgreSQL for concurrent access |

---

## Scaling Roadmap

### Phase 1: Current — Single Process
- Sequential Python pipeline
- File-based caching and CSV output
- Suitable for up to ~1,000 messages per batch

### Phase 2: Parallel Workers
- Message queue (Kafka/RabbitMQ)
- Multiple Python workers
- Redis for shared caching
- ~100,000 messages per day

### Phase 3: Microservices
- Separate Feature, Safety, Media, Router services
- Kubernetes with HPA
- PostgreSQL for decision history
- 1M+ messages per day

---

## Error Handling & Resilience

The router supports **9 execution modes** with automatic failover:

| Priority | Mode | When Used |
|:---------|:-----|:----------|
| 1 | `DETERMINISTIC_DIRECT` | Preclassifier provides high-confidence routing |
| 2 | `GEMINI_LIVE` | Gemini API available |
| 3 | `GROQ_LIVE` | Groq API available, Gemini down |
| 4 | `NVIDIA_LIVE` | NVIDIA API available |
| 5 | `SCHEMA_REPAIR` | LLM schema violations auto-repaired |
| 6 | `NETWORK_FALLBACK` | All APIs down |
| 7 | `RATE_LIMIT_FALLBACK` | Quota exhausted |
| 8 | `POLICY_REJECTION_FALLBACK` | Provider safety rejection |
| 9 | `DETERMINISTIC_FINAL_FALLBACK` | Everything failed → `digest/unknown/0.60` |

{: .important }
The system **never crashes**. Even if all external APIs are down, it falls back to the deterministic pipeline and produces a valid routing decision for every message.
