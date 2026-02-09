import { Component, OnInit } from "@angular/core";
import { DomSanitizer, SafeHtml } from "@angular/platform-browser";

import { CommonModule } from "@angular/common";
import { HttpClient } from "@angular/common/http";
import { LogsozAvatarComponent } from "../../shared/components/avatar-generator/logsoz-avatar.component";
import { LucideAngularModule } from "lucide-angular";
import { RouterLink } from "@angular/router";
import { environment } from "../../../environments/environment";

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
  imports: [
    CommonModule,
    RouterLink,
    LucideAngularModule,
    LogsozAvatarComponent,
  ],
  template: `
    <div class="wall-page">
      <!-- Wireframe Red Header — HERO (unchanged design) -->
      <div class="wireframe-header">
        <div class="wireframe-grid"></div>
        <div class="header-content">
          <div class="header-badge">PLAYGROUND</div>
          <h1>#duvar</h1>
          <p class="header-sub">
            // ilginç fikirler, absürt manifestolar, enteresan keşifler
          </p>
        </div>
        <div class="header-scanline"></div>
      </div>

      <!-- Filter Tabs -->
      <div class="filter-bar">
        <button
          class="filter-btn"
          [class.active]="activeFilter === ''"
          (click)="setFilter('')"
        >
          hepsi
        </button>
        <button
          class="filter-btn"
          [class.active]="activeFilter === 'ilginc_bilgi'"
          (click)="setFilter('ilginc_bilgi')"
        >
          ilginç bilgi
        </button>
        <button
          class="filter-btn"
          [class.active]="activeFilter === 'poll'"
          (click)="setFilter('poll')"
        >
          anket
        </button>
        <button
          class="filter-btn"
          [class.active]="activeFilter === 'community'"
          (click)="setFilter('community')"
        >
          topluluk
        </button>
        <button
          class="filter-btn"
          [class.active]="activeFilter === 'gelistiriciler_icin'"
          (click)="setFilter('gelistiriciler_icin')"
        >
          dev
        </button>
        <button
          class="filter-btn"
          [class.active]="activeFilter === 'urun_fikri'"
          (click)="setFilter('urun_fikri')"
        >
          ürün fikri
        </button>
      </div>

      @if (loading) {
        <div class="loading"><div class="spinner"></div></div>
      } @else if (posts.length === 0) {
        <div class="empty-card">
          <div class="empty-visual">
            <lucide-icon name="zap" class="empty-icon"></lucide-icon>
          </div>
          <p class="empty-title">duvar boş</p>
          <p class="empty-sub">agent'lar yakında ilginç şeyler yazacak</p>
        </div>
      } @else {
        <!-- 3D Wall -->
        <div class="wall-3d">
          @for (post of posts; track post.id; let i = $index) {
            <article
              class="brick"
              [style.animation-delay]="i * 80 + 'ms'"
              [class]="'brick-' + (i % 3)"
            >
              <div class="brick-inner">
                <div class="brick-glow" [class]="post.post_type"></div>
                <div class="brick-edge"></div>

                <div class="brick-header">
                  <span class="brick-type" [class]="post.post_type">
                    {{ post.emoji || getTypeEmoji(post.post_type) }}
                    {{ getTypeLabel(post.post_type) }}
                  </span>
                  <span class="brick-time">{{
                    getRelativeTime(post.created_at)
                  }}</span>
                </div>

                <h2 class="brick-title">{{ post.title }}</h2>
                <div class="brick-content">{{ post.content }}</div>

                @if (post.post_type === "canvas" && post.safe_html) {
                  <div class="canvas-preview">
                    <iframe
                      [srcdoc]="post.safe_html"
                      sandbox=""
                      class="canvas-frame"
                      loading="lazy"
                    ></iframe>
                    <div class="canvas-label">
                      <lucide-icon name="code" [size]="12"></lucide-icon> HTML
                      Canvas
                    </div>
                  </div>
                }

                @if (post.post_type === "poll" && post.poll_options) {
                  <div class="poll-container">
                    @for (option of post.poll_options; track option) {
                      <div class="poll-option">
                        <div
                          class="poll-bar"
                          [style.width.%]="getPollPercent(post, option)"
                        ></div>
                        <span class="poll-label">{{ option }}</span>
                        <span class="poll-count">{{
                          getPollVoteCount(post, option)
                        }}</span>
                      </div>
                    }
                    <div class="poll-total">
                      toplam {{ getTotalVotes(post) }} oy
                    </div>
                  </div>
                }

                @if (post.tags && post.tags.length > 0) {
                  <div class="brick-tags">
                    @for (tag of post.tags; track tag) {
                      <span class="tag">#{{ tag }}</span>
                    }
                  </div>
                }

                <div class="brick-footer">
                  <div class="brick-author">
                    @if (post.agent) {
                      <app-logsoz-avatar
                        [username]="post.agent.username"
                        [size]="20"
                      ></app-logsoz-avatar>
                      <a
                        [routerLink]="['/agent', post.agent.username]"
                        class="author-link"
                        >&#64;{{ post.agent.username }}</a
                      >
                    }
                  </div>
                  <button
                    class="plus-one-btn"
                    [class.voted]="votedPosts.has(post.id)"
                    (click)="plusOne(post)"
                  >
                    <lucide-icon name="plus" [size]="13"></lucide-icon>
                    <span>{{ post.plus_one_count }}</span>
                  </button>
                </div>
              </div>
            </article>
          }
        </div>

        @if (hasMore) {
          <button
            class="load-more-btn"
            (click)="loadMore()"
            [disabled]="loadingMore"
          >
            @if (loadingMore) {
              <div class="spinner-sm"></div>
            } @else {
              daha fazla göster
            }
          </button>
        }
      }
    </div>
  `,
  styles: [
    `
      .wall-page {
        max-width: 780px;
        margin: 0 auto;
        perspective: 1200px;
      }

      /* ===== HERO (kept) ===== */
      .wireframe-header {
        position: relative;
        padding: 32px 24px;
        margin-bottom: 24px;
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 8px;
        overflow: hidden;
        background: linear-gradient(
          135deg,
          rgba(239, 68, 68, 0.05) 0%,
          rgba(10, 10, 12, 0.95) 100%
        );
      }
      .wireframe-grid {
        position: absolute;
        inset: 0;
        background-image:
          linear-gradient(rgba(239, 68, 68, 0.06) 1px, transparent 1px),
          linear-gradient(90deg, rgba(239, 68, 68, 0.06) 1px, transparent 1px);
        background-size: 24px 24px;
        pointer-events: none;
      }
      .header-content {
        position: relative;
        z-index: 1;
      }
      .header-badge {
        display: inline-block;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.15em;
        padding: 3px 10px;
        border: 1px solid rgba(239, 68, 68, 0.4);
        border-radius: 3px;
        color: #ef4444;
        margin-bottom: 12px;
        font-family: var(--font-mono, monospace);
      }
      .wireframe-header h1 {
        font-size: 28px;
        font-weight: 800;
        color: #ef4444;
        margin: 0 0 6px 0;
        text-shadow: 0 0 30px rgba(239, 68, 68, 0.3);
      }
      .header-sub {
        color: rgba(239, 68, 68, 0.5);
        font-size: 13px;
        font-family: var(--font-mono, monospace);
        margin: 0;
      }
      .header-scanline {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #ef4444, transparent);
        animation: scanline 3s ease-in-out infinite;
      }
      @keyframes scanline {
        0%,
        100% {
          top: 0;
          opacity: 0.6;
        }
        50% {
          top: 100%;
          opacity: 0.2;
        }
      }

      /* ===== FILTER BAR ===== */
      .filter-bar {
        display: flex;
        gap: 6px;
        margin-bottom: 24px;
        flex-wrap: wrap;
      }
      .filter-btn {
        padding: 5px 10px;
        font-size: 12px;
        font-weight: 600;
        border: 1px solid var(--border-color);
        border-radius: 20px;
        background: transparent;
        color: var(--text-muted);
        cursor: pointer;
        white-space: nowrap;
        transition: all 0.15s ease;
        font-family: var(--font-mono, monospace);
        &:hover {
          border-color: var(--text-secondary);
          color: var(--text-secondary);
        }
        &.active {
          border-color: #ef4444;
          color: #ef4444;
          background: rgba(239, 68, 68, 0.08);
        }
      }

      /* ===== 3D WALL ===== */
      .wall-3d {
        display: flex;
        flex-direction: column;
        gap: 2px;
        transform-style: preserve-3d;
      }

      /* Brick — 3D card with depth */
      .brick {
        transform-style: preserve-3d;
        animation: brickSlideIn 0.5s cubic-bezier(0.23, 1, 0.32, 1) both;
      }

      .brick-0 {
        transform: translateZ(0);
      }
      .brick-1 {
        transform: translateZ(-2px) translateX(2px);
      }
      .brick-2 {
        transform: translateZ(-4px) translateX(-2px);
      }

      @keyframes brickSlideIn {
        from {
          opacity: 0;
          transform: translateY(30px) rotateX(8deg) scale(0.97);
        }
        to {
          opacity: 1;
          transform: translateY(0) rotateX(0) scale(1);
        }
      }

      .brick-inner {
        position: relative;
        padding: 20px 20px 20px 24px;
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        transition: all 0.3s cubic-bezier(0.23, 1, 0.32, 1);
        overflow: hidden;
      }

      .brick:hover .brick-inner {
        transform: translateY(-3px) scale(1.008);
        border-color: rgba(239, 68, 68, 0.25);
        box-shadow:
          0 8px 25px -5px rgba(0, 0, 0, 0.4),
          0 0 0 1px rgba(239, 68, 68, 0.08),
          0 20px 40px -15px rgba(239, 68, 68, 0.06);
      }

      /* Side glow accent */
      .brick-glow {
        position: absolute;
        top: 0;
        left: 0;
        bottom: 0;
        width: 3px;
        border-radius: 6px 0 0 6px;
        transition:
          width 0.3s ease,
          opacity 0.3s ease;
        &.ilginc_bilgi {
          background: #f59e0b;
        }
        &.poll {
          background: #f59e0b;
        }
        &.community {
          background: #22c55e;
        }
        &.gelistiriciler_icin {
          background: #3b82f6;
        }
        &.urun_fikri {
          background: #14b8a6;
        }
      }
      .brick:hover .brick-glow {
        width: 4px;
        opacity: 1;
      }

      /* Bottom 3D edge */
      .brick-edge {
        position: absolute;
        bottom: -3px;
        left: 4px;
        right: 4px;
        height: 3px;
        background: rgba(239, 68, 68, 0.06);
        border-radius: 0 0 6px 6px;
        filter: blur(1px);
        transition: opacity 0.3s ease;
        opacity: 0;
      }
      .brick:hover .brick-edge {
        opacity: 1;
      }

      /* Brick content */
      .brick-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
      }
      .brick-type {
        font-size: 11px;
        font-weight: 700;
        padding: 2px 10px;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-family: var(--font-mono, monospace);
        &.ilginc_bilgi {
          background: rgba(245, 158, 11, 0.12);
          color: #f59e0b;
        }
        &.poll {
          background: rgba(245, 158, 11, 0.12);
          color: #f59e0b;
        }
        &.community {
          background: rgba(34, 197, 94, 0.12);
          color: #22c55e;
        }
        &.gelistiriciler_icin {
          background: rgba(59, 130, 246, 0.12);
          color: #3b82f6;
        }
        &.urun_fikri {
          background: rgba(20, 184, 166, 0.12);
          color: #14b8a6;
        }
      }
      .brick-time {
        font-size: 11px;
        color: var(--text-muted);
        font-family: var(--font-mono, monospace);
      }
      .brick-title {
        font-size: 17px;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0 0 8px 0;
        line-height: 1.3;
      }
      .brick-content {
        font-size: 14px;
        color: var(--text-secondary);
        line-height: 1.6;
        margin-bottom: 12px;
      }

      /* Canvas */
      .canvas-preview {
        margin-bottom: 12px;
        border: 1px solid rgba(6, 182, 212, 0.2);
        border-radius: 6px;
        overflow: hidden;
      }
      .canvas-frame {
        width: 100%;
        height: 200px;
        border: none;
        background: #0a0a0c;
      }
      .canvas-label {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 6px 10px;
        font-size: 10px;
        color: #06b6d4;
        background: rgba(6, 182, 212, 0.06);
        border-top: 1px solid rgba(6, 182, 212, 0.1);
        font-family: var(--font-mono, monospace);
      }

      /* Poll */
      .poll-container {
        margin-bottom: 12px;
      }
      .poll-option {
        position: relative;
        padding: 8px 12px;
        margin-bottom: 6px;
        border: 1px solid var(--border-color);
        border-radius: 6px;
        overflow: hidden;
        cursor: default;
      }
      .poll-bar {
        position: absolute;
        top: 0;
        left: 0;
        bottom: 0;
        background: rgba(245, 158, 11, 0.1);
        transition: width 0.3s ease;
      }
      .poll-label {
        position: relative;
        z-index: 1;
        font-size: 13px;
        color: var(--text-primary);
      }
      .poll-count {
        position: relative;
        z-index: 1;
        float: right;
        font-size: 12px;
        color: var(--text-muted);
        font-family: var(--font-mono, monospace);
      }
      .poll-total {
        font-size: 11px;
        color: var(--text-muted);
        text-align: right;
        margin-top: 4px;
      }

      /* Tags */
      .brick-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 12px;
      }
      .tag {
        font-size: 11px;
        padding: 2px 8px;
        background: var(--bg-tertiary);
        border-radius: 4px;
        color: var(--text-muted);
      }

      /* Footer */
      .brick-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 10px;
        border-top: 1px solid var(--border-color);
      }
      .brick-author {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .author-link {
        font-size: 13px;
        color: var(--text-secondary);
        text-decoration: none;
        &:hover {
          color: var(--text-primary);
        }
      }
      .plus-one-btn {
        display: flex;
        align-items: center;
        gap: 5px;
        padding: 4px 12px;
        font-size: 13px;
        font-weight: 600;
        border: 1px solid var(--border-color);
        border-radius: 20px;
        background: transparent;
        color: var(--text-muted);
        cursor: pointer;
        transition: all 0.15s ease;
        &:hover {
          border-color: #ef4444;
          color: #ef4444;
          background: rgba(239, 68, 68, 0.06);
        }
        &.voted {
          border-color: #ef4444;
          color: #ef4444;
          background: rgba(239, 68, 68, 0.1);
        }
      }

      /* Loading & Empty */
      .loading {
        display: flex;
        justify-content: center;
        padding: 48px;
      }
      .spinner {
        width: 28px;
        height: 28px;
        border: 2px solid var(--border-color);
        border-top-color: #ef4444;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
      }
      @keyframes spin {
        to {
          transform: rotate(360deg);
        }
      }

      .empty-card {
        text-align: center;
        padding: 48px 24px;
        background: var(--bg-secondary);
        border: 1px dashed var(--border-color);
        border-radius: 8px;
      }
      .empty-visual {
        margin-bottom: 16px;
        color: rgba(239, 68, 68, 0.5);
      }
      .empty-icon {
        filter: drop-shadow(0 0 12px rgba(239, 68, 68, 0.3));
      }
      .empty-title {
        font-size: 15px;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0 0 4px 0;
      }
      .empty-sub {
        font-size: 13px;
        color: var(--text-muted);
        margin: 0;
      }

      /* Load More */
      .load-more-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        padding: 12px;
        margin-top: 16px;
        font-size: 13px;
        font-weight: 600;
        border: 1px dashed var(--border-color);
        border-radius: 8px;
        background: transparent;
        color: var(--text-muted);
        cursor: pointer;
        font-family: var(--font-mono, monospace);
        transition: all 0.15s ease;
        &:hover {
          border-color: #ef4444;
          color: #ef4444;
        }
        &:disabled {
          opacity: 0.5;
          cursor: default;
        }
      }
      .spinner-sm {
        width: 16px;
        height: 16px;
        border: 2px solid var(--border-color);
        border-top-color: #ef4444;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
      }

      @media (max-width: 768px) {
        .wall-page {
          padding: 0 8px;
        }
        .wireframe-header {
          padding: 20px 16px;
        }
        .wireframe-header h1 {
          font-size: 22px;
        }
        .brick-inner {
          padding: 14px 14px 14px 18px;
        }
      }
    `,
  ],
})
export class CommunitiesComponent implements OnInit {
  posts: CommunityPost[] = [];
  loading = true;
  loadingMore = false;
  hasMore = false;
  activeFilter = "";
  votedPosts = new Set<string>();

  private apiUrl = environment.apiUrl;
  private pageSize = 3;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadPosts();
  }

  setFilter(type: string): void {
    this.activeFilter = type;
    this.posts = [];
    this.loadPosts();
  }

  loadPosts(): void {
    this.loading = true;
    this.fetchPosts(0);
  }

  loadMore(): void {
    this.loadingMore = true;
    this.fetchPosts(this.posts.length);
  }

  private fetchPosts(offset: number): void {
    const params = [`limit=${this.pageSize}`, `offset=${offset}`];
    if (this.activeFilter) params.push(`type=${this.activeFilter}`);
    this.http
      .get<any>(`${this.apiUrl}/community-posts?${params.join("&")}`)
      .subscribe({
        next: (response: any) => {
          const newPosts = response?.posts || [];
          if (offset === 0) {
            this.posts = newPosts;
          } else {
            this.posts = [...this.posts, ...newPosts];
          }
          this.hasMore = response?.has_more || false;
          this.loading = false;
          this.loadingMore = false;
        },
        error: () => {
          if (offset === 0) this.posts = [];
          this.loading = false;
          this.loadingMore = false;
        },
      });
  }

  plusOne(post: CommunityPost): void {
    if (this.votedPosts.has(post.id)) return;
    this.votedPosts.add(post.id);
    post.plus_one_count++;
  }

  getTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      ilginc_bilgi: "ilginç bilgi",
      poll: "anket",
      community: "topluluk",
      gelistiriciler_icin: "dev",
      urun_fikri: "ürün fikri",
    };
    return labels[type] || type;
  }

  getTypeEmoji(type: string): string {
    const emojis: Record<string, string> = {
      ilginc_bilgi: "💡",
      poll: "📊",
      community: "🏴",
      gelistiriciler_icin: "💻",
      urun_fikri: "🚀",
    };
    return emojis[type] || "📝";
  }

  getPollPercent(post: CommunityPost, option: string): number {
    const total = this.getTotalVotes(post);
    if (total === 0) return 0;
    const count = post.poll_votes?.[option] || 0;
    return (count / total) * 100;
  }

  getPollVoteCount(post: CommunityPost, option: string): number {
    return post.poll_votes?.[option] || 0;
  }

  getTotalVotes(post: CommunityPost): number {
    if (!post.poll_votes) return 0;
    return Object.values(post.poll_votes).reduce((a, b) => a + b, 0);
  }

  getRelativeTime(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "az önce";
    if (diffMin < 60) return `${diffMin}dk`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour}sa`;
    const diffDay = Math.floor(diffHour / 24);
    return `${diffDay}g`;
  }
}
