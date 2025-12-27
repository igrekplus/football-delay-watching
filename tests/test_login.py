"""
ログイン機能のE2Eテスト（Playwright使用）

テストケース:
1. ID/PWログイン正常系
2. ID/PWログイン異常系（間違いエラー表示）
3. Googleログインボタン表示確認
4. 許可リスト外エラー表示

実行方法:
    pip install playwright pytest pytest-playwright
    playwright install chromium
    pytest tests/test_login.py -v
"""

import pytest
from playwright.sync_api import Page, expect
import os

# テスト対象URL
BASE_URL = os.environ.get("TEST_BASE_URL", "https://football-delay-watching-a8830.web.app")

# テスト用クレデンシャル（環境変数から取得、デフォルト値はダミー）
TEST_EMAIL = os.environ.get("TEST_LOGIN_EMAIL", "sampleexample@gmail.com")
TEST_PASSWORD = os.environ.get("TEST_LOGIN_PASSWORD", "mysample123!?")


class TestLoginPage:
    """ログインページのテスト"""

    def test_login_page_elements_visible(self, page: Page):
        """ログインページの要素が表示されていることを確認"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        # タイトル確認
        expect(page.locator("h1")).to_contain_text("サッカー観戦ガイド")

        # ログインフォーム要素
        expect(page.locator("#email")).to_be_visible()
        expect(page.locator("#password")).to_be_visible()
        expect(page.locator(".login-btn")).to_be_visible()
        expect(page.locator(".login-btn")).to_contain_text("ログイン")

        # Googleログインボタン
        expect(page.locator(".google-btn")).to_be_visible()
        expect(page.locator(".google-btn")).to_contain_text("Googleでログイン")

        # 区切り線
        expect(page.locator(".divider")).to_be_visible()
        expect(page.locator(".divider")).to_contain_text("または")

    def test_login_success_with_valid_credentials(self, page: Page):
        """正しい認証情報でログイン成功"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        # ログイン実行
        page.fill("#email", TEST_EMAIL)
        page.fill("#password", TEST_PASSWORD)
        page.click(".login-btn")

        # ログイン成功を待機
        page.wait_for_timeout(3000)

        # 成功メッセージまたはレポート一覧が表示
        # （onAuthStateChangedの処理時間を考慮）
        page.wait_for_selector("#content.visible", timeout=10000)

        # レポート一覧が表示されていることを確認
        expect(page.locator("#content")).to_have_class(/visible/)
        expect(page.locator(".report-list h2")).to_contain_text("レポート一覧")

        # ログインフォームが非表示
        expect(page.locator("#login-section")).not_to_be_visible()

        # ユーザー情報が表示
        expect(page.locator("#user-info")).to_be_visible()
        expect(page.locator("#user-email")).to_contain_text(TEST_EMAIL)

    def test_login_error_with_wrong_password(self, page: Page):
        """間違ったパスワードでエラーメッセージ表示"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        # 間違った認証情報でログイン
        page.fill("#email", "wrong@example.com")
        page.fill("#password", "wrongpassword")
        page.click(".login-btn")

        # エラーメッセージを待機
        page.wait_for_timeout(3000)

        # エラーメッセージが表示
        error_msg = page.locator("#error-message")
        expect(error_msg).to_be_visible()
        expect(error_msg).to_contain_text("メールアドレスまたはパスワードが間違っています")

        # ログインフォームが引き続き表示
        expect(page.locator("#login-section")).to_be_visible()

    def test_login_error_empty_fields(self, page: Page):
        """空のフィールドでエラーメッセージ表示"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        # 空のままログインボタンをクリック
        page.click(".login-btn")

        # エラーメッセージが表示
        error_msg = page.locator("#error-message")
        expect(error_msg).to_be_visible()
        expect(error_msg).to_contain_text("メールアドレスとパスワードを入力してください")

    def test_logout_functionality(self, page: Page):
        """ログアウト機能の確認"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        # ログイン
        page.fill("#email", TEST_EMAIL)
        page.fill("#password", TEST_PASSWORD)
        page.click(".login-btn")
        page.wait_for_selector("#content.visible", timeout=10000)

        # ログアウト
        page.click(".logout-btn")
        page.wait_for_timeout(2000)

        # ログインフォームに戻る
        expect(page.locator("#login-section")).to_be_visible()
        expect(page.locator("#content")).not_to_have_class(/visible/)


class TestGoogleLogin:
    """Googleログインのテスト（UI要素のみ、実際の認証フローはスキップ）"""

    def test_google_login_button_styling(self, page: Page):
        """Googleログインボタンのスタイル確認"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        google_btn = page.locator(".google-btn")
        expect(google_btn).to_be_visible()

        # SVGアイコンが含まれていることを確認
        expect(google_btn.locator("svg")).to_be_visible()

    @pytest.mark.skip(reason="Googleログインはポップアップが必要なため自動テスト困難")
    def test_google_login_popup(self, page: Page):
        """Googleログインポップアップの起動確認"""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
