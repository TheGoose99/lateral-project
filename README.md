# Takeaway Platform

Interview-ready modular monolith: customers browse restaurants, place orders, and track status; staff manage menus and move orders through a locked state machine.

```text
Browser -> Nginx :8080 -> React SPA
                       -> FastAPI (Gunicorn + Uvicorn workers) -> PostgreSQL
                                                              -> Redis
```

## 1. What you need

- Docker Engine with the Compose plugin (`docker compose version` should print a version).
- Free local port **8080**.
- This repository as the working directory (run every command from the repo root).

Do not commit `.env`. Compose values are for a local demo only.

## 2. Start the stack

1. Copy the example environment file (once):

   ```bash
   cp .env.example .env
   ```

2. Build images and start every service:

   ```bash
   docker compose up --build
   ```

   First start can take several minutes. Leave this terminal open; logs stay in the foreground.

3. Wait until Nginx and the API are healthy. You should see containers for `db`, `redis`, `api`, `frontend`, and `nginx`. Startup runs `alembic upgrade head` and seeds demo restaurants, menus, and users.

4. Confirm the stack from another terminal:

   ```bash
   curl -s http://localhost:8080/ready
   ```

   Expected body includes `"status":"ready"`, `"database":"ok"`, and `"redis":"ok"`.

5. Open these URLs:

   | What | URL |
   | --- | --- |
   | App | http://localhost:8080 |
   | Swagger | http://localhost:8080/api/docs |
   | Readiness | http://localhost:8080/ready |

Equivalent: `make up` for step 2. Stop later with `Ctrl+C` in that terminal, then `docker compose down` (or `make down`).

## 3. Demo accounts

Password for every seeded user: `correct-horse-battery-staple`

| Role | Email | After sign-in |
| --- | --- | --- |
| Customer | `customer@example.com` | Home + **My orders** |
| Staff | `staff@example.com` | **Staff queue** (Bun & Bun only) |
| Admin | `admin@example.com` | **Staff queue** for every restaurant |

Sign out in the header before switching roles. The SPA keeps one cookie session at a time.

## 4. Suggested demo (about 5 minutes)

Use two browser windows (or one window plus an incognito window). Keep the stack from section 2 running.

### A. Customer places an order

1. Window 1: open http://localhost:8080.
2. Click **Sign in**. Stay on **Log in**.
3. Email `customer@example.com`, password `correct-horse-battery-staple`, click **Sign in**.
4. On the home page, open the restaurant **Bun & Bun**.
5. Click **+ Add** on any available item. Open **Cart** in the header.
6. Click **Continue to checkout**, then **Place order**.
7. You should see **ORDER CONFIRMED** and status `pending`. Click **Track this order**.
8. Leave this tab open. **My orders** and the order detail page poll while the order is active.

### B. Staff moves the order

1. Window 2: open http://localhost:8080, click **Sign in**.
2. Email `staff@example.com`, same password, click **Sign in**. You land on **Order queue** (`/staff`).
3. Find the new order (status **Pending**). Click **Accept**.
4. From **Accepted**, either:
   - skip kitchen: click **Out for delivery**, or
   - full path: **Start preparing**, then **Out for delivery**.
5. Click **Mark delivered**.
6. Window 1 should catch up without a refresh. Invalid jumps (for example pending → delivered) return **409** if you try them in Swagger.

Required flow: `pending → accepted → (preparing, optional) → out_for_delivery → delivered`. Cancel needs a reason and is allowed until `out_for_delivery`.

### C. Hide a menu item

1. Still signed in as staff, click **Menu** in the header.
2. On an item that is visible to customers, click **Hide**. The line should show **Hidden from customers**.
3. Window 1: sign out, or open Bun & Bun in a private window without staff session. Refresh the public restaurant page. That item should be gone.
4. Optional: click **Show** in **Menu** to restore it.

### D. Swagger (Bearer), not the SPA

The app itself uses httpOnly cookies. You do **not** copy tokens to use the UI.

1. Open http://localhost:8080/api/docs.
2. Expand `POST /api/v1/auth/login`, click **Try it out**, body:

   ```json
   {
     "email": "customer@example.com",
     "password": "correct-horse-battery-staple"
   }
   ```

3. Click **Execute**. Copy `access_token` from the JSON (not the refresh cookie).
4. Click **Authorize**, paste the token, confirm. Swagger sends `Authorization: Bearer …` and skips CSRF.
5. Call a customer endpoint such as `GET /api/v1/orders` to confirm.

## 5. Run tests

Keep Docker available. The demo stack may stay up; tests use a separate Postgres (`test-db` Compose profile).

```bash
make test
```

That command:

1. Starts `test-db` and waits until it is healthy.
2. Migrates that database (not the demo volume).
3. Runs the backend pytest suite with rate limits off and `REDIS_URL` empty.

Expected: all tests pass. Do not point tests at the seeded demo database.

Lint (optional, from a running API image or a local backend venv):

```bash
docker compose run --rm --no-deps api ruff check .
```

## 6. Stop and reset

| Goal | Command |
| --- | --- |
| Stop containers, keep data | `docker compose down` |
| Wipe the local Postgres volume (destructive) | `docker compose down -v` |
| Follow logs | `make logs` or `docker compose logs -f --tail=100` |

After `down -v`, the next `docker compose up --build` migrates and re-seeds.

## Design notes

- Prices and totals are calculated on the server; order lines store name/price snapshots.
- Roles come from the database, not from the JWT payload.
- Staff see only their restaurant; admins see all.
- Order flow is `pending → accepted → (preparing, optional) → out_for_delivery → delivered`. Cancellation needs a reason and is allowed until `out_for_delivery`.
- The demo image includes tests and dev dependencies and seeds demo data on every start; this is intentional.

## Security choices

- **SPA session:** httpOnly `takeaway_access` and `takeaway_refresh` cookies (`SameSite=Lax`). The refresh cookie is scoped to `/api/v1/auth`. Tokens are not stored in `localStorage`.
- **CSRF:** readable `takeaway_csrf` cookie plus `X-CSRF-Token` on POST/PATCH/DELETE when the SPA uses cookies. Swagger/Bearer requests skip CSRF so `Authorize` still works.
- **Refresh tokens** are opaque secrets stored only as SHA-256 hashes. `POST /api/v1/auth/refresh` reads the refresh cookie, rotates it, and reusing a revoked refresh token revokes the rest of that user's family.
- **Checkout idempotency:** optional `Idempotency-Key` on `POST /api/v1/orders`. The same customer + key + body returns the original order; a different body with the same key returns 409.
- **Rate limits** on register/login/refresh/logout (10/min/IP) and order placement (20/min/IP), stored in Redis so Gunicorn workers share the window. Tests fall back to in-memory when `REDIS_URL` is empty.
- **CORS** is locked to `FRONTEND_ORIGIN` with credentials. The demo itself is same-origin through Nginx.
- **Nginx** sets `nosniff`, `DENY` framing, referrer policy, and a CSP on the SPA. It overwrites `X-Forwarded-For` with `$remote_addr` so clients cannot spoof the rate-limit IP.
- **SECRET_KEY** must be 32+ bytes in production; development logs a warning if the default is left in place.

Intentionally not in this homework: WAF/CAPTCHA and `Secure` cookies on HTTP localhost.

## Layout

- `backend/` FastAPI, SQLAlchemy, Alembic, tests
- `frontend/` React + TypeScript SPA
- `nginx/` reverse proxy (only published port)
- `compose.yaml` local runtime
