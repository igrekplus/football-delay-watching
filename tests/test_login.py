"""
ログイン機能のE2Eテスト（Playwright使用）

テストケース:
1. ID/PWログイン正常系
2. ID/PWログイン異常系（間違いエラー表示）
3. Googleログインボタン表示確認
4. ログアウト機能
5. セッション永続化（ページリロード後も維持）
6. レースコンディション対策（ログイン後のリダイレクト確認）

実行方法:
    pip install playwright pytest pytest-playwright
    playwright install chromium
    pytest tests/test_login.py -v

    # ヘッドレスモードを無効にして実行（デバッグ時）
    pytest tests/test_login.py -v --headed

    # 特定のテストのみ実行
    pytest tests/test_login.py::TestLoginPage::test_login_success_stable -v
"""

import pytest
from playwright.sync_api import Page, expect
import os

# テスト対象URL
BASE_URL = os.environ.get("TEST_BASE_URL", "https://football-delay-watching-a8830.web.app")

# テスト用クレデンシャル（環境変数から取得、デフォルト値はダミー）
TEST_EMAIL = os.environ.get("TEST_LOGIN_EMAIL", "sampleexample@gmail.com")
TEST_PASSWORD = os.environ.get("TEST_LOGIN_PASSWORD", "mysample123!?")


@pytest.fixture
def clean_page(page: Page):
    """
    各テスト前にFirebaseセッションをクリアするフィクスチャ
    IndexedDBのfirebaseLocalStorageDbを削除
    """
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    
    # FirebaseのIndexedDBをクリア（セッションリセット）
    page.evaluate("""
        () => {
            return new Promise((resolve) => {
                const deleteRequest = indexedDB.deleteDatabase('firebaseLocalStorageDb');
                deleteRequest.onsuccess = () => resolve('deleted');
                deleteRequest.onerror = () => resolve('error');
                deleteRequest.onblocked = () => resolve('blocked');
            });
        }
    """)
    
    # ページをリロードしてセッションをリセット
    page.reload()
    page.wait_for_load_state("networkidle")
    
    # ログインフォームが表示されるまで待機
    page.wait_for_selector("#login-section", state="visible", timeout=10000)
    
    return page


class TestLoginPage:
    """ログインページのテスト"""

    def test_login_page_elements_visible(self, page: Page):
        """ログインページの要素が表示されていることを確認"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # ページ読み込み待機（Firebaseセッション復元のため）
        page.wait_for_timeout(2000)

        # タイトル確認
        expect(page.locator("h1")).to_contain_text("サッカー観戦ガイド")

        # ログインフォーム要素（ログイン済みの場合はスキップ）
        if page.locator("#login-section").is_visible():
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

    def test_login_success_stable(self, clean_page: Page):
        """
        正しい認証情報でログイン成功し、セッションが安定すること
        - レースコンディション対策: 15秒待機後もレポート一覧が表示されていること
        """
        page = clean_page
        
        # ログイン実行
        page.fill("#email", TEST_EMAIL)
        page.fill("#password", TEST_PASSWORD)
        page.click(".login-btn")

        # ログイン成功を待機（onAuthStateChanged + 許可リストチェック）
        page.wait_for_selector("#content.visible", timeout=15000)

        # レポート一覧が表示されていることを確認
        expect(page.locator("#content")).to_have_class(r".*visible.*")
        expect(page.locator(".report-list h2")).to_contain_text("レポート一覧")

        # ログインフォームが非表示
        expect(page.locator("#login-section")).not_to_be_visible()

        # ユーザー情報が表示
        expect(page.locator("#user-info")).to_be_visible()
        expect(page.locator("#user-email")).to_contain_text(TEST_EMAIL)
        
        # レースコンディション確認: 15秒待機後もログイン状態が維持されること
        page.wait_for_timeout(15000)
        
        # まだレポート一覧が表示されているか確認（ログイン画面に戻っていないか）
        expect(page.locator("#content")).to_have_class(r".*visible.*")
        expect(page.locator("#login-section")).not_to_be_visible()
        
        # JavaScript経由で認証状態を確認
        auth_state = page.evaluate("""
            () => {
                const user = firebase.auth().currentUser;
                return {
                    isLoggedIn: !!user,
                    email: user?.email
                };
            }
        """)
        assert auth_state["isLoggedIn"] is True
        assert auth_state["email"] == TEST_EMAIL

    def test_login_error_with_wrong_password(self, clean_page: Page):
        """間違ったパスワードでエラーメッセージ表示"""
        page = clean_page

        # 間違った認証情報でログイン
        page.fill("#email", "wrong@example.com")
        page.fill("#password", "wrongpassword")
        page.click(".login-btn")

        # エラーメッセージを待機（Firebaseの応答時間を考慮）
        page.wait_for_timeout(5000)

        # エラーメッセージが表示
        error_msg = page.locator("#error-message")
        expect(error_msg).to_be_visible()
        expect(error_msg).to_contain_text("メールアドレスまたはパスワードが間違っています")

        # ログインフォームが引き続き表示
        expect(page.locator("#login-section")).to_be_visible()

    def test_login_error_empty_fields(self, clean_page: Page):
        """空のフィールドでエラーメッセージ表示"""
        page = clean_page

        # 空のままログインボタンをクリック
        page.click(".login-btn")

        # エラーメッセージが表示
        error_msg = page.locator("#error-message")
        expect(error_msg).to_be_visible()
        expect(error_msg).to_contain_text("メールアドレスとパスワードを入力してください")

    def test_logout_functionality(self, clean_page: Page):
        """ログアウト機能の確認"""
        page = clean_page

        # ログイン
        page.fill("#email", TEST_EMAIL)
        page.fill("#password", TEST_PASSWORD)
        page.click(".login-btn")
        page.wait_for_selector("#content.visible", timeout=15000)

        # ログアウト
        page.click(".logout-btn")
        page.wait_for_timeout(3000)

        # ログインフォームに戻る
        expect(page.locator("#login-section")).to_be_visible()
        expect(page.locator("#content")).not_to_have_class(r".*visible.*")

    def test_session_persistence_after_reload(self, page: Page):
        """
        ページリロード後もセッションが維持されること
        - IndexedDBにセッションが保存されていれば自動ログインされる
        """
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        
        # まずログアウト状態にする（必要な場合）
        if page.locator("#user-info").is_visible():
            page.click(".logout-btn")
            page.wait_for_timeout(2000)
        
        # ログイン
        page.fill("#email", TEST_EMAIL)
        page.fill("#password", TEST_PASSWORD)
        page.click(".login-btn")
        page.wait_for_selector("#content.visible", timeout=15000)
        
        # ページをリロード
        page.reload()
        page.wait_for_load_state("networkidle")
        
        # セッション復元を待機
        page.wait_for_timeout(5000)
        
        # 自動的にログイン状態が復元され、レポート一覧が表示されること
        expect(page.locator("#content")).to_have_class(r".*visible.*")
        expect(page.locator("#user-email")).to_contain_text(TEST_EMAIL)


class TestGoogleLogin:
    """Googleログインのテスト（UI要素のみ、実際の認証フローはスキップ）"""

    def test_google_login_button_styling(self, page: Page):
        """Googleログインボタンのスタイル確認"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        
        # ログイン済みの場合はログアウト
        if page.locator("#user-info").is_visible():
            page.click(".logout-btn")
            page.wait_for_timeout(2000)

        google_btn = page.locator(".google-btn")
        expect(google_btn).to_be_visible()

        # SVGアイコン（4色Googleロゴ）が含まれていることを確認
        expect(google_btn.locator("svg")).to_be_visible()

    @pytest.mark.skip(reason="Googleログインはポップアップが必要なため自動テスト困難")
    def test_google_login_popup(self, page: Page):
        """Googleログインポップアップの起動確認"""
        pass


class TestAllowedEmailsList:
    """許可リスト関連のテスト"""

    def test_allowed_emails_json_accessible(self, page: Page):
        """allowed_emails.jsonがアクセス可能であること"""
        response = page.goto(f"{BASE_URL}/allowed_emails.json")
        assert response.status == 200
        
        # JSONとしてパース可能であること
        content = page.content()
        # emails配列が存在することを確認
        assert "emails" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
