#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.getcwd())

import logging

from src.domain.models import MatchAggregate, MatchCore, MatchFacts
from src.youtube_service import YouTubeService

# ロギング設定
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def test_rank_filter():
    service = YouTubeService(api_key="dummy")

    # 1. Sランクの試合
    match_s = MatchAggregate(
        core=MatchCore(
            id="1",
            home_team="Team S",
            away_team="Away S",
            competition="C",
            kickoff_jst="T",
            kickoff_local="T",
            rank="S",
            is_target=True,
        ),
        facts=MatchFacts(),
    )

    # 2. Aランクの試合
    match_a = MatchAggregate(
        core=MatchCore(
            id="2",
            home_team="Team A",
            away_team="Away A",
            competition="C",
            kickoff_jst="T",
            kickoff_local="T",
            rank="A",
            is_target=True,
        ),
        facts=MatchFacts(),
    )

    # 3. Absoluteランクの試合
    match_abs = MatchAggregate(
        core=MatchCore(
            id="3",
            home_team="Team Abs",
            away_team="Away Abs",
            competition="C",
            kickoff_jst="T",
            kickoff_local="T",
            rank="Absolute",
            is_target=True,
        ),
        facts=MatchFacts(),
    )

    # 4. Bランクの試合（スキップされるべき）
    match_b = MatchAggregate(
        core=MatchCore(
            id="4",
            home_team="Team B",
            away_team="Away B",
            competition="C",
            kickoff_jst="T",
            kickoff_local="T",
            rank="B",
            is_target=True,
        ),
        facts=MatchFacts(),
    )

    # 5. ランクなし（スキップされるべき）
    match_none = MatchAggregate(
        core=MatchCore(
            id="5",
            home_team="Team None",
            away_team="Away None",
            competition="C",
            kickoff_jst="T",
            kickoff_local="T",
            rank="",
            is_target=True,
        ),
        facts=MatchFacts(),
    )

    matches = [match_s, match_a, match_abs, match_b, match_none]

    print("\n--- Testing YouTube rank filter ---")

    # get_videos_for_match をモック化して、呼ばれたかどうかを確認
    call_count = 0

    def mock_get_videos(match):
        nonlocal call_count
        call_count += 1
        print(
            f"  [CALL] get_videos_for_match called for {match.core.home_team} (rank={match.core.rank})"
        )
        return {"kept": [], "removed": [], "overflow": []}

    service.get_videos_for_match = mock_get_videos

    results = service.process_matches(matches)

    print(f"\nTotal calls to get_videos_for_match: {call_count}")
    print(f"Total results entries: {len(results)}")

    assert call_count == 3, f"Expected 3 calls (S, A, Absolute), but got {call_count}"
    assert "Team S vs Away S" in results
    assert "Team A vs Away A" in results
    assert "Team Abs vs Away Abs" in results
    assert "Team B vs Away B" not in results
    assert "Team None vs Away None" not in results

    print("\n✅ Rank filter test PASSED!")


if __name__ == "__main__":
    test_rank_filter()
