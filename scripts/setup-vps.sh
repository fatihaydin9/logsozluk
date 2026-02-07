#!/bin/bash
set -euo pipefail

# ============================================
# Logsözlük VPS Kurulum Script'i
# Ubuntu 22.04+ için
# Kullanım: ssh root@SUNUCU_IP < scripts/setup-vps.sh
# ============================================

echo "=== Logsözlük VPS Kurulumu ==="

# 1. Sistem güncellemesi
echo "[1/6] Sistem güncelleniyor..."
apt-get update -qq && apt-get upgrade -y -qq

# 2. Temel paketler
echo "[2/6] Gerekli paketler kuruluyor..."
apt-get install -y -qq git curl ufw fail2ban

# 3. Firewall ayarları
echo "[3/6] Firewall ayarlanıyor..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (Caddy redirect)
ufw allow 443/tcp   # HTTPS (Caddy)
echo "y" | ufw enable

# 4. Docker kurulumu
echo "[4/6] Docker kuruluyor..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
fi

# 5. Deploy kullanıcısı oluştur
echo "[5/6] Deploy kullanıcısı oluşturuluyor..."
if ! id "deploy" &>/dev/null; then
    useradd -m -s /bin/bash -G docker deploy
    mkdir -p /home/deploy/.ssh
    cp /root/.ssh/authorized_keys /home/deploy/.ssh/ 2>/dev/null || true
    chown -R deploy:deploy /home/deploy/.ssh
    chmod 700 /home/deploy/.ssh
    chmod 600 /home/deploy/.ssh/authorized_keys 2>/dev/null || true
    echo "deploy ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/deploy
fi

# 6. Proje dizini
echo "[6/6] Proje dizini hazırlanıyor..."
mkdir -p /opt/logsozluk
chown deploy:deploy /opt/logsozluk

echo ""
echo "=== VPS Kurulumu Tamamlandı ==="
echo ""
echo "Sonraki adımlar:"
echo "  1. ssh deploy@$(hostname -I | awk '{print $1}')"
echo "  2. cd /opt/logsozluk"
echo "  3. git clone https://github.com/fatihaydin9/logsozluk.git ."
echo "  4. cp .env.example .env && nano .env  # Secret'ları düzenle"
echo "  5. make prod-up"
echo ""
echo "DNS: Domain A kaydını şu IP'ye yönlendir: $(hostname -I | awk '{print $1}')"
