import logging
import os
from config import config
from src.match_processor import MatchProcessor
from src.facts_service import FactsService
from src.news_service import NewsService
from src.report_generator import ReportGenerator
from src.cache_warmer import run_cache_warming

logger = logging.getLogger(__name__)

# Firebase Hosting URL
FIREBASE_BASE_URL = "https://football-delay-watching-a8830.web.app"

class GenerateGuideWorkflow:
    """
    Workflow for generating the Football Delay Watching Guide.
    Orchestrates data fetching, content generation, and delivery.
    """

    def run(self, dry_run: bool = False):
        logger.info(f"Starting workflow... (Dry Run: {dry_run}, Mock: {config.USE_MOCK_DATA})")

        # 1. Match Extraction & Selection
        processor = MatchProcessor()
        matches = processor.run()
        
        if not matches:
            logger.info("No target matches found for today.")
            # Even if no matches, we might want to check cache warming? Use original logic flow.
            # Original flow: continues safely as facts_service etc handle empty lists usually?
            # Original code:
            # if not matches: logger.info...
            # then it proceeds to facts_service.enrich_matches(matches) which does nothing if empty.
        
        # 2. Facts Acquisition
        facts_service = FactsService()
        facts_service.enrich_matches(matches)
        
        # 3. News Collection & Summarization
        news_service = NewsService()
        news_service.process_news(matches)
        
        # 3.5 YouTube Videos
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
        
        # 4. Report Generation
        generator = ReportGenerator()
        logger.info("Generating per-match reports")
        report_list = generator.generate_all(matches, youtube_videos=youtube_videos, youtube_stats=youtube_stats)
        logger.info(f"Generated {len(report_list)} individual match reports")
        
        # 4.5 HTML Generation
        html_paths = self._generate_html(report_list)
        
        # 5. Email Notification (シンプルなデバッグサマリ)
        self._send_debug_email(matches, report_list, youtube_stats)
        
        # 6. Write Quota Info
        self._write_quota_info()
        
        # 7. Cache Warming
        self._run_cache_warming()
        
        logger.info("Workflow completed.")

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
