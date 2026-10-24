# Deploy Five Bones from GitHub to Railway

This repository supplies two independent Railway services. The web service builds React/Vite and serves static files with Nginx. The API runs FastAPI and WebSockets with persistent PostgreSQL data. The extension is a download, not a Railway service.

## 1. Commit and push

From the repository root:

```bash
git add .
git commit -m "Prepare Five Bones for Railway and PostgreSQL"
git push origin HEAD
```

Create/connect your GitHub repository first if it has no remote. `.env`, databases, dependencies, ZIPs, and build outputs are ignored. Keep the source PNG assets: both frontend and extension builds bundle them. GitHub Actions runs Python rules/session tests against SQLite and PostgreSQL, TypeScript and endpoint checks, production bundles, independent Docker images with health/restart smoke checks, and Chromium browser tests. Its extension artifact points to localhost; rebuild with your real API domain before distribution.

## 2. Create the Railway project and services

Create a Railway project and add **PostgreSQL**. Add two services connected to this same GitHub repository/branch, named `api` and `web`.

Set these service settings explicitly:

| Setting | API service | Web service |
| --- | --- | --- |
| Root Directory | repository root `/` | repository root `/` |
| Config File | `/server/railway.json` | `/web/railway.json` |
| Dockerfile (set by config) | `server/Dockerfile` | `web/Dockerfile` |
| Health check (set by config) | `/api/v1/health` | `/health` |
| Replicas | **1** | 1 initially |

**Do not set Root Directory to `/web` or `/server`.** The frontend needs root assets and shared packages. The config-file paths select different builds while preserving that context. Leave the custom build/start commands empty; Dockerfiles supply them. Each service has its own watch patterns and deploys independently. The extension gets no service.

Keep the API at one replica in one region, with one worker, and disable Railway Serverless/app sleeping. Socket fan-out and rate limiting are process-local. PostgreSQL transactions lock room rows, but multiple API processes do not share live broadcasts. The API configuration requests zero deployment overlap and a 15-second drain; clients reconnect after replacement. Database initialization creates missing tables automatically; existing room rows are preserved.

## 3. Allocate public domains and configure variables

Use Railway **Settings → Networking → Generate Domain** for both services, or attach your own domains. In the examples below replace `YOUR-WEB-DOMAIN` and `YOUR-API-DOMAIN` with those real hostnames, without a trailing slash.

If Railway needs a first deployment before it can generate domains, deploy **web** once with `VITE_API_BASE_URL=https://api.invalid` and `VITE_WS_BASE_URL=wss://api.invalid`. Its static health check works without an API. Generate its domain, configure/deploy the API using that web origin, generate the API domain, then replace the web variables with the actual API domain and redeploy web. Do not use the placeholder build to host a game.

### API service variables

```dotenv
APP_ENV=production
DATABASE_URL=${{Postgres.DATABASE_URL}}
APP_BASE_URL=https://YOUR-WEB-DOMAIN
ALLOWED_ORIGINS=https://YOUR-WEB-DOMAIN,https://app.roll20.net
WS_ALLOWED_ORIGINS=https://YOUR-WEB-DOMAIN,https://app.roll20.net
HOST_INVITE_SECRET=REPLACE_WITH_YOUR_OWN_RANDOM_SECRET
WEB_CONCURRENCY=1
RETENTION_DAYS=30
```

Use Railway's variable-reference picker for `DATABASE_URL`: `Postgres` must match your actual database service name. The internal database reference belongs **only on the API**, not on the web service or in a Vite variable. Do not set `DATABASE_PATH` for production. `APP_ENV=production` refuses SQLite, short host secrets, insecure public origins, and multiple workers.

Generate your own host secret locally:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Paste it into Railway's API variables and keep it privately for the GM. The GM enters it when creating a table; players receive a room invite instead. Never put it in GitHub, frontend variables, screenshots, or the extension. Saved seat tokens remain separate from this creation secret.

Origins are exact, comma-separated HTTPS origins: no `*`, paths, or trailing routes. Include every standalone frontend domain you actually use. Include `https://app.roll20.net` for the extension. CORS and WebSocket origins are checked independently; neither replaces per-seat/GM authorization. If you omit `WS_ALLOWED_ORIGINS`, it inherits `ALLOWED_ORIGINS`.

Leave Railway's supplied `PORT` in place. The API starts through `python -m app.start`, binds `0.0.0.0:$PORT`, and has no dependency on a fixed external port. If networking asks for a target port, select the port shown in its startup log.

### Web service variables

```dotenv
VITE_API_BASE_URL=https://YOUR-API-DOMAIN
VITE_WS_BASE_URL=wss://YOUR-API-DOMAIN
```

These are **public build-time** values. Use the public API domain, not Railway's private `.railway.internal` hostname. Change a value and **rebuild/redeploy web**; restarting an old image does not replace its JavaScript. Both Docker build arguments are declared explicitly. If the WebSocket variable is omitted, it derives `wss://` from the HTTPS API origin. Insecure public endpoint combinations are rejected.

Nginx listens on Railway's supplied `PORT` (8080 by default locally). No API credentials, database URL, or host secret belong in this service. Web health tests static serving; API readiness tests database connectivity.

## 4. Deploy and verify

Deploy API, then rebuild/deploy web with the real API domain. In Railway logs check that the API completed startup and each health check passed. Railway terminates public HTTPS/WSS; the containers receive internal HTTP traffic.

Check:

```bash
curl --fail https://YOUR-API-DOMAIN/api/v1/health
curl --fail https://YOUR-API-DOMAIN/live
curl --fail https://YOUR-WEB-DOMAIN/health
```

All should return a successful JSON response. `/health` on the API is another readiness alias. Readiness returns HTTP 503 without database details when the database is unavailable; liveness does not query the database.

Open the web URL, host a table using your creation secret, and save its recovery token. Join in two separate browser profiles. Check that each player sees only their own dice before showdown, complete a hand, inspect the ledger, and refresh both clients. Then restart/redeploy **only the API** and confirm reconnection preserves dice, balances, and turn state. In browser developer tools, the room socket should use `wss://YOUR-API-DOMAIN/...` and authenticate in its first message, with no credential in the URL. Test a player cheat notification and a GM NPC turn as well. Automated local tests cover role redaction and durable command retries; live Railway networking still needs this acceptance check.

A healthy API with a disconnected browser usually means a wrong compiled web endpoint or an omitted exact origin. Inspect the browser Network/WebSocket view and API logs, correct the service variables, and redeploy the affected service. A startup failure in production is often a missing secret, database reference, or HTTPS origin. Never loosen origin validation to `*`.

## 5. Build and distribute the extension

At your local repository root, after installing the Node/Python development tools:

```bash
VITE_API_BASE_URL=https://YOUR-API-DOMAIN \
VITE_WS_BASE_URL=wss://YOUR-API-DOMAIN \
pnpm build:extension
```

Outputs:

- `extension/dist/`: unpacked MV3 extension.
- `extension/fivebones-extension.zip`: distributable archive with the manifest, bundled script, and image assets.

Send the ZIP privately to players. They extract it, open `chrome://extensions` or `edge://extensions`, enable Developer mode, choose **Load unpacked**, and select the extracted folder containing `manifest.json`. Refresh a Roll20 editor page and use the Five Bones launcher. The same public API handles the standalone site and extension. The extension has only storage permission and does not edit sheets or access Roll20 authentication. There is no automatic update mechanism: rebuild/reload and redistribute when code or backend domains change. Actual Roll20 and Edge acceptance is manual; the automated extension test uses a controlled page at the permitted origin.

## 6. Data, backups, and updates

PostgreSQL stores private room state, hashed credentials, command receipts, audits, and ledger records. Restarting or rebuilding either application does not reset it. The API container filesystem is disposable. Protect database access and backups as carefully as seat tokens. Configure Railway's available PostgreSQL backup policy and retention explicitly; this repository does not enable a managed backup plan or scheduled purge for you.

Start a new production campaign unless you need existing local rooms. For an existing SQLite database, stop the source API, stop writes to the destination API, back up both databases, and run this once from a trusted machine/environment that can reach PostgreSQL:

```bash
DATABASE_URL='YOUR_POSTGRES_CONNECTION_URL' PYTHONPATH=server \
.venv/bin/python -m app.migrate --source-sqlite /absolute/path/fivebones.sqlite3 --confirm
```

Use a reachable connection URL (Railway private addresses are reachable only inside its network). A room-ID collision aborts the whole copy; no destination rooms are overwritten. The source is opened read-only. Tokens and private state remain valid, but browser storage does not move between website/API origins: save recovery tokens before migration and resume explicitly at the new site. Share new-domain invite links. Do not copy a live SQLite file without a consistent backup.

During maintenance, stop API access before using offline administration with the same `DATABASE_URL`:

```bash
PYTHONPATH=server .venv/bin/python -m app.admin rotate-host --room ROOM_ID --confirm
PYTHONPATH=server .venv/bin/python -m app.admin purge --days 30 --confirm
```

Inside the API image, omit `PYTHONPATH=server .venv/bin/` and use `python -m app.admin ...`. Rotation prints a new private recovery token and invalidates old GM credentials. Purge removes only ended rooms old enough by creation date. Manage exported files and backup retention separately. There is no public reset or administration route. Future incompatible schema changes require an explicit migration; current initialization only creates the existing table when absent.

The local builds/tests and their limitations are recorded in [tests/RESULTS.md](tests/RESULTS.md). GitHub-hosted CI and live Railway deployment run only after you push/connect the repository; they have not been performed by the local checks.

Reference: Railway's official [monorepo guide](https://docs.railway.com/guides/monorepo), [Dockerfile guide](https://docs.railway.com/guides/dockerfiles), [configuration reference](https://docs.railway.com/reference/config-as-code), [health checks](https://docs.railway.com/guides/healthchecks), and [PostgreSQL guide](https://docs.railway.com/guides/postgresql).
