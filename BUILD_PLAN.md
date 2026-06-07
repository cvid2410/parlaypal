# BUILD_PLAN.md - ParlayPal Signals

> Phased roadmap. Work top to bottom. Each ticket has acceptance criteria - don't mark a
> ticket done until they pass. Read `CLAUDE.md` first; the NON-NEGOTIABLES there override
> anything here. v1 target: 4–6 weeks to a paid, working product on ~6–10 soft leagues.

---

## Status snapshot (2026-05-31)

The detection→delivery→billing→grading spine works end-to-end locally (10 leagues, adaptive
polling, ~95 backend tests). **Remaining for the v1 "definition of done":**

- **Code gaps:** SES email delivery (2.5) · "Place at {book}" deep links (2.5) · CLV-gate
  *enforcement* (3.3 - report exists, not wired to block leagues) · Stripe trial (3.1) ·
  tracker design decision + per-user bet tracking (3.4) · CloudWatch metrics/dashboard (1.5).
- **Owner / external:** lawyer review + `/docs/legal-positioning.md` (0.1) · `/docs/data-feeds.md`
  + secrets manager + paid Odds-API tier (0.2) · live Stripe keys & Price ids (3.1) · Honduras
  feed confirmation.
- **Deploy (biggest):** none of the AWS path exists yet - RDS in CloudFormation, ECS service
  split, CloudWatch. Everything runs in local docker-compose today.

Legend below: ✅ done · ⚠️ partial · ⛔ deferred/optional. Owner-only tickets noted.

---

## Phase 0 - Foundations & decisions (before writing pipeline code)

**0.1 - Legal framing (owner task, not code)** - ⚠️ OWNER, partial
- [ ] Confirm data/analytics positioning for MD/DC/VA; get a lawyer's eye before charging.
- [x] Draft the "for entertainment / not financial advice" + 1-800-GAMBLER boilerplate used app-wide.
- *AC:* a one-paragraph positioning statement committed to `/docs/legal-positioning.md`.
- *Status (2026-05-31):* disclaimers + 1-800-GAMBLER live across the copy engine, footers, and the
  rewritten Privacy/Terms (data/analytics framing). MISSING: lawyer review + `/docs/legal-positioning.md`.

**0.2 - Data feed signups (owner task)** - ⚠️ OWNER, partial
- [x] Odds aggregator for sharp reference + breadth. Start: The Odds API (cheap). Note: free
      tier (~500 req/mo) is useless for polling - budget for a paid tier; refresh rate is the
      real cost driver.
- [x] Fixtures/results feed for settlement (API-Football or similar).
- [x] Confirm which of DK/FanDuel/BetMGM the existing parlaypal ingestion already covers.
- *AC:* API keys in a secrets manager; a `/docs/data-feeds.md` listing each feed, what it
  covers, cost, and rate limits.
- *Status:* The Odds API (DK/FD/MGM + Pinnacle sharp ref) and API-Football (results/scores/standings)
  both wired. MISSING: keys are in `backend/.env` not a secrets manager; no `/docs/data-feeds.md`;
  paid Odds-API tier for prod polling; Honduras coverage unconfirmed.

**0.3 - Repo restructure** - ✅ done
- [x] Carve the existing parlaypal repo into services: `ingestors/`, `workers/`, `api/`,
      `scheduler/`, `frontend/` (existing Vue), `shared/` (models, math, schemas).
- [x] Add `CLAUDE.md` + this file to repo root.
- [x] Wire local dev: docker-compose with Postgres + Redis.
- *AC:* `docker-compose up` brings up Postgres + Redis; each service has a runnable stub. - met.

**0.4 - Data model + migrations** - ✅ done
- [x] Implement the schema from `CLAUDE.md` as migrations (Alembic). Partition
      `odds_snapshots` by day.
- [x] Seed `leagues` with the v1 target leagues, flagging `is_soft` and `sharp_ref_book`.
- *AC:* migrations apply cleanly; v1 leagues seeded; a script can insert/read a fake odds snapshot. - met.

---

## Phase 1 - The detection spine (Weeks 1–2)

> Goal: an odds change flows in → gets devigged → EV/arb computed → a signal row is written.
> No delivery, no UI yet. Prove the brain works end-to-end with one league.

**1.1 - Core math module (`shared/math.py`)** - ✅ done
- [x] Port `american_to_decimal`, `no_vig_prob`, `ev_pct`, `find_arb`, `kelly` from `CLAUDE.md`.
- [x] Unit tests with known inputs/outputs (incl. the +547 SGP and a 2-way arb example).
- *AC:* `pytest shared/` green; arb detector correctly flags a sum-of-inverse-odds < 1 case. - met.
- *Status:* also added N-way `devig_multi`/`find_arb_multi` for soccer's 3-way h2h.

**1.2 - Sharp reference ingestion** - ✅ done (built as `ingestors/odds.py`, not `sharp.py`)
- [x] Pull the sharp book / consensus for the v1 leagues via the aggregator. Poll loop
      (2–10s) or WS if available. Write to Redis hot state + append to `odds_snapshots`.
- *AC:* Redis hash `odds:{fixture}:{market}` reflects current sharp lines; history rows accrue. - met.
- *Status:* Pinnacle pulled via The Odds API in the same pass as soft books; adaptive (kickoff-aware)
  poll cadence on top.

**1.3 - Soft-book ingestion (extend existing parlaypal ingestion)** - ✅ done
- [x] Reuse/extend DK/FD/MGM adapters to feed the same canonical hot-state format.
- [x] Diff against last-seen; only emit a change event when movement exceeds a threshold
      (NON-NEGOTIABLE #3).
- *AC:* a soft-book line change for a v1 league emits exactly one change event onto the bus. - met.

**1.4 - Detection consumer (`workers/detect.py`)** - ✅ done
- [x] ARQ consumer on the change event. On each event: read all books for that market from
      Redis, compute `fair_prob` (devig sharp), then `ev_pct` and `find_arb`.
- [x] Apply global `MIN_EDGE` floor. Build `signals` rows. Compute `kelly_frac`.
- [x] Dedup via `SET nx ex` on `dedup_hash` keyed to TTL (NON-NEGOTIABLE #3). Re-alert only
      on improved edge_bucket.
- [x] Hand off accepted signals to the (stub) fanout queue.
- *AC:* feeding a known soft+sharp pair produces one persisted signal with correct edge_pct;
  a flapping line does not create duplicates. - met.

**1.5 - Observability from day one** - ⚠️ partial
- [ ] Emit pipeline lag (ingest→detect ms), signals/min, error rates to CloudWatch.
- *AC:* a dashboard shows end-to-end latency for a test signal.
- *Status:* structured JSON metrics (ingest lag, signals/min, errors) emitted to stdout via
  `shared/metrics.py`. MISSING: CloudWatch sink + dashboard (ties to deploy).

---

## Phase 2 - Normalization + delivery (Weeks 3–4)

> Goal: signals actually reach a human, in approved language, for the chosen leagues.

**2.1 - Normalization / alias layer (`shared/normalize.py`) - THE TIME SINK, scope tight** - ⚠️ partial (de-risked)
- [x] Per-book adapters resolve team + fixture + market to canonical IDs using `team_aliases`
      + a fixture match (tolerance window on kickoff time).
- [x] Unmatched → `review_queue` table, NOT dropped (NON-NEGOTIABLE #6).
- [ ] Build the alias seed for the v1 leagues only.
- *AC:* >95% of incoming v1-league markets resolve; unmatched land in the review queue with
  enough context to alias manually.
- *Status:* single-aggregator de-risk - The Odds API normalizes names and gives each event a stable
  `id`, so signal-side resolution is ~100% with no alias seed. The gap is CROSS-FEED matching to
  API-Football (logos/results) by `norm_team` + date; misses (e.g. "Botafogo" vs "Botafogo SP") fall
  back gracefully. MISSING: the `team_aliases` seed to lift cross-feed match rate.

**2.2 - Template copy engine (`shared/copy.py`)** - ✅ done
- [x] Implement `explain(signal)` with per-kind template pools (ev / arb / middle / model /
      promo) + `REASONS` fragment injection. Variant chosen deterministically off
      `dedup_hash` (same signal → same text).
- [x] NO LLM at runtime. Never emit certainty language for individual +EV bets
      (NON-NEGOTIABLE #1).
- *AC:* generating copy for the same signal twice is identical; copy renders correct
  computed odds/edge; a lint test asserts banned phrases ("guaranteed win", "lock", etc.)
  never appear for kind=ev. - met. (ev + arb pools; middle/model/promo arrive with those kinds.)

**2.3 - (Offline, optional) LLM variant generator (`tools/gen_variants.py`)** - ⛔ deferred (optional)
- [ ] One-off script: use the Anthropic API to draft ~20 on-message variants per kind for
      human review, output to a file the engine loads. Human approves before use.
- *AC:* produces a reviewable variant file; engine reads approved variants only.

**2.4 - Fan-out / routing (`workers/fanout.py`)** - ✅ done
- [x] Maintain Redis routing sets (`sub:league:{id}`, `sub:book:{book}`). On a signal,
      intersect to get eligible users; filter by each user's `min_edge`; enqueue delivery.
      Do NOT iterate all users (NON-NEGOTIABLE #5).
- [x] Free tier → delayed queue (~12 min); model/live kinds filtered out for lower tiers.
- *AC:* a signal reaches only matching users; a free user receives it delayed; idempotent
  (`alerts_sent` prevents doubles, NON-NEGOTIABLE #4). - met.

**2.5 - Delivery channels (`workers/deliver.py`)** - ⚠️ partial
- [x] Discord webhook ~~+ SES email~~ for v1. Format the template copy into a clean card/message.
- [ ] Include a "Place at {book}" deep link where the book supports it.
- *AC:* a test user gets a correctly formatted Discord + email alert for a live signal.
- *Status:* channel abstraction with a local Log channel + Discord webhook (idempotent via
  `alerts_sent`). MISSING: SES email channel; "Place at {book}" deep link.

---

## Phase 3 - Monetize + prove it works (Weeks 5–6)

> Goal: people can pay, signals get graded, and the tracker shows honest results. Plus a thin
> free shell so parlaypal traffic lands somewhere.

**3.1 - Stripe + tiering gate (`api/billing.py`)** - ⚠️ partial
- [ ] Stripe checkout for Bettor ($29) / Sharp ($79); 7-day or $1 card-gated trial.
- [x] Webhook updates `users.tier`; gate routing/fanout by tier. Cancel-anytime monthly default.
- *AC:* upgrading a user unlocks live (undelayed) signals end-to-end; downgrade re-delays them. - met (logic).
- *Status:* Checkout Session + signature-verified webhook (upgrade/cancel→downgrade), tier gate on the
  signals API + fanout. A dev-only `/billing/dev-upgrade` lets the UI demo without keys. MISSING: live
  Stripe keys + Price ids (owner); no trial.

**3.2 - Settlement + CLV grading (`scheduler/settle.py`)** - ✅ done
- [x] Cron: on market close / match settle, record `closing_odds`, compute `beat_clv`, and
      `result`/`pnl_units` into `signal_grades` using the results feed.
- *AC:* settled signals get graded; a query returns CLV-beat % and P&L by league/kind. - met.
- *Status:* CLV graded from our own Pinnacle close (no feed needed); result/P&L fill in once the
  results resolver scores the fixture.

**3.3 - CLV gate enforcement (process + check)** - ⚠️ partial
- [x] A report/check that a league or market must beat closing line on backtest before it's
      enabled for users (NON-NEGOTIABLE #2). ~~Gate league activation behind it.~~
- *AC:* enabling a league requires its CLV-beat backtest to pass a threshold; failing leagues
  stay internal-only.
- *Status:* `shared/clv.py` report + `meets_clv_gate()` + `scripts/clv_report.py` exist. MISSING: the
  ENFORCEMENT hook - a failing league isn't actually blocked from serving signals yet.

**3.4 - Lightweight tracker (frontend + `api/tracker.py`)** - ⚠️ built, then hidden (owner deciding)
- [x] ~~Track bets placed *from our signals*~~ Show bankroll curve, ROI, win rate, CLV-beat %,
      and recent W/L history (show losses honestly).
- *AC:* the Results screen renders real graded data for a test user. - met, then Results tab hidden.
- *Status:* `/api/results` + ResultsView render the SERVICE track record (flat 1u). The per-user
  "bets I placed from your signals" variant in the AC is NOT built - owner is rethinking the design;
  tab hidden (code kept, one-line restore).

**3.5 - Thin free shell (frontend, reuse Vue)** - ✅ done
- [x] Scores / fixtures / standings across leagues via the fixtures feed (buy, don't build -
      it's a commodity). Signup wall. Delayed signal teasers (blurred live cards + "won
      earlier" results) with upgrade CTA.
- *AC:* a free user sees scores + delayed teasers; tapping a locked signal opens the upgrade flow. - met.
- *Status:* full web-app shell (Scores w/ logos, per-league Standings, Leagues, locked signal teasers,
  upgrade modal). Note: free teaser is "locked live cards" (redacted), not the 12-min delayed reveal.

---

## Phase 4 - v2 and beyond (after v1 has paying users)

Prioritize by what retains/converts, not by what's fun.

- **4.1 Models (the moat):** xG/Poisson goals model, then corners + cards models (softest
  markets). Ship per-market only after the CLV gate passes.
- **4.2 More leagues:** expand the soft long tail; rank by `(line softness) × (data availability)`.
- **4.3 Live in-play:** the hard, latency-critical Sharp-tier feature.
- **4.4 Conversational "Ask":** LLM over our own fixtures/scores/standings (free-tier
  differentiator; never picks). *(A "coming soon" Ask tab placeholder ships in the v1 shell.)*
- **4.5 Web push + SMS:** warm the push channel via score alerts first, then signal pushes.
- **4.6 Affiliate offers tab:** surface sportsbook signup bonuses (the one place affiliate
  revenue doesn't conflict with the product, since it pays before users get limited).
- **4.7 Polished free companion app:** only if conversion data justifies the second product.

---

## Definition of done for v1

A subscriber, for ~6–10 soft soccer leagues, reliably receives pre-game value-bet and arb
alerts (live; free users delayed) in compliant template language, can pay via Stripe, and can
see an honest tracker showing CLV-beat % and P&L - with every shipped league having passed the
CLV gate. Models, live, and the full free app are explicitly deferred.

## Sequencing notes for the agent

- Build vertically through ONE league first (end-to-end: ingest → detect → deliver) before
  widening. A working slice beats a broad skeleton.
- Normalization (2.1) will eat the most time - keep the v1 league set small on purpose.
- Don't build the tracker's auto-sync; it's commoditized (see CLAUDE.md). Track our own signals only.
- When in doubt about copy/compliance or shipping a market, STOP and surface it - the
  NON-NEGOTIABLES win over velocity.

## Implementation notes (added during build)

- **Single-aggregator de-risk:** all books (soft + Pinnacle sharp ref) are pulled through The
  Odds API, which already normalizes team names across books and assigns each event a stable
  `id`. v1 uses that `event.id` as the canonical fixture key, deferring most of the 2.1
  cross-book normalization time-sink until we add direct book APIs or join the fixtures feed.
- **Deferred infra:** RDS Postgres is not yet in `infra/` CloudFormation (local dev uses
  docker-compose Postgres). Add an RDS stack + full ECS service-per-process split when moving
  the spine to AWS. Until then, the single image runs `api` and `worker` as separate
  containers/processes.
