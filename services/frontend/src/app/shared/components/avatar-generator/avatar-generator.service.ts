import { Injectable } from '@angular/core';
import {
  AvatarConfig,
  CharacterType,
  Expression,
  MetalTone,
  METAL_COLORS,
  DEFAULT_AVATAR,
} from './avatar.types';

@Injectable({
  providedIn: 'root'
})
export class AvatarGeneratorService {

  private readonly characters: CharacterType[] = [
    'classic_cola', 'crushed_rebel', 'energy_maniac', 'vintage_tin',
    'coffee_addict', 'spray_artist', 'oil_drum', 'sardine_tin',
    'paint_bucket', 'soup_can', 'beer_belly', 'soda_pop'
  ];
  private readonly expressions: Expression[] = ['grin', 'meh', 'derp', 'angry', 'cool', 'worried', 'sleepy', 'excited'];
  private readonly tones: MetalTone[] = [
    'aluminum', 'steel', 'copper', 'gold', 'rusty', 'chrome',
    'painted_red', 'painted_blue', 'painted_green', 'painted_black'
  ];

  generateFromSeed(seed: string): AvatarConfig {
    const hash = this.hashString(seed);
    return {
      character: this.characters[hash % this.characters.length],
      expression: this.expressions[(hash >> 4) % this.expressions.length],
      tone: this.tones[(hash >> 8) % this.tones.length],
      seed,
    };
  }

  generateRandom(): AvatarConfig {
    return {
      character: this.randomItem(this.characters),
      expression: this.randomItem(this.expressions),
      tone: this.randomItem(this.tones),
    };
  }

  generateSVG(config: AvatarConfig, size: number = 100): string {
    const m = METAL_COLORS[config.tone];
    const id = config.seed || Math.random().toString(36).slice(2, 8);

    return `
      <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <!-- Metalik silindir gradient -->
          <linearGradient id="metalBody-${id}" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="${m.dark}"/>
            <stop offset="20%" stop-color="${m.base}"/>
            <stop offset="35%" stop-color="${m.light}"/>
            <stop offset="45%" stop-color="${m.reflection}"/>
            <stop offset="55%" stop-color="${m.light}"/>
            <stop offset="80%" stop-color="${m.base}"/>
            <stop offset="100%" stop-color="${m.dark}"/>
          </linearGradient>

          <!-- Üst kapak gradient -->
          <radialGradient id="topCap-${id}" cx="40%" cy="40%">
            <stop offset="0%" stop-color="${m.shine}"/>
            <stop offset="40%" stop-color="${m.light}"/>
            <stop offset="100%" stop-color="${m.dark}"/>
          </radialGradient>

          <!-- Alt gölge gradient -->
          <linearGradient id="bottomShade-${id}" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="${m.base}"/>
            <stop offset="100%" stop-color="${m.dark}"/>
          </linearGradient>

          <!-- Parlama highlight -->
          <linearGradient id="shine-${id}" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="white" stop-opacity="0.6"/>
            <stop offset="100%" stop-color="white" stop-opacity="0"/>
          </linearGradient>

          <!-- Gölge filtresi -->
          <filter id="shadow-${id}" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="2" dy="4" stdDeviation="3" flood-opacity="0.3"/>
          </filter>
        </defs>

        <g filter="url(#shadow-${id})">
          ${this.renderCharacter(config.character, m, id)}
          ${this.renderFace(config.expression, config.character)}
        </g>
      </svg>
    `;
  }

  private renderCharacter(char: CharacterType, m: any, id: string): string {
    switch (char) {
      case 'classic_cola':
        return `
          <!-- Klasik kola tenekesi -->
          <ellipse cx="50" cy="88" rx="26" ry="7" fill="${m.dark}"/>
          <rect x="24" y="22" width="52" height="66" rx="2" fill="url(#metalBody-${id})"/>
          <ellipse cx="50" cy="22" rx="26" ry="7" fill="url(#topCap-${id})"/>
          <!-- Üst kenar -->
          <ellipse cx="50" cy="22" rx="22" ry="5" fill="${m.dark}" opacity="0.3"/>
          <!-- Alt kenar -->
          <ellipse cx="50" cy="88" rx="26" ry="5" fill="${m.dark}" opacity="0.4"/>
          <!-- Parlama şeridi -->
          <rect x="28" y="25" width="8" height="58" rx="2" fill="url(#shine-${id})" opacity="0.4"/>
          <!-- Açma halkası -->
          <ellipse cx="50" cy="18" rx="10" ry="3" fill="${m.light}" stroke="${m.dark}" stroke-width="1"/>
          <ellipse cx="50" cy="18" rx="6" ry="2" fill="${m.dark}" opacity="0.5"/>
          <circle cx="56" cy="14" r="3" fill="${m.light}" stroke="${m.dark}" stroke-width="0.5"/>
        `;

      case 'crushed_rebel':
        return `
          <!-- Ezilmiş teneke -->
          <path d="M 28 85 Q 35 92 50 90 Q 65 92 72 85 L 76 50 Q 68 45 50 48 Q 32 45 24 50 Z" fill="url(#metalBody-${id})"/>
          <ellipse cx="50" cy="28" rx="24" ry="8" fill="url(#topCap-${id})" transform="rotate(-12 50 28)"/>
          <!-- Ezik çizgiler -->
          <path d="M 26 55 Q 40 52 74 58" stroke="${m.dark}" stroke-width="2" fill="none" opacity="0.5"/>
          <path d="M 25 70 Q 50 65 73 72" stroke="${m.dark}" stroke-width="2" fill="none" opacity="0.4"/>
          <!-- Hasar detayları -->
          <ellipse cx="65" cy="60" rx="5" ry="8" fill="${m.dark}" opacity="0.2"/>
          <!-- Açık kapak -->
          <path d="M 40 22 Q 50 15 60 22" stroke="${m.light}" stroke-width="2" fill="none"/>
          <ellipse cx="50" cy="20" rx="8" ry="4" fill="${m.dark}" opacity="0.8"/>
        `;

      case 'energy_maniac':
        return `
          <!-- İnce uzun enerji içeceği -->
          <ellipse cx="50" cy="92" rx="18" ry="5" fill="${m.dark}"/>
          <rect x="32" y="12" width="36" height="80" rx="2" fill="url(#metalBody-${id})"/>
          <ellipse cx="50" cy="12" rx="18" ry="5" fill="url(#topCap-${id})"/>
          <!-- Şimşek deseni -->
          <polygon points="45,30 55,30 48,50 56,50 42,75 50,55 42,55" fill="${m.shine}" opacity="0.6"/>
          <!-- Parlama -->
          <rect x="35" y="15" width="5" height="70" rx="1" fill="url(#shine-${id})" opacity="0.5"/>
          <!-- Üst detay -->
          <rect x="32" y="16" width="36" height="4" fill="${m.dark}" opacity="0.3"/>
          <rect x="32" y="84" width="36" height="4" fill="${m.dark}" opacity="0.3"/>
        `;

      case 'vintage_tin':
        return `
          <!-- Vintage konserve -->
          <ellipse cx="50" cy="85" rx="30" ry="10" fill="${m.dark}"/>
          <rect x="20" y="25" width="60" height="60" rx="3" fill="url(#metalBody-${id})"/>
          <ellipse cx="50" cy="25" rx="30" ry="10" fill="url(#topCap-${id})"/>
          <!-- Kenar çizgileri -->
          <ellipse cx="50" cy="30" rx="28" ry="3" fill="none" stroke="${m.dark}" stroke-width="2" opacity="0.4"/>
          <ellipse cx="50" cy="80" rx="28" ry="3" fill="none" stroke="${m.dark}" stroke-width="2" opacity="0.4"/>
          <!-- Retro etiket alanı -->
          <rect x="25" y="40" width="50" height="30" rx="2" fill="${m.light}" opacity="0.15"/>
          <!-- Vintage çizgiler -->
          <line x1="25" y1="45" x2="75" y2="45" stroke="${m.dark}" stroke-width="1" opacity="0.3"/>
          <line x1="25" y1="65" x2="75" y2="65" stroke="${m.dark}" stroke-width="1" opacity="0.3"/>
        `;

      case 'coffee_addict':
        return `
          <!-- Kahve kutusu - kulplu -->
          <ellipse cx="50" cy="88" rx="22" ry="6" fill="${m.dark}"/>
          <rect x="28" y="28" width="44" height="60" rx="2" fill="url(#metalBody-${id})"/>
          <ellipse cx="50" cy="28" rx="22" ry="6" fill="url(#topCap-${id})"/>
          <!-- Kulp -->
          <path d="M 72 40 Q 85 40 85 55 Q 85 70 72 70" stroke="${m.base}" stroke-width="6" fill="none"/>
          <path d="M 72 40 Q 82 40 82 55 Q 82 70 72 70" stroke="${m.light}" stroke-width="3" fill="none"/>
          <!-- Buhar delikleri -->
          <circle cx="42" cy="24" r="2" fill="${m.dark}" opacity="0.6"/>
          <circle cx="50" cy="24" r="2" fill="${m.dark}" opacity="0.6"/>
          <circle cx="58" cy="24" r="2" fill="${m.dark}" opacity="0.6"/>
          <!-- Buhar -->
          <path d="M 45 18 Q 43 12 46 8" stroke="${m.light}" stroke-width="2" fill="none" opacity="0.5"/>
          <path d="M 55 18 Q 57 10 54 5" stroke="${m.light}" stroke-width="2" fill="none" opacity="0.5"/>
        `;

      case 'spray_artist':
        return `
          <!-- Sprey boya kutusu -->
          <ellipse cx="50" cy="90" rx="20" ry="6" fill="${m.dark}"/>
          <rect x="30" y="30" width="40" height="60" rx="2" fill="url(#metalBody-${id})"/>
          <ellipse cx="50" cy="30" rx="20" ry="6" fill="url(#topCap-${id})"/>
          <!-- Sprey başlığı -->
          <rect x="44" y="12" width="12" height="18" rx="2" fill="${m.dark}"/>
          <ellipse cx="50" cy="12" rx="6" ry="3" fill="${m.light}"/>
          <rect x="46" y="8" width="8" height="6" rx="2" fill="${m.base}"/>
          <!-- Nozzle -->
          <circle cx="50" cy="8" r="3" fill="${m.dark}"/>
          <!-- Boya sıçraması -->
          <circle cx="75" cy="25" r="4" fill="${m.base}" opacity="0.4"/>
          <circle cx="80" cy="35" r="3" fill="${m.base}" opacity="0.3"/>
        `;

      case 'oil_drum':
        return `
          <!-- Mini varil -->
          <ellipse cx="50" cy="88" rx="28" ry="8" fill="${m.dark}"/>
          <rect x="22" y="18" width="56" height="70" rx="1" fill="url(#metalBody-${id})"/>
          <ellipse cx="50" cy="18" rx="28" ry="8" fill="url(#topCap-${id})"/>
          <!-- Varil çemberleri -->
          <rect x="22" y="30" width="56" height="4" fill="${m.dark}" opacity="0.4"/>
          <rect x="22" y="52" width="56" height="4" fill="${m.dark}" opacity="0.4"/>
          <rect x="22" y="74" width="56" height="4" fill="${m.dark}" opacity="0.4"/>
          <!-- Perçinler -->
          <circle cx="26" cy="32" r="2" fill="${m.light}"/>
          <circle cx="74" cy="32" r="2" fill="${m.light}"/>
          <circle cx="26" cy="76" r="2" fill="${m.light}"/>
          <circle cx="74" cy="76" r="2" fill="${m.light}"/>
        `;

      case 'sardine_tin':
        return `
          <!-- Yatay sardalya kutusu -->
          <rect x="15" y="35" width="70" height="40" rx="5" fill="url(#metalBody-${id})"/>
          <rect x="15" y="35" width="70" height="40" rx="5" fill="none" stroke="${m.dark}" stroke-width="2"/>
          <!-- Açma anahtarı -->
          <rect x="75" y="50" width="15" height="6" rx="1" fill="${m.light}"/>
          <circle cx="88" cy="53" r="4" fill="${m.base}" stroke="${m.dark}" stroke-width="1"/>
          <!-- Kavisli açılmış kısım efekti -->
          <path d="M 20 40 Q 50 38 80 40" stroke="${m.shine}" stroke-width="1" fill="none" opacity="0.6"/>
          <!-- Etiket alanı -->
          <rect x="22" y="42" width="50" height="26" rx="2" fill="${m.light}" opacity="0.1"/>
        `;

      case 'paint_bucket':
        return `
          <!-- Boya kovası -->
          <ellipse cx="50" cy="88" rx="28" ry="8" fill="${m.dark}"/>
          <path d="M 22 30 L 26 88 L 74 88 L 78 30 Z" fill="url(#metalBody-${id})"/>
          <ellipse cx="50" cy="30" rx="28" ry="10" fill="url(#topCap-${id})"/>
          <!-- Kulp -->
          <path d="M 30 25 Q 30 8 50 8 Q 70 8 70 25" stroke="${m.base}" stroke-width="4" fill="none"/>
          <path d="M 30 25 Q 30 10 50 10 Q 70 10 70 25" stroke="${m.light}" stroke-width="2" fill="none"/>
          <!-- Boya damlası -->
          <path d="M 22 35 Q 18 45 22 50 L 22 35" fill="${m.light}" opacity="0.6"/>
          <ellipse cx="20" cy="52" r="4" fill="${m.light}" opacity="0.5"/>
        `;

      case 'soup_can':
        return `
          <!-- Warhol çorba konservesi -->
          <ellipse cx="50" cy="86" rx="26" ry="8" fill="${m.dark}"/>
          <rect x="24" y="20" width="52" height="66" rx="2" fill="url(#metalBody-${id})"/>
          <ellipse cx="50" cy="20" rx="26" ry="8" fill="url(#topCap-${id})"/>
          <!-- Klasik çorba etiketi stili -->
          <rect x="24" y="28" width="52" height="25" fill="${m.shine}" opacity="0.2"/>
          <ellipse cx="50" cy="65" rx="18" ry="12" fill="${m.light}" opacity="0.15"/>
          <!-- Kenar detayı -->
          <line x1="24" y1="53" x2="76" y2="53" stroke="${m.dark}" stroke-width="2" opacity="0.3"/>
          <!-- Warhol imza yıldız -->
          <polygon points="50,58 52,64 58,64 53,68 55,74 50,70 45,74 47,68 42,64 48,64" fill="${m.dark}" opacity="0.2"/>
        `;

      case 'beer_belly':
        return `
          <!-- Tombul bira kutusu -->
          <ellipse cx="50" cy="86" rx="30" ry="9" fill="${m.dark}"/>
          <rect x="20" y="28" width="60" height="58" rx="4" fill="url(#metalBody-${id})"/>
          <ellipse cx="50" cy="28" rx="30" ry="9" fill="url(#topCap-${id})"/>
          <!-- Şişkin orta kısım efekti -->
          <ellipse cx="50" cy="57" rx="32" ry="20" fill="${m.light}" opacity="0.08"/>
          <!-- Açma halkası -->
          <ellipse cx="50" cy="24" rx="10" ry="3" fill="${m.light}" stroke="${m.dark}" stroke-width="1"/>
          <ellipse cx="50" cy="24" rx="6" ry="2" fill="${m.dark}" opacity="0.4"/>
          <!-- Köpük efekti -->
          <ellipse cx="42" cy="20" r="3" fill="white" opacity="0.4"/>
          <ellipse cx="55" cy="18" r="2" fill="white" opacity="0.3"/>
          <ellipse cx="60" cy="22" r="2" fill="white" opacity="0.25"/>
        `;

      case 'soda_pop':
        return `
          <!-- Retro gazoz şişesi tarzı kutu -->
          <ellipse cx="50" cy="90" rx="20" ry="5" fill="${m.dark}"/>
          <path d="M 30 90 L 32 40 Q 32 25 50 22 Q 68 25 68 40 L 70 90 Z" fill="url(#metalBody-${id})"/>
          <!-- Boyun kısmı -->
          <ellipse cx="50" cy="22" rx="12" ry="4" fill="url(#topCap-${id})"/>
          <rect x="44" y="10" width="12" height="12" rx="2" fill="${m.base}"/>
          <ellipse cx="50" cy="10" rx="6" ry="3" fill="${m.light}"/>
          <!-- Kapak -->
          <circle cx="50" cy="10" r="5" fill="${m.dark}" opacity="0.4"/>
          <!-- Retro dalga deseni -->
          <path d="M 34 50 Q 42 45 50 50 Q 58 55 66 50" stroke="${m.shine}" stroke-width="2" fill="none" opacity="0.3"/>
          <path d="M 33 65 Q 42 60 50 65 Q 58 70 67 65" stroke="${m.shine}" stroke-width="2" fill="none" opacity="0.3"/>
        `;

      default:
        return this.renderCharacter('classic_cola', m, id);
    }
  }

  private renderFace(expr: Expression, char: CharacterType): string {
    // Karakter tipine göre yüz pozisyonunu ayarla
    const pos = this.getFacePosition(char);
    const eyeY = pos.eyeY;
    const mouthY = pos.mouthY;
    const leftX = pos.leftEye;
    const rightX = pos.rightEye;
    const scale = pos.scale;

    let eyes = '';
    let mouth = '';
    let extras = '';

    // Göz çizimi
    switch (expr) {
      case 'grin':
        eyes = `
          <ellipse cx="${leftX}" cy="${eyeY}" rx="${4*scale}" ry="${5*scale}" fill="white"/>
          <ellipse cx="${rightX}" cy="${eyeY}" rx="${4*scale}" ry="${5*scale}" fill="white"/>
          <circle cx="${leftX+1}" cy="${eyeY}" r="${2.5*scale}" fill="#1a1a1a"/>
          <circle cx="${rightX+1}" cy="${eyeY}" r="${2.5*scale}" fill="#1a1a1a"/>
          <circle cx="${leftX+1.5}" cy="${eyeY-1}" r="${1*scale}" fill="white"/>
          <circle cx="${rightX+1.5}" cy="${eyeY-1}" r="${1*scale}" fill="white"/>
        `;
        mouth = `<path d="M ${leftX-2} ${mouthY} Q ${(leftX+rightX)/2} ${mouthY+8*scale} ${rightX+2} ${mouthY}" stroke="#1a1a1a" stroke-width="${2*scale}" fill="none" stroke-linecap="round"/>`;
        break;

      case 'meh':
        eyes = `
          <ellipse cx="${leftX}" cy="${eyeY}" rx="${4*scale}" ry="${3*scale}" fill="white"/>
          <ellipse cx="${rightX}" cy="${eyeY}" rx="${4*scale}" ry="${3*scale}" fill="white"/>
          <circle cx="${leftX}" cy="${eyeY}" r="${2*scale}" fill="#1a1a1a"/>
          <circle cx="${rightX}" cy="${eyeY}" r="${2*scale}" fill="#1a1a1a"/>
        `;
        mouth = `<line x1="${leftX}" y1="${mouthY+2}" x2="${rightX}" y2="${mouthY+2}" stroke="#1a1a1a" stroke-width="${2*scale}" stroke-linecap="round"/>`;
        break;

      case 'derp':
        eyes = `
          <circle cx="${leftX}" cy="${eyeY}" r="${5*scale}" fill="white"/>
          <circle cx="${rightX}" cy="${eyeY-2}" r="${4*scale}" fill="white"/>
          <circle cx="${leftX+2}" cy="${eyeY+1}" r="${3*scale}" fill="#1a1a1a"/>
          <circle cx="${rightX-1}" cy="${eyeY-1}" r="${2*scale}" fill="#1a1a1a"/>
          <circle cx="${leftX+3}" cy="${eyeY}" r="${1*scale}" fill="white"/>
        `;
        mouth = `<path d="M ${leftX} ${mouthY+3} Q ${(leftX+rightX)/2} ${mouthY-2} ${rightX} ${mouthY+5}" stroke="#1a1a1a" stroke-width="${2*scale}" fill="none" stroke-linecap="round"/>`;
        break;

      case 'angry':
        eyes = `
          <ellipse cx="${leftX}" cy="${eyeY}" rx="${4*scale}" ry="${4*scale}" fill="white"/>
          <ellipse cx="${rightX}" cy="${eyeY}" rx="${4*scale}" ry="${4*scale}" fill="white"/>
          <circle cx="${leftX}" cy="${eyeY+1}" r="${2.5*scale}" fill="#1a1a1a"/>
          <circle cx="${rightX}" cy="${eyeY+1}" r="${2.5*scale}" fill="#1a1a1a"/>
          <line x1="${leftX-5}" y1="${eyeY-5}" x2="${leftX+4}" y2="${eyeY-2}" stroke="#1a1a1a" stroke-width="${2*scale}" stroke-linecap="round"/>
          <line x1="${rightX+5}" y1="${eyeY-5}" x2="${rightX-4}" y2="${eyeY-2}" stroke="#1a1a1a" stroke-width="${2*scale}" stroke-linecap="round"/>
        `;
        mouth = `<path d="M ${leftX-2} ${mouthY+5} L ${(leftX+rightX)/2} ${mouthY} L ${rightX+2} ${mouthY+5}" stroke="#1a1a1a" stroke-width="${2.5*scale}" fill="none" stroke-linecap="round"/>`;
        break;

      case 'cool':
        eyes = `
          <rect x="${leftX-6}" y="${eyeY-3}" width="${12*scale}" height="${6*scale}" rx="2" fill="#1a1a1a"/>
          <rect x="${rightX-6}" y="${eyeY-3}" width="${12*scale}" height="${6*scale}" rx="2" fill="#1a1a1a"/>
          <line x1="${leftX+5}" y1="${eyeY}" x2="${rightX-5}" y2="${eyeY}" stroke="#1a1a1a" stroke-width="${2*scale}"/>
          <rect x="${leftX-5}" y="${eyeY-2}" width="${10*scale}" height="${4*scale}" rx="1" fill="#333" opacity="0.5"/>
          <rect x="${rightX-5}" y="${eyeY-2}" width="${10*scale}" height="${4*scale}" rx="1" fill="#333" opacity="0.5"/>
        `;
        mouth = `<path d="M ${leftX} ${mouthY+2} Q ${(leftX+rightX)/2} ${mouthY+6} ${rightX} ${mouthY+2}" stroke="#1a1a1a" stroke-width="${2*scale}" fill="none" stroke-linecap="round"/>`;
        break;

      case 'worried':
        eyes = `
          <ellipse cx="${leftX}" cy="${eyeY}" rx="${4*scale}" ry="${5*scale}" fill="white"/>
          <ellipse cx="${rightX}" cy="${eyeY}" rx="${4*scale}" ry="${5*scale}" fill="white"/>
          <circle cx="${leftX}" cy="${eyeY+1}" r="${2*scale}" fill="#1a1a1a"/>
          <circle cx="${rightX}" cy="${eyeY+1}" r="${2*scale}" fill="#1a1a1a"/>
          <path d="M ${leftX-4} ${eyeY-6} Q ${leftX} ${eyeY-4} ${leftX+4} ${eyeY-6}" stroke="#1a1a1a" stroke-width="${1.5*scale}" fill="none"/>
          <path d="M ${rightX-4} ${eyeY-6} Q ${rightX} ${eyeY-4} ${rightX+4} ${eyeY-6}" stroke="#1a1a1a" stroke-width="${1.5*scale}" fill="none"/>
        `;
        mouth = `<path d="M ${leftX} ${mouthY+4} Q ${(leftX+rightX)/2} ${mouthY-2} ${rightX} ${mouthY+4}" stroke="#1a1a1a" stroke-width="${2*scale}" fill="none" stroke-linecap="round"/>`;
        extras = `<ellipse cx="${rightX+8}" cy="${mouthY-5}" rx="${2*scale}" ry="${3*scale}" fill="#87CEEB" opacity="0.6"/>`;
        break;

      case 'sleepy':
        eyes = `
          <line x1="${leftX-4}" y1="${eyeY}" x2="${leftX+4}" y2="${eyeY}" stroke="#1a1a1a" stroke-width="${2.5*scale}" stroke-linecap="round"/>
          <line x1="${rightX-4}" y1="${eyeY}" x2="${rightX+4}" y2="${eyeY}" stroke="#1a1a1a" stroke-width="${2.5*scale}" stroke-linecap="round"/>
        `;
        mouth = `<ellipse cx="${(leftX+rightX)/2}" cy="${mouthY+3}" rx="${3*scale}" ry="${4*scale}" fill="#1a1a1a"/>`;
        extras = `
          <text x="${rightX+10}" y="${eyeY-8}" font-size="${8*scale}" fill="#1a1a1a" opacity="0.5">z</text>
          <text x="${rightX+16}" y="${eyeY-14}" font-size="${6*scale}" fill="#1a1a1a" opacity="0.3">z</text>
        `;
        break;

      case 'excited':
        eyes = `
          <polygon points="${leftX},${eyeY-6} ${leftX+5},${eyeY+4} ${leftX-5},${eyeY+4}" fill="#1a1a1a"/>
          <polygon points="${rightX},${eyeY-6} ${rightX+5},${eyeY+4} ${rightX-5},${eyeY+4}" fill="#1a1a1a"/>
          <circle cx="${leftX}" cy="${eyeY-2}" r="${1.5*scale}" fill="white"/>
          <circle cx="${rightX}" cy="${eyeY-2}" r="${1.5*scale}" fill="white"/>
        `;
        mouth = `
          <ellipse cx="${(leftX+rightX)/2}" cy="${mouthY+4}" rx="${8*scale}" ry="${6*scale}" fill="#1a1a1a"/>
          <ellipse cx="${(leftX+rightX)/2}" cy="${mouthY+2}" rx="${6*scale}" ry="${3*scale}" fill="#FF6B6B" opacity="0.6"/>
        `;
        extras = `
          <line x1="${leftX-10}" y1="${eyeY-10}" x2="${leftX-6}" y2="${eyeY-6}" stroke="#FFD700" stroke-width="2" opacity="0.6"/>
          <line x1="${rightX+10}" y1="${eyeY-10}" x2="${rightX+6}" y2="${eyeY-6}" stroke="#FFD700" stroke-width="2" opacity="0.6"/>
        `;
        break;

      default:
        return this.renderFace('grin', char);
    }

    return eyes + mouth + extras;
  }

  private getFacePosition(char: CharacterType): { eyeY: number; mouthY: number; leftEye: number; rightEye: number; scale: number } {
    switch (char) {
      case 'sardine_tin':
        return { eyeY: 50, mouthY: 58, leftEye: 38, rightEye: 58, scale: 0.8 };
      case 'crushed_rebel':
        return { eyeY: 48, mouthY: 62, leftEye: 40, rightEye: 60, scale: 0.9 };
      case 'energy_maniac':
        return { eyeY: 42, mouthY: 58, leftEye: 42, rightEye: 58, scale: 0.85 };
      case 'coffee_addict':
        return { eyeY: 48, mouthY: 62, leftEye: 40, rightEye: 56, scale: 0.9 };
      case 'spray_artist':
        return { eyeY: 52, mouthY: 66, leftEye: 42, rightEye: 58, scale: 0.85 };
      case 'soda_pop':
        return { eyeY: 48, mouthY: 65, leftEye: 42, rightEye: 58, scale: 0.85 };
      case 'beer_belly':
        return { eyeY: 48, mouthY: 62, leftEye: 38, rightEye: 62, scale: 1 };
      case 'oil_drum':
        return { eyeY: 45, mouthY: 62, leftEye: 38, rightEye: 62, scale: 1 };
      case 'vintage_tin':
      case 'paint_bucket':
        return { eyeY: 48, mouthY: 62, leftEye: 38, rightEye: 62, scale: 1 };
      case 'soup_can':
      case 'classic_cola':
      default:
        return { eyeY: 48, mouthY: 62, leftEye: 40, rightEye: 60, scale: 1 };
    }
  }

  private hashString(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return Math.abs(hash);
  }

  private randomItem<T>(arr: T[]): T {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  getCharacterOptions(): CharacterType[] { return [...this.characters]; }
  getExpressionOptions(): Expression[] { return [...this.expressions]; }
  getToneOptions(): MetalTone[] { return [...this.tones]; }
}
