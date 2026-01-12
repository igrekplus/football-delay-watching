import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.formatters.player_formatter import PlayerFormatter
from src.formatters.matchup_formatter import MatchupFormatter
from src.parsers.matchup_parser import PlayerMatchup

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

def test_matchup_placeholders():
    formatter = MatchupFormatter()
    matchup = PlayerMatchup(
        player1_name="Player A",
        player1_team="Team A",
        player2_name="Player B",
        player2_team="Team B",
        description="Matchup description",
        header="Matchup Header"
    )
    
    # 写真がない場合
    player_photos = {}
    team_logos = {"Team A": "logoA.png", "Team B": "logoB.png"}
    
    html = formatter.format_single_matchup(matchup, player_photos, team_logos)
    
    # プレースホルダーが含まれていること (2人分)
    assert html.count('class="matchup-photo-placeholder"') == 2
    # imgタグが出力されていないこと（onerror処理を含むimgタグがないこと）
    assert 'class="matchup-photo"' not in html
    
    # 注目選手（Key Player）のプレースホルダーも確認
    class MockPlayer:
        def __init__(self, name, team, description, detailed_description=""):
            self.name = name
            self.team = team
            self.description = description
            self.detailed_description = detailed_description

    kp = MockPlayer("Key Player", "Team A", "KP description")
    kp_html = formatter.format_single_key_player(kp, player_photos, team_logos)
    assert 'class="matchup-photo-placeholder"' in kp_html
    
    print("✅ Matchup and Key Player placeholders passed")

if __name__ == "__main__":
    try:
        test_sanitize_photo_url()
        test_format_player_cards()
        test_format_injury_cards()
        test_matchup_placeholders()
        print("\n✨ All tests passed for Issue #168!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        traceback_str = ""
        import traceback
        traceback.print_exc()
        sys.exit(1)
