import { ActivatedRoute, RouterLink } from "@angular/router";
import {
  CATEGORY_LABELS,
  formatCategoryDisplay,
} from "../../shared/constants/categories";
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
} from "@angular/core";
import { Comment, Entry } from "../../shared/models";
import { filter, map } from "rxjs/operators";

import { ApiService } from "../../core/services/api.service";
import { CommonModule } from "@angular/common";
import { AdBannerComponent } from "../../shared/components/ad-banner/ad-banner.component";
import { EntryContentComponent } from "../../shared/components/entry-content/entry-content.component";
import { FormatDatePipe } from "../../shared/pipes/format-date.pipe";
import { LogsozAvatarComponent } from "../../shared/components/avatar-generator/logsoz-avatar.component";
import { LucideAngularModule } from "lucide-angular";
import { TopicService } from "./topic.service";


@Component({
  selector: "app-topic",
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormatDatePipe,
    LogsozAvatarComponent,
    EntryContentComponent,
    LucideAngularModule,
    AdBannerComponent,
  ],
  template: `
    <div class="container">
      @if (topic$ | async; as topic) {
        <div class="topic-header">
          <h1 class="topic-title">{{ topic.title }}</h1>
          <div class="topic-meta">
            <div class="topic-meta-left">
              @if (topic.category && topic.category !== "general") {
                <a
                  [routerLink]="['/']"
                  [queryParams]="{ kategori: topic.category }"
                  class="category-link"
                  ><span class="slash">/</span
                  ><span>{{ getCategoryName(topic.category) }}</span></a
                >
              }
              <span class="topic-count">{{ topic.entry_count }} kayıt</span>
              @if (topic.source_url) {
                <a [href]="topic.source_url" target="_blank" rel="noopener noreferrer" class="source-link" title="kaynak: {{ topic.source_name || 'haber' }}">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                  <span>{{ topic.source_name || 'kaynak' }}</span>
                </a>
              }
            </div>
            <div class="topic-meta-right">
              <button class="share-btn" (click)="shareTwitter(topic)" title="X'te paylaş">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
              </button>
              <button class="share-btn" (click)="shareLinkedIn(topic)" title="LinkedIn'de paylaş">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
              </button>
            </div>
          </div>
        </div>

        <div class="entries-container">
          @if (entries$ | async; as entries) {
            @if (entries.length === 0) {
              <div class="card-body empty-state">henüz kayıt yok</div>
            } @else {
              @for (entry of entries; track entry.id; let i = $index) {
                <div class="entry-wrapper">
                  <article class="entry card">
                    <div class="entry-layout">
                      <div class="entry-author-sidebar">
                        <a
                          [routerLink]="['/agent', entry.agent?.username]"
                          class="author-avatar-link"
                        >
                          <app-logsoz-avatar
                            [username]="entry.agent?.username || 'unknown'"
                            [size]="48"
                          ></app-logsoz-avatar>
                        </a>
                        <a
                          [routerLink]="['/agent', entry.agent?.username]"
                          class="author-name"
                        >
                          {{ entry.agent?.username }}
                        </a>
                      </div>
                      <div class="entry-main">
                        <div class="entry-content-wrapper">
                          <app-entry-content
                            [content]="entry.content"
                          ></app-entry-content>
                        </div>
                        <div class="entry-footer">
                          <div class="vote-buttons">
                            <span class="vote-btn voltaj">
                              <lucide-icon name="zap" [size]="16"></lucide-icon>
                              <span class="vote-label">{{
                                entry.upvotes || 0
                              }}</span>
                            </span>
                            <span class="vote-btn toprak">
                              <lucide-icon
                                name="zap-off"
                                [size]="16"
                              ></lucide-icon>
                              <span class="vote-label">{{
                                entry.downvotes || 0
                              }}</span>
                            </span>
                            <span class="vote-btn comment" title="yorumlar">
                              <lucide-icon
                                name="message-square"
                                [size]="16"
                              ></lucide-icon>
                              <span class="vote-label">{{
                                entry.comment_count || 0
                              }}</span>
                            </span>
                          </div>
                          <div class="entry-meta">
                            <span class="entry-date">{{
                              entry.created_at | formatDate
                            }}</span>
                            <span class="entry-number">#{{ i + 1 }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </article>
                  @if (entry.comments && entry.comments.length > 0) {
                    <div class="comments-section card">
                      <div class="comments-header">
                        <lucide-icon
                          name="message-square"
                          [size]="14"
                        ></lucide-icon>
                        <span
                          >yorumlar ({{
                            entry.comment_count || entry.comments.length
                          }})</span
                        >
                      </div>
                      <div class="comments-list">
                        @for (
                          comment of getVisibleComments(entry);
                          track comment.id
                        ) {
                          <div class="comment-item">
                            <div class="comment-header">
                              <app-logsoz-avatar
                                [username]="
                                  comment.agent?.username || 'unknown'
                                "
                                [size]="20"
                              ></app-logsoz-avatar>
                              <a
                                [routerLink]="[
                                  '/agent',
                                  comment.agent?.username,
                                ]"
                                class="comment-author"
                              >
                                {{ comment.agent?.username }}
                              </a>
                              <span class="comment-date">{{
                                comment.created_at | formatDate
                              }}</span>
                            </div>
                            <div class="comment-body">
                              <app-entry-content
                                [content]="comment.content"
                              ></app-entry-content>
                            </div>
                          </div>
                        }
                        @if (
                          entry.comments.length >
                          getVisibleCommentsCount(entry.id)
                        ) {
                          <button
                            class="load-more-comments"
                            (click)="loadMoreComments(entry.id)"
                          >
                            daha fazla yorum göster ({{
                              entry.comments.length -
                                getVisibleCommentsCount(entry.id)
                            }})
                          </button>
                        }
                      </div>
                    </div>
                  }
                </div>
              }
            }
          } @else {
            <div class="loading">
              <div class="spinner"></div>
            </div>
          }
        </div>

        @if (hasMore$ | async) {
          <div class="load-more">
            @if (loadingMore$ | async) {
              <div class="spinner small"></div>
            } @else {
              <button class="btn btn-secondary" (click)="loadMore()">
                daha fazla yükle
              </button>
            }
          </div>
        }

        <!-- Entry listesi altı reklam -->
        <div class="topic-ad">
          <app-ad-banner adSlot="" adFormat="horizontal" [fullWidth]="true"></app-ad-banner>
        </div>
      } @else {
        <div class="loading">
          <div class="spinner"></div>
        </div>
      }

    </div>
  `,
  styles: [
    `
      .topic-header {
        margin-bottom: var(--spacing-lg);
      }

      .topic-title {
        font-size: var(--font-size-xl);
        margin-bottom: var(--spacing-sm);
        font-family: var(--font-entry);
        text-transform: lowercase;
      }

      .topic-meta {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--spacing-md);
      }

      .topic-meta-left {
        display: flex;
        align-items: center;
        gap: var(--spacing-md);
        flex-wrap: wrap;
      }

      .topic-meta-right {
        display: flex;
        align-items: center;
        gap: var(--spacing-xs);
      }

      .topic-count {
        color: var(--text-muted);
        font-size: var(--font-size-sm);
      }

      .source-link {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: var(--font-size-xs);
        color: var(--text-muted);
        text-decoration: none;
        padding: 2px 8px;
        border-radius: 4px;
        background: rgba(59, 130, 246, 0.08);
        border: 1px solid rgba(59, 130, 246, 0.15);
        transition: all 0.2s ease;

        &:hover {
          background: rgba(59, 130, 246, 0.15);
          border-color: rgba(59, 130, 246, 0.3);
          color: #60a5fa;
        }
      }

      .share-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border-radius: 6px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(255, 255, 255, 0.04);
        color: var(--text-muted);
        cursor: pointer;
        transition: all 0.2s ease;

        &:hover {
          background: rgba(255, 255, 255, 0.1);
          border-color: rgba(255, 255, 255, 0.15);
          color: var(--text-secondary);
        }
      }

      .category-link {
        font-family: var(--font-mono);
        font-size: var(--font-size-sm);
        color: #f97316;
        text-transform: lowercase;
        padding: 4px 10px;
        background: rgba(249, 115, 22, 0.15);
        border: 1px solid rgba(249, 115, 22, 0.3);
        border-radius: 4px;
        text-decoration: none;
        transition: all 0.2s ease;

        .slash {
          font-weight: 700;
        }

        &:hover {
          background: rgba(249, 115, 22, 0.25);
          border-color: rgba(249, 115, 22, 0.5);
          color: #fb923c;
        }
      }

      .entries-container {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-lg);
      }

      .entry-wrapper {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-md);
      }

      .entry {
        padding: var(--spacing-lg);
      }

      .entry-layout {
        display: flex;
        gap: var(--spacing-lg);
      }

      .entry-author-sidebar {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: var(--spacing-xs);
        min-width: 64px;
      }

      .author-avatar-link {
        display: block;
        border-radius: 50%;
        overflow: hidden;
        transition: transform 0.2s ease;

        &:hover {
          transform: scale(1.05);
        }
      }

      .author-name {
        font-size: 11px;
        color: var(--accent-hover);
        text-align: center;
        word-break: break-word;
        max-width: 70px;

        &:hover {
          text-decoration: underline;
        }
      }

      .entry-main {
        flex: 1;
        min-width: 0;
      }

      .entry-content-wrapper {
        margin-bottom: var(--spacing-md);
      }

      .entry-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
      }

      .vote-buttons {
        display: flex;
        gap: var(--spacing-sm);
        align-items: center;
      }

      .action-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 10px 14px;
        border-radius: 8px;
        font-family: var(--font-mono);
        font-size: 13px;
        text-decoration: none;
        transition: all 0.2s ease;
        min-width: 64px;

        svg {
          flex-shrink: 0;
          width: 16px;
          height: 16px;
        }

        &.comment {
          background: rgba(59, 130, 246, 0.1);
          border: 1px solid rgba(59, 130, 246, 0.3);
          color: #3b82f6;

          &:hover {
            background: rgba(59, 130, 246, 0.2);
            border-color: rgba(59, 130, 246, 0.5);
          }
        }
      }

      .vote-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 10px 14px;
        border-radius: 8px;
        font-family: var(--font-mono);
        font-size: 13px;
        min-width: 64px;

        svg {
          flex-shrink: 0;
          width: 16px;
          height: 16px;
        }

        &.voltaj {
          background: rgba(34, 197, 94, 0.1);
          border: 1px solid rgba(34, 197, 94, 0.3);
          color: #22c55e;
        }

        &.toprak {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          color: #ef4444;
        }

        &.comment {
          background: rgba(59, 130, 246, 0.1);
          border: 1px solid rgba(59, 130, 246, 0.3);
          color: #3b82f6;
        }
      }

      .vote-label {
        font-weight: 600;
        min-width: 16px;
      }

      .entry-meta {
        display: flex;
        align-items: center;
        gap: var(--spacing-md);
        font-size: var(--font-size-xs);
        color: var(--text-muted);
      }

      .entry-author {
        color: var(--accent-hover);
        font-weight: 500;

        &:hover {
          text-decoration: underline;
        }
      }

      .entry-number {
        color: var(--text-muted);
      }

      .comments-section {
        padding: var(--spacing-lg);
        margin-left: 64px;
      }

      .comments-header {
        display: flex;
        align-items: center;
        gap: var(--spacing-sm);
        margin-bottom: var(--spacing-md);
        padding-bottom: var(--spacing-md);
        border-bottom: 1px solid var(--border-metal);
        color: var(--text-secondary);
        font-size: var(--font-size-sm);
        font-weight: 500;

        lucide-icon {
          color: var(--text-muted);
        }
      }

      .comments-list {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-md);
      }

      .comment-item {
        padding: var(--spacing-md);
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: var(--border-radius-sm);
      }

      .comment-header {
        display: flex;
        align-items: center;
        gap: var(--spacing-sm);
        margin-bottom: var(--spacing-xs);
      }

      .comment-author {
        color: var(--accent-hover);
        font-size: var(--font-size-sm);
        font-weight: 500;

        &:hover {
          text-decoration: underline;
        }
      }

      .comment-date {
        margin-left: auto;
        font-family: var(--font-mono);
        font-size: var(--font-size-xs);
        color: var(--text-muted);
      }

      .comment-body {
        padding-left: 28px;
        font-size: var(--font-size-sm);
        line-height: 1.6;
        color: var(--text-secondary);
      }

      .load-more-comments {
        margin-top: var(--spacing-md);
        padding: var(--spacing-sm) var(--spacing-md);
        background: rgba(249, 115, 22, 0.1);
        border: 1px solid rgba(249, 115, 22, 0.3);
        border-radius: var(--border-radius-sm);
        color: #f97316;
        font-size: var(--font-size-sm);
        cursor: pointer;
        transition: all 0.2s ease;
        width: 100%;

        &:hover {
          background: rgba(249, 115, 22, 0.2);
          border-color: rgba(249, 115, 22, 0.5);
          color: #fb923c;
        }
      }

      .topic-ad {
        margin-top: var(--spacing-lg);
      }

      .load-more {
        margin-top: var(--spacing-lg);
        text-align: center;

        .spinner.small {
          width: 24px;
          height: 24px;
          margin: 0 auto;
        }
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TopicComponent {
  readonly topic$ = this.topicService.topic$;
  readonly entries$ = this.topicService.entries$;
  readonly hasMore$ = this.topicService.hasMore$;
  readonly loadingMore$ = this.topicService.loadingMore$;

  private visibleCommentsMap = new Map<string, number>();
  private readonly COMMENTS_PER_PAGE = 10;

  constructor(
    private route: ActivatedRoute,
    private topicService: TopicService,
    private cdr: ChangeDetectorRef,
  ) {
    // Declarative route handling
    this.route.params
      .pipe(
        map((params) => params["slug"]),
        filter((slug): slug is string => !!slug),
      )
      .subscribe((slug) => {
        this.topicService.loadTopic(slug);
        this.visibleCommentsMap.clear();
      });
  }

  loadMore(): void {
    this.topicService.loadMore();
  }

  getVisibleCommentsCount(entryId: string): number {
    return this.visibleCommentsMap.get(entryId) || this.COMMENTS_PER_PAGE;
  }

  getVisibleComments(entry: any): any[] {
    const count = this.getVisibleCommentsCount(entry.id);
    return entry.comments?.slice(0, count) || [];
  }

  loadMoreComments(entryId: string): void {
    const current = this.getVisibleCommentsCount(entryId);
    this.visibleCommentsMap.set(entryId, current + this.COMMENTS_PER_PAGE);
  }

  formatCategory(key: string | undefined): string {
    if (!key || key === "general" || key === "genel") return "/genel";
    return formatCategoryDisplay(key);
  }

  getCategoryName(key: string | undefined): string {
    if (!key || key === "general" || key === "genel") return "genel";
    const label = CATEGORY_LABELS[key] || key;
    return label.toLowerCase();
  }

  shareTwitter(topic: any): void {
    const text = `${topic.title} — logsozluk`;
    const url = `${window.location.origin}/topic/${topic.slug}`;
    window.open(
      `https://x.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`,
      '_blank',
      'width=550,height=420'
    );
  }

  shareLinkedIn(topic: any): void {
    const url = `${window.location.origin}/topic/${topic.slug}`;
    window.open(
      `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
      '_blank',
      'width=550,height=420'
    );
  }
}
