import shutil
import unittest
from datetime import datetime
from pathlib import Path

from src.utils.standings_cache import (
    CACHE_DIR,
    CACHE_FILE,
    get_week_key,
    has_standings,
    load_standings,
    save_standings,
)


class TestStandingsCache(unittest.TestCase):
    def setUp(self):
        # テスト用ディレクトリを作成
        self.test_cache_dir = Path(__file__).parent / "test_standings"
        if self.test_cache_dir.exists():
            shutil.rmtree(self.test_cache_dir)
        self.test_cache_dir.mkdir(parents=True, exist_ok=True)

        # モジュールの変数を一時的にテスト用に置換
        self.original_cache_dir = CACHE_DIR
        self.original_cache_file = CACHE_FILE

        import src.utils.standings_cache as sc

        sc.CACHE_DIR = self.test_cache_dir
        sc.CACHE_FILE = self.test_cache_dir / "standings_cache.csv"

    def tearDown(self):
        # テスト終了後にクリーンアップ
        if self.test_cache_dir.exists():
            shutil.rmtree(self.test_cache_dir)

        # オリジナルの値に戻す
        import src.utils.standings_cache as sc

        sc.CACHE_DIR = self.original_cache_dir
        sc.CACHE_FILE = self.original_cache_file

    def test_get_week_key(self):
        # 2026-02-23 (Monday) -> 2026-02-23
        dt = datetime(2026, 2, 23)
        self.assertEqual(get_week_key(dt), "2026-02-23")

        # 2026-02-25 (Wednesday) -> 2026-02-23
        dt = datetime(2026, 2, 25)
        self.assertEqual(get_week_key(dt), "2026-02-23")

        # 2026-03-01 (Sunday) -> 2026-02-23
        dt = datetime(2026, 3, 1)
        self.assertEqual(get_week_key(dt), "2026-02-23")

    def test_save_and_load(self):
        week_key = "2026-02-23"
        league = "EPL"
        standings = [
            {
                "rank": 1,
                "team": {"id": 1, "name": "Team A", "logo": "logoA"},
                "points": 10,
                "all": {
                    "played": 5,
                    "win": 3,
                    "draw": 1,
                    "lose": 1,
                    "goals": {"for": 10, "against": 5},
                },
                "goalsDiff": 5,
                "form": "WWDLW",
                "description": "Top",
            }
        ]

        # 初期状態はFalse
        self.assertFalse(has_standings(week_key, league))

        # 保存
        save_standings(week_key, league, standings)

        # 保存後はTrue
        self.assertTrue(has_standings(week_key, league))

        # 読み込み
        loaded = load_standings(week_key, league)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["team"]["name"], "Team A")
        self.assertEqual(loaded[0]["rank"], 1)
        self.assertEqual(loaded[0]["all"]["goals"]["for"], 10)


if __name__ == "__main__":
    unittest.main()
