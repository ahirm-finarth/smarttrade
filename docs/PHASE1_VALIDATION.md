# Phase 1 validation evidence

Verified on 5 October 2026, using the supplied MySQL instance and original synthetic sources. Development branch: `phase-1` per the user's updated instruction.

| Check | Verified result |
| --- | --- |
| GitHub authentication | Account `ahirm-finarth`, numeric user ID 251194736; token-free HTTPS remote and local noreply identity |
| Initial repository / database | Empty GitHub repository; supplied MySQL had zero tables before migrations |
| Migration | Revision `30af12917573` applied; Alembic check reports no upgrade operations |
| Schema | Nine Smart Trade domain tables plus `smart_trade_alembic_version`; all domain tables utf8mb4; explicit relationships and DECIMAL monetary fields |
| Source fidelity | CSV and workbook contents normalize identically; missing business fields remain nullable |
| Seed | Counts 5 / 12 / 18 / 9 / 6 / 6 / 7 / 14 / 3; repeated seed preserves counts, IDs, data, and persistence timestamps |
| FastAPI | Running server verified health, list, detail, summary; API unknown IDs return 404; all five case pages render persisted records |
| Dashboard | MySQL counts: 5 cases; expected PASS 2, REFER 3, BLOCK 0; four product groups |
| LLM scaffold | Backend-only client and mock tests; optional authenticated model-list diagnostic reachable and configured model listed; no trade processing calls |
| Backend tests | 19 passed, including all three opt-in MySQL integration tests |
| Backend style | Ruff lint and format checks pass |
| Frontend | ESLint, TypeScript/type generation, and Prettier pass |
| Production build | Next.js 16.3.8 build succeeds; dynamic `/` and `/cases/[caseId]` routes |
| Production runtime | Compiled frontend starts and serves MySQL-backed dashboard/case workflows |
| Browser tests | Four passed in both development and production runs: two workflows each at desktop and mobile sizes |
| Visual review | Independent reviewer returned `ship` for dashboard and case overview captures, sampled implementation and reported navigation tests; other tabs were behavior-tested |
| Secret safety | Ignored real environment file; placeholders only in example; tracked files, git historical blobs, frontend client/server build scanned with no real credential material detected |

The backend test run reports one upstream Starlette deprecation warning about the httpx TestClient adapter. It does not affect passing test results. Browser runs report an environment color-output warning. No application check fails.

The supplied dataset contains expected outcomes and historical control data. All such records remain demo references. No decisions, screening, rules, document extraction, or approval actions are implemented.

## Implementation history

Each commit was checked, inspected, scanned for credentials and pushed independently. Documentation finalizes the run in a separate Conventional Commit; use `git log --reverse --oneline` or the GitHub `phase-1` history for its final hash.

```text
71b7476 chore(repo): initialize Smart Trade monorepo foundation
7d6743b feat(api): bootstrap FastAPI service and secure runtime configuration
9ba8c72 feat(db): add MySQL persistence and Smart Trade schema migrations
c76a577 style(db): format initial schema migration
f53196c feat(llm): add reusable model endpoint integration scaffold
1624bf6 feat(data): ingest synthetic Smart Trade case datasets
ce3b7ad feat(api): expose Smart Trade case and dashboard query endpoints
802600a feat(web): bootstrap Smart Trade operations interface
8c73071 feat(web): add API-backed trade case dashboard
5b74ae7 feat(web): add synthetic trade case detail workspace
05bb91e fix(web): contain mobile tables and keep filters readable
7216f2d style(web): format operations interface for maintainability
16284ff test(phase1): validate Smart Trade foundation and seeded workflows
```

Final verification checks that local HEAD equals `origin/phase-1`, no working-tree changes remain, and the remote branch contains the completed history. Nothing is merged into a separate `main` branch as part of this Phase 1 request.
