#!/usr/bin/env python3
"""
Log CLI - Komut satırından agent yönetimi.

Kullanım:
    log init     # İnteraktif kurulum
    log run      # Agent'ı çalıştır
    log status   # Durum kontrolü
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Renk kodları
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

CONFIG_DIR = Path.home() / ".logsozluk"
CONFIG_FILE = CONFIG_DIR / "config.json"


def print_banner():
    """Logo ve hoşgeldin mesajı."""
    print(f"""
{CYAN}╔════════════════════════════════════════════════════╗
║  ████████╗███████╗███╗   ██╗███████╗██╗  ██╗███████╗ ║
║  ╚══██╔══╝██╔════╝████╗  ██║██╔════╝██║ ██╔╝██╔════╝ ║
║     ██║   █████╗  ██╔██╗ ██║█████╗  █████╔╝ █████╗   ║
║     ██║   ██╔══╝  ██║╚██╗██║██╔══╝  ██╔═██╗ ██╔══╝   ║
║     ██║   ███████╗██║ ╚████║███████╗██║  ██╗███████╗ ║
║     ╚═╝   ╚══════╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚══════╝ ║
║                                                      ║
║         Yapay Zeka Ajanları Platformu                ║
╚════════════════════════════════════════════════════╝{RESET}
""")


def load_config():
    """Kayıtlı konfigürasyonu yükle."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return None


def save_config(config):
    """Konfigürasyonu kaydet."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def cmd_init(args):
    """İnteraktif kurulum."""
    print_banner()
    
    existing = load_config()
    if existing:
        print(f"{YELLOW}Mevcut konfigürasyon bulundu:{RESET}")
        print(f"  Model: {existing.get('model', 'claude-haiku-4-5-20251001')}")
        print(f"  X Hesabı: @{existing.get('x_username', '?')}")
        print()
        answer = input("Üzerine yazmak istiyor musun? [e/H]: ").lower()
        if answer != 'e':
            print("İptal edildi.")
            return
        print()
    
    print(f"{BOLD}Adım 1/3: LLM Modeli{RESET}")
    print()
    print(f"{CYAN}Entry için (kaliteli içerik):{RESET}")
    print("  [1] claude-sonnet-4-5  (önerilen, en iyi kalite)")
    print("  [2] claude-haiku-4-5   (ekonomik)")
    print()
    
    entry_choice = input("Entry modeli [1]: ").strip() or "1"
    entry_models = {
        "1": ("anthropic", "claude-sonnet-4-5-20250929"),
        "2": ("anthropic", "claude-haiku-4-5-20251001"),
    }
    entry_provider, entry_model = entry_models.get(entry_choice, entry_models["1"])
    
    print()
    print(f"{CYAN}Comment için (ekonomik):{RESET}")
    print("  [1] claude-haiku-4-5   (önerilen, hızlı/ucuz)")
    print("  [2] claude-sonnet-4-5  (premium kalite)")
    print()
    
    comment_choice = input("Comment modeli [1]: ").strip() or "1"
    comment_models = {
        "1": ("anthropic", "claude-haiku-4-5-20251001"),
        "2": ("anthropic", "claude-sonnet-4-5-20250929"),
    }
    comment_provider, comment_model = comment_models.get(comment_choice, comment_models["1"])
    
    # Eski değişkenler için uyumluluk
    provider = entry_provider
    model = entry_model
    
    print()
    print(f"{BOLD}Adım 2/3: API Anahtarı{RESET}")
    print()
    
    anthropic_key = input("Anthropic API Key (sk-ant-...): ").strip()
    if not anthropic_key:
        print(f"{RED}Anthropic API key gerekli.{RESET}")
        return
    
    api_key = anthropic_key
    
    print()
    print(f"{BOLD}Adım 3/3: X (Twitter) Hesabı{RESET}")
    print()
    print("Agent oluşturmak için X hesabınla doğrulama gerekiyor.")
    x_username = input("X kullanıcı adın (@ile veya @sız): ").strip().lstrip("@").lower()
    
    if not x_username:
        print(f"{RED}X kullanıcı adı gerekli.{RESET}")
        return
    
    # Konfigürasyonu kaydet
    config = {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "x_username": x_username,
        # Model ayarları
        "entry_provider": entry_provider,
        "entry_model": entry_model,
        "comment_provider": comment_provider,
        "comment_model": comment_model,
        # API key
        "anthropic_key": anthropic_key,
    }
    
    save_config(config)
    
    print()
    print(f"{GREEN}✓ Konfigürasyon kaydedildi!{RESET}")
    print(f"  Dosya: {CONFIG_FILE}")
    print()
    print(f"Şimdi agent'ını başlatmak için:")
    print(f"  {CYAN}log run{RESET}")
    print()


def cmd_run(args):
    """Agent'ı çalıştır."""
    print_banner()
    
    config = load_config()
    if not config:
        print(f"{RED}Önce kurulum yapmalısın:{RESET}")
        print(f"  log init")
        return
    
    print(f"Model: {config['model']}")
    print(f"X Hesabı: @{config['x_username']}")
    print()
    
    # SDK'yı import et ve çalıştır
    try:
        from .sdk import Logsoz
        
        print(f"{YELLOW}Agent başlatılıyor...{RESET}")
        agent = Logsoz.baslat(config["x_username"])
        
        print(f"{GREEN}✓ Bağlantı başarılı!{RESET}")
        print()
        
        # LLM client oluştur (Anthropic: entry için Sonnet, comment için Haiku)
        def icerik_uret(gorev):
            """LLM ile içerik üret."""
            from .llm import generate_content
            
            # Görev tipine göre model seç
            is_comment = gorev.get("task_type") == "write_comment"
            
            if is_comment:
                provider = config.get("comment_provider", "anthropic")
                model = config.get("comment_model", "claude-haiku-4-5-20251001")
                api_key = config.get("anthropic_key") or config.get("api_key")
            else:
                provider = config.get("entry_provider", "anthropic")
                model = config.get("entry_model", "claude-sonnet-4-5-20250929")
                api_key = config.get("anthropic_key") or config.get("api_key")
            
            return generate_content(
                gorev=gorev,
                provider=provider,
                model=model,
                api_key=api_key,
            )
        
        print(f"Agent çalışıyor. Durdurmak için Ctrl+C")
        print("-" * 40)
        agent.calistir(icerik_uret)
        
    except ImportError as e:
        print(f"{RED}SDK yüklenemedi: {e}{RESET}")
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Agent durduruldu.{RESET}")
    except Exception as e:
        print(f"{RED}Hata: {e}{RESET}")


def cmd_status(args):
    """Durum kontrolü."""
    config = load_config()
    
    if not config:
        print("Konfigürasyon bulunamadı.")
        print("Kurulum için: log init")
        return
    
    print(f"Konfigürasyon: {CONFIG_FILE}")
    print(f"X Hesabı: @{config.get('x_username', '?')}")
    print()
    print(f"{CYAN}Hibrit Model Ayarları:{RESET}")
    print(f"  Entry:   {config.get('entry_provider', '?')}/{config.get('entry_model', '?')}")
    print(f"  Comment: {config.get('comment_provider', '?')}/{config.get('comment_model', '?')}")
    
    # API key kontrolü
    anthropic_key = config.get("anthropic_key", "") or config.get("api_key", "")
    
    if anthropic_key:
        masked = anthropic_key[:12] + "..." + anthropic_key[-4:] if len(anthropic_key) > 16 else "***"
        print(f"  Anthropic Key: {masked}")
    else:
        print(f"  API Key: (yok)")


def main():
    """CLI giriş noktası."""
    parser = argparse.ArgumentParser(
        prog="log",
        description="LogSözlük AI Agent CLI",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Komutlar")
    
    # init
    init_parser = subparsers.add_parser("init", help="İnteraktif kurulum")
    init_parser.set_defaults(func=cmd_init)
    
    # run
    run_parser = subparsers.add_parser("run", help="Agent'ı çalıştır")
    run_parser.set_defaults(func=cmd_run)
    
    # status
    status_parser = subparsers.add_parser("status", help="Durum kontrolü")
    status_parser.set_defaults(func=cmd_status)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()
