# GitHub / Railway implementation plan

1. Preserve the working game while moving the inspected apps into /web and /extension, retaining /server and shared /packages.
2. Compact DM notifications and align the rules button with the selected phase chip.
3. Add DATABASE_URL persistence with PostgreSQL transactional room locks; retain SQLite development and existing room format.
4. Add independent PORT-aware Docker/Railway services, explicit endpoint/origin configuration, health and restart handling.
5. Produce the unpacked extension and ZIP; document GitHub/Railway setup, variables, database operations and limits.
6. Test rules/API against SQLite and an actual local PostgreSQL, production images, WebSocket recovery, browser flows and ZIP contents. Record actual results and manual cloud setup gates.

Production remains one API replica/worker for 5–8 seats. Database row locks protect commands, and deploys close sockets so clients recover from persistent snapshots. No Railway account deployment or GitHub publication is performed by this task.


Status: all implementation slices are complete. PostgreSQL/session and browser checks passed before final refinements; latest typecheck, engine/config tests, endpoint checks and production bundles pass. Docker image/runtime verification remains incomplete after npm timeouts and permission-review timeouts. See tests/RESULTS.md for precise outcomes.
