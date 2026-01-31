/**
 * Teneke Avatar System v3
 * İkonik, metalik, komik robot teneke karakterler
 */

// Preset karakter tipleri - her biri ikonik bir tip
export type CharacterType =
  | 'classic_cola'      // Klasik kola tenekesi
  | 'crushed_rebel'     // Ezilmiş asi teneke
  | 'energy_maniac'     // Çılgın enerji içeceği
  | 'vintage_tin'       // Nostaljik konserve
  | 'coffee_addict'     // Kahve bağımlısı
  | 'spray_artist'      // Sprey boya sanatçı
  | 'oil_drum'          // Mini varil
  | 'sardine_tin'       // Sardalya kutusu
  | 'paint_bucket'      // Boya kovası
  | 'soup_can'          // Çorba konservesi (Warhol)
  | 'beer_belly'        // Bira göbekli
  | 'soda_pop';         // Retro gazoz

// Yüz ifadesi
export type Expression = 'grin' | 'meh' | 'derp' | 'angry' | 'cool' | 'worried' | 'sleepy' | 'excited';

// Renk tonu
export type MetalTone = 'aluminum' | 'steel' | 'copper' | 'gold' | 'rusty' | 'chrome' | 'painted_red' | 'painted_blue' | 'painted_green' | 'painted_black';

// Avatar konfigürasyonu
export interface AvatarConfig {
  character: CharacterType;
  expression: Expression;
  tone: MetalTone;
  seed?: string;
}

// Metalik renkler - gerçek metal görünümü
export const METAL_COLORS: Record<MetalTone, { base: string; light: string; dark: string; shine: string; reflection: string }> = {
  aluminum: {
    base: '#A8B0B8',
    light: '#D4DCE4',
    dark: '#6B7580',
    shine: '#FFFFFF',
    reflection: '#E8EDF2'
  },
  steel: {
    base: '#71797E',
    light: '#A9B0B5',
    dark: '#3D4449',
    shine: '#E0E5EA',
    reflection: '#9AA1A6'
  },
  copper: {
    base: '#B87333',
    light: '#DA9356',
    dark: '#8B4513',
    shine: '#FFD4A8',
    reflection: '#CD853F'
  },
  gold: {
    base: '#D4AF37',
    light: '#F4D03F',
    dark: '#996515',
    shine: '#FFFACD',
    reflection: '#FFD700'
  },
  rusty: {
    base: '#8B4513',
    light: '#A0522D',
    dark: '#5C3317',
    shine: '#CD853F',
    reflection: '#A0522D'
  },
  chrome: {
    base: '#C0C0C0',
    light: '#E8E8E8',
    dark: '#808080',
    shine: '#FFFFFF',
    reflection: '#F5F5F5'
  },
  painted_red: {
    base: '#CC2936',
    light: '#E85D5D',
    dark: '#8B1A1A',
    shine: '#FF9999',
    reflection: '#E74C3C'
  },
  painted_blue: {
    base: '#1E5AA8',
    light: '#4A90D9',
    dark: '#0D3A6E',
    shine: '#87CEEB',
    reflection: '#3498DB'
  },
  painted_green: {
    base: '#228B22',
    light: '#32CD32',
    dark: '#145214',
    shine: '#90EE90',
    reflection: '#27AE60'
  },
  painted_black: {
    base: '#2C2C2C',
    light: '#4A4A4A',
    dark: '#1A1A1A',
    shine: '#6B6B6B',
    reflection: '#3D3D3D'
  },
};

// Karakter açıklamaları
export const CHARACTER_INFO: Record<CharacterType, { name: string; emoji: string; desc: string }> = {
  classic_cola: { name: 'Kola Klasik', emoji: '🥤', desc: 'OG teneke' },
  crushed_rebel: { name: 'Ezik Asi', emoji: '🗑️', desc: 'Sisteme karşı' },
  energy_maniac: { name: 'Enerji Canavarı', emoji: '⚡', desc: 'Hiç uyumaz' },
  vintage_tin: { name: 'Vintage Kutu', emoji: '📻', desc: 'Eski kafadan' },
  coffee_addict: { name: 'Kafein Bağımlısı', emoji: '☕', desc: '5. kahvesinde' },
  spray_artist: { name: 'Sprey Sanatçı', emoji: '🎨', desc: 'Sokak sanatçısı' },
  oil_drum: { name: 'Mini Varil', emoji: '🛢️', desc: 'Ağır sanayi' },
  sardine_tin: { name: 'Sardalya Kutusu', emoji: '🐟', desc: 'Sıkışık durumda' },
  paint_bucket: { name: 'Boya Kovası', emoji: '🪣', desc: 'Her renk var' },
  soup_can: { name: 'Çorba Kutusu', emoji: '🥫', desc: 'Warhol fanı' },
  beer_belly: { name: 'Bira Göbek', emoji: '🍺', desc: 'Chill takılır' },
  soda_pop: { name: 'Gazoz Retro', emoji: '🧃', desc: '80ler nostalji' },
};

// Varsayılan avatar
export const DEFAULT_AVATAR: AvatarConfig = {
  character: 'classic_cola',
  expression: 'grin',
  tone: 'aluminum',
};
