# FinArth Smart Trade

Phase 1 provides a persisted synthetic trade-case register, operations dashboard, and read-only case workspace. FastAPI queries the supplied MySQL database; Next.js renders those API responses. The frontend contains no hardcoded demo cases.

**Synthetic Demo Data:** expected PASS / REFER / BLOCK outcomes, document confidence, findings, screening signals, and approval events are supplied reference records. Phase 1 does not derive decisions, extract documents, run compliance checks, execute rules, or perform approval actions.

Work is committed to [`phase-1`](https://github.com/ahirm-finarth/smarttrade/tree/phase-1), following the requested Phase 1 branch. The GitHub repository was empty when initialized.

## Prerequisites

- Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).
- Node.js 20.9 or newer and npm; verified locally with Node 22.
- Network access to the supplied MySQL 8-compatible instance and permission to create Smart Trade-owned tables.
- Credentials provided through process environment variables or a local, ignored `.env` at the repository root.

## Fresh clone and setup

```sh
git clone --branch phase-1 https://github.com/ahirm-finarth/smarttrade.git
cd smarttrade
make setup
```

`make setup` installs Python dependencies using `backend/uv.lock` into `backend/.venv` and Node dependencies using `frontend/package-lock.json`. Python setup may also be run with `make setup-backend`; Node setup with `make setup-frontend`.

If your environment already provides credentials, use them directly. Otherwise copy the placeholder file and populate it privately:

```sh
cp .env.example .env
```

Do not overwrite an existing credential file. Never commit real credentials.

## Runtime configuration

Backend settings read the root `.env` automatically; process environment variables override matching file values. Choose **one** database configuration family and remove unused placeholder keys:

| Configuration | Variables |
| --- | --- |
| Preferred MySQL URL | `DATABASE_URL` pointing to MySQL |
| MySQL fields | `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` |
| Supplied DB aliases | `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` |

A MySQL `DATABASE_URL` takes precedence. Otherwise the backend constructs the SQLAlchemy URL internally using PyMySQL and `utf8mb4`. The default port is 3306. Passwords are Pydantic `SecretStr` values; URLs and SQL parameter values are never logged by the application.

`LLM_API_URL`, `LLM_MODEL`, and `LLM_API_KEY` are backend-only settings. Configuration is optional for Phase 1; application startup and case routes do not call the LLM. The supplied `/v1` endpoint supports the optional OpenAI-compatible client. For another endpoint, explicitly set `LLM_PROTOCOL=openai` only after verifying its protocol. Unknown protocols are refused.

The frontend defaults to `http://localhost:8000`. To override, put **only** `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local` or export it before starting/building Next.js. Next.js public values are fixed at build time. Do not copy backend credentials into frontend configuration. `CORS_ORIGINS` is a JSON array and defaults to `http://localhost:3000`.

`GH_TOKEN` was used securely for GitHub authentication during setup; it is not required by either application. Git remotes contain no token.

## MySQL, migrations, and demo import

Inspect connectivity and existing table ownership first:

```sh
make check-db
make migrate
make seed
```

Migrations use `smart_trade_alembic_version`, manage only Smart Trade-owned tables, and exclude unrelated tables from autogeneration. The initial migration is additive. Never reset the supplied database. No Docker or additional database service is required.

The default source is `data/raw/`, which contains nine supplied CSV datasets and their matching workbook. To explicitly import the workbook:

```sh
make seed SOURCE=data/raw/Smart_Trade_Demo_Data.xlsx
```

The import is atomic and idempotent. It validates schema, identifiers, DECIMAL precision and timezone-bearing dates; rejects orphan records; protects non-demo identifier collisions; and reconciles only importer-owned related rows. Missing datasets and unrelated records are preserved. Omitted cases are preserved rather than automatically deleted. See [data/README.md](data/README.md) for source mapping and absent fields.

| Dataset / MySQL table | Imported records |
| --- | ---: |
| `smart_trade_cases` | 5 |
| `smart_trade_case_parties` | 12 |
| `smart_trade_case_documents` | 18 |
| `smart_trade_trade_lines` | 9 |
| `smart_trade_discrepancies` | 6 |
| `smart_trade_risk_events` | 6 |
| `smart_trade_approval_events` | 7 |
| `smart_trade_demo_risk_rules` | 14 |
| `smart_trade_demo_screening_references` | 3 |

The last two tables are passive synthetic reference inventory; their contents are never executed or used for live screening. `smart_trade_alembic_version` stores the schema revision.

## Start the applications

Run these in separate terminals from the repository root:

```sh
make backend
```

```sh
make frontend
```

- Dashboard: http://localhost:3000/
- Case workspace: `http://localhost:3000/cases/{case_id}`; click any case in the register.
- Backend: http://localhost:8000
- API documentation: http://localhost:8000/docs
- Required-database health: http://localhost:8000/health

For the production frontend:

```sh
make build
npm --prefix frontend run start
```

Health returns HTTP 503 when MySQL is unavailable and reports only application status, connectivity, and whether LLM settings are configured. LLM availability does not control readiness. API failures return sanitized messages. Case workspaces show document inventory metadata and read-only historical events; they include no document viewer or processing actions.

## API

| Method | Route | Response |
| --- | --- | --- |
| GET | `/health` | Required MySQL connectivity, safe LLM configuration flag |
| GET | `/api/v1/cases` | Paginated case summaries; `q`, `product`, `outcome`, `limit`, `offset` filters |
| GET | `/api/v1/cases/{case_id}` | Case metadata plus all six related inventories |
| GET | `/api/v1/dashboard/summary` | Database counts, expected outcomes, product distribution |
| GET | `/api/v1/cases/{case_id}/parties` | Party inventory |
| GET | `/api/v1/cases/{case_id}/documents` | Document inventory |
| GET | `/api/v1/cases/{case_id}/trade-lines` | Trade line inventory |
| GET | `/api/v1/cases/{case_id}/discrepancies` | Supplied finding inventory |
| GET | `/api/v1/cases/{case_id}/risk-events` | Supplied risk signals |
| GET | `/api/v1/cases/{case_id}/approvals` | Historical demo events |

API unknown case IDs return 404. Next.js renders the matching not-found screen; streamed page responses can retain HTTP 200 after the loading shell has already been sent. Monetary API fields are decimal strings; the frontend formats them without floating-point conversion. Approval dates are normalized to UTC in MySQL and displayed in IST. Persistence timestamps describe database records, not invented trade events.

## Checks and diagnostics

```sh
make test          # 16 isolated tests; 3 supplied-MySQL tests skipped by default
make test-mysql    # All 19 tests; requires migrated/seeded supplied database
make lint
make typecheck
make build
make secrets
python3 scripts/check_secrets.py --history --frontend-build
make check-llm     # Optional model-list request; sends no trade data
```

For browser checks, keep the backend running. Playwright reuses a running frontend or starts the development frontend:

```sh
cd frontend
npx playwright install chromium
cd ..
make test-e2e
```

The browser suite compares dashboard values and case records with the running API on desktop and mobile, exercises filters, empty states, case navigation, all tabs, keyboard interaction, viewport containment, and unknown cases. Screenshots and traces are ignored. Backend isolated tests use temporary in-memory SQLite solely for test isolation; production and integration tests use the supplied MySQL. `create_all()` appears only in isolated tests; Alembic is the application migration strategy.

The secret scan checks configured credential material, recognizable GitHub tokens, and tracked environment files; optional modes check historical blobs and compiled frontend artifacts. Non-credential LLM placeholder sentinels are excluded to avoid matching ordinary framework identifiers. It supplements inspection and never prints matching content or secret values.

## Architecture and repository layout

```text
frontend/                 Next.js App Router, TypeScript, Tailwind
  app/                    Dashboard, case route, loading/error/not-found states
  components/             Shell, register, metrics, reusable tables, case tabs
  lib/                    Central API client and exact decimal/date formatting
  types/                  Typed API response contracts
  tests/                  Desktop/mobile Playwright workflows
backend/
  app/api/v1/             Thin read-only FastAPI routes
  app/core/               Secure environment settings
  app/db/                 Engine, sessions, database readiness
  app/models/             SQLAlchemy source-grounded domain and UTC handling
  app/schemas/            Pydantic response schemas
  app/repositories/       MySQL queries and eager-loaded case detail
  app/services/           Case queries and transactional demo import
  app/integrations/llm/   Optional reusable client, unused by trade workflows
  app/scripts/            Safe database, seed, and model diagnostics
  alembic/                Scoped schema migration
  tests/                  API, configuration, seed, LLM and MySQL tests
data/raw/                 Original supplied CSVs and XLSX
scripts/                  Secret inspection
docs/                     Phase 1 validation evidence
Makefile                  Local development and checks
```

Design conventions are recorded in [DESIGN.md](DESIGN.md) and `.impeccable/design.json`. [docs/PHASE1_VALIDATION.md](docs/PHASE1_VALIDATION.md) records the checks actually run. The [branch commit history](https://github.com/ahirm-finarth/smarttrade/commits/phase-1) contains individually pushed Conventional Commits.

## Deferred work

Phase 2 and later own document intelligence/OCR, extraction, evidence graphs, documentary examination, rule execution, screening integrations, calculated decisions, maker/checker actions, agents, Smart Insights, SWIFT and core-banking integration. Phase 1 ends at the persisted read-only product foundation.
