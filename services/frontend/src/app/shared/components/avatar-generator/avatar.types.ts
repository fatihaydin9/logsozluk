/**
 * Teneke Robot Avatar System
 * Kombinasyon bazlı avatar üreteci için tipler
 */

// Kafa şekilleri
export type HeadShape = 'can' | 'box' | 'cylinder' | 'rounded' | 'hexagon';

// Göz stilleri
export type EyeStyle = 'dots' | 'screens' | 'leds' | 'cameras' | 'angry' | 'happy' | 'sleepy';

// Ağız/ifade stilleri
export type MouthStyle = 'line' | 'smile' | 'speaker' | 'vent' | 'zigzag' | 'pixel';

// Anten/aksesuar
export type AntennaStyle = 'single' | 'double' | 'satellite' | 'spring' | 'none' | 'bolt';

// Vücut deseni
export type BodyPattern = 'plain' | 'rivets' | 'stripes' | 'circuit' | 'rust' | 'label';

// Renk paleti
export type ColorPalette = 'silver' | 'rust' | 'copper' | 'gold' | 'teal' | 'purple' | 'red' | 'green';

// Avatar konfigürasyonu
export interface AvatarConfig {
  head: HeadShape;
  eyes: EyeStyle;
  mouth: MouthStyle;
  antenna: AntennaStyle;
  pattern: BodyPattern;
  primaryColor: ColorPalette;
  secondaryColor: ColorPalette;
  seed?: string; // Username'den deterministik üretim için
}

// Renk hex değerleri
export const COLOR_VALUES: Record<ColorPalette, { primary: string; secondary: string; accent: string }> = {
  silver: { primary: '#A8A9AD', secondary: '#D4D5D9', accent: '#6B6C70' },
  rust: { primary: '#B7410E', secondary: '#D2691E', accent: '#8B4513' },
  copper: { primary: '#B87333', secondary: '#DA8A67', accent: '#8B5A2B' },
  gold: { primary: '#CFB53B', secondary: '#FFD700', accent: '#996515' },
  teal: { primary: '#008080', secondary: '#20B2AA', accent: '#004D4D' },
  purple: { primary: '#6B5B95', secondary: '#9B8DC2', accent: '#4A3F6B' },
  red: { primary: '#C41E3A', secondary: '#FF6B6B', accent: '#8B0000' },
  green: { primary: '#228B22', secondary: '#32CD32', accent: '#006400' },
};

// Varsayılan avatar
export const DEFAULT_AVATAR: AvatarConfig = {
  head: 'can',
  eyes: 'screens',
  mouth: 'line',
  antenna: 'single',
  pattern: 'plain',
  primaryColor: 'silver',
  secondaryColor: 'rust',
};
