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

        # マーケット名ごとに最新のソート済みデータを保持するための辞書
        parsed_markets = {}

        for bet in bets:
            market_name = bet.get("name")
            if market_name in target_markets:
                values = bet.get("values", [])
                # オッズを数値に変換できる項目のみを抽出し、昇順ソートして上位5名を採用 (Issue #204)
                valid_values = []
                for v in values:
                    odd_str = v.get("odd")
                    try:
                        odd_float = float(odd_str) if odd_str is not None else None
                        if odd_float is not None:
                            valid_values.append(
                                {
                                    "player": v.get("value"),
                                    "odd": odd_str,
                                    "_sort_key": odd_float,
                                }
                            )
                    except (ValueError, TypeError):
                        continue

                if not valid_values:
                    continue

                # オッズ昇順にソート（低いほど上位）
                valid_values.sort(key=lambda x: x["_sort_key"])

                top_values = []
                for v in valid_values[:5]:
                    top_values.append({"player": v["player"], "odd": v["odd"]})

                if top_values:
                    # 同じマーケット名が複数回登場した場合は、最新のもので上書き（重複排除）
                    parsed_markets[market_name] = {
                        "market": target_markets[market_name],
                        "values": top_values,
                    }

        # 元の定義順（Anytime -> First -> Last）を尊重しつつリスト化
        match.facts.scorer_odds = []
        for market_key in target_markets:
            if market_key in parsed_markets:
                match.facts.scorer_odds.append(parsed_markets[market_key])

        if match.facts.scorer_odds:
            logger.debug(
                f"Set scorer odds for {match.core.id}: {len(match.facts.scorer_odds)} markets"
            )
