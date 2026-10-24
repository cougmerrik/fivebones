# Developer / host / player deployment plan

## Development

- Provide `.env.example` with `APP_BASE_URL`, `API_BASE_URL`, `PUBLIC_WSS_URL`, database path, allowed origins, host invite secret and retention config.
- Web: `pnpm install && pnpm --filter web dev` (adjust filters to actual implementation).
- Server: create Python venv; install dependencies; `uvicorn app.main:app --reload` from `server/`.
- Test: `pytest`, `pnpm test`, and optional Playwright run.
- Docker Compose: `docker compose up --build` should bring up web, API, and persistent DB volume.
- Provide a seed/development script creating test NPCs and seats only in dev mode.

## Host production

- Single small instance is sufficient for ~5 human players and NPCs. Provide Docker deployment with SQLite on a persistent volume and reverse proxy providing HTTPS/WSS. No load-balancing assumptions.
- Back up persistent database; server handles restart and reconnection. All player sessions persist across page refreshes.
- Set restrictive allowed origins for standalone app and extension origin as practical. Origin alone is not authorization; seat/GM tokens are required.
- Set environment-specific server endpoint for extension build. Do not hard-code localhost in production extension.
- Include a simple admin process to rotate host keys and delete a room / purge old data.

## Chrome/Edge extension distribution

1. Run extension build into `apps/extension/dist` (actual path may vary).
2. Give players ONLY that bundled directory ZIP. No browser store required for private testing.
3. Unzip, open `chrome://extensions` or `edge://extensions`, enable Developer mode, choose **Load unpacked** and select extracted dist.
4. Navigate to Roll20 game and refresh. Click Five Bones launcher; enter room invite / seat token.
5. For each new version, redistribute and instruct players to replace/reload unpacked directory. Don't imply self-updating.
6. If overlay unavailable or browser unsupported, use the standalone link, with no feature loss other than Roll20 framing / optional read-only import.

## GM operations

Create room, choose fixed-limit stake preset, invite players, enter starting GP, seat NPCs, play hands, finish session, export ledger, send results for manual Roll20 sheet adjustment.

## Operational cautions

- Mobile browsers are not an extension target in this MVP. Standalone mobile responsiveness is a nice-to-have, desktop is required.
- Roll20 may modify its DOM/iframe structure. Optional character read integration should fail gracefully; never make it essential.
- Roll20 does not endorse this software. Respect their terms, avoid undocumented APIs or scraping platform data unrelated to the visible user-selected sheet.
- In-game gold only, not cash/value exchange.


## Production deployment amendment

The maintained GitHub/Railway implementation guide is [RAILWAY_DEPLOY.md](../RAILWAY_DEPLOY.md). Production uses PostgreSQL via DATABASE_URL, with independent root-context web/API Docker builds and HTTPS/WSS. SQLite remains available for local development. The MV3 extension is built and distributed separately, never deployed as a Railway service.
