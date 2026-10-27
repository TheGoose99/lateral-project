# Implementation Plan

1. **Foundation:** repository, Compose, API, frontend, Nginx, smoke tests.
2. **Database:** SQLAlchemy sessions, Alembic, users, restaurants, memberships, menu items, orders, order items, status events, constraints and indexes.
3. **Authentication and browsing:** Argon2id, authentication/session design, role loading from database, restaurant/menu APIs.
4. **Ordering:** server-side pricing, snapshots, transactions, idempotency, ownership, staff scope, locked state transitions, audit events.
5. **Frontend:** discovery, menu, cart/checkout, customer order views/polling, staff queue/actions and menu management.
6. **Quality/security:** PostgreSQL integration and concurrency tests, consistent errors, rate limiting, CSRF/Origin protections, logging and validation.
7. **Release/interview prep:** clean-start verification, smoke tests, docs, demo and change-request drills.

## Acceptance rules
- Do not mark tasks complete unless the command/test actually passed.
- Use PostgreSQL integration tests for database semantics.
- Keep routers thin and business rules in services.
- Calculate prices on the server and snapshot item names/prices on orders.
- Invalid state transitions return a consistent conflict response.
- Never trust client-supplied role, price, total, or staff membership.
