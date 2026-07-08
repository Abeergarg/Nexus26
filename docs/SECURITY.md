# Security Policy

## PII Scrubbing

All natural language query text submitted to `/api/navigation/route` passes through `core/security.scrub_pii()` before processing or caching. The following PII types are redacted:

| Type | Regex Pattern | Replacement |
|------|--------------|-------------|
| Email addresses | `[\w\.-]+@[\w\.-]+\.\w+` | `[REDACTED_EMAIL]` |
| Phone numbers | International format | `[REDACTED_PHONE]` |
| Credit card numbers | 13–16 digit sequences | `[REDACTED_CARD]` |
| Names | "my name is X", "I am X", "name: X" | `[REDACTED_NAME]` |

Scrub statistics are returned in every route response (`scrub_stats` field).

---

## Rate Limiting

- **Limit**: 60 requests per IP per 60 seconds (sliding window)
- **Algorithm**: In-memory deque per client IP
- **Response**: HTTP 429 with `Retry-After` header
- **Exempt paths**: `/health/live`, `/health/ready`, `/`

Configure via `RATE_LIMIT_REQUESTS_PER_MINUTE` and `RATE_LIMIT_WINDOW_SECONDS` in `core/constants.py`.

---

## RBAC (Role-Based Access Control)

The `/api/operations/replenish` endpoint checks the `X-User-Role` request header:

| Role | Permission |
|------|-----------|
| `Administrator` | Can trigger supply replenishment |
| Any other value | HTTP 403 Forbidden |

This is a simulation of RBAC using a trusted header. In production, replace with JWT bearer token validation.

---

## CORS Policy

All origins are currently allowed (`allow_origins=["*"]`). For production hardening, restrict to your frontend domain:

```python
allow_origins=["https://nexus26-delta.vercel.app"]
```

---

## Error Response Security

- Stack traces are **never** returned to clients. All unhandled exceptions return a generic `INTERNAL_SERVER_ERROR` message.
- Every error response includes a `request_id` for operator correlation without exposing internals.
- Pydantic validation errors expose field paths and types but not values.

---

## XSS Prevention (Frontend)

- All API response data inserted into the DOM uses `element.textContent` (not `innerHTML`).
- A `sanitizeText()` helper strips HTML tags from any string before DOM insertion.
- No `eval()` or `Function()` calls exist in `app.js`.

---

## Dependency Security

CI runs `pip-audit --requirement requirements.txt` on every push to check for known CVEs in dependencies.
