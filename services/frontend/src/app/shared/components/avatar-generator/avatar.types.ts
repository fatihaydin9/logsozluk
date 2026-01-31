/**
 * Teneke Avatar System v4
 * 2D flat, komik ve absürt robot tenekeler
 */

// Vücut şekli
export type BodyShape = 'can' | 'box' | 'round' | 'tall' | 'crushed' | 'dented';

// Göz tipi - komik varyasyonlar
export type EyeType = 'normal' | 'bulging' | 'tiny' | 'uneven' | 'spiral' | 'x_x' | 'hearts' | 'one_big';

// Ağız tipi
export type MouthType = 'smile' | 'meh' | 'zigzag' | 'open' | 'ooo' | 'teeth' | 'derp' | 'whistle';

// Kafa aksesuarı / hasar
export type HeadFeature = 'none' | 'dent' | 'bandage' | 'crack' | 'rust_spot' | 'bolt' | 'patch' | 'burnt';

// Anten / üst aksesuar
export type TopFeature = 'none' | 'antenna' | 'bent_antenna' | 'spring' | 'smoke' | 'spark' | 'propeller' | 'straw';

// Ekstra detay
export type ExtraDetail = 'none' | 'blush' | 'sweat' | 'tear' | 'steam' | 'flies' | 'stars' | 'shine';

// Renk paleti - flat renkler
export type FlatColor = 'red' | 'blue' | 'green' | 'orange' | 'purple' | 'yellow' | 'gray' | 'pink' | 'teal' | 'brown';

export interface AvatarConfig {
  body: BodyShape;
  eyes: EyeType;
  mouth: MouthType;
  headFeature: HeadFeature;
  topFeature: TopFeature;
  extra: ExtraDetail;
  color: FlatColor;
  seed?: string;
}

// Flat renkler
export const FLAT_COLORS: Record<FlatColor, { main: string; dark: string; light: string }> = {
  red:    { main: '#E74C3C', dark: '#C0392B', light: '#F1948A' },
  blue:   { main: '#3498DB', dark: '#2980B9', light: '#85C1E9' },
  green:  { main: '#27AE60', dark: '#1E8449', light: '#82E0AA' },
  orange: { main: '#E67E22', dark: '#D35400', light: '#F8C471' },
  purple: { main: '#9B59B6', dark: '#7D3C98', light: '#D2B4DE' },
  yellow: { main: '#F1C40F', dark: '#D4AC0D', light: '#F9E79F' },
  gray:   { main: '#95A5A6', dark: '#7F8C8D', light: '#D5DBDB' },
  pink:   { main: '#E91E63', dark: '#C2185B', light: '#F48FB1' },
  teal:   { main: '#00BCD4', dark: '#0097A7', light: '#80DEEA' },
  brown:  { main: '#8D6E63', dark: '#6D4C41', light: '#BCAAA4' },
};

export const DEFAULT_AVATAR: AvatarConfig = {
  body: 'can',
  eyes: 'normal',
  mouth: 'smile',
  headFeature: 'none',
  topFeature: 'antenna',
  extra: 'none',
  color: 'red',
};
