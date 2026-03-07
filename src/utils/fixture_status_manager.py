"""
Fixtureステータス管理クライアント

Fixture単位でレポート処理状況を管理するCSVをGCSに保存・読み込みする。
"""

import csv
import io
import logging
from datetime import datetime

from src.utils.datetime_util import DateTimeUtil

logger = logging.getLogger(__name__)


class FixtureStatusManager:
    """GCS上のFixtureステータスCSVを管理"""

    CSV_PATH = "schedule/fixture_status.csv"
    CSV_COLUMNS = [
        "fixture_id",
        "date",
        "kickoff_jst",
        "status",
        "first_attempt_at",
        "last_attempt_at",
        "attempts",
        "error_message",
    ]

    # ステータス定数
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETE = "complete"
    STATUS_FAILED = "failed"
    STATUS_PARTIAL = "partial"  # 一部コンテンツ欠損

    # 最大再試行回数
    MAX_RETRY_ATTEMPTS = 3

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

    def _read_csv(self) -> list[dict[str, str]]:
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

    def _write_csv(self, rows: list[dict[str, str]]) -> bool:
        """リストをCSVとして書き込む"""
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(self.CSV_PATH)

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=self.CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

            blob.upload_from_string(output.getvalue(), content_type="text/csv")
            logger.info(f"CSV updated: {self.CSV_PATH}")
            return True
        except Exception as e:
            logger.error(f"Failed to write CSV to GCS: {e}")
            return False

    def get_status(self, fixture_id: str) -> str | None:
        """指定fixtureIdのステータスを取得"""
        rows = self._read_csv()
        for row in rows:
            if row.get("fixture_id") == str(fixture_id):
                return row.get("status")
        return None

    def is_processable(self, fixture_id: str) -> bool:
        """処理対象かどうか判定（未処理 or 失敗で再試行可能）

        詳細なログを出力して判定理由を明確化
        """
        rows = self._read_csv()

        for row in rows:
            if row.get("fixture_id") == str(fixture_id):
                status = row.get("status")
                attempts = int(row.get("attempts", "0"))
                last_attempt = row.get("last_attempt_at", "不明")

                # 完了済みはスキップ
                if status == self.STATUS_COMPLETE:
                    logger.debug(
                        f"[FixtureStatus {fixture_id}] スキップ: 処理完了済み (last_attempt: {last_attempt})"
                    )
                    return False

                # 部分完了は再処理対象（次回実行時に再取得を試みる）
                if status == self.STATUS_PARTIAL:
                    logger.info(
                        f"[FixtureStatus {fixture_id}] 再処理対象: 部分完了 (一部コンテンツ欠損, last_attempt: {last_attempt})"
                    )
                    return True

                # 失敗で再試行上限に達している場合はスキップ
                if status == self.STATUS_FAILED and attempts >= self.MAX_RETRY_ATTEMPTS:
                    logger.warning(
                        f"[FixtureStatus {fixture_id}] スキップ: 再試行上限到達 ({attempts}/{self.MAX_RETRY_ATTEMPTS})"
                    )
                    return False

                # それ以外（pending, processing, failed with attempts < max）は処理可能
                logger.debug(
                    f"[FixtureStatus {fixture_id}] 処理可能: status={status}, attempts={attempts}/{self.MAX_RETRY_ATTEMPTS}"
                )
                return True

        # レコードが存在しない = 未処理 = 処理可能
        logger.debug(
            f"[FixtureStatus {fixture_id}] 処理可能: 初回処理（GCSレコードなし）"
        )
        return True

    def mark_processing(self, fixture_id: str, kickoff_utc: datetime) -> bool:
        """処理開始をマーク"""
        kickoff_jst = DateTimeUtil.to_jst(kickoff_utc)
        date_str = kickoff_jst.strftime("%Y-%m-%d")
        kickoff_str = kickoff_jst.isoformat()

        return self._update_status(
            fixture_id=str(fixture_id),
            date=date_str,
            kickoff_jst=kickoff_str,
            status=self.STATUS_PROCESSING,
            increment_attempts=False,
        )

    def mark_complete(self, fixture_id: str) -> bool:
        """処理完了をマーク"""
        return self._update_status(
            fixture_id=str(fixture_id),
            status=self.STATUS_COMPLETE,
            increment_attempts=False,
        )

    def mark_failed(self, fixture_id: str, error: str) -> bool:
        """処理失敗をマーク（再試行カウント増加）"""
        return self._update_status(
            fixture_id=str(fixture_id),
            status=self.STATUS_FAILED,
            error_message=error,
            increment_attempts=True,
        )

    def mark_partial(self, fixture_id: str, missing_content: str) -> bool:
        """部分完了をマーク（一部コンテンツ欠損、次回再処理対象）"""
        return self._update_status(
            fixture_id=str(fixture_id),
            status=self.STATUS_PARTIAL,
            error_message=f"Missing: {missing_content}",
            increment_attempts=False,  # 部分完了はリトライカウントを増やさない
        )

    def _update_status(
        self,
        fixture_id: str,
        status: str,
        date: str = None,
        kickoff_jst: str = None,
        error_message: str = None,
        increment_attempts: bool = False,
    ) -> bool:
        """ステータスを更新または追加"""
        rows = self._read_csv()
        now_str = DateTimeUtil.now_jst().isoformat()

        # 既存の行を更新
        found = False
        for row in rows:
            if row.get("fixture_id") == fixture_id:
                row["status"] = status
                row["last_attempt_at"] = now_str

                if date:
                    row["date"] = date
                if kickoff_jst:
                    row["kickoff_jst"] = kickoff_jst
                if error_message:
                    row["error_message"] = error_message

                if increment_attempts:
                    current_attempts = int(row.get("attempts", "0"))
                    row["attempts"] = str(current_attempts + 1)

                found = True
                break

        # 新規追加
        if not found:
            rows.append(
                {
                    "fixture_id": fixture_id,
                    "date": date or "",
                    "kickoff_jst": kickoff_jst or "",
                    "status": status,
                    "first_attempt_at": now_str,
                    "last_attempt_at": now_str,
                    "attempts": "1" if increment_attempts else "0",
                    "error_message": error_message or "",
                }
            )

        # キックオフ時刻でソート（降順: 新しい試合が先頭）
        rows.sort(key=lambda x: x.get("kickoff_jst", ""), reverse=True)

        # 直近30日分のみ保持（古いデータを削除）
        # kickoff_jstが空の行は保持
        from datetime import timedelta

        cutoff_date = (DateTimeUtil.now_jst() - timedelta(days=30)).strftime("%Y-%m-%d")
        rows = [r for r in rows if not r.get("date") or r.get("date") >= cutoff_date]

        return self._write_csv(rows)

    def get_all_statuses(self) -> list[dict[str, str]]:
        """全ステータスを取得（デバッグ用）"""
        return self._read_csv()

    def cleanup_old_records(self, days: int = 30) -> int:
        """指定日数より古いレコードを削除

        Args:
            days: 保持する日数

        Returns:
            削除したレコード数
        """
        rows = self._read_csv()
        initial_count = len(rows)

        from datetime import timedelta

        cutoff_date = (DateTimeUtil.now_jst() - timedelta(days=days)).strftime(
            "%Y-%m-%d"
        )
        rows = [r for r in rows if not r.get("date") or r.get("date") >= cutoff_date]

        deleted_count = initial_count - len(rows)

        if deleted_count > 0:
            self._write_csv(rows)
            logger.info(
                f"Cleaned up {deleted_count} old fixture records (older than {days} days)"
            )

        return deleted_count
