"""
チームの選手リストを取得してCSVに出力するスクリプト

Usage:
    python scripts/fetch_squad_list.py --team-id 50

Team IDs:
    Manchester City: 50
    Arsenal: 42
    Liverpool: 40
    Manchester United: 33
    Chelsea: 49
    Tottenham: 47
"""

import argparse
import csv
import logging
import sys
from pathlib import Path

import requests

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://v3.football.api-sports.io"


def get_api_football_key() -> str:
    """設定モジュールから API-Football のキーを取得する。"""
    from config import config

    return config.API_FOOTBALL_KEY


def resolve_output_path(team_id: int, output_override: str | None) -> Path:
    """
    出力先パスをプロジェクトルート基準で解決する。

    相対パス指定でも、呼び出し元の cwd ではなくリポジトリ直下に出力する。
    これにより worktree 間で誤って別ディレクトリへ CSV を生成しにくくする。
    """
    if output_override:
        output_path = Path(output_override)
    else:
        output_path = Path("data") / f"player_{team_id}.csv"

    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    return output_path


def fetch_squad(team_id: int) -> list:
    """
    チームの選手リスト（スカッド）を取得

    Args:
        team_id: API-Football の team ID

    Returns:
        選手リスト [{"id": 123, "name": "Player Name", ...}, ...]
    """
    url = f"{BASE_URL}/players/squads"
    headers = {"x-apisports-key": get_api_football_key()}
    params = {"team": team_id}

    logger.info(f"Fetching squad for team ID: {team_id}")

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    data = response.json()

    if not data.get("response"):
        logger.error(f"No data returned for team ID: {team_id}")
        return []

    team_data = data["response"][0]
    team_name = team_data.get("team", {}).get("name", "Unknown")
    players = team_data.get("players", [])

    logger.info(f"Found {len(players)} players for {team_name}")

    return players


def export_to_csv(players: list, output_path: str, team_name: str = ""):
    """
    選手リストをCSVにエクスポート

    CSV Format:
        player_id,name,position,number,instagram_url,profile_format,profile_detail
    """
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # ヘッダー
        writer.writerow(
            [
                "player_id",
                "name",
                "position",
                "number",
                "instagram_url",
                "profile_format",
                "profile_detail",
            ]
        )

        # 選手データ（ポジション順にソート: GK, DF, MF, FW）
        position_order = {
            "Goalkeeper": 0,
            "Defender": 1,
            "Midfielder": 2,
            "Attacker": 3,
        }
        sorted_players = sorted(
            players,
            key=lambda p: (
                position_order.get(p.get("position", ""), 99),
                p.get("number") or 999,
            ),
        )

        for player in sorted_players:
            player_id = player.get("id", "")
            name = player.get("name", "")
            position = player.get("position", "")
            number = player.get("number", "")
            # instagram_url は手動で埋める（初期値は空）
            instagram_url = ""

            writer.writerow(
                [
                    player_id,
                    name,
                    position,
                    number,
                    instagram_url,
                    "",
                    "",
                ]
            )

    logger.info(f"Exported {len(players)} players to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Fetch squad list from API-Football")
    parser.add_argument(
        "--team-id", type=int, required=True, help="API-Football team ID"
    )
    parser.add_argument("--output", type=str, help="Output CSV path (optional)")
    args = parser.parse_args()

    # デフォルト出力先
    output_path = resolve_output_path(args.team_id, args.output)

    # 出力ディレクトリを作成
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 選手リスト取得
    players = fetch_squad(args.team_id)

    if not players:
        logger.error("No players found. Check the team ID and API key.")
        sys.exit(1)

    # CSV出力
    export_to_csv(players, str(output_path))

    print(f"\n✅ Exported to: {output_path}")
    print("📝 Please manually fill in the 'instagram_url' / 'profile_*' columns")
    print(
        "☁️  After editing, run: "
        "python src/workflows/generate_player_profile/push_csv.py"
    )


if __name__ == "__main__":
    main()
