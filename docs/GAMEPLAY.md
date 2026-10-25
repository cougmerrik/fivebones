# Gameplay and campaign conventions

Five Bones uses fictional campaign gold. The authoritative rules are in [spec/RULES.md](../spec/RULES.md); the conventions below describe the implemented table.

## House defaults (explicit, not campaign canon)

- Ante equals small bet; first round uses small bet, second round big bet. Presets: 10/20, 100/200, 1000/2000 cp. Internal money is integer copper (100 cp = 1 gp).
- First dealer is first seated player; dealer rotates through all seats. Action starts clockwise to dealer's left, skipping folded/ineligible seats. Rerolls use the same order.
- A bet opens a round; at most two raises total per round. Everyone must act and match or fold. No all-ins, partial calls, credit, or side pots. Only seats with a positive balance and enough ante enter. A seat can spend its last coins on an ante, then check or fold if it cannot afford a call.
- Best hand uses lexicographic kickers from [spec/RULES.md](../spec/RULES.md). Exact ties split equally; spare copper goes clockwise from dealer among tied winners.
- Widowmaker is exactly 6,6,6,1,1. It loses to every non-Widowmaker at showdown, but wins uncontested. All-Widowmaker showdowns pause for GM adjudication: the MVP adjudication refunds each contribution, requires a reason, and logs it. Arbitrary client-selected payouts are never accepted.
- Configuration is fixed per room. Creation API accepts `anteCp` (0 through small bet), `ties` (`kickers` or `category`) and `remainder` (`clockwise` or `counterclockwise`); the host form exposes these options. Core conventions are centralized in `server/app/engine.py`; future campaign decisions can replace them with tests.
- Disconnect never causes an automatic action. A disconnected actor pauses the game. The GM can explicitly confirm a force-fold. Reconnect restores the seat's private state.
- GM can authorize up to ten NPC scripted initial rolls, each with up to five replacement faces. Partial replacement streams fall back to secure RNG. Script authorization retains a durable GM-only audit record; public log contains authorization metadata only. Human dice cannot be scripted. NPC wagers are manual GM actions; explicitly queued reroll selections may execute automatically. There is no automated betting strategy.
- Skills, tournament automation, optional sheet import, sound and NPC personalities are deferred.

## Private cheating and DM adjudication

This campaign update explicitly supersedes the original prohibition on human-dice changes **for the actions below**. Ordinary dice, checks, bets and payouts remain server-authoritative.

- Human players enter Dexterity at join. The check is **1d20 + floor((Dexterity − 10) / 2)**; there are no Charisma checks. Scores and checks are private to their owner and the DM. Dexterity is locked for the entire room session after joining or one-time initialization, including between hands. Legacy seats can add a missing score once on their turn; they cannot replace an existing score.
- One cheat action per seat per hand, on that seat’s own turn during either betting round or rerolls. Sending it keeps the same actor and does not place a wager or consume the ordinary reroll opportunity.
- **Loaded die:** swap and roll a selected die immediately, without DM approval. Five has exactly **33%** probability; each other face has **13.4%**. The DM receives a private swap check and before/after notification. The chosen slot remains loaded during that hand's normal reroll; all dice reset to fair dice next hand. These lifetime/other-face distribution details are explicit implementation conventions.
- **Change die:** choose a slot and face; the server applies it immediately and sends a private Dexterity check and notification to the DM. The check does not automatically decide success, detection, or consequences.
- **Other:** describe the action privately to the DM. It does not roll or change dice automatically. The DM can request one server-rolled Dexterity check, record adjudication, or use the separate dice-change controls. Consequences are decided out of game.
- The DM can change an active, nonfolded seat's individual dice during a live hand. A reason is required. Private audit records retain actor, hand, slot, old/new face and reason. The owner sees their changes; opponents and spectators see neither requests, scores, checks nor edits before legal showdown. The DM's editing controls do not expose an entire unrevealed human hand.
- Requests, notifications and edits persist across reconnect and server restart. Durable command receipts prevent duplicate checks/swaps/edits on retry. No edits to completed hands, folded hands, balances, winners, or payouts are allowed through these controls. The ordinary ledger CSV contains no cheat details.

Use **Private actions** on a player's screen and **DM private actions** on the host's screen. On an NPC turn, the host also sees **NPC private actions** with the same server-rolled Dexterity checks and cheat choices. NPC attempts are GM-only, privately audited, and hidden from human opponents. At NPC creation, the host enters independent **NPC starting GP** and **New NPC Dexterity** values; these do not use the human join-form gold. New NPC Dexterity defaults to 10, is validated in 1–30, and locks when seated. A legacy NPC can have a missing score initialized once by the DM on its turn. The host can acknowledge an already-applied cheat or record an Other adjudication; acknowledgment is not an approval gate. Pending Other requests expire at hand end or when their owner folds. Completed notifications remain in private history. “Hold” and “Reroll” captions appear only during the reroll phase.

## Table layout

Connection status sits at the top right of the Connection & room panel header, visible even when collapsed. The room panel now follows private actions; compact per-seat ledger boxes stay above the game: `Merrik 120g (-5g)`. Each box shows current gold and net change from its opening snapshot. Negative net is red, positive is bright green, and zero is neutral. Values update on wagers and settlement, including live committed wagers. Full transactions, copyable settlements and GM CSV export remain in the Ledger tab.

The connection/room panel contains room credentials without a duplicate table title. It starts collapsed for players on join/reload and expanded for the host; players can expand it to access recovery and leave controls. There is no bottom tagline. The main title uses the supplied `title.png`, bundled locally for the website and extension, displayed 25% smaller than the previous layout (450px maximum). The header divider is removed, and Hands & rules sits at the game area’s top right; it remains available in the entry panel before joining. The End session control is enabled in the lobby and between completed hands, with a normal confirmation and continued ledger access; during a live hand it is disabled with an explanation to finish or adjudicate that hand.

Dice visuals use the supplied root assets `pip1.png` through `pip6.png`, bundled locally for the website and extension. The shared renderer shows those images in private hands, visible roster hands and the rules examples. Dice-button labels and reroll selection remain accessible; authoritative face values still come from the server.

The game area shows `Ante → Betting 1 → Reroll → Betting 2 → Showdown → Next Hand`, with the server’s current stage highlighted and the current hand centered beneath it. Ante preparation maps to the lobby; ordinary ante/roll/showdown/settlement operations are atomic server transitions, so normal hands move directly to the next stable stage. An all-Widowmaker adjudication highlights Showdown until the GM resolves it. No client timer delays actions or changes authoritative phases.

On wide app surfaces, private actions sit beside the compact table so they can remain visible with the title. Narrow app/extension panels stack them below the table. The private sidebar can scroll independently when its contents grow. Roster dice are centered within their seat cards. Connection & room follows the private-action area, retaining its collapsed player default and right-aligned status.

## Participation and absent players

The blue button at the left of the game toolbar lets a player choose **Sit out next hand**. When sitting out, the purple **Join next hand** button opts back in. The preference persists across hands and reloads. Using it during a live hand does not fold the current dice or remove existing wagers. Roster cards show everyone's next-hand status; the GM needs at least two eligible participants to start.

The GM has per-seat **Remove … from play** and **Restore …** controls. Removing an active seat folds it immediately, preserves committed gold in the pot, and moves play along. It stays out until the GM restores it. The seat and its ledger remain available for settlement; restoring affects future hands only. Resolve an all-Widowmaker adjudication before removing a seat from that hand.

## Reusable NPC presets

Under **settings → Saved NPC presets**, fill in the NPC name, starting GP and Dexterity and click **Save NPC preset**. Choose a saved name and click **Load NPC preset** to fill the form, then **Seat NPC** to add it to this room. Saving an existing name updates that template. Templates persist across rooms in this browser or extension; website and extension storage are separate. They do not carry a previous NPC's final balance, dice, scripts, or active seat identity into a new game.

## Queued NPC rolls and automatic rerolls

1. Seat an NPC and open **settings → Authorize scripted NPC rolls (audit logged)**.
2. Select that NPC. Enter a JSON list, one entry for each future hand it will enter:

```json
[
  {"initial": [2, 2, 2, 4, 6], "rerollIndexes": [3, 4], "replacements": [2, 2]},
  {"initial": [1, 2, 3, 4, 5], "rerollIndexes": [], "replacements": []}
]
```

The first entry starts with three twos. When this NPC reaches its reroll turn, the server replaces **dice 4 and 5** with **2 and 2**, producing five twos. `rerollIndexes` is zero-based: 0 means die 1, 1 means die 2, through 4 meaning die 5. Each index is paired with the replacement at the same position. For example, indexes `[4, 1]` with replacements `[6, 3]` sets die 5 to 6 and die 2 to 3; no sorting is applied.

The second entry keeps its straight: empty indexes and replacements make it **stand pat automatically**.

3. Click **Authorize NPC queue**. This replaces the remaining queue and records the plan privately for the GM. Enter `[]` as the entire queue to clear it.
4. Start the next hand. Its first entry supplies the initial dice and that hand's reroll plan; sitting out does not consume an entry. The GM sees a private automatic-reroll indicator on the NPC card.
5. Continue making that NPC's betting decisions. When its reroll turn arrives, the **server executes the queued selection and replacements automatically**, then advances. Consecutive scripted NPCs are processed in seat order, stopping at a human or a manually controlled NPC. If everyone has rerolled, Betting 2 begins immediately. The GM still controls all betting, folding, and private cheat choices.

Each initial roll must contain exactly five integers from 1 through 6. An automatic plan needs zero through five unique indexes from 0 through 4 and **exactly one valid replacement face per index**. Missing or extra replacement faces reject the plan. Up to ten hands may be queued.

A loaded die retains its 33% chance of a five. Its paired scripted face is consumed but ignored; the next selected slot still gets its own paired replacement. Folded/removed NPCs never execute a reroll. Current-hand plans survive reload and are not changed by authorizing a different future queue. Automatic execution, turn advancement and audit are persisted in the triggering command's transaction, so reconnects and command retries cannot reroll twice. Opponents see only the normal reroll count; selections, faces and detailed audits stay GM-only until legal showdown.

**Existing queues:** entries without `rerollIndexes` retain the previous manual reroll and replacement-stream behavior. Add `rerollIndexes` and matching replacements to enable automation; the app does not guess which dice an old replacement stream was intended to replace. Legacy manual streams can still fall back to fair server dice when replacements run out.

## Turn and session recaps

**What just happened** appears above the current turn and describes the last public action. It uses the authoritative server state and never exposes private cheat details. When the GM chooses **End session** between hands, the main game area shows every participant's starting/final gold and signed net, with copyable settlement text and GM CSV download. Completed summaries survive reload.

## Joining the permanent Belwether room

The Roll20 extension supplies the room automatically. Players enter name, starting GP and Dexterity and press **Join belwether**. The standalone equivalent is `/?room=belwether`. No invite-code entry is needed for this campaign flow. A saved credential resumes an existing seat; name alone never recovers another player's seat.

The DM uses `/?room=belwether&isdm=1` or the overlay's **DM access** button. Enter the host invitation secret once per browser/extension surface and choose **Remember DM access**. The app remembers a derived DM credential, not the host secret. `isdm=1` selects the screen and is never authorization.

After finishing the current session, use **Start fresh belwether session**. The alias moves to a fresh ledger without deleting the old one. Players viewing a finished game get **Join new belwether session** and re-enter their character details/current gold. DM **Previous session summaries** retains the completed campaign results. Existing random-ID rooms can still be reached through manual connection/recovery.
