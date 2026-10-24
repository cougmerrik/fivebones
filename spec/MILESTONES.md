# Milestones / exit gates

**M0 Design/traces**: Schema, legal transitions, house defaults recorded. Identify host/iframe constraints before any Roll20 integration work.

**M1 Rules**: rank evaluator, Widowmaker, seat turns, two rounds of fixed-limit betting, reroll 0–5 exactly once, uncontested wins and settlement all covered with deterministic tests.

**M2 Server**: room creation/join, private seat tokens, audited GM NPC control, persistence, redacted WebSockets, idempotency. API security tests pass.

**M3 Website**: functional GM + five players through three hands, balance/ledger/copy CSV and reconnect. No extension needed.

**M4 Browser extension**: MV3 builds, overlay mounts with no Roll20 internals, shadow-root style isolation, same client view, drag/minimize/persist. Manual sheet import is optional; manual entry is nonoptional.

**M5 Release**: Docker deployment, install guide, sample env, known limitations, end-to-end test run.

**Later**: GM-configurable skill actions, riverboat tournament advancement based on total winnings, custom NPC dialogue/behavior, public chat summaries, art/audio polish. Do not trade core correctness for these.
