# Architecture

A modular monolith with one API process and one PostgreSQL database.

```text
Browser -> Nginx :8080 -> React static app (SPA fallback)
                       -> FastAPI (Gunicorn + Uvicorn workers) -> PostgreSQL
                                                             -> Redis (rate limits)
```

Backend modules:

- `core`: settings, security, errors, logging
- `db`: engine, sessions, model metadata, migrations
- `models`: SQLAlchemy entities
- `schemas`: request/response validation
- `api`: route handlers and dependency wiring
- `services`: business rules and transaction boundaries

Nginx is the only published Compose service. PostgreSQL is not exposed to the host. The dedicated `test-db` service uses the Compose `test` profile (`make test`) and is bound to `127.0.0.1:5433`.

Swagger UI is at `/api/docs` and the OpenAPI document at `/api/openapi.json` so both stay behind the `/api/` reverse-proxy path.

Security (local demo, not a full production hardening pass):

- SPA: httpOnly access/refresh cookies plus CSRF header on mutations
- Swagger: Bearer `access_token` from login JSON (CSRF skipped)
- Redis sliding-window rate limits on auth and order creation (in-memory if `REDIS_URL` is unset)
- CORS allowlist for `FRONTEND_ORIGIN` with credentials
- Nginx security headers / CSP on the SPA

Order flow: `pending → accepted → (preparing, optional) → out_for_delivery → delivered`. Cancellation is allowed until `out_for_delivery`.

Roles:

- `customer`: browse, order, track, cancel (early states)
- `staff`: one restaurant via `users.restaurant_id`
- `admin`: all restaurants
