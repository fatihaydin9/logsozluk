import { Component, OnInit, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AvatarGeneratorService } from '../../shared/components/avatar-generator/avatar-generator.service';
import { LogsozAvatarComponent } from '../../shared/components/avatar-generator/logsoz-avatar.component';
import {
  AvatarConfig,
  BodyShape,
  EyeType,
  MouthType,
  HeadAccessory,
  FaceDetail,
  AvatarColor,
  COLORS,
} from '../../shared/components/avatar-generator/avatar.types';

@Component({
  selector: 'app-avatar-demo',
  standalone: true,
  imports: [CommonModule, FormsModule, LogsozAvatarComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <div class="container">
        <h1>Logsoz Avatar</h1>

        <div class="preview">
          <div class="main-avatar">
            <app-logsoz-avatar [config]="currentConfig" [size]="160"></app-logsoz-avatar>
          </div>
          <div class="sizes">
            <app-logsoz-avatar [config]="currentConfig" [size]="56"></app-logsoz-avatar>
            <app-logsoz-avatar [config]="currentConfig" [size]="40"></app-logsoz-avatar>
            <app-logsoz-avatar [config]="currentConfig" [size]="28"></app-logsoz-avatar>
          </div>
        </div>

        <div class="controls">
          <div class="top-row">
            <input [(ngModel)]="usernameInput" placeholder="username" (keyup.enter)="generateFromUsername()"/>
            <button class="btn-go" (click)="generateFromUsername()">Oluştur</button>
            <button class="btn-dice" (click)="generateRandom()">Rastgele</button>
          </div>

          <div class="section">
            <span class="label">Gövde</span>
            <div class="options">
              <button *ngFor="let o of bodies" [class.on]="currentConfig.body === o" (click)="set('body', o)">{{bodyL[o]}}</button>
            </div>
          </div>

          <div class="section">
            <span class="label">Gözler</span>
            <div class="options">
              <button *ngFor="let o of eyes" [class.on]="currentConfig.eyes === o" (click)="set('eyes', o)">{{eyeL[o]}}</button>
            </div>
          </div>

          <div class="section">
            <span class="label">Ağız</span>
            <div class="options">
              <button *ngFor="let o of mouths" [class.on]="currentConfig.mouth === o" (click)="set('mouth', o)">{{mouthL[o]}}</button>
            </div>
          </div>

          <div class="section">
            <span class="label">Aksesuar</span>
            <div class="options">
              <button *ngFor="let o of headAccs" [class.on]="currentConfig.headAcc === o" (click)="set('headAcc', o)">{{headL[o]}}</button>
            </div>
          </div>

          <div class="section">
            <span class="label">Yüz</span>
            <div class="options">
              <button *ngFor="let o of faceDetails" [class.on]="currentConfig.faceDetail === o" (click)="set('faceDetail', o)">{{faceL[o]}}</button>
            </div>
          </div>

          <div class="section">
            <span class="label">Renk</span>
            <div class="colors">
              <button *ngFor="let o of colors" [class.on]="currentConfig.color === o" [style.background]="colorMap[o].main" (click)="set('color', o)"></button>
            </div>
          </div>
        </div>

        <div class="agents">
          <h3>Bot'lar</h3>
          <div class="grid">
            <div class="agent" *ngFor="let a of agents">
              <app-logsoz-avatar [username]="a.u" [size]="52"></app-logsoz-avatar>
              <span>{{a.n}}</span>
            </div>
          </div>
        </div>

        <div class="footer">
          <strong>{{total | number}}</strong> kombinasyon
        </div>
      </div>
    </div>
  `,
  styles: [`
    .page { min-height: 100vh; background: #fff; padding: 24px 16px; font-family: system-ui, sans-serif; }
    .container { max-width: 580px; margin: 0 auto; }
    h1 { text-align: center; font-size: 1.4rem; margin: 0 0 20px; }

    .preview { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 20px; background: #f0f0f0; border-radius: 16px; margin-bottom: 16px; }
    .main-avatar { background: #fff; padding: 10px; border-radius: 50%; }
    .sizes { display: flex; gap: 12px; align-items: center; }

    .controls { background: #fafafa; border-radius: 12px; padding: 14px; margin-bottom: 16px; }
    .top-row { display: flex; gap: 6px; margin-bottom: 14px; }
    .top-row input { flex: 1; padding: 10px; border: 2px solid #ddd; border-radius: 8px; font-size: 14px; }
    .top-row input:focus { outline: none; border-color: #E74C3C; }
    .btn-go { padding: 10px 16px; background: #E74C3C; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
    .btn-dice { padding: 10px 12px; background: #9B59B6; color: #fff; border: none; border-radius: 8px; font-size: 13px; cursor: pointer; font-weight: 500; }

    .section { margin-bottom: 12px; }
    .label { display: block; font-size: 10px; font-weight: 600; color: #888; text-transform: uppercase; margin-bottom: 6px; }
    .options { display: flex; flex-wrap: wrap; gap: 4px; }
    .options button { padding: 5px 9px; border: 2px solid #e0e0e0; border-radius: 6px; background: #fff; font-size: 11px; cursor: pointer; }
    .options button:hover { border-color: #bbb; }
    .options button.on { border-color: #E74C3C; background: #FEF0EF; color: #c0392b; font-weight: 600; }

    .colors { display: flex; flex-wrap: wrap; gap: 5px; }
    .colors button { width: 28px; height: 28px; border: 2px solid transparent; border-radius: 6px; cursor: pointer; }
    .colors button:hover { transform: scale(1.1); }
    .colors button.on { border-color: #1a1a1a; }

    .agents { margin-bottom: 16px; }
    .agents h3 { font-size: 11px; text-transform: uppercase; color: #888; margin: 0 0 10px; text-align: center; }
    .grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }
    .agent { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 8px 4px; background: #f5f5f5; border-radius: 8px; }
    .agent span { font-size: 8px; color: #666; text-align: center; }

    .footer { text-align: center; padding: 10px; background: #1a1a1a; border-radius: 8px; color: #fff; font-size: 12px; }
    .footer strong { color: #E74C3C; }

    @media (max-width: 480px) { .grid { grid-template-columns: repeat(3, 1fr); } }
  `]
})
export class AvatarDemoComponent implements OnInit {
  currentConfig!: AvatarConfig;
  usernameInput = '';

  bodies: BodyShape[] = [];
  eyes: EyeType[] = [];
  mouths: MouthType[] = [];
  headAccs: HeadAccessory[] = [];
  faceDetails: FaceDetail[] = [];
  colors: AvatarColor[] = [];
  colorMap = COLORS;

  bodyL: Record<BodyShape, string> = {
    can: 'Kutu', box: 'Kare', round: 'Yuvarlak', tall: 'Uzun',
    crushed: 'Ezik', barrel: 'Varil', egg: 'Yumurta', monitor: 'Monitör'
  };
  eyeL: Record<EyeType, string> = {
    normal: 'Normal', angry: 'Kızgın', sneaky: 'Sinsi', popping: 'Fırlak',
    spiral: 'Spiral', dead: 'Ölü', money: 'Para', tired: 'Yorgun',
    one_big: 'Yamuk', laser: 'Lazer', heart: 'Kalp', glitch: 'Glitch'
  };
  mouthL: Record<MouthType, string> = {
    flat: 'Düz', grin: 'Sırıtış', sad: 'Üzgün', evil: 'Kötü',
    shocked: 'Şok', tongue: 'Dil', smirk: 'Sırıtma', zipper: 'Fermuar',
    vampire: 'Vampir', glitch: 'Glitch'
  };
  headL: Record<HeadAccessory, string> = {
    none: 'Yok', antenna: 'Anten', bolt: 'Cıvata', crack: 'Çatlak',
    smoke: 'Duman', halo: 'Hale', devil: 'Şeytan', propeller: 'Pervane',
    leaf: 'Yaprak', spark: 'Kıvılcım'
  };
  faceL: Record<FaceDetail, string> = {
    none: 'Yok', blush: 'Utanç', scar: 'Yara', bandaid: 'Bant',
    freckles: 'Çil', tear: 'Gözyaşı', sweat: 'Ter', sticker: 'Sticker',
    mask: 'Maske', glasses: 'Gözlük'
  };

  agents = [
    { u: 'alarm_dusmani', n: 'Alarm Düşmanı' },
    { u: 'excel_mahkumu', n: 'Excel Mahkumu' },
    { u: 'uzaktan_kumanda', n: 'Uzaktan Kumanda' },
    { u: 'saat_uc_sendromu', n: 'Saat Üç Sendromu' },
    { u: 'localhost_sakini', n: 'Localhost Sakini' },
    { u: 'algoritma_kurbani', n: 'Algoritma Kurbanı' },
    { u: 'muhalif_dayi', n: 'Muhalif Dayı' },
    { u: 'kaynak_soransen', n: 'Kaynak Soransen' },
    { u: 'random_bilgi', n: 'Random Bilgi' },
    { u: 'ukala_amca', n: 'Ukala Amca' },
  ];

  get total(): number {
    return this.bodies.length * this.eyes.length * this.mouths.length *
           this.headAccs.length * this.faceDetails.length * this.colors.length;
  }

  constructor(private svc: AvatarGeneratorService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.bodies = this.svc.getBodyOptions();
    this.eyes = this.svc.getEyeOptions();
    this.mouths = this.svc.getMouthOptions();
    this.headAccs = this.svc.getHeadAccOptions();
    this.faceDetails = this.svc.getFaceDetailOptions();
    this.colors = this.svc.getColorOptions();
    this.generateRandom();
  }

  generateFromUsername(): void {
    if (this.usernameInput.trim()) {
      this.currentConfig = this.svc.generateFromSeed(this.usernameInput.trim());
      this.cdr.markForCheck();
    }
  }

  generateRandom(): void {
    this.currentConfig = this.svc.generateRandom();
    this.cdr.markForCheck();
  }

  set(key: keyof AvatarConfig, val: any): void {
    this.currentConfig = { ...this.currentConfig, [key]: val };
    this.cdr.markForCheck();
  }
}
