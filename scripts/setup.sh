#!/usr/bin/env bash
# Phase 1 setup script for Raspberry Pi OS Lite (aarch64).
# Run once with internet access, then deploy offline to car.
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VOSK_MODEL="vosk-model-ja-0.22"
VOSK_URL="https://alphacephei.com/vosk/models/${VOSK_MODEL}.zip"
PIPER_VERSION="v1.2.0"
PIPER_URL="https://github.com/rhasspy/piper/releases/download/${PIPER_VERSION}/piper_linux_aarch64.tar.gz"
KOKORO_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/ja/ja_JP/kokoro/medium"

echo "=== Japanese Tutor — Phase 1 Setup ==="

# ── 1. System deps ──
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
    python3 python3-pip python3-venv \
    sqlite3 unzip curl wget git \
    build-essential

# ── 2. Wi-Fi hotspot ──
sudo apt install -y hostapd dnsmasq

sudo tee /etc/hostapd/hostapd.conf > /dev/null <<'EOF'
interface=wlan0
driver=nl80211
ssid=JapaneseTutor
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=JapaneseTutor123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

sudo sed -i 's|#DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

sudo tee /etc/dnsmasq.conf > /dev/null <<'EOF'
interface=wlan0
dhcp-range=192.168.50.10,192.168.50.100,255.255.255.0,24h
EOF

# Static IP for wlan0
sudo tee /etc/network/interfaces.d/wlan0 > /dev/null <<'EOF'
allow-hotplug wlan0
iface wlan0 inet static
    address 192.168.50.1
    netmask 255.255.255.0
EOF

sudo systemctl unmask hostapd
sudo systemctl enable hostapd dnsmasq
echo "Hotspot configured — SSID: JapaneseTutor, IP: 192.168.50.1"

# ── 3. Caddy ──
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy

sudo cp "$(dirname "$0")/../caddy/Caddyfile" /etc/caddy/Caddyfile
sudo systemctl enable caddy

# ── 4. App directory ──
mkdir -p "${INSTALL_DIR}/models/vosk"
mkdir -p "${INSTALL_DIR}/models/piper"
mkdir -p "${INSTALL_DIR}/data/tts_cache"

# ── 5. Python venv ──
python3 -m venv "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip
"${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

# ── 6. Vosk Japanese model ──
echo "Downloading Vosk Japanese model (~1.3 GB)…"
wget -q --show-progress -O /tmp/vosk-ja.zip "${VOSK_URL}"
unzip -q /tmp/vosk-ja.zip -d "${INSTALL_DIR}/models/vosk/"
rm /tmp/vosk-ja.zip
echo "Vosk model installed."

# ── 7. Piper TTS (Phase 3 — downloaded now for offline use later) ──
echo "Downloading Piper TTS binary…"
wget -q --show-progress -O /tmp/piper.tar.gz "${PIPER_URL}"
tar -xzf /tmp/piper.tar.gz -C "${INSTALL_DIR}/models/piper/" --strip-components=1
rm /tmp/piper.tar.gz
chmod +x "${INSTALL_DIR}/models/piper/piper"

echo "Downloading Piper Japanese voice…"
wget -q --show-progress -O "${INSTALL_DIR}/models/piper/ja_JP-kokoro-medium.onnx" \
    "${KOKORO_BASE}/ja_JP-kokoro-medium.onnx"
wget -q --show-progress -O "${INSTALL_DIR}/models/piper/ja_JP-kokoro-medium.onnx.json" \
    "${KOKORO_BASE}/ja_JP-kokoro-medium.onnx.json"
echo "Piper installed."

# ── 8. Systemd service ──
sudo tee /etc/systemd/system/japanesetutor.service > /dev/null <<EOF
[Unit]
Description=Japanese Tutor FastAPI Server
After=network.target

[Service]
User=pi
WorkingDirectory=${INSTALL_DIR}
Environment=TUTOR_BASE_DIR=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/uvicorn server.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable japanesetutor

echo ""
echo "=== Setup complete ==="
echo "Reboot, then:"
echo "  1. Connect phone to Wi-Fi: JapaneseTutor / JapaneseTutor123"
echo "  2. Open https://192.168.50.1 in phone browser"
echo "  3. Accept cert warning (one-time)"
echo "     Better: install Caddy root CA — see caddy/Caddyfile comments"
echo "  4. Kana drills ready!"
