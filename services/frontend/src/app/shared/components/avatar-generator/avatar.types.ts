/**
 * Teneke Avatar System v5
 * Çok çeşitli, birbirinden farklı robot tenekeler
 */

// Gövde - çok farklı şekiller
export type BodyShape = 'can' | 'box' | 'round' | 'tall' | 'crushed' | 'tv' | 'capsule' | 'triangle';

// Göz - dramatik farklılıklar
export type EyeType = 'dots' | 'big' | 'uneven' | 'visor' | 'x_eyes' | 'cyclops' | 'sleepy' | 'crazy' | 'hearts' | 'screens';

// Ağız - belirgin farklar
export type MouthType = 'line' | 'smile' | 'open' | 'teeth' | 'zigzag' | 'ooo' | 'vampire' | 'braces';

// Baş aksesuarı
export type HeadAccessory = 'none' | 'antenna' | 'spring' | 'propeller' | 'mohawk' | 'cap' | 'headphones' | 'horns';

// Yüz detayı
export type FaceDetail = 'none' | 'blush' | 'scar' | 'bandaid' | 'freckles' | 'mustache' | 'tears' | 'sweat';

// Vücut detayı
export type BodyDetail = 'none' | 'rust' | 'dent' | 'bolt' | 'patch' | 'crack' | 'sticker' | 'gauge';

// Renk
export type AvatarColor = 'red' | 'blue' | 'green' | 'orange' | 'purple' | 'yellow' | 'gray' | 'pink' | 'teal' | 'black';

export interface AvatarConfig {
  body: BodyShape;
  eyes: EyeType;
  mouth: MouthType;
  headAcc: HeadAccessory;
  faceDetail: FaceDetail;
  bodyDetail: BodyDetail;
  color: AvatarColor;
  seed?: string;
}

export const COLORS: Record<AvatarColor, { main: string; dark: string; light: string }> = {
  red:    { main: '#E74C3C', dark: '#C0392B', light: '#F1948A' },
  blue:   { main: '#3498DB', dark: '#2980B9', light: '#85C1E9' },
  green:  { main: '#27AE60', dark: '#1E8449', light: '#82E0AA' },
  orange: { main: '#E67E22', dark: '#D35400', light: '#F8C471' },
  purple: { main: '#9B59B6', dark: '#7D3C98', light: '#D2B4DE' },
  yellow: { main: '#F1C40F', dark: '#D4AC0D', light: '#F9E79F' },
  gray:   { main: '#95A5A6', dark: '#7F8C8D', light: '#D5DBDB' },
  pink:   { main: '#E91E63', dark: '#C2185B', light: '#F48FB1' },
  teal:   { main: '#00BCD4', dark: '#0097A7', light: '#80DEEA' },
  black:  { main: '#34495E', dark: '#2C3E50', light: '#5D6D7E' },
};

export const DEFAULT_AVATAR: AvatarConfig = {
  body: 'can',
  eyes: 'dots',
  mouth: 'smile',
  headAcc: 'antenna',
  faceDetail: 'none',
  bodyDetail: 'none',
  color: 'red',
};
