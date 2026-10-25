# Reference technical architecture

## Monorepo shape

```text
web/               React/Vite standalone app
extension/         Chrome/Edge MV3 content script wrapper + build
packages/ui/            Shared React game table and hooks
packages/contracts/     TypeScript wire types and validation
server/app/             FastAPI app, websocket, persistence, game state machine
server/tests/           pytest rules and API integration tests
docs/                   Development and deployment instructions
infra/                  Optional reverse-proxy example
```

Game rules live on server only. Client may evaluate *display-only* hints but cannot validate authoritative state.

## Server state machine

LOBBY -> ANTE_COLLECTION -> FIRST_ROLL -> BETTING_1 -> REROLL -> BETTING_2 -> SHOWDOWN -> SETTLEMENT -> READY_NEXT_HAND.

Special transitions: FOLD -> remaining active <2 => UNCONTESTED_WIN; every state can restore from server snapshot following reconnect. Need adjudication if showdown contains only Widowmakers, and underfunded seats cannot enter hand. Enforce active seat membership and acting turn server-side. Each state transition transactionally updates room, balances, hand events, and replay log.

## Security & privacy

- Host issued non-guessable room secret and separate per-seat unguessable tokens. The public room code isn't authentication.
- Server authorizes all commands by seat token and room membership. GM features require GM host role with distinct credential; nothing in UI alone is authorization.
- WSS and HTTPS in deployment. Minimal local development exceptions. Rate-limit join / command traffic; input validate names and amounts; cap room size and NPC lists.
- JSON serialization of each client view explicitly redacts hidden dice, held dice, NPC scripted queues and host keys. Include adversarial tests that inspect serialized messages, not only React UI.
- Dice RNG uses server `secrets.randbelow(6)+1`; scripted GM dice use audited data. All bet and payout maths use integers in cp.
- Idempotent command IDs: client retry/reconnect must not duplicate ante/bet/reroll/settlement. Optimistic version and mutex/DB transaction for room writes.
- Add heartbeat/reconnection and snapshot/event sequence numbers. Persist active room so application restart doesn't wipe ledger (at minimum SQLite).
- Do not store Roll20 character details other than user-authorized display name and starting GP. Do not store passwords/cookies from Roll20.
- Extension CSP: local bundled JS/CSS only; `connect-src`/host permissions for configured WSS server, no remote code injection. `chrome.storage.local` for overlay layout and chosen endpoint/seat token as appropriate; do not expose tokens to page global scope.
- Consider server access logs and per-room retention. Provide GM delete/export function and document retention policy.

## Browser overlay implementation

- MV3 content script matches scoped Roll20 game pages; only insert UI in top window, avoid duplicate mounts.
- Isolated world + shadow root on one owned host node; all styling contained in own stylesheet. No patching Roll20 JS objects, private APIs, websocket messages or network requests.
- Share `FiveBonesApp` between website and extension; extension supplies auth/session config and wrapper window.
- Read-only sheet adapter is *optional* and guarded by an explicit user action. For frame separation, minimally permissioned frame script sends only `{name, gp}` when matching sheet is visible. Verify real DOM in manual test before claiming supported integration. If absent, fall back to entry fields.
- Use tight domain match patterns and explicit local configuration for API origin; production host must be documented. Avoid universal `<all_urls>` permissions.

## Persistence model (minimal)

Room(id, public_code_hash, gm_token_hash, game_config, version, phase, dealer_seat, created_at)
Seat(id, room_id, role, display_name, player_token_hash, opening_balance_cp, active_balance_cp, connected_at)
Hand(id, room_id, hand_no, phase, dealer_seat, current_actor, pot_cp)
HandSeat(hand_id, seat_id, status, original_dice_private, final_dice_private, reroll_indexes_private, committed_cp, reroll_count_public)
Event(room_id, seq, hand_id, actor_id, event_type, public_payload, private_payload, created_at, command_id)
LedgerEntry(room_id, hand_id, seat_id, entry_type, amount_cp, created_at)
NPCQueue(room_id, seat_id, scripted_values_encrypted_or_access_restricted, gm_only)

Exact schema is flexible, but must support reconnect, replay, audit and accounting. Avoid leaking private data in exported public logs.


## Implemented persistence / production topology

The implementation stores a room aggregate and hashed credentials in a transactional rooms table, rather than separate tables for each conceptual entity above. PostgreSQL via DATABASE_URL is required for production; SQLite remains available locally. Room writes use PostgreSQL row locks or SQLite immediate transactions, including durable per-credential command receipts. Deploy one API replica/worker because live socket fan-out is process-local. Web and API have independent Dockerfiles/Railway configs; both use the repository root build context. See [RAILWAY_DEPLOY.md](../RAILWAY_DEPLOY.md).


The optional permanent Belwether campaign entrypoint stores a transactional alias/current-room mapping, hashed DM credentials and start receipts in a separate campaigns table. Player joins use private retry keys to recover the same seat, and campaign DM authority remains server-verified. Ordinary rooms, private projections and ledger state machines are unchanged; previous sessions are retained. See contracts/PROTOCOL.md for endpoints.
