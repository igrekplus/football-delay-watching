import logging
from datetime import datetime, timedelta
from typing import Any

from config import config
from src.domain.models import MatchAggregate
from src.utils.team_colors import get_team_color

logger = logging.getLogger(__name__)


class FactsFormatter:
    """
    APIから取得した生データを MatchAggregate オブジェクトに整形して流し込むサービス。
    ロジックのみを保持し、外部通信は行わない。
    """

    def format_lineups(
        self, match: MatchAggregate, data: dict[str, Any]
    ) -> list[tuple[int, str, str]]:
        """スタメン情報を整形し、選手詳細取得用のIDリストを返す"""
        if not data.get("response"):
            logger.error(f"No lineup data for match {match.core.id}")
            if hasattr(config, "ERROR_PARTIAL"):
                match.error_status = config.ERROR_PARTIAL
            match.error_status = config.ERROR_PARTIAL
            return []

        # Populate Team Colors
        match.facts.home_team_color = get_team_color(match.core.home_team)
        match.facts.away_team_color = get_team_color(match.core.away_team)

        player_id_name_pairs = []

        for team_data in data.get("response", []):
            team_name = team_data["team"]["name"]
            formation = team_data["formation"]

            # Extract coach info
            coach_name = team_data.get("coach", {}).get("name", "")
            coach_photo = team_data.get("coach", {}).get("photo", "")

            # Extract player data
            start_xi_data = [
                (p["player"]["name"], p["player"]["id"], p["player"].get("number"))
                for p in team_data["startXI"]
            ]
            subs_data = [
                (
                    p["player"]["name"],
                    p["player"]["id"],
                    p["player"].get("number"),
                    p["player"].get("pos", ""),
                )
                for p in team_data["substitutes"]
            ]

            start_xi = [p[0] for p in start_xi_data]
            subs = [p[0] for p in subs_data]

            # Store player numbers
            for name, _, number in start_xi_data:
                if number is not None:
                    match.facts.player_numbers[name] = number

            for name, _, number, pos in subs_data:
                if number is not None:
                    match.facts.player_numbers[name] = number
                if pos:
                    match.facts.player_positions[name] = pos

            # Collect player IDs for details lookup
            player_id_name_pairs.extend(
                [(p[1], p[0], team_name) for p in start_xi_data]
            )
            player_id_name_pairs.extend([(p[1], p[0], team_name) for p in subs_data])

            # Assign to match object
            if team_name == match.core.home_team:
                match.facts.home_formation = formation
                match.facts.home_lineup = start_xi
                match.facts.home_bench = subs
                match.facts.home_manager = coach_name
                match.facts.home_manager_photo = coach_photo
            elif team_name == match.core.away_team:
                match.facts.away_formation = formation
                match.facts.away_lineup = start_xi
                match.facts.away_bench = subs
                match.facts.away_manager = coach_name
                match.facts.away_manager_photo = coach_photo

        return player_id_name_pairs

    def format_injuries(
        self, match: MatchAggregate, data: dict[str, Any]
    ) -> list[tuple[int, str, str]]:
        """怪我人情報を整形し、選手詳細取得用のIDリストを返す"""
        injuries = []
        player_id_name_pairs = []

        for item in data.get("response", []):
            player_id = item["player"].get("id")
            player_name = item["player"]["name"]
            team_name = item["team"]["name"]
            reason = item["player"].get("reason", "Unknown")
            photo = item["player"].get("photo", "")

            injuries.append(
                {
                    "name": player_name,
                    "team": team_name,
                    "reason": reason,
                    "photo": photo,
                }
            )

            if player_id:
                player_id_name_pairs.append((player_id, player_name, team_name))

            if photo:
                match.facts.player_photos[player_name] = photo

        if injuries:
            match.facts.injuries_list = injuries[:5]
            match.facts.injuries_info = ", ".join(
                f"{i['name']}（{i['team']}）： {i['reason']}"
                for i in match.facts.injuries_list
            )
        else:
            match.facts.injuries_list = []
            match.facts.injuries_info = "なし"

        return player_id_name_pairs

    def format_recent_form(
        self, match: MatchAggregate, home_raw: dict[str, Any], away_raw: dict[str, Any]
    ):
        """直近フォーム情報を整形"""
        # 試合開催日の前日までを対象 (Issue #176)
        match_date = match.core.kickoff_at_utc

        match.facts.home_recent_form_details = self._parse_form(
            home_raw, match.core.home_team, match_date
        )
        match.facts.away_recent_form_details = self._parse_form(
            away_raw, match.core.away_team, match_date
        )

        # サマリー集計
        match.facts.home_form_summary = self._calculate_form_summary(
            match.facts.home_recent_form_details
        )
        match.facts.away_form_summary = self._calculate_form_summary(
            match.facts.away_recent_form_details
        )

    def _calculate_form_summary(self, form_details: list[dict]) -> str:
        """勝・分・負の数をカウントしてサマリー文字列を生成"""
        if not form_details:
            return ""

        wins = sum(1 for d in form_details if d.get("result") == "W")
        draws = sum(1 for d in form_details if d.get("result") == "D")
        losses = sum(1 for d in form_details if d.get("result") == "L")

        return f"{wins}勝{draws}分{losses}負"

    def format_h2h(self, match: MatchAggregate, data: dict[str, Any], home_id: int):
        """H2H情報を整形"""
        if not data.get("response"):
            logger.info(
                f"H2H: No history found for {match.core.home_team} vs {match.core.away_team}"
            )
            match.facts.h2h_summary = "対戦履歴なし"
            match.facts.h2h_details = []
            return

        # 日付フィルタリング (直近5年、かつターゲット日以前)
        cutoff_date = config.TARGET_DATE - timedelta(days=5 * 365)
        max_date = config.TARGET_DATE.replace(hour=0, minute=0, second=0, microsecond=0)

        filtered_matches = []
        for h2h_fixture in data["response"]:
            fixture_date_str = h2h_fixture.get("fixture", {}).get("date", "")
            if not fixture_date_str:
                continue

            try:
                fixture_date = datetime.fromisoformat(
                    fixture_date_str.replace("Z", "+00:00")
                )
                if fixture_date < cutoff_date or fixture_date >= max_date:
                    continue
            except (ValueError, TypeError):
                continue

            filtered_matches.append(h2h_fixture)

        # 降順ソート
        filtered_matches.sort(
            key=lambda x: x.get("fixture", {}).get("date", ""), reverse=True
        )

        if not filtered_matches:
            match.facts.h2h_summary = "過去5年間の対戦なし"
            match.facts.h2h_details = []
            return

        h2h_details = []
        home_wins = 0
        away_wins = 0
        draws = 0

        for h2h_fixture in filtered_matches:
            goals = h2h_fixture.get("goals", {})
            teams = h2h_fixture.get("teams", {})

            fixture_date_str = h2h_fixture.get("fixture", {}).get("date", "")[:10]
            competition = h2h_fixture.get("league", {}).get("name", "Unknown")
            league_logo = h2h_fixture.get("league", {}).get("logo") or ""
            home_team_name = teams.get("home", {}).get("name", "")
            home_team_logo = teams.get("home", {}).get("logo") or ""
            away_team_name = teams.get("away", {}).get("name", "")
            away_team_logo = teams.get("away", {}).get("logo") or ""
            home_goals = goals.get("home", 0) or 0
            away_goals = goals.get("away", 0) or 0
            score = f"{home_goals}-{away_goals}"
            fixture_home_id = teams.get("home", {}).get("id")

            # 勝敗判定
            if home_goals == away_goals:
                winner = "draw"
                draws += 1
                result_key = "D"
            elif home_goals > away_goals:
                if fixture_home_id == home_id:
                    winner = match.core.home_team
                    home_wins += 1
                    result_key = "W"
                else:
                    winner = match.core.away_team
                    away_wins += 1
                    result_key = "L"
            else:
                if fixture_home_id == home_id:
                    winner = match.core.away_team
                    away_wins += 1
                    result_key = "L"
                else:
                    winner = match.core.home_team
                    home_wins += 1
                    result_key = "W"

            h2h_details.append(
                {
                    "date": fixture_date_str,
                    "competition": competition,
                    "league_logo": league_logo,
                    "home": home_team_name,
                    "home_logo": home_team_logo,
                    "away": away_team_name,
                    "away_logo": away_team_logo,
                    "score": score,
                    "winner": winner,
                    "result_key": result_key,
                }
            )

        match.facts.h2h_details = h2h_details[:8]
        total = home_wins + draws + away_wins
        match.facts.h2h_summary = f"過去5年間 {total}試合: {match.core.home_team} {home_wins}勝, 引分 {draws}, {match.core.away_team} {away_wins}勝"

    def format_standings(self, match: MatchAggregate, raw_standings: list[dict] | None):
        """
        APIまたはキャッシュから取得した順位表データを整形して MatchFacts にセット
        """
        if not raw_standings:
            match.facts.standings_table = []
            return

        formatted_table = []
        for entry in raw_standings:
            # 必要なフィールドを抽出
            item = {
                "rank": entry.get("rank"),
                "team_id": entry.get("team", {}).get("id"),
                "team_name": entry.get("team", {}).get("name"),
                "team_logo": entry.get("team", {}).get("logo"),
                "points": entry.get("points"),
                "played": entry.get("all", {}).get("played"),
                "won": entry.get("all", {}).get("win"),
                "draw": entry.get("all", {}).get("draw"),
                "lost": entry.get("all", {}).get("lose"),
                "goals_for": entry.get("all", {}).get("goals", {}).get("for"),
                "goals_against": entry.get("all", {}).get("goals", {}).get("against"),
                "goals_diff": entry.get("goalsDiff"),
                "form": entry.get("form"),
                "description": entry.get("description", ""),
            }
            formatted_table.append(item)

        match.facts.standings_table = formatted_table
        logger.info(
            f"Formatted {len(formatted_table)} standings entries for {match.core.competition}"
        )

    def _parse_form(
        self, data: dict[str, Any], team_name: str, match_date: datetime = None
    ) -> list[dict[str, Any]]:
        """個別チームのフォーム情報を解析"""
        if not data.get("response"):
            return []

        finished_statuses = {"FT", "AET", "PEN"}

        # 試合開催日が渡された場合はその前日（00:00:00）を基準に、なければ報告生成日
        if match_date:
            max_date = match_date.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            max_date = config.TARGET_DATE.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        form_details = []

        for fixture_item in data["response"]:
            status = fixture_item.get("fixture", {}).get("status", {}).get("short", "")
            if status not in finished_statuses:
                continue

            fixture_dt_str = fixture_item.get("fixture", {}).get("date", "")
            if fixture_dt_str:
                try:
                    fixture_dt = datetime.fromisoformat(
                        fixture_dt_str.replace("Z", "+00:00")
                    )
                    if fixture_dt >= max_date:
                        continue
                except (ValueError, TypeError):
                    pass

            league_info = fixture_item.get("league", {})
            goals = fixture_item.get("goals", {})
            teams = fixture_item.get("teams", {})

            fixture_date = fixture_item.get("fixture", {}).get("date", "")[:10]

            # 対戦相手とロゴ
            home_team_data = teams.get("home", {})
            away_team_data = teams.get("away", {})

            if home_team_data.get("name") == team_name:
                opponent = away_team_data.get("name", "")
                opponent_logo = away_team_data.get("logo", "")
            else:
                opponent = home_team_data.get("name", "")
                opponent_logo = home_team_data.get("logo", "")

            home_goals = goals.get("home", 0) or 0
            away_goals = goals.get("away", 0) or 0

            # 視点に応じたスコアと勝敗
            is_home = teams.get("home", {}).get("name", "") == team_name
            if is_home:
                score = f"{home_goals}-{away_goals}"
                if home_goals > away_goals:
                    result = "W"
                elif home_goals < away_goals:
                    result = "L"
                else:
                    result = "D"
            else:
                score = f"{away_goals}-{home_goals}"
                if away_goals > home_goals:
                    result = "W"
                elif away_goals < home_goals:
                    result = "L"
                else:
                    result = "D"

            form_details.append(
                {
                    "date": fixture_date,
                    "opponent": opponent,
                    "opponent_logo": opponent_logo,
                    "competition": league_info.get("name", "Unknown"),
                    "round": league_info.get("round", ""),
                    "score": score,
                    "result": result,
                }
            )

        form_details.sort(key=lambda x: x["date"], reverse=True)
        return form_details[:5]
