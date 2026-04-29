import unittest
from unittest.mock import MagicMock, patch

from config import config
from src.domain.models import MatchAggregate, MatchCore
from src.news_service import NewsService

PSG_BAYERN_PREVIEW_WITH_PAST_RESULTS = """
パリ・サンジェルマン（PSG）とバイエルン・ミュンヘンがUEFAチャンピオンズリーグ準決勝ファーストレグで激突する。両チームともに直近のリーグ戦では好調を維持し、万全の状態でこの大一番に臨む。

現欧州王者であるPSGは、今季もその強さを見せつけている。リーグ・アンでは首位を独走し、直近のアンジェ戦でも3-0で勝利を収め、その勢いはとどまるところを知らない。チャンピオンズリーグにおいても、これまでモナコ、チェルシーを撃破し、準々決勝ではリヴァプールを合計スコア4-0で圧倒する盤石の戦いぶりで準決勝へと駒を進めた。

対するバイエルン・ミュンヘンも、ドイツの絶対王者として揺るぎない地位を築いている。直近のマインツ戦では3点差をひっくり返す劇的な4-3の勝利を収め、チームの士気は最高潮に達している。

両チームは昨年のリーグフェーズで対戦しており、その際はバイエルンが2-1で勝利を収めている。しかし、この準決勝は、緻密な戦術と個の能力がぶつかり合う、まさに頂上決戦となるだろう。パリの地で、どちらが優位に立つのか、その行方に注目が集まる。
""".strip()


class TestNewsSpoilerRegression(unittest.TestCase):
    def setUp(self):
        self.original_transfer_flag = config.ENABLE_TRANSFER_NEWS
        self.original_mock_flag = config.USE_MOCK_DATA
        config.ENABLE_TRANSFER_NEWS = False
        config.USE_MOCK_DATA = False

    def tearDown(self):
        config.ENABLE_TRANSFER_NEWS = self.original_transfer_flag
        config.USE_MOCK_DATA = self.original_mock_flag

    def _create_psg_bayern_match(self):
        core = MatchCore(
            id="1540841",
            home_team="Paris Saint Germain",
            away_team="Bayern München",
            competition="CL",
            kickoff_jst="2026/04/29 04:00 JST",
            kickoff_local="2026-04-28 19:00 Local",
            is_target=True,
        )
        return MatchAggregate(core=core)

    def test_psg_bayern_preview_with_past_results_is_not_hidden(self):
        """過去試合の結果を含むPSG/Bayernプレビューは対象試合結果でなければ表示する。"""
        mock_llm = MagicMock()
        mock_llm.check_spoiler.return_value = (
            True,
            "対象試合の結果に触れていない",
            [],
        )
        service = NewsService(llm_client=mock_llm)
        match = self._create_psg_bayern_match()

        with (
            patch.object(
                service,
                "_generate_summary",
                return_value=PSG_BAYERN_PREVIEW_WITH_PAST_RESULTS,
            ),
            patch.object(
                service, "_generate_tactical_preview", return_value="tactical"
            ),
            patch.object(service, "_process_interviews"),
        ):
            service.process_news([match])

        self.assertEqual(
            match.preview.news_summary,
            PSG_BAYERN_PREVIEW_WITH_PAST_RESULTS,
        )
        self.assertNotIn("表示を控えています", match.preview.news_summary)
        mock_llm.check_spoiler.assert_called_once_with(
            PSG_BAYERN_PREVIEW_WITH_PAST_RESULTS,
            "Paris Saint Germain",
            "Bayern München",
        )

    def test_psg_bayern_contradictory_verdict_without_evidence_is_not_hidden(self):
        """実ログで出た is_safe=false/evidence空 の矛盾判定は隠さない。"""
        mock_llm = MagicMock()
        mock_llm.check_spoiler.return_value = (
            False,
            "対象試合の結果には言及していません。",
            [],
        )
        service = NewsService(llm_client=mock_llm)
        match = self._create_psg_bayern_match()

        with (
            patch.object(
                service,
                "_generate_summary",
                return_value=PSG_BAYERN_PREVIEW_WITH_PAST_RESULTS,
            ),
            patch.object(
                service, "_generate_tactical_preview", return_value="tactical"
            ),
            patch.object(service, "_process_interviews"),
            self.assertLogs("src.news_service", level="WARNING") as cm,
        ):
            service.process_news([match])

        self.assertEqual(
            match.preview.news_summary,
            PSG_BAYERN_PREVIEW_WITH_PAST_RESULTS,
        )
        self.assertTrue(any("inconsistent_verdict" in line for line in cm.output))


if __name__ == "__main__":
    unittest.main()
