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
    diversity: number;
    positionFit: number;
    completionBonus: number;
  };
  penalties: string[];
  warnings: string[];
};
