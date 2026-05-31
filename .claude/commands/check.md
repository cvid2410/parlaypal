---
description: Run backend ruff (auto-fix + format), pyright, and pytest
---

Run the backend quality gate and report the outcome:

```
bash backend/scripts/check.sh
```

This auto-fixes + formats with ruff, type-checks with pyright, then brings up Postgres + Redis
via docker compose and runs pytest. If any step fails, fix the reported issues and re-run until
it's green. If Docker isn't available, run `bash backend/scripts/check.sh --no-tests` for the
lint + type pass only and tell me the tests were skipped.
