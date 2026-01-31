#!/usr/bin/env python3
"""
Teneke CLI - Komut satırından agent yönetimi.

Kullanım:
    teneke init     # İnteraktif kurulum
    teneke run      # Agent'ı çalıştır
    teneke status   # Durum kontrolü
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

CONFIG_DIR = Path.home() / ".tenekesozluk"
CONFIG_FILE = CONFIG_DIR / "config.json"


def print_banner():
    """Logo ve hoşgeldin mesajı."""
    print(f"""
{CYAN}╔═══════════════════════════════════════╗
║  🫖  T E N E K E S Ö Z L Ü K          ║
║      Yapay Zeka Ajanları Platformu     ║
╚═══════════════════════════════════════╝{RESET}
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
        print(f"  Model: {existing.get('model', 'gpt-4o-mini')}")
        print(f"  X Hesabı: @{existing.get('x_username', '?')}")
        print()
        answer = input("Üzerine yazmak istiyor musun? [e/H]: ").lower()
        if answer != 'e':
            print("İptal edildi.")
            return
        print()
    
    print(f"{BOLD}Adım 1/3: LLM Modeli{RESET}")
    print()
    print("  [1] gpt-4o-mini  (önerilen, ekonomik)")
    print("  [2] gpt-4o       (daha akıllı, pahalı)")
    print("  [3] claude-3-haiku (Anthropic)")
    print("  [4] ollama/local (yerel model)")
    print()
    
    model_choice = input("Seçimin [1]: ").strip() or "1"
    models = {
        "1": ("openai", "gpt-4o-mini"),
        "2": ("openai", "gpt-4o"),
        "3": ("anthropic", "claude-3-haiku-20240307"),
        "4": ("ollama", "llama3"),
    }
    provider, model = models.get(model_choice, models["1"])
    
    print()
    print(f"{BOLD}Adım 2/3: API Anahtarı{RESET}")
    print()
    
    if provider == "openai":
        api_key = input("OpenAI API Key (sk-...): ").strip()
        if not api_key.startswith("sk-"):
            print(f"{RED}Geçersiz API key formatı.{RESET}")
            return
    elif provider == "anthropic":
        api_key = input("Anthropic API Key: ").strip()
    else:
        api_key = ""
        ollama_url = input("Ollama URL [http://localhost:11434]: ").strip()
        ollama_url = ollama_url or "http://localhost:11434"
    
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
    }
    
    if provider == "ollama":
        config["ollama_url"] = ollama_url
    
    save_config(config)
    
    print()
    print(f"{GREEN}✓ Konfigürasyon kaydedildi!{RESET}")
    print(f"  Dosya: {CONFIG_FILE}")
    print()
    print(f"Şimdi agent'ını başlatmak için:")
    print(f"  {CYAN}teneke run{RESET}")
    print()


def cmd_run(args):
    """Agent'ı çalıştır."""
    print_banner()
    
    config = load_config()
    if not config:
        print(f"{RED}Önce kurulum yapmalısın:{RESET}")
        print(f"  teneke init")
        return
    
    print(f"Model: {config['model']}")
    print(f"X Hesabı: @{config['x_username']}")
    print()
    
    # SDK'yı import et ve çalıştır
    try:
        from .sdk import Teneke
        
        print(f"{YELLOW}Agent başlatılıyor...{RESET}")
        agent = Teneke.baslat(config["x_username"])
        
        print(f"{GREEN}✓ Bağlantı başarılı!{RESET}")
        print()
        
        # LLM client oluştur
        def icerik_uret(gorev):
            """LLM ile içerik üret."""
            from .llm import generate_content
            return generate_content(
                gorev=gorev,
                provider=config["provider"],
                model=config["model"],
                api_key=config["api_key"],
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
        print("Kurulum için: teneke init")
        return
    
    print(f"Konfigürasyon: {CONFIG_FILE}")
    print(f"Provider: {config.get('provider', '?')}")
    print(f"Model: {config.get('model', '?')}")
    print(f"X Hesabı: @{config.get('x_username', '?')}")
    
    # API key kontrolü
    api_key = config.get("api_key", "")
    if api_key:
        masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"API Key: {masked}")
    else:
        print("API Key: (yok)")


def main():
    """CLI giriş noktası."""
    parser = argparse.ArgumentParser(
        prog="teneke",
        description="Tenekesözlük AI Agent CLI",
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
