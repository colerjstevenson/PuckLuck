from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .game_service import data_ready, eligible, get_player, list_categories, metadata, score_lineup, spin
from .models import (
    EligibleRequest,
    EligibleResponse,
    HealthResponse,
    PlayerCardResponse,
    ScoreRequest,
    ScoreResponse,
    SpinRequest,
    SpinResponse,
)

app = FastAPI(title="NHL Classic API", version="0.1.0")

origins_csv = os.getenv("FRONTEND_ORIGINS", "*")
origins = [item.strip() for item in origins_csv.split(",") if item.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    meta = metadata()
    return HealthResponse(
        status="ok",
        playerCount=meta["playerCount"],
        categoryCount=meta["categoryCount"],
        dataSource=meta.get("dataSource", "unknown"),
        sourceRowCount=meta.get("sourceRowCount", 0),
        dataReady=meta.get("dataReady", False),
    )


def _ensure_runtime_data() -> None:
    if data_ready():
        return
    raise HTTPException(status_code=503, detail="Player data source unavailable")


@app.get("/categories")
def categories() -> list[dict]:
    _ensure_runtime_data()
    return list_categories()


@app.post("/spin", response_model=SpinResponse)
def spin_round(payload: SpinRequest) -> SpinResponse:
    _ensure_runtime_data()
    result = spin(keep_side=payload.keepSide, keep_category_id=payload.keepCategoryId)
    return SpinResponse(**result)


@app.post("/eligible", response_model=EligibleResponse)
def eligible_players(payload: EligibleRequest) -> EligibleResponse:
    _ensure_runtime_data()
    total, players = eligible(payload.leftCategoryId, payload.rightCategoryId, payload.limit)
    cards = [PlayerCardResponse(**p) for p in players]
    return EligibleResponse(
        leftCategoryId=payload.leftCategoryId,
        rightCategoryId=payload.rightCategoryId,
        totalMatches=total,
        players=cards,
    )


@app.get("/player/{player_id}", response_model=PlayerCardResponse)
def player_detail(player_id: str) -> PlayerCardResponse:
    _ensure_runtime_data()
    player = get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return PlayerCardResponse(**player)


@app.post("/score", response_model=ScoreResponse)
def score(payload: ScoreRequest) -> ScoreResponse:
    _ensure_runtime_data()
    result = score_lineup([item.model_dump() for item in payload.lineup])
    return ScoreResponse(**result)
