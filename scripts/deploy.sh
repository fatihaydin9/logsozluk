#!/bin/bash
set -euo pipefail

# ============================================
# Logsözlük Deploy Script'i
# Kullanım: ssh deploy@SUNUCU_IP 'cd /opt/logsozluk && ./scripts/deploy.sh'
# ============================================

echo "=== Logsözlük Deploy ==="

cd /opt/logsozluk

# 1. Son kodu çek
echo "[1/4] Kod çekiliyor..."
git pull origin main

# 2. Image'ları build et
echo "[2/4] Docker image'lar build ediliyor..."
docker compose build --no-cache frontend
docker compose build api-gateway agenda-engine

# 3. Servisleri yeniden başlat
echo "[3/4] Servisler yeniden başlatılıyor..."
docker compose up -d

# 4. Health check
echo "[4/4] Sağlık kontrolü..."
sleep 10
docker compose ps

echo ""
echo "=== Deploy Tamamlandı ==="
