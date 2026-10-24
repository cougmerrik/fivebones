# Paste into Codex

Build **Five Bones**, a small fantasy tavern dice-poker multiplayer game for a Roll20 D&D campaign. The product must work as a **standalone hosted web app**, and its same interface must optionally appear as a floating, movable, resizable Chrome/Edge Manifest V3 **overlay inside Roll20**. Roll20 is on the **free tier**: no Roll20 Mod scripts, paid APIs, sheet edits, or prohibited internal endpoint use.

Read all files in this repository starting with `AGENTS.md`, `spec/PRODUCT.md`, `spec/RULES.md`, `spec/ARCHITECTURE.md`, `contracts/PROTOCOL.md`, `tests/ACCEPTANCE.md`, and `spec/DEPLOYMENT.md`. Treat them as the product contract.

Implement a playable MVP **now**, not a proposal. The MVP must support:

1. A GM creating a room with an invite code and joining as host; five human players (and optionally NPCs) joining with per-seat permissions; secure reconnection; a spectator or disconnected state without leakage.
2. Server-authored 5d6 hidden first rolls, a phase of fixed-limit betting, **exactly one opportunity** to reroll any 0–5 dice while keeping the number rerolled public, another fixed-limit betting phase, then showdown. Enforce hand ranks, tied hands, and the Widowmaker rule exactly as documented. GM advances NPCs using the same game engine; NPC predetermined dice sequences allowed only through audited GM controls.
3. User interface with animated but cosmetic dice, hold/reroll controls, ante/call/raise/fold/check as appropriate, a room roster and pot, turn status, private hand, showdown results, and a clear game log. Never use client-generated RNG for authoritative rolls.
4. A ledger per player with **starting GP entered manually (or optionally imported read-only)**, per-hand deltas, net gain/loss, expected final GP, and copyable settlement summary. No sheet writes. Fixed-limit table stake presets and optional silver-piece denominations; internal amounts use integer copper pieces to avoid floating precision.
5. Standalone web UX with polished rustic/tavern styling that works in desktop browsers; same interface rendered in a Roll20-injected Shadow DOM window. Overlay must be collapsible, movable, and remember local position. If extension fails, use the standalone app.
6. Optional 2014 Roll20 read-only importer: on user command inspect only an opened sheet for visible `name="attr_character_name"` and `name="attr_gp"` values (and optionally other visible coins if explicitly chosen). Be frame-aware and permission-limited; if sheet cannot be read, provide manual entry. Never write, submit, manipulate Roll20 state or read authentication.
7. Production-appropriate authorization, secure WebSocket transport, event acknowledgments, idempotency, reconnect recovery, tests, deployment instructions, and a locally reproducible dev environment.

**Rules discipline:** `spec/RULES.md` distinguishes settled rules from unresolved specifics. Do not invent canonical tie-break or settlement behavior silently. For ambiguous cases, choose a *labeled and configurable MVP house default* consistent with dice poker, make it easy to change, and document it in README and tests. Skills are explicitly optional: no skill action may manipulate a legitimate dice result. Prefer postponing skill actions and full tournament automation to post-MVP unless time permits.

**Execution path:**

- Phase 0: inspect environment, write short plan and traceability checklist.
- Phase 1: implement rules and deterministic unit tests; cover Widowmaker, ranking precedence, betting constraints, ties, uncontested wins, fixed-limit cap and reroll count.
- Phase 2: implement room server, state machine, wallet/ledger with idempotent commands and reconnect behavior. Test redaction for every role.
- Phase 3: implement a responsive standalone client that can play full human-vs-human and human-vs-GM NPC hands locally.
- Phase 4: wrap the same client in a MV3 Roll20 overlay. Provide installation build artifacts or build output instructions. Manual GP entry and Roll20-import fallback always work.
- Phase 5: deliver Docker/dev commands, deployment notes, e2e scenarios and known limits; run tests and fix failures.

**Definition of done:** GM + 5 browser sessions can complete multiple consecutive hands, with an NPC seat, fixed-limit betting and reconnect, balances reconcile, one player can encounter Widowmaker, no private dice leak, and the same UI runs separately in a browser tab and in an injected Roll20 overlay. The GM can export a session ledger. Return a summary of files created, commands actually run, passing/failing tests, unresolved rules defaults, and the URL or steps to launch it. Do not falsely claim live Roll20 testing unless it was actually performed.
