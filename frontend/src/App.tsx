import { useEffect, useMemo, useRef, useState } from "react";
import { fetchCategories, fetchEligible, fetchPlayers, scoreLineup, spinRound } from "./api";
import { CategoryTile } from "./components/CategoryTile";
import { RinkBoard } from "./components/RinkBoard";
import { ScoreModal } from "./components/ScoreModal";
import { useIsMobile } from "./hooks/useIsMobile";
import type { Category, GameMode, LineupSlot, PlayerCard, ScoreResponse, SpinResponse } from "./types";

const SLOT_SEQUENCE: LineupSlot[] = ["F1", "F2", "F3", "D1", "D2", "G"];
const SLOT_LABELS: Record<LineupSlot, string> = {
  F1: "F",
  F2: "F",
  F3: "F",
  D1: "D",
  D2: "D",
  G: "G",
};

type RinkBoardMobileProps = {
  lineup: Partial<Record<LineupSlot, PlayerCard>>;
  onSlotAction: (slot: LineupSlot) => void;
  selectedPlayerId: string | null;
  selectedLineupSlot: LineupSlot | null;
};

function RinkBoardMobile({ lineup, onSlotAction, selectedPlayerId, selectedLineupSlot }: RinkBoardMobileProps) {
  return (
    <section className="rink-mobile" aria-label="Lineup board">
      {SLOT_SEQUENCE.map((slot) => {
        const player = lineup[slot];
        const hasSelection = Boolean(selectedPlayerId || selectedLineupSlot);
        const isMoveTarget = Boolean(selectedLineupSlot && !player);
        const isSelectedLineupSlot = selectedLineupSlot === slot;

        return (
          <button
            key={slot}
            type="button"
            className={`rink-mobile-slot slot-${slot}${hasSelection ? " has-selection" : ""}${isMoveTarget ? " move-target" : ""}${isSelectedLineupSlot ? " is-selected" : ""}`}
            onClick={() => onSlotAction(slot)}
          >
            <div className="slot-top-row">
              <span>{slot}</span>
              <span className="slot-type">{SLOT_LABELS[slot]}</span>
            </div>
            {player ? (
              <div className="slot-player mobile-player-card">
                <strong>{player.name}</strong>
                <span>{player.positionGroup}</span>
              </div>
            ) : (
              <p className="slot-empty">{selectedLineupSlot ? "Move here" : "Tap to assign"}</p>
            )}
          </button>
        );
      })}
    </section>
  );
}

type PlayerListMobileProps = {
  filteredPlayers: PlayerCard[];
  gameMode: GameMode;
  slottedPlayerIds: Set<string>;
  invalidPlayerId: string | null;
  isGameOver: boolean;
  selectedPlayerId: string | null;
  onDraftPlayer: (player: PlayerCard) => void;
};

function PlayerListMobile({
  filteredPlayers,
  gameMode,
  slottedPlayerIds,
  invalidPlayerId,
  isGameOver,
  selectedPlayerId,
  onDraftPlayer,
}: PlayerListMobileProps) {
  return (
    <div className="player-list player-list-mobile" aria-label="Guided eligible player list">
      {filteredPlayers.length === 0 ? (
        <p className="empty-hint">No players loaded yet. Add a player to continue or start a new game.</p>
      ) : (
        filteredPlayers.map((player) => (
          <button
            key={player.id}
            className={`player-card player-card-mobile ${slottedPlayerIds.has(player.id) ? "selected" : ""}${invalidPlayerId === player.id ? " invalid" : ""}`}
            type="button"
            disabled={isGameOver}
            onClick={() => onDraftPlayer(player)}
            aria-pressed={selectedPlayerId === player.id}
          >
            <div className="card-main">
              <h3>{player.name}</h3>
              {gameMode === "classic" ? (
                <>
                  <p>
                    {player.position} | {player.birthCountry ?? "N/A"} | {player.stats.points} PTS
                  </p>
                  <p className="teams-line">{player.teamsPlayedFor.slice(0, 2).join(" / ") || "No teams"}</p>
                </>
              ) : null}
            </div>
          </button>
        ))
      )}
    </div>
  );
}

export default function App() {
  const modePickerThumbnail = `${import.meta.env.BASE_URL}thumbnail.png`;
  const isMobile = useIsMobile(768);
  const [gameMode, setGameMode] = useState<GameMode | null>(null);
  const [round, setRound] = useState<SpinResponse | null>(null);
  const [spinPreview, setSpinPreview] = useState<{ left: Category; right: Category } | null>(null);
  const [eligiblePlayers, setEligiblePlayers] = useState<PlayerCard[]>([]);
  const [allPlayers, setAllPlayers] = useState<PlayerCard[]>([]);
  const [eligibleCount, setEligibleCount] = useState(0);
  const [lineup, setLineup] = useState<Partial<Record<LineupSlot, PlayerCard>>>({});
  const [respinsLeft, setRespinsLeft] = useState(2);
  const [loading, setLoading] = useState(false);
  const [startingGame, setStartingGame] = useState(false);
  const [isSpinning, setIsSpinning] = useState(false);
  const [spinningSide, setSpinningSide] = useState<"left" | "right" | "both" | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);
  const [selectedLineupSlot, setSelectedLineupSlot] = useState<LineupSlot | null>(null);
  const [invalidPlayerId, setInvalidPlayerId] = useState<string | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [isGameOver, setIsGameOver] = useState(false);
  const [roundAdvancePending, setRoundAdvancePending] = useState(false);
  const categoriesRef = useRef<Category[]>([]);
  const finalScoreRequestedRef = useRef(false);
  const invalidPlayerTimeoutRef = useRef<number | null>(null);

  const playerPool = gameMode === "pro" ? allPlayers : eligiblePlayers;

  const selectedPlayer = useMemo(
    () => playerPool.find((player) => player.id === selectedPlayerId) ?? null,
    [playerPool, selectedPlayerId],
  );

  const eligiblePlayerIds = useMemo(() => new Set(eligiblePlayers.map((player) => player.id)), [eligiblePlayers]);

  const filteredPlayers = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) {
      return playerPool;
    }

    return playerPool.filter((player) => {
      const haystack =
        gameMode === "pro"
          ? player.name.toLowerCase()
          : [player.name, player.position, player.positionGroup, player.birthCountry ?? "", player.teamsPlayedFor.join(" ")]
              .join(" ")
              .toLowerCase();
      return haystack.includes(query);
    });
  }, [gameMode, playerPool, searchQuery]);

  const slottedPlayerIds = useMemo(() => new Set(Object.values(lineup).map((p) => p?.id).filter(Boolean)), [lineup]);
  const slottedCount = slottedPlayerIds.size;
  const previousSlottedCountRef = useRef(slottedCount);

  useEffect(() => {
    categoriesRef.current = categories;
  }, [categories]);

  useEffect(() => {
    const previous = previousSlottedCountRef.current;
    const increased = slottedCount > previous;
    previousSlottedCountRef.current = slottedCount;

    if (!increased || isGameOver || slottedCount === SLOT_SEQUENCE.length || loading) {
      return;
    }

    void spin();
  }, [isGameOver, loading, slottedCount]);

  useEffect(() => {
    if (slottedCount !== SLOT_SEQUENCE.length) {
      finalScoreRequestedRef.current = false;
      return;
    }

    if (isGameOver || loading || finalScoreRequestedRef.current) {
      return;
    }

    finalScoreRequestedRef.current = true;
    void submitScore({ endGame: true });
  }, [isGameOver, loading, slottedCount, lineup]);

  function randomCategoryPair(sourceCategories: Category[]): { left: Category; right: Category } | null {
    if (sourceCategories.length < 2) {
      return null;
    }

    for (let attempts = 0; attempts < 40; attempts += 1) {
      const left = sourceCategories[Math.floor(Math.random() * sourceCategories.length)];
      const rightCandidates = sourceCategories.filter((category) => category.group !== left.group && category.id !== left.id);
      if (rightCandidates.length === 0) {
        continue;
      }
      const right = rightCandidates[Math.floor(Math.random() * rightCandidates.length)];
      return { left, right };
    }

    return { left: sourceCategories[0], right: sourceCategories[1] };
  }

  async function spin(payload?: { keepSide?: "left" | "right"; keepCategoryId?: string }, options?: { resetRespins?: boolean }) {
    if (loading || isGameOver) {
      return;
    }

    setRoundAdvancePending(false);
    setLoading(true);
    setError(null);
    setIsSpinning(true);
    setSpinningSide(payload?.keepSide ? (payload.keepSide === "left" ? "right" : "left") : "both");
    setSelectedPlayerId(null);
    setSelectedLineupSlot(null);
    setSearchQuery("");
    if (options?.resetRespins) {
      setRespinsLeft(2);
    }

    const spinStartedAt = performance.now();
    const minimumSpinTime = 900;
    const spinInterval = window.setInterval(() => {
      const preview = randomCategoryPair(categoriesRef.current);
      if (preview) {
        setSpinPreview(preview);
      }
    }, 70);

    try {
      const nextRound = await spinRound(payload);
      const eligible = await fetchEligible(nextRound.left.id, nextRound.right.id);
      const elapsed = performance.now() - spinStartedAt;
      if (elapsed < minimumSpinTime) {
        await new Promise((resolve) => window.setTimeout(resolve, minimumSpinTime - elapsed));
      }
      setRound(nextRound);
      setEligiblePlayers(eligible.players);
      setEligibleCount(eligible.totalMatches);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to spin categories.");
    } finally {
      window.clearInterval(spinInterval);
      setSpinPreview(null);
      setIsSpinning(false);
      setSpinningSide(null);
      setRoundAdvancePending(false);
      setLoading(false);
    }
  }

  useEffect(() => {
    return () => {
      if (invalidPlayerTimeoutRef.current) {
        window.clearTimeout(invalidPlayerTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadCategories() {
      try {
        const nextCategories = await fetchCategories();
        if (!cancelled) {
          setCategories(nextCategories);
        }
      } catch {
        if (!cancelled) {
          setCategories([]);
        }
      }
    }

    void loadCategories();

    return () => {
      cancelled = true;
    };
  }, []);

  function placePlayer(slot: LineupSlot, playerId: string): { lineupCompleted: boolean } | null {
    if (isGameOver) {
      return null;
    }

    const player = eligiblePlayers.find((item) => item.id === playerId);
    if (!player) {
      return null;
    }

    if (lineup[slot]) {
      return null;
    }

    let lineupCompleted = false;
    setLineup((current) => {
      const next: Partial<Record<LineupSlot, PlayerCard>> = {};
      for (const key of SLOT_SEQUENCE) {
        const existing = current[key];
        if (!existing || existing.id !== playerId) {
          next[key] = existing;
        }
      }
      next[slot] = player;
      lineupCompleted = SLOT_SEQUENCE.every((lineupSlot) => Boolean(next[lineupSlot]));
      return next;
    });

    return { lineupCompleted };
  }

  function flashInvalidPlayer(playerId: string) {
    if (invalidPlayerTimeoutRef.current) {
      window.clearTimeout(invalidPlayerTimeoutRef.current);
    }
    setInvalidPlayerId(playerId);
    invalidPlayerTimeoutRef.current = window.setTimeout(() => {
      setInvalidPlayerId(null);
      invalidPlayerTimeoutRef.current = null;
    }, 850);
  }

  function draftPlayer(player: PlayerCard) {
    if (isGameOver) {
      return;
    }

    if (slottedPlayerIds.has(player.id)) {
      return;
    }

    if (gameMode === "pro" && !eligiblePlayerIds.has(player.id)) {
      setSelectedPlayerId(null);
      setSelectedLineupSlot(null);
      flashInvalidPlayer(player.id);
      return;
    }

    setSelectedLineupSlot(null);
    setInvalidPlayerId(null);
    setSelectedPlayerId(player.id);
    setSearchQuery(player.name);
  }

  function handleSlotAction(slot: LineupSlot) {
    if (isGameOver) {
      return;
    }

    if (selectedPlayer) {
      const placementResult = placePlayer(slot, selectedPlayer.id);
      if (!placementResult) {
        return;
      }

      setSelectedPlayerId(null);
      setSelectedLineupSlot(null);
      setSearchQuery("");

      if (!placementResult.lineupCompleted) {
        setRoundAdvancePending(true);
      }
      return;
    }

    if (selectedLineupSlot) {
      if (slot === selectedLineupSlot) {
        setSelectedLineupSlot(null);
        return;
      }

      if (lineup[slot]) {
        setSelectedLineupSlot(slot);
        return;
      }

      setLineup((current) => {
        const movingPlayer = current[selectedLineupSlot];
        if (!movingPlayer || current[slot]) {
          return current;
        }

        return {
          ...current,
          [selectedLineupSlot]: undefined,
          [slot]: movingPlayer,
        };
      });
      setSelectedLineupSlot(null);
      return;
    }

    if (lineup[slot]) {
      setSelectedLineupSlot(slot);
    }
  }

  async function submitScore(options?: {
    endGame?: boolean;
    lineupOverride?: Partial<Record<LineupSlot, PlayerCard>>;
  }) {
    if (isGameOver && !options?.endGame) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const payload: Partial<Record<LineupSlot, string>> = {};
      const sourceLineup = options?.lineupOverride ?? lineup;
      for (const slot of SLOT_SEQUENCE) {
        const player = sourceLineup[slot];
        if (player) {
          payload[slot] = player.id;
        }
      }
      const result = await scoreLineup(payload);
      setScore(result);
      if (options?.endGame) {
        setIsGameOver(true);
      }
    } catch (err) {
      if (options?.endGame) {
        finalScoreRequestedRef.current = false;
      }
      setError(err instanceof Error ? err.message : "Failed to score lineup.");
    } finally {
      setLoading(false);
    }
  }

  async function respin(side: "left" | "right") {
    if (isGameOver || !round || respinsLeft < 1) {
      return;
    }
    const keepSide = side === "left" ? "right" : "left";
    const keepCategoryId = keepSide === "left" ? round.left.id : round.right.id;
    setRespinsLeft((value) => value - 1);
    await spin({ keepSide, keepCategoryId }, { resetRespins: false });
  }

  async function startGame(nextMode: GameMode) {
    if (loading || startingGame) {
      return;
    }

    setStartingGame(true);
    setError(null);

    try {
      if (nextMode === "pro" && allPlayers.length === 0) {
        const players = await fetchPlayers();
        setAllPlayers(players);
      }

      setGameMode(nextMode);
      await spin(undefined, { resetRespins: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start game.");
    } finally {
      setStartingGame(false);
    }
  }

  function resetGame() {
    if (!gameMode) {
      return;
    }

    finalScoreRequestedRef.current = false;
    setLineup({});
    setRespinsLeft(2);
    setScore(null);
    setIsGameOver(false);
    setRoundAdvancePending(false);
    setSelectedPlayerId(null);
    setSelectedLineupSlot(null);
    setInvalidPlayerId(null);
    setSearchQuery("");
    void spin();
  }

  const modeLabel = gameMode === "pro" ? "Pro Mode" : "Classic Mode";
  const searchLabel = gameMode === "pro" ? "Search all players" : "Search eligible players";
  const searchPlaceholder = gameMode === "pro" ? "Type a player name" : "Type a name, team, position, or country";
  const searchHint =
    gameMode === "pro"
      ? "Pick a player by name, then place them on the rink. Off-category players flash red and cannot be drafted."
      : "Pick a player, then click a slot on the rink. To reposition your lineup, click a player on the rink, then click an empty slot.";
  const mobileSearchHint =
    gameMode === "pro"
      ? "Pick a player by name, then tap a slot. Off-category players flash red and cannot be drafted."
      : "Pick a player, then tap a slot. To reposition, tap a slotted player and then an empty slot.";

  const displayedLeftCategory = isSpinning
    ? spinningSide === "right"
      ? round?.left ?? spinPreview?.left ?? null
      : spinPreview?.left ?? round?.left ?? null
    : round?.left ?? null;
  const displayedRightCategory = isSpinning
    ? spinningSide === "left"
      ? round?.right ?? spinPreview?.right ?? null
      : spinPreview?.right ?? round?.right ?? null
    : round?.right ?? null;

  return (
    <main className="page-shell">
      <header className="hero">
        <p className="kicker">{modeLabel}</p>
        <h1>Puck Luck</h1>
        <p>Draft the best team possible using two random categories each round. Can you draft a dynasty?</p>
      </header>

      {isMobile ? (
        <section className="mobile-layout">
          <div className="panel controls-panel mobile-panel">
            <div className="tiles-row">
              <CategoryTile
                title="Category A"
                category={displayedLeftCategory}
                disabled={loading || isGameOver || respinsLeft < 1}
                onRespin={() => void respin("left")}
                spinning={isSpinning && (spinningSide === "both" || spinningSide === "left")}
              />
              <CategoryTile
                title="Category B"
                category={displayedRightCategory}
                disabled={loading || isGameOver || respinsLeft < 1}
                onRespin={() => void respin("right")}
                spinning={isSpinning && (spinningSide === "both" || spinningSide === "right")}
              />
            </div>

            <div className="mobile-meta-row">
              <p>Respins left: {respinsLeft}</p>
              {gameMode === "classic" ? <p>Eligible players: {eligibleCount}</p> : null}
            </div>

            {roundAdvancePending || isSpinning ? (
              <p className="round-transition" role="status" aria-live="polite">
                {isSpinning ? "Round complete. Spinning new categories..." : "Player placed. Ending round..."}
              </p>
            ) : null}

            {error ? <p className="error">{error}</p> : null}
          </div>

          <div className="panel rink-panel mobile-panel">
            <RinkBoardMobile
              lineup={lineup}
              onSlotAction={handleSlotAction}
              selectedPlayerId={selectedPlayerId}
              selectedLineupSlot={selectedLineupSlot}
            />
          </div>

          <div className="panel controls-panel mobile-panel">
            <div className="player-search">
              <label className="player-search-label" htmlFor="player-search-input-mobile">
                {searchLabel}
              </label>
              <input
                id="player-search-input-mobile"
                className="player-search-input"
                type="search"
                placeholder={searchPlaceholder}
                value={searchQuery}
                onChange={(event) => {
                  if (isGameOver) {
                    return;
                  }
                  setSearchQuery(event.target.value);
                  if (!event.target.value) {
                    setSelectedPlayerId(null);
                  }
                  setSelectedLineupSlot(null);
                }}
              />
              <p className="player-search-hint">{mobileSearchHint}</p>
            </div>

            {selectedPlayer ? <p className="selected-player-chip">Selected: {selectedPlayer.name}</p> : null}

            <PlayerListMobile
              filteredPlayers={filteredPlayers}
              gameMode={gameMode ?? "classic"}
              slottedPlayerIds={slottedPlayerIds}
              invalidPlayerId={invalidPlayerId}
              isGameOver={isGameOver}
              selectedPlayerId={selectedPlayerId}
              onDraftPlayer={draftPlayer}
            />

            <div className="actions-row mobile-actions-row">
              <button className="secondary" type="button" disabled={loading} onClick={resetGame}>
                New Game
              </button>
            </div>
          </div>
        </section>
      ) : (
        <section className="game-grid">
          <div className="panel controls-panel">
            <div className="tiles-row">
              <CategoryTile
                title="Category A"
                category={displayedLeftCategory}
                disabled={loading || isGameOver || respinsLeft < 1}
                onRespin={() => void respin("left")}
                spinning={isSpinning && (spinningSide === "both" || spinningSide === "left")}
              />
              <CategoryTile
                title="Category B"
                category={displayedRightCategory}
                disabled={loading || isGameOver || respinsLeft < 1}
                onRespin={() => void respin("right")}
                spinning={isSpinning && (spinningSide === "both" || spinningSide === "right")}
              />
            </div>

            <div className="actions-row">
              <button className="secondary" type="button" disabled={loading} onClick={resetGame}>
                New Game
              </button>
            </div>

            <div className="meta-row">
              <p>Respins left: {respinsLeft}</p>
              {gameMode === "classic" ? <p>Eligible players: {eligibleCount}</p> : null}
            </div>

            {roundAdvancePending || isSpinning ? (
              <p className="round-transition" role="status" aria-live="polite">
                {isSpinning ? "Round complete. Spinning new categories..." : "Player placed. Ending round..."}
              </p>
            ) : null}

            {error ? <p className="error">{error}</p> : null}

            <div className="player-search">
              <label className="player-search-label" htmlFor="player-search-input">
                {searchLabel}
              </label>
              <input
                id="player-search-input"
                className="player-search-input"
                type="search"
                placeholder={searchPlaceholder}
                value={searchQuery}
                onChange={(event) => {
                  if (isGameOver) {
                    return;
                  }
                  setSearchQuery(event.target.value);
                  if (!event.target.value) {
                    setSelectedPlayerId(null);
                  }
                  setSelectedLineupSlot(null);
                }}
              />
              <p className="player-search-hint">{searchHint}</p>
            </div>

            {selectedPlayer ? <p className="selected-player-chip">Selected: {selectedPlayer.name}</p> : null}

            <div className="player-list" aria-label="Guided eligible player list">
              {filteredPlayers.length === 0 ? (
                <p className="empty-hint">No players loaded yet. Add a player to continue or start a new game.</p>
              ) : (
                filteredPlayers.map((player) => (
                  <button
                    key={player.id}
                    className={`player-card ${slottedPlayerIds.has(player.id) ? "selected" : ""}${invalidPlayerId === player.id ? " invalid" : ""}`}
                    type="button"
                    disabled={isGameOver}
                    onClick={() => draftPlayer(player)}
                    aria-pressed={selectedPlayerId === player.id}
                  >
                    <div className="card-main">
                      <h3>{player.name}</h3>
                      {gameMode === "classic" ? (
                        <>
                          <p>
                            {player.position} | {player.birthCountry ?? "N/A"} | {player.stats.points} PTS
                          </p>
                          <p className="teams-line">{player.teamsPlayedFor.slice(0, 2).join(" / ") || "No teams"}</p>
                        </>
                      ) : null}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="panel rink-panel">
            <RinkBoard
              lineup={lineup}
              onSlotAction={handleSlotAction}
              selectedPlayerId={selectedPlayerId}
              selectedLineupSlot={selectedLineupSlot}
            />
          </div>
        </section>
      )}

      <ScoreModal result={score} onClose={() => setScore(null)} onRestart={resetGame} gameOver={isGameOver} />

      {gameMode === null ? (
        <div className="mode-picker-backdrop" role="dialog" aria-modal="true" aria-label="Choose game mode">
          <div className="mode-picker-card panel">
            <img className="mode-picker-logo" src={modePickerThumbnail} alt="Puck Luck logo" />
            <p className="kicker">Choose Your Challenge</p>
            <h2>Pick a game mode</h2>
            <p className="mode-picker-copy">Classic Mode provides you with a list of eligle players and there stats, or choose Pro Mode and rely solely on your own hockey knowledge!</p>

            {error ? <p className="error">{error}</p> : null}

            <div className="mode-picker-grid">
              <button type="button" className="mode-option" onClick={() => void startGame("classic")} disabled={startingGame}>
                <strong>Classic Mode</strong>
                <span>Eligible players only, with team and stat clues.</span>
              </button>
              <button type="button" className="mode-option" onClick={() => void startGame("pro")} disabled={startingGame}>
                <strong>Pro Mode</strong>
                <span>All players by name only. Wrong category picks flash red and fail.</span>
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
