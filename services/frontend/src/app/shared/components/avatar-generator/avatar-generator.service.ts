import { Injectable } from '@angular/core';
import {
  AvatarConfig,
  BodyShape,
  EyeType,
  MouthType,
  HeadFeature,
  TopFeature,
  ExtraDetail,
  FlatColor,
  FLAT_COLORS,
  DEFAULT_AVATAR,
} from './avatar.types';

@Injectable({
  providedIn: 'root'
})
export class AvatarGeneratorService {

  private readonly bodies: BodyShape[] = ['can', 'box', 'round', 'tall', 'crushed', 'dented'];
  private readonly eyes: EyeType[] = ['normal', 'bulging', 'tiny', 'uneven', 'spiral', 'x_x', 'hearts', 'one_big'];
  private readonly mouths: MouthType[] = ['smile', 'meh', 'zigzag', 'open', 'ooo', 'teeth', 'derp', 'whistle'];
  private readonly headFeatures: HeadFeature[] = ['none', 'dent', 'bandage', 'crack', 'rust_spot', 'bolt', 'patch', 'burnt'];
  private readonly topFeatures: TopFeature[] = ['none', 'antenna', 'bent_antenna', 'spring', 'smoke', 'spark', 'propeller', 'straw'];
  private readonly extras: ExtraDetail[] = ['none', 'blush', 'sweat', 'tear', 'steam', 'flies', 'stars', 'shine'];
  private readonly colors: FlatColor[] = ['red', 'blue', 'green', 'orange', 'purple', 'yellow', 'gray', 'pink', 'teal', 'brown'];

  generateFromSeed(seed: string): AvatarConfig {
    const hash = this.hashString(seed);
    return {
      body: this.bodies[hash % this.bodies.length],
      eyes: this.eyes[(hash >> 3) % this.eyes.length],
      mouth: this.mouths[(hash >> 6) % this.mouths.length],
      headFeature: this.headFeatures[(hash >> 9) % this.headFeatures.length],
      topFeature: this.topFeatures[(hash >> 12) % this.topFeatures.length],
      extra: this.extras[(hash >> 15) % this.extras.length],
      color: this.colors[(hash >> 18) % this.colors.length],
      seed,
    };
  }

  generateRandom(): AvatarConfig {
    return {
      body: this.randomItem(this.bodies),
      eyes: this.randomItem(this.eyes),
      mouth: this.randomItem(this.mouths),
      headFeature: this.randomItem(this.headFeatures),
      topFeature: this.randomItem(this.topFeatures),
      extra: this.randomItem(this.extras),
      color: this.randomItem(this.colors),
    };
  }

  generateSVG(config: AvatarConfig, size: number = 100): string {
    const c = FLAT_COLORS[config.color];
    const id = config.seed || Math.random().toString(36).slice(2, 8);

    return `
      <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        ${this.renderTopFeature(config.topFeature, c)}
        ${this.renderBody(config.body, c)}
        ${this.renderHeadFeature(config.headFeature, config.body, c)}
        ${this.renderEyes(config.eyes, config.body)}
        ${this.renderMouth(config.mouth, config.body)}
        ${this.renderExtra(config.extra, config.body)}
      </svg>
    `;
  }

  private renderBody(body: BodyShape, c: any): string {
    switch (body) {
      case 'can':
        return `
          <rect x="25" y="22" width="50" height="60" rx="4" fill="${c.main}"/>
          <rect x="25" y="22" width="50" height="8" fill="${c.dark}"/>
          <rect x="25" y="74" width="50" height="8" fill="${c.dark}"/>
          <rect x="28" y="30" width="6" height="44" fill="${c.light}" opacity="0.4"/>
        `;

      case 'box':
        return `
          <rect x="22" y="25" width="56" height="55" fill="${c.main}"/>
          <rect x="22" y="25" width="56" height="6" fill="${c.dark}"/>
          <rect x="22" y="74" width="56" height="6" fill="${c.dark}"/>
          <line x1="22" y1="25" x2="22" y2="80" stroke="${c.dark}" stroke-width="3"/>
          <line x1="78" y1="25" x2="78" y2="80" stroke="${c.dark}" stroke-width="3"/>
        `;

      case 'round':
        return `
          <ellipse cx="50" cy="52" rx="30" ry="32" fill="${c.main}"/>
          <ellipse cx="50" cy="52" rx="30" ry="32" fill="none" stroke="${c.dark}" stroke-width="3"/>
          <ellipse cx="40" cy="45" rx="8" ry="12" fill="${c.light}" opacity="0.3"/>
        `;

      case 'tall':
        return `
          <rect x="32" y="15" width="36" height="72" rx="4" fill="${c.main}"/>
          <rect x="32" y="15" width="36" height="8" fill="${c.dark}"/>
          <rect x="32" y="79" width="36" height="8" fill="${c.dark}"/>
          <rect x="35" y="23" width="5" height="56" fill="${c.light}" opacity="0.4"/>
        `;

      case 'crushed':
        return `
          <path d="M 28 80 Q 35 88 50 85 Q 65 88 72 80 L 76 40 Q 70 35 50 38 Q 30 35 24 40 Z" fill="${c.main}"/>
          <path d="M 24 40 Q 30 35 50 38 Q 70 35 76 40" fill="${c.dark}"/>
          <path d="M 28 55 Q 45 50 72 58" stroke="${c.dark}" stroke-width="2" fill="none"/>
          <path d="M 26 70 Q 50 65 74 72" stroke="${c.dark}" stroke-width="2" fill="none"/>
        `;

      case 'dented':
        return `
          <rect x="25" y="22" width="50" height="60" rx="4" fill="${c.main}"/>
          <rect x="25" y="22" width="50" height="8" fill="${c.dark}"/>
          <rect x="25" y="74" width="50" height="8" fill="${c.dark}"/>
          <ellipse cx="60" cy="50" rx="12" ry="15" fill="${c.dark}" opacity="0.3"/>
          <path d="M 55 40 Q 65 50 55 60" stroke="${c.dark}" stroke-width="1.5" fill="none"/>
        `;

      default:
        return this.renderBody('can', c);
    }
  }

  private renderEyes(eyes: EyeType, body: BodyShape): string {
    const yBase = body === 'crushed' ? 48 : body === 'round' ? 45 : body === 'tall' ? 38 : 42;
    const leftX = body === 'round' ? 38 : 38;
    const rightX = body === 'round' ? 62 : 62;

    switch (eyes) {
      case 'normal':
        return `
          <circle cx="${leftX}" cy="${yBase}" r="8" fill="white"/>
          <circle cx="${rightX}" cy="${yBase}" r="8" fill="white"/>
          <circle cx="${leftX+1}" cy="${yBase}" r="4" fill="#1a1a1a"/>
          <circle cx="${rightX+1}" cy="${yBase}" r="4" fill="#1a1a1a"/>
          <circle cx="${leftX+2}" cy="${yBase-1}" r="1.5" fill="white"/>
          <circle cx="${rightX+2}" cy="${yBase-1}" r="1.5" fill="white"/>
        `;

      case 'bulging':
        return `
          <circle cx="${leftX-2}" cy="${yBase}" r="12" fill="white"/>
          <circle cx="${rightX+2}" cy="${yBase}" r="12" fill="white"/>
          <circle cx="${leftX-2}" cy="${yBase}" r="12" fill="none" stroke="#1a1a1a" stroke-width="2"/>
          <circle cx="${rightX+2}" cy="${yBase}" r="12" fill="none" stroke="#1a1a1a" stroke-width="2"/>
          <circle cx="${leftX}" cy="${yBase}" r="5" fill="#1a1a1a"/>
          <circle cx="${rightX}" cy="${yBase}" r="5" fill="#1a1a1a"/>
          <circle cx="${leftX+2}" cy="${yBase-2}" r="2" fill="white"/>
          <circle cx="${rightX+2}" cy="${yBase-2}" r="2" fill="white"/>
        `;

      case 'tiny':
        return `
          <circle cx="${leftX}" cy="${yBase}" r="3" fill="#1a1a1a"/>
          <circle cx="${rightX}" cy="${yBase}" r="3" fill="#1a1a1a"/>
          <circle cx="${leftX+0.5}" cy="${yBase-0.5}" r="1" fill="white"/>
          <circle cx="${rightX+0.5}" cy="${yBase-0.5}" r="1" fill="white"/>
        `;

      case 'uneven':
        return `
          <circle cx="${leftX}" cy="${yBase-3}" r="10" fill="white"/>
          <circle cx="${rightX}" cy="${yBase+2}" r="6" fill="white"/>
          <circle cx="${leftX+1}" cy="${yBase-2}" r="5" fill="#1a1a1a"/>
          <circle cx="${rightX}" cy="${yBase+2}" r="3" fill="#1a1a1a"/>
          <circle cx="${leftX+3}" cy="${yBase-4}" r="2" fill="white"/>
        `;

      case 'spiral':
        return `
          <circle cx="${leftX}" cy="${yBase}" r="8" fill="white"/>
          <circle cx="${rightX}" cy="${yBase}" r="8" fill="white"/>
          <path d="M ${leftX} ${yBase} m -5 0 a 5 5 0 1 1 5 -5 a 3 3 0 1 1 -3 3 a 1.5 1.5 0 1 1 1.5 -1.5" stroke="#1a1a1a" stroke-width="1.5" fill="none"/>
          <path d="M ${rightX} ${yBase} m -5 0 a 5 5 0 1 1 5 -5 a 3 3 0 1 1 -3 3 a 1.5 1.5 0 1 1 1.5 -1.5" stroke="#1a1a1a" stroke-width="1.5" fill="none"/>
        `;

      case 'x_x':
        return `
          <line x1="${leftX-5}" y1="${yBase-5}" x2="${leftX+5}" y2="${yBase+5}" stroke="#1a1a1a" stroke-width="3" stroke-linecap="round"/>
          <line x1="${leftX-5}" y1="${yBase+5}" x2="${leftX+5}" y2="${yBase-5}" stroke="#1a1a1a" stroke-width="3" stroke-linecap="round"/>
          <line x1="${rightX-5}" y1="${yBase-5}" x2="${rightX+5}" y2="${yBase+5}" stroke="#1a1a1a" stroke-width="3" stroke-linecap="round"/>
          <line x1="${rightX-5}" y1="${yBase+5}" x2="${rightX+5}" y2="${yBase-5}" stroke="#1a1a1a" stroke-width="3" stroke-linecap="round"/>
        `;

      case 'hearts':
        return `
          <path d="M ${leftX} ${yBase+4} C ${leftX-8} ${yBase-2} ${leftX-8} ${yBase-8} ${leftX} ${yBase-4} C ${leftX+8} ${yBase-8} ${leftX+8} ${yBase-2} ${leftX} ${yBase+4}" fill="#E74C3C"/>
          <path d="M ${rightX} ${yBase+4} C ${rightX-8} ${yBase-2} ${rightX-8} ${yBase-8} ${rightX} ${yBase-4} C ${rightX+8} ${yBase-8} ${rightX+8} ${yBase-2} ${rightX} ${yBase+4}" fill="#E74C3C"/>
        `;

      case 'one_big':
        return `
          <ellipse cx="50" cy="${yBase}" rx="18" ry="14" fill="white"/>
          <ellipse cx="50" cy="${yBase}" rx="18" ry="14" fill="none" stroke="#1a1a1a" stroke-width="2"/>
          <circle cx="52" cy="${yBase}" r="7" fill="#1a1a1a"/>
          <circle cx="55" cy="${yBase-3}" r="3" fill="white"/>
        `;

      default:
        return this.renderEyes('normal', body);
    }
  }

  private renderMouth(mouth: MouthType, body: BodyShape): string {
    const yBase = body === 'crushed' ? 68 : body === 'round' ? 62 : body === 'tall' ? 58 : 60;
    const cx = 50;

    switch (mouth) {
      case 'smile':
        return `<path d="M ${cx-12} ${yBase} Q ${cx} ${yBase+12} ${cx+12} ${yBase}" stroke="#1a1a1a" stroke-width="3" fill="none" stroke-linecap="round"/>`;

      case 'meh':
        return `<line x1="${cx-10}" y1="${yBase+3}" x2="${cx+10}" y2="${yBase+3}" stroke="#1a1a1a" stroke-width="3" stroke-linecap="round"/>`;

      case 'zigzag':
        return `<path d="M ${cx-12} ${yBase+3} L ${cx-6} ${yBase-2} L ${cx} ${yBase+5} L ${cx+6} ${yBase-2} L ${cx+12} ${yBase+3}" stroke="#1a1a1a" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;

      case 'open':
        return `
          <ellipse cx="${cx}" cy="${yBase+4}" rx="10" ry="8" fill="#1a1a1a"/>
          <ellipse cx="${cx}" cy="${yBase+1}" rx="7" ry="4" fill="#C0392B"/>
        `;

      case 'ooo':
        return `
          <circle cx="${cx}" cy="${yBase+4}" r="7" fill="#1a1a1a"/>
          <ellipse cx="${cx}" cy="${yBase+2}" rx="4" ry="3" fill="#555"/>
        `;

      case 'teeth':
        return `
          <rect x="${cx-12}" y="${yBase}" width="24" height="12" rx="3" fill="#1a1a1a"/>
          <rect x="${cx-10}" y="${yBase+2}" width="5" height="6" fill="white"/>
          <rect x="${cx-3}" y="${yBase+2}" width="5" height="6" fill="white"/>
          <rect x="${cx+4}" y="${yBase+2}" width="5" height="6" fill="white"/>
        `;

      case 'derp':
        return `<path d="M ${cx-10} ${yBase+5} Q ${cx-5} ${yBase-3} ${cx+2} ${yBase+8} Q ${cx+8} ${yBase} ${cx+12} ${yBase+3}" stroke="#1a1a1a" stroke-width="3" fill="none" stroke-linecap="round"/>`;

      case 'whistle':
        return `
          <circle cx="${cx+5}" cy="${yBase+3}" r="5" fill="#1a1a1a"/>
          <line x1="${cx-8}" y1="${yBase+3}" x2="${cx}" y2="${yBase+3}" stroke="#1a1a1a" stroke-width="2"/>
          <!-- Nota -->
          <ellipse cx="${cx+18}" cy="${yBase-8}" rx="3" ry="2" fill="#1a1a1a" transform="rotate(-20 ${cx+18} ${yBase-8})"/>
          <line x1="${cx+20}" y1="${yBase-8}" x2="${cx+20}" y2="${yBase-18}" stroke="#1a1a1a" stroke-width="1.5"/>
        `;

      default:
        return this.renderMouth('smile', body);
    }
  }

  private renderHeadFeature(feature: HeadFeature, body: BodyShape, c: any): string {
    const yBase = body === 'crushed' ? 42 : body === 'round' ? 30 : body === 'tall' ? 25 : 32;

    switch (feature) {
      case 'dent':
        return `
          <ellipse cx="65" cy="${yBase+15}" rx="8" ry="10" fill="${c.dark}" opacity="0.5"/>
          <path d="M 60 ${yBase+10} Q 68 ${yBase+15} 62 ${yBase+22}" stroke="${c.dark}" stroke-width="1" fill="none"/>
        `;

      case 'bandage':
        return `
          <rect x="55" y="${yBase+5}" width="18" height="8" rx="1" fill="#F5DEB3"/>
          <line x1="58" y1="${yBase+7}" x2="58" y2="${yBase+11}" stroke="#DEB887" stroke-width="1"/>
          <line x1="62" y1="${yBase+7}" x2="62" y2="${yBase+11}" stroke="#DEB887" stroke-width="1"/>
          <line x1="66" y1="${yBase+7}" x2="66" y2="${yBase+11}" stroke="#DEB887" stroke-width="1"/>
          <line x1="70" y1="${yBase+7}" x2="70" y2="${yBase+11}" stroke="#DEB887" stroke-width="1"/>
        `;

      case 'crack':
        return `
          <path d="M 60 ${yBase} L 65 ${yBase+8} L 58 ${yBase+12} L 68 ${yBase+22} L 62 ${yBase+18}" stroke="#1a1a1a" stroke-width="2" fill="none" stroke-linecap="round"/>
        `;

      case 'rust_spot':
        return `
          <ellipse cx="62" cy="${yBase+12}" rx="7" ry="5" fill="#8B4513" opacity="0.6"/>
          <ellipse cx="58" cy="${yBase+18}" rx="4" ry="3" fill="#A0522D" opacity="0.5"/>
          <circle cx="68" cy="${yBase+8}" r="2" fill="#8B4513" opacity="0.4"/>
        `;

      case 'bolt':
        return `
          <circle cx="65" cy="${yBase+10}" r="5" fill="#71797E"/>
          <line x1="62" y1="${yBase+10}" x2="68" y2="${yBase+10}" stroke="#4A4A4A" stroke-width="2"/>
          <line x1="65" y1="${yBase+7}" x2="65" y2="${yBase+13}" stroke="#4A4A4A" stroke-width="2"/>
        `;

      case 'patch':
        return `
          <rect x="56" y="${yBase+8}" width="14" height="14" fill="#71797E" stroke="#4A4A4A" stroke-width="1"/>
          <circle cx="59" cy="${yBase+11}" r="1.5" fill="#4A4A4A"/>
          <circle cx="67" cy="${yBase+11}" r="1.5" fill="#4A4A4A"/>
          <circle cx="59" cy="${yBase+19}" r="1.5" fill="#4A4A4A"/>
          <circle cx="67" cy="${yBase+19}" r="1.5" fill="#4A4A4A"/>
        `;

      case 'burnt':
        return `
          <ellipse cx="62" cy="${yBase+12}" rx="10" ry="8" fill="#1a1a1a" opacity="0.4"/>
          <path d="M 55 ${yBase+8} Q 62 ${yBase+5} 68 ${yBase+10}" stroke="#1a1a1a" stroke-width="1" fill="none" opacity="0.3"/>
          <!-- Kıvılcımlar -->
          <circle cx="58" cy="${yBase+5}" r="1" fill="#F39C12"/>
          <circle cx="68" cy="${yBase+7}" r="1.5" fill="#E74C3C"/>
        `;

      case 'none':
      default:
        return '';
    }
  }

  private renderTopFeature(feature: TopFeature, c: any): string {
    switch (feature) {
      case 'antenna':
        return `
          <line x1="50" y1="22" x2="50" y2="8" stroke="#555" stroke-width="3"/>
          <circle cx="50" cy="6" r="4" fill="#E74C3C"/>
        `;

      case 'bent_antenna':
        return `
          <path d="M 50 22 L 50 14 Q 50 8 58 5" stroke="#555" stroke-width="3" fill="none"/>
          <circle cx="60" cy="5" r="4" fill="#3498DB"/>
        `;

      case 'spring':
        return `
          <path d="M 50 22 Q 44 18 50 14 Q 56 10 50 6 Q 44 2 50 -2" stroke="#555" stroke-width="2.5" fill="none"/>
          <circle cx="50" cy="-4" r="3" fill="#9B59B6"/>
        `;

      case 'smoke':
        return `
          <ellipse cx="55" cy="12" rx="6" ry="4" fill="#95A5A6" opacity="0.6"/>
          <ellipse cx="60" cy="6" rx="5" ry="3" fill="#BDC3C7" opacity="0.5"/>
          <ellipse cx="52" cy="2" rx="4" ry="2.5" fill="#D5DBDB" opacity="0.4"/>
        `;

      case 'spark':
        return `
          <polygon points="50,5 52,12 58,12 54,17 56,24 50,19 44,24 46,17 42,12 48,12" fill="#F1C40F"/>
          <polygon points="50,8 51,12 54,12 52,15 53,19 50,16 47,19 48,15 46,12 49,12" fill="#F39C12"/>
        `;

      case 'propeller':
        return `
          <ellipse cx="50" cy="10" rx="16" ry="4" fill="#71797E" transform="rotate(30 50 10)"/>
          <ellipse cx="50" cy="10" rx="16" ry="4" fill="#95A5A6" transform="rotate(-30 50 10)"/>
          <circle cx="50" cy="10" r="4" fill="#555"/>
        `;

      case 'straw':
        return `
          <rect x="54" y="-5" width="5" height="28" rx="2" fill="#E74C3C"/>
          <rect x="55" y="-5" width="1.5" height="28" fill="#C0392B" opacity="0.5"/>
          <path d="M 56.5 -5 Q 56.5 -10 65 -12" stroke="#E74C3C" stroke-width="5" fill="none" stroke-linecap="round"/>
        `;

      case 'none':
      default:
        return '';
    }
  }

  private renderExtra(extra: ExtraDetail, body: BodyShape): string {
    const yBase = body === 'crushed' ? 48 : body === 'round' ? 45 : 42;

    switch (extra) {
      case 'blush':
        return `
          <ellipse cx="30" cy="${yBase+8}" rx="6" ry="4" fill="#FADBD8" opacity="0.8"/>
          <ellipse cx="70" cy="${yBase+8}" rx="6" ry="4" fill="#FADBD8" opacity="0.8"/>
        `;

      case 'sweat':
        return `
          <ellipse cx="72" cy="${yBase-5}" rx="3" ry="5" fill="#85C1E9"/>
          <ellipse cx="74" cy="${yBase-8}" rx="1.5" ry="2" fill="#AED6F1"/>
        `;

      case 'tear':
        return `
          <ellipse cx="28" cy="${yBase+5}" rx="3" ry="6" fill="#85C1E9"/>
          <circle cx="28" cy="${yBase+12}" r="2" fill="#85C1E9"/>
        `;

      case 'steam':
        return `
          <path d="M 75 35 Q 80 30 78 25 Q 82 20 80 15" stroke="#BDC3C7" stroke-width="2" fill="none" opacity="0.6"/>
          <path d="M 80 38 Q 85 33 83 28" stroke="#D5DBDB" stroke-width="2" fill="none" opacity="0.5"/>
        `;

      case 'flies':
        return `
          <g>
            <ellipse cx="78" cy="30" rx="2" ry="1" fill="#1a1a1a"/>
            <line x1="77" y1="29" x2="75" y2="27" stroke="#1a1a1a" stroke-width="0.5"/>
            <line x1="79" y1="29" x2="81" y2="27" stroke="#1a1a1a" stroke-width="0.5"/>
          </g>
          <g>
            <ellipse cx="82" cy="38" rx="1.5" ry="0.8" fill="#1a1a1a"/>
            <line x1="81" y1="37" x2="79" y2="35" stroke="#1a1a1a" stroke-width="0.5"/>
          </g>
          <!-- Uçuş çizgileri -->
          <path d="M 76 32 Q 74 34 76 36" stroke="#1a1a1a" stroke-width="0.5" fill="none" opacity="0.4"/>
        `;

      case 'stars':
        return `
          <polygon points="78,25 79,28 82,28 80,30 81,33 78,31 75,33 76,30 74,28 77,28" fill="#F1C40F"/>
          <polygon points="22,35 23,37 25,37 24,39 24.5,41 22,40 19.5,41 20,39 19,37 21,37" fill="#F1C40F"/>
        `;

      case 'shine':
        return `
          <line x1="75" y1="28" x2="82" y2="22" stroke="white" stroke-width="2" stroke-linecap="round"/>
          <line x1="80" y1="30" x2="85" y2="26" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
        `;

      case 'none':
      default:
        return '';
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

  getBodyOptions(): BodyShape[] { return [...this.bodies]; }
  getEyeOptions(): EyeType[] { return [...this.eyes]; }
  getMouthOptions(): MouthType[] { return [...this.mouths]; }
  getHeadFeatureOptions(): HeadFeature[] { return [...this.headFeatures]; }
  getTopFeatureOptions(): TopFeature[] { return [...this.topFeatures]; }
  getExtraOptions(): ExtraDetail[] { return [...this.extras]; }
  getColorOptions(): FlatColor[] { return [...this.colors]; }
}
