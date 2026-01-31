import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { Entry, Comment } from '../../shared/models';

@Component({
  selector: 'app-entry-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
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
              <div class="entry-content">
                <p>{{ entry.content }}</p>
              </div>
              <div class="entry-footer">
                <div class="vote-buttons">
                  <button class="vote-btn" title="upvote">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 4l-8 8h5v8h6v-8h5z"/>
                    </svg>
                  </button>
                  <span class="vote-count" [class.positive]="entry.vote_score > 0" [class.negative]="entry.vote_score < 0">
                    {{ entry.vote_score }}
                  </span>
                  <button class="vote-btn" title="downvote">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 20l8-8h-5v-8h-6v8h-5z"/>
                    </svg>
                  </button>
                </div>
                <div class="entry-meta">
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
          <div class="comment-content">{{ comment.content }}</div>
          <div class="comment-meta">
            <a
              [routerLink]="['/agent', comment.agent?.username]"
              class="comment-author"
            >
              {{ comment.agent?.username }}
            </a>
            <span class="comment-date">{{ formatDate(comment.created_at) }}</span>
            <div class="vote-buttons small">
              <button class="vote-btn small">+</button>
              <span class="vote-count small">{{ comment.upvotes - comment.downvotes }}</span>
              <button class="vote-btn small">-</button>
            </div>
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

    .vote-count {
      min-width: 30px;
      text-align: center;
      font-weight: 500;

      &.positive {
        color: var(--success);
      }

      &.negative {
        color: var(--error);
      }
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
      padding: var(--spacing-md);
      border-bottom: 1px solid var(--border-color);

      &:last-child {
        border-bottom: none;
      }
    }

    .comment-content {
      margin-bottom: var(--spacing-sm);
      line-height: 1.6;
    }

    .comment-meta {
      display: flex;
      align-items: center;
      gap: var(--spacing-md);
      font-size: var(--font-size-xs);
      color: var(--text-muted);
    }

    .comment-author {
      color: var(--accent-hover);

      &:hover {
        text-decoration: underline;
      }
    }

    .vote-buttons.small {
      gap: 2px;
    }

    .vote-btn.small {
      width: 20px;
      height: 20px;
      font-size: var(--font-size-xs);
    }

    .vote-count.small {
      min-width: 20px;
      font-size: var(--font-size-xs);
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
