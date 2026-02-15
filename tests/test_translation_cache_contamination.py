import unittest

from src.clients.cache_store import CacheStore
from src.utils.name_translator import NameTranslator
from src.utils.team_name_translator import TeamNameTranslator


class InMemoryCacheStore(CacheStore):
    def __init__(self):
        self.data = {}

    def read(self, path: str) -> dict | None:
        return self.data.get(path)

    def write(self, path: str, data: dict) -> None:
        self.data[path] = data

    def exists(self, path: str) -> bool:
        return path in self.data

    def delete(self, path: str) -> bool:
        if path in self.data:
            del self.data[path]
            return True
        return False


class TestTranslationCacheContamination(unittest.TestCase):
    def test_name_translator_ignores_mock_cache_in_non_mock_mode(self):
        store = InMemoryCacheStore()
        translator = NameTranslator(cache_store=store, use_mock=False)
        name = "Nico Gonzalez"
        path = translator._get_cache_path(name)
        store.write(
            path,
            {
                "original": name,
                "full": "[MOCK]Nico Gonzalez",
                "short": "Nico Gonzalez",
                "katakana": "[MOCK]Nico Gonzalez",
            },
        )

        translator._batch_translate = lambda names: {
            "Nico Gonzalez": {"full": "ニコ・ゴンサレス", "short": "N・ゴンサレス"}
        }

        result = translator._get_translations([name])
        self.assertEqual(result[name], "ニコ・ゴンサレス")
        cached = store.read(path)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["full"], "ニコ・ゴンサレス")

    def test_team_translator_ignores_mock_cache_in_non_mock_mode(self):
        store = InMemoryCacheStore()
        translator = TeamNameTranslator(cache_store=store, use_mock=False)
        team_name = "Salford City"
        path = translator._get_cache_path(team_name)
        store.write(
            path,
            {
                "original": team_name,
                "katakana": "[MOCK]Salford City",
                "keywords": ["[MOCK]Salford City"],
            },
        )

        translator._translate_team = lambda name: {
            "katakana": "サルフォード・シティ",
            "keywords": ["サルフォード"],
        }

        result = translator._get_translation_data(team_name)
        self.assertIsNotNone(result)
        self.assertEqual(result["katakana"], "サルフォード・シティ")
        cached = store.read(path)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["katakana"], "サルフォード・シティ")


if __name__ == "__main__":
    unittest.main()
