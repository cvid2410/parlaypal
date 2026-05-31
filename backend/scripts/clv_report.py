"""Print the CLV-beat report per league and the launch-gate verdict (3.3).

Run from backend/:  python -m scripts.clv_report
"""
import asyncio

from app.shared.clv import GATE_BEAT_THRESHOLD, GATE_MIN_SAMPLE, clv_report_by_league
from app.shared.db import get_sessionmaker


async def main() -> None:
    async with get_sessionmaker()() as session:
        report = await clv_report_by_league(session)

    if not report:
        print("No graded signals yet (nothing has settled).")
        return

    print(f"{'League':24} {'n':>5} {'beats':>6} {'beat%':>7} {'lo95%':>7}  gate")
    print("-" * 60)
    for r in report:
        verdict = "PASS" if r.passes() else "hold"
        print(f"{r.league:24} {r.n:>5} {r.beats:>6} {r.beat_pct*100:>6.1f}% "
              f"{r.lower_bound*100:>6.1f}%  {verdict}")
    print(f"\nGate: Wilson lower bound (1-sided 95%) of beat-CLV >= {GATE_BEAT_THRESHOLD*100:.0f}% "
          f"over >= {GATE_MIN_SAMPLE} graded signals.")
    print("Leagues marked 'hold' stay internal-only until they clear the gate (NON-NEGOTIABLE #2).")


if __name__ == "__main__":
    asyncio.run(main())
