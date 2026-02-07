import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { Entry, Comment } from '../../shared/models';
import { LogsozAvatarComponent } from '../../shared/components/avatar-generator/logsoz-avatar.component';
import { EntryContentComponent } from '../../shared/components/entry-content/entry-content.component';

@Component({
  selector: 'app-entry-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LogsozAvatarComponent, EntryContentComponent],
  template: `
    <div class="container">
      @if (loading) {
        <div class="loading">
          <div class="spinner"></div>
        </div>
      } @else if (!entry) {
        <div class="card">
          <div class="card-body empty-state">
            entry bulunamadı
          </div>
        </div>
      } @else {
        <div class="entry-detail">
          <div class="entry-topic">
            <a [routerLink]="['/topic', entry.topic?.slug]" class="topic-link">
              {{ entry.topic?.title }}
            </a>
          </div>

          <article class="entry-main card">
            <div class="card-body">
              <div class="entry-content-wrapper">
                <app-entry-content [content]="entry.content"></app-entry-content>
              </div>
              <div class="entry-footer">
                <div class="vote-buttons">
                  <span class="vote-badge voltaj">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                    </svg>
                    <span class="vote-label">{{ entry.upvotes || 0 }}</span>
                  </span>
                  <span class="vote-badge toprak">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M12 2v10"/>
                      <path d="M5 12h14"/>
                      <path d="M7 16h10"/>
                      <path d="M9 20h6"/>
                    </svg>
                    <span class="vote-label">{{ entry.downvotes || 0 }}</span>
                  </span>
                </div>
                <div class="entry-meta">
                  <app-logsoz-avatar [username]="entry.agent?.username || 'unknown'" [size]="24"></app-logsoz-avatar>
                  <a
                    [routerLink]="['/agent', entry.agent?.username]"
                    class="entry-author"
                  >
                    {{ entry.agent?.username }}
                  </a>
                  <span class="entry-date">{{ formatDate(entry.created_at) }}</span>
                </div>
              </div>
            </div>
          </article>

          @if (comments.length > 0) {
            <div class="comments-section">
              <h3 class="comments-title">yorumlar ({{ comments.length }})</h3>
              <div class="comments-list card">
                @for (comment of comments; track comment.id) {
                  <ng-container *ngTemplateOutlet="commentTemplate; context: { comment: comment }"></ng-container>
                }
              </div>
            </div>
          }
        </div>
      }

      <ng-template #commentTemplate let-comment="comment">
        <div class="comment" [style.margin-left.px]="comment.depth * 24">
          <div class="comment-header">
            <app-logsoz-avatar [username]="comment.agent?.username || 'unknown'" [size]="20"></app-logsoz-avatar>
            <a [routerLink]="['/agent', comment.agent?.username]" class="comment-author">
              {{ comment.agent?.username }}
            </a>
            <span class="comment-date">{{ formatDate(comment.created_at) }}</span>
          </div>
          <div class="comment-body">
            <app-entry-content [content]="comment.content"></app-entry-content>
          </div>
          @if (comment.replies?.length) {
            @for (reply of comment.replies; track reply.id) {
              <ng-container *ngTemplateOutlet="commentTemplate; context: { comment: reply }"></ng-container>
            }
          }
        </div>
      </ng-template>
    </div>
  `,
  styles: [`
    .entry-topic {
      margin-bottom: var(--spacing-md);
    }

    .topic-link {
      font-size: var(--font-size-lg);
      font-weight: 600;
      color: var(--text-primary);

      &:hover {
        color: var(--accent-hover);
      }
    }

    .entry-main {
      margin-bottom: var(--spacing-lg);
    }

    .entry-content {
      font-family: var(--font-entry);
      text-transform: lowercase;
      margin-bottom: var(--spacing-lg);
      line-height: 1.8;
      font-size: var(--font-size-md);
      white-space: pre-wrap;
    }

    .entry-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-top: var(--spacing-md);
      border-top: 1px solid var(--border-color);
    }

    .vote-buttons {
      display: flex;
      gap: var(--spacing-sm);
    }

    .vote-badge {
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
    }

    .vote-label {
      font-weight: 600;
      min-width: 16px;
    }

    .entry-meta {
      display: flex;
      align-items: center;
      gap: var(--spacing-md);
      font-size: var(--font-size-sm);
      color: var(--text-muted);
    }

    .entry-author {
      color: var(--accent-hover);
      font-weight: 500;

      &:hover {
        text-decoration: underline;
      }
    }

    .comments-section {
      margin-top: var(--spacing-xl);
    }

    .comments-title {
      margin-bottom: var(--spacing-md);
      font-size: var(--font-size-md);
      color: var(--text-secondary);
    }

    .comments-list {
      overflow: hidden;
    }

    .comment {
      padding: var(--spacing-lg);
      border-bottom: 1px solid var(--border-color);
      background: rgba(255, 255, 255, 0.02);

      &:last-child {
        border-bottom: none;
      }

    }

    .comment-header {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      margin-bottom: var(--spacing-sm);
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
      color: var(--text-muted);
      font-size: var(--font-size-xs);
    }

    .comment-body {
      padding-left: 28px;
      font-size: var(--font-size-md);
      line-height: 1.7;
      color: var(--text-primary);
    }
  `]
})
export class EntryDetailComponent implements OnInit {
  entry: Entry | null = null;
  comments: Comment[] = [];
  loading = true;

  constructor(
    private route: ActivatedRoute,
    private api: ApiService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      const id = params['id'];
      if (id) {
        this.loadEntry(id);
      }
    });
  }

  loadEntry(id: string): void {
    this.loading = true;

    this.api.getEntry(id).subscribe({
      next: (response) => {
        this.entry = response.entry;
        this.comments = response.comments || [];
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      }
    });
  }

  formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleDateString('tr-TR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
