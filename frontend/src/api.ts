import type { Category, EligibleResponse, LineupSlot, PlayerCard, ScoreResponse, SpinResponse } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const ELIGIBLE_FETCH_LIMIT = 8000;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function spinRound(payload?: { keepSide?: "left" | "right"; keepCategoryId?: string }): Promise<SpinResponse> {
  return request<SpinResponse>("/spin", {
    method: "POST",
    body: JSON.stringify(payload ?? {}),
  });
}

export async function fetchCategories(): Promise<Category[]> {
  return request<Category[]>("/categories");
}

export async function fetchEligible(leftCategoryId: string, rightCategoryId: string): Promise<EligibleResponse> {
  return request<EligibleResponse>("/eligible", {
    method: "POST",
    body: JSON.stringify({ leftCategoryId, rightCategoryId, limit: ELIGIBLE_FETCH_LIMIT }),
  });
}

export async function fetchPlayers(): Promise<PlayerCard[]> {
  return request<PlayerCard[]>(`/players?limit=${ELIGIBLE_FETCH_LIMIT}`);
}

export async function scoreLineup(lineup: Partial<Record<LineupSlot, string>>): Promise<ScoreResponse> {
  const picks = Object.entries(lineup)
    .filter(([, playerId]) => Boolean(playerId))
    .map(([slot, playerId]) => ({ slot, playerId }));

  return request<ScoreResponse>("/score", {
    method: "POST",
    body: JSON.stringify({ lineup: picks }),
  });
}
