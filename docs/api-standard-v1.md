# FinEx API v1 Standard Specification

**Prefix:** `/api/v1`  
**Security:** Bearer JWT / Cookie session  
**Protocol:** HTTPS / JSON  

---

## 1. Response Envelope Format

All API responses (except file streams) must adhere to the standardized envelope.

### 1.1 Success Response (`200 OK`, `201 Created`, `202 Accepted`)
```json
{
  "success": true,
  "data": {},
  "meta": {
    "correlation_id": "c1f7b7e0-4a8b-4b2a-9e1b-0a7b5d1e2f3a",
    "timestamp": "2026-10-16T12:00:00Z",
    "version": "v1",
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 100,
      "total_pages": 5,
      "has_next": true,
      "has_prev": false
    }
  }
}
```
*Note: `pagination` is omitted for single-resource endpoints.*

### 1.2 Error Response (`400`, `401`, `403`, `404`, `409`, `422`, `500`)
```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested portfolio could not be found.",
    "details": [
      {
        "field": "portfolio_id",
        "issue": "No portfolio exists with ID 'e5a1b2c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c'"
      }
    ]
  },
  "meta": {
    "correlation_id": "c1f7b7e0-4a8b-4b2a-9e1b-0a7b5d1e2f3a",
    "timestamp": "2026-10-16T12:00:00Z",
    "version": "v1"
  }
}
```

---

## 2. Standard Error Codes

| HTTP Status | Error Code | Description |
|---|---|---|
| 400 | `BAD_REQUEST` | Generic client syntax or format error |
| 400 | `INVALID_PAYLOAD` | Request body does not comply with business rules |
| 401 | `UNAUTHORIZED` | Missing, invalid, or expired authentication token |
| 401 | `TOKEN_EXPIRED` | JWT has expired; token refresh required |
| 403 | `FORBIDDEN` | Authenticated user lacks permission for target resource |
| 404 | `RESOURCE_NOT_FOUND` | Target entity does not exist or user does not own it |
| 409 | `CONFLICT` | Resource already exists or version conflict occurred |
| 409 | `IDEMPOTENCY_CONFLICT` | Replay request key submitted with mismatched payload |
| 422 | `VALIDATION_ERROR` | Request parameters failed Pydantic schema validation |
| 429 | `RATE_LIMIT_EXCEEDED` | Request threshold exceeded; retry after delay |
| 500 | `INTERNAL_SERVER_ERROR` | Unexpected server failure; sensitive traces masked |
| 503 | `SERVICE_UNAVAILABLE` | Upstream provider or database is temporarily unreachable |

---

## 3. Headers and Correlation ID

- **Request:**
  - `X-Correlation-ID` (optional, client-provided UUID; if omitted, backend generates one).
  - `Authorization: Bearer <token>`
- **Response:**
  - `X-Correlation-ID`: Always returned with the identical UUID.
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
