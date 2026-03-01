import logging
import re

from config import config
from src.domain.models import MatchAggregate
from src.formatters import (
    MatchInfoFormatter,
    MatchupFormatter,
    PlayerFormatter,
    YouTubeSectionFormatter,
)
from src.parsers import (
    parse_former_club_text,
    parse_key_player_text,
    parse_matchup_text,
)
from src.utils.api_stats import ApiStats
from src.utils.datetime_util import DateTimeUtil
from src.utils.formation_image import get_formation_layout_data
from src.utils.player_profile import (
    build_player_profile_id,
    parse_player_profile_sections,
)

logger = logging.getLogger(__name__)


class ReportGenerator:
    WEB_IMAGE_DIR = "public/reports"

    def __init__(self):
        self.player_formatter = PlayerFormatter()
        self.match_info_formatter = MatchInfoFormatter()
        self.youtube_formatter = YouTubeSectionFormatter()
        self.matchup_formatter = MatchupFormatter()

    def generate_all(
        self,
        matches: list[MatchAggregate],
        youtube_videos: dict[str, list[dict]] = None,
        youtube_stats: dict[str, int] = None,
    ) -> list[dict]:
        """
        全試合レポートを生成（新方式: 1試合=1レポート）
        """
        if youtube_videos is None:
            youtube_videos = {}
        if youtube_stats is None:
            youtube_stats = {"api_calls": 0, "cache_hits": 0}

        # 共通セクションを生成
        excluded_section = self._generate_excluded_section(matches, youtube_stats)

        # 各試合のレポートを生成
        generation_datetime = DateTimeUtil.format_filename_datetime()

        report_list = []
        target_matches = [m for m in matches if m.core.is_target]

        for match in target_matches:
            markdown_content, image_paths = self.generate_single_match(
                match, youtube_videos, excluded_section
            )

            # MatchCore に get_report_filename があるか、MatchAggregate にあるか
            # model.py を見ると MatchAggregate に実装されているのでそのまま
            filename = match.get_report_filename(generation_datetime)

            report_list.append(
                {
                    "match": match,
                    "markdown_content": markdown_content,
                    "image_paths": image_paths,
                    "filename": filename,
                }
            )

            logger.info(
                f"Generated report for: {match.core.home_team} vs {match.core.away_team} -> {filename}"
            )

        return report_list

    def generate_single_match(
        self,
        match: MatchAggregate,
        youtube_videos: dict[str, list[dict]],
        excluded_section: str,
    ) -> tuple:
        """
        1試合分のHTMLレポートを生成（選手名カタカナ変換込み）
        """
        logger.info(
            f"[REPORT] Generating single match: {match.core.home_team} vs {match.core.away_team}"
        )
        from config import config
        from src.template_engine import render_template
        from src.utils.name_translator import NameTranslator

        # デバッグ/モックモードの見出し設定
        mode_prefix = ""
        mode_banner = ""
        if config.USE_MOCK_DATA:
            mode_prefix = "[MOCK] "
            mode_banner = '<div class="mode-banner mode-banner-mock">🧪 MOCK MODE - このレポートはモックデータです</div>'
        elif config.DEBUG_MODE:
            mode_prefix = "[DEBUG] "
            mode_banner = '<div class="mode-banner mode-banner-debug">🔧 DEBUG MODE - このレポートはデバッグ用です</div>'

        # 生成日時
        from src.utils.datetime_util import DateTimeUtil

        timestamp = DateTimeUtil.format_display_timestamp()

        # 選手名をカタカナに変換（フォーメーション図の短縮名用にも必要）
        player_names = self._extract_player_names(match)
        translator = NameTranslator()

        image_paths = []
        match_report_context, match_images = self._get_match_report_context(
            match, youtube_videos
        )
        image_paths.extend(match_images)

        # 追加情報の統合
        match_report_context.update(
            {
                "mode_prefix": mode_prefix,
                "mode_banner": mode_banner,
                "timestamp": timestamp,
                "excluded_section": excluded_section,
                "competition_display": "Premier League"
                if match.core.competition == "EPL"
                else match.core.competition,
            }
        )

        # テンプレートでレンダリング
        html_content = render_template("report.html", **match_report_context)

        # 選手名をカタカナに変換（全体）
        if player_names:
            html_content = translator.translate_names_in_html(
                html_content, player_names
            )

        logger.info(
            f"[REPORT] Single match report completed: {match_report_context.get('filename', 'unknown')}"
        )
        return html_content, image_paths

    def _build_player_profile_modal_html(self, match: MatchAggregate) -> str:
        """選手プロフィールのモーダル HTML を生成する。"""
        from src.template_engine import render_template

        profiles = []
        for player_name, profile in sorted(match.facts.player_profiles.items()):
            sections = parse_player_profile_sections(profile)
            if not sections:
                continue
            profiles.append(
                {
                    "name": player_name,
                    "profile_id": build_player_profile_id(player_name),
                    "sections": sections,
                }
            )

        return render_template("partials/player_profile_modal.html", profiles=profiles)

    def _generate_excluded_section(
        self, matches: list[MatchAggregate], youtube_stats: dict[str, int]
    ) -> str:
        """選外試合リストとAPI使用状況のセクションを生成（HTML形式）"""
        excluded = [m for m in matches if not m.core.is_target]

        html_parts = ['<div class="debug-info">']
        html_parts.append("<h3>選外試合リスト</h3>")
        if not excluded:
            html_parts.append("<p>なし</p>")
        else:
            html_parts.append("<ul>")
            for match in excluded:
                html_parts.append(
                    f"<li>{match.core.home_team} vs {match.core.away_team} （{match.core.competition}）… {match.core.selection_reason}</li>"
                )
            html_parts.append("</ul>")

        html_parts.append("<h3>API使用状況</h3>")
        api_table = ApiStats.format_table()  # Markdown table
        # Convert Markdown table to HTML
        html_parts.append(self._markdown_table_to_html(api_table))
        html_parts.append(
            "<p><small>*Gmail API: OAuth認証済みアカウントの送信制限</small></p>"
        )
        html_parts.append("</div>")

        return "\n".join(html_parts)

    def _markdown_table_to_html(self, md_table: str) -> str:
        """Markdown テーブルを HTML テーブルに変換"""
        lines = [line.strip() for line in md_table.strip().split("\n") if line.strip()]
        if not lines:
            return ""

        html = ['<table class="api-stats-table">']
        for i, line in enumerate(lines):
            if line.startswith("|---") or line.startswith("| ---"):
                continue  # Skip separator line
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            tag = "th" if i == 0 else "td"
            row_tag = "thead" if i == 0 else "tbody"
            if i == 0:
                html.append(f"<{row_tag}><tr>")
            elif i == 1 or (i > 1 and "</tbody>" not in html[-1]):
                if i == 1:
                    html.append("<tbody>")
                html.append("<tr>")
            for cell in cells:
                # Convert Markdown links to HTML
                cell = re.sub(
                    r"\[([^\]]+)\]\(([^)]+)\)",
                    r'<a href="\2" target="_blank">\1</a>',
                    cell,
                )
                html.append(f"<{tag}>{cell}</{tag}>")
            html.append("</tr>")
            if i == 0:
                html.append(f"</{row_tag}>")
        html.append("</tbody>")
        html.append("</table>")
        return "\n".join(html)

    def _format_form_details_table(self, form_details: list) -> str:
        """直近試合詳細テーブルをHTML形式で生成"""
        from src.template_engine import render_template

        return render_template("partials/form_table.html", form_details=form_details)

    def _get_match_report_context(
        self, match: MatchAggregate, youtube_videos: dict[str, list[dict]]
    ) -> tuple:
        """
        1試合分のレポート用コンテキストデータを生成

        Returns:
            (context_dict, image_paths)
        """
        import markdown as md_lib

        from src.template_engine import render_template
        from src.utils.name_translator import NameTranslator

        image_paths = []

        # デバッグ/モックモードの見出し設定
        if config.USE_MOCK_DATA:
            pass
        elif config.DEBUG_MODE:
            pass

        # 生成日時
        from src.utils.datetime_util import DateTimeUtil

        DateTimeUtil.format_display_timestamp()

        # コンテキストデータの準備
        image_paths = []

        # 選手名をカタカナに変換（フォーメーション図の短縮名用にも必要）
        player_names = self._extract_player_names(match)
        translator = NameTranslator()
        # フォーメーション図用の短縮名辞書を取得
        short_names_dict = translator.get_short_names(player_names)

        # 【重要】選手名カタカナ変換マップを取得し、player_photosを拡張する
        # これにより、LLMがカタカナで出力した選手名でも写真を表示できるようになる
        translations = translator._get_translations(player_names)
        player_photos_extended = dict(match.facts.player_photos)
        for eng_name, jp_name in translations.items():
            if eng_name in match.facts.player_photos and jp_name:
                player_photos_extended[jp_name] = match.facts.player_photos[eng_name]

        print(
            f"DEBUG: Home Logo: {match.core.home_logo}, Away Logo: {match.core.away_logo}"
        )

        # 選手カードの生成
        home_cards_html = self.player_formatter.format_player_cards(
            match.facts.home_lineup,
            match.facts.home_formation,
            match.core.home_team,
            match.facts.player_nationalities,
            match.facts.player_numbers,
            match.facts.player_birthdates,
            match.facts.player_photos,
            player_instagram=match.facts.player_instagram,
            player_profiles=match.facts.player_profiles,
        )
        away_cards_html = self.player_formatter.format_player_cards(
            match.facts.away_lineup,
            match.facts.away_formation,
            match.core.away_team,
            match.facts.player_nationalities,
            match.facts.player_numbers,
            match.facts.player_birthdates,
            match.facts.player_photos,
            player_instagram=match.facts.player_instagram,
            player_profiles=match.facts.player_profiles,
        )
        home_bench_html = self.player_formatter.format_player_cards(
            match.facts.home_bench,
            "",
            match.core.home_team,
            match.facts.player_nationalities,
            match.facts.player_numbers,
            match.facts.player_birthdates,
            match.facts.player_photos,
            position_label="SUB",
            player_positions=match.facts.player_positions,
            player_instagram=match.facts.player_instagram,
            player_profiles=match.facts.player_profiles,
            css_class="player-cards-scroll",
        )
        away_bench_html = self.player_formatter.format_player_cards(
            match.facts.away_bench,
            "",
            match.core.away_team,
            match.facts.player_nationalities,
            match.facts.player_numbers,
            match.facts.player_birthdates,
            match.facts.player_photos,
            position_label="SUB",
            player_positions=match.facts.player_positions,
            player_instagram=match.facts.player_instagram,
            player_profiles=match.facts.player_profiles,
            css_class="player-cards-scroll",
        )

        home_injuries = [
            i
            for i in match.facts.injuries_list
            if i.get("team", "") == match.core.home_team
        ]
        away_injuries = [
            i
            for i in match.facts.injuries_list
            if i.get("team", "") == match.core.away_team
        ]
        home_injury_html = self.player_formatter.format_injury_cards(
            home_injuries, match.facts.player_photos, css_class="player-cards-scroll"
        )
        away_injury_html = self.player_formatter.format_injury_cards(
            away_injuries, match.facts.player_photos, css_class="player-cards-scroll"
        )

        # フォーメーションデータ
        home_formation_data = get_formation_layout_data(
            formation=match.facts.home_formation,
            players=match.facts.home_lineup,
            team_name=match.core.home_team,
            team_logo=match.core.home_logo,
            team_color=match.facts.home_team_color,
            is_home=True,
            player_nationalities=match.facts.player_nationalities,
            player_numbers=match.facts.player_numbers,
            player_photos=match.facts.player_photos,
            player_profiles=match.facts.player_profiles,
            player_short_names=short_names_dict,
        )
        away_formation_data = get_formation_layout_data(
            formation=match.facts.away_formation,
            players=match.facts.away_lineup,
            team_name=match.core.away_team,
            team_logo=match.core.away_logo,
            team_color=match.facts.away_team_color,
            is_home=False,
            player_nationalities=match.facts.player_nationalities,
            player_numbers=match.facts.player_numbers,
            player_photos=match.facts.player_photos,
            player_profiles=match.facts.player_profiles,
            player_short_names=short_names_dict,
        )

        formation_html = render_template(
            "partials/formation_section.html",
            home=home_formation_data,
            away=away_formation_data,
        )
        logger.info(
            f"[REPORT] Formation images generated for {match.core.home_team} vs {match.core.away_team}"
        )

        # 同国対決
        same_country_html = ""
        if match.facts.same_country_matchups:
            # 構造化データからマッチアップを構築（LLM出力パースに頼らない）
            matchups = self._build_same_country_matchups(
                matchups_data=match.facts.same_country_matchups,
                llm_text=match.facts.same_country_text,
                home_team=match.core.home_team,
                away_team=match.core.away_team,
                translator=translator,  # 追加
            )
            if matchups:
                team_logos = {
                    match.core.home_team: match.core.home_logo,
                    match.core.away_team: match.core.away_logo,
                }
                same_country_html = self.matchup_formatter.format_matchup_section(
                    matchups=matchups,
                    player_photos=player_photos_extended,
                    team_logos=team_logos,
                    section_title="■ 同国対決",
                )
        elif match.facts.same_country_text:
            # フォールバック: テキストがあるが構造化データがない場合（古いキャッシュ等）
            matchups = parse_matchup_text(match.facts.same_country_text)
            if matchups:
                team_logos = {
                    match.core.home_team: match.core.home_logo,
                    match.core.away_team: match.core.away_logo,
                }
                same_country_html = self.matchup_formatter.format_matchup_section(
                    matchups=matchups,
                    player_photos=player_photos_extended,
                    team_logos=team_logos,
                    section_title="■ 同国対決",
                )
            else:
                same_country_html = (
                    f"<h3>■ 同国対決</h3><p>{match.facts.same_country_text}</p>"
                )

        # ニュース・戦術プレビュー・古巣対決
        news_html = md_lib.markdown(match.preview.news_summary, extensions=["nl2br"])

        # 予測セクション (Issue #199 分割配置)
        win_prediction_html = ""
        scorer_prediction_html = ""
        from src.template_engine import render_template as render_partial

        if match.facts.prediction_percent:
            logger.info(f"Rendering win prediction section for {match.core.id}")
            win_prediction_html = render_partial(
                "partials/win_prediction_section.html",
                prediction_percent=match.facts.prediction_percent,
                home_team=match.core.home_team,
                away_team=match.core.away_team,
                home_logo=match.core.home_logo,
                away_logo=match.core.away_logo,
                home_team_color=match.facts.home_team_color,
                away_team_color=match.facts.away_team_color,
            )

        if match.facts.scorer_odds:
            logger.info(f"Rendering scorer prediction section for {match.core.id}")
            scorer_prediction_html = render_partial(
                "partials/scorer_prediction_section.html",
                scorer_odds=match.facts.scorer_odds,
            )

        tactical_html = self._format_tactical_preview_with_visuals(
            match, md_lib, player_photos_extended, translator
        )

        # 古巣対決（構造化してパース）
        former_club_html = ""
        if match.facts.former_club_trivia:
            entries = parse_former_club_text(
                match.facts.former_club_trivia,
                home_team=match.core.home_team,
                away_team=match.core.away_team,
            )
            if entries:
                team_logos = {
                    match.core.home_team: match.core.home_logo,
                    match.core.away_team: match.core.away_logo,
                }
                former_club_html = self.matchup_formatter.format_former_club_section(
                    entries=entries,
                    player_photos=player_photos_extended,
                    team_logos=team_logos,
                    section_title="■ 古巣対決",
                )
            else:
                # パース失敗時はフォールバックとしてMarkdown変換
                former_club_html = md_lib.markdown(
                    match.facts.former_club_trivia, extensions=["nl2br"]
                )

        # 監督コメント
        home_interview_html = (
            md_lib.markdown(match.preview.home_interview, extensions=["nl2br"])
            if match.preview.home_interview
            else ""
        )
        away_interview_html = (
            md_lib.markdown(match.preview.away_interview, extensions=["nl2br"])
            if match.preview.away_interview
            else ""
        )
        manager_section_html = render_template(
            "partials/manager_section.html",
            home_team_logo=match.core.home_logo,
            home_manager_photo=match.facts.home_manager_photo,
            home_team=match.core.home_team,
            home_manager=match.facts.home_manager,
            home_interview=home_interview_html,
            away_team_logo=match.core.away_logo,
            away_manager_photo=match.facts.away_manager_photo,
            away_team=match.core.away_team,
            away_manager=match.facts.away_manager,
            away_interview=away_interview_html,
        )

        # 移籍情報 (Issue #201: Market closed check)
        if config.ENABLE_TRANSFER_NEWS:
            home_transfer_html = (
                md_lib.markdown(match.preview.home_transfer_news, extensions=["nl2br"])
                if match.preview.home_transfer_news
                else ""
            )
            away_transfer_html = (
                md_lib.markdown(match.preview.away_transfer_news, extensions=["nl2br"])
                if match.preview.away_transfer_news
                else ""
            )
            transfer_section_html = render_template(
                "partials/transfer_section.html",
                home_team_logo=match.core.home_logo,
                home_team=match.core.home_team,
                home_transfer_html=home_transfer_html,
                away_team_logo=match.core.away_logo,
                away_team=match.core.away_team,
                away_transfer_html=away_transfer_html,
            )
        else:
            transfer_section_html = ""

        # YouTube
        match_key = f"{match.core.home_team} vs {match.core.away_team}"

        video_data = youtube_videos.get(match_key, {})
        youtube_html = self.youtube_formatter.format_youtube_section(
            video_data, match_key
        )
        debug_youtube_html = self.youtube_formatter.format_debug_video_section(
            youtube_videos, match_key, match_rank=match.core.rank
        )

        # 順位表 (Issue #192)
        standings_html = ""
        if match.facts.standings_table:
            standings_html = render_template(
                "partials/standings_table.html",
                standings=match.facts.standings_table,
                match=match,
            )

        context = {
            "match": match,
            "match_info_html": self.match_info_formatter.format_match_info_html(match),
            "standings_html": standings_html,
            "home_cards_html": home_cards_html,
            "away_cards_html": away_cards_html,
            "home_bench_html": home_bench_html,
            "away_bench_html": away_bench_html,
            "home_injury_html": home_injury_html,
            "away_injury_html": away_injury_html,
            "formation_html": formation_html,
            "player_profile_modal_html": self._build_player_profile_modal_html(match),
            "has_recent_form": bool(
                match.facts.home_recent_form_details
                or match.facts.away_recent_form_details
            ),
            "same_country_html": same_country_html,
            "news_html": news_html,
            "win_prediction_html": win_prediction_html,
            "scorer_prediction_html": scorer_prediction_html,
            "tactical_html": tactical_html,
            "manager_section_html": manager_section_html,
            "transfer_section_html": transfer_section_html,
            "former_club_html": former_club_html,
            "youtube_html": youtube_html,
            "debug_youtube_html": debug_youtube_html,
        }

        return context, image_paths

    def _format_tactical_preview_with_visuals(
        self, match, md_lib, player_photos: dict = None, translator=None
    ) -> str:
        """戦術プレビュー内の各セクションを個別にビジュアル化して結合"""
        import re

        from src.parsers.tactical_style_parser import parse_tactical_style_text
        from src.utils.name_translator import NameTranslator

        if player_photos is None:
            player_photos = match.facts.player_photos

        if translator is None:
            translator = NameTranslator()

        text = match.preview.tactical_preview
        if not text:
            return ""

        team_logos = {
            match.core.home_team: match.core.home_logo,
            match.core.away_team: match.core.away_logo,
        }

        # セクション見出しで分割
        # 戻り値は [リード文, 見出し1, 内容1, 見出し2, 内容2, ...] の形式
        parts = re.split(r"\n(### .+)", "\n" + text)

        lead_text = parts[0].strip()
        final_html = ""

        if lead_text:
            final_html += md_lib.markdown(lead_text, extensions=["nl2br"])

        # セクションごとに処理
        for i in range(1, len(parts), 2):
            # 見出しから "### " と余分な空白を削除
            title_raw = parts[i].strip()
            title = re.sub(r"^###\s*", "", title_raw)
            content = parts[i + 1].strip() if i + 1 < len(parts) else ""

            if "⚽ キープレイヤー" in title:
                key_players = parse_key_player_text(content)
                if key_players:
                    # 解説文を日本語化
                    player_names = [p.name for p in key_players]
                    for p in key_players:
                        p.description = translator.translate_names_in_html(
                            p.description, player_names
                        )
                        if p.detailed_description:
                            p.detailed_description = translator.translate_names_in_html(
                                p.detailed_description, player_names
                            )

                    final_html += self.matchup_formatter.format_key_player_section(
                        key_players=key_players,
                        player_photos=player_photos,
                        team_logos=team_logos,
                        section_title=title,
                    )
                else:
                    final_html += md_lib.markdown(
                        f"### {title}\n{content}", extensions=["nl2br"]
                    )

            elif "🎯 戦術スタイル" in title:
                tactical_styles = parse_tactical_style_text(
                    content, match.core.home_team, match.core.away_team
                )
                if tactical_styles:
                    final_html += self.matchup_formatter.format_tactical_style_section(
                        tactical_styles=tactical_styles,
                        team_logos=team_logos,
                        section_title=title,
                    )
                else:
                    final_html += md_lib.markdown(
                        f"### {title}\n{content}", extensions=["nl2br"]
                    )

            elif "🔥 キーマッチアップ" in title:
                matchups = parse_matchup_text(content)
                if matchups:
                    # 解説文を日本語化
                    all_p_names = []
                    for m in matchups:
                        all_p_names.extend([p[0] for p in m.players])
                    for m in matchups:
                        m.description = translator.translate_names_in_html(
                            m.description, all_p_names
                        )

                    final_html += self.matchup_formatter.format_matchup_section(
                        matchups=matchups,
                        player_photos=player_photos,
                        team_logos=team_logos,
                        section_title=title,
                    )
                else:
                    final_html += md_lib.markdown(
                        f"### {title}\n{content}", extensions=["nl2br"]
                    )

            else:
                # 未知のセクションはそのままMarkdownとして処理
                final_html += md_lib.markdown(
                    f"### {title}\n{content}", extensions=["nl2br"]
                )

        return final_html

    def _extract_player_names(self, match: MatchAggregate) -> list[str]:
        """
        Extract player names from match data

        Returns:
            List of player names
        """
        names = []

        # スタメン
        if match.facts.home_lineup:
            names.extend(match.facts.home_lineup)
        if match.facts.away_lineup:
            names.extend(match.facts.away_lineup)

        # ベンチ
        if match.facts.home_bench:
            names.extend(match.facts.home_bench)
        if match.facts.away_bench:
            names.extend(match.facts.away_bench)

        # 負傷者
        if match.facts.injuries_list:
            for injury in match.facts.injuries_list:
                if injury.get("player"):
                    names.append(injury["player"])

        # 監督名
        if match.facts.home_manager:
            names.append(match.facts.home_manager)
        if match.facts.away_manager:
            names.append(match.facts.away_manager)

        # 同国対決セクションから抽出
        if match.facts.same_country_text:
            matchups = parse_matchup_text(match.facts.same_country_text)
            for m in matchups:
                names.extend([p[0] for p in m.players])

        # 戦術プレビューのキープレイヤーから抽出
        if match.preview.tactical_preview:
            kp_separator = "### ⚽ キープレイヤー"
            parts = match.preview.tactical_preview.split(kp_separator)
            if len(parts) >= 2:
                kp_content = parts[1]
                next_section_match = re.search(r"\n### ", kp_content)
                if next_section_match:
                    kp_content = kp_content[: next_section_match.start()]

                key_players = parse_key_player_text(kp_content)
                for p in key_players:
                    names.append(p.name)

        # 戦術プレビューのキーマッチアップから抽出
        if match.preview.tactical_preview:
            # キーマッチアップ部分を抽出（_format_tactical_preview_with_visuals と同じロジック）
            separator = "### 🔥 キーマッチアップ"
            parts = match.preview.tactical_preview.split(separator)
            if len(parts) >= 2:
                matchup_text = parts[1]
                next_section_match = re.search(r"\n### ", matchup_text)
                if next_section_match:
                    matchup_text = matchup_text[: next_section_match.start()]

                matchups = parse_matchup_text(matchup_text)
                for m in matchups:
                    names.extend([p[0] for p in m.players])

        # 古巣対決セクションから抽出
        if match.facts.former_club_trivia:
            entries = parse_former_club_text(
                match.facts.former_club_trivia,
                home_team=match.core.home_team,
                away_team=match.core.away_team,
            )
            for e in entries:
                names.append(e.name)

        # 予測セクションの得点者オッズから抽出 (Issue #199)
        if match.facts.scorer_odds:
            for market in match.facts.scorer_odds:
                if "values" in market:
                    for item in market["values"]:
                        if "player" in item:
                            names.append(item["player"])

        return names

    def _build_same_country_matchups(
        self,
        matchups_data: list[dict],
        llm_text: str,
        home_team: str,
        away_team: str,
        translator=None,
    ) -> list:
        """
        構造化データ(same_country_matchups)からPlayerMatchupリストを構築。
        説明文はllm_textから国ごとに抽出する。
        """
        from html import escape

        from src.parsers.matchup_parser import PlayerMatchup
        from src.utils.name_translator import NameTranslator
        from src.utils.nationality_flags import get_flag_emoji

        if translator is None:
            translator = NameTranslator()

        if not matchups_data:
            return []

        # LLMテキストを国ごとのセクションに分割
        sections = {}
        if llm_text:
            # 絵文字や国旗を含むヘッダーパターンで分割
            parts = re.split(
                r"\n?([🇦-🇿🏴\U0001f1e6-\U0001f1ff\U000e0020-\U000e007f]+\s*\*\*?[^*]+\*\*?)\n?",
                "\n" + llm_text,
            )
            for i in range(1, len(parts), 2):
                header = parts[i].strip()
                content = parts[i + 1].strip() if i + 1 < len(parts) else ""
                # 国名だけ抽出（太字や絵文字を除去）してキーにする
                country_key = re.sub(
                    r"[🇦-🇿🏴\U0001f1e6-\U0001f1ff\U000e0020-\U000e007f*]+", "", header
                ).strip()
                if country_key:
                    sections[country_key] = content

        result = []
        for m in matchups_data:
            country = m.get("country", "")
            flag = get_flag_emoji(country)
            header = f"{flag} {country}" if flag else country

            # 選手リスト構築 (最大4名)
            players = []
            home_players = m.get("home_players", [])
            away_players = m.get("away_players", [])

            # バランスよく4名選出（各チーム2名ずつなど）
            # 1. 各チームの先頭1名ずつ
            if home_players:
                players.append((home_players[0], home_team))
            if away_players:
                players.append((away_players[0], away_team))

            # 2. 残り枠を埋める
            remaining_home = home_players[1:]
            remaining_away = away_players[1:]

            while len(players) < 4 and (remaining_home or remaining_away):
                if remaining_home and len(players) < 4:
                    players.append((remaining_home.pop(0), home_team))
                if remaining_away and len(players) < 4:
                    players.append((remaining_away.pop(0), away_team))

            # 説明文を取得
            description = sections.get(country, "")
            if not description:
                # あいまい一致で再試行
                for key, val in sections.items():
                    if country.lower() in key.lower() or key.lower() in country.lower():
                        description = val
                        break

            # 本文内の **Diogo Dalot** (Manchester United) 的な記述を掃除（パルサーと合わせる）
            # ただしここでは構造化データ優先なので、説明文内の残存マッチング情報を消す必要はないかもしれないが、
            # パルサーの _process_section と同様のクリーンアップを行う。
            for p_name in home_players + away_players:
                description = re.sub(
                    rf"\*\*{re.escape(p_name)}\*\*\s*[（\(][^）\)]+[）\)]",
                    "",
                    description,
                )

            # クリーンアップ（接続詞など）
            description = re.sub(
                r"^\s*(?:は[、,]?\s*|と\s*|の\s*|vs\s*[:：]?\s*|,\s*)+", "", description
            )
            # 連続する「と」や「、」を掃除
            description = re.sub(r"\s*[と、,]\s*[と、,]\s*", " ", description)
            description = re.sub(
                r"^\s*(?:の対決[。．,、\s]*|のマッチアップ[。．,、\s]*)",
                "",
                description,
            )
            description = re.sub(r"^[。．.,、\s\(\(（]+", "", description).strip()

            # 説明文中の選手名を日本語化
            all_country_players = home_players + away_players
            description = translator.translate_names_in_html(
                description, all_country_players
            )

            result.append(
                PlayerMatchup(
                    header=escape(header),
                    players=[(escape(p[0]), escape(p[1])) for p in players],
                    description=escape(description.replace("**", "")),
                )
            )

        return result
