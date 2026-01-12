import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.formatters.player_formatter import PlayerFormatter

def test_sanitize_photo_url():
    formatter = PlayerFormatter()
    
    assert formatter._sanitize_photo_url("https://example.com/photo.jpg") == "https://example.com/photo.jpg"
    assert formatter._sanitize_photo_url("NO PHOTO YET") == ""
    assert formatter._sanitize_photo_url("no photo yet") == ""
    assert formatter._sanitize_photo_url("null") == ""
    assert formatter._sanitize_photo_url("None") == ""
    assert formatter._sanitize_photo_url("") == ""
    assert formatter._sanitize_photo_url(None) == ""
    
    print("✅ _sanitize_photo_url passed")

def test_format_player_cards():
    formatter = PlayerFormatter()
    lineup = ["John Doe"]
    player_photos = {"John Doe": "NO PHOTO YET"}
    
    html = formatter.format_player_cards(
        lineup=lineup,
        formation="4-4-2",
        team_name="Test Team",
        player_photos=player_photos
    )
    
    # "NO PHOTO YET" が含まれていないこと
    assert "NO PHOTO YET" not in html
    # プレースホルダーが含まれていること
    assert 'class="player-card-photo player-card-photo-placeholder"' in html
    
    print("✅ format_player_cards passed")

def test_format_injury_cards():
    formatter = PlayerFormatter()
    injuries = [{"name": "Jane Smith", "team": "Test Team", "reason": "Injury", "photo": "null"}]
    
    html = formatter.format_injury_cards(injuries)
    
    # "null" が含まれていないこと
    assert 'src="null"' not in html
    # プレースホルダーが含まれていること
    assert 'class="player-card-photo player-card-photo-placeholder"' in html
    
    print("✅ format_injury_cards passed")

if __name__ == "__main__":
    try:
        test_sanitize_photo_url()
        test_format_player_cards()
        test_format_injury_cards()
        print("\n✨ All tests passed for Issue #168!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        sys.exit(1)
