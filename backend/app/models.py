from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    id: str
    label: str
    group: str


class SpinRequest(BaseModel):
    keepSide: Literal["left", "right"] | None = None
    keepCategoryId: str | None = None


class SpinResponse(BaseModel):
    left: CategoryResponse
    right: CategoryResponse
    roundToken: str
    eligibleCount: int


class EligibleRequest(BaseModel):
    leftCategoryId: str
    rightCategoryId: str
    # Return all practical matches for large category intersections.
    limit: int = Field(default=8000, ge=1, le=8000)


class PlayerCardResponse(BaseModel):
    id: str
    name: str
    headshot: str | None = None
    position: str
    positionGroup: str
    birthCountry: str | None = None
    active: bool
    teamsPlayedFor: list[str]
    stats: dict
    awards: list[str]
    inHHOF: bool
    sweaterNumber: int | None = None


class EligibleResponse(BaseModel):
    leftCategoryId: str
    rightCategoryId: str
    totalMatches: int
    players: list[PlayerCardResponse]


class LineupPick(BaseModel):
    slot: Literal["F1", "F2", "F3", "D1", "D2", "G"]
    playerId: str


class ScoreRequest(BaseModel):
    lineup: list[LineupPick] = Field(default_factory=list, min_length=1)


class ScoreBreakdown(BaseModel):
    production: int
    awards: int
    cups: int
    grit: int
    hallOfFame: int
    positionFit: int


class ScoreWeightedContribution(BaseModel):
    production: int
    awards: int
    cups: int
    grit: int
    hallOfFame: int
    positionFit: int
    goalieQuality: int


class ScoreAdjustment(BaseModel):
    label: str
    points: int


class ScorePlayerBreakdown(BaseModel):
    slot: Literal["F1", "F2", "F3", "D1", "D2", "G"]
    playerId: str
    playerName: str
    breakdown: ScoreBreakdown


class ScoreResponse(BaseModel):
    totalScore: int
    breakdown: ScoreBreakdown
    weightedContribution: ScoreWeightedContribution
    scoreSubtotal: int
    bonusTotal: int
    hardPenaltyTotal: int
    bonuses: list[ScoreAdjustment]
    penaltiesApplied: list[ScoreAdjustment]
    goalieQuality: int
    goalieQualityFloorForA: int
    goalieGatePassedForA: bool
    finalScoreEquation: str
    playerBreakdown: list[ScorePlayerBreakdown]
    penalties: list[str]
    warnings: list[str]
    grade: str


class HealthResponse(BaseModel):
    status: str
    playerCount: int
    categoryCount: int
    dataSource: str
    sourceRowCount: int = 0
    dataReady: bool = False
