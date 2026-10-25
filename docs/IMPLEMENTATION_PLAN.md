# GitHub / Railway implementation plan

1. Preserve the working game while moving the inspected apps into /web and /extension, retaining /server and shared /packages.
2. Compact DM notifications and align the rules button with the selected phase chip.
3. Add DATABASE_URL persistence with PostgreSQL transactional room locks; retain SQLite development and existing room format.
4. Add independent PORT-aware Docker/Railway services, explicit endpoint/origin configuration, health and restart handling.
5. Produce the unpacked extension and ZIP; document GitHub/Railway setup, variables, database operations and limits.
6. Test rules/API against SQLite and an actual local PostgreSQL, production images, WebSocket recovery, browser flows and ZIP contents. Record actual results and manual cloud setup gates.

Production remains one API replica/worker for 5–8 seats. Database row locks protect commands, and deploys close sockets so clients recover from persistent snapshots. No Railway account deployment or GitHub publication is performed by this task.


Status: all implementation slices are complete. PostgreSQL/session and browser checks passed before final refinements; latest typecheck, engine/config tests, endpoint checks and production bundles pass. Docker image/runtime verification remains incomplete after npm timeouts and permission-review timeouts. See tests/RESULTS.md for precise outcomes.

## Live table controls and session recap

1. Add persisted next-hand participation and GM removal/restoration without deleting seats or ledger history. A live removal folds the target immediately; completed hands remain immutable. Players cannot undo a GM removal themselves.
2. Keep the last public turn recap on the server, with no cheat details or hidden faces; render it above the turn indicator.
3. Add reusable browser/extension-local NPC templates (name, opening GP, Dexterity), and explain audited NPC queues in the UI and documentation.
4. Show final balances/net in the main game area when the GM ends a session.
5. Verify money conservation, arbitrary-seat removal, turn advancement, authorization, old-room compatibility, retries/reload, preset persistence, final summary, responsive layout, and production web/extension builds. No production database or deployment changes.

Live table slice status: implemented and verified. SQLite/PostgreSQL suite: 90 passed, 1 expected skip; eight browser scenarios pass across full/targeted runs. TypeScript, endpoint checks and live-endpoint production bundles pass. No production deployment or game-data mutation performed.

## Automatic queued NPC rerolls

Extend queued hands with validated rerollIndexes and a matching replacement list. Execute due scripted NPC rerolls server-side after normal commands, in seat order and within the same transactional receipt. Stop at human/manual turns; handle chained NPCs and automatic standing pat. Keep plans/faces and detailed execution audits GM-only, publish only ordinary reroll counts, preserve opted-out queues and loaded-die odds, and leave old entries without selections manual. Update instructions/examples, test validation/privacy/retries/reload/order, and rebuild production site/extension. No live deployment or game changes.

Automatic reroll status: complete. Full SQLite/PostgreSQL suite 111 passed (1 expected skip), all 9 browser scenarios passed, TypeScript and 12 endpoint checks passed. Production web/extension bundles and ZIP verified; no deployment or production data changes.

## Belwether streamlined room access

Add a persistent server-side belwether alias pointing at the current room, with separately hashed remembered DM credentials and retained previous room ledgers. Player alias joins keep name/gold/Dexterity but need no room/invite entry, with durable idempotent join recovery. Require the existing host secret once per DM device; isdm=1 only chooses UI mode. A fresh session requires an ended prior session and uses serialized/idempotent campaign commands. Make the extension default to this room, keep extension credentials in isolated storage, and support the stable website link and legacy manual recovery. Verify unauthorized DM access, concurrent session creation, retries, session switching, refresh/reconnect, private projections and built overlay; update deployment/setup docs and production bundles. No live state changes or deployment.

Belwether status: implemented. Full SQLite/PostgreSQL suite: 123 passed, 1 expected skip; full Chromium suite: 12 passed. TypeScript, endpoint checks, production website/extension builds and ZIP verification passed. No deployment or production-data mutation performed; final targeted browser verification is recorded in tests/RESULTS.md.
