"""Run sport-key discovery once (register active soccer competitions, enable/disable).

Run from backend/:  python -m scripts.discover_sports
"""

import asyncio

from app.scheduler.discovery import discover_sports


async def main() -> None:
    print(await discover_sports())


if __name__ == "__main__":
    asyncio.run(main())
