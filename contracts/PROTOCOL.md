# Transport contracts — proposed v1

Clients use HTTPS endpoints to create/join rooms and a WSS connection for state and commands. Types are illustrative; implement runtime validation on server and frontend.

## HTTP

- `POST /api/v1/rooms`: host creates table, returns `roomId`, invite code, host token (secret) and joining URL. Rate limit.
- `POST /api/v1/rooms/{id}/join`: join code + name + starting amount cp -> private seat token and ID; require available human seat.
- `GET /api/v1/health`: readiness.
- `GET /api/v1/rooms/{id}/ledger.csv`: GM-authenticated only; export event derived ledger.
- `POST /api/v1/rooms/{id}/delete`: authenticated GM action with confirmation.

## WebSocket

`/api/v1/rooms/{id}/ws?` Avoid tokens in URL query; authenticate with first message or supported header and TLS. Socket initializes `authenticate {seatToken}` and gets a **role-specific** `snapshot`.

Commands: `{type:"command", id:"uuid", expectedVersion:42, action:"bet"|"call"|"raise"|"check"|"fold"|"setReroll"|"startHand"|"takeNPCAction"|"adjudicate"|"endSession", data:{...}}`.

Response: `{type:"ack", id:"uuid", accepted:true|false, roomVersion:43, errorCode?:"WRONG_PHASE"|"NOT_YOUR_TURN"|"INSUFFICIENT_FUNDS"|"CONFLICT"|"UNAUTHORIZED"}`.

Event: `{type:"event", seq:102, name:"betPlaced"|"rerollCount"|"showdown"|"settlement"|..., public:{...}}`; private seat data should be separate `private` response to authorized socket only. Snapshot includes public phase/pot/roster/commitments/turn, and **only own** dice, own held flags and private actions. The GM is **not** automatically permitted to read unrevealed human dice.

## Commands and constraints

- `setReroll {indexes:[0,2,4]}` is one-shot per hand, index range 0..4, unique indexes, max 5, current actor only. Server generates replacements and publishes reroll **count** but not faces/indexes.
- `bet/call/raise`: server computes exact cp amount from fixed-limit config and current commitment; do not accept arbitrary amount from client.
- `fold`: never reveal folded dice; if only one active seat remains, award pot without showdown.
- `startHand`: GM only, enforce sufficient ante and minimum qualifying entrants, rotate dealer.
- `takeNPCAction`: GM only, only active NPC current actor; validation applies to NPC too.
- `adjudicate`: only for explicit exceptional state with logged reason; cannot edit human dice.

## Ledger invariants

Every money transfer has an explicit event, using integer cp. For every hand `sum(seat balance deltas) == 0` when house rake is zero, including antes/bets and payouts. Pot = committed contributions not yet distributed. Net P/L = ending game money minus starting game money. UI may show an independent Roll20 snapshot and copy its suggested final value; warn when player changed their Roll20 gold independently during the session.

## Redaction fixture

For a player, serialize opponent seat state as `{id, displayName, folded, commitmentCp, rerollCount}` only. Never include `dice`, `rerollIndexes`, scripted queue, host token, other seat token, hidden hand result, or sensitive database IDs in public event bodies. Show revealed dice only when participant is legally exposed at showdown.

## Implemented MVP details

The executable contract lives in `server/app/main.py` (strict Pydantic envelopes and action-specific data allowlists) and `packages/contracts/index.ts` (client projection validation). HTTP names use the fields above; all room creation/join responses use `seatToken`, including GM credentials. Creation additionally accepts `name`, `smallBetCp` (10, 100, 1000), optional `anteCp`, `ties`, `remainder`, and `hostSecret`. Join accepts `spectator:true` to issue a read-only credential without seating a player.

The MVP sends complete role-specific `snapshot` frames after accepted/rejected commands and connectivity changes. `state.events` embeds the ordered public event log with monotonic `seq`; separate incremental event/private frame delivery is deferred. The private hand is included only in its authorized snapshot projection. `ping` yields `pong`; clients reconnect and reauthenticate to recover snapshots. Tokens are never URL parameters.

Phases FIRST_ROLL/ANTE_COLLECTION/SHOWDOWN/SETTLEMENT are atomic transitions inside a command. Stable phases are LOBBY, BETTING_1, REROLL, BETTING_2, ADJUDICATION, READY_NEXT_HAND. Showdown dice and rank labels stay visible in READY_NEXT_HAND for nonfolded showdown participants. Uncontested settlements do not reveal opposing dice. Active-seat connected flags are transport-derived, not game actions; they do not increment room version or cause automatic folds.

`forceFold {confirmed:true}` requires GM authority and acts only on the current seat; UI asks the GM to explicitly confirm. `adjudicate {reason}` only refunds original contributions in ADJUDICATION. `scriptNPC {seatId,queue:[{initial:[1,2,3,4,5],replacements:[6]}]}` is GM-only, retains a private audit record and never modifies human dice. `takeNPCAction {action,data:{...}}` wraps only ordinary legal actions for the current NPC.

Unknown action-data keys are rejected (including supplied amounts, winners or dice arrays in ordinary commands). Explicit cheat/GM-edit commands below allow validated die slots/faces under the campaign amendment. Command receipts are scoped to authenticated credentials and command ID and persist across restarts. Reusing an ID returns its original acknowledgment; a rejected command requires a new ID after addressing its error. Stale expectedVersion yields CONFLICT without a monetary mutation. Successful commands increment room version once.

The ledger CSV contains individual signed transfers, HAND_NET rows by hand/seat, and TOTAL rows with opening, current and net copper. During an unfinished hand, current balances exclude coins committed to the pot. Export requires a GM bearer credential; public exports never include private NPC audit/scripts or folded dice.

## Private cheat commands (campaign amendment)

Join accepts optional `dexterity` (strict integer 1–30); the UI requires it for new humans. Legacy clients may omit it and add it through `setAbilities {dexterity}`. Existing scores are immutable throughout the session (`DEXTERITY_LOCKED`), even between hands. Only a missing legacy score may be initialized once, before a hand or on one’s active turn. Scores are sent only to the owner and GM. No Charisma field is accepted.

- `requestCheat {kind:"loadedDie",dieIndex:0}`: own active human turn, once per hand; rolls a server Dexterity check and applies the loaded die immediately. Exact five probability = 165/500; every other face = 67/500. The slot stays loaded for the hand's normal reroll. No GM approval gate.
- `requestCheat {kind:"changeDie",dieIndex:0,face:6}`: same limits; applies the requested face immediately and rolls a private Dexterity check.
- `requestCheat {kind:"other",description:"..."}`: own turn, once per hand; a trimmed 1–500 character description and no automatic check/effect.
- `rollCheatCheck {requestId:"1",ability:"dexterity"}`: GM only; a pending Other action may receive one server check. No client-supplied d20 or total is accepted.
- `resolveCheat {requestId:"1",decision:"noted",reason:"..."}`: GM acknowledgement of an applied action or narrative adjudication of Other; a trimmed reason (1–500 characters) is required. This is never an approval gate for Loaded die or Change die.
- `gmChangeDie {seatId:"2",dieIndex:0,face:6,reason:"..."}`: GM only, current live hand and nonfolded target only; stores an audited individual-face change.

Snapshots add role-scoped `cheatRequests` and `diceChanges`; opponent/spectator lists are empty. Own/GM seat projections may include `abilities` and `loadedIndexes`. GM still cannot inspect an entire unrevealed human hand. Only selected changed faces appear in the private audit. No cheat details are appended to public events or the ordinary ledger CSV. Each command uses the existing optimistic version, transactional write and durable receipt semantics. Changes never advance turn or move coins. In-play pending notifications expire at folds/settlement; history remains private and durable.

### NPC cheating and immutable Dexterity update

- `addNPC {name,startingCp,dexterity}` is GM-only and validates both starting money and Dexterity before creating a seat. Omitted Dexterity defaults to 10 for compatibility. Starting money sets opening/current balance; it is not a mid-session money-edit action.
- `requestNPCCheat {kind,dieIndex?,face?,description?}` is GM-only and targets only the current NPC actor. It shares human cheat validation, one attempt per hand, immediate effects, exact 33%-five loaded die, and server d20 + NPC Dexterity modifier. Attempts/results/audits are visible only to the GM; ordinary players/spectators get empty private lists. Clients cannot supply d20/check totals.
- `setNPCDexterity {seatId,dexterity}` is a GM-only, one-time initialization for an NPC with no score; an existing score cannot be edited. It cannot target a human.
- `setAbilities {dexterity}` may only initialize a missing human score. Existing values cannot be replaced, including in LOBBY or READY_NEXT_HAND.

All new NPC actions retain optimistic version checks and durable, per-credential command receipts. Repeating the same NPC cheat command ID returns its original acknowledgement without rerolling the check or loaded die.

## Live table controls

- `setParticipation {participating:boolean}`: seated humans change their own persistent next-hand preference. GM may supply `seatId` for any nonremoved human/NPC. Players cannot supply another seat ID; spectators cannot participate. No active hand is changed.
- `removeSeat {seatId,confirmed:true}`: GM-only; folds a live target during betting/rerolls, retains all wagers/history, excludes it until restored. Does not delete credentials. Rejects during ADJUDICATION.
- `restoreSeat {seatId}`: GM-only; restores eligibility for future hands, never returns to the current hand.

Snapshots include public seat `nextHand` and `removed` flags; old rooms default to true/false. `lastTurn` is a server-authored public recap that survives reconnect/restart. Private actions do not update this field. Existing receipt/version semantics apply to all controls.

NPC presets are browser/extension-local configuration templates with name, opening gold, and Dexterity. They contain no tokens, live balances, hidden dice, or scripts; seating a template still uses the GM-authorized server command. Web uses localStorage; the extension uses isolated chrome.storage.local.
