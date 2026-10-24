# Development and verification

Run all commands from the repository root. Production deployment is documented in [RAILWAY_DEPLOY.md](../RAILWAY_DEPLOY.md).

## Layout

- `web/`: React/Vite entry point, static-server Dockerfile, legacy Railway config, public environment example.
- `server/`: FastAPI, pure rules engine, PostgreSQL/SQLite persistence, tests, Dockerfile and legacy Railway config.
- `extension/`: MV3 wrapper around the shared interface, build script, ZIP packaging and public environment example.
- `packages/ui/`, `packages/contracts/`: shared interface and protocol validation.
- `docs/`: development and implementation notes. Specifications remain under `spec/` and `contracts/`.

## Bare development

Use Python 3.11+ (container/CI: 3.12), Node 24.14 and pnpm 10.11.0:

```bash
python3 -m venv .venv
.venv/bin/pip install -r server/requirements.lock
corepack enable
pnpm install --frozen-lockfile
cp .env.example .env
set -a
source .env
set +a
PYTHONPATH=server .venv/bin/python -m app.start
```

In a second terminal, load `.env` in the same way and run `pnpm dev`; open http://localhost:5173. The shell examples use Bash. Other shells can set these same variables explicitly. The Python startup reads the environment; it does not implicitly load a `.env` file. Vite also supports `web/.env` for its public build variables. Extension builds read exported shell variables.

With `DATABASE_URL` empty, `DATABASE_PATH` selects a local SQLite file. No Railway account is required. To test PostgreSQL locally, use the optional Compose override:

```bash
docker compose -f compose.yaml -f compose.postgres.yaml up --build
```

Its database is local-only on port 15432, with explicitly development-only credentials. Alternatively export your own `DATABASE_URL=postgresql://...` for the bare API. Production uses PostgreSQL and `APP_ENV=production`.

## Environment

See root, `server/`, `web/`, and `extension/` `.env.example` files. `DATABASE_URL`, `HOST_INVITE_SECRET`, `ALLOWED_ORIGINS`, and `WS_ALLOWED_ORIGINS` are server-only. `APP_BASE_URL` is the website origin used for invitations. `PORT` controls the API listening port. `VITE_API_BASE_URL` and optional `VITE_WS_BASE_URL` are public build-time frontend/extension values; never place credentials there. HTTPS derives WSS automatically. Explicit insecure public sockets are rejected. Local loopback endpoints remain available for development.

## Checks and production bundles

```bash
PYTHONPATH=server .venv/bin/pytest server/tests -q
pnpm typecheck
pnpm test:contracts
pnpm build
pnpm exec playwright install chromium
pnpm test
```

To run the session tests against PostgreSQL as well, set `TEST_DATABASE_URL` to a dedicated test database. Its user must be allowed to create/drop schemas. Each test gets a unique schema; cleanup drops only that schema. Never point this variable at a production database.

```bash
TEST_DATABASE_URL=postgresql://fivebones:local-development-only@localhost:15432/fivebones \
PYTHONPATH=server .venv/bin/pytest server/tests -q
```

Browser tests start isolated servers on 18000/15173, use a `/tmp` database, and build an isolated test extension. Set `CHROMIUM_EXECUTABLE` to an existing full Chromium binary if needed. They do not replace the normal localhost:8000/5173 table. The extension test uses a controlled Roll20-origin page, not a live campaign. Hosted Roll20/Edge and Railway networking require manual acceptance.

`pnpm build:web` produces only `web/dist`. `pnpm build:extension` produces `extension/dist` and `extension/fivebones-extension.zip`. Both bundle the supplied local PNGs. `docker compose build` builds the two production-style images independently; no extension service is included. GitHub Actions runs the checks on push/PR with a PostgreSQL service.

## Architecture and limits

The authoritative rules engine, RNG, balances, private dice, credentials and command receipts live on the server. A persisted JSON room aggregate is updated transactionally. PostgreSQL uses `SELECT ... FOR UPDATE`; SQLite uses `BEGIN IMMEDIATE`. Tokens are stored as hashes. Role filtering happens server-side before each snapshot. Dexterity and cheat controls follow the explicit campaign amendment in `spec/RULES.md`.

Socket connections retry every two seconds after disconnection and recover a fresh authorized snapshot. Durable command IDs prevent duplicate accepted wagers/cheats after lost acknowledgments. Graceful shutdown disconnects sockets for recovery. Keep a single API process and replica because connected-socket fan-out and rate limits are process-local. PostgreSQL enables durable production storage, not distributed socket routing.

See the deployment guide before migrating SQLite or rotating credentials; stop writes and back up first. No production reset/debug endpoints exist.
