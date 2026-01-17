#!/usr/bin/env python3
"""
GCSキャッシュ状況確認ツール

使い方:
    python3 healthcheck/check_gcs_cache.py
"""

import subprocess
from datetime import datetime

# GCS Bucket
BUCKET = "gs://football-delay-watching-cache"

# Target teams from config
EPL_TEAMS = [
    "Liverpool",
    "Chelsea",
    "Arsenal",
    "Nottingham_Forest",
    "Brighton",
    "Manchester_City",
    "Bournemouth",
    "Newcastle",
    "Aston_Villa",
    "Fulham",
]

CL_TEAMS = [
    "Liverpool",
    "Barcelona",
    "Arsenal",
    "Inter",
    "Bayer_Leverkusen",
    "Atletico_Madrid",
    "AC_Milan",
    "Atalanta",
    "Monaco",
    "Sporting_CP",
    "Bayern_Munich",
    "Borussia_Dortmund",
    "Real_Madrid",
]


def run_gsutil(args):
    """gsutilコマンドを実行"""
    try:
        result = subprocess.run(
            ["gsutil"] + args, capture_output=True, text=True, timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1


def count_files(path):
    """GCSパス内のファイル数をカウント"""
    stdout, stderr, code = run_gsutil(["ls", "-r", path])
    if code != 0:
        return 0
    return len([line for line in stdout.strip().split("\n") if line.endswith(".json")])


def main():
    print("=" * 60)
    print("📦 GCSキャッシュ状況確認")
    print("=" * 60)
    print(f"🕐 確認日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 バケット: {BUCKET}")
    print()

    # 全体の統計
    print("### 全体統計")
    for folder in [
        "fixtures",
        "lineups",
        "players",
        "injuries",
        "statistics",
        "headtohead",
    ]:
        count = count_files(f"{BUCKET}/{folder}/")
        print(f"  {folder}: {count} files")
    print()

    # EPLチーム別の選手キャッシュ
    print("### EPL対象チーム (選手キャッシュ)")
    all_teams = set(EPL_TEAMS + CL_TEAMS)
    cached_teams = []
    uncached_teams = []

    for team in sorted(all_teams):
        # チーム名のスペースをアンダースコアに変換
        team_path = team.replace(" ", "_")
        count = count_files(f"{BUCKET}/players/{team_path}/")
        if count > 0:
            cached_teams.append((team, count))
            print(f"  ✅ {team}: {count} players")
        else:
            uncached_teams.append(team)

    print()
    print("### 未キャッシュチーム")
    for team in uncached_teams:
        print(f"  ❌ {team}")

    print()
    print("=" * 60)
    print(f"📊 サマリー: {len(cached_teams)} cached / {len(uncached_teams)} uncached")
    print("=" * 60)


if __name__ == "__main__":
    main()
