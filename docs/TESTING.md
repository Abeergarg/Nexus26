# Testing Guide

## Test Suite Structure

```
backend/tests/
├── test_integration.py        # End-to-end API integration tests
├── test_security_exploit.py   # RBAC, SQL injection, XSS defense tests
├── test_wayfinding.py         # Dijkstra routing logic unit tests
├── test_operations.py         # Heat index, forecast, replenishment tests
├── test_cache.py              # SemanticCache TF-IDF and TTL tests
├── test_middleware.py         # RequestID, RateLimit, RequestLogging middleware
├── test_health.py             # /health/live and /health/ready probe tests
└── test_constants.py          # Domain constant type and value validation
```

## Running Tests Locally

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=app --cov-report=term-missing

# Run a specific test file
python -m pytest tests/test_integration.py -v

# Run quality pipeline (format check + lint + tests)
python run_pipeline.py
```

## Coverage Targets

| Module | Target |
|--------|--------|
| `app/core/` | ≥ 85% |
| `app/features/` | ≥ 75% |
| **Overall** | **≥ 75%** |

CI fails if overall coverage drops below 75%.

## CI Gates

Every push/PR runs in GitHub Actions:

1. **Black** — code formatting check
2. **Flake8** — PEP 8 linting (max line length: 120)
3. **Bandit** — security static analysis (skips B101 `assert`)
4. **pip-audit** — dependency CVE scan
5. **pytest + coverage** — all tests + coverage threshold gate

Coverage reports are uploaded as GitHub Actions artifacts (retained 30 days).

## Async Tests

Async tests use `pytest-anyio` with `asyncio_mode = "auto"` configured in `pyproject.toml`. Mark async tests with `@pytest.mark.anyio`.
