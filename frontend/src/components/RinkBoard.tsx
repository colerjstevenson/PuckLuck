import type { LineupSlot, PlayerCard } from "../types";

const SLOT_ORDER: LineupSlot[] = ["F1", "F2", "F3", "D1", "D2", "G"];

const SLOT_LABELS: Record<LineupSlot, string> = {
  F1: "F",
  F2: "F",
  F3: "F",
  D1: "D",
  D2: "D",
  G: "G",
};

type RinkBoardProps = {
  lineup: Partial<Record<LineupSlot, PlayerCard>>;
  onSlotAction: (slot: LineupSlot) => void;
  selectedPlayerId: string | null;
  selectedLineupSlot: LineupSlot | null;
};

export function RinkBoard({ lineup, onSlotAction, selectedPlayerId, selectedLineupSlot }: RinkBoardProps) {
  return (
    <section className="rink-shell" aria-label="Lineup rink">
      {SLOT_ORDER.map((slot) => {
        const player = lineup[slot];
        const hasSelection = Boolean(selectedPlayerId || selectedLineupSlot);
        const isMoveTarget = Boolean(selectedLineupSlot && !player);
        const isSelectedLineupSlot = selectedLineupSlot === slot;
        return (
          <div
            key={slot}
            className={`rink-slot slot-${slot}${hasSelection ? " has-selection" : ""}${isMoveTarget ? " move-target" : ""}${isSelectedLineupSlot ? " is-selected" : ""}`}
            onClick={() => onSlotAction(slot)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSlotAction(slot);
              }
            }}
            role="button"
            tabIndex={0}
          >
            <div className="slot-top-row">
              <span>{slot}</span>
              <span className="slot-type">{SLOT_LABELS[slot]}</span>
            </div>
            {player ? (
              <button
                type="button"
                className={`slot-player${isSelectedLineupSlot ? " is-selected" : ""}`}
                onClick={(event) => {
                  event.stopPropagation();
                  onSlotAction(slot);
                }}
                title={isSelectedLineupSlot ? "Selected. Click an empty slot to move this player." : "Click to select this player for moving."}
              >
                <strong>{player.name}</strong>
                <span>{player.positionGroup}</span>
              </button>
            ) : (
              <p className="slot-empty">{selectedLineupSlot ? "Move here" : "Pick player"}</p>
            )}
          </div>
        );
      })}
    </section>
  );
}
