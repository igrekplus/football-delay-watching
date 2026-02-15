#!/bin/bash

# scripts/safe_deploy.sh
# Firebase Hostingへのデプロイ前に同期を強制するスクリプト

set -e

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Safe Deploy Process Starting ===${NC}"

# 1. venv の確認
if [ ! -d ".venv" ]; then
    echo -e "${RED}Error: .venv directory not found.${NC}"
    echo "Please run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 2. 同期処理の実行
echo -e "${GREEN}Step 1: Syncing reports from Firebase to local...${NC}"
source .venv/bin/activate
python scripts/sync_firebase_reports.py

# 2.5. カレンダーHTMLの再生成（CSVのレポートリンクを反映）
echo -e "${GREEN}Step 1.5: Regenerating calendar.html from CSV data...${NC}"
python -m src.calendar_generator
echo -e "${GREEN}Calendar HTML updated.${NC}"

# 3. ユーザー確認 (CI環境以外の場合)
if [ -t 0 ]; then
    echo -e "${GREEN}Sync complete.${NC}"
    read -p "Do you want to proceed with firebase deploy? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Deploy cancelled by user.${NC}"
        exit 1
    fi
fi

# 4. デプロイ実行
echo -e "${GREEN}Step 2: Deploying to Firebase Hosting...${NC}"
firebase deploy --only hosting

echo -e "${GREEN}=== Safe Deploy Complete ===${NC}"
