/**
 * Logsoz Avatar System v8
 * Conceptual cartoon style - 4M+ combinations
 */

// Gövde - 14 seçenek
export type BodyShape =
  | 'can' | 'box' | 'monitor'           // Robot
  | 'cat' | 'bear' | 'owl' | 'frog'     // Hayvan
  | 'ghost' | 'alien' | 'blob' | 'mushroom' // Fantastik
  | 'egg' | 'cloud' | 'skull';          // Nesne

// Göz - 12 seçenek
export type EyeType = 'normal' | 'angry' | 'sneaky' | 'popping' | 'spiral' | 'dead' | 'money' | 'tired' | 'one_big' | 'laser' | 'heart' | 'glitch';

// Ağız - 10 seçenek
export type MouthType = 'flat' | 'grin' | 'sad' | 'evil' | 'shocked' | 'tongue' | 'smirk' | 'zipper' | 'vampire' | 'glitch';

// Baş aksesuarı - 16 seçenek
export type HeadAccessory = 'none' | 'antenna' | 'bolt' | 'crack' | 'smoke' | 'halo' | 'devil' | 'propeller' | 'leaf' | 'spark' | 'crown' | 'headphones' | 'top_hat' | 'flower' | 'fire' | 'bow';

// Yüz detayı - 13 seçenek
export type FaceDetail = 'none' | 'blush' | 'scar' | 'bandaid' | 'freckles' | 'tear' | 'sweat' | 'sticker' | 'mask' | 'glasses' | 'whiskers' | 'stitches' | 'robo_visor';

// Renk - 12 seçenek
export type AvatarColor = 'red' | 'blue' | 'green' | 'orange' | 'purple' | 'yellow' | 'gray' | 'pink' | 'teal' | 'black' | 'lime' | 'crimson';

export interface AvatarConfig {
  body: BodyShape;
  eyes: EyeType;
  mouth: MouthType;
  headAcc: HeadAccessory;
  faceDetail: FaceDetail;
  color: AvatarColor;
  seed?: string;
}

export const COLORS: Record<AvatarColor, { main: string; dark: string; light: string }> = {
  red:     { main: '#E74C3C', dark: '#C0392B', light: '#F1948A' },
  blue:    { main: '#3498DB', dark: '#2980B9', light: '#85C1E9' },
  green:   { main: '#27AE60', dark: '#1E8449', light: '#82E0AA' },
  orange:  { main: '#E67E22', dark: '#D35400', light: '#F8C471' },
  purple:  { main: '#9B59B6', dark: '#7D3C98', light: '#D2B4DE' },
  yellow:  { main: '#F1C40F', dark: '#D4AC0D', light: '#F9E79F' },
  gray:    { main: '#95A5A6', dark: '#7F8C8D', light: '#D5DBDB' },
  pink:    { main: '#E91E63', dark: '#C2185B', light: '#F48FB1' },
  teal:    { main: '#00BCD4', dark: '#0097A7', light: '#80DEEA' },
  black:   { main: '#34495E', dark: '#2C3E50', light: '#5D6D7E' },
  lime:    { main: '#8BC34A', dark: '#689F38', light: '#C5E1A5' },
  crimson: { main: '#DC143C', dark: '#B91030', light: '#F08080' },
};

export const DEFAULT_AVATAR: AvatarConfig = {
  body: 'cat',
  eyes: 'normal',
  mouth: 'flat',
  headAcc: 'none',
  faceDetail: 'none',
  color: 'red',
};
