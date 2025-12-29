# Refactoring Implementation Plan (Issues #80, #81, #82)

## Goal
Decouple `main.py`, `match_processor.py`, and `cache_warmer.py` to improve maintainability and readability.
- **Issue #80**: Flatten `main.py` by extracting the workflow into a UseCase/Workflow class.
- **Issue #81**: Split `match_processor.py` into distinct components (Fetcher, Ranker, Selector).
- **Issue #82**: Refactor `cache_warmer.py` to separate execution policy (time/quota) from logic.

## Proposed Changes

### 1. Refactor `match_processor.py` (#81)
Break down `MatchProcessor` responsibilities.

#### [NEW] `src/clients/api_football_client.py`
- Move raw API fetching logic here.
- Methods: `get_fixtures(league_id, season, date)`, `get_squad(team_id)`, `get_player(player_id, season)`.
- Handles `CachingHttpClient` creation.

#### [NEW] `src/domain/match_ranker.py`
- Move `_assign_rank` logic here.
- Class `MatchRanker` with `assign_rank(match: MatchData)`.

#### [NEW] `src/domain/match_selector.py`
- Move `select_matches` logic here.
- Class `MatchSelector` with `select(matches, limit)`.

#### [MODIFY] `src/match_processor.py`
- Orchestrates the above components.
- Uses `ApiFootballClient` to fetch.
- Uses `MatchRanker` to rank.
- Uses `MatchSelector` to select.
- Uses `TimeWindowService` (see below) to filter.

### 2. Refactor `cache_warmer.py` (#82)

#### [NEW] `src/utils/execution_policy.py`
- Handles operational rules.
- Method: `should_continue(quota_remaining) -> bool`
- Method: `is_within_time_limit(limit_hour, limit_minute) -> bool`

#### [MODIFY] `src/cache_warmer.py`
- Use `ExecutionPolicy` for time/quota checks.
- Use `ApiFootballClient` for data fetching (re-use client).
- Simplify `run()` method.

### 3. Refactor `main.py` (#80)

#### [NEW] `src/workflows/generate_guide_workflow.py`
- Encapsulates the main business logic flow.
- Class `GenerateGuideWorkflow`.
- Method `run(dry_run, mock_mode)`.
- Orchestrates: `MatchProcessor` -> `FactsService` -> `NewsService` -> `YouTubeService` -> `ReportGenerator` -> `HtmlGenerator` -> `EmailService` -> `CacheWarmer`.

#### [MODIFY] `main.py`
- Simplifies to just argument parsing, logging setup, and calling `GenerateGuideWorkflow.run()`.

## Verification Plan
1. **Mock Mode Test**: Run `python main.py --dry-run` with `USE_MOCK_DATA=True` to verify the flow remains consistent.
2. **Debug Mode Test**: Run `python main.py` with `DEBUG_MODE=True` (and mock=False if possible, or just rely on mock if quota is low) to ensure components wire up correctly.
3. **Check Outputs**: Verify logs, reports, and HTML generation still happen.
