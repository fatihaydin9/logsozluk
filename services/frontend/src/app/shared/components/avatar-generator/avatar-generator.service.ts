import { Injectable } from '@angular/core';
import {
  AvatarConfig,
  BodyShape,
  EyeType,
  MouthType,
  HeadAccessory,
  FaceDetail,
  BodyDetail,
  AvatarColor,
  COLORS,
  DEFAULT_AVATAR,
} from './avatar.types';

@Injectable({
  providedIn: 'root'
})
export class AvatarGeneratorService {

  private readonly bodies: BodyShape[] = ['can', 'box', 'round', 'tall', 'crushed', 'tv', 'capsule', 'triangle'];
  private readonly eyes: EyeType[] = ['dots', 'big', 'uneven', 'visor', 'x_eyes', 'cyclops', 'sleepy', 'crazy', 'hearts', 'screens'];
  private readonly mouths: MouthType[] = ['line', 'smile', 'open', 'teeth', 'zigzag', 'ooo', 'vampire', 'braces'];
  private readonly headAccs: HeadAccessory[] = ['none', 'antenna', 'spring', 'propeller', 'mohawk', 'cap', 'headphones', 'horns'];
  private readonly faceDetails: FaceDetail[] = ['none', 'blush', 'scar', 'bandaid', 'freckles', 'mustache', 'tears', 'sweat'];
  private readonly bodyDetails: BodyDetail[] = ['none', 'rust', 'dent', 'bolt', 'patch', 'crack', 'sticker', 'gauge'];
  private readonly colors: AvatarColor[] = ['red', 'blue', 'green', 'orange', 'purple', 'yellow', 'gray', 'pink', 'teal', 'black'];

  generateFromSeed(seed: string): AvatarConfig {
    const hash = this.hashString(seed);
    return {
      body: this.bodies[hash % this.bodies.length],
      eyes: this.eyes[(hash >> 3) % this.eyes.length],
      mouth: this.mouths[(hash >> 6) % this.mouths.length],
      headAcc: this.headAccs[(hash >> 9) % this.headAccs.length],
      faceDetail: this.faceDetails[(hash >> 12) % this.faceDetails.length],
      bodyDetail: this.bodyDetails[(hash >> 15) % this.bodyDetails.length],
      color: this.colors[(hash >> 18) % this.colors.length],
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
      bodyDetail: this.randomItem(this.bodyDetails),
      color: this.randomItem(this.colors),
    };
  }

  generateSVG(config: AvatarConfig, size: number = 100): string {
    const c = COLORS[config.color];
    const stroke = '#2D2D2D';
    const sw = 3; // stroke width

    return `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      ${this.renderHeadAcc(config.headAcc, c, stroke, sw)}
      ${this.renderBody(config.body, c, stroke, sw)}
      ${this.renderBodyDetail(config.bodyDetail, config.body, c, stroke)}
      ${this.renderEyes(config.eyes, config.body, stroke)}
      ${this.renderMouth(config.mouth, config.body, stroke)}
      ${this.renderFaceDetail(config.faceDetail, config.body, stroke)}
    </svg>`;
  }

  private renderBody(body: BodyShape, c: any, stroke: string, sw: number): string {
    switch (body) {
      case 'can':
        return `
          <rect x="26" y="25" width="48" height="55" rx="4" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <line x1="26" y1="35" x2="74" y2="35" stroke="${stroke}" stroke-width="2"/>
          <line x1="26" y1="70" x2="74" y2="70" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'box':
        return `
          <rect x="24" y="28" width="52" height="48" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <line x1="24" y1="38" x2="76" y2="38" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'round':
        return `<circle cx="50" cy="53" r="30" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>`;
      case 'tall':
        return `
          <rect x="32" y="15" width="36" height="72" rx="4" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <line x1="32" y1="25" x2="68" y2="25" stroke="${stroke}" stroke-width="2"/>
          <line x1="32" y1="77" x2="68" y2="77" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'crushed':
        return `<path d="M 30 80 Q 40 88 50 85 Q 60 88 70 80 L 73 42 Q 65 36 50 40 Q 35 36 27 42 Z" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>`;
      case 'tv':
        return `
          <rect x="22" y="30" width="56" height="44" rx="4" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <rect x="28" y="36" width="44" height="32" rx="2" fill="#1a1a1a" stroke="${stroke}" stroke-width="2"/>
          <rect x="32" y="74" width="10" height="10" fill="${c.main}" stroke="${stroke}" stroke-width="2"/>
          <rect x="58" y="74" width="10" height="10" fill="${c.main}" stroke="${stroke}" stroke-width="2"/>
          <line x1="38" y1="30" x2="30" y2="18" stroke="${stroke}" stroke-width="${sw}"/>
          <line x1="62" y1="30" x2="70" y2="18" stroke="${stroke}" stroke-width="${sw}"/>
          <circle cx="30" cy="16" r="3" fill="${c.main}" stroke="${stroke}" stroke-width="2"/>
          <circle cx="70" cy="16" r="3" fill="${c.main}" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'capsule':
        return `<rect x="32" y="28" width="36" height="52" rx="18" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>`;
      case 'triangle':
        return `<polygon points="50,18 80,78 20,78" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}" stroke-linejoin="round"/>`;
      default:
        return this.renderBody('can', c, stroke, sw);
    }
  }

  private renderEyes(eyes: EyeType, body: BodyShape, stroke: string): string {
    const pos = this.getEyePos(body);
    const y = pos.y, lx = pos.lx, rx = pos.rx;

    switch (eyes) {
      case 'dots':
        return `
          <circle cx="${lx}" cy="${y}" r="6" fill="white" stroke="${stroke}" stroke-width="2"/>
          <circle cx="${rx}" cy="${y}" r="6" fill="white" stroke="${stroke}" stroke-width="2"/>
          <circle cx="${lx+1}" cy="${y}" r="3" fill="${stroke}"/>
          <circle cx="${rx+1}" cy="${y}" r="3" fill="${stroke}"/>
        `;
      case 'big':
        return `
          <circle cx="${lx}" cy="${y}" r="10" fill="white" stroke="${stroke}" stroke-width="2.5"/>
          <circle cx="${rx}" cy="${y}" r="10" fill="white" stroke="${stroke}" stroke-width="2.5"/>
          <circle cx="${lx+2}" cy="${y}" r="5" fill="${stroke}"/>
          <circle cx="${rx+2}" cy="${y}" r="5" fill="${stroke}"/>
          <circle cx="${lx+3}" cy="${y-2}" r="2" fill="white"/>
          <circle cx="${rx+3}" cy="${y-2}" r="2" fill="white"/>
        `;
      case 'uneven':
        return `
          <circle cx="${lx-2}" cy="${y-3}" r="9" fill="white" stroke="${stroke}" stroke-width="2.5"/>
          <circle cx="${rx+2}" cy="${y+2}" r="5" fill="white" stroke="${stroke}" stroke-width="2"/>
          <circle cx="${lx-1}" cy="${y-2}" r="4" fill="${stroke}"/>
          <circle cx="${rx+2}" cy="${y+2}" r="2.5" fill="${stroke}"/>
        `;
      case 'visor':
        return `
          <rect x="${lx-14}" y="${y-7}" width="${rx-lx+28}" height="14" rx="7" fill="${stroke}"/>
          <rect x="${lx-11}" y="${y-4}" width="${rx-lx+22}" height="8" rx="4" fill="#5DADE2"/>
        `;
      case 'x_eyes':
        return `
          <line x1="${lx-5}" y1="${y-5}" x2="${lx+5}" y2="${y+5}" stroke="${stroke}" stroke-width="4" stroke-linecap="round"/>
          <line x1="${lx-5}" y1="${y+5}" x2="${lx+5}" y2="${y-5}" stroke="${stroke}" stroke-width="4" stroke-linecap="round"/>
          <line x1="${rx-5}" y1="${y-5}" x2="${rx+5}" y2="${y+5}" stroke="${stroke}" stroke-width="4" stroke-linecap="round"/>
          <line x1="${rx-5}" y1="${y+5}" x2="${rx+5}" y2="${y-5}" stroke="${stroke}" stroke-width="4" stroke-linecap="round"/>
        `;
      case 'cyclops':
        return `
          <circle cx="50" cy="${y}" r="12" fill="white" stroke="${stroke}" stroke-width="3"/>
          <circle cx="52" cy="${y}" r="6" fill="${stroke}"/>
          <circle cx="54" cy="${y-2}" r="2.5" fill="white"/>
        `;
      case 'sleepy':
        return `
          <path d="M ${lx-7} ${y} Q ${lx} ${y-6} ${lx+7} ${y}" stroke="${stroke}" stroke-width="3" fill="none" stroke-linecap="round"/>
          <path d="M ${rx-7} ${y} Q ${rx} ${y-6} ${rx+7} ${y}" stroke="${stroke}" stroke-width="3" fill="none" stroke-linecap="round"/>
        `;
      case 'crazy':
        return `
          <circle cx="${lx}" cy="${y}" r="8" fill="white" stroke="${stroke}" stroke-width="2"/>
          <circle cx="${rx}" cy="${y}" r="8" fill="white" stroke="${stroke}" stroke-width="2"/>
          <circle cx="${lx-2}" cy="${y+2}" r="4" fill="${stroke}"/>
          <circle cx="${rx+3}" cy="${y-2}" r="4" fill="${stroke}"/>
        `;
      case 'hearts':
        return `
          <path d="M ${lx} ${y+5} C ${lx-9} ${y-2} ${lx-9} ${y-9} ${lx} ${y-3} C ${lx+9} ${y-9} ${lx+9} ${y-2} ${lx} ${y+5}" fill="#E91E63" stroke="${stroke}" stroke-width="1.5"/>
          <path d="M ${rx} ${y+5} C ${rx-9} ${y-2} ${rx-9} ${y-9} ${rx} ${y-3} C ${rx+9} ${y-9} ${rx+9} ${y-2} ${rx} ${y+5}" fill="#E91E63" stroke="${stroke}" stroke-width="1.5"/>
        `;
      case 'screens':
        return `
          <rect x="${lx-7}" y="${y-5}" width="14" height="10" rx="2" fill="${stroke}"/>
          <rect x="${lx-5}" y="${y-3}" width="10" height="6" fill="#00FF41"/>
          <rect x="${rx-7}" y="${y-5}" width="14" height="10" rx="2" fill="${stroke}"/>
          <rect x="${rx-5}" y="${y-3}" width="10" height="6" fill="#00FF41"/>
        `;
      default:
        return this.renderEyes('dots', body, stroke);
    }
  }

  private renderMouth(mouth: MouthType, body: BodyShape, stroke: string): string {
    const y = this.getMouthY(body);
    const cx = 50;

    switch (mouth) {
      case 'line':
        return `<line x1="${cx-10}" y1="${y}" x2="${cx+10}" y2="${y}" stroke="${stroke}" stroke-width="3" stroke-linecap="round"/>`;
      case 'smile':
        return `<path d="M ${cx-11} ${y-2} Q ${cx} ${y+10} ${cx+11} ${y-2}" stroke="${stroke}" stroke-width="3" fill="none" stroke-linecap="round"/>`;
      case 'open':
        return `
          <ellipse cx="${cx}" cy="${y+2}" rx="9" ry="7" fill="${stroke}"/>
          <ellipse cx="${cx}" cy="${y}" rx="6" ry="4" fill="#C0392B"/>
        `;
      case 'teeth':
        return `
          <rect x="${cx-11}" y="${y-2}" width="22" height="12" rx="2" fill="${stroke}"/>
          <rect x="${cx-8}" y="${y}" width="5" height="7" fill="white"/>
          <rect x="${cx-1}" y="${y}" width="5" height="7" fill="white"/>
          <rect x="${cx+6}" y="${y}" width="5" height="7" fill="white"/>
        `;
      case 'zigzag':
        return `<path d="M ${cx-12} ${y+2} L ${cx-6} ${y-4} L ${cx} ${y+3} L ${cx+6} ${y-4} L ${cx+12} ${y+2}" stroke="${stroke}" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
      case 'ooo':
        return `<circle cx="${cx}" cy="${y+2}" r="7" fill="${stroke}"/>`;
      case 'vampire':
        return `
          <path d="M ${cx-10} ${y} Q ${cx} ${y+5} ${cx+10} ${y}" stroke="${stroke}" stroke-width="2.5" fill="none"/>
          <polygon points="${cx-4},${y+1} ${cx-2},${y+9} ${cx},${y+1}" fill="white" stroke="${stroke}" stroke-width="1"/>
          <polygon points="${cx},${y+1} ${cx+2},${y+9} ${cx+4},${y+1}" fill="white" stroke="${stroke}" stroke-width="1"/>
        `;
      case 'braces':
        return `
          <rect x="${cx-12}" y="${y-1}" width="24" height="10" rx="2" fill="white" stroke="${stroke}" stroke-width="2"/>
          <line x1="${cx-12}" y1="${y+3}" x2="${cx+12}" y2="${y+3}" stroke="#3498DB" stroke-width="2"/>
          <rect x="${cx-9}" y="${y+1}" width="3" height="5" fill="#3498DB"/>
          <rect x="${cx-3}" y="${y+1}" width="3" height="5" fill="#3498DB"/>
          <rect x="${cx+3}" y="${y+1}" width="3" height="5" fill="#3498DB"/>
        `;
      default:
        return this.renderMouth('smile', body, stroke);
    }
  }

  private renderHeadAcc(acc: HeadAccessory, c: any, stroke: string, sw: number): string {
    switch (acc) {
      case 'antenna':
        return `
          <line x1="50" y1="25" x2="50" y2="10" stroke="${stroke}" stroke-width="${sw}"/>
          <circle cx="50" cy="8" r="5" fill="#E74C3C" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'spring':
        return `
          <path d="M 50 25 Q 42 20 50 15 Q 58 10 50 5" stroke="${stroke}" stroke-width="${sw}" fill="none"/>
          <circle cx="50" cy="3" r="4" fill="#9B59B6" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'propeller':
        return `
          <line x1="50" y1="25" x2="50" y2="14" stroke="${stroke}" stroke-width="${sw}"/>
          <ellipse cx="50" cy="10" rx="16" ry="5" fill="#95A5A6" stroke="${stroke}" stroke-width="2"/>
          <ellipse cx="50" cy="10" rx="16" ry="5" fill="#71797E" stroke="${stroke}" stroke-width="2" transform="rotate(60 50 10)"/>
          <circle cx="50" cy="10" r="4" fill="${stroke}"/>
        `;
      case 'mohawk':
        return `
          <path d="M 42 25 L 42 8 Q 50 2 58 8 L 58 25" fill="#E74C3C" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'cap':
        return `
          <ellipse cx="50" cy="28" rx="26" ry="7" fill="#34495E" stroke="${stroke}" stroke-width="2"/>
          <path d="M 26 28 Q 26 12 50 10 Q 74 12 74 28" fill="#34495E" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'headphones':
        return `
          <path d="M 24 48 Q 24 18 50 15 Q 76 18 76 48" stroke="${stroke}" stroke-width="5" fill="none"/>
          <ellipse cx="24" cy="50" rx="7" ry="10" fill="#1a1a1a" stroke="${stroke}" stroke-width="2"/>
          <ellipse cx="76" cy="50" rx="7" ry="10" fill="#1a1a1a" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'horns':
        return `
          <path d="M 32 32 Q 22 26 20 12" stroke="${c.dark}" stroke-width="6" fill="none" stroke-linecap="round"/>
          <path d="M 68 32 Q 78 26 80 12" stroke="${c.dark}" stroke-width="6" fill="none" stroke-linecap="round"/>
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
          <ellipse cx="32" cy="${eyeY+10}" rx="6" ry="3" fill="#FADBD8"/>
          <ellipse cx="68" cy="${eyeY+10}" rx="6" ry="3" fill="#FADBD8"/>
        `;
      case 'scar':
        return `
          <line x1="64" y1="${eyeY-8}" x2="70" y2="${eyeY+6}" stroke="${stroke}" stroke-width="2"/>
          <line x1="62" y1="${eyeY-4}" x2="68" y2="${eyeY-2}" stroke="${stroke}" stroke-width="1.5"/>
          <line x1="66" y1="${eyeY+2}" x2="72" y2="${eyeY+4}" stroke="${stroke}" stroke-width="1.5"/>
        `;
      case 'bandaid':
        return `
          <rect x="62" y="${eyeY}" width="14" height="7" rx="1" fill="#F5CBA7" stroke="${stroke}" stroke-width="1.5" transform="rotate(-15 69 ${eyeY+3})"/>
        `;
      case 'freckles':
        return `
          <circle cx="34" cy="${eyeY+8}" r="2" fill="#A0522D"/>
          <circle cx="38" cy="${eyeY+11}" r="2" fill="#A0522D"/>
          <circle cx="32" cy="${eyeY+13}" r="2" fill="#A0522D"/>
          <circle cx="66" cy="${eyeY+8}" r="2" fill="#A0522D"/>
          <circle cx="62" cy="${eyeY+11}" r="2" fill="#A0522D"/>
          <circle cx="68" cy="${eyeY+13}" r="2" fill="#A0522D"/>
        `;
      case 'mustache':
        return `
          <path d="M 38 ${mouthY-4} Q 44 ${mouthY-10} 50 ${mouthY-5} Q 56 ${mouthY-10} 62 ${mouthY-4}" stroke="${stroke}" stroke-width="3" fill="none" stroke-linecap="round"/>
        `;
      case 'tears':
        return `
          <ellipse cx="32" cy="${eyeY+12}" rx="3" ry="6" fill="#85C1E9" stroke="${stroke}" stroke-width="1"/>
        `;
      case 'sweat':
        return `
          <ellipse cx="70" cy="${eyeY-3}" rx="4" ry="6" fill="#85C1E9" stroke="${stroke}" stroke-width="1"/>
        `;
      case 'none':
      default:
        return '';
    }
  }

  private renderBodyDetail(detail: BodyDetail, body: BodyShape, c: any, stroke: string): string {
    const baseY = body === 'crushed' ? 58 : body === 'round' ? 60 : body === 'tall' ? 58 : body === 'tv' ? 66 : body === 'triangle' ? 62 : 58;

    switch (detail) {
      case 'rust':
        return `
          <ellipse cx="62" cy="${baseY}" rx="8" ry="5" fill="#8B4513" opacity="0.5"/>
          <ellipse cx="58" cy="${baseY+6}" rx="5" ry="3" fill="#A0522D" opacity="0.4"/>
        `;
      case 'dent':
        return `<ellipse cx="62" cy="${baseY}" rx="8" ry="10" fill="${c.dark}" opacity="0.3"/>`;
      case 'bolt':
        return `
          <circle cx="64" cy="${baseY}" r="5" fill="#95A5A6" stroke="${stroke}" stroke-width="2"/>
          <line x1="61" y1="${baseY}" x2="67" y2="${baseY}" stroke="${stroke}" stroke-width="2"/>
          <line x1="64" y1="${baseY-3}" x2="64" y2="${baseY+3}" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'patch':
        return `
          <rect x="58" y="${baseY-6}" width="12" height="12" fill="#71797E" stroke="${stroke}" stroke-width="2"/>
          <circle cx="61" cy="${baseY-3}" r="1.5" fill="${stroke}"/>
          <circle cx="67" cy="${baseY-3}" r="1.5" fill="${stroke}"/>
          <circle cx="61" cy="${baseY+3}" r="1.5" fill="${stroke}"/>
          <circle cx="67" cy="${baseY+3}" r="1.5" fill="${stroke}"/>
        `;
      case 'crack':
        return `<path d="M 62 ${baseY-10} L 65 ${baseY-3} L 60 ${baseY} L 67 ${baseY+8}" stroke="${stroke}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
      case 'sticker':
        return `
          <circle cx="64" cy="${baseY}" r="7" fill="#F1C40F" stroke="${stroke}" stroke-width="2"/>
          <text x="64" y="${baseY+3}" font-size="9" fill="${stroke}" text-anchor="middle" font-weight="bold">:)</text>
        `;
      case 'gauge':
        return `
          <circle cx="64" cy="${baseY}" r="7" fill="white" stroke="${stroke}" stroke-width="2"/>
          <line x1="64" y1="${baseY}" x2="67" y2="${baseY-4}" stroke="#E74C3C" stroke-width="2" stroke-linecap="round"/>
          <circle cx="64" cy="${baseY}" r="2" fill="${stroke}"/>
        `;
      case 'none':
      default:
        return '';
    }
  }

  private getEyePos(body: BodyShape): { y: number; lx: number; rx: number } {
    switch (body) {
      case 'crushed': return { y: 50, lx: 40, rx: 60 };
      case 'round': return { y: 48, lx: 38, rx: 62 };
      case 'tall': return { y: 40, lx: 42, rx: 58 };
      case 'tv': return { y: 50, lx: 40, rx: 60 };
      case 'capsule': return { y: 48, lx: 40, rx: 60 };
      case 'triangle': return { y: 52, lx: 42, rx: 58 };
      default: return { y: 46, lx: 38, rx: 62 };
    }
  }

  private getMouthY(body: BodyShape): number {
    switch (body) {
      case 'crushed': return 68;
      case 'round': return 62;
      case 'tall': return 62;
      case 'tv': return 62;
      case 'capsule': return 62;
      case 'triangle': return 68;
      default: return 60;
    }
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
  getBodyDetailOptions(): BodyDetail[] { return [...this.bodyDetails]; }
  getColorOptions(): AvatarColor[] { return [...this.colors]; }
}
