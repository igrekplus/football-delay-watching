import logging

from config import config
from src.clients.api_football_client import ApiFootballClient
from src.domain.models import MatchAggregate

logger = logging.getLogger(__name__)


class PredictionService:
    """
    予測データ取得サービス (Issue #199)

    API-Football から勝敗予測パーセントと得点者オッズを取得し、
    MatchAggregate オブジェクトを補完する。
    """

    def __init__(self, api_client: ApiFootballClient = None):
        self.api = api_client or ApiFootballClient()

    def enrich_matches(self, matches: list[MatchAggregate]):
        """is_target 試合のみに予測データを付加"""
        if config.USE_MOCK_DATA:
            logger.info("Skipping prediction enrichment in mock mode")
            return

        target_matches = [m for m in matches if m.core.is_target]
        if not target_matches:
            return

        logger.info(f"Enriching {len(target_matches)} matches with prediction data")
        for match in target_matches:
            self._enrich_single(match)

    def _enrich_single(self, match: MatchAggregate):
        """1試合に対して予測データを取得・パースする"""
        fixture_id = match.core.id
        logger.info(f"Fetching prediction/odds for fixture {fixture_id}")

        # 1. 勝敗予測 (Predictions)
        try:
            pred_data = self.api.fetch_predictions(fixture_id)
            if pred_data.get("response"):
                # 通常 response は単一要素のリスト
                prediction = pred_data["response"][0].get("predictions", {})
                percent = prediction.get("percent", {})
                if percent:
                    match.facts.prediction_percent = {
                        "home": percent.get("home", "0%"),
                        "draw": percent.get("draw", "0%"),
                        "away": percent.get("away", "0%"),
                    }
                    logger.debug(
                        f"Set prediction percent for {fixture_id}: {match.facts.prediction_percent}"
                    )
        except Exception as e:
            logger.warning(f"Failed to fetch predictions for {fixture_id}: {e}")

        # 2. オッズ (Odds - Scorer Markets)
        try:
            odds_data = self.api.fetch_odds(fixture_id)
            if odds_data.get("response"):
                # response[0].bookmakers[]
                bookmakers = odds_data["response"][0].get("bookmakers", [])
                if bookmakers:
                    # 最初に見つかったブックメーカー（または指定IDがあればそれ）を使用
                    # fetch_odds で既に bookmaker=8 で絞っている想定
                    bets = bookmakers[0].get("bets", [])
                    self._parse_scorer_odds(match, bets)
        except Exception as e:
            logger.warning(f"Failed to fetch odds for {fixture_id}: {e}")

    def _parse_scorer_odds(self, match: MatchAggregate, bets: list[dict]):
        """得点者市場のオッズをパースして格納"""
        target_markets = {
            "Anytime Goal Scorer": "Anytime Goal Scorer",
            "First Goal Scorer": "First Goal Scorer",
            "Last Goal Scorer": "Last Goal Scorer",
        }

        match.facts.scorer_odds = []

        for bet in bets:
            market_name = bet.get("name")
            if market_name in target_markets:
                values = bet.get("values", [])
                # 上位5名に制限 (Issue #199 フィードバック)
                top_values = []
                for v in values[:5]:
                    top_values.append({"player": v.get("value"), "odd": v.get("odd")})

                if top_values:
                    match.facts.scorer_odds.append(
                        {"market": target_markets[market_name], "values": top_values}
                    )

        if match.facts.scorer_odds:
            logger.debug(
                f"Set scorer odds for {match.core.id}: {len(match.facts.scorer_odds)} markets"
            )
