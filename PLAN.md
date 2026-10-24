# Implementation trace

- M0: Read all product contracts. Persist one transactional SQLite JSON aggregate per room, hashed bearer credentials, redacted projections, sequenced public log, command receipts and ledger.
- M1: Pure Python rank/betting/reroll/settlement state machine with deterministic tests.
- M2: FastAPI HTTP and authenticated WebSocket transport, SQLite persistence, optimistic versions and durable idempotency.
- M3: Shared React table: manual identity/GP, GM/NPC controls, bets, rerolls, ledger and reconnect.
- M4: Same React application in an isolated MV3 Shadow DOM, movable/resizable/minimized layout. Optional sheet import deferred; manual entry always works.
- M5: Build, integration/browser checks, Docker, setup and honest acceptance report.

House defaults follow spec/RULES.md. Configurable ante, kicker-versus-category ties and remainder direction; all Widowmakers pause for GM refund adjudication (no client-selected payouts). Skills/tournament deferred.

## Delivered trace

- M0: Complete. Original contracts reviewed; aggregate schema, state transitions, defaults and security boundary documented here, in README and contracts/PROTOCOL.md.
- M1: Complete. Pure engine; all ranks, Widowmaker, betting cap, one-shot rerolls, insufficient funds, deterministic tie/remainder behavior and conservation verified.
- M2: Complete. SQLite authority and durable receipts; strict role/data checks; hashed tokens, redacted authenticated WebSockets, CSV/delete operations, offline host rotation/purge.
- M3: Complete. Six browser contexts (GM + five humans), one NPC and three hands pass. Reload, disconnect with confirmed force-fold, recovery, clipboard and ledger flows covered.
- M4: Built. Same React app, isolated storage, closed Shadow DOM, scoped MV3 launcher, move/resize/minimize/persistence. Simulated-host Chromium mounting, overlay-to-standalone synchronization, and extension session recovery passed. Live Roll20/Edge manual gate remains; optional sheet importer intentionally omitted.
- M5: Development/build/test and container deployment instructions supplied. Docker images build and the running containers pass actual API restart/private-state recovery/idempotent retry checks; evidence is recorded in tests/RESULTS.md.

No skill actions, tournament automation, demo accounts, dev reset HTTP routes, sheet writes or Roll20 internal access were added.
