# UI QA for the fork

Browser checks for layout and the planner flows, run against a local dev stack
(never against production – the flow test writes data).

```bash
uv run python mealie/app.py              # backend on :9000 (SQLite dev DB)
cd frontend && pnpm dev                   # frontend on :3000
uv run python dev/qa/seed.py              # recipes, plan, freezer, goals, 2nd member
cd dev/qa && npm i --no-save playwright@1.55.0 && npx playwright install webkit
node layout-check.mjs   # overflow at 320–1280 px, gutters, safe areas, long titles, touch targets
node flows.mjs          # plan → remove dish, week → shopping list, freezer, weight, ideas
```

`layout-check.mjs` simulates the iPhone home indicator by overriding the
`--fork-safe-bottom` token (see `frontend/app/assets/fork-theme.scss`).
