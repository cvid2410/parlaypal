# CLAUDE.md - ParlayPal Signals

> Read this file at the start of every session. It is the source of truth for what we're
> building, the stack, and the rules that must not drift. The phased work lives in
> `BUILD_PLAN.md`.

## What this project is

ParlayPal (parlaypal.gg) is pivoting from a World Cup 2026 parlay builder into a
**soccer-only betting-edge SaaS**: it ingests odds from multiple sportsbooks in real time,
detects mispriced markets (value bets, arbitrage), and pushes those signals to subscribers
before the lines correct.

This is **not** a request/response CRUD app. It is a **streaming pipeline** (odds flow in
continuously → get evaluated the instant they change → push out to users) with a thin
web/app layer bolted on. Architect around the stream, not the page.

## The niche (why we win)

The +EV/arb category is crowded (OddsJam, Outlier, Bet Hero, Pikkit). We do **not** compete
head-on. Our defensible wedge is the *intersection* of four things:

1. **Soccer only** - go deep where generalists go wide.
2. **The soft long tail** - Liga MX, Brazil Série A/B, J-League, Eredivisie, MLS,
   Eliteserien, Allsvenskan/Superettan, La Liga 2, Chilean Primera, etc. A book's line is
   only as sharp as the money on it; obscure leagues are mispriced and slow. This is where
   the edge actually is.
   **Coverage constraint:** only seed leagues The Odds API actually carries (67 soccer
   leagues - pull the live list from `GET /v4/sports?all=true`). **Liga Nacional de Honduras,
   the natural CONCACAF wedge, is NOT in The Odds API**, so it's deferred until a feed exists
   (OpticOdds / a local book). Don't seed a league with no odds feed - it can't produce
   signals, only a dead row.
3. **Owner domain knowledge** - deep CONCACAF / Central & South American football knowledge
   that generalist tools' teams will never have.
4. **Existing distribution** - parlaypal.gg already has a soccer audience and a
   DK/FanDuel/BetMGM odds pipeline. Near-zero CAC.

Positioning line: *"The only betting-edge tool built only for soccer - every league on
earth, all year, including the ones the big tools don't even cover."*

**Hunt the soft long tail for classic +EV** - a soft book lagging the sharp price only
happens where the money is thin. Do NOT try to out-cover OddsJam by claiming "+EV value
bets" on big-5 / WC markets (EPL/La Liga/World Cup lines are sharp → no soft-book edge;
faking one breaks NON-NEGOTIABLE #1/#2).

**But big leagues + the World Cup still get signals - just the right *kind*.** Match the
signal type to the market sharpness:
- **+EV (devig vs sharp):** soft leagues only.
- **Arbitrage & middles (mechanical, guaranteed by math):** ALL leagues, incl. big-5 + WC.
  Big games have the most books → the most fleeting arbs. (Don't need the CLV gate.)
- **Best price / line-shopping (informational, no edge claim):** every market, incl. WC -
  and it's what the existing big-league/WC audience wants.
- **Odds boosts / promos (book-subsidized, genuinely +EV):** best honest edge on big games;
  needs a promo data source.

## Tech stack (use what already exists; this mirrors the owner's stack)

- **Language:** Python 3.12
- **API:** FastAPI
- **Workers / async jobs:** ARQ (Redis-backed)
- **Cache / hot state / message bus:** Redis (hashes for latest odds, Redis Streams for the bus)
- **Database:** PostgreSQL (RDS). `odds_snapshots` is high-volume time-series - partition by
  day; TimescaleDB is a candidate later.
- **Frontend:** Vue (the existing parlaypal frontend - evolve, don't rebuild)
- **Infra:** AWS ECS on EC2/Fargate, ElastiCache (Redis), RDS (Postgres), S3, all via
  CloudFormation.
- **Payments:** Stripe
- **Delivery:** Discord webhooks + email (SES) for v1; web push (VAPID) + SMS (Twilio) later
- **Observability:** CloudWatch (Coralogix optional)

Run as separate ECS services so they scale independently:
`ingestors` (network-bound, many small) · `workers` (CPU: detection) · `api` (user-facing) ·
`scheduler` (settlement/CLV cron).

## Reuse vs. build new

**Reuse from existing parlaypal:** DK/FanDuel/BetMGM odds ingestion + normalization (the
hardest part - already partly solved), the Vue frontend shell, auth, AWS/CFN setup.

**Build new:** sharp-reference ingestion (Pinnacle via aggregator) + devig, the event-driven
detection core, signal persistence + dedup, fan-out/routing + delivery, Stripe tiering,
settlement + CLV grading, template copy engine.

**Evolve, don't rebuild:** parlaypal becomes the frontend + ingestion layer of this system.

## Architecture (the signal lifecycle)

```
SOURCES        INGEST          NORMALIZE        EVALUATE         ROUTE           LEARN
DK/FD/MGM  →   adapter     →   canonical    →   detection   →   fan-out     →   settle +
Pinnacle*      workers         keys +           engine          by tier +       grade CLV
(sharp ref)    (1/book)        alias map        (EV / arb)      filter          → tracker +
               ↓               ↓                ↓               ↓               calibrate
        [Redis raw stream] [Redis hot state] [emit on        Discord/email   [Postgres history
                                             meaningful Δ]    (delayed q       → backtest/CLV]
                            [Postgres odds                    for free tier)
                             history append]
```

* Pinnacle does not operate in the regulated US market - obtain it via an odds aggregator
  (The Odds API to start, OpticOdds/OddsJam-data later), or substitute Circa / sharp
  consensus as the reference.

Everything is **event-driven**: an odds change is a message, not a row to poll for.

## Data model (canonical entities - get this right early)

```sql
leagues(id, name, country, sharp_ref_book, is_soft, model_enabled)
fixtures(id, league_id, home_id, away_id, kickoff_utc, status)
team_aliases(team_id, book, raw_name)        -- "Paris SG"="PSG"="Paris St-G"
markets(id, type, line, period)              -- ('total', 2.5, 'FT')

odds_snapshots(fixture_id, book, market_id, selection, decimal_odds, ts)  -- firehose; partition by day

signals(id, fixture_id, market_id, selection, book, kind,                -- ev|arb|middle|model|promo
        offered_odds, fair_prob, edge_pct, kelly_frac,
        ttl_sec, created_at, dedup_hash, status)                         -- live|expired|settled
signal_grades(signal_id, closing_odds, beat_clv bool, result, pnl_units) -- win|loss|push

users(id, tier, bankroll, ...)
subscriptions(user_id, leagues[], books[], min_edge, channels[])         -- user filter
alerts_sent(signal_id, user_id, channel, ts)                            -- idempotency + audit
```

## Core math (reference implementations)

```python
def american_to_decimal(o):
    return 1 + (o/100 if o > 0 else 100/abs(o))

def no_vig_prob(dec_a, dec_b):          # devig a 2-way sharp market
    ia, ib = 1/dec_a, 1/dec_b
    return ia / (ia + ib)               # true prob of side A

def ev_pct(your_dec, true_prob):
    return (your_dec * true_prob - 1) * 100   # > 0 = +EV

def find_arb(dec_a, dec_b):             # 2-way
    margin = 1 - (1/dec_a + 1/dec_b)
    return None if margin <= 0 else {
        "profit_pct": margin * 100,
        "stake_a_frac": (1/dec_a) / (1/dec_a + 1/dec_b),
        "stake_b_frac": (1/dec_b) / (1/dec_a + 1/dec_b),
    }

def kelly(true_prob, dec_odds, fraction=0.25):   # fractional Kelly for stake sizing
    b = dec_odds - 1
    f = (true_prob * b - (1 - true_prob)) / b
    return max(0.0, f * fraction)
```

## NON-NEGOTIABLES (do not drift from these)

1. **Compliance - template copy only, never an LLM in the live signal path.** All
   user-facing signal explanations come from approved templates filled with computed values.
   No runtime LLM generation of betting advice. Never produce language implying certainty of
   winning ("guaranteed win", "lock", "can't lose") for an *individual* +EV bet. (Arbitrage
   may say "guaranteed profit" because it mathematically is.) The LLM belongs only in the
   offline variant-pool generator and the free-tier conversational "Ask" feature (scores /
   standings / fixtures over our own data - never picks).

2. **CLV-gate before shipping a market.** Never ship a new league or market type to users
   until backtested signals in it demonstrably beat the closing line. If our "+EV" isn't
   beating closing lines, our fair-prob is wrong - fix it before users lose money trusting us.

3. **Emit only on meaningful change.** Diff each odds update against last-seen and threshold
   it. A 1-cent move must not recompute/re-alert. Use `SET nx ex` on a dedup hash
   (canon_event + market + selection + book + edge_bucket) keyed to the signal TTL so a
   flapping line can't spam users - but re-alert if the edge materially improves.

4. **Idempotent delivery.** Record `alerts_sent` per (signal, user, channel). Never double-send.

5. **Don't loop all users per signal.** Fan-out via a precomputed routing index
   (Redis sets per league/book) → intersect → filter by each user's `min_edge` → deliver.
   Tiering is enforced here (free tier → delayed queue; model/live signals filtered out for
   lower tiers).

6. **Unmatched entities go to a review queue, never `/dev/null`.** A missed normalization
   match is a missed signal (= missed revenue). Surface them for manual aliasing.

7. **Responsible gambling.** Every user-facing surface carries 1-800-GAMBLER and a
   "for entertainment / bet responsibly" line. Stakes are framed as % of a stated bankroll.

## Tiers (product)

- **Free:** soccer companion - live scores, fixtures, standings across all leagues +
  conversational "Ask" + **delayed (≈12 min) signal *teasers*** (blurred/locked live cards,
  "won earlier" results visible). Signup required. Leaks no edge (scores aren't an edge).
- **Bettor ($29/mo):** all value bets live, all leagues, stake calculator, filter by your books.
- **Sharp ($79/mo):** + live in-play, our corners/cards models, instant push, custom alerts.

Pricing rule: never price a tier above the edge its target bankroll can realistically clear,
or users net-lose and churn angry. Free → $29 → $79 maps to growing bankroll.

## v1 scope (ship this first - see BUILD_PLAN.md)

**IN:** pre-game value bets + arbs; devig against sharp reference (NO homegrown models yet);
~6–10 soft leagues the owner knows; Discord + email delivery; Stripe with paid gate;
lightweight tracker (bets from our signals, not full auto-sync); thin free shell (scores).

**OUT (v2+):** corners/cards models; live in-play; conversational Ask; full polished free
app; auto-sync bet tracking; web push; affiliate offers tab.

## Open decision that gates launch (not an engineering problem)

**Legal framing for MD/DC/VA.** Position the product as **data/analytics**, not picks/tout
advice (this is how incumbents stay clean). Get a lawyer's review before charging money.
Flag this in any planning output; do not let it block engineering, but do not let launch
happen without it.
