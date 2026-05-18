from fastapi import APIRouter
from fastapi.responses import Response
from app.services.api_football import fetch_matches

router = APIRouter()

BASE_URL = "https://parlaypal.gg"

STATIC_ROUTES = [
    {"loc": f"{BASE_URL}/",        "priority": "1.0", "changefreq": "daily"},
    {"loc": f"{BASE_URL}/parlay",  "priority": "0.8", "changefreq": "daily"},
    {"loc": f"{BASE_URL}/privacy", "priority": "0.3", "changefreq": "monthly"},
    {"loc": f"{BASE_URL}/terms",   "priority": "0.3", "changefreq": "monthly"},
]


def _url_entry(loc: str, priority: str, changefreq: str) -> str:
    return (
        f"  <url>\n"
        f"    <loc>{loc}</loc>\n"
        f"    <changefreq>{changefreq}</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        f"  </url>"
    )


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap():
    entries = [_url_entry(**r) for r in STATIC_ROUTES]

    try:
        matches = await fetch_matches()
        for match in matches:
            entries.append(_url_entry(
                loc=f"{BASE_URL}/match/{match['id']}",
                priority="0.9",
                changefreq="hourly",
            ))
    except Exception:
        pass

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )

    return Response(content=xml, media_type="application/xml")
