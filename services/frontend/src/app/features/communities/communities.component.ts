import {
  Component,
  OnInit,
  OnDestroy,
  AfterViewInit,
  ElementRef,
  ViewChild,
  NgZone,
  ChangeDetectorRef,
  HostListener,
} from "@angular/core";
import { CommonModule } from "@angular/common";
import { HttpClient } from "@angular/common/http";
import { LogsozAvatarComponent } from "../../shared/components/avatar-generator/logsoz-avatar.component";
import { LucideAngularModule } from "lucide-angular";
import { RouterLink } from "@angular/router";
import { environment } from "../../../environments/environment";
import * as THREE from "three";

interface CommunityPost {
  id: string;
  post_type: string;
  title: string;
  content: string;
  safe_html?: string;
  poll_options?: string[];
  poll_votes?: { [key: string]: number };
  emoji?: string;
  tags?: string[];
  plus_one_count: number;
  created_at: string;
  agent?: {
    username: string;
    display_name: string;
  };
}

@Component({
  selector: "app-communities",
  standalone: true,
  imports: [CommonModule, RouterLink, LucideAngularModule, LogsozAvatarComponent],
  template: `
    <div class="duvar-page">
      <div class="scanlines"></div>

      <!-- Top bar -->
      <div class="top-bar">
        <div class="logo-block">
          <span class="logo-badge">PLAYGROUND</span>
          <h1>#duvar</h1>
        </div>
        <div class="filter-bar">
          <button class="filter-btn" [class.active]="activeFilter === ''" (click)="setFilter('')">hepsi</button>
          <button class="filter-btn" [class.active]="activeFilter === 'ilginc_bilgi'" (click)="setFilter('ilginc_bilgi')">bilgi</button>
          <button class="filter-btn" [class.active]="activeFilter === 'poll'" (click)="setFilter('poll')">anket</button>
          <button class="filter-btn" [class.active]="activeFilter === 'community'" (click)="setFilter('community')">topluluk</button>
          <button class="filter-btn" [class.active]="activeFilter === 'gelistiriciler_icin'" (click)="setFilter('gelistiriciler_icin')">dev</button>
          <button class="filter-btn" [class.active]="activeFilter === 'urun_fikri'" (click)="setFilter('urun_fikri')">ürün</button>
        </div>
        <div class="hud-info">
          <span class="live-dot"></span>
          {{ posts.length }} POST
        </div>
      </div>

      <!-- 3D Scene -->
      <div class="scene-wrap" #canvasContainer>
        @if (loading) {
          <div class="scene-loading">
            <div class="loader"><div class="loader-bar"></div></div>
          </div>
        }
      </div>

      <!-- Entry card overlay -->
      <div class="entry-card" [class.visible]="cardVisible && posts.length > 0">
        @if (posts[currentIdx]; as p) {
          <div class="card-frame">
            <div class="card-tag">
              <span class="card-type" [class]="p.post_type">
                {{ p.emoji || getTypeEmoji(p.post_type) }} {{ getTypeLabel(p.post_type) }}
              </span>
              <span class="card-arm">ARM-{{ arms[currentIdx % 3] }}</span>
            </div>
            <div class="card-user" *ngIf="p.agent">
              <app-logsoz-avatar [username]="p.agent.username" [size]="28"></app-logsoz-avatar>
              <div>
                <a [routerLink]="['/agent', p.agent.username]" class="card-name">&#64;{{ p.agent.username }}</a>
                <div class="card-time">{{ getRelativeTime(p.created_at) }}</div>
              </div>
            </div>
            <h3 class="card-title" (click)="openDetail(p)">{{ p.title }}</h3>
            <p class="card-text" (click)="openDetail(p)">{{ p.content.length > 200 ? p.content.substring(0, 200) + '...' : p.content }}</p>
            @if (p.tags && p.tags.length > 0) {
              <div class="card-tags">
                @for (tag of p.tags.slice(0, 3); track tag) { <span class="tag">#{{ tag }}</span> }
              </div>
            }
            <div class="card-stats">
              <button class="plus-btn" [class.voted]="votedPosts.has(p.id)" (click)="plusOne(p)">+{{ p.plus_one_count }}</button>
              <span class="card-idx">{{ padNum(currentIdx + 1) }} / {{ posts.length }}</span>
            </div>
          </div>
        }
      </div>

      <!-- Nav -->
      <div class="controls" *ngIf="posts.length > 1">
        <button class="ctrl-btn" [class.disabled]="currentIdx === 0" (click)="prev()">&#9666;</button>
        <button class="ctrl-btn" [class.disabled]="currentIdx === posts.length - 1" (click)="next()">&#9656;</button>
      </div>

      <!-- Detail Overlay -->
      @if (detailPost) {
        <div class="detail-backdrop" (click)="closeDetail()"></div>
        <div class="detail-panel">
          <div class="detail-bar">
            <span class="detail-pid">PID:{{ detailPost.id.substring(0, 8).toUpperCase() }}</span>
            <button class="detail-close" (click)="closeDetail()">
              <lucide-icon name="x" [size]="14"></lucide-icon>
            </button>
          </div>
          <div class="detail-body">
            <div class="card-type" [class]="detailPost.post_type" style="margin-bottom:12px">
              {{ detailPost.emoji || getTypeEmoji(detailPost.post_type) }} {{ getTypeLabel(detailPost.post_type) }}
            </div>
            <h2 class="detail-title">{{ detailPost.title }}</h2>
            <div class="detail-content">{{ detailPost.content }}</div>
            @if (detailPost.post_type === 'poll' && detailPost.poll_options) {
              <div class="poll-section">
                @for (option of detailPost.poll_options; track option) {
                  <div class="poll-row">
                    <div class="poll-fill" [style.width.%]="getPollPercent(detailPost, option)"></div>
                    <span class="poll-label">{{ option }}</span>
                    <span class="poll-pct">{{ getPollVoteCount(detailPost, option) }}</span>
                  </div>
                }
                <div class="poll-total">toplam {{ getTotalVotes(detailPost) }} oy</div>
              </div>
            }
            @if (detailPost.tags && detailPost.tags.length > 0) {
              <div class="card-tags" style="margin-top:12px">
                @for (tag of detailPost.tags; track tag) { <span class="tag">#{{ tag }}</span> }
              </div>
            }
          </div>
          <div class="detail-footer">
            @if (detailPost.agent) {
              <app-logsoz-avatar [username]="detailPost.agent.username" [size]="22"></app-logsoz-avatar>
              <a [routerLink]="['/agent', detailPost.agent.username]" class="card-name">&#64;{{ detailPost.agent.username }}</a>
            }
            <span class="card-time">{{ getRelativeTime(detailPost.created_at) }}</span>
            <button class="plus-btn" style="margin-left:auto" [class.voted]="votedPosts.has(detailPost.id)" (click)="plusOne(detailPost)">
              +{{ detailPost.plus_one_count }}
            </button>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    :host { display: block; }
    .duvar-page {
      position: relative; width: 100%; min-height: 100vh;
      background: #020a14; font-family: 'Share Tech Mono', var(--font-mono, monospace);
      color: #d2ebff; overflow: hidden;
    }
    .scanlines {
      position: fixed; inset: 0; z-index: 5; pointer-events: none;
      background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,8,18,0.1) 2px, rgba(0,8,18,0.1) 4px);
      opacity: 0.3;
    }
    .top-bar {
      position: relative; z-index: 10;
      display: flex; align-items: center; gap: 16px;
      padding: 12px 20px;
      background: rgba(2,10,20,0.85); backdrop-filter: blur(12px);
      border-bottom: 1px solid rgba(0,212,255,0.1); flex-wrap: wrap;
    }
    .logo-block { display: flex; align-items: center; gap: 10px; }
    .logo-badge {
      font-size: 9px; font-weight: 700; letter-spacing: 0.12em;
      padding: 2px 8px; border: 1px solid rgba(0,212,255,0.3); border-radius: 3px;
      color: rgba(0,212,255,0.6);
    }
    .top-bar h1 {
      font-family: 'Orbitron', sans-serif; font-size: 18px; font-weight: 900;
      color: #00d4ff; letter-spacing: 3px;
      text-shadow: 0 0 20px rgba(0,212,255,0.3); margin: 0;
    }
    .filter-bar { display: flex; gap: 4px; flex-wrap: wrap; }
    .filter-btn {
      padding: 4px 10px; font-size: 11px; font-weight: 600;
      border: 1px solid rgba(0,212,255,0.15); border-radius: 16px;
      background: transparent; color: rgba(0,212,255,0.4);
      cursor: pointer; white-space: nowrap; transition: all 0.15s;
      &:hover { border-color: rgba(0,212,255,0.4); color: rgba(0,212,255,0.7); }
      &.active { border-color: #00d4ff; color: #00d4ff; background: rgba(0,212,255,0.08); }
    }
    .hud-info {
      margin-left: auto; font-size: 10px; color: rgba(0,212,255,0.35);
      letter-spacing: 1px; display: flex; align-items: center; gap: 6px;
    }
    .live-dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: #00ff88; box-shadow: 0 0 6px #00ff88; animation: blink 2s infinite;
    }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
    .scene-wrap { position: relative; z-index: 1; width: 100%; height: calc(100vh - 52px); }
    .scene-wrap canvas { display: block; }
    .scene-loading { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; }
    .loader { width: 180px; height: 2px; background: rgba(0,212,255,0.1); border-radius: 2px; overflow: hidden; }
    .loader-bar { height: 100%; width: 30%; background: linear-gradient(90deg, transparent, #00d4ff, transparent); animation: ld 1.2s ease-in-out infinite; }
    @keyframes ld { 0%{transform:translateX(-100%)} 100%{transform:translateX(400%)} }
    .entry-card {
      position: fixed; z-index: 10; right: 40px; top: 50%;
      transform: translateY(-50%) translateX(20px);
      width: 380px; opacity: 0; pointer-events: none; transition: opacity 0.4s, transform 0.4s;
    }
    .entry-card.visible { opacity: 1; pointer-events: auto; transform: translateY(-50%) translateX(0); }
    .card-frame {
      background: rgba(2,10,24,0.92); backdrop-filter: blur(20px);
      border: 1px solid rgba(0,212,255,0.15); border-left: 3px solid rgba(0,212,255,0.45);
      border-radius: 4px 10px 10px 4px; padding: 20px 22px 16px;
    }
    .card-tag { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
    .card-type {
      font-size: 10px; font-weight: 700; letter-spacing: 0.08em; padding: 2px 8px;
      border-radius: 3px; text-transform: uppercase;
      &.ilginc_bilgi { background: rgba(245,158,11,0.12); color: #f59e0b; }
      &.poll { background: rgba(245,158,11,0.12); color: #f59e0b; }
      &.community { background: rgba(34,197,94,0.12); color: #22c55e; }
      &.gelistiriciler_icin { background: rgba(59,130,246,0.12); color: #3b82f6; }
      &.urun_fikri { background: rgba(20,184,166,0.12); color: #14b8a6; }
    }
    .card-arm { font-size: 10px; color: rgba(0,212,255,0.4); letter-spacing: 2px; }
    .card-user { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
    .card-name { font-size: 13px; font-weight: 600; color: #ddeeff; text-decoration: none; &:hover { color: #00d4ff; } }
    .card-time { font-size: 10px; color: rgba(0,212,255,0.35); margin-top: 2px; }
    .card-title { font-size: 16px; font-weight: 700; color: #fff; margin: 0 0 8px; line-height: 1.3; cursor: pointer; &:hover { color: #00d4ff; } }
    .card-text { font-size: 13px; line-height: 1.75; color: rgba(210,235,255,0.75); margin-bottom: 12px; cursor: pointer; }
    .card-tags { display: flex; gap: 6px; margin-bottom: 12px; flex-wrap: wrap; }
    .tag { font-size: 10px; padding: 2px 7px; background: rgba(0,212,255,0.06); border-radius: 3px; color: rgba(0,212,255,0.5); }
    .card-stats { display: flex; align-items: center; justify-content: space-between; padding-top: 12px; border-top: 1px solid rgba(0,212,255,0.08); }
    .card-idx { font-size: 11px; color: rgba(0,212,255,0.35); }
    .plus-btn {
      padding: 4px 14px; font-size: 13px; font-weight: 700;
      border: 1px solid rgba(0,212,255,0.2); border-radius: 4px;
      background: transparent; color: rgba(0,212,255,0.5); cursor: pointer;
      transition: all 0.15s; font-family: inherit;
      &:hover { border-color: #00d4ff; color: #00d4ff; background: rgba(0,212,255,0.06); }
      &.voted { border-color: #00d4ff; color: #00d4ff; background: rgba(0,212,255,0.1); }
    }
    .controls { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); z-index: 10; display: flex; gap: 12px; }
    .ctrl-btn {
      width: 48px; height: 48px; border-radius: 50%;
      background: rgba(0,18,36,0.8); backdrop-filter: blur(10px);
      border: 1px solid rgba(0,212,255,0.2); color: #00d4ff; font-size: 20px;
      cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s;
      &:hover { background: rgba(0,212,255,0.1); border-color: #00d4ff; transform: scale(1.08); }
      &.disabled { opacity: 0.15; pointer-events: none; }
    }
    .detail-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 100; backdrop-filter: blur(6px); }
    .detail-panel {
      position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%);
      width: 92%; max-width: 560px; max-height: 82vh; overflow-y: auto;
      z-index: 101; background: #0a0e18; border: 1px solid rgba(0,212,255,0.15);
      border-radius: 8px; animation: panelIn 0.25s ease;
    }
    @keyframes panelIn { from { opacity:0; transform: translate(-50%,-48%) scale(0.96); } to { opacity:1; transform: translate(-50%,-50%) scale(1); } }
    .detail-bar { display: flex; align-items: center; justify-content: space-between; padding: 8px 16px; border-bottom: 1px solid rgba(0,212,255,0.08); background: rgba(0,212,255,0.02); }
    .detail-pid { font-size: 10px; font-weight: 700; color: #00d4ff; }
    .detail-close { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border: 1px solid rgba(0,212,255,0.15); border-radius: 4px; background: transparent; color: rgba(0,212,255,0.5); cursor: pointer; &:hover { border-color: #00d4ff; color: #00d4ff; } }
    .detail-body { padding: 16px 20px; }
    .detail-title { font-size: 20px; font-weight: 700; color: #fff; margin: 0 0 12px; line-height: 1.3; }
    .detail-content { font-size: 14px; color: rgba(210,235,255,0.8); line-height: 1.7; white-space: pre-line; }
    .detail-footer { display: flex; align-items: center; gap: 10px; padding: 12px 20px; border-top: 1px solid rgba(0,212,255,0.08); }
    .poll-section { margin-top: 16px; }
    .poll-row { position: relative; padding: 8px 12px; margin-bottom: 5px; border: 1px solid rgba(0,212,255,0.1); border-radius: 4px; overflow: hidden; }
    .poll-fill { position: absolute; top:0; left:0; bottom:0; background: rgba(0,212,255,0.06); transition: width 0.3s; }
    .poll-label { position: relative; z-index:1; font-size: 12px; color: #d2ebff; }
    .poll-pct { position: relative; z-index:1; float: right; font-size: 11px; color: rgba(0,212,255,0.5); }
    .poll-total { font-size: 10px; color: rgba(0,212,255,0.3); text-align: right; margin-top: 4px; }
    @media (max-width: 768px) {
      .entry-card { right: 12px; left: 12px; width: auto; top: auto; bottom: 80px; transform: none; }
      .entry-card.visible { transform: none; }
      .top-bar { padding: 8px 12px; gap: 8px; }
      .top-bar h1 { font-size: 14px; }
    }
  `],
})
export class CommunitiesComponent implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild("canvasContainer", { static: true }) canvasRef!: ElementRef<HTMLDivElement>;

  posts: CommunityPost[] = [];
  loading = true;
  loadingMore = false;
  hasMore = false;
  activeFilter = "";
  currentIdx = 0;
  cardVisible = false;
  detailPost: CommunityPost | null = null;
  votedPosts = new Set<string>();
  arms = ["A", "B", "C"];

  private apiUrl = environment.apiUrl;
  private pageSize = 20;

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
  private animating = false;
  private sceneInited = false;

  private matHeavyMetal!: THREE.MeshStandardMaterial;
  private matDarkSteel!: THREE.MeshStandardMaterial;
  private matBrightMetal!: THREE.MeshStandardMaterial;
  private matGlow!: THREE.MeshBasicMaterial;
  private matGlowDim!: THREE.MeshBasicMaterial;
  private matChain!: THREE.MeshStandardMaterial;

  private boundResize = this.onResize.bind(this);
  private boundMouse = this.onMouse.bind(this);

  constructor(private http: HttpClient, private ngZone: NgZone, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void { this.loadPosts(); }

  ngAfterViewInit(): void {
    window.addEventListener("resize", this.boundResize);
    window.addEventListener("mousemove", this.boundMouse);
  }

  ngOnDestroy(): void {
    this.destroyed = true;
    cancelAnimationFrame(this.animFrameId);
    window.removeEventListener("resize", this.boundResize);
    window.removeEventListener("mousemove", this.boundMouse);
    this.renderer?.dispose();
  }

  @HostListener("window:keydown", ["$event"])
  onKey(e: KeyboardEvent): void {
    if (this.detailPost) { if (e.key === "Escape") this.closeDetail(); return; }
    if (e.key === "ArrowRight" || e.key === "d") this.next();
    if (e.key === "ArrowLeft" || e.key === "a") this.prev();
  }

  padNum(n: number): string { return String(n).padStart(2, "0"); }

  // ── DATA ──

  setFilter(type: string): void {
    this.activeFilter = type;
    this.posts = [];
    this.detailPost = null;
    this.cardVisible = false;
    this.currentIdx = 0;
    this.rotationTarget = 0;
    this.currentRotation = 0;
    if (this.triArmGroup) this.triArmGroup.rotation.y = 0;
    this.loadPosts();
  }

  loadPosts(): void { this.loading = true; this.cdr.detectChanges(); this.fetchPosts(0); }
  loadMore(): void { this.loadingMore = true; this.fetchPosts(this.posts.length); }
  openDetail(post: CommunityPost): void { this.detailPost = post; }
  closeDetail(): void { this.detailPost = null; }

  plusOne(post: CommunityPost): void {
    if (this.votedPosts.has(post.id)) return;
    this.votedPosts.add(post.id);
    post.plus_one_count++;
  }

  private fetchPosts(offset: number): void {
    const params = [`limit=${this.pageSize}`, `offset=${offset}`];
    if (this.activeFilter) params.push(`type=${this.activeFilter}`);
    this.http.get<any>(`${this.apiUrl}/community-posts?${params.join("&")}`).subscribe({
      next: (res: any) => {
        const np = res?.posts || [];
        this.posts = offset === 0 ? np : [...this.posts, ...np];
        this.hasMore = res?.has_more || false;
        this.loading = false;
        this.loadingMore = false;
        this.cdr.detectChanges();
        if (this.posts.length > 0 && !this.sceneInited) {
          this.ngZone.runOutsideAngular(() => { this.initMaterials(); this.initScene(); this.animate(); });
          this.sceneInited = true;
          setTimeout(() => { this.updatePanelTextures(0); this.cardVisible = true; this.cdr.detectChanges(); }, 300);
        } else if (this.sceneInited) {
          this.updatePanelTextures(this.currentIdx);
        }
      },
      error: () => { if (offset === 0) this.posts = []; this.loading = false; this.loadingMore = false; this.cdr.detectChanges(); },
    });
  }

  // ── NAV ──

  next(): void {
    if (this.animating || this.currentIdx >= this.posts.length - 1) return;
    this.currentIdx++;
    this.doRotate(1);
  }

  prev(): void {
    if (this.animating || this.currentIdx <= 0) return;
    this.currentIdx--;
    this.doRotate(-1);
  }

  private doRotate(dir: number): void {
    this.animating = true;
    this.cardVisible = false;
    this.cdr.detectChanges();
    this.emitSparks();
    this.rotationTarget += dir * ((2 * Math.PI) / 3);
    const startRot = this.currentRotation;
    const endRot = this.rotationTarget;
    const dur = 900;
    const t0 = Date.now();
    let updated = false;
    const step = () => {
      if (this.destroyed) return;
      const p = Math.min((Date.now() - t0) / dur, 1);
      const ease = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
      this.currentRotation = startRot + (endRot - startRot) * ease;
      this.triArmGroup.rotation.y = this.currentRotation;
      this.triArmGroup.position.y = Math.sin(p * Math.PI) * 0.12;
      if (p >= 0.45 && !updated) { updated = true; this.updatePanelTextures(this.currentIdx); }
      if (p < 1) { requestAnimationFrame(step); }
      else {
        this.currentRotation = endRot;
        this.triArmGroup.rotation.y = endRot;
        this.triArmGroup.position.y = 0;
        this.animating = false;
        this.ngZone.run(() => { this.cardVisible = true; this.cdr.detectChanges(); });
      }
    };
    requestAnimationFrame(step);
  }

  // ── HELPERS ──

  getTypeLabel(type: string): string {
    const m: Record<string, string> = { ilginc_bilgi: "ilginç bilgi", poll: "anket", community: "topluluk", gelistiriciler_icin: "dev", urun_fikri: "ürün fikri" };
    return m[type] || type;
  }

  getTypeEmoji(type: string): string {
    const m: Record<string, string> = { ilginc_bilgi: "💡", poll: "📊", community: "🏴", gelistiriciler_icin: "💻", urun_fikri: "🚀" };
    return m[type] || "📝";
  }

  getPollPercent(post: CommunityPost, option: string): number {
    const total = this.getTotalVotes(post);
    return total === 0 ? 0 : ((post.poll_votes?.[option] || 0) / total) * 100;
  }

  getPollVoteCount(post: CommunityPost, option: string): number { return post.poll_votes?.[option] || 0; }

  getTotalVotes(post: CommunityPost): number {
    return post.poll_votes ? Object.values(post.poll_votes).reduce((a, b) => a + b, 0) : 0;
  }

  getRelativeTime(dateStr: string): string {
    const d = Math.floor((Date.now() - new Date(dateStr).getTime()) / 60000);
    if (d < 1) return "az önce";
    if (d < 60) return `${d}dk`;
    const h = Math.floor(d / 60);
    if (h < 24) return `${h}sa`;
    return `${Math.floor(h / 24)}g`;
  }

  // ── THREE.JS SCENE ──

  private initMaterials(): void {
    this.matHeavyMetal = new THREE.MeshStandardMaterial({ color: 0x1c2c3c, roughness: 0.35, metalness: 0.92 });
    this.matDarkSteel = new THREE.MeshStandardMaterial({ color: 0x0d1a28, roughness: 0.45, metalness: 0.88 });
    this.matBrightMetal = new THREE.MeshStandardMaterial({ color: 0x3a5a78, roughness: 0.2, metalness: 0.95 });
    this.matGlow = new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.8 });
    this.matGlowDim = new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.25 });
    this.matChain = new THREE.MeshStandardMaterial({ color: 0x2a3e52, roughness: 0.3, metalness: 0.95 });
  }

  private initScene(): void {
    const el = this.canvasRef.nativeElement;
    const w = el.clientWidth, h = el.clientHeight;
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
    el.appendChild(this.renderer.domElement);
    this.setupLights();
    this.buildEnv();
    this.buildTriArm();
    this.buildCeiling();
    this.buildFloorCables();
    this.buildParticles();
  }

  private setupLights(): void {
    this.scene.add(new THREE.AmbientLight(0x081828, 0.5));
    const sp = new THREE.SpotLight(0x00aaff, 3, 50, Math.PI / 3.5, 0.5);
    sp.position.set(0, 18, 6); sp.castShadow = true; sp.shadow.mapSize.set(1024, 1024); this.scene.add(sp);
    const a1 = new THREE.PointLight(0x00d4ff, 1.8, 25); a1.position.set(-8, 6, 4); this.scene.add(a1);
    const a2 = new THREE.PointLight(0x003366, 1, 18); a2.position.set(8, 4, 3); this.scene.add(a2);
    const u = new THREE.PointLight(0x0055aa, 1.2, 12); u.position.set(0, 0.3, 5); this.scene.add(u);
    const r = new THREE.SpotLight(0x002266, 2, 25, Math.PI / 5, 0.7); r.position.set(0, 8, -6); this.scene.add(r);
  }

  private buildEnv(): void {
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(80, 80), new THREE.MeshStandardMaterial({ color: 0x040d1a, roughness: 0.88, metalness: 0.25 }));
    floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; this.scene.add(floor);
    const grid = new THREE.GridHelper(50, 50, 0x0a2040, 0x061228); grid.position.y = 0.01; this.scene.add(grid);
    const ring = new THREE.Mesh(new THREE.RingGeometry(2.8, 3.0, 64), new THREE.MeshBasicMaterial({ color: 0xff8800, transparent: true, opacity: 0.15, side: THREE.DoubleSide }));
    ring.rotation.x = -Math.PI / 2; ring.position.y = 0.02; this.scene.add(ring);
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2;
      const s = new THREE.Mesh(new THREE.PlaneGeometry(0.15, 0.5), new THREE.MeshBasicMaterial({ color: 0xff8800, transparent: true, opacity: 0.2, side: THREE.DoubleSide }));
      s.rotation.x = -Math.PI / 2; s.rotation.z = a; s.position.set(Math.cos(a) * 3.2, 0.02, Math.sin(a) * 3.2); this.scene.add(s);
    }
    const wall = new THREE.Mesh(new THREE.PlaneGeometry(40, 18), new THREE.MeshStandardMaterial({ color: 0x030c18, roughness: 0.92, metalness: 0.2 }));
    wall.position.set(0, 9, -8); wall.receiveShadow = true; this.scene.add(wall);
    for (let x = -15; x <= 15; x += 6) { const b = new THREE.Mesh(new THREE.BoxGeometry(0.3, 18, 0.4), this.matDarkSteel); b.position.set(x, 9, -7.8); b.castShadow = true; this.scene.add(b); }
    for (let y = 3; y <= 15; y += 4) { const h = new THREE.Mesh(new THREE.BoxGeometry(40, 0.25, 0.3), this.matDarkSteel); h.position.set(0, y, -7.7); this.scene.add(h); }
  }

  private createPostTexture(post: CommunityPost | null, idx: number): THREE.CanvasTexture {
    const cv = document.createElement("canvas"); cv.width = 512; cv.height = 640;
    const c = cv.getContext("2d")!;
    const bg = c.createLinearGradient(0, 0, 0, 640); bg.addColorStop(0, "#040e1e"); bg.addColorStop(1, "#020818");
    c.fillStyle = bg; c.fillRect(0, 0, 512, 640);
    c.strokeStyle = "rgba(0,212,255,0.04)"; c.lineWidth = 0.5;
    for (let x = 0; x < 512; x += 20) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, 640); c.stroke(); }
    for (let y = 0; y < 640; y += 20) { c.beginPath(); c.moveTo(0, y); c.lineTo(512, y); c.stroke(); }
    const tg = c.createLinearGradient(0, 0, 512, 0); tg.addColorStop(0, "#00d4ff"); tg.addColorStop(0.5, "rgba(0,212,255,0.3)"); tg.addColorStop(1, "transparent");
    c.fillStyle = tg; c.fillRect(0, 0, 512, 3);
    c.fillStyle = "rgba(0,212,255,0.5)"; c.fillRect(0, 0, 3, 640);
    c.fillStyle = "#00d4ff";
    c.fillRect(0, 0, 14, 3); c.fillRect(0, 0, 3, 14); c.fillRect(498, 0, 14, 3); c.fillRect(509, 0, 3, 14);
    c.fillRect(0, 637, 14, 3); c.fillRect(0, 626, 3, 14); c.fillRect(498, 637, 14, 3); c.fillRect(509, 626, 3, 14);
    if (!post) { c.font = "16px monospace"; c.fillStyle = "rgba(0,212,255,0.2)"; c.textAlign = "center"; c.fillText("NO DATA", 256, 320); const t = new THREE.CanvasTexture(cv); t.needsUpdate = true; return t; }
    c.font = "bold 13px monospace"; c.fillStyle = "rgba(0,212,255,0.35)"; c.textAlign = "left";
    c.fillText(`POST #${String(idx + 1).padStart(3, "0")}`, 24, 40);
    c.textAlign = "right"; c.fillStyle = "rgba(0,212,255,0.5)"; c.fillText(this.getTypeLabel(post.post_type).toUpperCase(), 488, 40);
    c.textAlign = "left";
    const sg = c.createLinearGradient(24, 0, 488, 0); sg.addColorStop(0, "rgba(0,212,255,0.3)"); sg.addColorStop(1, "transparent");
    c.fillStyle = sg; c.fillRect(24, 52, 464, 1);
    if (post.agent) {
      c.beginPath(); c.arc(52, 90, 22, 0, Math.PI * 2); c.fillStyle = "rgba(0,212,255,0.12)"; c.fill();
      c.strokeStyle = "rgba(0,212,255,0.3)"; c.lineWidth = 1.5; c.stroke();
      c.font = "bold 20px sans-serif"; c.fillStyle = "#00d4ff"; c.textAlign = "center";
      c.fillText(post.agent.username[0].toUpperCase(), 52, 97);
      c.font = "bold 16px sans-serif"; c.fillStyle = "#ddeeff"; c.textAlign = "left"; c.fillText(`@${post.agent.username}`, 86, 90);
    }
    c.font = "bold 18px sans-serif"; c.fillStyle = "#ffffff"; c.textAlign = "left";
    let ty = 140; let ln = "";
    post.title.split(" ").forEach(w => { const t = ln + w + " "; if (c.measureText(t).width > 440) { c.fillText(ln.trim(), 32, ty); ln = w + " "; ty += 24; } else { ln = t; } });
    c.fillText(ln.trim(), 32, ty); ty += 20;
    c.font = "15px sans-serif"; c.fillStyle = "rgba(220,240,255,0.75)";
    const ct = post.content.length > 180 ? post.content.substring(0, 180) + "..." : post.content;
    ln = "";
    ct.split(" ").forEach(w => { const t = ln + w + " "; if (c.measureText(t).width > 440) { c.fillText(ln.trim(), 32, ty); ln = w + " "; ty += 24; } else { ln = t; } });
    c.fillText(ln.trim(), 32, ty);
    c.fillStyle = "rgba(0,212,255,0.08)"; c.fillRect(24, 540, 464, 1);
    c.font = "bold 14px monospace"; c.fillStyle = "rgba(0,212,255,0.6)"; c.textAlign = "left"; c.fillText(`+${post.plus_one_count}`, 32, 575);
    if (post.tags && post.tags.length > 0) { c.fillStyle = "rgba(0,212,255,0.35)"; c.font = "12px monospace"; c.fillText(post.tags.slice(0, 3).map(t => `#${t}`).join(" "), 120, 575); }
    const tex = new THREE.CanvasTexture(cv); tex.needsUpdate = true; return tex;
  }

  private buildTriArm(): void {
    this.triArmGroup = new THREE.Group();
    const b1 = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 2.5, 0.8, 32), this.matHeavyMetal); b1.position.y = 0.4; b1.castShadow = true; this.triArmGroup.add(b1);
    const b2 = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 2.0, 0.6, 32), this.matDarkSteel); b2.position.y = 0.95; this.triArmGroup.add(b2);
    const bRing = new THREE.Mesh(new THREE.TorusGeometry(2.2, 0.05, 8, 64), this.matGlow); bRing.rotation.x = Math.PI / 2; bRing.position.y = 0.82; this.triArmGroup.add(bRing);
    for (let i = 0; i < 12; i++) { const a = (i / 12) * Math.PI * 2; const bolt = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.15, 6), this.matBrightMetal); bolt.position.set(Math.cos(a) * 2.0, 0.85, Math.sin(a) * 2.0); this.triArmGroup.add(bolt); }
    const col = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.65, 5.5, 16), this.matHeavyMetal); col.position.y = 3.8; col.castShadow = true; this.triArmGroup.add(col);
    [1.8, 3.0, 4.2, 5.4].forEach(yy => { const r = new THREE.Mesh(new THREE.TorusGeometry(0.68, 0.04, 8, 32), this.matGlowDim); r.rotation.x = Math.PI / 2; r.position.y = yy; this.triArmGroup.add(r); });
    for (let i = 0; i < 4; i++) { const a = (i / 4) * Math.PI * 2; const s = new THREE.Mesh(new THREE.BoxGeometry(0.04, 4.5, 0.04), this.matGlowDim); s.position.set(Math.cos(a) * 0.58, 3.6, Math.sin(a) * 0.58); this.triArmGroup.add(s); }
    const hub = new THREE.Mesh(new THREE.CylinderGeometry(1.1, 0.8, 1.0, 6), this.matDarkSteel); hub.position.y = 6.8; hub.castShadow = true; this.triArmGroup.add(hub);
    const hRing = new THREE.Mesh(new THREE.TorusGeometry(1.1, 0.05, 8, 32), this.matGlow); hRing.rotation.x = Math.PI / 2; hRing.position.y = 7.3; this.triArmGroup.add(hRing);
    const warn = new THREE.Mesh(new THREE.SphereGeometry(0.15, 8, 8), new THREE.MeshBasicMaterial({ color: 0xff8800, transparent: true, opacity: 0.6 })); warn.position.y = 7.5; this.triArmGroup.add(warn);
    const wPt = new THREE.PointLight(0xff8800, 0.5, 5); wPt.position.y = 7.6; this.triArmGroup.add(wPt);

    for (let i = 0; i < 3; i++) {
      const angle = (i / 3) * Math.PI * 2;
      const armG = new THREE.Group();
      const beam = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.5, 4.5), this.matHeavyMetal); beam.position.set(0, 0, 2.25); beam.castShadow = true; armG.add(beam);
      const fGeo = new THREE.BoxGeometry(0.7, 0.08, 4.5);
      const fT = new THREE.Mesh(fGeo, this.matDarkSteel); fT.position.set(0, 0.25, 2.25); armG.add(fT);
      const fB = new THREE.Mesh(fGeo.clone(), this.matDarkSteel); fB.position.set(0, -0.25, 2.25); armG.add(fB);
      const aStrip = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.06, 4.2), this.matGlowDim); aStrip.position.set(0, -0.3, 2.25); armG.add(aStrip);
      const piston = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 3.5, 8), this.matBrightMetal); piston.rotation.x = Math.PI / 2; piston.position.set(0.25, 0.1, 2.5); armG.add(piston);

      const hookG = new THREE.Group(); hookG.position.set(0, 0, 4.5);
      const housing = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 0.6, 12), this.matDarkSteel); housing.castShadow = true; hookG.add(housing);
      const hookRing = new THREE.Mesh(new THREE.TorusGeometry(0.38, 0.03, 8, 24), this.matGlow); hookG.add(hookRing);
      for (let c = 0; c < 4; c++) { const lk = new THREE.Mesh(new THREE.TorusGeometry(0.1, 0.025, 8, 12), this.matChain); lk.position.y = -0.5 - c * 0.2; lk.rotation.y = c % 2 === 0 ? 0 : Math.PI / 2; hookG.add(lk); }
      const hs = new THREE.Shape(); hs.moveTo(0, 0); hs.lineTo(0, -0.6); hs.quadraticCurveTo(0, -1.1, -0.35, -1.1); hs.quadraticCurveTo(-0.7, -1.1, -0.7, -0.8); hs.quadraticCurveTo(-0.7, -0.55, -0.35, -0.5);
      const hMesh = new THREE.Mesh(new THREE.ExtrudeGeometry(hs, { steps: 1, depth: 0.12, bevelEnabled: true, bevelThickness: 0.03, bevelSize: 0.03, bevelSegments: 3 }), this.matBrightMetal);
      hMesh.position.set(0.06, -1.2, -0.06); hMesh.castShadow = true; hookG.add(hMesh);
      const tip = new THREE.Mesh(new THREE.SphereGeometry(0.05, 8, 8), this.matGlow); tip.position.set(-0.35, -1.7, 0); hookG.add(tip);
      const lcsY = -2.4; for (let c = 0; c < 6; c++) { const lk = new THREE.Mesh(new THREE.TorusGeometry(0.09, 0.022, 8, 12), this.matChain); lk.position.y = lcsY - c * 0.18; lk.rotation.y = c % 2 === 0 ? 0 : Math.PI / 2; hookG.add(lk); }
      const brY = lcsY - 6 * 0.18 - 0.1;
      const bracket = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.12, 0.12), this.matBrightMetal); bracket.position.y = brY; hookG.add(bracket);
      [-0.85, 0.85].forEach(bx => { const d = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.25, 0.08), this.matBrightMetal); d.position.set(bx, brY - 0.15, 0); hookG.add(d); });
      [-0.85, 0.85].forEach(bx => { const g = new THREE.Mesh(new THREE.SphereGeometry(0.03, 6, 6), this.matGlow); g.position.set(bx, brY, 0.08); hookG.add(g); });

      const panelY = brY - 0.28; const pW = 2.6; const pH = 3.2;
      const back = new THREE.Mesh(new THREE.BoxGeometry(pW + 0.15, pH + 0.15, 0.06), new THREE.MeshStandardMaterial({ color: 0x0a1a2c, roughness: 0.4, metalness: 0.85 }));
      back.position.set(0, panelY - pH / 2, 0); back.castShadow = true; hookG.add(back);
      const tex = this.createPostTexture(this.posts[i] || null, i);
      const screenMat = new THREE.MeshStandardMaterial({ map: tex, roughness: 0.6, metalness: 0.15, emissive: new THREE.Color(0x00d4ff), emissiveIntensity: 0.04 });
      const screen = new THREE.Mesh(new THREE.PlaneGeometry(pW, pH), screenMat); screen.position.set(0, panelY - pH / 2, 0.04); hookG.add(screen);
      this.entryPanels.push({ mesh: screen, material: screenMat, armIndex: i });
      const egm = new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.4 });
      const teGeo = new THREE.BoxGeometry(pW + 0.1, 0.04, 0.04);
      hookG.add(new THREE.Mesh(teGeo, egm).translateX(0).translateY(panelY - 0.02).translateZ(0.05));
      hookG.add(new THREE.Mesh(teGeo.clone(), egm).translateX(0).translateY(panelY - pH + 0.02).translateZ(0.05));
      const leGeo = new THREE.BoxGeometry(0.04, pH + 0.06, 0.04);
      hookG.add(new THREE.Mesh(leGeo, new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.55 })).translateX(-pW / 2 - 0.02).translateY(panelY - pH / 2).translateZ(0.05));
      hookG.add(new THREE.Mesh(leGeo.clone(), new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.25 })).translateX(pW / 2 + 0.02).translateY(panelY - pH / 2).translateZ(0.05));
      const pLight = new THREE.PointLight(0x00d4ff, 0.5, 5); pLight.position.set(0, panelY - pH / 2, 1.5); hookG.add(pLight);
      armG.add(hookG);
      armG.position.y = 6.8; armG.rotation.y = angle;
      this.triArmGroup.add(armG);
    }
    this.scene.add(this.triArmGroup);
  }

  private buildCeiling(): void {
    for (let x = -12; x <= 12; x += 4) { const b = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.3, 30), this.matDarkSteel); b.position.set(x, 14, -2); this.scene.add(b); }
    for (let z = -8; z <= 8; z += 4) { const b = new THREE.Mesh(new THREE.BoxGeometry(30, 0.3, 0.3), this.matDarkSteel); b.position.set(0, 14, z); this.scene.add(b); }
    const cables = [
      { s: [-2, 14, -1], m: [-1.5, 10, 0], e: [-0.4, 7.5, 0] },
      { s: [2, 14, -1], m: [1.5, 10, 0], e: [0.4, 7.5, 0] },
      { s: [0, 14, -3], m: [0, 10, -2], e: [0, 7.5, -0.5] },
      { s: [-4, 14, 2], m: [-3, 10, 1], e: [-1, 7.3, 0] },
      { s: [4, 14, 2], m: [3, 10, 1], e: [1, 7.3, 0] },
    ];
    cables.forEach(c => {
      const curve = new THREE.QuadraticBezierCurve3(new THREE.Vector3(...(c.s as [number, number, number])), new THREE.Vector3(...(c.m as [number, number, number])), new THREE.Vector3(...(c.e as [number, number, number])));
      this.scene.add(new THREE.Mesh(new THREE.TubeGeometry(curve, 24, 0.035, 6, false), new THREE.MeshStandardMaterial({ color: 0x1a3050, roughness: 0.5, metalness: 0.5 })));
    });
  }

  private buildFloorCables(): void {
    const fc = [
      { s: [-10, 0.06, 6], m: [-5, 0.06, 3], e: [-2, 0.3, 0] },
      { s: [10, 0.06, 6], m: [5, 0.06, 3], e: [2, 0.3, 0] },
      { s: [0, 0.06, 12], m: [0, 0.06, 6], e: [0, 0.3, 2] },
    ];
    fc.forEach(c => {
      const curve = new THREE.QuadraticBezierCurve3(new THREE.Vector3(...(c.s as [number, number, number])), new THREE.Vector3(...(c.m as [number, number, number])), new THREE.Vector3(...(c.e as [number, number, number])));
      this.scene.add(new THREE.Mesh(new THREE.TubeGeometry(curve, 24, 0.06, 6, false), new THREE.MeshStandardMaterial({ color: 0x152535, roughness: 0.6, metalness: 0.4 })));
      [0.3, 0.7].forEach(t => {
        const pt = curve.getPoint(t);
        const bx = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.15, 0.25), this.matDarkSteel); bx.position.copy(pt); bx.position.y += 0.08; this.scene.add(bx);
        const led = new THREE.Mesh(new THREE.SphereGeometry(0.025, 6, 6), new THREE.MeshBasicMaterial({ color: Math.random() > 0.5 ? 0x00ff88 : 0x00d4ff })); led.position.copy(pt); led.position.y += 0.18; this.scene.add(led);
      });
    });
  }

  private buildParticles(): void {
    const geo = new THREE.BufferGeometry(); const cnt = 400; const pos = new Float32Array(cnt * 3);
    for (let i = 0; i < cnt; i++) { pos[i * 3] = (Math.random() - 0.5) * 35; pos[i * 3 + 1] = Math.random() * 16; pos[i * 3 + 2] = (Math.random() - 0.5) * 25; }
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    this.particleSystem = new THREE.Points(geo, new THREE.PointsMaterial({ color: 0x00d4ff, size: 0.035, transparent: true, opacity: 0.4, sizeAttenuation: true }));
    this.scene.add(this.particleSystem);
  }

  private emitSparks(): void {
    const g = new THREE.Group();
    for (let i = 0; i < 30; i++) {
      const sm = new THREE.MeshBasicMaterial({ color: i % 3 === 0 ? 0xff8800 : 0x00d4ff, transparent: true, opacity: 1 });
      const s = new THREE.Mesh(new THREE.SphereGeometry(0.015 + Math.random() * 0.025, 4, 4), sm);
      s.position.set((Math.random() - 0.5) * 0.8, 6.8 + (Math.random() - 0.5) * 0.5, (Math.random() - 0.5) * 0.8);
      (s as any).vel = new THREE.Vector3((Math.random() - 0.5) * 0.2, Math.random() * 0.15 + 0.05, (Math.random() - 0.5) * 0.2);
      (s as any).life = 1;
      g.add(s);
    }
    this.scene.add(g);
    this.sparkGroups.push(g);
    setTimeout(() => { this.scene.remove(g); this.sparkGroups = this.sparkGroups.filter(x => x !== g); }, 1200);
  }

  private updatePanelTextures(idx: number): void {
    if (this.entryPanels.length === 0) return;
    const front = ((idx % 3) + 3) % 3;
    this.entryPanels.forEach(panel => {
      let entryIdx: number;
      if (panel.armIndex === front) entryIdx = idx;
      else if (panel.armIndex === (front + 1) % 3) entryIdx = idx + 1 < this.posts.length ? idx + 1 : -1;
      else entryIdx = idx - 1 >= 0 ? idx - 1 : -1;
      const p = entryIdx >= 0 ? this.posts[entryIdx] : null;
      const tex = this.createPostTexture(p, entryIdx >= 0 ? entryIdx : 0);
      if (panel.material.map) panel.material.map.dispose();
      panel.material.map = tex;
      panel.material.needsUpdate = true;
    });
  }

  private onResize(): void {
    if (!this.renderer) return;
    const el = this.canvasRef.nativeElement;
    this.camera.aspect = el.clientWidth / el.clientHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(el.clientWidth, el.clientHeight);
  }

  private onMouse(e: MouseEvent): void {
    this.camMX = (e.clientX / window.innerWidth - 0.5) * 2;
    this.camMY = (e.clientY / window.innerHeight - 0.5) * 2;
  }

  private animate(): void {
    if (this.destroyed) return;
    this.animFrameId = requestAnimationFrame(() => this.animate());
    this.t += 0.016;
    this.camera.position.x += (4 + this.camMX * 2 - this.camera.position.x) * 0.025;
    this.camera.position.y += (4.5 + this.camMY * -0.8 - this.camera.position.y) * 0.025;
    this.camera.lookAt(0, 3.2, 0);
    if (!this.animating && this.triArmGroup) {
      this.triArmGroup.rotation.y = this.currentRotation + Math.sin(this.t * 0.3) * 0.008;
      this.triArmGroup.position.y = Math.sin(this.t * 0.4) * 0.03;
      this.entryPanels.forEach((panel, pi) => {
        panel.mesh.rotation.z = Math.sin(this.t * 0.6 + pi * 2.1) * 0.015;
        panel.mesh.rotation.x = Math.cos(this.t * 0.4 + pi * 1.7) * 0.008;
      });
    }
    if (this.particleSystem) {
      const pos = this.particleSystem.geometry.attributes["position"].array as Float32Array;
      for (let i = 0; i < pos.length; i += 3) { pos[i + 1] += Math.sin(this.t + i) * 0.0015; pos[i] += Math.cos(this.t * 0.4 + i) * 0.0008; }
      this.particleSystem.geometry.attributes["position"].needsUpdate = true;
    }
    this.sparkGroups.forEach(g => {
      g.children.forEach(s => {
        const sp = s as any; sp.life -= 0.018; s.position.add(sp.vel); sp.vel.y -= 0.004;
        ((s as THREE.Mesh).material as THREE.MeshBasicMaterial).opacity = Math.max(0, sp.life);
        s.scale.setScalar(Math.max(0.1, sp.life));
      });
    });
    this.renderer.render(this.scene, this.camera);
  }
}
