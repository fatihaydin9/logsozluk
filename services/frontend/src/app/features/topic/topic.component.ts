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
import { EntryContentComponent } from "../../shared/components/entry-content/entry-content.component";
import { FormatDatePipe } from "../../shared/pipes/format-date.pipe";
import { LogsozAvatarComponent } from "../../shared/components/avatar-generator/logsoz-avatar.component";
import { LucideAngularModule } from "lucide-angular";
import { TopicService } from "./topic.service";
import { VotersPopupComponent } from "../../shared/components/voters-popup/voters-popup.component";

@Component({
  selector: "app-topic",
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormatDatePipe,
    LogsozAvatarComponent,
    EntryContentComponent,
    VotersPopupComponent,
    LucideAngularModule,
  ],
  template: `
    <div class="container">
      @if (topic$ | async; as topic) {
        <div class="topic-header">
          <h1 class="topic-title">{{ topic.title }}</h1>
          <div class="topic-meta">
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
                            <button
                              class="vote-btn voltaj"
                              title="voltajlayanları gör"
                              (click)="showVoters(entry.id, 1)"
                            >
                              <lucide-icon name="zap" [size]="16"></lucide-icon>
                              <span class="vote-label">{{
                                entry.upvotes || 0
                              }}</span>
                            </button>
                            <button
                              class="vote-btn toprak"
                              title="topraklayanları gör"
                              (click)="showVoters(entry.id, -1)"
                            >
                              <lucide-icon
                                name="zap-off"
                                [size]="16"
                              ></lucide-icon>
                              <span class="vote-label">{{
                                entry.downvotes || 0
                              }}</span>
                            </button>
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
      } @else {
        <div class="loading">
          <div class="spinner"></div>
        </div>
      }

      <!-- Voters Popup -->
      @if (votersPopup.visible) {
        <app-voters-popup
          [entryId]="votersPopup.entryId"
          [voteType]="votersPopup.voteType"
          (close)="closeVotersPopup()"
        >
        </app-voters-popup>
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
        gap: var(--spacing-md);
      }

      .topic-count {
        color: var(--text-muted);
        font-size: var(--font-size-sm);
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
        cursor: pointer;
        transition: all 0.2s ease;
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
          text-decoration: none;
        }
      }

      .vote-label {
        font-weight: 600;
        min-width: 16px;
      }

      .vote-btn[data-tooltip] {
        position: relative;

        &::after {
          content: attr(data-tooltip);
          position: absolute;
          top: calc(100% + 4px);
          left: calc(100% - 8px);
          padding: 4px 8px;
          background: rgba(0, 0, 0, 0.9);
          color: #fff;
          font-size: 10px;
          font-family: var(--font-mono);
          white-space: nowrap;
          border-radius: 4px;
          opacity: 0;
          visibility: hidden;
          transition:
            opacity 0.15s ease,
            visibility 0.15s ease;
          pointer-events: none;
          z-index: 100;
        }

        &:hover::after {
          opacity: 1;
          visibility: visible;
        }
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
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid var(--border-metal);
        border-radius: var(--border-radius-sm);
        color: var(--text-secondary);
        font-size: var(--font-size-sm);
        cursor: pointer;
        transition: all 0.2s ease;
        width: 100%;

        &:hover {
          background: rgba(255, 255, 255, 0.08);
          border-color: rgba(255, 255, 255, 0.15);
          color: var(--text-primary);
        }
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

  // Voters popup state
  votersPopup = {
    visible: false,
    entryId: "",
    voteType: null as number | null,
  };

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

  showVoters(entryId: string, voteType: number): void {
    this.votersPopup = {
      visible: true,
      entryId,
      voteType,
    };
    this.cdr.markForCheck();
  }

  closeVotersPopup(): void {
    this.votersPopup = {
      visible: false,
      entryId: "",
      voteType: null,
    };
    this.cdr.markForCheck();
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
}
