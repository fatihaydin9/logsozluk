import { Injectable } from '@angular/core';
import {
  AvatarConfig,
  BodyShape,
  EyeType,
  MouthType,
  HeadAccessory,
  FaceDetail,
  AvatarColor,
  COLORS,
} from './avatar.types';

@Injectable({
  providedIn: 'root'
})
export class AvatarGeneratorService {

  // 14 × 12 × 10 × 16 × 13 × 12 = 4,193,280 combinations
  private readonly bodies: BodyShape[] = ['can', 'box', 'monitor', 'cat', 'bear', 'owl', 'frog', 'ghost', 'alien', 'blob', 'mushroom', 'egg', 'cloud', 'skull'];
  private readonly eyes: EyeType[] = ['normal', 'angry', 'sneaky', 'popping', 'spiral', 'dead', 'money', 'tired', 'one_big', 'laser', 'heart', 'glitch'];
  private readonly mouths: MouthType[] = ['flat', 'grin', 'sad', 'evil', 'shocked', 'tongue', 'smirk', 'zipper', 'vampire', 'glitch'];
  private readonly headAccs: HeadAccessory[] = ['none', 'antenna', 'bolt', 'crack', 'smoke', 'halo', 'devil', 'propeller', 'leaf', 'spark', 'crown', 'headphones', 'top_hat', 'flower', 'fire', 'bow'];
  private readonly faceDetails: FaceDetail[] = ['none', 'blush', 'scar', 'bandaid', 'freckles', 'tear', 'sweat', 'sticker', 'mask', 'glasses', 'whiskers', 'stitches', 'robo_visor'];
  private readonly colors: AvatarColor[] = ['red', 'blue', 'green', 'orange', 'purple', 'yellow', 'gray', 'pink', 'teal', 'black', 'lime', 'crimson'];

  generateFromSeed(seed: string): AvatarConfig {
    const hash = this.hashString(seed);
    return {
      body: this.bodies[hash % this.bodies.length],
      eyes: this.eyes[(hash >> 4) % this.eyes.length],
      mouth: this.mouths[(hash >> 8) % this.mouths.length],
      headAcc: this.headAccs[(hash >> 12) % this.headAccs.length],
      faceDetail: this.faceDetails[(hash >> 16) % this.faceDetails.length],
      color: this.colors[(hash >> 20) % this.colors.length],
      seed,
    };
  }

  generateRandom(): AvatarConfig {
    return {
      body: this.randomItem(this.bodies),
      eyes: this.randomItem(this.eyes),
      mouth: this.randomItem(this.mouths),
      headAcc: this.randomItem(this.headAccs),
      faceDetail: this.randomItem(this.faceDetails),
      color: this.randomItem(this.colors),
    };
  }

  generateSVG(config: AvatarConfig, size: number = 100): string {
    const c = COLORS[config.color];
    const stroke = '#1a1a1a';
    const sw = 3;

    return `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      ${this.renderHeadAcc(config.headAcc, c, stroke, sw, config.body)}
      ${this.renderBody(config.body, c, stroke, sw)}
      ${this.renderEyes(config.eyes, config.body, stroke)}
      ${this.renderMouth(config.mouth, config.body, stroke)}
      ${this.renderFaceDetail(config.faceDetail, config.body, stroke)}
    </svg>`;
  }

  private renderBody(body: BodyShape, c: any, stroke: string, sw: number): string {
    switch (body) {
      case 'can':
        // göçük yemiş, yamulmuş teneke kutu - bir tarafı ezik
        return `
          <path d="M 30 26 Q 28 26 26 30 L 24 74 Q 24 80 30 80 L 68 82 Q 76 82 76 76 L 74 30 Q 74 26 70 24 Z" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}" stroke-linejoin="round"/>
          <path d="M 26 30 Q 40 36 54 32 Q 68 28 74 30" stroke="${stroke}" stroke-width="2" fill="${c.dark}"/>
          <path d="M 24 74 Q 38 78 56 76 Q 70 74 76 76" stroke="${stroke}" stroke-width="2" fill="${c.dark}"/>
          <circle cx="36" cy="52" r="2" fill="${c.dark}"/>
          <circle cx="64" cy="48" r="1.5" fill="${c.dark}"/>
          <path d="M 58 56 Q 62 52 66 56" stroke="${c.dark}" stroke-width="1.5" fill="none"/>
        `;
      case 'box':
        // yamuk mukavva kutu - bant sarkmış, kapak açık
        return `
          <path d="M 24 38 L 28 78 L 74 76 L 72 34 Z" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}" stroke-linejoin="round"/>
          <path d="M 24 38 L 34 28 Q 50 24 68 30 L 72 34" stroke="${stroke}" stroke-width="2.5" fill="${c.dark}" stroke-linejoin="round"/>
          <path d="M 34 28 L 38 38" stroke="${stroke}" stroke-width="2"/>
          <rect x="42" y="32" width="16" height="6" rx="1" fill="#D4A574" stroke="${stroke}" stroke-width="1.5" transform="rotate(-3 50 35)"/>
          <line x1="42" y1="56" x2="56" y2="54" stroke="${stroke}" stroke-width="1" stroke-dasharray="3,3"/>
        `;
      case 'monitor':
        // çatlak CRT monitör - parazitli, yamuk stand
        return `
          <path d="M 22 26 Q 20 24 24 22 L 76 24 Q 80 24 78 28 L 76 66 Q 76 70 72 70 L 28 68 Q 24 68 22 64 Z" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <path d="M 26 28 L 74 30 L 72 64 L 26 62 Z" fill="#1a1a1a" stroke="${stroke}" stroke-width="2"/>
          <line x1="30" y1="42" x2="70" y2="43" stroke="#333" stroke-width="1" opacity="0.4"/>
          <line x1="28" y1="52" x2="72" y2="53" stroke="#333" stroke-width="1" opacity="0.3"/>
          <path d="M 56 66 L 60 74 L 64 74" stroke="${stroke}" stroke-width="2.5" fill="none" stroke-linecap="round"/>
          <path d="M 44 68 L 40 76 L 36 76" stroke="${stroke}" stroke-width="2.5" fill="none" stroke-linecap="round"/>
          <path d="M 34 76 L 66 76" stroke="${stroke}" stroke-width="3" stroke-linecap="round"/>
          <path d="M 62 34 L 66 42 L 60 48" stroke="#444" stroke-width="1.5" fill="none"/>
        `;
      case 'cat':
        // kocaman kafalı deli kedi - bir kulağı kırık, şişman yanak
        return `
          <path d="M 22 56 Q 18 40 26 34 Q 30 30 30 22 L 24 8 Q 40 20 42 28 Q 46 26 54 26 Q 56 20 60 8 L 78 22 Q 74 28 72 34 Q 80 42 78 58 Q 76 72 62 78 Q 50 82 38 78 Q 22 72 22 56 Z" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}" stroke-linejoin="round"/>
          <path d="M 24 8 Q 36 18 42 28" fill="${c.light}" stroke="none"/>
          <path d="M 26 12 Q 34 18 38 26" stroke="none" fill="${c.light}"/>
          <path d="M 60 8 L 78 22 Q 74 28 72 34" fill="${c.light}" stroke="none"/>
          <path d="M 64 14 Q 72 20 70 30" stroke="none" fill="${c.light}"/>
          <ellipse cx="50" cy="64" rx="12" ry="6" fill="${c.light}" opacity="0.5"/>
        `;
      case 'bear':
        // tombul kaçık ayı - dev yanak, küçük kulaklar, göbek lekesi
        return `
          <circle cx="50" cy="56" r="30" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <ellipse cx="28" cy="32" rx="12" ry="10" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}" transform="rotate(-15 28 32)"/>
          <ellipse cx="72" cy="30" rx="10" ry="12" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}" transform="rotate(20 72 30)"/>
          <ellipse cx="28" cy="32" rx="6" ry="5" fill="${c.light}" stroke="none" transform="rotate(-15 28 32)"/>
          <ellipse cx="72" cy="30" rx="5" ry="6" fill="${c.light}" stroke="none" transform="rotate(20 72 30)"/>
          <ellipse cx="50" cy="66" rx="16" ry="10" fill="${c.light}" opacity="0.4"/>
          <circle cx="42" cy="62" r="8" fill="${c.light}" opacity="0.2"/>
          <circle cx="60" cy="60" r="6" fill="${c.light}" opacity="0.2"/>
        `;
      case 'owl':
        // kafası devasa baykuş - gövdeden taşan göz yuvası, minik gaga, tüy detay
        return `
          <path d="M 26 52 Q 22 30 32 20 Q 42 12 50 14 Q 58 12 68 20 Q 78 30 74 52 Q 72 70 62 78 Q 50 84 38 78 Q 28 70 26 52 Z" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <circle cx="38" cy="40" r="14" fill="${c.light}" stroke="${stroke}" stroke-width="2"/>
          <circle cx="62" cy="40" r="14" fill="${c.light}" stroke="${stroke}" stroke-width="2"/>
          <path d="M 36 64 L 50 74 L 64 64" fill="${c.light}" stroke="none" opacity="0.4"/>
          <path d="M 32 20 Q 38 10 50 14" stroke="${c.dark}" stroke-width="2" fill="none"/>
          <path d="M 68 20 Q 62 10 50 14" stroke="${c.dark}" stroke-width="2" fill="none"/>
          <polygon points="50,50 46,56 54,56" fill="${c.dark}" stroke="${stroke}" stroke-width="1.5"/>
        `;
      case 'frog':
        // aşırı yassı, geniş sırıtkan kurbağa - patlak göz yuvaları
        return `
          <ellipse cx="50" cy="60" rx="32" ry="20" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <ellipse cx="32" cy="36" rx="14" ry="12" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <ellipse cx="68" cy="34" rx="12" ry="14" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <ellipse cx="32" cy="36" rx="10" ry="8" fill="${c.light}" stroke="none" opacity="0.3"/>
          <ellipse cx="68" cy="34" rx="8" ry="10" fill="${c.light}" stroke="none" opacity="0.3"/>
          <path d="M 22 58 Q 18 62 20 66" stroke="${c.dark}" stroke-width="2" fill="none" stroke-linecap="round"/>
          <path d="M 78 56 Q 82 60 80 64" stroke="${c.dark}" stroke-width="2" fill="none" stroke-linecap="round"/>
          <ellipse cx="50" cy="68" rx="8" ry="3" fill="${c.light}" opacity="0.3"/>
        `;
      case 'ghost':
        // eriyen hayalet - bir kolu uzanmış, damla damla akıyor
        return `
          <path d="M 28 50 Q 24 20 50 18 Q 78 20 74 50 L 76 58 Q 80 60 82 66 Q 80 72 76 68 L 74 76 Q 68 66 62 76 Q 56 66 50 78 Q 44 66 38 76 Q 32 68 26 78 Z" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}" stroke-linejoin="round"/>
          <path d="M 28 50 Q 24 52 18 50 Q 14 48 12 54 Q 14 60 20 58 Q 24 56 28 58" fill="${c.main}" stroke="${stroke}" stroke-width="2.5" stroke-linejoin="round"/>
          <ellipse cx="40" cy="22" rx="6" ry="3" fill="${c.light}" opacity="0.3"/>
          <circle cx="70" cy="74" r="3" fill="${c.light}" opacity="0.5"/>
          <circle cx="34" cy="80" r="2" fill="${c.light}" opacity="0.4"/>
        `;
      case 'alien':
        // kocaman beyin-kafa, minicik çene, ince boyun
        return `
          <path d="M 50 82 Q 42 82 40 72 L 38 62 Q 34 56 30 48 Q 22 34 28 22 Q 34 10 50 8 Q 66 10 72 22 Q 78 34 70 48 Q 66 56 62 62 L 60 72 Q 58 82 50 82 Z" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <ellipse cx="50" cy="26" rx="24" ry="18" fill="${c.light}" opacity="0.15"/>
          <path d="M 28 22 Q 24 16 20 18" stroke="${c.dark}" stroke-width="2" fill="none" stroke-linecap="round"/>
          <path d="M 72 22 Q 76 16 80 18" stroke="${c.dark}" stroke-width="2" fill="none" stroke-linecap="round"/>
          <ellipse cx="50" cy="74" rx="6" ry="2" fill="${c.dark}" opacity="0.3"/>
        `;
      case 'blob':
        // tamamen amorf, kabarcıklı, eriyen jöle
        return `
          <path d="M 34 76 Q 18 68 20 50 Q 16 38 26 28 Q 36 18 52 20 Q 70 16 78 32 Q 86 48 76 62 Q 82 72 72 80 Q 60 86 48 82 Q 38 84 34 76 Z" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <circle cx="32" cy="42" r="4" fill="${c.light}" opacity="0.5"/>
          <circle cx="66" cy="34" r="6" fill="${c.light}" opacity="0.3"/>
          <circle cx="56" cy="70" r="3" fill="${c.light}" opacity="0.4"/>
          <circle cx="40" cy="60" r="5" fill="${c.light}" opacity="0.2"/>
          <ellipse cx="70" cy="56" rx="4" ry="3" fill="${c.light}" opacity="0.35"/>
          <path d="M 46 82 Q 44 88 46 90" stroke="${c.main}" stroke-width="3" fill="none" stroke-linecap="round" opacity="0.6"/>
          <circle cx="46" cy="92" r="2" fill="${c.main}" opacity="0.4"/>
        `;
      case 'mushroom':
        // eğri büğrü mantar - yamuk şapka, puan puan, eğik sap
        return `
          <path d="M 14 54 Q 10 28 34 18 Q 50 12 70 20 Q 88 30 84 54 Z" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}" stroke-linejoin="round"/>
          <path d="M 38 54 Q 36 58 38 62 L 40 80 Q 42 84 50 84 Q 58 84 60 80 L 62 60 Q 64 56 60 54" fill="${c.light}" stroke="${stroke}" stroke-width="${sw}"/>
          <circle cx="32" cy="34" r="7" fill="${c.light}" opacity="0.5"/>
          <circle cx="56" cy="26" r="5" fill="${c.light}" opacity="0.5"/>
          <circle cx="72" cy="38" r="4" fill="${c.light}" opacity="0.5"/>
          <circle cx="44" cy="42" r="3" fill="${c.light}" opacity="0.4"/>
          <path d="M 40 80 Q 38 86 42 88" stroke="${c.dark}" stroke-width="1.5" fill="none" stroke-linecap="round"/>
        `;
      case 'egg':
        // çatlak yumurta - zigzag çatlak, parça düşmüş
        return `
          <ellipse cx="50" cy="52" rx="26" ry="34" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <path d="M 34 38 L 38 32 L 42 40 L 48 30 L 52 38 L 56 28 L 60 36 L 64 30 L 66 38" stroke="${c.dark}" stroke-width="2" fill="none" stroke-linejoin="round"/>
          <ellipse cx="50" cy="28" rx="18" ry="8" fill="${c.light}" opacity="0.2"/>
          <path d="M 70 44 Q 78 40 80 36 Q 82 32 78 30 Q 74 34 72 40" fill="${c.main}" stroke="${stroke}" stroke-width="2" stroke-linejoin="round"/>
        `;
      case 'cloud':
        // asimetrik kabarık bulut - bir tarafı şiş, alttan yağmur damlaları
        return `
          <circle cx="34" cy="48" r="20" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <circle cx="62" cy="44" r="22" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <circle cx="46" cy="34" r="18" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <circle cx="72" cy="54" r="14" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <path d="M 18 54 Q 18 70 30 70 L 74 68 Q 84 66 82 56" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <rect x="19" y="48" width="63" height="18" fill="${c.main}" stroke="none"/>
          <ellipse cx="46" cy="34" rx="12" ry="8" fill="${c.light}" opacity="0.25"/>
          <line x1="30" y1="74" x2="28" y2="82" stroke="${c.dark}" stroke-width="2" stroke-linecap="round" opacity="0.4"/>
          <line x1="44" y1="72" x2="42" y2="78" stroke="${c.dark}" stroke-width="2" stroke-linecap="round" opacity="0.3"/>
          <line x1="60" y1="72" x2="58" y2="80" stroke="${c.dark}" stroke-width="2" stroke-linecap="round" opacity="0.35"/>
        `;
      case 'skull':
        // çatlak, yamuk kafatası - eksik diş, bir göz yuvası büyük
        return `
          <path d="M 50 16 Q 22 16 20 44 Q 18 60 28 66 L 28 74 Q 28 82 36 82 L 64 82 Q 72 82 72 74 L 72 66 Q 82 60 80 44 Q 78 16 50 16 Z" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <line x1="38" y1="74" x2="38" y2="82" stroke="${stroke}" stroke-width="2"/>
          <line x1="48" y1="74" x2="48" y2="82" stroke="${stroke}" stroke-width="2"/>
          <line x1="58" y1="74" x2="58" y2="82" stroke="${stroke}" stroke-width="2"/>
          <path d="M 62 22 L 68 32 L 60 38" stroke="${c.dark}" stroke-width="2" fill="none" stroke-linecap="round"/>
          <path d="M 64 26 L 60 30" stroke="${c.dark}" stroke-width="1.5" fill="none"/>
          <rect x="52" y="74" width="8" height="8" fill="${c.dark}" opacity="0.3" rx="1"/>
        `;
      default:
        return this.renderBody('can', c, stroke, sw);
    }
  }

  private renderEyes(eyes: EyeType, body: BodyShape, stroke: string): string {
    const pos = this.getEyePos(body);
    const y = pos.y, lx = pos.lx, rx = pos.rx;

    switch (eyes) {
      case 'normal':
        return `
          <circle cx="${lx}" cy="${y}" r="7" fill="white" stroke="${stroke}" stroke-width="2.5"/>
          <circle cx="${rx}" cy="${y}" r="7" fill="white" stroke="${stroke}" stroke-width="2.5"/>
          <circle cx="${lx+1}" cy="${y+1}" r="4" fill="${stroke}"/>
          <circle cx="${rx+1}" cy="${y+1}" r="4" fill="${stroke}"/>
        `;
      case 'angry':
        return `
          <circle cx="${lx}" cy="${y}" r="7" fill="white" stroke="${stroke}" stroke-width="2.5"/>
          <circle cx="${rx}" cy="${y}" r="7" fill="white" stroke="${stroke}" stroke-width="2.5"/>
          <circle cx="${lx+1}" cy="${y+1}" r="4" fill="${stroke}"/>
          <circle cx="${rx+1}" cy="${y+1}" r="4" fill="${stroke}"/>
          <line x1="${lx-8}" y1="${y-9}" x2="${lx+6}" y2="${y-5}" stroke="${stroke}" stroke-width="3" stroke-linecap="round"/>
          <line x1="${rx+8}" y1="${y-9}" x2="${rx-6}" y2="${y-5}" stroke="${stroke}" stroke-width="3" stroke-linecap="round"/>
        `;
      case 'sneaky':
        return `
          <path d="M ${lx-8} ${y-2} Q ${lx} ${y-8} ${lx+8} ${y-2}" stroke="${stroke}" stroke-width="3" fill="none" stroke-linecap="round"/>
          <path d="M ${rx-8} ${y-2} Q ${rx} ${y-8} ${rx+8} ${y-2}" stroke="${stroke}" stroke-width="3" fill="none" stroke-linecap="round"/>
          <circle cx="${lx}" cy="${y-4}" r="2" fill="${stroke}"/>
          <circle cx="${rx}" cy="${y-4}" r="2" fill="${stroke}"/>
        `;
      case 'popping':
        return `
          <ellipse cx="${lx-2}" cy="${y}" rx="11" ry="13" fill="white" stroke="${stroke}" stroke-width="2.5"/>
          <ellipse cx="${rx+2}" cy="${y}" rx="11" ry="13" fill="white" stroke="${stroke}" stroke-width="2.5"/>
          <circle cx="${lx}" cy="${y+2}" r="6" fill="${stroke}"/>
          <circle cx="${rx}" cy="${y+2}" r="6" fill="${stroke}"/>
          <circle cx="${lx+2}" cy="${y}" r="2" fill="white"/>
          <circle cx="${rx+2}" cy="${y}" r="2" fill="white"/>
        `;
      case 'spiral':
        return `
          <circle cx="${lx}" cy="${y}" r="9" fill="white" stroke="${stroke}" stroke-width="2"/>
          <circle cx="${rx}" cy="${y}" r="9" fill="white" stroke="${stroke}" stroke-width="2"/>
          <path d="M ${lx} ${y-6} A 3 3 0 0 1 ${lx+3} ${y-3} A 3 3 0 0 1 ${lx} ${y} A 3 3 0 0 1 ${lx-3} ${y+3} A 3 3 0 0 1 ${lx} ${y+6}" stroke="${stroke}" stroke-width="2" fill="none"/>
          <path d="M ${rx} ${y-6} A 3 3 0 0 1 ${rx+3} ${y-3} A 3 3 0 0 1 ${rx} ${y} A 3 3 0 0 1 ${rx-3} ${y+3} A 3 3 0 0 1 ${rx} ${y+6}" stroke="${stroke}" stroke-width="2" fill="none"/>
        `;
      case 'dead':
        return `
          <line x1="${lx-6}" y1="${y-6}" x2="${lx+6}" y2="${y+6}" stroke="${stroke}" stroke-width="4" stroke-linecap="round"/>
          <line x1="${lx-6}" y1="${y+6}" x2="${lx+6}" y2="${y-6}" stroke="${stroke}" stroke-width="4" stroke-linecap="round"/>
          <line x1="${rx-6}" y1="${y-6}" x2="${rx+6}" y2="${y+6}" stroke="${stroke}" stroke-width="4" stroke-linecap="round"/>
          <line x1="${rx-6}" y1="${y+6}" x2="${rx+6}" y2="${y-6}" stroke="${stroke}" stroke-width="4" stroke-linecap="round"/>
        `;
      case 'money':
        return `
          <circle cx="${lx}" cy="${y}" r="9" fill="#27AE60" stroke="${stroke}" stroke-width="2"/>
          <circle cx="${rx}" cy="${y}" r="9" fill="#27AE60" stroke="${stroke}" stroke-width="2"/>
          <text x="${lx}" y="${y+4}" font-size="12" fill="white" text-anchor="middle" font-weight="bold">$</text>
          <text x="${rx}" y="${y+4}" font-size="12" fill="white" text-anchor="middle" font-weight="bold">$</text>
        `;
      case 'tired':
        return `
          <path d="M ${lx-7} ${y+2} Q ${lx} ${y-5} ${lx+7} ${y+2}" stroke="${stroke}" stroke-width="3" fill="none" stroke-linecap="round"/>
          <path d="M ${rx-7} ${y+2} Q ${rx} ${y-5} ${rx+7} ${y+2}" stroke="${stroke}" stroke-width="3" fill="none" stroke-linecap="round"/>
          <ellipse cx="${lx}" cy="${y+8}" rx="4" ry="2" fill="#AAAAAA"/>
          <ellipse cx="${rx}" cy="${y+8}" rx="4" ry="2" fill="#AAAAAA"/>
        `;
      case 'one_big':
        return `
          <circle cx="${lx-3}" cy="${y}" r="12" fill="white" stroke="${stroke}" stroke-width="2.5"/>
          <circle cx="${rx+3}" cy="${y+2}" r="5" fill="white" stroke="${stroke}" stroke-width="2"/>
          <circle cx="${lx-1}" cy="${y+2}" r="6" fill="${stroke}"/>
          <circle cx="${rx+3}" cy="${y+2}" r="3" fill="${stroke}"/>
        `;
      case 'laser':
        return `
          <rect x="${lx-9}" y="${y-5}" width="18" height="10" rx="2" fill="${stroke}"/>
          <rect x="${rx-9}" y="${y-5}" width="18" height="10" rx="2" fill="${stroke}"/>
          <rect x="${lx-6}" y="${y-2}" width="12" height="4" fill="#E74C3C"/>
          <rect x="${rx-6}" y="${y-2}" width="12" height="4" fill="#E74C3C"/>
        `;
      case 'heart':
        return `
          <path d="M ${lx} ${y+6} C ${lx-10} ${y-2} ${lx-10} ${y-10} ${lx} ${y-4} C ${lx+10} ${y-10} ${lx+10} ${y-2} ${lx} ${y+6}" fill="#E91E63" stroke="${stroke}" stroke-width="1.5"/>
          <path d="M ${rx} ${y+6} C ${rx-10} ${y-2} ${rx-10} ${y-10} ${rx} ${y-4} C ${rx+10} ${y-10} ${rx+10} ${y-2} ${rx} ${y+6}" fill="#E91E63" stroke="${stroke}" stroke-width="1.5"/>
        `;
      case 'glitch':
        return `
          <rect x="${lx-8}" y="${y-6}" width="16" height="12" fill="white" stroke="${stroke}" stroke-width="2"/>
          <rect x="${rx-8}" y="${y-6}" width="16" height="12" fill="white" stroke="${stroke}" stroke-width="2"/>
          <rect x="${lx-6}" y="${y-4}" width="5" height="8" fill="#00FF00"/>
          <rect x="${lx+1}" y="${y-2}" width="5" height="6" fill="#FF0000"/>
          <rect x="${rx-6}" y="${y-2}" width="5" height="6" fill="#0000FF"/>
          <rect x="${rx+1}" y="${y-4}" width="5" height="8" fill="#00FF00"/>
        `;
      default:
        return this.renderEyes('normal', body, stroke);
    }
  }

  private renderMouth(mouth: MouthType, body: BodyShape, stroke: string): string {
    const y = this.getMouthY(body);
    const cx = 50;

    switch (mouth) {
      case 'flat':
        return `<line x1="${cx-12}" y1="${y}" x2="${cx+12}" y2="${y}" stroke="${stroke}" stroke-width="3" stroke-linecap="round"/>`;
      case 'grin':
        return `
          <path d="M ${cx-14} ${y-4} Q ${cx} ${y+14} ${cx+14} ${y-4}" stroke="${stroke}" stroke-width="3" fill="white"/>
          <line x1="${cx-10}" y1="${y+2}" x2="${cx+10}" y2="${y+2}" stroke="${stroke}" stroke-width="1.5"/>
        `;
      case 'sad':
        return `<path d="M ${cx-12} ${y+6} Q ${cx} ${y-8} ${cx+12} ${y+6}" stroke="${stroke}" stroke-width="3" fill="none" stroke-linecap="round"/>`;
      case 'evil':
        return `<path d="M ${cx-14} ${y} Q ${cx-7} ${y+8} ${cx} ${y} Q ${cx+7} ${y+8} ${cx+14} ${y}" stroke="${stroke}" stroke-width="3" fill="none" stroke-linecap="round"/>`;
      case 'shocked':
        return `
          <ellipse cx="${cx}" cy="${y+3}" rx="10" ry="12" fill="${stroke}"/>
          <ellipse cx="${cx}" cy="${y+1}" rx="6" ry="7" fill="#C0392B"/>
        `;
      case 'tongue':
        return `
          <path d="M ${cx-12} ${y-2} Q ${cx} ${y+8} ${cx+12} ${y-2}" stroke="${stroke}" stroke-width="3" fill="none"/>
          <ellipse cx="${cx}" cy="${y+8}" rx="6" ry="8" fill="#E91E63" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'smirk':
        return `<path d="M ${cx-8} ${y+2} Q ${cx+4} ${y+2} ${cx+12} ${y-6}" stroke="${stroke}" stroke-width="3" fill="none" stroke-linecap="round"/>`;
      case 'zipper':
        return `
          <rect x="${cx-14}" y="${y-3}" width="28" height="10" fill="#71797E" stroke="${stroke}" stroke-width="2"/>
          <line x1="${cx-10}" y1="${y-3}" x2="${cx-10}" y2="${y+7}" stroke="${stroke}" stroke-width="2"/>
          <line x1="${cx-4}" y1="${y-3}" x2="${cx-4}" y2="${y+7}" stroke="${stroke}" stroke-width="2"/>
          <line x1="${cx+2}" y1="${y-3}" x2="${cx+2}" y2="${y+7}" stroke="${stroke}" stroke-width="2"/>
          <line x1="${cx+8}" y1="${y-3}" x2="${cx+8}" y2="${y+7}" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'vampire':
        return `
          <path d="M ${cx-12} ${y} Q ${cx} ${y+6} ${cx+12} ${y}" stroke="${stroke}" stroke-width="2.5" fill="none"/>
          <polygon points="${cx-5},${y+1} ${cx-3},${y+10} ${cx-1},${y+1}" fill="white" stroke="${stroke}" stroke-width="1"/>
          <polygon points="${cx+1},${y+1} ${cx+3},${y+10} ${cx+5},${y+1}" fill="white" stroke="${stroke}" stroke-width="1"/>
        `;
      case 'glitch':
        return `
          <rect x="${cx-12}" y="${y-2}" width="24" height="8" fill="${stroke}"/>
          <rect x="${cx-10}" y="${y}" width="6" height="4" fill="#00FF00"/>
          <rect x="${cx-2}" y="${y-1}" width="6" height="4" fill="#FF0000"/>
          <rect x="${cx+6}" y="${y}" width="6" height="4" fill="#0000FF"/>
        `;
      default:
        return this.renderMouth('flat', body, stroke);
    }
  }

  private readonly topYMap: Record<BodyShape, number> = {
    can: 26, box: 28, monitor: 22,
    cat: 8, bear: 26, owl: 14, frog: 34,
    ghost: 18, alien: 8, blob: 20, mushroom: 12,
    egg: 18, cloud: 20, skull: 16,
  };

  private renderHeadAcc(acc: HeadAccessory, c: any, stroke: string, sw: number, body: BodyShape): string {
    const topY = this.topYMap[body] ?? 28;

    switch (acc) {
      case 'antenna':
        return `
          <line x1="50" y1="${topY}" x2="50" y2="${topY-16}" stroke="${stroke}" stroke-width="${sw}"/>
          <circle cx="50" cy="${topY-18}" r="5" fill="#E74C3C" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'bolt':
        return `
          <circle cx="72" cy="45" r="6" fill="#F1C40F" stroke="${stroke}" stroke-width="2"/>
          <line x1="69" y1="45" x2="75" y2="45" stroke="${stroke}" stroke-width="2"/>
          <line x1="72" y1="42" x2="72" y2="48" stroke="${stroke}" stroke-width="2"/>
          <circle cx="28" cy="45" r="6" fill="#F1C40F" stroke="${stroke}" stroke-width="2"/>
          <line x1="25" y1="45" x2="31" y2="45" stroke="${stroke}" stroke-width="2"/>
          <line x1="28" y1="42" x2="28" y2="48" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'crack':
        return `<path d="M 62 ${topY} L 68 ${topY+12} L 58 ${topY+18} L 66 ${topY+28}" stroke="${stroke}" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
      case 'smoke':
        return `
          <ellipse cx="68" cy="${topY-8}" rx="6" ry="4" fill="#95A5A6" opacity="0.7"/>
          <ellipse cx="72" cy="${topY-16}" rx="5" ry="3" fill="#BDC3C7" opacity="0.6"/>
          <ellipse cx="66" cy="${topY-22}" rx="4" ry="3" fill="#D5DBDB" opacity="0.5"/>
        `;
      case 'halo':
        return `<ellipse cx="50" cy="${topY-10}" rx="18" ry="5" fill="none" stroke="#F1C40F" stroke-width="4"/>`;
      case 'devil':
        return `
          <path d="M 30 ${topY+8} Q 24 ${topY-8} 22 ${topY-18}" stroke="#C0392B" stroke-width="5" fill="none" stroke-linecap="round"/>
          <path d="M 70 ${topY+8} Q 76 ${topY-8} 78 ${topY-18}" stroke="#C0392B" stroke-width="5" fill="none" stroke-linecap="round"/>
        `;
      case 'propeller':
        return `
          <line x1="50" y1="${topY}" x2="50" y2="${topY-10}" stroke="${stroke}" stroke-width="${sw}"/>
          <ellipse cx="50" cy="${topY-12}" rx="14" ry="4" fill="#95A5A6" stroke="${stroke}" stroke-width="2"/>
          <ellipse cx="50" cy="${topY-12}" rx="14" ry="4" fill="#71797E" stroke="${stroke}" stroke-width="2" transform="rotate(60 50 ${topY-12})"/>
          <circle cx="50" cy="${topY-12}" r="3" fill="${stroke}"/>
        `;
      case 'leaf':
        return `
          <path d="M 50 ${topY-2} Q 42 ${topY-14} 50 ${topY-20} Q 58 ${topY-14} 50 ${topY-2}" fill="#27AE60" stroke="${stroke}" stroke-width="2"/>
          <line x1="50" y1="${topY-2}" x2="50" y2="${topY-16}" stroke="${stroke}" stroke-width="1.5"/>
        `;
      case 'spark':
        return `
          <polygon points="50,${topY-20} 53,${topY-10} 62,${topY-10} 55,${topY-4} 58,${topY+6} 50,${topY} 42,${topY+6} 45,${topY-4} 38,${topY-10} 47,${topY-10}" fill="#F1C40F" stroke="${stroke}" stroke-width="1.5"/>
        `;
      case 'crown':
        return `
          <polygon points="34,${topY} 38,${topY-14} 44,${topY-6} 50,${topY-16} 56,${topY-6} 62,${topY-14} 66,${topY}" fill="#F1C40F" stroke="${stroke}" stroke-width="2"/>
          <rect x="34" y="${topY-2}" width="32" height="4" fill="#F1C40F" stroke="${stroke}" stroke-width="1.5"/>
        `;
      case 'headphones':
        return `
          <path d="M 28 ${topY+10} Q 28 ${topY-10} 50 ${topY-12} Q 72 ${topY-10} 72 ${topY+10}" stroke="${stroke}" stroke-width="4" fill="none" stroke-linecap="round"/>
          <rect x="22" y="${topY+6}" width="10" height="14" rx="4" fill="#555" stroke="${stroke}" stroke-width="2"/>
          <rect x="68" y="${topY+6}" width="10" height="14" rx="4" fill="#555" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'top_hat':
        return `
          <rect x="38" y="${topY-24}" width="24" height="22" rx="2" fill="#2C3E50" stroke="${stroke}" stroke-width="2"/>
          <rect x="30" y="${topY-4}" width="40" height="6" rx="2" fill="#2C3E50" stroke="${stroke}" stroke-width="2"/>
          <rect x="38" y="${topY-18}" width="24" height="4" fill="#8B4513" stroke="none"/>
        `;
      case 'flower':
        return `
          <circle cx="44" cy="${topY-10}" r="5" fill="#FF69B4" stroke="${stroke}" stroke-width="1.5"/>
          <circle cx="56" cy="${topY-10}" r="5" fill="#FF69B4" stroke="${stroke}" stroke-width="1.5"/>
          <circle cx="48" cy="${topY-16}" r="5" fill="#FF69B4" stroke="${stroke}" stroke-width="1.5"/>
          <circle cx="52" cy="${topY-4}" r="5" fill="#FF69B4" stroke="${stroke}" stroke-width="1.5"/>
          <circle cx="50" cy="${topY-10}" r="4" fill="#F1C40F" stroke="${stroke}" stroke-width="1"/>
          <line x1="50" y1="${topY-4}" x2="50" y2="${topY+2}" stroke="#27AE60" stroke-width="2"/>
        `;
      case 'fire':
        return `
          <path d="M 50 ${topY+4} Q 40 ${topY-6} 44 ${topY-16} Q 46 ${topY-10} 50 ${topY-24} Q 54 ${topY-10} 56 ${topY-16} Q 60 ${topY-6} 50 ${topY+4} Z" fill="#E67E22" stroke="${stroke}" stroke-width="1.5"/>
          <path d="M 50 ${topY+2} Q 44 ${topY-4} 46 ${topY-10} Q 48 ${topY-6} 50 ${topY-16} Q 52 ${topY-6} 54 ${topY-10} Q 56 ${topY-4} 50 ${topY+2} Z" fill="#F1C40F" stroke="none"/>
        `;
      case 'bow':
        return `
          <ellipse cx="42" cy="${topY-6}" rx="8" ry="6" fill="#E91E63" stroke="${stroke}" stroke-width="2"/>
          <ellipse cx="58" cy="${topY-6}" rx="8" ry="6" fill="#E91E63" stroke="${stroke}" stroke-width="2"/>
          <circle cx="50" cy="${topY-4}" r="4" fill="#C2185B" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'none':
      default:
        return '';
    }
  }

  private renderFaceDetail(detail: FaceDetail, body: BodyShape, stroke: string): string {
    const eyeY = this.getEyePos(body).y;
    const mouthY = this.getMouthY(body);

    switch (detail) {
      case 'blush':
        return `
          <ellipse cx="32" cy="${eyeY+10}" rx="5" ry="3" fill="#FADBD8"/>
          <ellipse cx="68" cy="${eyeY+10}" rx="5" ry="3" fill="#FADBD8"/>
        `;
      case 'scar':
        return `
          <line x1="64" y1="${eyeY-8}" x2="70" y2="${eyeY+6}" stroke="${stroke}" stroke-width="2"/>
          <line x1="62" y1="${eyeY-4}" x2="68" y2="${eyeY-2}" stroke="${stroke}" stroke-width="1.5"/>
          <line x1="66" y1="${eyeY+2}" x2="72" y2="${eyeY+4}" stroke="${stroke}" stroke-width="1.5"/>
        `;
      case 'bandaid':
        return `<rect x="62" y="${eyeY}" width="14" height="7" rx="1" fill="#F5CBA7" stroke="${stroke}" stroke-width="1.5" transform="rotate(-15 69 ${eyeY+3})"/>`;
      case 'freckles':
        return `
          <circle cx="34" cy="${eyeY+8}" r="1.5" fill="#A0522D"/>
          <circle cx="38" cy="${eyeY+11}" r="1.5" fill="#A0522D"/>
          <circle cx="32" cy="${eyeY+13}" r="1.5" fill="#A0522D"/>
          <circle cx="66" cy="${eyeY+8}" r="1.5" fill="#A0522D"/>
          <circle cx="62" cy="${eyeY+11}" r="1.5" fill="#A0522D"/>
          <circle cx="68" cy="${eyeY+13}" r="1.5" fill="#A0522D"/>
        `;
      case 'tear':
        return `<ellipse cx="32" cy="${eyeY+12}" rx="3" ry="6" fill="#85C1E9" stroke="${stroke}" stroke-width="1"/>`;
      case 'sweat':
        return `<ellipse cx="70" cy="${eyeY-3}" rx="4" ry="6" fill="#85C1E9" stroke="${stroke}" stroke-width="1"/>`;
      case 'sticker':
        return `
          <circle cx="68" cy="${mouthY-2}" r="6" fill="#F1C40F" stroke="${stroke}" stroke-width="1.5"/>
          <text x="68" y="${mouthY+1}" font-size="8" fill="${stroke}" text-anchor="middle">:)</text>
        `;
      case 'mask':
        return `
          <rect x="30" y="${eyeY-10}" width="40" height="16" rx="3" fill="#1a1a1a" stroke="${stroke}" stroke-width="2"/>
          <ellipse cx="40" cy="${eyeY-2}" rx="6" ry="5" fill="white"/>
          <ellipse cx="60" cy="${eyeY-2}" rx="6" ry="5" fill="white"/>
        `;
      case 'glasses':
        return `
          <circle cx="38" cy="${eyeY}" r="10" fill="none" stroke="${stroke}" stroke-width="2.5"/>
          <circle cx="62" cy="${eyeY}" r="10" fill="none" stroke="${stroke}" stroke-width="2.5"/>
          <line x1="48" y1="${eyeY}" x2="52" y2="${eyeY}" stroke="${stroke}" stroke-width="2.5"/>
          <line x1="28" y1="${eyeY}" x2="24" y2="${eyeY-4}" stroke="${stroke}" stroke-width="2"/>
          <line x1="72" y1="${eyeY}" x2="76" y2="${eyeY-4}" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'whiskers':
        return `
          <line x1="18" y1="${eyeY+6}" x2="34" y2="${eyeY+8}" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="18" y1="${eyeY+11}" x2="34" y2="${eyeY+11}" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="18" y1="${eyeY+16}" x2="34" y2="${eyeY+14}" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="82" y1="${eyeY+6}" x2="66" y2="${eyeY+8}" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="82" y1="${eyeY+11}" x2="66" y2="${eyeY+11}" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="82" y1="${eyeY+16}" x2="66" y2="${eyeY+14}" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round"/>
        `;
      case 'stitches':
        return `
          <line x1="50" y1="${eyeY-12}" x2="50" y2="${mouthY+8}" stroke="${stroke}" stroke-width="2" stroke-dasharray="4,3"/>
          <line x1="46" y1="${eyeY-6}" x2="54" y2="${eyeY-6}" stroke="${stroke}" stroke-width="1.5"/>
          <line x1="46" y1="${eyeY+4}" x2="54" y2="${eyeY+4}" stroke="${stroke}" stroke-width="1.5"/>
          <line x1="46" y1="${mouthY}" x2="54" y2="${mouthY}" stroke="${stroke}" stroke-width="1.5"/>
        `;
      case 'robo_visor':
        return `
          <rect x="28" y="${eyeY-3}" width="44" height="8" rx="3" fill="#E74C3C" opacity="0.7" stroke="${stroke}" stroke-width="1.5"/>
          <rect x="32" y="${eyeY-1}" width="36" height="4" rx="2" fill="#FF6B6B" opacity="0.5"/>
        `;
      case 'none':
      default:
        return '';
    }
  }

  private getEyePos(body: BodyShape): { y: number; lx: number; rx: number } {
    const map: Record<BodyShape, { y: number; lx: number; rx: number }> = {
      can:      { y: 48, lx: 38, rx: 60 },
      box:      { y: 52, lx: 38, rx: 60 },
      monitor:  { y: 44, lx: 40, rx: 60 },
      cat:      { y: 46, lx: 36, rx: 60 },
      bear:     { y: 50, lx: 36, rx: 62 },
      owl:      { y: 40, lx: 38, rx: 62 },
      frog:     { y: 36, lx: 32, rx: 68 },
      ghost:    { y: 40, lx: 38, rx: 62 },
      alien:    { y: 36, lx: 38, rx: 62 },
      blob:     { y: 44, lx: 38, rx: 64 },
      mushroom: { y: 38, lx: 38, rx: 62 },
      egg:      { y: 46, lx: 40, rx: 60 },
      cloud:    { y: 46, lx: 36, rx: 60 },
      skull:    { y: 40, lx: 36, rx: 62 },
    };
    return map[body] ?? { y: 48, lx: 38, rx: 62 };
  }

  private getMouthY(body: BodyShape): number {
    const map: Record<BodyShape, number> = {
      can: 62, box: 64, monitor: 56,
      cat: 60, bear: 64, owl: 62, frog: 62,
      ghost: 54, alien: 56, blob: 58, mushroom: 48,
      egg: 62, cloud: 58, skull: 58,
    };
    return map[body] ?? 62;
  }

  private hashString(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash) + str.charCodeAt(i);
      hash = hash & hash;
    }
    return Math.abs(hash);
  }

  private randomItem<T>(arr: T[]): T {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  getBodyOptions(): BodyShape[] { return [...this.bodies]; }
  getEyeOptions(): EyeType[] { return [...this.eyes]; }
  getMouthOptions(): MouthType[] { return [...this.mouths]; }
  getHeadAccOptions(): HeadAccessory[] { return [...this.headAccs]; }
  getFaceDetailOptions(): FaceDetail[] { return [...this.faceDetails]; }
  getColorOptions(): AvatarColor[] { return [...this.colors]; }
}
