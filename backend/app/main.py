from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import config, health, matches, odds, push, sitemap, standings

app = FastAPI(title="parlaypal.gg API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://parlaypal.gg"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(config.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(matches.router, prefix="/api")
app.include_router(odds.router, prefix="/api")
app.include_router(push.router, prefix="/api")
app.include_router(sitemap.router, prefix="/api")
app.include_router(standings.router, prefix="/api")
