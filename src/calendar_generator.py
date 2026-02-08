import logging
import os
from datetime import datetime, timedelta
from typing import Any

import pytz

from config import config
from settings.calendar_data_loader import get_calendar_info
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
        # 再来週の土曜日の終わり (+3 weeks total range from start_of_this_week)
        # 実際には 4週間分: 先週(1), 今週(1), 来週(1), 再来週(1)
        end_date = start_of_week + timedelta(weeks=3) - timedelta(seconds=1)

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
                        "commentary": get_calendar_info(fixture["id"]),
                    }
                    all_fixtures.append(match_info)
                    count += 1

            logger.info(f"Found {count} fixtures for {league_name} in range")

        return all_fixtures

    def _build_timeline(self, fixtures: list[dict[str, Any]]) -> dict:
        """データを週別・リーグ別のタイムライン構造に変換し、ソートする (UTC基準)"""
        # 3週間の開始日を再計算 (UTC基準で月曜開始)
        # MECEにするため、UTCの週単位（月〜日）で区切る
        now_utc = datetime.now(pytz.UTC)
        # 月曜日 = weekday() 0
        days_since_monday = now_utc.weekday()
        start_of_this_week = now_utc - timedelta(days=days_since_monday)
        start_of_this_week = start_of_this_week.replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        weeks = []
        for i in range(-1, 3):  # 先週, 今週, 来週, 再来週 (計4週間)
            s = start_of_this_week + timedelta(weeks=i)
            e = s + timedelta(weeks=1) - timedelta(seconds=1)

            # ラベル用の表示 (JST換算)
            s_jst = DateTimeUtil.to_jst(s)
            e_jst = DateTimeUtil.to_jst(e)

            # 「今週」などの相対表記を廃止し、日付範囲（曜日付き）にする
            weekday_s = ["月", "火", "水", "木", "金", "土", "日"][s_jst.weekday()]
            weekday_e = ["月", "火", "水", "木", "金", "土", "日"][e_jst.weekday()]
            label = f"{s_jst.month}/{s_jst.day}({weekday_s}) - {e_jst.month}/{e_jst.day}({weekday_e})"
            weeks.append(
                {
                    "start": s,
                    "end": e,
                    "label": label,
                    "leagues": {},
                }
            )

        for f in fixtures:
            # kickoff_utc は無いので kickoff_jst を UTC に変換
            kickoff_jst = f["kickoff_jst"]
            kickoff_utc = DateTimeUtil.to_utc(kickoff_jst)
            league_name = f["competition_name"]

            # どの週に属するか判定
            target_week = None
            for w in weeks:
                if w["start"] <= kickoff_utc <= w["end"]:
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
                    dt_utc = DateTimeUtil.to_utc(dt_jst)

                    weekday_jst = ["月", "火", "水", "木", "金", "土", "日"][
                        dt_jst.weekday()
                    ]
                    weekday_utc = ["月", "火", "水", "木", "金", "土", "日"][
                        dt_utc.weekday()
                    ]

                    jst_display = f"JST {dt_jst.month}/{dt_jst.day}({weekday_jst}) {dt_jst.strftime('%H:%M')}"
                    utc_display = f"(UTC: {dt_utc.month}/{dt_utc.day}({weekday_utc}) {dt_utc.strftime('%H:%M')})"

                    html += f"""
                            <div class="match-row-container" data-fixture-id="{m["fixture_id"]}" onclick="toggleAccordion(this)">
                                <div class="match-row-main">
                                    <div class="match-time-combined">
                                        <span class="match-time-jst">{jst_display}</span>
                                        <span class="match-time-utc">{utc_display}</span>
                                    </div>
                                    <div class="match-teams-compact">
                                        <div class="compact-logo-wrapper"><img src="{m["home_logo"]}" class="team-logo-compact"></div>
                                        <span class="team-name-compact">{m["home_team"]}</span>
                                        <span class="vs-text">vs</span>
                                        <span class="team-name-compact">{m["away_team"]}</span>
                                        <div class="compact-logo-wrapper"><img src="{m["away_logo"]}" class="team-logo-compact"></div>
                                        {f'<a href="{m["commentary"]["report_link"]}" class="report-link-inline" onclick="event.stopPropagation()">📄 Report</a>' if m.get("commentary") and m["commentary"].get("report_link") else ""}
                                    </div>
                                    <div class="match-meta-info">
                                        {f'<div class="detail-item commentary-info">🎙️ 解説: {m["commentary"]["commentator"]} / {m["commentary"]["announcer"]}</div>' if m.get("commentary") and (m["commentary"].get("commentator") or m["commentary"].get("announcer")) else ""}
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
