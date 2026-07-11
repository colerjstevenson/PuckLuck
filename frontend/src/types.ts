export type Category = {
  id: string;
  label: string;
  group: string;
};

export type SpinResponse = {
  left: Category;
  right: Category;
  roundToken: string;
  eligibleCount: number;
};

export type PlayerCard = {
  id: string;
  name: string;
  headshot?: string | null;
  position: string;
  positionGroup: string;
  birthCountry?: string | null;
  active: boolean;
  teamsPlayedFor: string[];
  stats: {
    gamesPlayed: number;
    goals: number;
    assists: number;
    points: number;
    pim: number;
  };
  awards: string[];
  inHHOF: boolean;
  sweaterNumber?: number | null;
};

export type EligibleResponse = {
  leftCategoryId: string;
  rightCategoryId: string;
  totalMatches: number;
  players: PlayerCard[];
};

export type LineupSlot = "F1" | "F2" | "F3" | "D1" | "D2" | "G";

export type ScoreResponse = {
  grade: string;
  totalScore: number;
  breakdown: {
    production: number;
    awards: number;
    cups: number;
    grit: number;
    hallOfFame: number;
    positionFit: number;
  };
  weightedContribution: {
    production: number;
    awards: number;
    cups: number;
    grit: number;
    hallOfFame: number;
    positionFit: number;
    goalieQuality: number;
  };
  scoreSubtotal: number;
  bonusTotal: number;
  hardPenaltyTotal: number;
  bonuses: {
    label: string;
    points: number;
  }[];
  penaltiesApplied: {
    label: string;
    points: number;
  }[];
  goalieQuality: number;
  goalieQualityFloorForA: number;
  goalieGatePassedForA: boolean;
  finalScoreEquation: string;
  playerBreakdown: {
    slot: LineupSlot;
    playerId: string;
    playerName: string;
    breakdown: {
      production: number;
      awards: number;
      cups: number;
      grit: number;
      hallOfFame: number;
      positionFit: number;
    };
  }[];
  penalties: string[];
  warnings: string[];
};
