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

Railway may automatically import JavaScript workspace packages as services. Keep `web`; repurpose `contracts` as `api` or create an empty service and connect it to this repository. Remove the extra `ui` and `extension` Railway services. Keep their source folders in GitHub: they are build dependencies, not separately hosted applications.

Set these service settings explicitly in the dashboard:

| Setting | API service | Web service |
| --- | --- | --- |
| Root Directory | repository root `/` | repository root `/` |
| Variable `RAILWAY_DOCKERFILE_PATH` | `server/Dockerfile` | `web/Dockerfile` |
| Custom Build Command | empty | empty |
| Custom Start Command | empty | empty |
| Health check path | `/api/v1/health` | `/health` |
| Health check timeout | 120 seconds | 120 seconds |
| Replicas | **1** | 1 initially |
| Restart policy | On Failure, 5 retries | On Failure, 5 retries |

**Do not set Root Directory to `/web` or `/server`.** The frontend needs root assets and shared packages. Add `RAILWAY_DOCKERFILE_PATH` in each service's Variables tab, clear any auto-imported `pnpm --filter ...` build/start commands, and apply/deploy the changes. Railway should now select Dockerfile builds instead of Railpack. The Dockerfiles supply their own build steps and startup commands; do not add a Node `start` script to fix an API detection error.

The checked-in `server/railway.json` and `web/railway.json` files describe the legacy Config as Code setup. Railway's current documentation says new services cannot opt into those files, and existing users must migrate before its 2026-12-01 cutoff. For new services, use the explicit dashboard settings and Dockerfile variables above. See [Railway's configuration notice](https://docs.railway.com/config-as-code) and [custom Dockerfile instructions](https://docs.railway.com/builds/dockerfiles).

Set watch paths separately if desired: API `server/**`; web `web/**`, `packages/**`, `extension/package.json`, `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, and `*.png`. The services deploy independently. The extension gets no service.

Keep the API at one replica in one region, with one worker, and disable Railway Serverless/app sleeping. Socket fan-out and rate limiting are process-local. PostgreSQL transactions lock room rows, but multiple API processes do not share live broadcasts. Set API variables `RAILWAY_DEPLOYMENT_OVERLAP_SECONDS=0` and `RAILWAY_DEPLOYMENT_DRAINING_SECONDS=15`; clients reconnect after replacement. Database initialization creates missing tables automatically; existing room rows are preserved.

## 3. Allocate public domains and configure variables

Use Railway **Settings → Networking → Generate Domain** for both services, or attach your own domains. In the examples below replace `YOUR-WEB-DOMAIN` and `YOUR-API-DOMAIN` with those real hostnames, without a trailing slash.

If Railway needs a first deployment before it can generate domains, deploy **web** once with `VITE_API_BASE_URL=https://api.invalid` and `VITE_WS_BASE_URL=wss://api.invalid`. Its static health check works without an API. Generate its domain, configure/deploy the API using that web origin, generate the API domain, then replace the web variables with the actual API domain and redeploy web. Do not use the placeholder build to host a game.

### API service variables

```dotenv
RAILWAY_DOCKERFILE_PATH=server/Dockerfile
RAILWAY_DEPLOYMENT_OVERLAP_SECONDS=0
RAILWAY_DEPLOYMENT_DRAINING_SECONDS=15
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
RAILWAY_DOCKERFILE_PATH=web/Dockerfile
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

If an API build says `Railpack`, `Detected Node`, or `No start command detected`, Railway has not selected the Python Dockerfile. Check the service's `RAILWAY_DOCKERFILE_PATH=server/Dockerfile`, root `/`, and cleared custom commands, then start a new deployment. A root Node start script is not needed.

If the website shows `Blocked request. This host ... is not allowed` and mentions Vite `server.allowedHosts`, the web service is running a development server. Set web variable `RAILWAY_DOCKERFILE_PATH=web/Dockerfile`, keep root `/`, clear custom build/start commands (especially `pnpm dev` or `vite`), and rebuild/deploy. The production image serves built files with Nginx; no Vite allowed-host change is needed. Check that the public-domain target port matches Nginx’s listening port (`PORT`, default 8080). Verify the new deployment at `/health`, which must return JSON `{"status":"ok"}`.

If startup logs still show `@fivebones/web ... dev`, `vite --host 0.0.0.0`, or port 5173, the active deployment is still the Node/Vite image. Check that the Dockerfile variable was added to **web**, then use the project’s staged-changes review/deploy action to apply the edited settings. Restarting an old deployment does not change its image, and selecting Redeploy on a historical deployment reuses its original configuration. Check the newest build for its Nginx final stage and wait for that deployment to become active. For an explicit port setup, set web `PORT=8080` and its public-domain target port to 8080. See [Railway staged changes](https://docs.railway.com/deployments/staged-changes) and [deployment actions](https://docs.railway.com/deployments/deployment-actions).

If the web Docker build succeeds through `COPY --from=build /app/web/dist` but startup reports `pnpm` not found, a stale service start override is still trying to launch Node tooling in the final Nginx image. In web Settings → Deploy → Custom Start Command, explicitly replace it with `/docker-entrypoint.sh nginx -g 'daemon off;'` and apply the staged changes as a new deployment. This runs Nginx’s official entrypoint so its configuration template is expanded with `PORT` before the server starts. Keep web `PORT=8080` and the public target port at 8080. pnpm is needed only in the build stage, which has already completed. Once the stale override is resolved, the image’s default startup also works.

If hosting/joining shows `TypeError: Failed to fetch` or `Fetch Failed`, inspect the browser request URL or the deployed JavaScript bundle. `VITE_API_BASE_URL` and `VITE_WS_BASE_URL` must use the API’s generated public `*.up.railway.app` domain. A compiled value such as `https://fivebonescontracts.railway.internal` cannot be reached by a player’s browser: private Railway hostnames are for service-to-service traffic. Replace both web variables with the public HTTPS/WSS API origin, apply the edited variables in a fresh web build, and reload the page. A restart of the existing Nginx image cannot change compiled values. Then verify the API public health endpoint and allow the exact website origin in API `ALLOWED_ORIGINS` and `WS_ALLOWED_ORIGINS`.

If the compiled frontend points to the correct public API but `/api/v1/health` and the browser preflight both return Railway HTTP 502 `Application failed to respond`, check API startup and port routing before changing CORS. Set API `PORT=8000` and its public-domain target port to 8000 for an explicit matching pair. The startup log must show Uvicorn listening on `0.0.0.0:8000`; inspect any traceback if it does not. The backend invitation variable is exactly `APP_BASE_URL`, not `API_BASE_URL`. Missing production configuration can prevent startup even when the Docker build succeeded.

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
