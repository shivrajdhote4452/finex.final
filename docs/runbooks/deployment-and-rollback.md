# FinEx Production Deployment and Rollback Runbook

**Author:** Shivraj Dhote (`shivraj.dhote@finex.internal`)  
**Task ID:** S8-API-02  
**Date:** 16 October 2026  
**Classification:** Internal Engineering Standard  

---

## 1. Overview and Architecture Principles
FinEx follows cloud-native, immutable container delivery across Azure Container Apps (Backend API) and Azure Static Web Apps (Frontend SPA):
- **Stateless API Process:** FastAPI running under Uvicorn workers in non-root container (`appuser`, UID 10001).
- **Zero In-Image Secrets:** All credentials (`JWT_SECRET_KEY`, `DATABRICKS_TOKEN`, `DATABASE_URL`) injected exclusively via Azure Key Vault / KeyVault secret references at container boot.
- **Dependency-Aware Readiness Probes:** Container readiness checks verify real database connectivity and analytical access (`/api/v1/health/ready` or `/readyz`).
- **Liveness Probes:** Independent process-level watchdog (`/api/v1/health/live` or `/healthz`) ensuring hung workers are terminated without premature cascading restarts.

---

## 2. Immutable Container Build & Tagging

### Build Command
```bash
# 1. Build immutable production image
docker build -f backend/Dockerfile -t finex-api:1.0.0-release .

# 2. Extract immutable SHA-256 image digest
docker inspect --format='{{index .RepoDigests 0}}' finex-api:1.0.0-release > deployment/image_digest.sha256

# 3. Tag and push to private container registry (e.g. GHCR / Azure Container Registry)
docker tag finex-api:1.0.0-release finexcr.azurecr.io/finex-api:1.0.0-release
docker push finexcr.azurecr.io/finex-api:1.0.0-release
```

### Build Verification Checklist
- [x] No `.env`, test tokens, or private keys included in image context (`.dockerignore` enforced).
- [x] Non-root user specified (`USER appuser`).
- [x] Python dependencies pinned in virtualenv without global mutation.
- [x] Base image uses minimal vulnerability footprint (`python:3.13-slim`).

---

## 3. Kubernetes / Azure Container Apps Probe Specification

```yaml
probes:
  liveness:
    httpGet:
      path: /api/v1/health/live
      port: 8000
    initialDelaySeconds: 10
    periodSeconds: 15
    timeoutSeconds: 3
    failureThreshold: 3
  readiness:
    httpGet:
      path: /api/v1/health/ready
      port: 8000
    initialDelaySeconds: 5
    periodSeconds: 10
    timeoutSeconds: 5
    failureThreshold: 2
```

> **Crucial Rule:** If the operational database experiences transient network partition, `/ready` responds with `503 Service Unavailable`, causing the ingress router to withdraw traffic gracefully from the replica *without* triggering process death. Once the database recovers, `/ready` automatically re-admits traffic.

---

## 4. Zero-Downtime Rolling Deployment Procedure

1. **Step 1: Execute Backward-Compatible Database Migrations**
   ```bash
   # Apply additive schema changes only (new columns nullable or with defaults)
   python -m alembic upgrade head
   ```
2. **Step 2: Deploy New Container Revision with 20% Canary / Staged Traffic**
   ```bash
   az containerapp revision set-mode --name finex-api-app --resource-group finex-prod-rg --mode multiple
   az containerapp update --name finex-api-app --resource-group finex-prod-rg \
     --image finexcr.azurecr.io/finex-api:1.0.0-release
   ```
3. **Step 3: Verification & Smoke Test**
   - Verify health checks: `curl -f https://api.finex.finance/api/v1/health/ready`
   - Run synthetic smoke test: `python backend/scripts/run_load_test.py`
4. **Step 4: Shift 100% Traffic**
   ```bash
   az containerapp ingress traffic set --name finex-api-app --resource-group finex-prod-rg \
     --traffic-weight latest=100
   ```

---

## 5. Rollback Procedure (Mean-Time-To-Recovery < 3 Minutes)

If error rate spikes (> 1% HTTP 5xx) or P95 latency degrades beyond 500ms post-deployment:

### Immediate Automated Rollback
```bash
# Shift 100% traffic immediately back to previous known-good revision
PREV_REVISION=$(az containerapp revision list --name finex-api-app -g finex-prod-rg --query "[?active].name" -o tsv | head -n 1)
az containerapp ingress traffic set --name finex-api-app -g finex-prod-rg --traffic-weight ${PREV_REVISION}=100
```

### Database Schema Compatibility Matrix
- **Rule 1: Additive Migrations Only.** Never drop columns or tables in the same release as code deployment.
- **Rule 2: Two-Phase Deprecation.** Old code must remain compatible with new schema state during rollbacks.
- **Rule 3:** If a migration breaks data invariants, restore isolated point-in-time snapshot to staging and perform emergency reconciliation using `data/quality/goal_spending_reconciliation.py` and `data/quality/paper_trading_reconciliation.py`.

---

## 6. Incident Response & Observability Runbook
- **Logs:** Query Azure Application Insights / Log Analytics with `CorrelationId`:
  ```kusto
  ContainerAppConsoleLogs_CL
  | where Log_s has "X-Correlation-ID"
  | project TimeGenerated, Log_s
  | order by TimeGenerated desc
  ```
- **Rate Limit Alarm:** Alert triggers if 429 count > 50 in 5 minutes.
- **Security Escalation:** Any `401 Unauthorized` spike on `/auth/refresh` indicates potential credential abuse; immediately trigger `POST /api/v1/auth/revoke` for affected account.
