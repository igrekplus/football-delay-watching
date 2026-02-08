import logging
import re
from typing import Any

from src.clients.llm_client import LLMClient
from src.domain.models import MatchAggregate

logger = logging.getLogger(__name__)


class TributeGenerator:
    """
    LLMを使用して同国対決や古巣対決のトリビアを生成するサービス。
    検出ロジックと生成ロジックの両方を保持する。
    """

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()

    def detect_and_generate_same_country(self, match: MatchAggregate):
        """同国対決を検出し、関係性テキストを生成"""
        matchups = self._detect_same_country_matchups(match)
        match.facts.same_country_matchups = matchups

        if matchups:
            logger.info(
                f"Detected same country matchups: {[m['country'] for m in matchups]}"
            )
            match.facts.same_country_text = self.llm.generate_same_country_trivia(
                home_team=match.core.home_team,
                away_team=match.core.away_team,
                matchups=matchups,
            )
        else:
            match.facts.same_country_text = ""

    def generate_former_club_trivia(self, match: MatchAggregate):
        """古巣対決トリビアを生成（ハルシネーション対策のファクトチェック付き）"""
        home_players = match.facts.home_lineup + match.facts.home_bench
        away_players = match.facts.away_lineup + match.facts.away_bench

        raw_trivia = self.llm.generate_former_club_trivia(
            home_team=match.core.home_team,
            away_team=match.core.away_team,
            home_players=home_players,
            away_players=away_players,
            match_date=match.core.match_date_local,
        )

        if not raw_trivia:
            match.facts.former_club_trivia = ""
            return

        # 1. Gemini Groundingの出典番号を削除
        cleaned_trivia = re.sub(r"\s*\[\d+(?:,\s*\d+)*\]", "", raw_trivia)

        # 2. パースして個別のエントリに分割
        from src.parsers.former_club_parser import parse_former_club_text

        entries = parse_former_club_text(
            cleaned_trivia,
            home_team=match.core.home_team,
            away_team=match.core.away_team,
        )

        if not entries:
            match.facts.former_club_trivia = ""
            return

        # 3. 各エントリをファクトチェック（別のLLM呼び出し）
        valid_entries = []
        for entry in entries:
            # 古巣と主張されているチームを特定
            # 現所属がホームなら、古巣はアウェイ。逆も然り。
            is_home_player = any(p in entry.name for p in home_players)
            opponent_team = (
                match.core.away_team if is_home_player else match.core.home_team
            )
            current_team = (
                match.core.home_team if is_home_player else match.core.away_team
            )

            is_valid, reason = self.llm.fact_check_former_club(
                player_name=entry.name,
                current_team=current_team,
                opponent_team=opponent_team,
                home_team=match.core.home_team,
                away_team=match.core.away_team,
            )

            if is_valid:
                valid_entries.append(entry)
            else:
                logger.warning(
                    f"[TRIBUTE] Former club entry rejected: {entry.name} - {reason}"
                )

        # 4. 有効なエントリのみでテキストを再構成
        if valid_entries:
            reconstructed_parts = []
            for entry in valid_entries:
                reconstructed_parts.append(
                    f"**{entry.name}** ({entry.team})\n{entry.description}"
                )

            match.facts.former_club_trivia = "\n\n".join(reconstructed_parts)
            logger.info(
                f"Generated and fact-checked former club trivia: {len(valid_entries)}/{len(entries)} valid"
            )
        else:
            match.facts.former_club_trivia = ""
            logger.info("No valid former club entries found after fact-check")

    def _detect_same_country_matchups(
        self, match: MatchAggregate
    ) -> list[dict[str, Any]]:
        """同国対決を検出"""
        home_players = match.facts.home_lineup + match.facts.home_bench
        away_players = match.facts.away_lineup + match.facts.away_bench

        home_by_country = {}
        away_by_country = {}

        for player in home_players:
            country = match.facts.player_nationalities.get(player, "")
            if country:
                home_by_country.setdefault(country, []).append(player)

        for player in away_players:
            country = match.facts.player_nationalities.get(player, "")
            if country:
                away_by_country.setdefault(country, []).append(player)

        # 除外する国籍
        excluded_countries = {"England", "Spain", "Germany", "France", "Italy"}
        common_countries = (
            set(home_by_country.keys()) & set(away_by_country.keys())
        ) - excluded_countries

        matchups = []
        for country in common_countries:
            matchups.append(
                {
                    "country": country,
                    "home_players": home_by_country[country],
                    "away_players": away_by_country[country],
                }
            )

        return matchups
