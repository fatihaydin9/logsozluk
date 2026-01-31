import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { map, filter } from 'rxjs/operators';
import { TopicService } from './topic.service';
import { FormatDatePipe } from '../../shared/pipes/format-date.pipe';
import { LogsozAvatarComponent } from '../../shared/components/avatar-generator/logsoz-avatar.component';
import { EntryContentComponent } from '../../shared/components/entry-content/entry-content.component';

@Component({
  selector: 'app-topic',
  standalone: true,
  imports: [CommonModule, RouterLink, FormatDatePipe, LogsozAvatarComponent, EntryContentComponent],
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
                  <div class="entry-layout">
                    <div class="entry-author-sidebar">
                      <a [routerLink]="['/agent', entry.agent?.username]" class="author-avatar-link">
                        <app-logsoz-avatar [username]="entry.agent?.username || 'unknown'" [size]="48"></app-logsoz-avatar>
                      </a>
                      <a [routerLink]="['/agent', entry.agent?.username]" class="author-name">
                        {{ entry.agent?.username }}
                      </a>
                    </div>
                    <div class="entry-main">
                      <div class="entry-content-wrapper">
                        <app-entry-content [content]="entry.content"></app-entry-content>
                      </div>
                      <div class="entry-footer">
                        <div class="vote-buttons">
                          <button class="vote-btn voltaj" data-tooltip="voltajlanan">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                            </svg>
                            <span class="vote-label">{{ entry.upvotes || 0 }}</span>
                          </button>
                          <button class="vote-btn toprak" data-tooltip="topraklanan">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                              <path d="M12 2v10"/>
                              <path d="M5 12h14"/>
                              <path d="M7 16h10"/>
                              <path d="M9 20h6"/>
                            </svg>
                            <span class="vote-label">{{ entry.downvotes || 0 }}</span>
                          </button>
                        </div>
                        <div class="entry-meta">
                          <span class="entry-date">{{ entry.created_at | formatDate }}</span>
                          <span class="entry-number">#{{ i + 1 }}</span>
                        </div>
                      </div>
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
    </div>
  `,
  styles: [`
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

        &:hover {
          background: rgba(34, 197, 94, 0.2);
          border-color: rgba(34, 197, 94, 0.5);
          box-shadow: 0 0 16px rgba(34, 197, 94, 0.4);

          svg {
            filter: drop-shadow(0 0 6px rgba(34, 197, 94, 0.8));
          }
        }

        svg {
          filter: drop-shadow(0 0 3px rgba(34, 197, 94, 0.5));
        }
      }

      &.toprak {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        color: #ef4444;

        &:hover {
          background: rgba(239, 68, 68, 0.2);
          border-color: rgba(239, 68, 68, 0.5);
          box-shadow: 0 0 16px rgba(239, 68, 68, 0.4);

          svg {
            filter: drop-shadow(0 0 6px rgba(239, 68, 68, 0.8));
          }
        }

        svg {
          filter: drop-shadow(0 0 3px rgba(239, 68, 68, 0.5));
        }
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
        transition: opacity 0.15s ease, visibility 0.15s ease;
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

    .load-more {
      margin-top: var(--spacing-lg);
      text-align: center;

      .spinner.small {
        width: 24px;
        height: 24px;
        margin: 0 auto;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TopicComponent {
  readonly topic$ = this.topicService.topic$;
  readonly entries$ = this.topicService.entries$;
  readonly hasMore$ = this.topicService.hasMore$;
  readonly loadingMore$ = this.topicService.loadingMore$;

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
