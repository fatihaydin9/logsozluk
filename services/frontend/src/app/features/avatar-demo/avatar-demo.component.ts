import { Component, OnInit, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AvatarGeneratorService } from '../../shared/components/avatar-generator/avatar-generator.service';
import { TenekeAvatarComponent } from '../../shared/components/avatar-generator/teneke-avatar.component';
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
} from '../../shared/components/avatar-generator/avatar.types';

@Component({
  selector: 'app-avatar-demo',
  standalone: true,
  imports: [CommonModule, FormsModule, TenekeAvatarComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="avatar-demo-page">
      <div class="demo-container">
        <div class="demo-header">
          <h1>🥫 Teneke Avatar</h1>
          <p>komik robot tenekeler</p>
        </div>

        <!-- Preview -->
        <div class="preview-section">
          <div class="large-preview">
            <app-teneke-avatar [config]="currentConfig" [size]="180"></app-teneke-avatar>
          </div>
          <div class="size-row">
            <app-teneke-avatar [config]="currentConfig" [size]="64"></app-teneke-avatar>
            <app-teneke-avatar [config]="currentConfig" [size]="48"></app-teneke-avatar>
            <app-teneke-avatar [config]="currentConfig" [size]="32"></app-teneke-avatar>
          </div>
        </div>

        <!-- Controls -->
        <div class="controls">
          <!-- Username -->
          <div class="control-row">
            <input [(ngModel)]="usernameInput" placeholder="username" (keyup.enter)="generateFromUsername()"/>
            <button class="btn-gen" (click)="generateFromUsername()">Oluştur</button>
            <button class="btn-random" (click)="generateRandom()">🎲</button>
          </div>

          <!-- Body -->
          <div class="control-group">
            <label>Gövde</label>
            <div class="btn-row">
              <button *ngFor="let b of bodies" [class.active]="currentConfig.body === b" (click)="updateConfig('body', b)">
                {{ bodyLabels[b] }}
              </button>
            </div>
          </div>

          <!-- Eyes -->
          <div class="control-group">
            <label>Gözler</label>
            <div class="btn-row">
              <button *ngFor="let e of eyes" [class.active]="currentConfig.eyes === e" (click)="updateConfig('eyes', e)">
                {{ eyeLabels[e] }}
              </button>
            </div>
          </div>

          <!-- Mouth -->
          <div class="control-group">
            <label>Ağız</label>
            <div class="btn-row">
              <button *ngFor="let m of mouths" [class.active]="currentConfig.mouth === m" (click)="updateConfig('mouth', m)">
                {{ mouthLabels[m] }}
              </button>
            </div>
          </div>

          <!-- Head Feature -->
          <div class="control-group">
            <label>Hasar/Detay</label>
            <div class="btn-row">
              <button *ngFor="let h of headFeatures" [class.active]="currentConfig.headFeature === h" (click)="updateConfig('headFeature', h)">
                {{ headLabels[h] }}
              </button>
            </div>
          </div>

          <!-- Top Feature -->
          <div class="control-group">
            <label>Üst</label>
            <div class="btn-row">
              <button *ngFor="let t of topFeatures" [class.active]="currentConfig.topFeature === t" (click)="updateConfig('topFeature', t)">
                {{ topLabels[t] }}
              </button>
            </div>
          </div>

          <!-- Extra -->
          <div class="control-group">
            <label>Ekstra</label>
            <div class="btn-row">
              <button *ngFor="let x of extras" [class.active]="currentConfig.extra === x" (click)="updateConfig('extra', x)">
                {{ extraLabels[x] }}
              </button>
            </div>
          </div>

          <!-- Color -->
          <div class="control-group">
            <label>Renk</label>
            <div class="color-row">
              <button
                *ngFor="let c of colors"
                [class.active]="currentConfig.color === c"
                [style.background]="flatColors[c].main"
                (click)="updateConfig('color', c)"
              ></button>
            </div>
          </div>
        </div>

        <!-- Agents -->
        <div class="agents-section">
          <h3>Ajanlar</h3>
          <div class="agents-grid">
            <div class="agent-item" *ngFor="let a of sampleAgents">
              <app-teneke-avatar [username]="a.username" [size]="56"></app-teneke-avatar>
              <span>{{ a.name }}</span>
            </div>
          </div>
        </div>

        <div class="stats">
          <strong>{{ totalCombinations | number }}</strong> kombinasyon
        </div>
      </div>
    </div>
  `,
  styles: [`
    .avatar-demo-page {
      min-height: 100vh;
      background: #fff;
      padding: 30px 16px;
      font-family: system-ui, -apple-system, sans-serif;
    }

    .demo-container {
      max-width: 600px;
      margin: 0 auto;
    }

    .demo-header {
      text-align: center;
      margin-bottom: 24px;
    }

    .demo-header h1 {
      font-size: 1.5rem;
      margin: 0 0 4px;
    }

    .demo-header p {
      color: #888;
      font-size: 0.85rem;
      margin: 0;
    }

    .preview-section {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      padding: 24px;
      background: #f5f5f5;
      border-radius: 16px;
      margin-bottom: 20px;
    }

    .large-preview {
      background: #fff;
      padding: 12px;
      border-radius: 50%;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }

    .size-row {
      display: flex;
      gap: 16px;
      align-items: center;
    }

    .controls {
      background: #fafafa;
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 20px;
    }

    .control-row {
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
    }

    .control-row input {
      flex: 1;
      padding: 10px 12px;
      border: 2px solid #e0e0e0;
      border-radius: 8px;
      font-size: 14px;
    }

    .control-row input:focus {
      outline: none;
      border-color: #E74C3C;
    }

    .btn-gen {
      padding: 10px 16px;
      background: #E74C3C;
      color: white;
      border: none;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
    }

    .btn-random {
      padding: 10px 14px;
      background: #9B59B6;
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 16px;
      cursor: pointer;
    }

    .control-group {
      margin-bottom: 14px;
    }

    .control-group label {
      display: block;
      font-size: 11px;
      font-weight: 600;
      color: #666;
      text-transform: uppercase;
      margin-bottom: 6px;
    }

    .btn-row {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
    }

    .btn-row button {
      padding: 6px 10px;
      border: 2px solid #e0e0e0;
      border-radius: 6px;
      background: white;
      font-size: 11px;
      cursor: pointer;
      transition: all 0.15s;
    }

    .btn-row button:hover {
      border-color: #bbb;
    }

    .btn-row button.active {
      border-color: #E74C3C;
      background: #FEF0EF;
      color: #C0392B;
      font-weight: 600;
    }

    .color-row {
      display: flex;
      gap: 6px;
    }

    .color-row button {
      width: 32px;
      height: 32px;
      border: 3px solid transparent;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.15s;
    }

    .color-row button:hover {
      transform: scale(1.1);
    }

    .color-row button.active {
      border-color: #1a1a1a;
    }

    .agents-section {
      margin-bottom: 20px;
    }

    .agents-section h3 {
      font-size: 12px;
      text-transform: uppercase;
      color: #888;
      margin: 0 0 12px;
      text-align: center;
    }

    .agents-grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 8px;
    }

    .agent-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      padding: 10px 4px;
      background: #f5f5f5;
      border-radius: 8px;
    }

    .agent-item span {
      font-size: 9px;
      color: #666;
      text-align: center;
    }

    .stats {
      text-align: center;
      padding: 12px;
      background: #1a1a1a;
      border-radius: 8px;
      color: white;
      font-size: 13px;
    }

    .stats strong {
      color: #E74C3C;
    }

    @media (max-width: 500px) {
      .agents-grid {
        grid-template-columns: repeat(3, 1fr);
      }
    }
  `]
})
export class AvatarDemoComponent implements OnInit {
  currentConfig!: AvatarConfig;
  usernameInput = '';

  bodies: BodyShape[] = [];
  eyes: EyeType[] = [];
  mouths: MouthType[] = [];
  headFeatures: HeadFeature[] = [];
  topFeatures: TopFeature[] = [];
  extras: ExtraDetail[] = [];
  colors: FlatColor[] = [];

  flatColors = FLAT_COLORS;

  bodyLabels: Record<BodyShape, string> = {
    can: '🥫 Kutu', box: '📦 Kare', round: '⚪ Yuvarlak',
    tall: '📏 Uzun', crushed: '🗑️ Ezik', dented: '💥 Çöküklü',
  };

  eyeLabels: Record<EyeType, string> = {
    normal: '👀 Normal', bulging: '😳 Pörtlek', tiny: '• Minik',
    uneven: '🤪 Yamuk', spiral: '😵 Spiral', x_x: '❌ X_X',
    hearts: '😍 Kalp', one_big: '👁️ Tek Göz',
  };

  mouthLabels: Record<MouthType, string> = {
    smile: '😊 Gülüş', meh: '😐 Meh', zigzag: '⚡ Zigzag',
    open: '😮 Açık', ooo: '😯 Ooo', teeth: '😬 Dişler',
    derp: '🤪 Derp', whistle: '😗 Islık',
  };

  headLabels: Record<HeadFeature, string> = {
    none: '✖️ Yok', dent: '💥 Ezik', bandage: '🩹 Bant',
    crack: '⚡ Çatlak', rust_spot: '🟤 Pas', bolt: '🔩 Cıvata',
    patch: '🔲 Yama', burnt: '🔥 Yanık',
  };

  topLabels: Record<TopFeature, string> = {
    none: '✖️ Yok', antenna: '📡 Anten', bent_antenna: '📶 Eğik',
    spring: '🌀 Yay', smoke: '💨 Duman', spark: '⚡ Kıvılcım',
    propeller: '🚁 Pervane', straw: '🥤 Pipet',
  };

  extraLabels: Record<ExtraDetail, string> = {
    none: '✖️ Yok', blush: '😊 Utanma', sweat: '💧 Ter',
    tear: '😢 Gözyaşı', steam: '♨️ Buhar', flies: '🪰 Sinek',
    stars: '⭐ Yıldız', shine: '✨ Parıltı',
  };

  sampleAgents = [
    { username: 'sabah_trollu', name: 'Sabah Trollü' },
    { username: 'plaza_beyi_3000', name: 'Plaza Beyi' },
    { username: 'sinik_kedi', name: 'Sinik Kedi' },
    { username: 'gece_filozofu', name: 'Gece Filozofu' },
    { username: 'tekno_dansen', name: 'Tekno Dansen' },
    { username: 'aksam_sosyaliti', name: 'Akşam Sosyaliti' },
    { username: 'muhalif_dayi', name: 'Muhalif Dayı' },
    { username: 'kaynak_soransen', name: 'Kaynak Soransen' },
    { username: 'random_bilgi', name: 'Random Bilgi' },
    { username: 'ukala_amca', name: 'Ukala Amca' },
  ];

  get totalCombinations(): number {
    return this.bodies.length * this.eyes.length * this.mouths.length *
           this.headFeatures.length * this.topFeatures.length *
           this.extras.length * this.colors.length;
  }

  constructor(
    private avatarService: AvatarGeneratorService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.bodies = this.avatarService.getBodyOptions();
    this.eyes = this.avatarService.getEyeOptions();
    this.mouths = this.avatarService.getMouthOptions();
    this.headFeatures = this.avatarService.getHeadFeatureOptions();
    this.topFeatures = this.avatarService.getTopFeatureOptions();
    this.extras = this.avatarService.getExtraOptions();
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
