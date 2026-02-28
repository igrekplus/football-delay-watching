#!/bin/bash

# scripts/safe_deploy.sh
# Firebase Hostingへのデプロイ前に同期を強制するスクリプト

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

GIT_COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null || true)"
SHARED_REPO_ROOT=""
if [ -n "${GIT_COMMON_DIR}" ]; then
    SHARED_REPO_ROOT="$(cd "${GIT_COMMON_DIR}/.." && pwd)"
fi

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Safe Deploy Process Starting ===${NC}"

# 1. venv の確認
VENV_DIR="${REPO_ROOT}/.venv"
if [ ! -d "${VENV_DIR}" ] && [ -n "${SHARED_REPO_ROOT}" ] && [ -d "${SHARED_REPO_ROOT}/.venv" ]; then
    VENV_DIR="${SHARED_REPO_ROOT}/.venv"
fi

if [ ! -d "${VENV_DIR}" ]; then
    echo -e "${RED}Error: .venv directory not found.${NC}"
    echo "Please run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 2. Python実行環境の有効化
source "${VENV_DIR}/bin/activate"

if [ "${VENV_DIR}" != "${REPO_ROOT}/.venv" ]; then
    echo -e "${GREEN}Using shared virtualenv: ${VENV_DIR}${NC}"
fi

# 3. 必須JSONファイルの存在・構文チェック
echo -e "${GREEN}Step 1: Validating required deploy JSON files...${NC}"
REQUIRED_JSON_FILES=("public/firebase_config.json" "public/allowed_emails.json")

for json_file in "${REQUIRED_JSON_FILES[@]}"; do
    if [ ! -f "${json_file}" ]; then
        echo -e "${RED}Error: Required file not found: ${json_file}${NC}"
        echo "Please create the file before deploy."
        exit 1
    fi

    if ! python -m json.tool "${json_file}" > /dev/null 2>&1; then
        echo -e "${RED}Error: Invalid JSON format: ${json_file}${NC}"
        exit 1
    fi
done
echo -e "${GREEN}Required JSON files are valid.${NC}"

# 4. 同期処理の実行
echo -e "${GREEN}Step 2: Syncing reports from Firebase to local...${NC}"
python scripts/sync_firebase_reports.py

# 5. カレンダーHTMLの再生成（CSVのレポートリンクを反映）
echo -e "${GREEN}Step 3: Regenerating calendar.html from CSV data...${NC}"
python -m src.calendar_generator
echo -e "${GREEN}Calendar HTML updated.${NC}"

# 6. ユーザー確認 (CI環境以外の場合)
if [ -t 0 ]; then
    echo -e "${GREEN}Sync complete.${NC}"
    read -p "Do you want to proceed with firebase deploy? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Deploy cancelled by user.${NC}"
        exit 1
    fi
fi

# 7. デプロイ実行
echo -e "${GREEN}Step 4: Deploying to Firebase Hosting...${NC}"
firebase deploy --only hosting

echo -e "${GREEN}=== Safe Deploy Complete ===${NC}"
