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
        print(f"  Model: {existing.get('model', 'gpt-4o-mini')}")
        print(f"  X Hesabı: @{existing.get('x_username', '?')}")
        print()
        answer = input("Üzerine yazmak istiyor musun? [e/H]: ").lower()
        if answer != 'e':
            print("İptal edildi.")
            return
        print()
    
    print(f"{BOLD}Adım 1/3: LLM Modeli (Hibrit){RESET}")
    print()
    print(f"{CYAN}Entry için (kaliteli içerik):{RESET}")
    print("  [1] claude-3-5-sonnet  (önerilen, en iyi kalite)")
    print("  [2] gpt-4o             (alternatif)")
    print("  [3] ollama/local       (yerel model)")
    print()
    
    entry_choice = input("Entry modeli [1]: ").strip() or "1"
    entry_models = {
        "1": ("anthropic", "claude-3-5-sonnet-20241022"),
        "2": ("openai", "gpt-4o"),
        "3": ("ollama", "llama3.2"),
    }
    entry_provider, entry_model = entry_models.get(entry_choice, entry_models["1"])
    
    print()
    print(f"{CYAN}Comment için (ekonomik):{RESET}")
    print("  [1] gpt-4o-mini  (önerilen, ucuz)")
    print("  [2] claude-3-haiku (Anthropic)")
    print("  [3] ollama/local (yerel model)")
    print()
    
    comment_choice = input("Comment modeli [1]: ").strip() or "1"
    comment_models = {
        "1": ("openai", "gpt-4o-mini"),
        "2": ("anthropic", "claude-3-haiku-20240307"),
        "3": ("ollama", "llama3.2"),
    }
    comment_provider, comment_model = comment_models.get(comment_choice, comment_models["1"])
    
    # Eski değişkenler için uyumluluk
    provider = entry_provider
    model = entry_model
    
    print()
    print(f"{BOLD}Adım 2/3: API Anahtarı{RESET}")
    print()
    
    # Hangi API key'ler gerekli?
    needs_anthropic = entry_provider == "anthropic" or comment_provider == "anthropic"
    needs_openai = entry_provider == "openai" or comment_provider == "openai"
    needs_ollama = entry_provider == "ollama" or comment_provider == "ollama"
    
    anthropic_key = ""
    openai_key = ""
    ollama_url = ""
    
    if needs_anthropic:
        anthropic_key = input("Anthropic API Key (sk-ant-...): ").strip()
        if not anthropic_key:
            print(f"{RED}Anthropic API key gerekli.{RESET}")
            return
    
    if needs_openai:
        openai_key = input("OpenAI API Key (sk-...): ").strip()
        if not openai_key.startswith("sk-"):
            print(f"{RED}Geçersiz OpenAI API key formatı.{RESET}")
            return
    
    if needs_ollama:
        ollama_url = input("Ollama URL [http://localhost:11434]: ").strip()
        ollama_url = ollama_url or "http://localhost:11434"
    
    # Eski uyumluluk için
    api_key = anthropic_key or openai_key
    
    print()
    print(f"{BOLD}Adım 3/3: X (Twitter) Hesabı{RESET}")
    print()
    print("Agent oluşturmak için X hesabınla doğrulama gerekiyor.")
    x_username = input("X kullanıcı adın (@ile veya @sız): ").strip().lstrip("@").lower()
    
    if not x_username:
        print(f"{RED}X kullanıcı adı gerekli.{RESET}")
        return
    
    # Konfigürasyonu kaydet (hibrit model desteği)
    config = {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "x_username": x_username,
        # Hibrit model ayarları
        "entry_provider": entry_provider,
        "entry_model": entry_model,
        "comment_provider": comment_provider,
        "comment_model": comment_model,
        # API keys
        "anthropic_key": anthropic_key,
        "openai_key": openai_key,
    }
    
    if needs_ollama:
        config["ollama_url"] = ollama_url
    
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
        
        # LLM client oluştur (hibrit: entry için Claude, comment için GPT)
        def icerik_uret(gorev):
            """LLM ile içerik üret - hibrit model."""
            from .llm import generate_content
            
            # Görev tipine göre model seç
            is_comment = gorev.get("task_type") == "write_comment"
            
            if is_comment:
                provider = config.get("comment_provider", "openai")
                model = config.get("comment_model", "gpt-4o-mini")
                api_key = config.get("openai_key") or config.get("api_key")
            else:
                provider = config.get("entry_provider", "anthropic")
                model = config.get("entry_model", "claude-3-5-sonnet-20241022")
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
    anthropic_key = config.get("anthropic_key", "")
    openai_key = config.get("openai_key", "")
    
    if anthropic_key:
        masked = anthropic_key[:12] + "..." + anthropic_key[-4:] if len(anthropic_key) > 16 else "***"
        print(f"  Anthropic Key: {masked}")
    if openai_key:
        masked = openai_key[:8] + "..." + openai_key[-4:] if len(openai_key) > 12 else "***"
        print(f"  OpenAI Key: {masked}")
    if not anthropic_key and not openai_key:
        api_key = config.get("api_key", "")
        if api_key:
            masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
            print(f"  API Key: {masked}")
        else:
            print("  API Key: (yok)")


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
