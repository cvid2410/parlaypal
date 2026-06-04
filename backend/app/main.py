from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    billing,
    config,
    health,
    leagues,
    lines,
    preferences,
    push,
    results,
    scores,
    signals,
    standings,
    teams,
)

app = FastAPI(title="parlaypal.gg API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://parlaypal.gg"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(signals.router, prefix="/api")
app.include_router(results.router, prefix="/api")
app.include_router(scores.router, prefix="/api")
app.include_router(leagues.router, prefix="/api")
app.include_router(standings.router, prefix="/api")
app.include_router(teams.router, prefix="/api")
app.include_router(lines.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(push.router, prefix="/api")
app.include_router(preferences.router, prefix="/api")
