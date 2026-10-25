# Five Bones

A multiplayer fantasy dice-poker table for your D&D campaign. Host a game in a browser, invite players, and manage NPCs from the GM seat. The optional Chrome/Edge extension puts the same table inside Roll20.

Five Bones uses fictional campaign gold. Dice, turns, private actions, and the ledger are controlled by the server. Character names and starting gold are entered manually; the app does not edit Roll20 sheets or access its authentication.

## At the table

- Five human seats and up to five GM-controlled NPCs, with private dice and reconnectable sessions.
- Five dice, two fixed-limit betting rounds, one reroll opportunity, showdown, and the Widowmaker rule.
- A compact phase tracker, centered dice, orientation-specific backgrounds, and the supplied title and dice artwork.
- Private Dexterity-based cheating: Loaded die, Change die, or a written action for DM adjudication. NPCs use the same checks; the DM has audited dice corrections.
- Next-hand opt-in/out, GM removal/restoration, reusable NPC presets, queued automatic NPC rerolls, and a public last-turn recap.
- Live gold/net summaries, a final session summary in the game area, settlement text, and GM CSV export.
- An in-app **Hands & rules** reference and an optional movable, resizable Roll20 overlay.

See [gameplay and campaign conventions](docs/GAMEPLAY.md) for participation controls, NPC preset/queued-roll instructions, betting defaults, tie handling, cheating details, and the table layout.

## Start locally

The simplest setup uses Docker Compose:

```bash
cp .env.example .env
docker compose up --build
```

Open **http://localhost:5173**. The API listens on **http://localhost:8000**. Local SQLite data persists in the `bones-data` volume; Railway is not required.

For a fresh local PostgreSQL setup instead:

```bash
docker compose -f compose.yaml -f compose.postgres.yaml up --build
```

Changing database configuration does not move existing rooms. Back up and migrate an existing game before switching databases.

For development without Docker, use Python 3.11+ (3.12 recommended), Node 24.14, and pnpm 10.11.0 through Corepack:

```bash
python3 -m venv .venv
.venv/bin/pip install -r server/requirements.lock
corepack enable
pnpm install --frozen-lockfile
cp .env.example .env
```

Start the API in one Bash terminal:

```bash
set -a
source .env
set +a
PYTHONPATH=server .venv/bin/python -m app.start
```

In a second terminal, load the same environment and start the website:

```bash
set -a
source .env
set +a
pnpm dev
```

## Belwether quick join

The extension automatically finds the current Belwether session. Players enter **name, starting GP and Dexterity → Join belwether**; room IDs and invite codes are filled by the campaign flow.

- [Player link](https://fivebonesweb-production.up.railway.app/?room=belwether)
- [DM link](https://fivebonesweb-production.up.railway.app/?room=belwether&isdm=1)

The DM enters the existing host invitation secret once under **DM access**, then the browser/extension remembers a separate private credential. The URL flag only selects the DM screen. Finish a session and choose **Start fresh belwether session** to reuse the same link with a new ledger. Previous summaries remain available. See [extension setup](docs/EXTENSION.md) for the full flow and manual recovery for older rooms.

## Play a session

1. Expand **Host a table**, choose stakes, and create the room. Save the private recovery token and share the invite link.
2. Players join in separate browsers/profiles with a name, starting GP, and Dexterity score. Dexterity stays locked for the session. The GM controller is separate from a human player seat.
3. Add NPCs with their own starting gold and Dexterity, then choose **Start next hand**. Follow the highlighted turn through betting and rerolls; the GM plays NPC turns.
4. Between hands, start another hand or end the session. Export the ledger or copy settlements, then update character sheets manually.

A recovery token grants access to its seat. Keep it private. Reloading or reconnecting restores the server's state; **Resume a saved seat** accepts a room ID and token on another device. An invite never grants GM access.

## Deploy with GitHub and Railway

Follow **[RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md)** for the complete deployment sequence, variables, domains, health checks, backups, and optional SQLite migration.

The deployment uses one GitHub repository and two independently deployable Railway services, plus PostgreSQL:

| Service | Root Directory | `RAILWAY_DOCKERFILE_PATH` variable |
| --- | --- | --- |
| API | `/` | `server/Dockerfile` |
| Web | `/` | `web/Dockerfile` |

Set each Dockerfile variable in Railway’s Variables tab and clear auto-generated custom build/start commands. Configure health checks in the dashboard; new services cannot opt into the legacy `railway.json` files. Both builds need the repository root as their context. Production requires PostgreSQL through `DATABASE_URL`, an HTTPS website/API, secure WSS, exact allowed origins, and a private host-creation secret. Frontend `VITE_API_BASE_URL` and `VITE_WS_BASE_URL` are public build-time values: changing them requires a rebuild. Keep one API replica and worker because live socket broadcasting is process-local.

The API binds to `0.0.0.0` and the supplied `PORT`. `/api/v1/health` and `/health` check database readiness; `/live` checks liveness. The web service has its own `/health` endpoint. The extension is distributed separately, never as a Railway service.

## Build the extension

Use the same public backend as your deployed website:

```bash
VITE_API_BASE_URL=https://YOUR-API-DOMAIN \
VITE_WS_BASE_URL=wss://YOUR-API-DOMAIN \
pnpm build:extension
```

This creates `extension/dist/` for **Load unpacked** and `extension/fivebones-extension.zip` for distribution. Without endpoint variables, the build connects to localhost for development.

In `chrome://extensions` or `edge://extensions`, enable Developer mode and load the folder containing `manifest.json`. Refresh a Roll20 editor page and use the Five Bones launcher. Include `https://app.roll20.net` in the API's CORS and WebSocket origins. Updates require rebuilding and reloading the extension.

See [extension instructions](docs/EXTENSION.md) for installation and recovery details. The extension requests only storage permission. Optional sheet import is deferred; manual entry works everywhere.

## Verify changes

```bash
PYTHONPATH=server .venv/bin/pytest server/tests -q
pnpm typecheck
pnpm test:contracts
pnpm build
pnpm exec playwright install chromium
pnpm test
```

Set `TEST_DATABASE_URL` to a dedicated PostgreSQL test database to run session checks against both databases. Browser tests use isolated ports and a temporary database. `pnpm build:web` produces only the website; `pnpm build:extension` produces only the extension and ZIP.

GitHub Actions runs rules/session tests, TypeScript and endpoint checks, production bundles, Docker health/restart checks, and Chromium acceptance. See [development instructions](docs/DEVELOPMENT.md) for exact test setup and [observed results](tests/RESULTS.md) for actual outcomes. The latest server run passes against SQLite and PostgreSQL, including migration and the live-table controls. Earlier Docker runtime verification was limited by network and permission-review timeouts; live Railway and browser-extension acceptance for each new build remain manual.

## Repository map

```text
web/                 React/Vite website and static-server Dockerfile
server/              FastAPI, rules engine, persistence, tests, and API Dockerfile
extension/           MV3 wrapper, build script, and ZIP packaging
packages/ui/         Shared React table and styling
packages/contracts/  Shared wire types and endpoint validation
docs/                Gameplay, development, and extension instructions
spec/                Product, rules, architecture, and deployment specifications
contracts/           Multiplayer protocol and table configuration
tests/               Browser acceptance, smoke checks, and verification records
```

The original PNG artwork is committed at the repository root and bundled into the website and extension. Dependencies, generated bundles/ZIPs, databases, and real `.env` files stay out of Git. Commit `.env.example` files as configuration templates.

Released under the [Apache License 2.0](LICENSE).
