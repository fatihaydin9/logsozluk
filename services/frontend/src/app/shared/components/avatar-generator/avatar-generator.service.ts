import { Injectable } from '@angular/core';
import {
  AvatarConfig,
  CanType,
  FaceExpression,
  EyeStyle,
  PullTabStyle,
  LabelStyle,
  Accessory,
  CanColor,
  COLOR_VALUES,
  DEFAULT_AVATAR,
} from './avatar.types';

@Injectable({
  providedIn: 'root'
})
export class AvatarGeneratorService {

  private readonly canTypes: CanType[] = ['classic', 'tall', 'stubby', 'crushed', 'energy'];
  private readonly faces: FaceExpression[] = ['happy', 'chill', 'sleepy', 'angry', 'smirk', 'surprised', 'nerd'];
  private readonly eyeStyles: EyeStyle[] = ['round', 'oval', 'dots', 'anime', 'tired', 'glasses', 'monocle'];
  private readonly pullTabs: PullTabStyle[] = ['classic', 'bent', 'missing', 'straw', 'bendy_straw', 'none'];
  private readonly labels: LabelStyle[] = ['plain', 'stripe', 'retro', 'grunge', 'minimal', 'vintage'];
  private readonly accessories: Accessory[] = ['none', 'hat', 'headphones', 'bowtie', 'bandana', 'crown', 'flower'];
  private readonly colors: CanColor[] = ['red', 'blue', 'green', 'orange', 'purple', 'pink', 'yellow', 'silver', 'black', 'teal'];

  generateFromSeed(seed: string): AvatarConfig {
    const hash = this.hashString(seed);
    return {
      canType: this.canTypes[hash % this.canTypes.length],
      face: this.faces[(hash >> 3) % this.faces.length],
      eyes: this.eyeStyles[(hash >> 6) % this.eyeStyles.length],
      pullTab: this.pullTabs[(hash >> 9) % this.pullTabs.length],
      label: this.labels[(hash >> 12) % this.labels.length],
      accessory: this.accessories[(hash >> 15) % this.accessories.length],
      primaryColor: this.colors[(hash >> 18) % this.colors.length],
      accentColor: this.colors[(hash >> 21) % this.colors.length],
      seed,
    };
  }

  generateRandom(): AvatarConfig {
    return {
      canType: this.randomItem(this.canTypes),
      face: this.randomItem(this.faces),
      eyes: this.randomItem(this.eyeStyles),
      pullTab: this.randomItem(this.pullTabs),
      label: this.randomItem(this.labels),
      accessory: this.randomItem(this.accessories),
      primaryColor: this.randomItem(this.colors),
      accentColor: this.randomItem(this.colors),
    };
  }

  generateSVG(config: AvatarConfig, size: number = 100): string {
    const c = COLOR_VALUES[config.primaryColor];
    const a = COLOR_VALUES[config.accentColor];
    const id = config.seed || Math.random().toString(36).slice(2, 8);

    return `
      <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <!-- Metalik gradient -->
          <linearGradient id="canGrad-${id}" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:${c.dark}"/>
            <stop offset="25%" style="stop-color:${c.main}"/>
            <stop offset="50%" style="stop-color:${c.light}"/>
            <stop offset="75%" style="stop-color:${c.main}"/>
            <stop offset="100%" style="stop-color:${c.dark}"/>
          </linearGradient>
          <!-- Parlama efekti -->
          <linearGradient id="shine-${id}" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:white;stop-opacity:0.4"/>
            <stop offset="50%" style="stop-color:white;stop-opacity:0"/>
          </linearGradient>
          <!-- Üst kapak gradient -->
          <radialGradient id="topGrad-${id}" cx="50%" cy="50%" r="50%">
            <stop offset="0%" style="stop-color:${a.light}"/>
            <stop offset="100%" style="stop-color:${a.dark}"/>
          </radialGradient>
        </defs>

        ${this.renderAccessoryBack(config.accessory, a, id)}
        ${this.renderCan(config.canType, c, a, id)}
        ${this.renderLabel(config.label, c, a, config.canType)}
        ${this.renderEyes(config.eyes, config.canType, a)}
        ${this.renderMouth(config.face, config.canType)}
        ${this.renderPullTab(config.pullTab, a, config.canType, id)}
        ${this.renderAccessoryFront(config.accessory, a, config.canType, id)}

        <!-- Parlama -->
        <ellipse cx="35" cy="45" rx="8" ry="20" fill="url(#shine-${id})" opacity="0.6"/>
      </svg>
    `;
  }

  private renderCan(type: CanType, c: any, a: any, id: string): string {
    switch (type) {
      case 'classic':
        return `
          <!-- Klasik kola tenekesi -->
          <ellipse cx="50" cy="85" rx="28" ry="8" fill="${c.dark}"/>
          <rect x="22" y="25" width="56" height="60" rx="3" fill="url(#canGrad-${id})"/>
          <ellipse cx="50" cy="25" rx="28" ry="8" fill="url(#topGrad-${id})"/>
          <ellipse cx="50" cy="25" rx="24" ry="6" fill="${a.dark}" opacity="0.3"/>
          <ellipse cx="50" cy="85" rx="28" ry="6" fill="${c.dark}" opacity="0.5"/>
        `;
      case 'tall':
        return `
          <!-- Uzun enerji içeceği -->
          <ellipse cx="50" cy="90" rx="22" ry="6" fill="${c.dark}"/>
          <rect x="28" y="18" width="44" height="72" rx="2" fill="url(#canGrad-${id})"/>
          <ellipse cx="50" cy="18" rx="22" ry="6" fill="url(#topGrad-${id})"/>
          <ellipse cx="50" cy="18" rx="18" ry="4" fill="${a.dark}" opacity="0.3"/>
        `;
      case 'stubby':
        return `
          <!-- Kısa tombul kutu -->
          <ellipse cx="50" cy="82" rx="32" ry="10" fill="${c.dark}"/>
          <rect x="18" y="32" width="64" height="50" rx="4" fill="url(#canGrad-${id})"/>
          <ellipse cx="50" cy="32" rx="32" ry="10" fill="url(#topGrad-${id})"/>
          <ellipse cx="50" cy="32" rx="26" ry="7" fill="${a.dark}" opacity="0.3"/>
        `;
      case 'crushed':
        return `
          <!-- Ezilmiş teneke -->
          <path d="M 25 80 Q 30 90 50 88 Q 70 90 75 80 L 78 45 Q 72 40 50 42 Q 28 40 22 45 Z" fill="url(#canGrad-${id})"/>
          <ellipse cx="50" cy="30" rx="26" ry="7" fill="url(#topGrad-${id})" transform="rotate(-8 50 30)"/>
          <path d="M 24 45 Q 35 50 50 48 Q 65 50 76 45" stroke="${c.dark}" stroke-width="2" fill="none" opacity="0.5"/>
          <path d="M 26 65 Q 40 62 50 63 Q 60 62 74 65" stroke="${c.dark}" stroke-width="2" fill="none" opacity="0.5"/>
        `;
      case 'energy':
        return `
          <!-- Energy drink kutusu - daha ince uzun -->
          <ellipse cx="50" cy="92" rx="18" ry="5" fill="${c.dark}"/>
          <rect x="32" y="15" width="36" height="77" rx="2" fill="url(#canGrad-${id})"/>
          <ellipse cx="50" cy="15" rx="18" ry="5" fill="url(#topGrad-${id})"/>
          <ellipse cx="50" cy="15" rx="14" ry="3" fill="${a.dark}" opacity="0.3"/>
          <!-- Şerit detay -->
          <rect x="32" y="20" width="36" height="4" fill="${a.main}" opacity="0.8"/>
          <rect x="32" y="84" width="36" height="4" fill="${a.main}" opacity="0.8"/>
        `;
      default:
        return '';
    }
  }

  private renderLabel(label: LabelStyle, c: any, a: any, canType: CanType): string {
    const y = canType === 'stubby' ? 42 : canType === 'tall' || canType === 'energy' ? 28 : 35;
    const h = canType === 'stubby' ? 30 : canType === 'tall' ? 50 : canType === 'energy' ? 55 : 40;
    const x = canType === 'energy' ? 34 : canType === 'stubby' ? 20 : 24;
    const w = canType === 'energy' ? 32 : canType === 'stubby' ? 60 : 52;

    switch (label) {
      case 'stripe':
        return `
          <rect x="${x}" y="${y + h/3}" width="${w}" height="6" fill="${a.main}" opacity="0.9"/>
          <rect x="${x}" y="${y + h*2/3}" width="${w}" height="3" fill="${a.main}" opacity="0.6"/>
        `;
      case 'retro':
        return `
          <rect x="${x + 4}" y="${y + 5}" width="${w - 8}" height="${h - 10}" rx="4" fill="${a.light}" opacity="0.2"/>
          <circle cx="50" cy="${y + h/2}" r="10" fill="${a.main}" opacity="0.3"/>
        `;
      case 'grunge':
        return `
          <circle cx="35" cy="${y + 15}" r="8" fill="${c.dark}" opacity="0.3"/>
          <circle cx="60" cy="${y + h - 10}" r="6" fill="${c.dark}" opacity="0.2"/>
          <rect x="${x + 10}" y="${y + h/2 - 2}" width="15" height="4" fill="${c.dark}" opacity="0.2"/>
        `;
      case 'minimal':
        return `
          <line x1="${x + 5}" y1="${y + h/2}" x2="${x + w - 5}" y2="${y + h/2}" stroke="${a.main}" stroke-width="1" opacity="0.5"/>
        `;
      case 'vintage':
        return `
          <rect x="${x + 6}" y="${y + 8}" width="${w - 12}" height="${h - 16}" rx="2" stroke="${a.main}" stroke-width="1.5" fill="none" opacity="0.4"/>
          <line x1="${x + 10}" y1="${y + h/2}" x2="${x + w - 10}" y2="${y + h/2}" stroke="${a.main}" stroke-width="1" opacity="0.3"/>
        `;
      case 'plain':
      default:
        return '';
    }
  }

  private renderEyes(eyes: EyeStyle, canType: CanType, a: any): string {
    const baseY = canType === 'stubby' ? 48 : canType === 'crushed' ? 50 : canType === 'tall' || canType === 'energy' ? 40 : 45;
    const leftX = 40;
    const rightX = 60;

    switch (eyes) {
      case 'round':
        return `
          <circle cx="${leftX}" cy="${baseY}" r="7" fill="white"/>
          <circle cx="${rightX}" cy="${baseY}" r="7" fill="white"/>
          <circle cx="${leftX + 1}" cy="${baseY}" r="4" fill="#1a1a1a"/>
          <circle cx="${rightX + 1}" cy="${baseY}" r="4" fill="#1a1a1a"/>
          <circle cx="${leftX + 2}" cy="${baseY - 1}" r="1.5" fill="white"/>
          <circle cx="${rightX + 2}" cy="${baseY - 1}" r="1.5" fill="white"/>
        `;
      case 'oval':
        return `
          <ellipse cx="${leftX}" cy="${baseY}" rx="6" ry="8" fill="white"/>
          <ellipse cx="${rightX}" cy="${baseY}" rx="6" ry="8" fill="white"/>
          <ellipse cx="${leftX + 1}" cy="${baseY + 1}" rx="3" ry="4" fill="#1a1a1a"/>
          <ellipse cx="${rightX + 1}" cy="${baseY + 1}" rx="3" ry="4" fill="#1a1a1a"/>
          <circle cx="${leftX + 2}" cy="${baseY - 1}" r="1.5" fill="white"/>
          <circle cx="${rightX + 2}" cy="${baseY - 1}" r="1.5" fill="white"/>
        `;
      case 'dots':
        return `
          <circle cx="${leftX}" cy="${baseY}" r="4" fill="#1a1a1a"/>
          <circle cx="${rightX}" cy="${baseY}" r="4" fill="#1a1a1a"/>
          <circle cx="${leftX + 1}" cy="${baseY - 1}" r="1" fill="white"/>
          <circle cx="${rightX + 1}" cy="${baseY - 1}" r="1" fill="white"/>
        `;
      case 'anime':
        return `
          <ellipse cx="${leftX}" cy="${baseY}" rx="8" ry="10" fill="white"/>
          <ellipse cx="${rightX}" cy="${baseY}" rx="8" ry="10" fill="white"/>
          <ellipse cx="${leftX + 2}" cy="${baseY + 2}" rx="5" ry="6" fill="#1a1a1a"/>
          <ellipse cx="${rightX + 2}" cy="${baseY + 2}" rx="5" ry="6" fill="#1a1a1a"/>
          <ellipse cx="${leftX + 3}" cy="${baseY - 1}" rx="2" ry="3" fill="white"/>
          <ellipse cx="${rightX + 3}" cy="${baseY - 1}" rx="2" ry="3" fill="white"/>
          <circle cx="${leftX}" cy="${baseY + 4}" r="1" fill="white" opacity="0.5"/>
          <circle cx="${rightX}" cy="${baseY + 4}" r="1" fill="white" opacity="0.5"/>
        `;
      case 'tired':
        return `
          <ellipse cx="${leftX}" cy="${baseY + 2}" rx="6" ry="4" fill="white"/>
          <ellipse cx="${rightX}" cy="${baseY + 2}" rx="6" ry="4" fill="white"/>
          <ellipse cx="${leftX}" cy="${baseY + 3}" rx="3" ry="2" fill="#1a1a1a"/>
          <ellipse cx="${rightX}" cy="${baseY + 3}" rx="3" ry="2" fill="#1a1a1a"/>
          <path d="M ${leftX - 6} ${baseY - 3} Q ${leftX} ${baseY - 6} ${leftX + 6} ${baseY - 3}" stroke="#1a1a1a" stroke-width="2" fill="none"/>
          <path d="M ${rightX - 6} ${baseY - 3} Q ${rightX} ${baseY - 6} ${rightX + 6} ${baseY - 3}" stroke="#1a1a1a" stroke-width="2" fill="none"/>
        `;
      case 'glasses':
        return `
          <circle cx="${leftX}" cy="${baseY}" r="7" fill="white"/>
          <circle cx="${rightX}" cy="${baseY}" r="7" fill="white"/>
          <circle cx="${leftX + 1}" cy="${baseY}" r="3" fill="#1a1a1a"/>
          <circle cx="${rightX + 1}" cy="${baseY}" r="3" fill="#1a1a1a"/>
          <circle cx="${leftX}" cy="${baseY}" r="9" stroke="#1a1a1a" stroke-width="2" fill="none"/>
          <circle cx="${rightX}" cy="${baseY}" r="9" stroke="#1a1a1a" stroke-width="2" fill="none"/>
          <line x1="${leftX + 9}" y1="${baseY}" x2="${rightX - 9}" y2="${baseY}" stroke="#1a1a1a" stroke-width="2"/>
          <line x1="${leftX - 9}" y1="${baseY}" x2="${leftX - 14}" y2="${baseY - 2}" stroke="#1a1a1a" stroke-width="2"/>
          <line x1="${rightX + 9}" y1="${baseY}" x2="${rightX + 14}" y2="${baseY - 2}" stroke="#1a1a1a" stroke-width="2"/>
        `;
      case 'monocle':
        return `
          <circle cx="${leftX}" cy="${baseY}" r="6" fill="white"/>
          <circle cx="${rightX}" cy="${baseY}" r="6" fill="white"/>
          <circle cx="${leftX + 1}" cy="${baseY}" r="3" fill="#1a1a1a"/>
          <circle cx="${rightX + 1}" cy="${baseY}" r="3" fill="#1a1a1a"/>
          <circle cx="${rightX}" cy="${baseY}" r="9" stroke="${a.main}" stroke-width="2" fill="none"/>
          <line x1="${rightX}" y1="${baseY + 9}" x2="${rightX + 5}" y2="${baseY + 25}" stroke="${a.main}" stroke-width="1.5"/>
        `;
      default:
        return '';
    }
  }

  private renderMouth(face: FaceExpression, canType: CanType): string {
    const baseY = canType === 'stubby' ? 62 : canType === 'crushed' ? 65 : canType === 'tall' || canType === 'energy' ? 58 : 60;
    const cx = 50;

    switch (face) {
      case 'happy':
        return `
          <path d="M ${cx - 10} ${baseY} Q ${cx} ${baseY + 10} ${cx + 10} ${baseY}" stroke="#1a1a1a" stroke-width="2.5" fill="none" stroke-linecap="round"/>
        `;
      case 'chill':
        return `
          <line x1="${cx - 8}" y1="${baseY + 2}" x2="${cx + 8}" y2="${baseY + 2}" stroke="#1a1a1a" stroke-width="2.5" stroke-linecap="round"/>
        `;
      case 'sleepy':
        return `
          <path d="M ${cx - 6} ${baseY + 3} Q ${cx} ${baseY} ${cx + 6} ${baseY + 3}" stroke="#1a1a1a" stroke-width="2" fill="none" stroke-linecap="round"/>
          <text x="${cx + 15}" y="${baseY - 5}" font-size="8" fill="#1a1a1a" opacity="0.6">z</text>
          <text x="${cx + 20}" y="${baseY - 10}" font-size="6" fill="#1a1a1a" opacity="0.4">z</text>
        `;
      case 'angry':
        return `
          <path d="M ${cx - 8} ${baseY + 4} L ${cx} ${baseY} L ${cx + 8} ${baseY + 4}" stroke="#1a1a1a" stroke-width="2.5" fill="none" stroke-linecap="round"/>
        `;
      case 'smirk':
        return `
          <path d="M ${cx - 8} ${baseY + 2} Q ${cx + 2} ${baseY + 2} ${cx + 10} ${baseY - 2}" stroke="#1a1a1a" stroke-width="2.5" fill="none" stroke-linecap="round"/>
        `;
      case 'surprised':
        return `
          <ellipse cx="${cx}" cy="${baseY + 3}" rx="5" ry="6" fill="#1a1a1a"/>
          <ellipse cx="${cx}" cy="${baseY + 2}" rx="3" ry="3" fill="#4a1a1a"/>
        `;
      case 'nerd':
        return `
          <path d="M ${cx - 10} ${baseY} Q ${cx} ${baseY + 6} ${cx + 10} ${baseY}" stroke="#1a1a1a" stroke-width="2" fill="none" stroke-linecap="round"/>
          <rect x="${cx - 2}" y="${baseY + 1}" width="4" height="3" fill="white" rx="1"/>
        `;
      default:
        return '';
    }
  }

  private renderPullTab(tab: PullTabStyle, a: any, canType: CanType, id: string): string {
    const topY = canType === 'stubby' ? 25 : canType === 'tall' || canType === 'energy' ? 10 : 18;
    const cx = 50;

    switch (tab) {
      case 'classic':
        return `
          <ellipse cx="${cx}" cy="${topY}" rx="8" ry="3" fill="${a.main}"/>
          <ellipse cx="${cx}" cy="${topY}" rx="6" ry="2" fill="${a.dark}"/>
          <circle cx="${cx + 5}" cy="${topY - 4}" r="3" fill="${a.light}" stroke="${a.dark}" stroke-width="1"/>
        `;
      case 'bent':
        return `
          <ellipse cx="${cx}" cy="${topY}" rx="8" ry="3" fill="${a.main}"/>
          <ellipse cx="${cx}" cy="${topY}" rx="6" ry="2" fill="${a.dark}"/>
          <path d="M ${cx + 3} ${topY - 2} Q ${cx + 8} ${topY - 8} ${cx + 12} ${topY - 5}" stroke="${a.light}" stroke-width="2" fill="none"/>
          <circle cx="${cx + 12}" cy="${topY - 5}" r="2.5" fill="${a.light}" stroke="${a.dark}" stroke-width="1"/>
        `;
      case 'missing':
        return `
          <ellipse cx="${cx}" cy="${topY}" rx="8" ry="3" fill="${a.main}"/>
          <ellipse cx="${cx}" cy="${topY + 1}" rx="5" ry="2" fill="#1a1a1a" opacity="0.8"/>
        `;
      case 'straw':
        return `
          <ellipse cx="${cx}" cy="${topY}" rx="8" ry="3" fill="${a.main}"/>
          <ellipse cx="${cx}" cy="${topY + 1}" rx="4" ry="1.5" fill="#1a1a1a" opacity="0.6"/>
          <rect x="${cx - 2}" y="${topY - 25}" width="4" height="28" rx="2" fill="#FF6B6B"/>
          <rect x="${cx - 1.5}" y="${topY - 25}" width="1" height="28" fill="#FF8A8A" opacity="0.5"/>
        `;
      case 'bendy_straw':
        return `
          <ellipse cx="${cx}" cy="${topY}" rx="8" ry="3" fill="${a.main}"/>
          <ellipse cx="${cx}" cy="${topY + 1}" rx="4" ry="1.5" fill="#1a1a1a" opacity="0.6"/>
          <path d="M ${cx} ${topY} L ${cx} ${topY - 10} Q ${cx} ${topY - 15} ${cx + 10} ${topY - 18} L ${cx + 20} ${topY - 18}" stroke="#FF6B6B" stroke-width="4" fill="none" stroke-linecap="round"/>
          <path d="M ${cx} ${topY} L ${cx} ${topY - 10} Q ${cx} ${topY - 15} ${cx + 10} ${topY - 18} L ${cx + 20} ${topY - 18}" stroke="#FF8A8A" stroke-width="1" fill="none" stroke-linecap="round" opacity="0.5"/>
        `;
      case 'none':
      default:
        return `
          <ellipse cx="${cx}" cy="${topY}" rx="8" ry="3" fill="${a.main}"/>
          <ellipse cx="${cx}" cy="${topY}" rx="6" ry="2" fill="${a.dark}" opacity="0.5"/>
        `;
    }
  }

  private renderAccessoryBack(accessory: Accessory, a: any, id: string): string {
    switch (accessory) {
      case 'headphones':
        return `
          <path d="M 20 35 Q 20 10 50 8 Q 80 10 80 35" stroke="#1a1a1a" stroke-width="4" fill="none"/>
        `;
      default:
        return '';
    }
  }

  private renderAccessoryFront(accessory: Accessory, a: any, canType: CanType, id: string): string {
    const topY = canType === 'stubby' ? 22 : canType === 'tall' || canType === 'energy' ? 5 : 15;

    switch (accessory) {
      case 'hat':
        return `
          <ellipse cx="50" cy="${topY + 5}" rx="30" ry="6" fill="#1a1a1a"/>
          <rect x="35" y="${topY - 15}" width="30" height="20" rx="2" fill="#1a1a1a"/>
          <rect x="38" y="${topY - 12}" width="24" height="3" fill="${a.main}"/>
        `;
      case 'headphones':
        return `
          <ellipse cx="22" cy="40" rx="8" ry="10" fill="#1a1a1a"/>
          <ellipse cx="22" cy="40" rx="5" ry="7" fill="#333"/>
          <ellipse cx="78" cy="40" rx="8" ry="10" fill="#1a1a1a"/>
          <ellipse cx="78" cy="40" rx="5" ry="7" fill="#333"/>
        `;
      case 'bowtie':
        return `
          <polygon points="40,72 50,75 60,72 60,78 50,75 40,78" fill="${a.main}"/>
          <circle cx="50" cy="75" r="3" fill="${a.light}"/>
        `;
      case 'bandana':
        return `
          <path d="M 25 ${topY + 12} Q 50 ${topY + 8} 75 ${topY + 12}" stroke="${a.main}" stroke-width="6" fill="none"/>
          <path d="M 75 ${topY + 12} L 82 ${topY + 20} L 78 ${topY + 25}" stroke="${a.main}" stroke-width="4" fill="none"/>
        `;
      case 'crown':
        return `
          <polygon points="30,${topY + 5} 35,${topY - 8} 42,${topY} 50,${topY - 12} 58,${topY} 65,${topY - 8} 70,${topY + 5}" fill="#FFD700" stroke="#FFA000" stroke-width="1"/>
          <circle cx="35" cy="${topY - 5}" r="2" fill="#FF6B6B"/>
          <circle cx="50" cy="${topY - 9}" r="2" fill="#4FC3F7"/>
          <circle cx="65" cy="${topY - 5}" r="2" fill="#81C784"/>
        `;
      case 'flower':
        return `
          <g transform="translate(70, ${topY})">
            <circle cx="0" cy="-6" r="4" fill="#FF80AB"/>
            <circle cx="5" cy="-2" r="4" fill="#FF80AB"/>
            <circle cx="3" cy="4" r="4" fill="#FF80AB"/>
            <circle cx="-3" cy="4" r="4" fill="#FF80AB"/>
            <circle cx="-5" cy="-2" r="4" fill="#FF80AB"/>
            <circle cx="0" cy="0" r="3" fill="#FFEB3B"/>
          </g>
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

  // Getter'lar
  getCanTypeOptions(): CanType[] { return [...this.canTypes]; }
  getFaceOptions(): FaceExpression[] { return [...this.faces]; }
  getEyeOptions(): EyeStyle[] { return [...this.eyeStyles]; }
  getPullTabOptions(): PullTabStyle[] { return [...this.pullTabs]; }
  getLabelOptions(): LabelStyle[] { return [...this.labels]; }
  getAccessoryOptions(): Accessory[] { return [...this.accessories]; }
  getColorOptions(): CanColor[] { return [...this.colors]; }
}
