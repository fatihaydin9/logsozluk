import { Injectable } from '@angular/core';
import {
  AvatarConfig,
  BodyShape,
  EyeType,
  MouthType,
  HeadAccessory,
  AvatarColor,
  COLORS,
} from './avatar.types';

@Injectable({
  providedIn: 'root'
})
export class AvatarGeneratorService {

  private readonly bodies: BodyShape[] = ['can', 'box', 'round', 'crushed', 'tall', 'barrel'];
  private readonly eyes: EyeType[] = ['normal', 'angry', 'sneaky', 'popping', 'spiral', 'dead', 'money', 'tired', 'one_big', 'laser'];
  private readonly mouths: MouthType[] = ['flat', 'grin', 'sad', 'evil', 'shocked', 'tongue', 'smirk', 'zipper'];
  private readonly headAccs: HeadAccessory[] = ['none', 'antenna', 'bolt', 'crack', 'smoke', 'halo', 'devil'];
  private readonly colors: AvatarColor[] = ['red', 'blue', 'green', 'orange', 'purple', 'yellow', 'gray', 'pink', 'teal', 'black'];

  generateFromSeed(seed: string): AvatarConfig {
    const hash = this.hashString(seed);
    return {
      body: this.bodies[hash % this.bodies.length],
      eyes: this.eyes[(hash >> 3) % this.eyes.length],
      mouth: this.mouths[(hash >> 6) % this.mouths.length],
      headAcc: this.headAccs[(hash >> 9) % this.headAccs.length],
      color: this.colors[(hash >> 12) % this.colors.length],
      seed,
    };
  }

  generateRandom(): AvatarConfig {
    return {
      body: this.randomItem(this.bodies),
      eyes: this.randomItem(this.eyes),
      mouth: this.randomItem(this.mouths),
      headAcc: this.randomItem(this.headAccs),
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
    </svg>`;
  }

  private renderBody(body: BodyShape, c: any, stroke: string, sw: number): string {
    switch (body) {
      case 'can':
        return `
          <rect x="28" y="28" width="44" height="52" rx="3" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <rect x="28" y="28" width="44" height="8" fill="${c.dark}" stroke="${stroke}" stroke-width="2"/>
          <rect x="28" y="72" width="44" height="8" fill="${c.dark}" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'box':
        return `
          <rect x="26" y="32" width="48" height="44" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <line x1="26" y1="40" x2="74" y2="40" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'round':
        return `<circle cx="50" cy="55" r="28" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>`;
      case 'crushed':
        return `
          <path d="M 32 78 Q 42 84 50 80 Q 58 84 68 78 L 72 42 Q 62 36 50 40 Q 38 36 28 42 Z" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
        `;
      case 'tall':
        return `
          <rect x="34" y="18" width="32" height="68" rx="3" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <rect x="34" y="18" width="32" height="8" fill="${c.dark}" stroke="${stroke}" stroke-width="2"/>
        `;
      case 'barrel':
        return `
          <ellipse cx="50" cy="55" rx="26" ry="30" fill="${c.main}" stroke="${stroke}" stroke-width="${sw}"/>
          <ellipse cx="50" cy="32" rx="20" ry="6" fill="${c.dark}" stroke="${stroke}" stroke-width="2"/>
          <line x1="26" y1="55" x2="74" y2="55" stroke="${stroke}" stroke-width="2"/>
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
        return `
          <path d="M ${cx-14} ${y} Q ${cx-7} ${y+8} ${cx} ${y} Q ${cx+7} ${y+8} ${cx+14} ${y}" stroke="${stroke}" stroke-width="3" fill="none" stroke-linecap="round"/>
        `;
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
      default:
        return this.renderMouth('flat', body, stroke);
    }
  }

  private renderHeadAcc(acc: HeadAccessory, c: any, stroke: string, sw: number, body: BodyShape): string {
    const topY = body === 'tall' ? 18 : body === 'round' ? 27 : body === 'crushed' ? 36 : body === 'barrel' ? 25 : 28;

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
        return `
          <path d="M 62 ${topY} L 68 ${topY+12} L 58 ${topY+18} L 66 ${topY+28}" stroke="${stroke}" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        `;
      case 'smoke':
        return `
          <ellipse cx="68" cy="${topY-8}" rx="6" ry="4" fill="#95A5A6" opacity="0.7"/>
          <ellipse cx="72" cy="${topY-16}" rx="5" ry="3" fill="#BDC3C7" opacity="0.6"/>
          <ellipse cx="66" cy="${topY-22}" rx="4" ry="3" fill="#D5DBDB" opacity="0.5"/>
        `;
      case 'halo':
        return `
          <ellipse cx="50" cy="${topY-10}" rx="18" ry="5" fill="none" stroke="#F1C40F" stroke-width="4"/>
        `;
      case 'devil':
        return `
          <path d="M 30 ${topY+8} Q 24 ${topY-8} 22 ${topY-18}" stroke="#C0392B" stroke-width="5" fill="none" stroke-linecap="round"/>
          <path d="M 70 ${topY+8} Q 76 ${topY-8} 78 ${topY-18}" stroke="#C0392B" stroke-width="5" fill="none" stroke-linecap="round"/>
        `;
      case 'none':
      default:
        return '';
    }
  }

  private getEyePos(body: BodyShape): { y: number; lx: number; rx: number } {
    switch (body) {
      case 'crushed': return { y: 52, lx: 40, rx: 60 };
      case 'round': return { y: 50, lx: 38, rx: 62 };
      case 'tall': return { y: 42, lx: 42, rx: 58 };
      case 'barrel': return { y: 48, lx: 38, rx: 62 };
      default: return { y: 48, lx: 38, rx: 62 };
    }
  }

  private getMouthY(body: BodyShape): number {
    switch (body) {
      case 'crushed': return 68;
      case 'round': return 65;
      case 'tall': return 62;
      case 'barrel': return 65;
      default: return 62;
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
  getColorOptions(): AvatarColor[] { return [...this.colors]; }
}
