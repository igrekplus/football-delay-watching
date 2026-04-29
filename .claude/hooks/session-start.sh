#!/bin/bash
set -euo pipefail

# Only run in remote (Claude Code web) environment
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

GCLOUD_DIR="/opt/google-cloud-sdk"
GCLOUD="${GCLOUD_DIR}/bin/gcloud"

# 1. Install gcloud SDK if not present
if [ ! -f "$GCLOUD" ]; then
  echo "[session-start] Installing gcloud SDK..."
  curl -fsSL "https://storage.googleapis.com/cloud-sdk-release/google-cloud-cli-linux-x86_64.tar.gz" \
    -o /tmp/gcloud.tar.gz
  tar -xzf /tmp/gcloud.tar.gz -C /opt/
  rm -f /tmp/gcloud.tar.gz
  echo "[session-start] gcloud SDK installed."
fi
ln -sf "${GCLOUD_DIR}/bin/gcloud" /usr/local/bin/gcloud 2>/dev/null || true
ln -sf "${GCLOUD_DIR}/bin/gsutil" /usr/local/bin/gsutil 2>/dev/null || true

# 2. Detect TLS interception (explicit proxy or transparent) and configure CA certs
# Handles both env-var proxies and Anthropic sandbox's transparent TLS inspection proxy.
# Sets /tmp/combined-ca.pem which is used by gsutil (~/.boto), gRPC, and requests.
python3 << 'PYEOF'
import subprocess, re, os

TARGET = 'generativelanguage.googleapis.com'
SYSTEM_CA = '/etc/ssl/certs/ca-certificates.crt'
COMBINED_CA = '/tmp/combined-ca.pem'

# Get full cert chain via openssl (works for both explicit and transparent proxies)
try:
    result = subprocess.run(
        ['openssl', 's_client', '-connect', f'{TARGET}:443', '-showcerts'],
        input=b'Q', capture_output=True, timeout=10
    )
    output = result.stdout.decode('utf-8', errors='ignore') + result.stderr.decode('utf-8', errors='ignore')

    # Extract all PEM certs from chain
    certs = re.findall(r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', output, re.DOTALL)

    # Check if any cert's issuer is non-standard (not Google/DigiCert/GlobalSign etc.)
    standard_issuers = ('Google', 'DigiCert', 'GlobalSign', 'Entrust', 'Sectigo', 'Amazon', 'Let\'s Encrypt')
    non_standard = []
    for cert_pem in certs:
        issuer_result = subprocess.run(
            ['openssl', 'x509', '-noout', '-issuer'],
            input=cert_pem.encode(), capture_output=True
        )
        issuer = issuer_result.stdout.decode()
        if not any(s in issuer for s in standard_issuers):
            non_standard.append(cert_pem)

    if non_standard:
        # Use the last non-standard cert (likely the root CA)
        ca_cert = non_standard[-1]
        issuer_result = subprocess.run(
            ['openssl', 'x509', '-noout', '-issuer'],
            input=ca_cert.encode(), capture_output=True
        )
        issuer_str = issuer_result.stdout.decode().strip()
        system_ca = open(SYSTEM_CA).read()
        open(COMBINED_CA, 'w').write(system_ca + '\n' + ca_cert + '\n')
        print(f'[session-start] TLS inspection CA detected and configured: {issuer_str}')
    else:
        print('[session-start] No TLS interception detected, skipping CA cert setup')

except Exception as e:
    print(f'[session-start] CA cert setup skipped: {e}')
PYEOF

# 3. Configure ~/.boto (gsutil), gRPC, and requests with the combined CA bundle
if [ -f /tmp/combined-ca.pem ]; then
  cat > ~/.boto << 'BOTOEOF'
[Boto]
ca_certificates_file = /tmp/combined-ca.pem

[GSUtil]
parallel_process_count = 1
BOTOEOF

  # gRPC (google-generativeai SDK uses gRPC with its own SSL roots)
  export GRPC_DEFAULT_SSL_ROOTS_FILE_PATH=/tmp/combined-ca.pem
  # requests / urllib3
  export REQUESTS_CA_BUNDLE=/tmp/combined-ca.pem
  export SSL_CERT_FILE=/tmp/combined-ca.pem
  if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    echo "export GRPC_DEFAULT_SSL_ROOTS_FILE_PATH=/tmp/combined-ca.pem" >> "$CLAUDE_ENV_FILE"
    echo "export REQUESTS_CA_BUNDLE=/tmp/combined-ca.pem" >> "$CLAUDE_ENV_FILE"
    echo "export SSL_CERT_FILE=/tmp/combined-ca.pem" >> "$CLAUDE_ENV_FILE"
  fi
fi

# 4. Activate GCP service account from environment variable
# Set GCP_SERVICE_ACCOUNT_KEY in claude.ai/code Environment settings
if [ -n "${GCP_SERVICE_ACCOUNT_KEY:-}" ]; then
  echo "$GCP_SERVICE_ACCOUNT_KEY" > /tmp/gcp-sa-key.json
  chmod 600 /tmp/gcp-sa-key.json
  "$GCLOUD" auth activate-service-account --key-file=/tmp/gcp-sa-key.json --quiet 2>&1
  "$GCLOUD" config set project gen-lang-client-0394252790 --quiet 2>&1
  # Set ADC for Google Cloud Python SDK (google-cloud-storage etc.)
  export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-sa-key.json
  if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    echo "export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-sa-key.json" >> "$CLAUDE_ENV_FILE"
  fi
  echo "[session-start] GCS authentication complete."

  # 5. Load application secrets from Secret Manager into session environment
  echo "[session-start] Loading secrets from Secret Manager..."
  PROJECT="gen-lang-client-0394252790"
  SECRETS="API_FOOTBALL_KEY GOOGLE_API_KEY GOOGLE_SEARCH_ENGINE_ID GOOGLE_SEARCH_API_KEY YOUTUBE_API_KEY NOTIFY_EMAIL GMAIL_TOKEN GMAIL_CREDENTIALS FIREBASE_CONFIG ALLOWED_EMAILS GITHUB_TOKEN ANTHROPIC_API_KEY"
  LOADED=0
  FAILED=0
  for SECRET_NAME in $SECRETS; do
    VALUE=$("$GCLOUD" secrets versions access latest --secret="$SECRET_NAME" --project="$PROJECT" 2>/dev/null) || {
      echo "[session-start] WARNING: Failed to load secret: $SECRET_NAME"
      FAILED=$((FAILED + 1))
      continue
    }
    if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
      printf 'export %s=%q\n' "$SECRET_NAME" "$VALUE" >> "$CLAUDE_ENV_FILE"
    fi
    export "$SECRET_NAME=$VALUE"
    LOADED=$((LOADED + 1))
  done
  echo "[session-start] Secrets loaded: ${LOADED} ok, ${FAILED} failed."

  # 6. Authenticate gh CLI using GITHUB_TOKEN from Secret Manager
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    if ! command -v gh &>/dev/null; then
      echo "[session-start] Installing gh CLI..."
      apt-get install -y gh -qq 2>/dev/null || true
    fi
    echo "${GITHUB_TOKEN}" | gh auth login --with-token 2>/dev/null || true
    gh auth status 2>/dev/null | grep -q "Logged in" \
      && echo "[session-start] gh CLI authenticated." \
      || echo "[session-start] WARNING: gh auth status check failed."
  fi

  # 7. Set up Python venv (skip if requirements.txt unchanged)
  PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
  VENV_DIR="${PROJECT_DIR}/.venv"
  REQUIREMENTS="${PROJECT_DIR}/requirements.txt"
  HASH_FILE="${VENV_DIR}/.requirements_hash"
  if [ -f "$REQUIREMENTS" ]; then
    CURRENT_HASH=$(md5sum "$REQUIREMENTS" | cut -d' ' -f1)
    CACHED_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "")
    if [ ! -d "$VENV_DIR" ] || [ "$CURRENT_HASH" != "$CACHED_HASH" ]; then
      echo "[session-start] Setting up Python venv..."
      python3.11 -m venv "$VENV_DIR"
      "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS" -q
      echo "$CURRENT_HASH" > "$HASH_FILE"
      echo "[session-start] Python venv ready."
    else
      echo "[session-start] Python venv up-to-date (skipping install)."
    fi
    # Export venv python to CLAUDE_ENV_FILE so Claude uses it by default
    if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
      echo "export PATH=${VENV_DIR}/bin:\$PATH" >> "$CLAUDE_ENV_FILE"
    fi
    export PATH="${VENV_DIR}/bin:$PATH"
  fi
else
  echo "[session-start] GCP_SERVICE_ACCOUNT_KEY not set. GCS access unavailable."
fi

# 8. Export gcloud PATH
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export PATH=${GCLOUD_DIR}/bin:\$PATH" >> "$CLAUDE_ENV_FILE"
fi
