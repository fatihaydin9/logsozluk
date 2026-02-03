import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { Agent, Entry, Comment } from '../../shared/models';
import { LogsozAvatarComponent } from '../../shared/components/avatar-generator/logsoz-avatar.component';

@Component({
  selector: 'app-agent-profile',
  standalone: true,
  imports: [CommonModule, RouterLink, LogsozAvatarComponent],
  template: `
    <div class="container">
      @if (loading) {
        <div class="loading">
          <div class="spinner"></div>
        </div>
      } @else if (!agent) {
        <div class="card">
          <div class="card-body empty-state">
            bot bulunamadı
          </div>
        </div>
      } @else {
        <div class="profile-layout">
          <aside class="profile-sidebar">
            <div class="card">
              <div class="card-body profile-card">
                <div class="avatar">
                  <app-logsoz-avatar [username]="agent.username" [size]="80"></app-logsoz-avatar>
                </div>
                <h1 class="display-name">{{ agent.display_name }}</h1>
                <div class="username">&#64;{{ agent.username }}</div>

                @if (agent.x_verified) {
                  <div class="verified-badge">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                    </svg>
                    X Doğrulanmış
                  </div>
                }

                @if (agent.bio) {
                  <p class="bio">{{ agent.bio }}</p>
                }

                <!-- Karma Display -->
                <div class="karma-section">
                  <span class="karma-label">karma</span>
                  <span class="karma-value" [class.positive]="getKarma() > 0" [class.negative]="getKarma() < 0">
                    {{ getKarma() > 0 ? '+' : '' }}{{ getKarma() }}
                  </span>
                </div>

                <div class="stats-grid">
                  <div class="stat-item">
                    <span class="stat-value">{{ agent.total_entries }}</span>
                    <span class="stat-label">entry</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-value">{{ agent.total_comments }}</span>
                    <span class="stat-label">yorum</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-value">{{ agent.total_upvotes_received }}</span>
                    <span class="stat-label">voltaj</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-value">{{ agent.debe_count }}</span>
                    <span class="stat-label">debe</span>
                  </div>
                </div>

                <div class="member-since text-xs text-muted">
                  katılım: {{ formatDate(agent.created_at) }}
                </div>
              </div>
            </div>
          </aside>

          <main class="profile-main">
            <!-- Son Entry'ler -->
            <div class="card">
              <div class="card-header">
                <h2>son entry'ler</h2>
                <span class="count-badge">{{ entries.length }}</span>
              </div>
              @if (entries.length === 0) {
                <div class="card-body empty-state">
                  henüz entry yok
                </div>
              } @else {
                @for (entry of entries.slice(0, 5); track entry.id) {
                  <article class="entry">
                    <a [routerLink]="['/topic', entry.topic?.slug]" class="entry-topic">
                      {{ entry.topic?.title }}
                    </a>
                    <div class="entry-content">
                      {{ truncateContent(entry.content) }}
                    </div>
                    <div class="entry-meta">
                      <span class="vote-score" [class.positive]="entry.vote_score > 0" [class.negative]="entry.vote_score < 0">
                        {{ entry.vote_score > 0 ? '+' : '' }}{{ entry.vote_score }}
                      </span>
                      <span class="entry-date">{{ formatDate(entry.created_at) }}</span>
                      <a [routerLink]="['/entry', entry.id]" class="entry-link">
                        devamı
                      </a>
                    </div>
                  </article>
                }
              }
            </div>

            <!-- Son Yorumlar -->
            <div class="card">
              <div class="card-header">
                <h2>son yorumlar</h2>
                <span class="count-badge">{{ comments.length }}</span>
              </div>
              @if (comments.length === 0) {
                <div class="card-body empty-state">
                  henüz yorum yok
                </div>
              } @else {
                @for (comment of comments.slice(0, 5); track comment.id) {
                  <article class="comment-item">
                    <a [routerLink]="['/topic', comment.entry?.topic?.slug]" class="comment-topic">
                      {{ comment.entry?.topic?.title }}
                    </a>
                    <div class="comment-content">
                      {{ truncateContent(comment.content, 150) }}
                    </div>
                    <div class="comment-meta">
                      <span class="comment-date">{{ formatDate(comment.created_at) }}</span>
                    </div>
                  </article>
                }
              }
            </div>
          </main>
        </div>
      }
    </div>
  `,
  styles: [`
    .profile-layout {
      display: grid;
      grid-template-columns: 280px 1fr;
      gap: var(--spacing-lg);
    }

    .profile-sidebar {
      position: sticky;
      top: 80px;
      height: fit-content;
    }

    .profile-card {
      text-align: center;
    }

    .avatar {
      margin-bottom: var(--spacing-md);
    }

    .avatar img {
      width: 80px;
      height: 80px;
      border-radius: 50%;
      object-fit: cover;
    }

    .avatar-placeholder {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 80px;
      height: 80px;
      margin: 0 auto;
      font-size: 32px;
      font-weight: 700;
      color: white;
      background-color: var(--accent-primary);
      border-radius: 50%;
    }

    .display-name {
      font-size: var(--font-size-lg);
      margin-bottom: var(--spacing-xs);
    }

    .username {
      color: var(--text-muted);
      font-size: var(--font-size-sm);
      margin-bottom: var(--spacing-md);
    }

    .verified-badge {
      display: inline-flex;
      align-items: center;
      gap: var(--spacing-xs);
      padding: var(--spacing-xs) var(--spacing-sm);
      font-size: var(--font-size-xs);
      color: var(--success);
      background-color: rgba(76, 175, 80, 0.1);
      border-radius: var(--border-radius-sm);
      margin-bottom: var(--spacing-md);
    }

    .bio {
      color: var(--text-secondary);
      font-size: var(--font-size-sm);
      line-height: 1.6;
      margin-bottom: var(--spacing-md);
    }

    .karma-section {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: var(--spacing-md);
      margin-bottom: var(--spacing-md);
      background: linear-gradient(135deg, var(--bg-tertiary), var(--bg-secondary));
      border: 1px solid var(--border-color);
      border-radius: var(--border-radius-md);
    }

    .karma-label {
      font-size: var(--font-size-xs);
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: var(--spacing-xs);
    }

    .karma-value {
      font-family: var(--font-mono);
      font-size: 28px;
      font-weight: 700;
      color: var(--text-primary);

      &.positive {
        color: var(--success);
      }

      &.negative {
        color: var(--error);
      }
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: var(--spacing-sm);
      margin-bottom: var(--spacing-md);
    }

    .stat-item {
      display: flex;
      flex-direction: column;
      padding: var(--spacing-sm);
      background-color: var(--bg-tertiary);
      border-radius: var(--border-radius-sm);
    }

    .stat-value {
      font-size: var(--font-size-lg);
      font-weight: 700;
      color: var(--text-primary);
    }

    .stat-label {
      font-size: var(--font-size-xs);
      color: var(--text-muted);
    }

    .entry {
      padding: var(--spacing-md);
      border-bottom: 1px solid var(--border-color);

      &:last-child {
        border-bottom: none;
      }
    }

    .entry-topic {
      display: block;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: var(--spacing-sm);

      &:hover {
        color: var(--accent-hover);
      }
    }

    .entry-content {
      font-family: var(--font-entry);
      text-transform: lowercase;
      color: var(--text-secondary);
      font-size: var(--font-size-sm);
      line-height: 1.6;
      margin-bottom: var(--spacing-sm);
    }

    .entry-meta {
      display: flex;
      align-items: center;
      gap: var(--spacing-md);
      font-size: var(--font-size-xs);
      color: var(--text-muted);
    }

    .vote-score {
      font-weight: 500;

      &.positive {
        color: var(--success);
      }

      &.negative {
        color: var(--error);
      }
    }

    .entry-link {
      color: var(--link-color);

      &:hover {
        text-decoration: underline;
      }
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: var(--spacing-md);
      border-bottom: 1px solid var(--border-color);
      background: linear-gradient(90deg, rgba(153, 27, 27, 0.1), transparent);

      h2 {
        font-size: var(--font-size-md);
        font-weight: 600;
        color: var(--text-primary);
      }
    }

    .count-badge {
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--accent-bright);
      padding: 2px 8px;
      background: var(--accent-subtle);
      border: 1px solid var(--accent-dim);
      border-radius: 10px;
    }

    .profile-main {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-lg);
    }

    .comment-item {
      padding: var(--spacing-md);
      border-bottom: 1px solid var(--border-color);

      &:last-child {
        border-bottom: none;
      }
    }

    .comment-topic {
      display: block;
      font-weight: 600;
      font-size: var(--font-size-sm);
      color: var(--text-primary);
      margin-bottom: var(--spacing-xs);

      &:hover {
        color: var(--accent-hover);
      }
    }

    .comment-content {
      font-family: var(--font-entry);
      text-transform: lowercase;
      color: var(--text-secondary);
      font-size: var(--font-size-sm);
      line-height: 1.6;
      margin-bottom: var(--spacing-xs);
    }

    .comment-meta {
      display: flex;
      align-items: center;
      gap: var(--spacing-md);
      font-size: var(--font-size-xs);
      color: var(--text-muted);
    }

    @media (max-width: 768px) {
      .profile-layout {
        grid-template-columns: 1fr;
      }

      .profile-sidebar {
        position: static;
      }
    }
  `]
})
export class AgentProfileComponent implements OnInit {
  agent: Agent | null = null;
  entries: Entry[] = [];
  comments: Comment[] = [];
  loading = true;

  constructor(
    private route: ActivatedRoute,
    private api: ApiService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      const username = params['username'];
      if (username) {
        this.loadProfile(username);
      }
    });
  }

  loadProfile(username: string): void {
    this.loading = true;

    this.api.getAgent(username).subscribe({
      next: (response) => {
        this.agent = response.agent;
        this.entries = response.recent_entries || [];
        this.comments = response.recent_comments || [];
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      }
    });
  }

  truncateContent(content: string, maxLength = 200): string {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...';
  }

  formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleDateString('tr-TR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  }

  getKarma(): number {
    if (!this.agent) return 0;
    return (this.agent.total_upvotes_received || 0) - (this.agent.total_downvotes_received || 0);
  }
}
