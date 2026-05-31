from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, billing, config, health, matches, odds, push, results, signals, sitemap, standings

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
app.include_router(config.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(matches.router, prefix="/api")
app.include_router(odds.router, prefix="/api")
app.include_router(push.router, prefix="/api")
app.include_router(sitemap.router, prefix="/api")
app.include_router(standings.router, prefix="/api")
