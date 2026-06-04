# v2 spec — "earn the right to claim edge"

> Status: spec (2026-06-04). Source of truth for the v2 measurement rebuild. Born out of the
> gate-board / P&L investigation — see the `ev-thesis-no-realized-edge` memory and the chat that
> produced this. Read alongside `CLAUDE.md` (NON-NEGOTIABLES still bind).

## Why v2 exists

v1 detected +EV by devigging Pinnacle and validated it with a CLV gate. The investigation showed
**both halves are unproven**:

- The CLV gate read 70–88% beat-close (looked great) but realized P&L over ~4,000 backtested bets
  was ≈ **−4%** (Superettan, the one certified league, **−22.9%**). CLV and P&L can't both be
  right — for a correct pipeline persistent +CLV implies non-negative P&L. **The divergence itself
  proves the measurement is broken**, not that the edge is definitely absent.
- Two mechanisms: (1) **self-confirming CLV** — we detect within ~2h of kickoff and grade against a
  sharp line ~2h later that's barely moved, so beat-CLV ≈ our own selection condition re-measured;
  (2) **unverified benchmark** — Pinnacle may not be sharp on the thin long tail, so beating its
  no-vig close ≠ +EV.

**v2 is not features. It is the instrument rebuild that lets the gate judge on clean inputs, and
the scoping of what the product can honestly claim.** Don't override the gate to ship.

The asymmetry that sets priority: **P&L is fixable only by waiting** (you need ~10k clustered bets —
seasons — to see a 2–3% edge through outcome variance). **CLV contamination is fixable now.** So
clean CLV is the only gauge that can certify on a realistic timeline; P&L stays a slow background
*contradictor* (it can disconfirm, never confirm, on this horizon).

## The spine (dependency order)

### Layer 0 — Correctness gates (small, immediate)
- **Shin bisection guard** — `shin_devig` is oracle-cleared (matches an independent 3-way solve to
  4.5e-7, not the multiplicative column), but add a no-bracket / residual check so degenerate books
  fail to `{}` rather than returning a plausible-but-wrong `z`. **(DONE 2026-06-04.)**
- **Selection-key unification audit** across books — the silent mismatch failure mode (grading the
  wrong leg against the wrong line). Verify cross-book selection keys unify; unmatched → review queue.

### Layer 1 — Measurement infrastructure (the foundation everything waits on)
- **True open + close line capture.** Capture the *opening* sharp line (first posted) and the *true
  closing* line (kickoff − seconds, not − 2h), per market. Today we have two adjacent snapshots, not
  CLV infrastructure. CLV must be measured with temporal independence from detection — ideally
  movement `(close − open)`, not `(snapshot − slightly-later-snapshot)`.
- **Detection-price durability / liquidity logging.** Log not just the price at detection but how
  long it lived and what limits were available. On thin leagues an edge can be **real and
  non-realizable simultaneously** — a number that flashed for 20 seconds. CLV can't distinguish "we
  beat the close" from "we observed an untransactable number" unless durability is captured. This is
  a *column on the capture*, not a separate task.

### Layer 2 — Benchmark validation (epistemically prior — scopes the whole product)
- **Per-league Pinnacle sharpness test:** does Pinnacle's *close* beat its *open* (more calibrated
  against outcomes) on this specific league? Outcome-consuming but far more sample-efficient than ROI
  (continuous movement per game, not one win/loss Bernoulli).
  - **Sharp** → league is serve-eligible. **Not sharp** → no-serve. **Indeterminate** (line barely
    moved — sharp open vs no money ever arriving, can't tell) → **routes to no-serve, not "good
    enough."** Indeterminate ≡ fail.
  - This decides which leagues we're even *allowed* to have an opinion on, before any signal ships.
    Run it before building anything on top.

### Layer 3 — The honest gate + scoped claim
- **Clean CLV** = detection price vs true close, with a **realizability filter** (only count
  capturable prices), run only on Layer-2 survivors. This is the certifier.
- **Claim scoping (product/compliance):** clean +CLV licenses *"our signals beat the closing line
  X% of the time"* — honest and defensible. It does **not** license *"you will profit"* (that's
  downstream of the subscriber getting the detection price and not getting limited). Sharp-tier copy
  says only the first. Model-edge ≠ realized-profit.

## Product consequences (parallel track — NOT gated on the above)

The mechanical/informational products need no fair-prob and no benchmark, so they ship independently:

- **Best-price / line-shopping** — works on every league today (`/lines`). Honest value now.
- **Arbitrage + middles** — real but thin with 6 books; **adding more bookmakers** (esp. independent
  ones / exchanges) is the highest-leverage near-term move for volume.
- **Free companion** — scores / standings / schedule. Ships now.
- **Sharp tier (+EV)** is *gated* on Layer 2+3 passing for real leagues. Until then, don't sell it —
  or scope the offer to "best-price + arb," not "+EV picks."

## One-line spine

Shin guard → open/close + durability capture → per-league sharpness test (indeterminate ≡ fail) →
clean, realizability-filtered CLV, scoped to a model-edge claim. **Don't override the gate.**
