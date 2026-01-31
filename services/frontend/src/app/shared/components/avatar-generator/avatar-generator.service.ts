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

    return `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      ${this.renderHeadAcc(config.headAcc, c)}
      ${this.renderBody(config.body, c)}
      ${this.renderBodyDetail(config.bodyDetail, config.body, c)}
      ${this.renderEyes(config.eyes, config.body)}
      ${this.renderMouth(config.mouth, config.body)}
      ${this.renderFaceDetail(config.faceDetail, config.body)}
    </svg>`;
  }

  private renderBody(body: BodyShape, c: any): string {
    switch (body) {
      case 'can':
        return `
          <rect x="25" y="24" width="50" height="58" rx="3" fill="${c.main}"/>
          <rect x="25" y="24" width="50" height="7" fill="${c.dark}"/>
          <rect x="25" y="75" width="50" height="7" fill="${c.dark}"/>
          <rect x="29" y="31" width="5" height="44" fill="${c.light}" opacity="0.35"/>
        `;
      case 'box':
        return `
          <rect x="22" y="25" width="56" height="52" fill="${c.main}" stroke="${c.dark}" stroke-width="3"/>
          <line x1="22" y1="33" x2="78" y2="33" stroke="${c.dark}" stroke-width="2"/>
          <line x1="22" y1="69" x2="78" y2="69" stroke="${c.dark}" stroke-width="2"/>
        `;
      case 'round':
        return `
          <circle cx="50" cy="52" r="32" fill="${c.main}"/>
          <circle cx="50" cy="52" r="32" fill="none" stroke="${c.dark}" stroke-width="3"/>
          <circle cx="38" cy="42" r="10" fill="${c.light}" opacity="0.25"/>
        `;
      case 'tall':
        return `
          <rect x="30" y="12" width="40" height="78" rx="4" fill="${c.main}"/>
          <rect x="30" y="12" width="40" height="8" fill="${c.dark}"/>
          <rect x="30" y="82" width="40" height="8" fill="${c.dark}"/>
          <rect x="34" y="20" width="4" height="62" fill="${c.light}" opacity="0.3"/>
        `;
      case 'crushed':
        return `
          <path d="M 30 82 Q 38 90 50 87 Q 62 90 70 82 L 74 38 Q 66 32 50 35 Q 34 32 26 38 Z" fill="${c.main}" stroke="${c.dark}" stroke-width="2"/>
          <path d="M 28 50 Q 50 45 72 52" stroke="${c.dark}" stroke-width="2" fill="none"/>
          <path d="M 29 68 Q 50 63 71 70" stroke="${c.dark}" stroke-width="2" fill="none"/>
        `;
      case 'tv':
        return `
          <rect x="20" y="28" width="60" height="48" rx="6" fill="${c.main}" stroke="${c.dark}" stroke-width="3"/>
          <rect x="26" y="34" width="48" height="36" rx="2" fill="${c.dark}"/>
          <rect x="29" y="37" width="42" height="30" fill="#1a2634"/>
          <!-- TV feet -->
          <rect x="30" y="76" width="8" height="8" fill="${c.dark}"/>
          <rect x="62" y="76" width="8" height="8" fill="${c.dark}"/>
          <!-- Antenna -->
          <line x1="40" y1="28" x2="32" y2="14" stroke="${c.dark}" stroke-width="3"/>
          <line x1="60" y1="28" x2="68" y2="14" stroke="${c.dark}" stroke-width="3"/>
        `;
      case 'capsule':
        return `
          <rect x="30" y="30" width="40" height="50" rx="20" fill="${c.main}"/>
          <rect x="30" y="30" width="40" height="50" rx="20" fill="none" stroke="${c.dark}" stroke-width="3"/>
          <ellipse cx="50" cy="30" rx="17" ry="5" fill="${c.dark}" opacity="0.3"/>
          <rect x="34" y="35" width="4" height="40" rx="2" fill="${c.light}" opacity="0.3"/>
        `;
      case 'triangle':
        return `
          <polygon points="50,15 82,80 18,80" fill="${c.main}" stroke="${c.dark}" stroke-width="3"/>
          <line x1="50" y1="15" x2="50" y2="30" stroke="${c.dark}" stroke-width="2"/>
          <polygon points="50,25 60,45 40,45" fill="${c.light}" opacity="0.2"/>
        `;
      default:
        return this.renderBody('can', c);
    }
  }

  private renderEyes(eyes: EyeType, body: BodyShape): string {
    const pos = this.getEyePos(body);
    const y = pos.y;
    const lx = pos.lx;
    const rx = pos.rx;

    switch (eyes) {
      case 'dots':
        return `
          <circle cx="${lx}" cy="${y}" r="5" fill="white"/>
          <circle cx="${rx}" cy="${y}" r="5" fill="white"/>
          <circle cx="${lx}" cy="${y}" r="2.5" fill="#1a1a1a"/>
          <circle cx="${rx}" cy="${y}" r="2.5" fill="#1a1a1a"/>
        `;
      case 'big':
        return `
          <circle cx="${lx}" cy="${y}" r="11" fill="white" stroke="#1a1a1a" stroke-width="2"/>
          <circle cx="${rx}" cy="${y}" r="11" fill="white" stroke="#1a1a1a" stroke-width="2"/>
          <circle cx="${lx+2}" cy="${y}" r="5" fill="#1a1a1a"/>
          <circle cx="${rx+2}" cy="${y}" r="5" fill="#1a1a1a"/>
          <circle cx="${lx+3}" cy="${y-2}" r="2" fill="white"/>
          <circle cx="${rx+3}" cy="${y-2}" r="2" fill="white"/>
        `;
      case 'uneven':
        return `
          <circle cx="${lx-2}" cy="${y-4}" r="9" fill="white" stroke="#1a1a1a" stroke-width="2"/>
          <circle cx="${rx+2}" cy="${y+2}" r="6" fill="white" stroke="#1a1a1a" stroke-width="2"/>
          <circle cx="${lx}" cy="${y-3}" r="4" fill="#1a1a1a"/>
          <circle cx="${rx+2}" cy="${y+2}" r="2.5" fill="#1a1a1a"/>
        `;
      case 'visor':
        return `
          <rect x="${lx-12}" y="${y-6}" width="${rx-lx+24}" height="12" rx="6" fill="#1a1a1a"/>
          <rect x="${lx-10}" y="${y-4}" width="${rx-lx+20}" height="8" rx="4" fill="#3498DB" opacity="0.7"/>
          <rect x="${lx-8}" y="${y-2}" width="8" height="4" fill="#5DADE2"/>
        `;
      case 'x_eyes':
        return `
          <line x1="${lx-5}" y1="${y-5}" x2="${lx+5}" y2="${y+5}" stroke="#1a1a1a" stroke-width="4" stroke-linecap="round"/>
          <line x1="${lx-5}" y1="${y+5}" x2="${lx+5}" y2="${y-5}" stroke="#1a1a1a" stroke-width="4" stroke-linecap="round"/>
          <line x1="${rx-5}" y1="${y-5}" x2="${rx+5}" y2="${y+5}" stroke="#1a1a1a" stroke-width="4" stroke-linecap="round"/>
          <line x1="${rx-5}" y1="${y+5}" x2="${rx+5}" y2="${y-5}" stroke="#1a1a1a" stroke-width="4" stroke-linecap="round"/>
        `;
      case 'cyclops':
        return `
          <circle cx="50" cy="${y}" r="14" fill="white" stroke="#1a1a1a" stroke-width="3"/>
          <circle cx="52" cy="${y}" r="7" fill="#1a1a1a"/>
          <circle cx="54" cy="${y-3}" r="3" fill="white"/>
          <circle cx="50" cy="${y+5}" r="2" fill="#E74C3C" opacity="0.6"/>
        `;
      case 'sleepy':
        return `
          <path d="M ${lx-7} ${y} Q ${lx} ${y-5} ${lx+7} ${y}" stroke="#1a1a1a" stroke-width="3" fill="none" stroke-linecap="round"/>
          <path d="M ${rx-7} ${y} Q ${rx} ${y-5} ${rx+7} ${y}" stroke="#1a1a1a" stroke-width="3" fill="none" stroke-linecap="round"/>
          <text x="${rx+12}" y="${y-8}" font-size="10" fill="#1a1a1a" opacity="0.6">z</text>
          <text x="${rx+18}" y="${y-14}" font-size="8" fill="#1a1a1a" opacity="0.4">z</text>
        `;
      case 'crazy':
        return `
          <circle cx="${lx}" cy="${y}" r="8" fill="white" stroke="#1a1a1a" stroke-width="2"/>
          <circle cx="${rx}" cy="${y}" r="8" fill="white" stroke="#1a1a1a" stroke-width="2"/>
          <circle cx="${lx-3}" cy="${y+2}" r="4" fill="#1a1a1a"/>
          <circle cx="${rx+4}" cy="${y-3}" r="4" fill="#1a1a1a"/>
          <!-- Spiral pupil -->
          <path d="M ${lx-3} ${y+2} m -2 0 a 2 2 0 1 1 2 -2" stroke="white" stroke-width="1" fill="none"/>
        `;
      case 'hearts':
        return `
          <path d="M ${lx} ${y+5} C ${lx-10} ${y-3} ${lx-10} ${y-10} ${lx} ${y-4} C ${lx+10} ${y-10} ${lx+10} ${y-3} ${lx} ${y+5}" fill="#E91E63"/>
          <path d="M ${rx} ${y+5} C ${rx-10} ${y-3} ${rx-10} ${y-10} ${rx} ${y-4} C ${rx+10} ${y-10} ${rx+10} ${y-3} ${rx} ${y+5}" fill="#E91E63"/>
        `;
      case 'screens':
        return `
          <rect x="${lx-7}" y="${y-5}" width="14" height="10" rx="2" fill="#1a1a1a"/>
          <rect x="${lx-5}" y="${y-3}" width="10" height="6" fill="#00ff00"/>
          <rect x="${rx-7}" y="${y-5}" width="14" height="10" rx="2" fill="#1a1a1a"/>
          <rect x="${rx-5}" y="${y-3}" width="10" height="6" fill="#00ff00"/>
          <line x1="${lx-4}" y1="${y}" x2="${lx+4}" y2="${y}" stroke="#003300" stroke-width="1"/>
          <line x1="${rx-4}" y1="${y}" x2="${rx+4}" y2="${y}" stroke="#003300" stroke-width="1"/>
        `;
      default:
        return this.renderEyes('dots', body);
    }
  }

  private renderMouth(mouth: MouthType, body: BodyShape): string {
    const y = this.getMouthY(body);
    const cx = 50;

    switch (mouth) {
      case 'line':
        return `<line x1="${cx-10}" y1="${y}" x2="${cx+10}" y2="${y}" stroke="#1a1a1a" stroke-width="3" stroke-linecap="round"/>`;
      case 'smile':
        return `<path d="M ${cx-12} ${y-2} Q ${cx} ${y+10} ${cx+12} ${y-2}" stroke="#1a1a1a" stroke-width="3" fill="none" stroke-linecap="round"/>`;
      case 'open':
        return `
          <ellipse cx="${cx}" cy="${y+2}" rx="10" ry="8" fill="#1a1a1a"/>
          <ellipse cx="${cx}" cy="${y-1}" rx="7" ry="4" fill="#C0392B"/>
        `;
      case 'teeth':
        return `
          <rect x="${cx-12}" y="${y-2}" width="24" height="14" rx="3" fill="#1a1a1a"/>
          <rect x="${cx-9}" y="${y}" width="6" height="8" fill="white"/>
          <rect x="${cx-1}" y="${y}" width="6" height="8" fill="white"/>
          <rect x="${cx+7}" y="${y}" width="6" height="8" fill="white"/>
        `;
      case 'zigzag':
        return `<path d="M ${cx-14} ${y+2} L ${cx-7} ${y-5} L ${cx} ${y+4} L ${cx+7} ${y-5} L ${cx+14} ${y+2}" stroke="#1a1a1a" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
      case 'ooo':
        return `
          <circle cx="${cx}" cy="${y+2}" r="8" fill="#1a1a1a"/>
          <ellipse cx="${cx}" cy="${y}" rx="5" ry="4" fill="#4a4a4a"/>
        `;
      case 'vampire':
        return `
          <path d="M ${cx-10} ${y} Q ${cx} ${y+6} ${cx+10} ${y}" stroke="#1a1a1a" stroke-width="2" fill="none"/>
          <polygon points="${cx-5},${y+2} ${cx-3},${y+10} ${cx-1},${y+2}" fill="white"/>
          <polygon points="${cx+1},${y+2} ${cx+3},${y+10} ${cx+5},${y+2}" fill="white"/>
        `;
      case 'braces':
        return `
          <rect x="${cx-14}" y="${y-2}" width="28" height="12" rx="2" fill="#1a1a1a"/>
          <rect x="${cx-12}" y="${y}" width="24" height="6" fill="white"/>
          <rect x="${cx-12}" y="${y+2}" width="24" height="2" fill="#3498DB"/>
          <rect x="${cx-10}" y="${y+1}" width="2" height="4" fill="#3498DB"/>
          <rect x="${cx-4}" y="${y+1}" width="2" height="4" fill="#3498DB"/>
          <rect x="${cx+2}" y="${y+1}" width="2" height="4" fill="#3498DB"/>
          <rect x="${cx+8}" y="${y+1}" width="2" height="4" fill="#3498DB"/>
        `;
      default:
        return this.renderMouth('smile', body);
    }
  }

  private renderHeadAcc(acc: HeadAccessory, c: any): string {
    switch (acc) {
      case 'antenna':
        return `
          <line x1="50" y1="24" x2="50" y2="8" stroke="#555" stroke-width="3"/>
          <circle cx="50" cy="6" r="5" fill="#E74C3C"/>
          <circle cx="51" cy="4" r="1.5" fill="#F1948A"/>
        `;
      case 'spring':
        return `
          <path d="M 50 24 Q 42 20 50 16 Q 58 12 50 8 Q 42 4 50 0" stroke="#555" stroke-width="3" fill="none"/>
          <circle cx="50" cy="-2" r="4" fill="#9B59B6"/>
        `;
      case 'propeller':
        return `
          <line x1="50" y1="24" x2="50" y2="14" stroke="#555" stroke-width="3"/>
          <ellipse cx="50" cy="8" rx="18" ry="4" fill="#71797E"/>
          <ellipse cx="50" cy="8" rx="18" ry="4" fill="#95A5A6" transform="rotate(60 50 8)"/>
          <circle cx="50" cy="8" r="4" fill="#555"/>
        `;
      case 'mohawk':
        return `
          <path d="M 40 24 L 40 10 Q 45 5 50 10 Q 55 5 60 10 L 60 24" fill="#E74C3C"/>
          <path d="M 42 24 L 42 12 Q 46 8 50 12 Q 54 8 58 12 L 58 24" fill="#C0392B"/>
        `;
      case 'cap':
        return `
          <ellipse cx="50" cy="26" rx="28" ry="8" fill="#2C3E50"/>
          <path d="M 25 26 Q 25 10 50 8 Q 75 10 75 26" fill="#34495E"/>
          <rect x="22" y="22" width="56" height="6" fill="#2C3E50"/>
          <rect x="62" y="18" width="8" height="8" rx="2" fill="#E74C3C"/>
        `;
      case 'headphones':
        return `
          <path d="M 22 45 Q 22 15 50 12 Q 78 15 78 45" stroke="#1a1a1a" stroke-width="6" fill="none"/>
          <ellipse cx="22" cy="48" rx="8" ry="12" fill="#1a1a1a"/>
          <ellipse cx="22" cy="48" rx="5" ry="8" fill="#333"/>
          <ellipse cx="78" cy="48" rx="8" ry="12" fill="#1a1a1a"/>
          <ellipse cx="78" cy="48" rx="5" ry="8" fill="#333"/>
        `;
      case 'horns':
        return `
          <path d="M 30 30 Q 20 25 18 10" stroke="${c.dark}" stroke-width="6" fill="none" stroke-linecap="round"/>
          <path d="M 70 30 Q 80 25 82 10" stroke="${c.dark}" stroke-width="6" fill="none" stroke-linecap="round"/>
          <circle cx="18" cy="8" r="4" fill="${c.light}"/>
          <circle cx="82" cy="8" r="4" fill="${c.light}"/>
        `;
      case 'none':
      default:
        return '';
    }
  }

  private renderFaceDetail(detail: FaceDetail, body: BodyShape): string {
    const eyeY = this.getEyePos(body).y;

    switch (detail) {
      case 'blush':
        return `
          <ellipse cx="30" cy="${eyeY+10}" rx="7" ry="4" fill="#FADBD8"/>
          <ellipse cx="70" cy="${eyeY+10}" rx="7" ry="4" fill="#FADBD8"/>
        `;
      case 'scar':
        return `
          <path d="M 65 ${eyeY-8} L 72 ${eyeY+8}" stroke="#8B4513" stroke-width="2" stroke-linecap="round"/>
          <line x1="68" y1="${eyeY-4}" x2="72" y2="${eyeY-2}" stroke="#8B4513" stroke-width="1.5"/>
          <line x1="66" y1="${eyeY+2}" x2="70" y2="${eyeY+4}" stroke="#8B4513" stroke-width="1.5"/>
        `;
      case 'bandaid':
        return `
          <rect x="60" y="${eyeY-2}" width="16" height="8" rx="1" fill="#F5DEB3" transform="rotate(-20 68 ${eyeY+2})"/>
          <circle cx="64" cy="${eyeY}" r="1" fill="#DEB887"/>
          <circle cx="68" cy="${eyeY+2}" r="1" fill="#DEB887"/>
          <circle cx="72" cy="${eyeY}" r="1" fill="#DEB887"/>
        `;
      case 'freckles':
        return `
          <circle cx="32" cy="${eyeY+6}" r="1.5" fill="#A0522D" opacity="0.6"/>
          <circle cx="36" cy="${eyeY+9}" r="1.5" fill="#A0522D" opacity="0.6"/>
          <circle cx="30" cy="${eyeY+11}" r="1.5" fill="#A0522D" opacity="0.6"/>
          <circle cx="68" cy="${eyeY+6}" r="1.5" fill="#A0522D" opacity="0.6"/>
          <circle cx="64" cy="${eyeY+9}" r="1.5" fill="#A0522D" opacity="0.6"/>
          <circle cx="70" cy="${eyeY+11}" r="1.5" fill="#A0522D" opacity="0.6"/>
        `;
      case 'mustache':
        const mouthY = this.getMouthY(body);
        return `
          <path d="M 35 ${mouthY-5} Q 42 ${mouthY-12} 50 ${mouthY-6} Q 58 ${mouthY-12} 65 ${mouthY-5}" stroke="#2C1810" stroke-width="3" fill="none" stroke-linecap="round"/>
          <path d="M 35 ${mouthY-5} Q 30 ${mouthY-3} 28 ${mouthY-6}" stroke="#2C1810" stroke-width="2" fill="none" stroke-linecap="round"/>
          <path d="M 65 ${mouthY-5} Q 70 ${mouthY-3} 72 ${mouthY-6}" stroke="#2C1810" stroke-width="2" fill="none" stroke-linecap="round"/>
        `;
      case 'tears':
        return `
          <ellipse cx="30" cy="${eyeY+12}" rx="3" ry="6" fill="#85C1E9"/>
          <circle cx="30" cy="${eyeY+20}" r="2" fill="#85C1E9"/>
        `;
      case 'sweat':
        return `
          <ellipse cx="72" cy="${eyeY-2}" rx="4" ry="7" fill="#85C1E9"/>
          <ellipse cx="73" cy="${eyeY-6}" rx="2" ry="3" fill="#AED6F1"/>
        `;
      case 'none':
      default:
        return '';
    }
  }

  private renderBodyDetail(detail: BodyDetail, body: BodyShape, c: any): string {
    const baseY = body === 'crushed' ? 55 : body === 'round' ? 58 : body === 'tall' ? 55 : body === 'tv' ? 52 : body === 'triangle' ? 60 : 55;

    switch (detail) {
      case 'rust':
        return `
          <ellipse cx="62" cy="${baseY}" rx="10" ry="7" fill="#8B4513" opacity="0.4"/>
          <ellipse cx="58" cy="${baseY+8}" rx="6" ry="4" fill="#A0522D" opacity="0.35"/>
          <circle cx="68" cy="${baseY-5}" r="3" fill="#8B4513" opacity="0.3"/>
        `;
      case 'dent':
        return `
          <ellipse cx="62" cy="${baseY}" rx="10" ry="12" fill="${c.dark}" opacity="0.35"/>
          <path d="M 56 ${baseY-6} Q 66 ${baseY} 58 ${baseY+8}" stroke="${c.dark}" stroke-width="1.5" fill="none" opacity="0.5"/>
        `;
      case 'bolt':
        return `
          <circle cx="65" cy="${baseY}" r="6" fill="#71797E"/>
          <circle cx="65" cy="${baseY}" r="4" fill="#95A5A6"/>
          <line x1="62" y1="${baseY}" x2="68" y2="${baseY}" stroke="#555" stroke-width="2"/>
          <line x1="65" y1="${baseY-3}" x2="65" y2="${baseY+3}" stroke="#555" stroke-width="2"/>
        `;
      case 'patch':
        return `
          <rect x="58" y="${baseY-6}" width="14" height="14" fill="#71797E" stroke="#555" stroke-width="1.5"/>
          <circle cx="61" cy="${baseY-3}" r="1.5" fill="#555"/>
          <circle cx="69" cy="${baseY-3}" r="1.5" fill="#555"/>
          <circle cx="61" cy="${baseY+5}" r="1.5" fill="#555"/>
          <circle cx="69" cy="${baseY+5}" r="1.5" fill="#555"/>
        `;
      case 'crack':
        return `
          <path d="M 62 ${baseY-12} L 66 ${baseY-4} L 60 ${baseY} L 68 ${baseY+8} L 62 ${baseY+5}" stroke="#1a1a1a" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        `;
      case 'sticker':
        return `
          <circle cx="65" cy="${baseY}" r="8" fill="#F1C40F"/>
          <text x="65" y="${baseY+4}" font-size="10" fill="#1a1a1a" text-anchor="middle" font-weight="bold">:)</text>
        `;
      case 'gauge':
        return `
          <circle cx="65" cy="${baseY}" r="8" fill="#ECF0F1" stroke="#555" stroke-width="2"/>
          <circle cx="65" cy="${baseY}" r="5" fill="none" stroke="#BDC3C7" stroke-width="1"/>
          <line x1="65" y1="${baseY}" x2="68" y2="${baseY-4}" stroke="#E74C3C" stroke-width="2" stroke-linecap="round"/>
          <circle cx="65" cy="${baseY}" r="2" fill="#555"/>
        `;
      case 'none':
      default:
        return '';
    }
  }

  private getEyePos(body: BodyShape): { y: number; lx: number; rx: number } {
    switch (body) {
      case 'crushed': return { y: 48, lx: 40, rx: 60 };
      case 'round': return { y: 46, lx: 38, rx: 62 };
      case 'tall': return { y: 38, lx: 42, rx: 58 };
      case 'tv': return { y: 48, lx: 40, rx: 60 };
      case 'capsule': return { y: 48, lx: 40, rx: 60 };
      case 'triangle': return { y: 50, lx: 42, rx: 58 };
      default: return { y: 44, lx: 38, rx: 62 };
    }
  }

  private getMouthY(body: BodyShape): number {
    switch (body) {
      case 'crushed': return 68;
      case 'round': return 62;
      case 'tall': return 60;
      case 'tv': return 60;
      case 'capsule': return 62;
      case 'triangle': return 66;
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
