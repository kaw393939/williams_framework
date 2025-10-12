# Sprint Delivery Plan –| Sprint | Goal | Committed Stories | Completed | Carry-over | Health | Notes |
|--------|------|-------------------|-----------|------------|-------|-------|
| 0 | Test infrastructure foundations | S0-101, S0-102, S0-103, S0-104 | S0-101, S0-102, S0-103, S0-104 | — | 🟢 | Streamlit harness + async clock + plugin doubles + segmented CI delivered |
| 1 | Pipeline enhancements | S1-201, S1-202, S1-203, S1-204 | S1-201, S1-202, S1-203, S1-204 | — | 🟢 | PDF + YouTube extractors, telemetry instrumentation, batch CLI ingest complete; 98% coverage maintained |
| 2 | Plugins & prompts | S2-301, S2-302, S2-303, S2-304, S2-305 | S2-301, S2-302, S2-303, S2-304, S2-305 | — | 🟢 | Plugin registry, prompt loader, lifecycle hooks, feature flags, sample plugin complete; 98% coverage maintained |-10-10

## 1. Cadence & Team Setup
- **Sprint length:** 2 weeks (10 working days).
- **Working hours:** Align with core overlap for pair programming and async updates.
- **Roles:** Delivery lead (coordinates backlog), QA/TDD steward (ensures red-first discipline), Engineering contributors, Documentation owner.
- **Rituals:**
  - Sprint Planning (Day 1 AM): review backlog, confirm capacity, write red tests for committed stories.
  - Mid-sprint Sync (Day 6 AM): surface blockers, adjust capacity.
  - Demo & Retro (Day 10 PM): showcase green suites, update blueprint docs.
  - Daily async standup: blockers, what moved to green, next red test.

## 2. Release Milestones
| Milestone | Target Sprint | Outcomes |
|-----------|----------------|----------|
| Stabilize test infrastructure | Sprint 0 | Factories, fixtures, CI wiring for UI/async tests |
| Pipeline enhancements shipped | Sprint 1 | Batch ingest, telemetry, retry strategy |
| Plugin runtime operational | Sprint 2 | Registry, prompts, sample plugin end-to-end |
| Streamlit presentation GA | Sprint 3 | Tier dashboards, search UI, caching |
| Background workers live | Sprint 4 | Scheduler, digest + maintenance jobs |
| Knowledge graph preview | Sprint 5 | Builder/resolver, UI integration |
| Ops hardening complete | Sprint 6 | Scripts, MinIO migration, Qdrant cleanup |

## 3. Sprint Scoreboard (Update Each Planning Session)
| Sprint | Goal | Committed Stories | Completed | Carry-over | Health | Notes |
|--------|------|-------------------|-----------|------------|-------|-------|
| 0 | Test infrastructure foundations | S0-101, S0-102, S0-103, S0-104 | S0-101, S0-102, S0-103, S0-104 | — | 🟢 | Streamlit harness + async clock + plugin doubles + segmented CI delivered |
| 1 | Pipeline enhancements | S1-201 | S1-201 | | � | PDF extractor + CLI ingest verified with tests |
| 2 | Plugins & prompts | | | | | |
| 3 | Presentation layer | | | | | |
| 4 | Background workers | | | | | |
| 5 | Knowledge graph | | | | | |
| 6 | Ops hardening | | | | | |

## 4. Sprint 0 – Test Infrastructure Foundations
> **Goal:** Enable fast red/green cycles across UI, async workers, and plugin suites.

- **Primary workstreams:** shared factories, Streamlit harness, async clock utilities.
- **Tracking template:** fill in story tables with IDs, estimates, red tests, acceptance criteria, dependencies, and status after planning.

### Story Table (populate during planning)
| Story ID | Title | Type | Tests to Write First | Acceptance Criteria | Dependencies | Status |
|----------|-------|------|----------------------|---------------------|--------------|--------|
| S0-101 | Streamlit testing harness bootstrap | Enabler | Unit: factory builds deterministic Streamlit state<br>Integration: headless harness mounts home page | Headless runner mounts app without external services; fixtures documented in `tests/README.md`; CI job `pytest -m ui` green. | Pipeline in-memory repos | [x] |
| S0-102 | Async virtual clock fixture | Enabler | Unit: virtual clock advances deterministically | Fixture exposes `advance()` and `now()` helpers for worker tests; example usage captured in `tests/workers/README.md`. | None | [x] |
| S0-103 | Plugin and prompt test doubles | Enabler | Unit: stub plugin emits deterministic hook output<br>Unit: prompt snapshot loader verifies checksum | Shared stub available under `tests/plugins/stubs.py`; snapshot fixtures stored under `tests/fixtures/prompts/`. | Pipeline factories | [x] |
| S0-104 | CI lane segmentation and coverage gates | Chore | Unit: workflow assertion for segmented `pytest` markers | GitHub Actions workflow runs unit/integration/ui matrices; coverage ≥90% enforced; docs updated with run commands. | Existing CI workflow | [x] |

## 5. Sprint 1 – Pipeline Enhancements
> **Goal:** Expand pipeline resilience and multi-source ingest while preserving ≥90% coverage.

- **Primary workstreams:** multi-source extractors, telemetry, batch CLI.
- **Tracking template:** populate during planning.

### Story Table
| Story ID | Title | Type | Tests to Write First | Acceptance Criteria | Dependencies | Status |
|----------|-------|------|----------------------|---------------------|--------------|--------|
| S1-201 | PDF extractor ingestion | Feature | Unit: PDF metadata normalization rules<br>Integration: pipeline ingest writes PDF content | CLI ingests sample PDF and stores processed summary and tier; failures logged gracefully. | S0-101, existing pipeline core | [x] |
| S1-202 | YouTube transcript extractor | Feature | Unit: transcript parsing fallback logic<br>Integration: pipeline ingest with transcript stub | Supports transcript + fallback to description; telemetry includes duration and channel metadata; docs updated. | S0-101 | [x] |
| S1-203 | Pipeline telemetry instrumentation | Feature | Unit: structured telemetry schema validation<br>Integration: loader logs MinIO failures | All pipeline errors emit structured events consumed by workers; JSON schema captured under `docs/telemetry.md`. | S0-104 | [x] |
| S1-204 | Batch CLI ingest with partial failure reporting | Feature | Integration: CLI batch run processes multiple URLs<br>E2E: sample feed run emits partial failure report | `poetry run pipeline --input sample-feed.json` outputs success/error summary; failing item does not halt run; progress logged. | S1-201, S1-202, S1-203 | [x] |

## 6. Sprint 2 – Plugins & Prompts
> **Goal:** Deliver plugin lifecycle and prompt validation with red-first coverage.

### Story Table
| Story ID | Title | Type | Tests to Write First | Acceptance Criteria | Dependencies | Status |
|----------|-------|------|----------------------|---------------------|--------------|--------|
| S2-301 | Plugin registry duplicate guard | Feature | Unit: duplicate ID raises `PluginError` with context | Registry prevents duplicate registrations, surfaces actionable error message, documented in developer guide. | S0-103 | [x] |
| S2-302 | Prompt loader validation | Feature | Unit: missing template raises configuration error<br>Integration: snapshot comparison for default prompt | Prompts autoload with checksum snapshots; configuration update documented. | S0-103 | [x] |
| S2-303 | Plugin lifecycle execution | Feature | Integration: stub plugin runs `on_load` → `before_store` hooks<br>Integration: hook output recorded in telemetry | Lifecycle hooks executed within pipeline with deterministic stub; hook output persisted to telemetry. | S2-301, S1-203 | [x] |
| S2-304 | Feature flag gating | Chore | Integration: disabling `settings.enable_plugins` skips registry bootstrap | Settings toggle disables plugin discovery safely; docs updated with configuration instructions. | S2-301 | [x] |
| S2-305 | Sample plugin acceptance flow | Feature | E2E: pipeline run with sample plugin modifies content<br>Integration: CLI telemetry records plugin events | Sample plugin packaged, documented, end-to-end test ensures hook modifies content and logs. | S2-303, S2-304 | [x] |

## 7. Sprint 3 – Presentation Layer
> **Goal:** Launch Streamlit app with deterministic UI tests and caching behavior.

### Story Table
| Story ID | Title | Type | Tests to Write First | Acceptance Criteria | Dependencies | Status |
|----------|-------|------|----------------------|---------------------|--------------|--------|
| S3-401 | Navigation structure helper | Feature | Unit: nav builder returns ordered entries | Sidebar lists planned pages with icons and QA IDs cached in constants. | S0-101 | [ ] |
| S3-402 | Library tier filter UI | Feature | Integration: tier dropdown options match config thresholds | Streamlit page displays tier filter matching pipeline tiers; selection filters table snapshot. | S3-401 | [ ] |
| S3-403 | Search caching and telemetry | Feature | Integration: search sets Redis keys and emits telemetry | UI search caches embeddings, logs cache hits/misses; config documented. | S1-203, S0-101 | [ ] |
| S3-404 | End-to-end Streamlit ingest flow | Feature | E2E: headless UI form submission updates library count | User submits content via UI, sees success toast, library count increments; screenshot archived. | S3-402, S3-403, S1-204 | [ ] |

## 8. Sprint 4 – Background Workers
> **Goal:** Introduce scheduler, digest, and maintenance workers with reliable tests.

### Story Table
| Story ID | Title | Type | Tests to Write First | Acceptance Criteria | Dependencies | Status |
|----------|-------|------|----------------------|---------------------|--------------|--------|
| S4-501 | Scheduler concurrency guard | Feature | Unit: job semaphore enforces max concurrency | Scheduler enforces max parallel jobs, logs when queueing; configurable via settings. | S0-102 | [ ] |
| S4-502 | Durable queue abstraction | Enabler | Unit: queue enqueues and dequeues deterministically<br>Integration: worker consumes in-memory queue stub | In-memory durable queue available for worker tests; interface documented for future adapters. | S0-102 | [ ] |
| S4-503 | Digest worker payload builder | Feature | Integration: digest worker builds snapshot payload | Worker produces JSON payload (no SMTP), stored for audit; docs include schema. | S4-501, S4-502, S1-203 | [ ] |
| S4-504 | Cron simulation harness | Feature | Integration: virtual clock triggers scheduled jobs<br>E2E: failure retry emits structured telemetry | Virtual clock fixture drives scheduler to trigger jobs; retries logged with exponential backoff metrics. | S4-501, S4-502 | [ ] |

## 9. Sprint 5 – Knowledge Graph
> **Goal:** Provide knowledge graph builder, resolver, and UI integration.

### Story Table
| Story ID | Title | Type | Tests to Write First | Acceptance Criteria | Dependencies | Status |
|----------|-------|------|----------------------|---------------------|--------------|--------|
| S5-601 | Knowledge graph builder deduplication | Feature | Unit: builder collapses duplicate node keys | Builder produces canonical node set without duplicates; docstrings updated. | S1-204 data feed | [ ] |
| S5-602 | Relationship weight normalization | Feature | Unit: relationship scores normalized to 0-1 | Relationships expose normalized weights; regression snapshot stored. | S5-601 | [ ] |
| S5-603 | Graph repository persistence | Feature | Integration: `networkx` graph persisted to JSON store | Graph snapshot saved and reloadable without data loss; adapter documented for Postgres upgrade. | S5-601 | [ ] |
| S5-604 | Graph query service | Feature | Integration: service returns top related content for tag | Query returns deterministic ordering; API documented for UI. | S5-603 | [ ] |
| S5-605 | Dashboard graph visualization | Feature | E2E: Streamlit graph page renders nodes/edges | Streamlit page renders interactive graph using testing harness; screenshot archived. | S3-404, S5-604 | [ ] |

## 10. Sprint 6 – Ops Hardening
> **Goal:** Finalize scripts, storage migrations, and cleanup reliability.

### Story Table
| Story ID | Title | Type | Tests to Write First | Acceptance Criteria | Dependencies | Status |
|----------|-------|------|----------------------|---------------------|--------------|--------|
| S6-701 | MinIO bucket naming fix and migration | Feature | Unit: bucket suffix helper generates deterministic names<br>Integration: migration script transforms legacy buckets | New helper applied across loaders; migration script idempotent and logged. | S1-203 | [ ] |
| S6-702 | YAML loader schema validation | Feature | Unit: invalid config raises descriptive error | All configs validated against schema; docs include troubleshooting. | None | [ ] |
| S6-703 | CLI `--dry-run` safety | Feature | Integration: dry-run leaves no persistent side effects | CLI flag prevents writes while logging actions; regression tests added. | S6-702 | [ ] |
| S6-704 | Environment bootstrap script | Feature | E2E: bootstrap creates buckets, tables, prompts idempotently | Script provisions required services; repeated runs produce no changes; documentation updated. | S6-701, S6-702 | [ ] |
| S6-705 | Maintenance worker MinIO cleanup | Feature | Integration: cleanup removes orphaned objects with new helper | Worker removes orphaned objects, emits telemetry, respects bucket naming. | S4-501, S4-502, S6-701 | [ ] |
| S6-706 | Qdrant delete helper resilience | Feature | Unit: delete ignores NotFound and classifies errors | Delete helper handles expected exceptions; logs structured failures. | None | [ ] |
| S6-707 | Qdrant cleanup worker | Feature | E2E: background job removes stale vectors and emits metrics | Cleanup job runs on schedule, records success/failure counters; observability documented. | S6-706, S4-504 | [ ] |

## 11. Definition of Ready / Done Checklist
- **Ready:** Story has clear user value, red-test list, fixtures identified, dependencies resolved, estimate added.
- **Done:** All pre-written tests green, coverage ≥90%, docs updated, demo recorded, plan updated with status + learnings.

## 12. Progress Log
Use this table to record updates whenever work advances.

| Date | Sprint | Story ID | Update | Next Step |
|------|--------|----------|--------|-----------|
| 2025-10-10 | 0 | S0-101 | Factory + `run_app` harness in place; unit + UI tests passing at 96.8% coverage. | Draft red tests for S0-102 async virtual clock fixture. |
| 2025-10-10 | 0 | S0-102 | Virtual clock fixture + docs delivered; worker unit tests in place with 96.8% suite coverage. | Identify next red tests for S0-103 plugin doubles. |
| 2025-10-10 | 0 | S0-103 | Stub plugin + prompt snapshot loader implemented with unit tests and docs; suite coverage steady at 96.8%. | Shift focus to S0-104 CI segmentation planning. |
| 2025-10-11 | 1 | S1-201 | PDF extractor implemented with unit + integration tests; pipeline stores PDF content through stub loader. | Extend coverage to CLI ingest flow and error handling. |
| 2025-10-11 | 1 | S1-201 | CLI defaults to PDF extractor; CLI unit/integration suites cover success + failure logging. | Prepare red tests for S1-202 YouTube transcript extractor. |
| 2025-10-10 | 0 | S0-104 | CI workflow split into unit/integration/UI lanes with coverage gate tests and docs updated; full suite green at 96.8%. | Move to Sprint 1 pipeline enhancements planning. |
| 2025-10-12 | 1 | S1-202 | YouTube transcript extractor implemented with unit, integration, and CLI tests; pipeline and CLI support transcript and fallback to description; all tests green at 97.9% coverage. | Update documentation and begin S1-203 telemetry instrumentation. |
| 2025-10-12 | 1 | S1-203 | Pipeline telemetry instrumentation complete: created docs/telemetry.md schema, app/core/telemetry.py logger, instrumented all pipeline error paths (extractor/transformer/loader) with structured event emission; all tests green at 98.0% coverage. | Begin S1-204 batch CLI ingest implementation. |
| 2025-10-12 | 1 | S1-204 | Batch CLI ingest with partial failure reporting complete: CLI accepts multiple URLs, continues on per-URL errors, emits JSON batch summary with success/failure counts; backward compatible with single-URL mode; 370 tests pass at 98.0% coverage. | Sprint 1 pipeline enhancements complete; update sprint scoreboard and prepare Sprint 2 planning. |
| 2025-10-12 | 2 | S2-301 | Plugin registry duplicate guard complete: implemented PluginRegistry with register(), get(), all() methods; duplicate prevention with PluginError; 5 unit tests green; 375 tests pass at 98.02% coverage. | Begin S2-302 prompt loader validation. |
| 2025-10-12 | 2 | S2-302 | Prompt loader validation complete: implemented PromptLoader with checksum validation, caching, and ConfigurationError handling; created config/prompts/summarize.prompt template; 5 unit tests green; 380 tests pass at 98.05% coverage. | Begin S2-303 plugin lifecycle execution. |
| 2025-10-12 | 2 | S2-303 | Plugin lifecycle execution complete: added plugin_registry param to ContentPipeline; implemented initialize() and before_store() hooks with telemetry emission; 4 integration tests green; 384 tests pass at 98.02% coverage. | Begin S2-304 feature flag gating. |
| 2025-10-12 | 2 | S2-304 | Feature flag gating complete: added get_settings() function to config; pipeline checks enable_plugins flag before executing hooks; 5 integration tests green; 389 tests pass at 98.03% coverage. | Begin S2-305 sample plugin acceptance flow. |
| 2025-10-12 | 2 | S2-305 | Sample plugin acceptance flow complete: created EnrichmentPlugin sample in app/plugins/samples/; plugin enriches content with tags; 6 E2E tests green; 395 tests pass at 98.07% coverage. | Sprint 2 plugins & prompts complete; update sprint scoreboard and prepare Sprint 3 planning. |

## 13. Tracking & Update Protocol
- **Status markers:** use `[ ]` (not started), `[~]` (in progress), `[x]` (done) inside each story row. Update during standups or whenever work begins/ends.
- **Sprint Scoreboard:** at planning, populate `Committed Stories` and add health notes. Mid-sprint, adjust `Health` (🟢 / 🟡 / 🔴) and record carry-over risk.
- **Progress Log:** every material change (new red test, green build, blocker) gets a dated entry referencing sprint and story ID.
- **Definition of Done:** before marking `[x]`, confirm tests in the "Tests to Write First" column exist and pass, docs are updated, and coverage remains ≥90%.
- **Change control:** when scope shifts, edit both this sprint plan and `docs/tdd-plan-2025-10-10.md` in the same session so documentation stays aligned.
