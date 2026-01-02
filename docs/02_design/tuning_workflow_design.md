# API Tuning Workflow Design

This document outlines the design for the API tuning workflow, intended to optimize the performance of YouTube, Google Custom Search, and Gemini (LLM) integrations.

## 1. Objectives

-   **Efficiency**: Minimize API quota usage while maximizing relevance.
-   **Quality**: Ensure search results and generated content are accurate, relevant, and spoiler-free.
-   **Maintainability**: Separate tuning tools from production code, but ensure they test the *actual* production logic.
-   **Workflow**: Provide a structured way for developers (and agents) to iterate on tuning.

## 2. Directory Structure

We will create a new directory `scripts/tuning/` to house the tuning scripts. This separates them from simple healthchecks and core functionality.

```
scripts/tuning/
├── tune_youtube.py       # Refactored from healthcheck/check_youtube_queries.py
├── tune_news_search.py   # Test news search queries (Google Custom Search)
└── tune_gemini.py        # Test LLM prompts (Summary, Preview, Spoiler Check)
```

## 3. Tuning Scripts Design

### 3.1. YouTube Tuning (`tune_youtube.py`)

*   **Purpose**: Verify that YouTube search queries return relevant videos (Highlights, Full Match, Training, etc.) and that filters work correctly.
*   **Logic**:
    *   Import `src.youtube_service.YouTubeService`.
    *   Accept CLI arguments for Match (Team A vs Team B), Date, and Mode (Training/Highlights).
    *   Use `YouTubeService.search_videos_raw` or specific methods to fetch results.
    *   Apply `YouTubePostFilter` explicitly to show what *would* be kept vs removed.
    *   Display "Flagged" keywords (e.g. "HIGHLIGHTS", "FULL MATCH") to help visual verification.
*   **Configurability**:
    *   Target logic: `settings/search_specs.py` and `src/youtube_filter.py`.

### 3.2. News Search Tuning (`tune_news_search.py`)

*   **Purpose**: Verify that Google Custom Search returns pre-match news articles relevant to the specific match.
*   **Logic**:
    *   Import `src.clients.google_search_client.GoogleSearchClient`.
    *   Accept CLI arguments for Teams and Competition.
    *   Execute `search_news` and `search_interviews`.
    *   Print Title, URL, Snippet, and Published Date.
    *   Highlight keywords that might indicate "post-match" (spoilers) or "irrelevant".
*   **Configurability**:
    *   Target logic: `src/clients/google_search_client.py` (Query building).

### 3.3. Gemini Tuning (`tune_gemini.py`)

*   **Purpose**: Verify prompts for News Summary, Tactical Preview, and Spoiler Checking.
*   **Logic**:
    *   Import `src.clients.llm_client.LLMClient`.
    *   **Modes**:
        *   `summary`: Generate pre-match summary.
        *   `preview`: Generate tactical preview.
        *   `spoiler`: Check specific text for spoilers.
    *   **Data Source**:
        *   To save Search API quota and ensure reproducibility, this script should support:
            *   `--articles-file <json_path>`: Load articles from a local JSON file (captured from `tune_news_search.py` or manually created).
            *   `--fetch-live`: (Optional) Call Search API live (chains with Search Client).
*   **Configurability**:
    *   Target logic: `src/clients/llm_client.py` (Propmpts).

## 4. Agent Workflow (.agent/workflows/api-tuning.md)

A workflow file to guide the agent (and user) through the tuning process.

**Steps:**
1.  **YouTube Tuning**: Run `tune_youtube.py`, check results, edit `settings/search_specs.py`.
2.  **Search Tuning**: Run `tune_news_search.py`, check results, edit `src/clients/google_search_client.py`.
3.  **Data Capture**: Run `tune_news_search.py --save articles.json` to capture test data.
4.  **Prompts Tuning**: Run `tune_gemini.py --articles-file articles.json`, check output, edit `src/clients/llm_client.py`.

## 5. Roles & Responsibilities

| Component | Responsibility | Location |
| (Script) | Run tuning, Print formatted output, Mock/Load data | `scripts/tuning/` |
| (Main Code) | Define Queries, Prompts, Business Logic | `src/`, `settings/` |
| (Workflow) | Guide the process | `.agent/workflows/` |

**Note**: The scripts should *never* contain the query/prompt logic itself. They must import it from the Main Code. If the Main Code currently buries logic inside large methods, refactoring to expose that logic (or allow dependency injection) is part of the implementation.

## 6. Implementation Steps

1.  Create `scripts/tuning/` directory.
2.  Implement `tune_youtube.py` (based on `check_youtube_queries.py` but cleaner imports).
3.  Implement `tune_news_search.py` (making sure `GoogleSearchClient` exposes necessary methods).
4.  Implement `tune_gemini.py` (adding `--articles-file` support).
5.  Create `.agent/workflows/api-tuning.md`.
6.  Verify by running each script.
