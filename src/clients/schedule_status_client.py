"""
スケジュールステータス管理クライアント

日付単位でレポート作成状況を管理するCSVをGCSに保存・読み込みする。
"""

import csv
import io
import logging
from typing import Optional, List, Dict
from datetime import datetime

from src.utils.datetime_util import DateTimeUtil

logger = logging.getLogger(__name__)


class ScheduleStatusClient:
    """GCS上のスケジュールステータスCSVを管理"""
    
    CSV_PATH = "schedule/report_status.csv"
    CSV_COLUMNS = ["date", "status", "processed_at", "match_count"]
    
    # ステータス定数
    STATUS_PENDING = "pending"
    STATUS_COMPLETE = "complete"
    STATUS_SKIPPED = "skipped"
    
    def __init__(self, bucket_name: str = None):
        from settings.cache_config import GCS_BUCKET_NAME
        self.bucket_name = bucket_name or GCS_BUCKET_NAME
        self._bucket = None
        self._client = None
    
    def _get_bucket(self):
        """GCSバケットを遅延初期化"""
        if self._bucket is None:
            try:
                from google.cloud import storage
                self._client = storage.Client()
                self._bucket = self._client.bucket(self.bucket_name)
                logger.debug(f"GCS client initialized for bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {e}")
                raise
        return self._bucket
    
    def _read_csv(self) -> List[Dict[str, str]]:
        """CSVを読み込んでリストとして返す"""
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(self.CSV_PATH)
            
            if not blob.exists():
                logger.info(f"CSV not found, will create: {self.CSV_PATH}")
                return []
            
            content = blob.download_as_text()
            reader = csv.DictReader(io.StringIO(content))
            return list(reader)
        except Exception as e:
            logger.warning(f"Failed to read CSV from GCS: {e}")
            return []
    
    def _write_csv(self, rows: List[Dict[str, str]]) -> bool:
        """リストをCSVとして書き込む"""
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(self.CSV_PATH)
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=self.CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
            
            blob.upload_from_string(
                output.getvalue(),
                content_type='text/csv'
            )
            logger.info(f"CSV updated: {self.CSV_PATH}")
            return True
        except Exception as e:
            logger.error(f"Failed to write CSV to GCS: {e}")
            return False
    
    def get_status(self, date_str: str) -> Optional[str]:
        """指定日付のステータスを取得"""
        rows = self._read_csv()
        for row in rows:
            if row.get("date") == date_str:
                return row.get("status")
        return None
    
    def is_processed(self, date_str: str) -> bool:
        """指定日付が処理済みかどうか"""
        status = self.get_status(date_str)
        return status in [self.STATUS_COMPLETE, self.STATUS_SKIPPED]
    
    def mark_complete(self, date_str: str, match_count: int) -> bool:
        """処理完了をマーク"""
        return self._update_status(date_str, self.STATUS_COMPLETE, match_count)
    
    def mark_skipped(self, date_str: str) -> bool:
        """スキップをマーク"""
        return self._update_status(date_str, self.STATUS_SKIPPED, 0)
    
    def _update_status(self, date_str: str, status: str, match_count: int) -> bool:
        """ステータスを更新または追加"""
        rows = self._read_csv()
        processed_at = DateTimeUtil.now_jst().isoformat()
        
        # 既存の行を更新
        found = False
        for row in rows:
            if row.get("date") == date_str:
                row["status"] = status
                row["processed_at"] = processed_at
                row["match_count"] = str(match_count)
                found = True
                break
        
        # 新規追加
        if not found:
            rows.append({
                "date": date_str,
                "status": status,
                "processed_at": processed_at,
                "match_count": str(match_count)
            })
        
        # 日付でソート（降順: 新しい日付が先頭）
        rows.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        # 直近30日分のみ保持（古いデータを削除）
        rows = rows[:30]
        
        return self._write_csv(rows)
    
    def get_all_statuses(self) -> List[Dict[str, str]]:
        """全ステータスを取得（デバッグ用）"""
        return self._read_csv()
