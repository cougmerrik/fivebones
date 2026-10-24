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
- GM can authorize up to ten NPC scripted initial rolls, each with up to five replacement faces. Partial replacement streams fall back to secure RNG. Script authorization retains a durable GM-only audit record; public log contains authorization metadata only. Human dice cannot be scripted. NPC decisions are manual GM actions, not an automated betting strategy.
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
