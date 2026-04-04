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

# 2. Obtain proxy CA certificate and configure ~/.boto
python3 << 'PYEOF'
import socket, ssl, os, base64, urllib.parse

proxy_url = os.environ.get('https_proxy') or os.environ.get('HTTPS_PROXY', '')
if not proxy_url:
    print('[session-start] No proxy detected, skipping CA cert setup')
    exit(0)

p = urllib.parse.urlparse(proxy_url)
TARGET = 'storage.googleapis.com'
try:
    creds = base64.b64encode(f'{p.username or ""}:{p.password or ""}'.encode()).decode()
    sock = socket.create_connection((p.hostname, p.port), timeout=10)
    sock.sendall(f'CONNECT {TARGET}:443 HTTP/1.1\r\nHost: {TARGET}\r\nProxy-Authorization: Basic {creds}\r\n\r\n'.encode())
    resp = sock.recv(4096)
    if b'200' in resp:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        tls = ctx.wrap_socket(sock, server_hostname=TARGET)
        cert_pem = ssl.DER_cert_to_PEM_cert(tls.getpeercert(binary_form=True))
        tls.close()
        system_ca = open('/etc/ssl/certs/ca-certificates.crt').read()
        open('/tmp/combined-ca.pem', 'w').write(system_ca + '\n' + cert_pem)
        print('[session-start] Proxy CA cert configured.')
    sock.close()
except Exception as e:
    print(f'[session-start] CA cert setup skipped: {e}')
PYEOF

# 3. Configure ~/.boto for gsutil
if [ -f /tmp/combined-ca.pem ]; then
  cat > ~/.boto << 'BOTOEOF'
[Boto]
ca_certificates_file = /tmp/combined-ca.pem

[GSUtil]
parallel_process_count = 1
BOTOEOF
fi

# 4. Activate GCP service account from environment variable
# Set GCP_SERVICE_ACCOUNT_KEY in claude.ai/code Environment settings
if [ -n "${GCP_SERVICE_ACCOUNT_KEY:-}" ]; then
  echo "$GCP_SERVICE_ACCOUNT_KEY" > /tmp/gcp-sa-key.json
  chmod 600 /tmp/gcp-sa-key.json
  "$GCLOUD" auth activate-service-account --key-file=/tmp/gcp-sa-key.json --quiet 2>&1
  "$GCLOUD" config set project gen-lang-client-0394252790 --quiet 2>&1
  echo "[session-start] GCS authentication complete."
else
  echo "[session-start] GCP_SERVICE_ACCOUNT_KEY not set. GCS access unavailable."
fi

# 5. Export PATH
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export PATH=${GCLOUD_DIR}/bin:\$PATH" >> "$CLAUDE_ENV_FILE"
fi
