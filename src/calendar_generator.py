import logging
import os
from datetime import datetime, timedelta
from typing import Any

import pytz

from config import config
from src.clients.api_football_client import ApiFootballClient
from src.utils.datetime_util import DateTimeUtil

logger = logging.getLogger(__name__)


class CalendarGenerator:
    """試合日程カレンダー生成クラス"""

    def __init__(self):
        self.api = ApiFootballClient()
        self.leagues = getattr(config, "LEAGUE_INFO", [])
        if not self.leagues:
            # Fallback if LEAGUE_INFO is not populated
            self.leagues = [
                {"name": name, "id": id, "display_name": name}
                for name, id in config.LEAGUE_IDS.items()
            ]

    def generate(self) -> str:
        """カレンダーHTMLを生成し、保存する"""
        fixtures = self._fetch_all_fixtures()
        timeline_data = self._build_timeline(fixtures)
        html = self._render_html(timeline_data)

        output_path = os.path.join("public", "calendar.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"Calendar generated at {output_path}")
        return output_path

    def _fetch_all_fixtures(self) -> list[dict[str, Any]]:
        """対象リーグの試合データを取得し、3週間分にフィルタリングする"""
        all_fixtures = []

        # 3週間の範囲を計算 (JST)
        now = DateTimeUtil.now_jst()
        # 今週の日曜日
        start_of_week = now - timedelta(days=(now.weekday() + 1) % 7)
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

        # 前週の日曜日
        start_date = start_of_week - timedelta(weeks=1)
        # 再来週の土曜日の終わり
        end_date = start_of_week + timedelta(weeks=2) - timedelta(seconds=1)

        logger.info(f"Calendar range: {start_date} to {end_date}")

        # シーズン計算
        season = now.year if now.month >= 7 else now.year - 1

        for league in self.leagues:
            league_id = league["id"]
            league_name = league["name"]

            logger.info(f"Fetching fixtures for {league_name} (ID: {league_id})")
            data = self.api.get_fixtures(league_id, season)

            count = 0
            for item in data.get("response", []):
                fixture = item["fixture"]
                kickoff_utc = datetime.fromisoformat(
                    fixture["date"].replace("Z", "+00:00")
                )
                kickoff_jst = DateTimeUtil.to_jst(kickoff_utc)

                if start_date <= kickoff_jst <= end_date:
                    # 現地時間の計算
                    fixture_tz_str = fixture.get("timezone", "UTC")
                    try:
                        fixture_tz = pytz.timezone(fixture_tz_str)
                        kickoff_local = kickoff_utc.astimezone(fixture_tz)
                    except Exception:
                        kickoff_local = kickoff_utc  # フォールバック

                    # 必要な情報を抽出
                    match_info = {
                        "fixture_id": fixture["id"],
                        "date": kickoff_jst.strftime("%Y-%m-%d"),
                        "kickoff_jst": kickoff_jst,
                        "kickoff_local": kickoff_local,
                        "timezone": fixture_tz_str,
                        "home_team": item["teams"]["home"]["name"],
                        "away_team": item["teams"]["away"]["name"],
                        "home_logo": item["teams"]["home"]["logo"],
                        "away_logo": item["teams"]["away"]["logo"],
                        "competition": league.get("display_name", league_name),
                        "competition_name": league_name,  # フィルタ用
                        "competition_logo": item["league"]["logo"],
                        "venue": fixture.get("venue", {}).get("name", ""),
                        "round": item["league"].get("round", ""),
                    }
                    all_fixtures.append(match_info)
                    count += 1

            logger.info(f"Found {count} fixtures for {league_name} in range")

        return all_fixtures

    def _build_timeline(self, fixtures: list[dict[str, Any]]) -> dict:
        """データを週別・リーグ別のタイムライン構造に変換し、ソートする"""
        # 3週間の開始日を再計算 (金曜開始)
        now = DateTimeUtil.now_jst()
        # 金曜日 = weekday() 4
        days_since_friday = (now.weekday() - 4) % 7
        start_of_this_week = now - timedelta(days=days_since_friday)
        start_of_this_week = start_of_this_week.replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        weeks = []
        for i in range(-1, 2):  # 前週, 今週, 来週
            s = start_of_this_week + timedelta(weeks=i)
            e = s + timedelta(days=6)
            label = "今週" if i == 0 else ("先週" if i == -1 else "来週")
            weeks.append(
                {
                    "start": s,
                    "end": e,
                    "label": f"{label} ({s.month}/{s.day} - {e.month}/{e.day})",
                    "leagues": {},
                }
            )

        # league_order は _render_html で定義されているため、ここでは不要
        # league_order = ["CL", "EPL", "LALIGA", "FA", "COPA", "EFL"]

        for f in fixtures:
            kickoff = f["kickoff_jst"]
            league_name = f["competition_name"]

            # どの週に属するか判定
            target_week = None
            for w in weeks:
                if (
                    w["start"]
                    <= kickoff
                    <= w["end"].replace(hour=23, minute=59, second=59)
                ):
                    target_week = w
                    break

            if not target_week:
                continue

            if league_name not in target_week["leagues"]:
                target_week["leagues"][league_name] = []

            target_week["leagues"][league_name].append(f)

        # 各リーグの試合をソート
        for w in weeks:
            for league_name in w["leagues"]:
                w["leagues"][league_name].sort(key=lambda x: x["kickoff_jst"])

        return weeks

    def _render_html(self, weeks_data: list) -> str:
        """HTMLを生成する（週別・リーグ横並びレイアウト）"""
        league_order = ["CL", "EPL", "LALIGA", "FA", "COPA", "EFL"]
        leagues_display = {
            league["name"]: league.get("display_name", league["name"])
            for league in self.leagues
        }

        html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>試合日程カレンダー | サッカー観戦ガイド</title>
    <link rel="stylesheet" href="/assets/report_styles.css">
    <link rel="stylesheet" href="/assets/calendar_styles.css">
</head>
<body>
    <div class="calendar-container">
        <header class="calendar-header">
            <nav class="nav-back"><a href="/" class="back-link">← トップページに戻る</a></nav>
            <h1>📅 試合日程カレンダー</h1>
        </header>

        <div class="filter-container">
            <span class="filter-title">表示するコンペティション:</span>
            <div class="filter-buttons">
                <button onclick="selectAll(true)">全選択</button>
                <button onclick="selectAll(false)">全解除</button>
            </div>
            <div class="filter-checkboxes">
                {" ".join([f'<label><input type="checkbox" class="league-filter" value="{name}" checked onchange="applyFilter()"> {leagues_display.get(name, name)}</label>' for name in league_order if name in leagues_display])}
            </div>
        </div>

        <div class="weeks-wrapper">
"""

        for week in weeks_data:
            if not any(league in week["leagues"] for league in league_order):
                continue

            html += f"""
            <section class="week-section">
                <h2 class="week-header" onclick="toggleWeekSection(this)">🗓️ {week["label"]} <span class="fold-icon">▼</span></h2>
                <div class="league-columns week-content">
"""

            for league_name in league_order:
                if league_name not in week["leagues"]:
                    continue

                matches = week["leagues"][league_name]
                display_name = leagues_display.get(league_name, league_name)

                html += f"""
                    <div class="league-column" data-league="{league_name}">
                        <h3 class="league-column-header">{display_name}</h3>
                        <div class="match-list">
"""
                for m in matches:
                    dt_jst = m["kickoff_jst"]
                    dt_local = m["kickoff_local"]
                    tz_str = m.get("timezone", "UTC")
                    # タイムゾーン略称を生成（例: Europe/London -> UK）
                    tz_abbr = (
                        tz_str.split("/")[-1][:3].upper()
                        if "/" in tz_str
                        else tz_str[:3].upper()
                    )

                    weekday = ["月", "火", "水", "木", "金", "土", "日"][
                        dt_jst.weekday()
                    ]
                    local_time_str = dt_local.strftime("%H:%M")
                    jst_time_str = dt_jst.strftime("%H:%M")
                    date_str = f"{dt_jst.month}/{dt_jst.day}({weekday})"
                    time_display = f"{local_time_str}({tz_abbr}) / {jst_time_str}(JST)"

                    html += f"""
                            <div class="match-row-container" data-fixture-id="{m["fixture_id"]}" onclick="toggleAccordion(this)">
                                <div class="match-row-main">
                                    <span class="match-date-compact">{date_str}</span>
                                    <span class="match-time-compact">{time_display}</span>
                                    <div class="match-teams-compact">
                                        <div class="compact-logo-wrapper"><img src="{m["home_logo"]}" class="team-logo-compact"></div>
                                        <span class="team-name-compact">{m["home_team"]}</span>
                                        <span class="team-name-compact">{m["away_team"]}</span>
                                        <div class="compact-logo-wrapper"><img src="{m["away_logo"]}" class="team-logo-compact"></div>
                                    </div>
                                </div>
                                <div class="match-accordion-content">
                                    <div class="detail-item">🏆 {m["round"]}</div>
                                    <div class="detail-item">📍 {m["venue"]}</div>
                                </div>
                            </div>"""

                html += """
                        </div>
                    </div>"""

            html += """
                </div>
            </section>"""

        html += (
            """
        </div>

        <footer class="timestamp">
            ページ更新時刻: """
            + DateTimeUtil.format_display_timestamp()
            + """
        </footer>
    </div>

    <script src="/assets/calendar_filter.js"></script>
</body>
</html>
"""
        )
        return html


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gen = CalendarGenerator()
    gen.generate()
