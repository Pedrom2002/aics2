# Testing Guide

This repo has three layers of automated tests. Each layer can be run independently.

| Layer | Tool | Location | Speed | When it runs |
| --- | --- | --- | --- | --- |
| Frontend unit | [Vitest](https://vitest.dev) + Testing Library | `packages/frontend/src/**/*.test.{ts,tsx}` | fast (ms) | every push (`ci.yml`) |
| Backend unit | [pytest](https://docs.pytest.org) | `packages/backend/tests/test_*.py` | fast (s) | every push (`ci.yml`) |
| Backend integration | pytest + httpx ASGI | `packages/backend/tests/integration/` | medium | every push (`ci.yml`) |
| Frontend E2E | [Playwright](https://playwright.dev) (chromium) | `packages/frontend/e2e/` | slow (min) | pull requests + manual (`e2e.yml`) |

---

## Running tests locally

### 1. Frontend unit tests

```bash
cd packages/frontend
pnpm install
pnpm test            # one-shot (CI mode)
pnpm test:watch      # interactive watch mode
```

### 2. Backend unit + integration tests

```bash
cd packages/backend
uv sync --extra dev --extra test
uv run pytest                          # everything
uv run pytest tests/integration -v     # only integration suite
uv run pytest tests/test_auth.py -v    # one file
uv run pytest -k "auth_lifecycle"      # by name
```

The backend test suite uses an in-memory SQLite database (see
`packages/backend/tests/conftest.py`) — no Postgres or Redis required for
local runs.

### 3. Frontend E2E tests (Playwright)

E2E tests assume **both** frontend and backend are already running. The
Playwright config does not start servers for you (so you can re-run quickly).

```bash
# terminal 1 — backend
cd packages/backend
uv run uvicorn src.main:app --reload

# terminal 2 — frontend
cd packages/frontend
pnpm dev

# terminal 3 — first-time only: install browsers
cd packages/frontend
pnpm exec playwright install chromium

# terminal 3 — run tests
pnpm exec playwright test                          # all specs
pnpm exec playwright test e2e/golden-paths/auth    # one file
pnpm exec playwright test --ui                     # interactive UI mode
pnpm exec playwright test --debug                  # step debugger
pnpm exec playwright show-report                   # open last HTML report
```

Override the targets if you're testing against a deployed environment:

```bash
PLAYWRIGHT_BASE_URL=https://staging.example.com \
PLAYWRIGHT_API_BASE_URL=https://api.staging.example.com \
  pnpm exec playwright test
```

#### Skipping behaviour

E2E specs auto-skip with a clear reason when:

- the backend health endpoint is unreachable (auth fixture cannot register a
  test user), or
- a UI element required by the spec is missing (selectors fall back gracefully).

This means `playwright test --list` always works, even in environments where
no backend is running.

---

## Test directory layout

```
packages/frontend/e2e/
├── fixtures/
│   └── auth.ts              # Test fixtures: makeTestUser, apiRegister, authenticatedPage
├── pages/                   # Page Object Models (POM) — one class per page
│   ├── login-page.ts
│   ├── register-page.ts
│   ├── dashboard-page.ts
│   └── match-detail-page.ts
├── golden-paths/            # End-to-end "happy path" specs, one per major flow
│   ├── auth.spec.ts
│   ├── match-detail.spec.ts
│   ├── scout.spec.ts
│   └── player.spec.ts
└── critical-flows.spec.ts   # Lightweight smoke checks (landing, redirects)

packages/backend/tests/
├── conftest.py              # client fixture (ASGI + SQLite)
├── test_*.py                # Unit / per-router tests
└── integration/             # Multi-router lifecycle tests
    ├── test_auth_flow.py
    ├── test_match_flow.py
    └── test_billing_flow.py
```

---

## Conventions

### Selector priority (Playwright)

1. **`getByRole` / `getByLabel` / `getByText`** — closest to what users see.
2. **`data-testid="..."`** — for elements that have no semantic role and are
   load-bearing for tests. Add the attribute to the component, then reference
   it as `page.locator('[data-testid="..."]')`.
3. **CSS / attribute selectors** — last resort, only for genuinely unique
   structural anchors.

Avoid XPath, nth-child positional selectors, and chained CSS selectors that
encode markup details.

### Page Object Model (POM)

- One file per page under `e2e/pages/`.
- Constructor takes a `page: Page`, exposes `Locator` properties, and provides
  intent-revealing methods (`login()`, `openTab()`).
- Specs import POMs and never reach into raw selectors directly.

### Fixtures

- Use the `test` export from `e2e/fixtures/auth.ts` instead of importing
  directly from `@playwright/test`. It auto-injects a registered `testUser`
  and an `authenticatedPage`.
- Fixtures should be idempotent and self-cleaning; do not share state across
  tests.

### Mocking with `page.route`

- Use `page.route(/\/api\/v1\/.../, ...)` to stub backend endpoints when a
  spec wants to test the frontend in isolation.
- Use a real backend only when the test specifically asserts integration
  behaviour (e.g. the `auth.spec.ts` register/login flow).

### Pytest integration tests

- Reuse the `client` fixture from `conftest.py`. Do not roll your own
  ASGITransport.
- One file per business flow (`test_<flow>_flow.py`), multiple `test_*`
  functions inside, each asserting a specific path.
- If a test depends on a feature still under development, mark it
  `@pytest.mark.skip(reason="waiting for stream X: <thing>")` so collection
  still works and the test serves as a TODO.

---

## Adding a new test

### Adding an E2E spec

1. Identify (or create) a POM in `e2e/pages/` for the page(s) you'll touch.
2. Create `e2e/golden-paths/<flow>.spec.ts`.
3. Import `test, expect` from `../fixtures/auth` (not from `@playwright/test`).
4. Add a `beforeAll` health check or `test.skip(...)` for any external dep.
5. Run `pnpm exec playwright test --list` to confirm collection.
6. Run `pnpm exec playwright test <file> --ui` to iterate.

### Adding a backend integration test

1. Pick the right file in `tests/integration/` (or create a new
   `test_<flow>_flow.py`).
2. Use `client: AsyncClient` as the only fixture you need; `setup_database`
   is autouse so the schema is recreated per test.
3. Register a fresh user inline at the top of each test — do not share users
   across tests.
4. For Stripe / Celery / external SDKs, monkeypatch at the router module
   (e.g. `src.routers.billing._get_stripe`) so the test stays hermetic.

---

## CI

- `ci.yml` runs lint, type-check, frontend build, backend pytest (incl.
  integration), and ML tests on every push and PR.
- `e2e.yml` runs Playwright on every PR and on manual `workflow_dispatch`.
  Failed runs upload the HTML report and server logs as artifacts.
