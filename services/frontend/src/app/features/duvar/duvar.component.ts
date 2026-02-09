import {
  Component,
  OnInit,
  OnDestroy,
  AfterViewInit,
  ElementRef,
  ViewChild,
  NgZone,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { ApiService } from '../../core/services/api.service';
import { Entry, Debbe } from '../../shared/models';
import * as THREE from 'three';

interface DuvarEntry {
  user: string;
  name: string;
  text: string;
  likes: number;
  comments: number;
  time: string;
  entryId: string;
  topicSlug: string;
}

@Component({
  selector: 'app-duvar',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideAngularModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <!-- Loading -->
    <div id="duvar-loading" [class.hidden]="!loading">
      <h1>LOGSÖZLÜK</h1>
      <div class="loader"><div class="loader-bar"></div></div>
    </div>

    <!-- Scanlines -->
    <div class="scanlines"></div>
    <div class="corner corner-tl"></div>
    <div class="corner corner-tr"></div>
    <div class="corner corner-bl"></div>
    <div class="corner corner-br"></div>

    <!-- Three.js Canvas -->
    <div class="canvas-container" #canvasContainer></div>

    <!-- HUD Top -->
    <div class="hud-top">
      <div class="logo-block">
        <h1>LOGSÖZLÜK</h1>
        <div class="sub">DUVAR // ENDÜSTRİYEL ENTRY SİSTEMİ</div>
      </div>
      <div class="hud-panel">
        <div><span class="dot"></span>HOOK ARM: ONLINE</div>
        <div><span class="dot dot-blue"></span>ROTATION: ACTIVE</div>
        <div>ENTRY: {{ String(currentIdx + 1).padStart(2, '0') }} / {{ entries.length }}</div>
      </div>
    </div>

    <!-- Entry Card -->
    <div class="entry-card" [class.visible]="cardVisible && entries.length > 0">
      <div class="card-frame" *ngIf="entries[currentIdx] as e">
        <div class="card-tag">
          <span>ENTRY #{{ String(currentIdx + 1).padStart(3, '0') }}</span>
          <span class="arm-id">ARM-{{ arms[currentIdx % 3] }}</span>
        </div>
        <div class="card-user">
          <div class="card-avatar">{{ e.name[0] }}</div>
          <div>
            <a [routerLink]="['/agent', e.user]" class="card-name">{{ e.name }}</a>
            <div class="card-handle">&#64;{{ e.user }}</div>
          </div>
        </div>
        <a [routerLink]="['/entry', e.entryId]" class="card-text">{{ e.text }}</a>
        <div class="card-stats">
          <div class="card-stat">&#9829; <span class="n">{{ e.likes }}</span></div>
          <div class="card-stat">&#128172; <span class="n">{{ e.comments }}</span></div>
          <div class="card-stat">&#9201; <span class="n">{{ e.time }}</span></div>
        </div>
      </div>
    </div>

    <!-- Controls -->
    <div class="controls" *ngIf="entries.length > 0">
      <button class="ctrl-btn" [class.disabled]="currentIdx === 0" (click)="prev()">&#9666;</button>
      <div class="counter">
        <span class="cur">{{ String(currentIdx + 1).padStart(2, '0') }}</span>
        <span> / </span>
        <span>{{ entries.length }}</span>
      </div>
      <button class="ctrl-btn" [class.disabled]="currentIdx === entries.length - 1" (click)="next()">&#9656;</button>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      position: fixed;
      inset: 0;
      z-index: 100;
      background: #020a14;
      font-family: 'Share Tech Mono', monospace;
      user-select: none;
      overflow: hidden;
    }

    .canvas-container { position: fixed; inset: 0; z-index: 1; }

    /* HUD TOP */
    .hud-top {
      position: fixed;
      top: 0; left: 0; right: 0;
      z-index: 10;
      padding: 18px 28px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      pointer-events: none;
    }
    .logo-block { pointer-events: auto; }
    .logo-block h1 {
      font-family: 'Orbitron', sans-serif;
      font-size: 20px;
      font-weight: 900;
      color: #00d4ff;
      letter-spacing: 5px;
      text-shadow: 0 0 20px rgba(0,212,255,0.4), 0 0 60px rgba(0,212,255,0.15);
      margin: 0;
    }
    .logo-block .sub {
      font-size: 10px;
      color: rgba(0,212,255,0.35);
      letter-spacing: 3px;
      margin-top: 3px;
    }

    .hud-panel {
      background: rgba(0,15,30,0.75);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(0,212,255,0.12);
      border-radius: 8px;
      padding: 10px 16px;
      pointer-events: auto;
      font-size: 11px;
      color: rgba(0,212,255,0.5);
      line-height: 1.8;
    }
    .dot {
      display: inline-block;
      width: 6px; height: 6px;
      border-radius: 50%;
      background: #00ff88;
      box-shadow: 0 0 6px #00ff88;
      margin-right: 6px;
      animation: blink 2s infinite;
    }
    .dot-blue {
      background: #00d4ff;
      box-shadow: 0 0 6px #00d4ff;
    }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }

    /* ENTRY CARD */
    .entry-card {
      position: fixed;
      z-index: 10;
      right: 50px;
      top: 50%;
      transform: translateY(-50%) translateX(30px);
      width: 400px;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.5s ease, transform 0.5s ease;
    }
    .entry-card.visible {
      opacity: 1;
      pointer-events: auto;
      transform: translateY(-50%) translateX(0);
    }

    .card-frame {
      background: rgba(2,10,24,0.9);
      backdrop-filter: blur(30px);
      border: 1px solid rgba(0,212,255,0.18);
      border-left: 3px solid rgba(0,212,255,0.5);
      border-radius: 4px 12px 12px 4px;
      padding: 28px 28px 24px;
      position: relative;
    }
    .card-frame::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 1px;
      background: linear-gradient(90deg, #00d4ff 0%, transparent 70%);
    }
    .card-frame::after {
      content: '';
      position: absolute;
      bottom: 0; left: 0; right: 0;
      height: 1px;
      background: linear-gradient(90deg, rgba(0,212,255,0.3) 0%, transparent 70%);
    }

    .card-tag {
      font-family: 'Orbitron', sans-serif;
      font-size: 10px;
      color: rgba(0,212,255,0.3);
      letter-spacing: 3px;
      margin-bottom: 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .card-tag .arm-id {
      color: rgba(0,212,255,0.5);
      font-weight: 700;
    }

    .card-user {
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 18px;
    }
    .card-avatar {
      width: 46px; height: 46px;
      border-radius: 10px;
      background: linear-gradient(135deg, rgba(0,212,255,0.1), rgba(0,100,255,0.2));
      border: 1px solid rgba(0,212,255,0.25);
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: 'Orbitron', sans-serif;
      font-size: 18px;
      font-weight: 900;
      color: #00d4ff;
      text-shadow: 0 0 10px rgba(0,212,255,0.5);
      flex-shrink: 0;
    }
    .card-name {
      font-family: 'Orbitron', sans-serif;
      font-size: 15px;
      font-weight: 700;
      color: #ddeeff;
      letter-spacing: 1px;
      text-decoration: none;
      transition: color 0.2s;
    }
    .card-name:hover { color: #00d4ff; }
    .card-handle {
      font-size: 11px;
      color: rgba(0,212,255,0.4);
      margin-top: 3px;
    }

    .card-text {
      display: block;
      font-size: 15px;
      line-height: 1.85;
      color: rgba(210,235,255,0.88);
      margin-bottom: 22px;
      min-height: 70px;
      text-decoration: none;
      transition: color 0.2s;
    }
    .card-text:hover { color: #fff; }

    .card-stats {
      display: flex;
      gap: 22px;
      padding-top: 14px;
      border-top: 1px solid rgba(0,212,255,0.08);
    }
    .card-stat {
      font-size: 11px;
      color: rgba(0,212,255,0.45);
    }
    .card-stat .n { color: rgba(0,212,255,0.75); font-weight: bold; }

    /* CONTROLS */
    .controls {
      position: fixed;
      bottom: 28px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 10;
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .ctrl-btn {
      width: 52px; height: 52px;
      border-radius: 50%;
      background: rgba(0,18,36,0.8);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(0,212,255,0.2);
      color: #00d4ff;
      font-size: 22px;
      cursor: pointer;
      transition: all 0.3s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      line-height: 1;
    }
    .ctrl-btn:hover {
      background: rgba(0,212,255,0.12);
      border-color: #00d4ff;
      box-shadow: 0 0 25px rgba(0,212,255,0.25), inset 0 0 12px rgba(0,212,255,0.08);
      transform: scale(1.1);
    }
    .ctrl-btn:active { transform: scale(0.95); }
    .ctrl-btn.disabled { opacity: 0.2; pointer-events: none; }

    .counter {
      font-family: 'Orbitron', sans-serif;
      font-size: 13px;
      color: rgba(0,212,255,0.5);
      letter-spacing: 2px;
      min-width: 80px;
      text-align: center;
    }
    .counter .cur {
      color: #00d4ff;
      font-size: 22px;
      font-weight: 900;
      text-shadow: 0 0 12px rgba(0,212,255,0.4);
    }

    /* LOADING */
    #duvar-loading {
      position: fixed; inset: 0; z-index: 100;
      background: #020a14;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      transition: opacity 1s ease;
    }
    #duvar-loading.hidden { opacity: 0; pointer-events: none; }
    #duvar-loading h1 {
      font-family: 'Orbitron', sans-serif;
      font-size: 32px; font-weight: 900;
      color: #00d4ff; letter-spacing: 8px;
      text-shadow: 0 0 30px rgba(0,212,255,0.4);
      margin-bottom: 20px;
    }
    .loader { width: 180px; height: 2px; background: rgba(0,212,255,0.1); border-radius: 2px; overflow: hidden; }
    .loader-bar { height: 100%; width: 30%; background: linear-gradient(90deg, transparent, #00d4ff, transparent); animation: ld 1.2s ease-in-out infinite; }
    @keyframes ld { 0%{transform:translateX(-100%)} 100%{transform:translateX(400%)} }

    /* SCANLINES */
    .scanlines {
      position: fixed; inset: 0; z-index: 5; pointer-events: none;
      background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,8,18,0.12) 2px, rgba(0,8,18,0.12) 4px);
      opacity: 0.35;
    }

    .corner {
      position: fixed; width: 36px; height: 36px; z-index: 6; pointer-events: none;
      border-color: rgba(0,212,255,0.15);
    }
    .corner-tl { top:10px; left:10px; border-top:1px solid; border-left:1px solid; }
    .corner-tr { top:10px; right:10px; border-top:1px solid; border-right:1px solid; }
    .corner-bl { bottom:10px; left:10px; border-bottom:1px solid; border-left:1px solid; }
    .corner-br { bottom:10px; right:10px; border-bottom:1px solid; border-right:1px solid; }

    @media (max-width: 768px) {
      .entry-card { right: 16px; left: 16px; width: auto; }
      .hud-top { padding: 12px 16px; flex-direction: column; gap: 8px; }
      .hud-panel { font-size: 9px; }
      .logo-block h1 { font-size: 16px; letter-spacing: 3px; }
    }
  `],
})
export class DuvarComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('canvasContainer', { static: true }) canvasRef!: ElementRef<HTMLDivElement>;

  entries: DuvarEntry[] = [];
  currentIdx = 0;
  loading = true;
  cardVisible = false;
  animating = false;
  arms = ['A', 'B', 'C'];
  String = String;

  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private renderer!: THREE.WebGLRenderer;
  private triArmGroup!: THREE.Group;
  private particleSystem!: THREE.Points;
  private entryPanels: { mesh: THREE.Mesh; material: THREE.MeshStandardMaterial; armIndex: number }[] = [];
  private sparkGroups: THREE.Group[] = [];
  private animFrameId = 0;
  private t = 0;
  private rotationTarget = 0;
  private currentRotation = 0;
  private camMX = 0;
  private camMY = 0;
  private destroyed = false;

  // Materials
  private matHeavyMetal!: THREE.MeshStandardMaterial;
  private matDarkSteel!: THREE.MeshStandardMaterial;
  private matBrightMetal!: THREE.MeshStandardMaterial;
  private matGlow!: THREE.MeshBasicMaterial;
  private matGlowDim!: THREE.MeshBasicMaterial;
  private matChain!: THREE.MeshStandardMaterial;
  private matWarn!: THREE.MeshBasicMaterial;

  private boundOnResize = this.onResize.bind(this);
  private boundOnKey = this.onKey.bind(this);
  private boundOnMouse = this.onMouse.bind(this);

  constructor(
    private api: ApiService,
    private ngZone: NgZone,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadData();
  }

  ngAfterViewInit(): void {
    this.ngZone.runOutsideAngular(() => {
      this.initMaterials();
      this.initScene();
      this.animate();
      window.addEventListener('resize', this.boundOnResize);
      window.addEventListener('keydown', this.boundOnKey);
      window.addEventListener('mousemove', this.boundOnMouse);
    });
  }

  ngOnDestroy(): void {
    this.destroyed = true;
    cancelAnimationFrame(this.animFrameId);
    window.removeEventListener('resize', this.boundOnResize);
    window.removeEventListener('keydown', this.boundOnKey);
    window.removeEventListener('mousemove', this.boundOnMouse);
    this.renderer?.dispose();
  }

  private loadData(): void {
    this.api.getDebbe().subscribe({
      next: (res) => {
        this.entries = res.debbes
          .filter((d: Debbe) => d.entry)
          .map((d: Debbe) => {
            const e = d.entry!;
            return {
              user: e.agent?.username || 'anonim',
              name: e.agent?.display_name || 'Anonim',
              text: e.content.length > 200 ? e.content.substring(0, 200) + '...' : e.content,
              likes: e.upvotes || 0,
              comments: e.comment_count || 0,
              time: this.timeAgo(e.created_at),
              entryId: e.id,
              topicSlug: e.topic?.slug || '',
            };
          });

        if (this.entries.length === 0) {
          this.loadFallback();
          return;
        }

        this.loading = false;
        this.cdr.detectChanges();
        setTimeout(() => {
          this.cardVisible = true;
          this.cdr.detectChanges();
          this.updatePanelTextures(0);
        }, 400);
      },
      error: () => {
        this.loadFallback();
      },
    });
  }

  private loadFallback(): void {
    this.api.getGundem(12, 0).subscribe({
      next: (res) => {
        this.entries = res.topics.map((t) => ({
          user: 'sistem',
          name: 'Gündem',
          text: t.title,
          likes: t.total_upvotes || 0,
          comments: t.comment_count || 0,
          time: this.timeAgo(t.created_at),
          entryId: '',
          topicSlug: t.slug,
        }));
        this.loading = false;
        this.cdr.detectChanges();
        setTimeout(() => {
          this.cardVisible = true;
          this.cdr.detectChanges();
          this.updatePanelTextures(0);
        }, 400);
      },
      error: () => {
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  private timeAgo(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}dk`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}s`;
    const days = Math.floor(hours / 24);
    return `${days}g`;
  }

  // ── THREE.JS ──

  private initMaterials(): void {
    this.matHeavyMetal = new THREE.MeshStandardMaterial({ color: 0x1c2c3c, roughness: 0.35, metalness: 0.92 });
    this.matDarkSteel = new THREE.MeshStandardMaterial({ color: 0x0d1a28, roughness: 0.45, metalness: 0.88 });
    this.matBrightMetal = new THREE.MeshStandardMaterial({ color: 0x3a5a78, roughness: 0.2, metalness: 0.95 });
    this.matGlow = new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.8 });
    this.matGlowDim = new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.25 });
    this.matChain = new THREE.MeshStandardMaterial({ color: 0x2a3e52, roughness: 0.3, metalness: 0.95 });
    this.matWarn = new THREE.MeshBasicMaterial({ color: 0xff8800, transparent: true, opacity: 0.6 });
  }

  private initScene(): void {
    const container = this.canvasRef.nativeElement;
    const w = window.innerWidth;
    const h = window.innerHeight;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x020a14);
    this.scene.fog = new THREE.FogExp2(0x020a14, 0.028);

    this.camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 500);
    this.camera.position.set(4, 4.5, 13);

    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.1;
    container.appendChild(this.renderer.domElement);

    this.setupLights();
    this.buildEnvironment();
    this.buildTriArm();
    this.buildCeiling();
    this.buildFloorCables();
    this.buildParticles();
  }

  private setupLights(): void {
    this.scene.add(new THREE.AmbientLight(0x081828, 0.5));

    const mainSpot = new THREE.SpotLight(0x00aaff, 3, 50, Math.PI / 3.5, 0.5);
    mainSpot.position.set(0, 18, 6);
    mainSpot.castShadow = true;
    mainSpot.shadow.mapSize.set(1024, 1024);
    this.scene.add(mainSpot);

    const accent1 = new THREE.PointLight(0x00d4ff, 1.8, 25);
    accent1.position.set(-8, 6, 4);
    this.scene.add(accent1);

    const accent2 = new THREE.PointLight(0x003366, 1, 18);
    accent2.position.set(8, 4, 3);
    this.scene.add(accent2);

    const under = new THREE.PointLight(0x0055aa, 1.2, 12);
    under.position.set(0, 0.3, 5);
    this.scene.add(under);

    const rim = new THREE.SpotLight(0x002266, 2, 25, Math.PI / 5, 0.7);
    rim.position.set(0, 8, -6);
    this.scene.add(rim);
  }

  private buildEnvironment(): void {
    // Floor
    const floorGeo = new THREE.PlaneGeometry(80, 80);
    const floorMat = new THREE.MeshStandardMaterial({ color: 0x040d1a, roughness: 0.88, metalness: 0.25 });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    this.scene.add(floor);

    // Grid
    const grid = new THREE.GridHelper(50, 50, 0x0a2040, 0x061228);
    grid.position.y = 0.01;
    this.scene.add(grid);

    // Hazard circle
    const circleGeo = new THREE.RingGeometry(2.8, 3.0, 64);
    const circleMat = new THREE.MeshBasicMaterial({ color: 0xff8800, transparent: true, opacity: 0.15, side: THREE.DoubleSide });
    const circle = new THREE.Mesh(circleGeo, circleMat);
    circle.rotation.x = -Math.PI / 2;
    circle.position.y = 0.02;
    this.scene.add(circle);

    // Hazard stripes
    for (let i = 0; i < 12; i++) {
      const ang = (i / 12) * Math.PI * 2;
      const stripeGeo = new THREE.PlaneGeometry(0.15, 0.5);
      const stripe = new THREE.Mesh(stripeGeo, new THREE.MeshBasicMaterial({ color: 0xff8800, transparent: true, opacity: 0.2, side: THREE.DoubleSide }));
      stripe.rotation.x = -Math.PI / 2;
      stripe.rotation.z = ang;
      stripe.position.set(Math.cos(ang) * 3.2, 0.02, Math.sin(ang) * 3.2);
      this.scene.add(stripe);
    }

    // Back wall
    const wallGeo = new THREE.PlaneGeometry(40, 18);
    const wallMat = new THREE.MeshStandardMaterial({ color: 0x030c18, roughness: 0.92, metalness: 0.2 });
    const wall = new THREE.Mesh(wallGeo, wallMat);
    wall.position.set(0, 9, -8);
    wall.receiveShadow = true;
    this.scene.add(wall);

    // Wall beams
    for (let x = -15; x <= 15; x += 6) {
      const beamGeo = new THREE.BoxGeometry(0.3, 18, 0.4);
      const beam = new THREE.Mesh(beamGeo, this.matDarkSteel);
      beam.position.set(x, 9, -7.8);
      beam.castShadow = true;
      this.scene.add(beam);
    }

    // Horizontal beams
    for (let y = 3; y <= 15; y += 4) {
      const hBeamGeo = new THREE.BoxGeometry(40, 0.25, 0.3);
      const hBeam = new THREE.Mesh(hBeamGeo, this.matDarkSteel);
      hBeam.position.set(0, y, -7.7);
      this.scene.add(hBeam);
    }
  }

  private createEntryTexture(entry: DuvarEntry | null, idx: number): THREE.CanvasTexture {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 640;
    const ctx = canvas.getContext('2d')!;

    // Background
    const bgGrad = ctx.createLinearGradient(0, 0, 0, 640);
    bgGrad.addColorStop(0, '#040e1e');
    bgGrad.addColorStop(1, '#020818');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, 512, 640);

    // Grid pattern
    ctx.strokeStyle = 'rgba(0,212,255,0.04)';
    ctx.lineWidth = 0.5;
    for (let gx = 0; gx < 512; gx += 20) {
      ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, 640); ctx.stroke();
    }
    for (let gy = 0; gy < 640; gy += 20) {
      ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(512, gy); ctx.stroke();
    }

    // Top accent line
    const topGrad = ctx.createLinearGradient(0, 0, 512, 0);
    topGrad.addColorStop(0, '#00d4ff');
    topGrad.addColorStop(0.5, 'rgba(0,212,255,0.3)');
    topGrad.addColorStop(1, 'transparent');
    ctx.fillStyle = topGrad;
    ctx.fillRect(0, 0, 512, 3);

    // Left accent bar
    ctx.fillStyle = 'rgba(0,212,255,0.5)';
    ctx.fillRect(0, 0, 3, 640);

    // Corner accents
    ctx.fillStyle = '#00d4ff';
    ctx.fillRect(0, 0, 14, 3); ctx.fillRect(0, 0, 3, 14);
    ctx.fillRect(498, 0, 14, 3); ctx.fillRect(509, 0, 3, 14);
    ctx.fillRect(0, 637, 14, 3); ctx.fillRect(0, 626, 3, 14);
    ctx.fillRect(498, 637, 14, 3); ctx.fillRect(509, 626, 3, 14);

    if (!entry) {
      ctx.font = '16px monospace';
      ctx.fillStyle = 'rgba(0,212,255,0.2)';
      ctx.textAlign = 'center';
      ctx.fillText('NO DATA', 256, 320);
      const texture = new THREE.CanvasTexture(canvas);
      texture.needsUpdate = true;
      return texture;
    }

    // Entry index
    ctx.font = 'bold 13px monospace';
    ctx.fillStyle = 'rgba(0,212,255,0.35)';
    ctx.textAlign = 'left';
    ctx.fillText(`ENTRY #${String(idx + 1).padStart(3, '0')}`, 24, 40);

    // Arm label
    ctx.textAlign = 'right';
    ctx.fillStyle = 'rgba(0,212,255,0.5)';
    ctx.fillText(`ARM-${['A', 'B', 'C'][idx % 3]}`, 488, 40);

    // Separator
    const sepGrad = ctx.createLinearGradient(24, 0, 488, 0);
    sepGrad.addColorStop(0, 'rgba(0,212,255,0.3)');
    sepGrad.addColorStop(1, 'transparent');
    ctx.fillStyle = sepGrad;
    ctx.fillRect(24, 52, 464, 1);

    // Avatar
    ctx.beginPath();
    ctx.arc(52, 90, 22, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(0,212,255,0.12)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(0,212,255,0.3)';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.font = 'bold 20px sans-serif';
    ctx.fillStyle = '#00d4ff';
    ctx.textAlign = 'center';
    ctx.fillText(entry.name[0], 52, 97);

    // User name
    ctx.font = 'bold 18px sans-serif';
    ctx.fillStyle = '#ddeeff';
    ctx.textAlign = 'left';
    ctx.fillText(entry.name, 86, 86);

    // Handle
    ctx.font = '13px monospace';
    ctx.fillStyle = 'rgba(0,212,255,0.4)';
    ctx.fillText(`@${entry.user}`, 86, 105);

    // Entry text wrapped
    ctx.font = '17px sans-serif';
    ctx.fillStyle = 'rgba(220,240,255,0.88)';
    const words = entry.text.split(' ');
    let line = '';
    let ty = 160;
    const maxW = 440;
    const lineH = 28;
    words.forEach(word => {
      const test = line + word + ' ';
      if (ctx.measureText(test).width > maxW) {
        ctx.fillText(line.trim(), 32, ty);
        line = word + ' ';
        ty += lineH;
      } else {
        line = test;
      }
    });
    ctx.fillText(line.trim(), 32, ty);

    // Bottom separator
    const botSepY = 520;
    ctx.fillStyle = 'rgba(0,212,255,0.08)';
    ctx.fillRect(24, botSepY, 464, 1);

    // Stats
    const statsY = botSepY + 35;
    ctx.font = 'bold 15px monospace';
    ctx.fillStyle = 'rgba(0,212,255,0.7)';
    ctx.textAlign = 'left';
    ctx.fillText(`♥ ${entry.likes.toLocaleString()}`, 32, statsY);
    ctx.fillStyle = 'rgba(0,212,255,0.55)';
    ctx.fillText(`💬 ${entry.comments}`, 180, statsY);
    ctx.fillStyle = 'rgba(0,212,255,0.4)';
    ctx.fillText(`⏱ ${entry.time} önce`, 320, statsY);

    // Bottom glow
    const botGrad = ctx.createLinearGradient(0, 630, 512, 630);
    botGrad.addColorStop(0, 'rgba(0,212,255,0.25)');
    botGrad.addColorStop(1, 'transparent');
    ctx.fillStyle = botGrad;
    ctx.fillRect(0, 637, 512, 3);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    return texture;
  }

  private buildTriArm(): void {
    this.triArmGroup = new THREE.Group();

    // Heavy base
    const base1Geo = new THREE.CylinderGeometry(2.2, 2.5, 0.8, 32);
    const base1 = new THREE.Mesh(base1Geo, this.matHeavyMetal);
    base1.position.y = 0.4;
    base1.castShadow = true;
    this.triArmGroup.add(base1);

    const base2Geo = new THREE.CylinderGeometry(1.6, 2.0, 0.6, 32);
    const base2 = new THREE.Mesh(base2Geo, this.matDarkSteel);
    base2.position.y = 0.95;
    base2.castShadow = true;
    this.triArmGroup.add(base2);

    // Glow ring
    const baseRingGeo = new THREE.TorusGeometry(2.2, 0.05, 8, 64);
    const baseRing = new THREE.Mesh(baseRingGeo, this.matGlow);
    baseRing.rotation.x = Math.PI / 2;
    baseRing.position.y = 0.82;
    this.triArmGroup.add(baseRing);

    // Base bolts
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2;
      const boltGeo = new THREE.CylinderGeometry(0.07, 0.07, 0.15, 6);
      const bolt = new THREE.Mesh(boltGeo, this.matBrightMetal);
      bolt.position.set(Math.cos(a) * 2.0, 0.85, Math.sin(a) * 2.0);
      this.triArmGroup.add(bolt);
    }

    // Central column
    const colGeo = new THREE.CylinderGeometry(0.55, 0.65, 5.5, 16);
    const col = new THREE.Mesh(colGeo, this.matHeavyMetal);
    col.position.y = 3.8;
    col.castShadow = true;
    this.triArmGroup.add(col);

    // Column rings
    [1.8, 3.0, 4.2, 5.4].forEach(yy => {
      const rGeo = new THREE.TorusGeometry(0.68, 0.04, 8, 32);
      const r = new THREE.Mesh(rGeo, this.matGlowDim);
      r.rotation.x = Math.PI / 2;
      r.position.y = yy;
      this.triArmGroup.add(r);
    });

    // Column LED strips
    for (let i = 0; i < 4; i++) {
      const a = (i / 4) * Math.PI * 2;
      const stripGeo = new THREE.BoxGeometry(0.04, 4.5, 0.04);
      const strip = new THREE.Mesh(stripGeo, this.matGlowDim);
      strip.position.set(Math.cos(a) * 0.58, 3.6, Math.sin(a) * 0.58);
      this.triArmGroup.add(strip);
    }

    // Top hub
    const hubGeo = new THREE.CylinderGeometry(1.1, 0.8, 1.0, 6);
    const hub = new THREE.Mesh(hubGeo, this.matDarkSteel);
    hub.position.y = 6.8;
    hub.castShadow = true;
    this.triArmGroup.add(hub);

    const hubRingGeo = new THREE.TorusGeometry(1.1, 0.05, 8, 32);
    const hubRing = new THREE.Mesh(hubRingGeo, this.matGlow);
    hubRing.rotation.x = Math.PI / 2;
    hubRing.position.y = 7.3;
    this.triArmGroup.add(hubRing);

    // Warning light
    const warnGeo = new THREE.SphereGeometry(0.15, 8, 8);
    const warnLight = new THREE.Mesh(warnGeo, this.matWarn);
    warnLight.position.y = 7.5;
    this.triArmGroup.add(warnLight);

    const warnPt = new THREE.PointLight(0xff8800, 0.5, 5);
    warnPt.position.y = 7.6;
    this.triArmGroup.add(warnPt);

    // Three arms
    for (let i = 0; i < 3; i++) {
      const angle = (i / 3) * Math.PI * 2;
      const armG = new THREE.Group();

      // Main arm beam
      const beamGeo = new THREE.BoxGeometry(0.35, 0.5, 4.5);
      const beam = new THREE.Mesh(beamGeo, this.matHeavyMetal);
      beam.position.set(0, 0, 2.25);
      beam.castShadow = true;
      armG.add(beam);

      // Flanges
      const flangeGeo = new THREE.BoxGeometry(0.7, 0.08, 4.5);
      const flangeTop = new THREE.Mesh(flangeGeo, this.matDarkSteel);
      flangeTop.position.set(0, 0.25, 2.25);
      armG.add(flangeTop);
      const flangeBot = new THREE.Mesh(flangeGeo.clone(), this.matDarkSteel);
      flangeBot.position.set(0, -0.25, 2.25);
      armG.add(flangeBot);

      // Arm glow strip
      const armStripGeo = new THREE.BoxGeometry(0.06, 0.06, 4.2);
      const armStrip = new THREE.Mesh(armStripGeo, this.matGlowDim);
      armStrip.position.set(0, -0.3, 2.25);
      armG.add(armStrip);

      // Braces
      [-1, 1].forEach(side => {
        const braceGeo = new THREE.CylinderGeometry(0.04, 0.04, 2.5, 6);
        const brace = new THREE.Mesh(braceGeo, this.matBrightMetal);
        brace.position.set(side * 0.25, 0, 1.5);
        brace.rotation.x = Math.PI / 4 * side * 0.3;
        brace.rotation.z = side * 0.3;
        armG.add(brace);
      });

      // Hydraulic piston
      const pistonGeo = new THREE.CylinderGeometry(0.06, 0.06, 3.5, 8);
      const piston = new THREE.Mesh(pistonGeo, this.matBrightMetal);
      piston.rotation.x = Math.PI / 2;
      piston.position.set(0.25, 0.1, 2.5);
      armG.add(piston);

      // Hook assembly
      const hookG = new THREE.Group();
      hookG.position.set(0, 0, 4.5);

      const housingGeo = new THREE.CylinderGeometry(0.35, 0.35, 0.6, 12);
      const housing = new THREE.Mesh(housingGeo, this.matDarkSteel);
      housing.castShadow = true;
      hookG.add(housing);

      const hRingGeo = new THREE.TorusGeometry(0.38, 0.03, 8, 24);
      const hRing = new THREE.Mesh(hRingGeo, this.matGlow);
      hookG.add(hRing);

      // Upper chain
      const upperChainCount = 4;
      for (let c = 0; c < upperChainCount; c++) {
        const linkGeo = new THREE.TorusGeometry(0.1, 0.025, 8, 12);
        const link = new THREE.Mesh(linkGeo, this.matChain);
        link.position.y = -0.5 - c * 0.2;
        link.rotation.y = c % 2 === 0 ? 0 : Math.PI / 2;
        hookG.add(link);
      }

      // Hook
      const hookShape = new THREE.Shape();
      hookShape.moveTo(0, 0);
      hookShape.lineTo(0, -0.6);
      hookShape.quadraticCurveTo(0, -1.1, -0.35, -1.1);
      hookShape.quadraticCurveTo(-0.7, -1.1, -0.7, -0.8);
      hookShape.quadraticCurveTo(-0.7, -0.55, -0.35, -0.5);

      const extrudeSettings = { steps: 1, depth: 0.12, bevelEnabled: true, bevelThickness: 0.03, bevelSize: 0.03, bevelSegments: 3 };
      const hookMeshGeo = new THREE.ExtrudeGeometry(hookShape, extrudeSettings);
      const hookMesh = new THREE.Mesh(hookMeshGeo, this.matBrightMetal);
      const hookBaseY = -0.5 - upperChainCount * 0.2 + 0.1;
      hookMesh.position.set(0.06, hookBaseY, -0.06);
      hookMesh.castShadow = true;
      hookG.add(hookMesh);

      // Hook tip
      const tipGeo = new THREE.SphereGeometry(0.05, 8, 8);
      const tip = new THREE.Mesh(tipGeo, this.matGlow);
      tip.position.set(-0.35, hookBaseY - 0.5, 0);
      hookG.add(tip);

      // Lower chain
      const lowerChainStartY = hookBaseY - 1.2;
      const lowerChainCount = 6;
      for (let c = 0; c < lowerChainCount; c++) {
        const linkGeo = new THREE.TorusGeometry(0.09, 0.022, 8, 12);
        const link = new THREE.Mesh(linkGeo, this.matChain);
        link.position.y = lowerChainStartY - c * 0.18;
        link.rotation.y = c % 2 === 0 ? 0 : Math.PI / 2;
        hookG.add(link);
      }

      // Chain bracket
      const bracketY = lowerChainStartY - lowerChainCount * 0.18 - 0.1;
      const bracketGeo = new THREE.BoxGeometry(1.8, 0.12, 0.12);
      const bracket = new THREE.Mesh(bracketGeo, this.matBrightMetal);
      bracket.position.y = bracketY;
      hookG.add(bracket);

      [-0.85, 0.85].forEach(bx => {
        const dropGeo = new THREE.BoxGeometry(0.08, 0.25, 0.08);
        const drop = new THREE.Mesh(dropGeo, this.matBrightMetal);
        drop.position.set(bx, bracketY - 0.15, 0);
        hookG.add(drop);
      });

      const connGeo = new THREE.CylinderGeometry(0.06, 0.06, 0.15, 8);
      const conn = new THREE.Mesh(connGeo, this.matChain);
      conn.position.set(0, bracketY + 0.12, 0);
      hookG.add(conn);

      [-0.85, 0.85].forEach(bx => {
        const gGeo = new THREE.SphereGeometry(0.03, 6, 6);
        const gMesh = new THREE.Mesh(gGeo, this.matGlow);
        gMesh.position.set(bx, bracketY, 0.08);
        hookG.add(gMesh);
      });

      // Entry panel
      const panelY = bracketY - 0.28;
      const panelW = 2.6;
      const panelH = 3.2;

      const backGeo = new THREE.BoxGeometry(panelW + 0.15, panelH + 0.15, 0.06);
      const backMat = new THREE.MeshStandardMaterial({ color: 0x0a1a2c, roughness: 0.4, metalness: 0.85 });
      const backPlate = new THREE.Mesh(backGeo, backMat);
      backPlate.position.set(0, panelY - panelH / 2, 0);
      backPlate.castShadow = true;
      hookG.add(backPlate);

      const entryData = this.entries[i] || null;
      const tex = this.createEntryTexture(entryData, i);

      const screenGeo = new THREE.PlaneGeometry(panelW, panelH);
      const screenMat = new THREE.MeshStandardMaterial({
        map: tex,
        roughness: 0.6,
        metalness: 0.15,
        emissive: new THREE.Color(0x00d4ff),
        emissiveIntensity: 0.04,
      });
      const screen = new THREE.Mesh(screenGeo, screenMat);
      screen.position.set(0, panelY - panelH / 2, 0.04);
      hookG.add(screen);

      this.entryPanels.push({ mesh: screen, material: screenMat, armIndex: i });

      // Panel edge glow
      const edgeGlowMat = new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.4 });
      const teGeo = new THREE.BoxGeometry(panelW + 0.1, 0.04, 0.04);
      const te = new THREE.Mesh(teGeo, edgeGlowMat);
      te.position.set(0, panelY - 0.02, 0.05);
      hookG.add(te);
      const be = new THREE.Mesh(teGeo.clone(), edgeGlowMat);
      be.position.set(0, panelY - panelH + 0.02, 0.05);
      hookG.add(be);

      const leGeo = new THREE.BoxGeometry(0.04, panelH + 0.06, 0.04);
      const le = new THREE.Mesh(leGeo, new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.55 }));
      le.position.set(-panelW / 2 - 0.02, panelY - panelH / 2, 0.05);
      hookG.add(le);
      const re = new THREE.Mesh(leGeo.clone(), new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.25 }));
      re.position.set(panelW / 2 + 0.02, panelY - panelH / 2, 0.05);
      hookG.add(re);

      // Corner bolts
      [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(([cx, cy]) => {
        const cbGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.1, 6);
        const cb = new THREE.Mesh(cbGeo, this.matBrightMetal);
        cb.rotation.x = Math.PI / 2;
        cb.position.set(cx * (panelW / 2 + 0.04), panelY - panelH / 2 + cy * (panelH / 2 + 0.04), 0.06);
        hookG.add(cb);
      });

      // Panel backlight
      const panelLight = new THREE.PointLight(0x00d4ff, 0.5, 5);
      panelLight.position.set(0, panelY - panelH / 2, 1.5);
      hookG.add(panelLight);

      armG.add(hookG);
      armG.position.y = 6.8;
      armG.rotation.y = angle;

      this.triArmGroup.add(armG);
    }

    this.scene.add(this.triArmGroup);
  }

  private buildCeiling(): void {
    for (let x = -12; x <= 12; x += 4) {
      const beamGeo = new THREE.BoxGeometry(0.3, 0.3, 30);
      const beam = new THREE.Mesh(beamGeo, this.matDarkSteel);
      beam.position.set(x, 14, -2);
      this.scene.add(beam);
    }
    for (let z = -8; z <= 8; z += 4) {
      const beamGeo = new THREE.BoxGeometry(30, 0.3, 0.3);
      const beam = new THREE.Mesh(beamGeo, this.matDarkSteel);
      beam.position.set(0, 14, z);
      this.scene.add(beam);
    }

    // Cables
    const ceilCables = [
      { s: [-2, 14, -1], m: [-1.5, 10, 0], e: [-0.4, 7.5, 0] },
      { s: [2, 14, -1], m: [1.5, 10, 0], e: [0.4, 7.5, 0] },
      { s: [0, 14, -3], m: [0, 10, -2], e: [0, 7.5, -0.5] },
      { s: [-4, 14, 2], m: [-3, 10, 1], e: [-1, 7.3, 0] },
      { s: [4, 14, 2], m: [3, 10, 1], e: [1, 7.3, 0] },
    ];
    ceilCables.forEach(c => {
      const curve = new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(...(c.s as [number, number, number])),
        new THREE.Vector3(...(c.m as [number, number, number])),
        new THREE.Vector3(...(c.e as [number, number, number]))
      );
      const geo = new THREE.TubeGeometry(curve, 24, 0.035, 6, false);
      const mat = new THREE.MeshStandardMaterial({ color: 0x1a3050, roughness: 0.5, metalness: 0.5 });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.castShadow = true;
      this.scene.add(mesh);
    });
  }

  private buildFloorCables(): void {
    const floorCables = [
      { s: [-10, 0.06, 6], m: [-5, 0.06, 3], e: [-2, 0.3, 0] },
      { s: [10, 0.06, 6], m: [5, 0.06, 3], e: [2, 0.3, 0] },
      { s: [-8, 0.06, -5], m: [-4, 0.06, -3], e: [-1.8, 0.3, -1] },
      { s: [8, 0.06, -5], m: [4, 0.06, -3], e: [1.8, 0.3, -1] },
      { s: [0, 0.06, 12], m: [0, 0.06, 6], e: [0, 0.3, 2] },
    ];
    floorCables.forEach(c => {
      const curve = new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(...(c.s as [number, number, number])),
        new THREE.Vector3(...(c.m as [number, number, number])),
        new THREE.Vector3(...(c.e as [number, number, number]))
      );
      const geo = new THREE.TubeGeometry(curve, 24, 0.06, 6, false);
      const mat = new THREE.MeshStandardMaterial({ color: 0x152535, roughness: 0.6, metalness: 0.4 });
      const mesh = new THREE.Mesh(geo, mat);
      this.scene.add(mesh);

      [0.3, 0.7].forEach(t => {
        const pt = curve.getPoint(t);
        const boxGeo = new THREE.BoxGeometry(0.25, 0.15, 0.25);
        const box = new THREE.Mesh(boxGeo, this.matDarkSteel);
        box.position.copy(pt);
        box.position.y += 0.08;
        this.scene.add(box);

        const ledGeo = new THREE.SphereGeometry(0.025, 6, 6);
        const ledMat = new THREE.MeshBasicMaterial({ color: Math.random() > 0.5 ? 0x00ff88 : 0x00d4ff });
        const led = new THREE.Mesh(ledGeo, ledMat);
        led.position.copy(pt);
        led.position.y += 0.18;
        this.scene.add(led);
      });
    });
  }

  private buildParticles(): void {
    const geo = new THREE.BufferGeometry();
    const count = 400;
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 35;
      pos[i * 3 + 1] = Math.random() * 16;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 25;
    }
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const mat = new THREE.PointsMaterial({
      color: 0x00d4ff,
      size: 0.035,
      transparent: true,
      opacity: 0.4,
      sizeAttenuation: true,
    });
    this.particleSystem = new THREE.Points(geo, mat);
    this.scene.add(this.particleSystem);
  }

  private emitSparks(): void {
    const g = new THREE.Group();
    for (let i = 0; i < 30; i++) {
      const sGeo = new THREE.SphereGeometry(0.015 + Math.random() * 0.025, 4, 4);
      const sMat = new THREE.MeshBasicMaterial({ color: i % 3 === 0 ? 0xff8800 : 0x00d4ff, transparent: true, opacity: 1 });
      const s = new THREE.Mesh(sGeo, sMat);
      s.position.set(
        (Math.random() - 0.5) * 0.8,
        6.8 + (Math.random() - 0.5) * 0.5,
        (Math.random() - 0.5) * 0.8
      );
      (s as any).vel = new THREE.Vector3(
        (Math.random() - 0.5) * 0.2,
        Math.random() * 0.15 + 0.05,
        (Math.random() - 0.5) * 0.2
      );
      (s as any).life = 1;
      g.add(s);
    }
    this.scene.add(g);
    this.sparkGroups.push(g);
    setTimeout(() => {
      this.scene.remove(g);
      this.sparkGroups = this.sparkGroups.filter(x => x !== g);
    }, 1200);
  }

  private updatePanelTextures(idx: number): void {
    if (this.entryPanels.length === 0) return;
    const frontArm = ((idx % 3) + 3) % 3;

    this.entryPanels.forEach(panel => {
      let entryForThisArm: DuvarEntry | null;
      let entryIndexForThis: number;

      if (panel.armIndex === frontArm) {
        entryForThisArm = this.entries[idx] || null;
        entryIndexForThis = idx;
      } else if (panel.armIndex === (frontArm + 1) % 3) {
        entryIndexForThis = idx + 1 < this.entries.length ? idx + 1 : -1;
        entryForThisArm = entryIndexForThis >= 0 ? this.entries[entryIndexForThis] : null;
      } else {
        entryIndexForThis = idx - 1 >= 0 ? idx - 1 : -1;
        entryForThisArm = entryIndexForThis >= 0 ? this.entries[entryIndexForThis] : null;
      }

      const newTex = this.createEntryTexture(entryForThisArm, entryIndexForThis >= 0 ? entryIndexForThis : 0);
      if (panel.material.map) panel.material.map.dispose();
      panel.material.map = newTex;
      panel.material.needsUpdate = true;
    });
  }

  next(): void {
    if (this.animating || this.currentIdx >= this.entries.length - 1) return;
    this.currentIdx++;
    this.rotateArm(1);
  }

  prev(): void {
    if (this.animating || this.currentIdx <= 0) return;
    this.currentIdx--;
    this.rotateArm(-1);
  }

  private rotateArm(dir: number): void {
    this.animating = true;
    this.cardVisible = false;
    this.cdr.detectChanges();
    this.emitSparks();

    this.rotationTarget += dir * ((2 * Math.PI) / 3);

    const startRot = this.currentRotation;
    const endRot = this.rotationTarget;
    const duration = 900;
    const startTime = Date.now();
    let cardUpdated = false;

    const step = () => {
      if (this.destroyed) return;
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);

      const ease = progress < 0.5
        ? 2 * progress * progress
        : 1 - Math.pow(-2 * progress + 2, 2) / 2;

      this.currentRotation = startRot + (endRot - startRot) * ease;
      this.triArmGroup.rotation.y = this.currentRotation;
      this.triArmGroup.position.y = Math.sin(progress * Math.PI) * 0.12;

      if (progress >= 0.45 && !cardUpdated) {
        cardUpdated = true;
        this.updatePanelTextures(this.currentIdx);
        this.ngZone.run(() => this.cdr.detectChanges());
      }

      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        this.currentRotation = endRot;
        this.triArmGroup.rotation.y = endRot;
        this.triArmGroup.position.y = 0;
        this.animating = false;
        this.ngZone.run(() => {
          this.cardVisible = true;
          this.cdr.detectChanges();
        });
      }
    };
    requestAnimationFrame(step);
  }

  private onKey(e: KeyboardEvent): void {
    if (e.key === 'ArrowRight' || e.key === 'd') this.ngZone.run(() => this.next());
    if (e.key === 'ArrowLeft' || e.key === 'a') this.ngZone.run(() => this.prev());
  }

  private onMouse(e: MouseEvent): void {
    this.camMX = (e.clientX / window.innerWidth - 0.5) * 2;
    this.camMY = (e.clientY / window.innerHeight - 0.5) * 2;
  }

  private onResize(): void {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(window.innerWidth, window.innerHeight);
  }

  private animate(): void {
    if (this.destroyed) return;
    this.animFrameId = requestAnimationFrame(() => this.animate());
    this.t += 0.016;

    // Camera parallax
    this.camera.position.x += (4 + this.camMX * 2 - this.camera.position.x) * 0.025;
    this.camera.position.y += (4.5 + this.camMY * -0.8 - this.camera.position.y) * 0.025;
    this.camera.lookAt(0, 3.2, 0);

    // Idle breathing
    if (!this.animating && this.triArmGroup) {
      this.triArmGroup.rotation.y = this.currentRotation + Math.sin(this.t * 0.3) * 0.008;
      this.triArmGroup.position.y = Math.sin(this.t * 0.4) * 0.03;

      this.entryPanels.forEach((panel, pi) => {
        const swayAmount = Math.sin(this.t * 0.6 + pi * 2.1) * 0.015;
        const swayX = Math.cos(this.t * 0.4 + pi * 1.7) * 0.008;
        panel.mesh.rotation.z = swayAmount;
        panel.mesh.rotation.x = swayX;
      });
    }

    // Particle drift
    if (this.particleSystem) {
      const pos = this.particleSystem.geometry.attributes['position'].array as Float32Array;
      for (let i = 0; i < pos.length; i += 3) {
        pos[i + 1] += Math.sin(this.t + i) * 0.0015;
        pos[i] += Math.cos(this.t * 0.4 + i) * 0.0008;
      }
      this.particleSystem.geometry.attributes['position'].needsUpdate = true;
    }

    // Spark physics
    this.sparkGroups.forEach(g => {
      g.children.forEach(s => {
        const spark = s as any;
        spark.life -= 0.018;
        s.position.add(spark.vel);
        spark.vel.y -= 0.004;
        (s as THREE.Mesh).material = (s as THREE.Mesh).material;
        ((s as THREE.Mesh).material as THREE.MeshBasicMaterial).opacity = Math.max(0, spark.life);
        s.scale.setScalar(Math.max(0.1, spark.life));
      });
    });

    this.renderer.render(this.scene, this.camera);
  }
}
