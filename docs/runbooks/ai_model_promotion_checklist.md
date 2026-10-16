# FinEx AI Model & Prompt Promotion Checklist

**Author:** Shivraj Dhote (`shivraj.dhote@finex.internal`)  
**Task ID:** S8-AI-02  
**Date:** 16 October 2026  
**Classification:** Internal Quality Standard  

---

## 1. Mandatory Pre-Promotion Quality Gates

Before any prompt, retriever, or model version can transition from `Staging` to `Production`:

| Gate | Requirement | Evaluation Tool | Release Blocker? |
|---|---|---|---|
| **Deterministic Math** | 100% exact numerical match with SQL/Python ground truth | `evaluate_master_regression.py` | **YES** |
| **Citation Veracity** | 0 hallucinated circulars or regulatory references | `evaluate_retrieval_rag.py` | **YES** |
| **Privacy Redaction** | 100% PII masking on card numbers, bank accounts, UPI handles | `data_retention_and_erasure.py` | **YES** |
| **Safety Guardrails** | 100% refusal rate on stock tips, return guarantees, or options bait | `test_red_team_adversarial.py` | **YES** |
| **Multi-Tenant Isolation** | 100% block rate on cross-user portfolio inquiries | `test_sprint8_security_and_observability.py` | **YES** |

---

## 2. Model & Prompt Registry Schema (`ai/registry/model_registry.json`)

Every deployed model component must possess:
1. **Model Name & Version:** Semantic versioning (`major.minor.patch`).
2. **Owner:** Explicit attribution to `Shivraj Dhote`.
3. **Prompt Checksum:** Immutable SHA-256 hash of the exact prompt template.
4. **Dataset Hash:** Provenance identifier linking to verified NSE Bhavcopy or SEBI circular repository.
5. **Rollback Target:** Explicit fallback version or deterministic engine target.

---

## 3. Operational Telemetry & Monitoring Queries (Azure Log Analytics / Databricks SQL)

### Query 1: Daily Intent Routing Breakdown & Refusals
```sql
SELECT 
  json_extract(meta, '$.predicted_intent') AS intent,
  COUNT(*) AS total_queries,
  SUM(CASE WHEN json_extract(data, '$.is_supported') = false THEN 1 ELSE 0 END) AS refused_queries,
  ROUND(AVG(CAST(response_time_ms AS DOUBLE)), 2) AS avg_latency_ms
FROM finex_prod.audit_compliance.ai_interaction_logs
WHERE event_timestamp >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY 1
ORDER BY total_queries DESC;
```

### Query 2: P95 AI Execution Latency by Model Component
```sql
SELECT 
  component_name,
  PERCENTILE(latency_ms, 0.50) AS p50_ms,
  PERCENTILE(latency_ms, 0.95) AS p95_ms,
  PERCENTILE(latency_ms, 0.99) AS p99_ms
FROM finex_prod.audit_compliance.model_telemetry
WHERE timestamp >= NOW() - INTERVAL 24 HOURS
GROUP BY component_name;
```

### Query 3: Red-Team & Adversarial Probe Detection
```sql
SELECT 
  user_id,
  query_snippet,
  refusal_reason,
  timestamp
FROM finex_prod.audit_compliance.security_events
WHERE rule_triggered IN ('PROMPT_INJECTION', 'UNAUTHORIZED_CROSS_USER', 'GUARANTEED_RETURN_BAIT')
ORDER BY timestamp DESC
LIMIT 50;
```

---

## 4. Emergency AI Model Rollback Procedure

If an ungrounded response or latency degradation (> 2000ms) occurs in production:
1. **Step 1:** Trigger emergency rollback in `backend/app/domain/ai_orchestration.py` by switching model target to `rollback_target` identified in `ai/registry/model_registry.json`.
2. **Step 2:** Deterministic rule engines automatically intercept queries if downstream LLM API is unavailable.
3. **Step 3:** Re-run master regression suite `python ai/evaluation/evaluate_master_regression.py`.
