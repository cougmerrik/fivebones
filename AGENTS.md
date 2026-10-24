# Codex operating instructions — Five Bones

Deliver a running, testable product rather than only designs or pseudocode. Follow `CODEX_PROMPT.md` and the specification files. Where requirements conflict, safety and data separation outrank convenience; settled game rules outrank example config.

## Hard constraints

- No paid Roll20 features, Mod scripts, API sandbox, custom sheet editing, scraping of undocumented endpoints, authentication/session cookie access, or impersonation.
- Extension may add a self-contained visual overlay in a Shadow DOM and may *optionally read visible* `attr_character_name` and `attr_gp` on the 2014 sheet. Never update sheet values or click on users' behalf. Never transmit or persist other character information.
- Manual player identity and starting GP must work without Roll20 or its DOM. The game must work at its own HTTPS URL.
- Outside the user-authorized cheating amendment in spec/RULES.md, never allow clients to choose dice results. Human and GM-controlled NPC Change die and 33%-five Loaded die are server-validated, private, on-turn actions with Dexterity checks and session-locked ability scores; GM current-hand dice corrections require a reason and private audit. Never allow clients to choose winners, balances, payout amounts, or other players' private actions. GM special NPC rolls must be explicitly authorized, GM-only, and audit logged.
- Never leak dice faces/holds to opponents before showdown. Public reroll count may be shared where required by rules.
- No real-money wagering, payments, casinos, or exchangeable currency; in-game fictional currency only.
- No Roll20 copyrighted graphics/assets. Use original CSS/vector assets and fantasy tavern styling.
- Use pin-scoped dependencies, documented .env.example, do not commit secrets, avoid unnecessary browser permissions.

## Engineering method

1. Inspect workspace, document plan, build vertical slices.
2. First make a tested pure rules engine; implement known rules without inventions.
3. Next make a playable browser-only tabletop with multiplayer server and ledger.
4. Then add a reusable UI mounting surface and optional MV3 browser overlay.
5. Use independent server-side state machines, transactional commands, and explicit role/access checks.
6. Include unit, integration and browser e2e tests; run them; report actual outcomes and remaining limitations.
7. Keep demo/test accounts or dev reset tools out of production routes.
8. Ensure reconnect/reload does not duplicate bets or reveal secret state.
9. End with exact local startup, extension load, deployment steps, and acceptance results.

## Preferred stack (change only with reason)

- Monorepo: pnpm workspace.
- Frontend: TypeScript + React + Vite; accessible interface; TanStack Query optional.
- Game server: Python FastAPI + WebSocket + Pydantic, tested with pytest; PostgreSQL via DATABASE_URL for production (the user’s deployment amendment); SQLite remains supported for local development. Use transactional writes through SQLAlchemy rather than an in-memory source of truth.
- Extension: Chrome/Edge Manifest V3 built with TypeScript; Roll20-specific wrapper injects the **same client UI** as web mode. Minimal permissions and isolated content scripts.
- Rules tests: Python pytest, plus API contract tests. UI: Playwright if environment permits.
- Use Docker Compose for local integration, but also provide bare development commands.

Keep implementation proportionate to 5–8 concurrent seats. Avoid premature microservices, message brokers and elaborate deployment.
