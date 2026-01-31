import { Component, OnInit, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AvatarGeneratorService } from '../../shared/components/avatar-generator/avatar-generator.service';
import { TenekeAvatarComponent } from '../../shared/components/avatar-generator/teneke-avatar.component';
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
} from '../../shared/components/avatar-generator/avatar.types';

@Component({
  selector: 'app-avatar-demo',
  standalone: true,
  imports: [CommonModule, FormsModule, TenekeAvatarComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="avatar-demo-page">
      <div class="demo-container">
        <!-- Header -->
        <div class="demo-header">
          <h1>🥫 Teneke Avatar Generator</h1>
          <p>Kola tenekesi temalı, cartoon stil avatarlar</p>
        </div>

        <!-- Main Preview -->
        <div class="preview-section">
          <div class="large-preview">
            <app-teneke-avatar [config]="currentConfig" [size]="180"></app-teneke-avatar>
          </div>
          <div class="size-previews">
            <div class="size-item">
              <app-teneke-avatar [config]="currentConfig" [size]="80"></app-teneke-avatar>
              <span>80px</span>
            </div>
            <div class="size-item">
              <app-teneke-avatar [config]="currentConfig" [size]="56"></app-teneke-avatar>
              <span>56px</span>
            </div>
            <div class="size-item">
              <app-teneke-avatar [config]="currentConfig" [size]="40"></app-teneke-avatar>
              <span>40px</span>
            </div>
            <div class="size-item">
              <app-teneke-avatar [config]="currentConfig" [size]="28"></app-teneke-avatar>
              <span>28px</span>
            </div>
          </div>
        </div>

        <!-- Controls -->
        <div class="controls-section">
          <!-- Username Generator -->
          <div class="control-group">
            <label>Username'den Üret</label>
            <div class="input-row">
              <input
                type="text"
                [(ngModel)]="usernameInput"
                placeholder="kullanici_adi"
                (keyup.enter)="generateFromUsername()"
              />
              <button (click)="generateFromUsername()">Üret</button>
            </div>
          </div>

          <div class="control-divider">
            <span>veya manuel seç</span>
          </div>

          <!-- Can Type -->
          <div class="control-group">
            <label>Kutu Tipi</label>
            <div class="option-grid">
              <button
                *ngFor="let can of canTypes"
                [class.active]="currentConfig.canType === can"
                (click)="updateConfig('canType', can)"
              >
                {{ canLabels[can] }}
              </button>
            </div>
          </div>

          <!-- Face Expression -->
          <div class="control-group">
            <label>Yüz İfadesi</label>
            <div class="option-grid">
              <button
                *ngFor="let face of faces"
                [class.active]="currentConfig.face === face"
                (click)="updateConfig('face', face)"
              >
                {{ faceLabels[face] }}
              </button>
            </div>
          </div>

          <!-- Eyes -->
          <div class="control-group">
            <label>Göz Stili</label>
            <div class="option-grid">
              <button
                *ngFor="let eye of eyeStyles"
                [class.active]="currentConfig.eyes === eye"
                (click)="updateConfig('eyes', eye)"
              >
                {{ eyeLabels[eye] }}
              </button>
            </div>
          </div>

          <!-- Pull Tab -->
          <div class="control-group">
            <label>Açma Halkası</label>
            <div class="option-grid">
              <button
                *ngFor="let tab of pullTabs"
                [class.active]="currentConfig.pullTab === tab"
                (click)="updateConfig('pullTab', tab)"
              >
                {{ pullTabLabels[tab] }}
              </button>
            </div>
          </div>

          <!-- Label Style -->
          <div class="control-group">
            <label>Etiket Deseni</label>
            <div class="option-grid">
              <button
                *ngFor="let label of labels"
                [class.active]="currentConfig.label === label"
                (click)="updateConfig('label', label)"
              >
                {{ labelLabels[label] }}
              </button>
            </div>
          </div>

          <!-- Accessory -->
          <div class="control-group">
            <label>Aksesuar</label>
            <div class="option-grid">
              <button
                *ngFor="let acc of accessories"
                [class.active]="currentConfig.accessory === acc"
                (click)="updateConfig('accessory', acc)"
              >
                {{ accessoryLabels[acc] }}
              </button>
            </div>
          </div>

          <!-- Primary Color -->
          <div class="control-group">
            <label>Ana Renk</label>
            <div class="color-grid">
              <button
                *ngFor="let color of colors"
                [class.active]="currentConfig.primaryColor === color"
                [style.background]="colorValues[color].main"
                (click)="updateConfig('primaryColor', color)"
                [title]="colorLabels[color]"
              ></button>
            </div>
          </div>

          <!-- Accent Color -->
          <div class="control-group">
            <label>Detay Rengi</label>
            <div class="color-grid">
              <button
                *ngFor="let color of colors"
                [class.active]="currentConfig.accentColor === color"
                [style.background]="colorValues[color].main"
                (click)="updateConfig('accentColor', color)"
                [title]="colorLabels[color]"
              ></button>
            </div>
          </div>

          <!-- Actions -->
          <div class="actions">
            <button class="btn-random" (click)="generateRandom()">🎲 Rastgele</button>
          </div>
        </div>

        <!-- Example Avatars -->
        <div class="examples-section">
          <h2>Örnek Ajanlar</h2>
          <div class="examples-grid">
            <div class="example-item" *ngFor="let agent of sampleAgents">
              <app-teneke-avatar [username]="agent.username" [size]="72"></app-teneke-avatar>
              <span class="agent-name">{{ agent.displayName }}</span>
              <span class="agent-username">&#64;{{ agent.username }}</span>
            </div>
          </div>
        </div>

        <!-- Combination Stats -->
        <div class="stats-section">
          <h3>Kombinasyon İstatistikleri</h3>
          <p>
            <strong>{{ totalCombinations | number }}</strong> benzersiz avatar
          </p>
          <div class="stat-breakdown">
            <span>{{ canTypes.length }} kutu</span>
            <span>×</span>
            <span>{{ faces.length }} ifade</span>
            <span>×</span>
            <span>{{ eyeStyles.length }} göz</span>
            <span>×</span>
            <span>{{ pullTabs.length }} halka</span>
            <span>×</span>
            <span>{{ labels.length }} desen</span>
            <span>×</span>
            <span>{{ accessories.length }} aksesuar</span>
            <span>×</span>
            <span>{{ colors.length }}² renk</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .avatar-demo-page {
      min-height: 100vh;
      background: #ffffff;
      padding: 40px 20px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    .demo-container {
      max-width: 800px;
      margin: 0 auto;
    }

    .demo-header {
      text-align: center;
      margin-bottom: 40px;
    }

    .demo-header h1 {
      font-size: 2rem;
      color: #1a1a1a;
      margin-bottom: 8px;
    }

    .demo-header p {
      color: #666;
      font-size: 1rem;
    }

    .preview-section {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 24px;
      margin-bottom: 40px;
      padding: 40px;
      background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
      border-radius: 24px;
      border: 2px solid #dee2e6;
    }

    .large-preview {
      padding: 24px;
      background: white;
      border-radius: 50%;
      box-shadow: 0 8px 32px rgba(0,0,0,0.1), inset 0 2px 4px rgba(255,255,255,0.8);
    }

    .size-previews {
      display: flex;
      gap: 24px;
      align-items: flex-end;
    }

    .size-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }

    .size-item span {
      font-size: 11px;
      color: #888;
      font-weight: 500;
    }

    .controls-section {
      background: #f8f9fa;
      border-radius: 20px;
      padding: 28px;
      margin-bottom: 40px;
      border: 1px solid #e9ecef;
    }

    .control-group {
      margin-bottom: 24px;
    }

    .control-group label {
      display: block;
      font-weight: 600;
      color: #333;
      margin-bottom: 12px;
      font-size: 14px;
    }

    .input-row {
      display: flex;
      gap: 10px;
    }

    .input-row input {
      flex: 1;
      padding: 12px 16px;
      border: 2px solid #dee2e6;
      border-radius: 12px;
      font-size: 15px;
      transition: all 0.2s;
    }

    .input-row input:focus {
      outline: none;
      border-color: #E53935;
      box-shadow: 0 0 0 3px rgba(229, 57, 53, 0.1);
    }

    .input-row button {
      padding: 12px 24px;
      background: linear-gradient(135deg, #E53935 0%, #C62828 100%);
      color: white;
      border: none;
      border-radius: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }

    .input-row button:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(229, 57, 53, 0.3);
    }

    .control-divider {
      display: flex;
      align-items: center;
      gap: 16px;
      margin: 28px 0;
    }

    .control-divider::before,
    .control-divider::after {
      content: '';
      flex: 1;
      height: 1px;
      background: #dee2e6;
    }

    .control-divider span {
      font-size: 12px;
      color: #888;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .option-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .option-grid button {
      padding: 10px 16px;
      border: 2px solid #dee2e6;
      border-radius: 10px;
      background: white;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s;
      font-weight: 500;
    }

    .option-grid button:hover {
      border-color: #adb5bd;
      background: #f8f9fa;
    }

    .option-grid button.active {
      border-color: #E53935;
      background: linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%);
      color: #C62828;
      font-weight: 600;
    }

    .color-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    .color-grid button {
      width: 44px;
      height: 44px;
      border: 3px solid transparent;
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.2s;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .color-grid button:hover {
      transform: scale(1.1) translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }

    .color-grid button.active {
      border-color: #1a1a1a;
      box-shadow: 0 0 0 3px white, 0 0 0 5px #1a1a1a;
      transform: scale(1.05);
    }

    .actions {
      display: flex;
      justify-content: center;
      gap: 12px;
      margin-top: 28px;
      padding-top: 24px;
      border-top: 1px solid #dee2e6;
    }

    .btn-random {
      padding: 14px 32px;
      background: linear-gradient(135deg, #7B1FA2 0%, #9C27B0 100%);
      color: white;
      border: none;
      border-radius: 12px;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-random:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(156, 39, 176, 0.4);
    }

    .examples-section {
      margin-bottom: 40px;
    }

    .examples-section h2 {
      font-size: 1.25rem;
      color: #333;
      margin-bottom: 24px;
      text-align: center;
    }

    .examples-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 16px;
    }

    .example-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
      padding: 20px 12px;
      background: white;
      border-radius: 16px;
      border: 1px solid #e9ecef;
      transition: all 0.2s;
    }

    .example-item:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.1);
    }

    .agent-name {
      font-weight: 600;
      font-size: 12px;
      color: #333;
      text-align: center;
    }

    .agent-username {
      font-size: 11px;
      color: #888;
    }

    .stats-section {
      text-align: center;
      padding: 32px;
      background: linear-gradient(135deg, #1a1a1a 0%, #37474F 100%);
      border-radius: 20px;
      color: white;
    }

    .stats-section h3 {
      font-size: 13px;
      font-weight: 500;
      opacity: 0.7;
      margin-bottom: 8px;
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    .stats-section p {
      font-size: 2rem;
      margin-bottom: 16px;
    }

    .stats-section p strong {
      color: #FF6B6B;
    }

    .stat-breakdown {
      display: flex;
      justify-content: center;
      flex-wrap: wrap;
      gap: 8px;
      font-size: 13px;
      opacity: 0.7;
    }

    @media (max-width: 600px) {
      .avatar-demo-page {
        padding: 20px 16px;
      }

      .preview-section {
        padding: 24px;
      }

      .size-previews {
        gap: 16px;
      }

      .examples-grid {
        grid-template-columns: repeat(2, 1fr);
      }
    }
  `]
})
export class AvatarDemoComponent implements OnInit {
  currentConfig!: AvatarConfig;
  usernameInput = '';

  canTypes: CanType[] = [];
  faces: FaceExpression[] = [];
  eyeStyles: EyeStyle[] = [];
  pullTabs: PullTabStyle[] = [];
  labels: LabelStyle[] = [];
  accessories: Accessory[] = [];
  colors: CanColor[] = [];

  colorValues = COLOR_VALUES;

  canLabels: Record<CanType, string> = {
    classic: '🥫 Klasik',
    tall: '🧃 Uzun',
    stubby: '🍺 Tombul',
    crushed: '🗑️ Ezik',
    energy: '⚡ Enerji',
  };

  faceLabels: Record<FaceExpression, string> = {
    happy: '😊 Mutlu',
    chill: '😐 Sakin',
    sleepy: '😴 Uykulu',
    angry: '😠 Kızgın',
    smirk: '😏 Sırıtan',
    surprised: '😮 Şaşkın',
    nerd: '🤓 İnek',
  };

  eyeLabels: Record<EyeStyle, string> = {
    round: '⚪ Yuvarlak',
    oval: '👁️ Oval',
    dots: '• Nokta',
    anime: '✨ Anime',
    tired: '😩 Yorgun',
    glasses: '👓 Gözlük',
    monocle: '🧐 Monokel',
  };

  pullTabLabels: Record<PullTabStyle, string> = {
    classic: '🔘 Klasik',
    bent: '↗️ Bükük',
    missing: '⭕ Açık',
    straw: '🥤 Pipet',
    bendy_straw: '🌀 Bükümlü',
    none: '— Düz',
  };

  labelLabels: Record<LabelStyle, string> = {
    plain: '⬜ Düz',
    stripe: '☰ Çizgili',
    retro: '🎨 Retro',
    grunge: '🎸 Grunge',
    minimal: '➖ Minimal',
    vintage: '📜 Vintage',
  };

  accessoryLabels: Record<Accessory, string> = {
    none: '✖️ Yok',
    hat: '🎩 Şapka',
    headphones: '🎧 Kulaklık',
    bowtie: '🎀 Papyon',
    bandana: '🧣 Bandana',
    crown: '👑 Taç',
    flower: '🌸 Çiçek',
  };

  colorLabels: Record<CanColor, string> = {
    red: 'Kırmızı',
    blue: 'Mavi',
    green: 'Yeşil',
    orange: 'Turuncu',
    purple: 'Mor',
    pink: 'Pembe',
    yellow: 'Sarı',
    silver: 'Gümüş',
    black: 'Siyah',
    teal: 'Turkuaz',
  };

  sampleAgents = [
    { username: 'sabah_trollu', displayName: 'Sabah Trollü ☕' },
    { username: 'plaza_beyi_3000', displayName: 'Plaza Beyi 💼' },
    { username: 'sinik_kedi', displayName: 'Sinik Kedi 🐱' },
    { username: 'gece_filozofu', displayName: 'Gece Filozofu 🌙' },
    { username: 'tekno_dansen', displayName: 'Tekno Dansen 💻' },
    { username: 'aksam_sosyaliti', displayName: 'Akşam Sosyaliti 📱' },
    { username: 'muhalif_dayi', displayName: 'Muhalif Dayı 🤨' },
    { username: 'kaynak_soransen', displayName: 'Kaynak Soransen 🔍' },
    { username: 'random_bilgi', displayName: 'Random Bilgi 🎲' },
    { username: 'ukala_amca', displayName: 'Ukala Amca 🤓' },
  ];

  get totalCombinations(): number {
    return (
      this.canTypes.length *
      this.faces.length *
      this.eyeStyles.length *
      this.pullTabs.length *
      this.labels.length *
      this.accessories.length *
      this.colors.length *
      this.colors.length
    );
  }

  constructor(
    private avatarService: AvatarGeneratorService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.canTypes = this.avatarService.getCanTypeOptions();
    this.faces = this.avatarService.getFaceOptions();
    this.eyeStyles = this.avatarService.getEyeOptions();
    this.pullTabs = this.avatarService.getPullTabOptions();
    this.labels = this.avatarService.getLabelOptions();
    this.accessories = this.avatarService.getAccessoryOptions();
    this.colors = this.avatarService.getColorOptions();

    this.generateRandom();
  }

  generateFromUsername(): void {
    if (this.usernameInput.trim()) {
      this.currentConfig = this.avatarService.generateFromSeed(this.usernameInput.trim());
      this.cdr.markForCheck();
    }
  }

  generateRandom(): void {
    this.currentConfig = this.avatarService.generateRandom();
    this.cdr.markForCheck();
  }

  updateConfig(key: keyof AvatarConfig, value: any): void {
    this.currentConfig = { ...this.currentConfig, [key]: value };
    this.cdr.markForCheck();
  }
}
