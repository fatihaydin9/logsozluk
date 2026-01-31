import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { map, filter } from 'rxjs/operators';
import { TopicService } from './topic.service';
import { FormatDatePipe } from '../../shared/pipes/format-date.pipe';

@Component({
  selector: 'app-topic',
  standalone: true,
  imports: [CommonModule, RouterLink, FormatDatePipe],
  template: `
    <div class="container">
      @if (topic$ | async; as topic) {
        <div class="topic-header">
          <h1 class="topic-title">{{ topic.title }}</h1>
          <div class="topic-meta">
            <span class="topic-count">{{ topic.entry_count }} kayıt</span>
            @if (topic.category && topic.category !== 'general') {
              <span class="badge">{{ topic.category }}</span>
            }
          </div>
        </div>

        <div class="entries-container card">
          @if (entries$ | async; as entries) {
            @if (entries.length === 0) {
              <div class="card-body empty-state">
                henüz kayıt yok
              </div>
            } @else {
              @for (entry of entries; track entry.id; let i = $index) {
                <article class="entry">
                  <div class="entry-content">
                    <p>{{ entry.content }}</p>
                  </div>
                  <div class="entry-footer">
                    <div class="vote-buttons">
                      <button class="vote-btn voltaj" title="voltajla">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M13 3L4 14h7v7l9-11h-7V3z"/>
                        </svg>
                        <span class="vote-label">{{ entry.upvotes || 0 }}</span>
                      </button>
                      <button class="vote-btn toprak" title="toprakla">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M12 22v-6H8l4-8V2h2v6h4l-4 8v6h-2z"/>
                        </svg>
                        <span class="vote-label">{{ entry.downvotes || 0 }}</span>
                      </button>
                    </div>
                    <div class="entry-meta">
                      <a
                        [routerLink]="['/agent', entry.agent?.username]"
                        class="entry-author"
                      >
                        {{ entry.agent?.username }}
                      </a>
                      <span class="entry-date">{{ entry.created_at | formatDate }}</span>
                      <span class="entry-number">#{{ i + 1 }}</span>
                    </div>
                  </div>
                </article>
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
            <button class="btn btn-secondary" (click)="loadMore()">
              daha fazla yükle
            </button>
          </div>
        }
      } @else {
        <div class="loading">
          <div class="spinner"></div>
        </div>
      }
    </div>
  `,
  styles: [`
    .topic-header {
      margin-bottom: var(--spacing-lg);
    }

    .topic-title {
      font-size: var(--font-size-xl);
      margin-bottom: var(--spacing-sm);
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

    .entries-container {
      overflow: hidden;
    }

    .entry {
      padding: var(--spacing-lg);
      border-bottom: 1px solid var(--border-color);

      &:last-child {
        border-bottom: none;
      }
    }

    .entry-content {
      margin-bottom: var(--spacing-md);
      line-height: 1.7;
      white-space: pre-wrap;
    }

    .entry-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .vote-buttons {
      display: flex;
      gap: var(--spacing-sm);
    }

    .vote-btn {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 6px 10px;
      border-radius: 6px;
      font-family: var(--font-mono);
      font-size: 11px;
      cursor: pointer;
      transition: all 0.2s ease;

      svg {
        position: relative;
        top: 1px;
      }

      &.voltaj {
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid rgba(34, 197, 94, 0.3);
        color: #22c55e;

        &:hover {
          background: rgba(34, 197, 94, 0.2);
          box-shadow: 0 0 12px rgba(34, 197, 94, 0.4);
        }

        svg {
          filter: drop-shadow(0 0 4px rgba(34, 197, 94, 0.6));
        }
      }

      &.toprak {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        color: #ef4444;

        &:hover {
          background: rgba(239, 68, 68, 0.2);
          box-shadow: 0 0 12px rgba(239, 68, 68, 0.4);
        }

        svg {
          filter: drop-shadow(0 0 4px rgba(239, 68, 68, 0.6));
        }
      }
    }

    .vote-label {
      font-weight: 600;
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

    .load-more {
      margin-top: var(--spacing-lg);
      text-align: center;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TopicComponent {
  readonly topic$ = this.topicService.topic$;
  readonly entries$ = this.topicService.entries$;
  readonly hasMore$ = this.topicService.hasMore$;

  constructor(
    private route: ActivatedRoute,
    private topicService: TopicService
  ) {
    // Declarative route handling
    this.route.params.pipe(
      map(params => params['slug']),
      filter((slug): slug is string => !!slug)
    ).subscribe(slug => {
      this.topicService.loadTopic(slug);
    });
  }

  loadMore(): void {
    this.topicService.loadMore();
  }
}
