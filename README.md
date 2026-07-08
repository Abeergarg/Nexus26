# Nexus26: Intelligent Stadium Operations Core

[![CI](https://github.com/Abeergarg/Nexus26/actions/workflows/ci.yml/badge.svg)](https://github.com/Abeergarg/Nexus26/actions)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?logo=vercel)](https://nexus26-delta.vercel.app)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org)

> **AI-powered real-time stadium operations for FIFA World Cup 2026.**
> Live crowd routing • Heat index forecasting • Semantic caching • WCAG 2.1 AA

---

## 🏟️ What is Nexus26?

Nexus26 is a production-grade intelligent operations platform for MetLife Stadium during FIFA World Cup 2026. It provides:

- **Agentic Wayfinding** — Dijkstra shortest-path routing with accessibility profiles (standard, mobility-impaired, eco-green) and multilingual turn-by-turn directions (EN, ES, FR, AR)
- **Live Resource Forecasting** — NOAA heat index calculation, resource depletion tracking (water, ice, medical), and automated logistics dispatch
- **Real-time Telemetry** — Crowd density simulation on a 50+ node stadium graph with live SVG heatmap
- **Privacy-First** — PII scrubbing gateway (emails, phones, credit cards, names) on all user queries
- **Semantic Cache** — TF-IDF + cosine similarity cache with configurable threshold for near-duplicate query detection

---

## 🚀 Live Demo

**[https://nexus26-delta.vercel.app](https://nexus26-delta.vercel.app)**

---

## 🛠️ Local Development

### Prerequisites
- Python 3.12+
- pip

### Setup

```bash
git clone https://github.com/Abeergarg/Nexus26.git
cd Nexus26/backend

pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `frontend/index.html` in your browser (or serve via any static file server).

### Interactive API Docs

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Project metadata |
| `GET` | `/health/live` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe |
| `GET` | `/api/telemetry/topology` | Stadium topology graph |
| `POST` | `/api/telemetry/simulate` | Ingest crowd density events |
| `POST` | `/api/navigation/route` | Calculate optimal route |
| `GET` | `/api/operations/forecast` | Live heat + resource forecast |
| `POST` | `/api/operations/replenish` | Restock supplies (Admin only) |
| `GET` | `/api/operations/cache/stats` | Cache performance metrics |

---

## 🧪 Running Tests

```bash
cd backend
python -m pytest tests/ --cov=app --cov-report=term-missing -v
```

---

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Security Policy](docs/SECURITY.md)
- [Testing Guide](docs/TESTING.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

---

## ♿ Accessibility

The dashboard meets **WCAG 2.1 Level AA** standards:
- Skip navigation link
- ARIA landmarks and live regions for all dynamic content
- Keyboard navigable with visible focus rings
- `prefers-reduced-motion` support (all animations suppressed)
- Windows High Contrast Mode compatible (`forced-colors: active`)
- All API data DOM-sanitized to prevent XSS

---

## 🔒 Security

- Per-IP rate limiting (60 req/min)
- PII scrubbing on all user inputs
- Request ID tracing on all responses
- No stack traces exposed to clients
- Dependency vulnerability scanning (pip-audit) in CI

---

## License

MIT © Abeergarg
