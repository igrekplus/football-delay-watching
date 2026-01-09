import logging
import os
from config import config
from src.match_processor import MatchProcessor
from src.facts_service import FactsService
from src.news_service import NewsService
from src.report_generator import ReportGenerator
from src.cache_warmer import run_cache_warming
from src.utils.datetime_util import DateTimeUtil
from src.utils.match_scheduler import MatchScheduler
from src.domain.match_selector import MatchSelector

logger = logging.getLogger(__name__)

# Firebase Hosting URL
FIREBASE_BASE_URL = "https://football-delay-watching-a8830.web.app"

class GenerateGuideWorkflow:
    """
    Workflow for generating the Football Delay Watching Guide.
    Orchestrates data fetching, content generation, and delivery.
    """

    def run(self, dry_run: bool = False):
        """メインエントリポイント（オーケストレーション）"""
        self._log_execution_info(dry_run)
        
        # Step 1: 試合選定
        matches, status_manager = self._step_select_matches()
        if not matches:
            self._log_skip_summary()
            return
        
        try:
            # Step 2: データエンリッチメント
            youtube_videos, youtube_stats = self._step_enrich_data(matches)
            
            # Step 3: レポート生成・配信
            report_list = self._step_generate_reports(matches, youtube_videos, youtube_stats)
            
            # Step 4: 完了処理
            self._step_finalize(matches, status_manager, youtube_videos)
            
        except Exception as e:
            self._handle_error(e, matches, status_manager)
            raise
        
        logger.info("Workflow completed.")

    def _log_execution_info(self, dry_run: bool):
        """実行情報のログ出力"""
        from src.utils.datetime_util import DateTimeUtil
        now_jst = DateTimeUtil.now_jst()
        logger.info("=" * 70)
        logger.info("GitHub Actions / ワークフロー実行開始")
        logger.info(f"実行時刻 (JST): {now_jst.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"TARGET_DATE: {config.TARGET_DATE.strftime('%Y-%m-%d %H:%M JST')}")
        logger.info(f"モード: {'モック' if config.USE_MOCK_DATA else 'デバッグ' if config.DEBUG_MODE else '本番'}")
        logger.info(f"Dry Run: {dry_run}")
        logger.info("=" * 70)
        logger.info(f"Starting workflow... (Dry Run: {dry_run}, Mock: {config.USE_MOCK_DATA})")

    def _step_select_matches(self):
        """
        ステップ1: 試合選定
        
        Returns:
            (matches, status_manager): 選定された試合リストとステータスマネージャー
        """
        processor = MatchProcessor()
        all_matches = processor.run()
        
        if not all_matches:
            return [], None
        
        # 2. 時間ベースフィルタリング + ステータス管理（本番モードのみ）
        status_manager = None
        if not config.USE_MOCK_DATA and not config.DEBUG_MODE:
            from src.utils.fixture_status_manager import FixtureStatusManager
            status_manager = FixtureStatusManager()
            scheduler = MatchScheduler()
            selector = MatchSelector()
            
            # 時間窓 + ステータス管理による二段階フィルタ
            processable_matches = scheduler.filter_processable_matches(all_matches, status_manager)
            
            if not processable_matches:
                logger.info("現在処理対象の試合なし（時間外 or 処理済み）。次回実行まで待機。")
                return [], None
            
            # 3. 最終選定（ランク順ソート + MATCH_LIMIT適用）
            matches = selector.select(processable_matches)
            logger.info(f"最終選定: {len([m for m in matches if m.is_target])} 試合（処理可能: {len(processable_matches)} 試合から）")
            
            # 処理開始マーク（is_target=Trueの試合のみ）
            for match in matches:
                if match.is_target:
                    status_manager.mark_processing(match.id, match.core.kickoff_at_utc)
                    logger.info(f"試合 {match.id} ({match.home_team} vs {match.away_team}) を処理開始としてマーク")
            
            return matches, status_manager
        else:
            # モック・デバッグモードでも選定ロジックを適用
            selector = MatchSelector()
            return selector.select(all_matches), None

    def _step_enrich_data(self, matches):
        """
        ステップ2: データエンリッチメント
        
        Returns:
            (youtube_videos, youtube_stats)
        """
        # 3. Facts Acquisition
        facts_service = FactsService()
        facts_service.enrich_matches(matches)
        
        # 4. News Collection & Summarization
        news_service = NewsService()
        news_service.process_news(matches)
        
        # 5. YouTube Videos
        youtube_videos = {}
        youtube_stats = {"api_calls": 0, "cache_hits": 0}
        try:
            from src.youtube_service import YouTubeService
            youtube_service = YouTubeService()
            youtube_videos = youtube_service.process_matches(matches)
            youtube_stats = {
                "api_calls": youtube_service.api_call_count,
                "cache_hits": youtube_service.cache_hit_count,
            }
            logger.info(f"YouTube videos fetched for {len(youtube_videos)} matches")
        except Exception as e:
            logger.warning(f"YouTube video fetch failed (continuing without videos): {e}")
        
        return youtube_videos, youtube_stats

    def _step_generate_reports(self, matches, youtube_videos, youtube_stats):
        """
        ステップ3: レポート生成・配信
        
        Returns:
            report_list: 生成されたレポートのリスト
        """
        # 6. Report Generation
        generator = ReportGenerator()
        logger.info("Generating per-match reports")
        report_list = generator.generate_all(matches, youtube_videos=youtube_videos, youtube_stats=youtube_stats)
        logger.info(f"Generated {len(report_list)} individual match reports")
        
        # 7. HTML Generation
        self._generate_html(report_list)
        
        # 8. Email Notification (シンプルなデバッグサマリ)
        self._send_debug_email(matches, report_list, youtube_stats)
        
        return report_list

    def _step_finalize(self, matches, status_manager, youtube_videos):
        """
        ステップ4: 完了処理
        """
        # 9. 品質チェックに基づくGCSステータス更新
        if status_manager:
            for match in matches:
                if match.is_target:
                    is_complete, missing = self._check_report_quality(match, youtube_videos)
                    if is_complete:
                        status_manager.mark_complete(match.id)
                        logger.info(f"試合 {match.id} ({match.home_team} vs {match.away_team}) を処理完了としてマーク")
                    else:
                        status_manager.mark_partial(match.id, ", ".join(missing))
                        logger.warning(f"試合 {match.id} ({match.home_team} vs {match.away_team}) を部分完了としてマーク (欠損: {missing})")
                else:
                    logger.info(f"試合 {match.id} ({match.home_team} vs {match.away_team}) はis_target=Falseのためスキップ（GCS更新なし）")

        # 11. Write Quota Info
        self._write_quota_info()
        
        # 12. Cache Warming
        self._run_cache_warming()
        
        # 13. 処理完了ログ
        match_count = len([m for m in matches if m.is_target])
        logger.info(f"処理完了: {match_count}試合のレポートを生成")

    def _handle_error(self, e, matches, status_manager):
        """エラーハンドリング（ステータス更新含む）"""
        logger.error(f"レポート生成に失敗: {e}", exc_info=True)
        
        # 10. 失敗時: GCSステータス更新
        if status_manager:
            for match in matches:
                if match.is_target:
                    status_manager.mark_failed(match.id, str(e))
                    logger.warning(f"試合 {match.id} を失敗としてマーク（再試行可能）")
        
        # 11. Write Quota Info
        self._write_quota_info()
        
        # 12. Cache Warming
        self._run_cache_warming()
        
        # 13. 処理完了ログ
        match_count = len([m for m in matches if m.is_target])
        logger.info(f"処理完了: {match_count}試合のレポートを生成")
        
        logger.info("Workflow completed.")

    def _check_report_quality(self, match, youtube_videos: dict) -> tuple:
        """
        レポートの品質をチェック
        
        Returns:
            (is_complete, missing_items): 完全か否かと、欠損コンテンツのリスト
        """
        missing = []
        
        # 必須: スタメン（ホーム・アウェイ両方）
        if not match.home_lineup or len(match.home_lineup) == 0:
            missing.append("home_lineup")
        if not match.away_lineup or len(match.away_lineup) == 0:
            missing.append("away_lineup")
        
        # 必須: ニュースサマリー または 戦術プレビュー
        if not match.news_summary and not match.tactical_preview:
            missing.append("news_summary/tactical_preview")
        
        # YouTube動画は品質判定から除外（クォータ切れ時に再処理ループを防ぐため）
        # 動画がなくても complete として扱う
        
        is_complete = len(missing) == 0
        return is_complete, missing

    def _generate_html(self, report_list):
        html_paths = []
        try:
            from src.html_generator import generate_html_reports, sync_from_firebase
            
            if not config.USE_MOCK_DATA:
                sync_from_firebase()
            else:
                logger.info("Mock mode: Skipping Firebase sync")
            
            html_paths = generate_html_reports(report_list)
            logger.info(f"Generated {len(html_paths)} HTML files")
        except Exception as e:
            logger.warning(f"HTML generation failed (continuing): {e}")
        return html_paths

    def _send_debug_email(self, matches, report_list, youtube_stats):
        """シンプルなデバッグサマリをメール送信"""
        if config.GMAIL_ENABLED and config.NOTIFY_EMAIL:
            try:
                from src.email_service import send_debug_summary
                
                # レポートURLを構築
                report_urls = []
                for r in report_list:
                    filename = r.get("filename", "")
                    if filename:
                        url = f"{FIREBASE_BASE_URL}/reports/{filename}.html"
                        report_urls.append(url)
                
                # 試合サマリを構築
                matches_summary = []
                target_matches = [m for m in matches if m.is_target]
                for match in target_matches:
                    matches_summary.append({
                        "home": match.home_team,
                        "away": match.away_team,
                        "competition": match.competition,
                        "kickoff": match.kickoff_jst,
                        "rank": match.rank
                    })
                
                # モード判定
                is_mock = config.USE_MOCK_DATA
                is_debug = config.DEBUG_MODE
                
                logger.info(f"Sending debug summary email to {config.NOTIFY_EMAIL}...")
                if send_debug_summary(
                    report_urls=report_urls,
                    matches_summary=matches_summary,
                    quota_info=config.QUOTA_INFO or {},
                    youtube_stats=youtube_stats,
                    is_mock=is_mock,
                    is_debug=is_debug
                ):
                    logger.info("Email sent successfully!")
                else:
                    logger.warning("Failed to send email notification.")
            except ImportError:
                logger.warning("Email service not available.")

    def _write_quota_info(self):
        if config.QUOTA_INFO:
            quota_file = "/tmp/quota.txt"
            try:
                with open(quota_file, "w", encoding="utf-8") as f:
                    for key, info in config.QUOTA_INFO.items():
                        f.write(f"{key}: {info}\n")
                logger.info(f"Quota info written to {quota_file}")
            except Exception as e:
                logger.warning(f"Failed to write quota info: {e}")

    def _run_cache_warming(self):
        # 7. Cache Warming (if quota available and GCS enabled)
        remaining_quota = 0
        
        # Get remaining quota from QUOTA_INFO or by checking API
        if "API-Football" in config.QUOTA_INFO:
            quota_str = config.QUOTA_INFO.get("API-Football", "")
            if "Remaining:" in quota_str:
                try:
                    remaining_quota = int(quota_str.split("Remaining:")[1].split("/")[0].strip())
                except (ValueError, IndexError):
                    pass
        
        # If no quota info (e.g. all cache hits in workflow), check directly via API if not mock
        if remaining_quota == 0 and not config.USE_MOCK_DATA:
            import requests # Or use ApiFootballClient?
            # To avoid cyclic dependency or overcomplication, reuse simple request or use client.
            # Ideally use ApiFootballClient but we need to instantiate it or pass it.
            # MatchProcessor has one.
            # Let's try to check simply.
            try:
                # Basic check
                url = "https://v3.football.api-sports.io/status"
                headers = {"x-apisports-key": config.API_FOOTBALL_KEY}
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    requests_info = data.get("response", {}).get("requests", {})
                    limit = requests_info.get("limit_day", 100)
                    current = requests_info.get("current", 0)
                    remaining_quota = limit - current
                    logger.info(f"API-Football quota check: {remaining_quota}/{limit} remaining")
            except Exception as e:
                logger.warning(f"Failed to check API quota: {e}")
        
        if remaining_quota > 0:
            logger.info(f"Starting cache warming with {remaining_quota} remaining quota...")
            result = run_cache_warming(remaining_quota)
            logger.info(f"Cache warming result: {result}")
        else:
            logger.info("Skipping cache warming: no quota info available or quota exhausted")

    def _log_skip_summary(self):
        """試合スキップ時のサマリログを出力"""
        from src.utils.datetime_util import DateTimeUtil
        
        target_date = config.TARGET_DATE
        date_str = DateTimeUtil.format_date_str(target_date)
        
        logger.info("=" * 50)
        logger.info("スキップサマリ")
        logger.info(f"  対象日: {date_str}")
        logger.info(f"  モード: {'モック' if config.USE_MOCK_DATA else 'デバッグ' if config.DEBUG_MODE else '本番'}")
        logger.info(f"  結果: 対象試合なし")
        logger.info("=" * 50)
