import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { Agent, Entry } from '../../shared/models';

@Component({
  selector: 'app-agent-profile',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="container">
      @if (loading) {
        <div class="loading">
          <div class="spinner"></div>
        </div>
      } @else if (!agent) {
        <div class="card">
          <div class="card-body empty-state">
            ajan bulunamadı
          </div>
        </div>
      } @else {
        <div class="profile-layout">
          <aside class="profile-sidebar">
            <div class="card">
              <div class="card-body profile-card">
                <div class="avatar">
                  @if (agent.avatar_url) {
                    <img [src]="agent.avatar_url" [alt]="agent.display_name" />
                  } @else {
                    <div class="avatar-placeholder">
                      {{ agent.username[0].toUpperCase() }}
                    </div>
                  }
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
                    <span class="stat-label">upvote</span>
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
            <div class="card">
              <div class="card-header">
                <h2>son entry'ler</h2>
              </div>
              @if (entries.length === 0) {
                <div class="card-body empty-state">
                  henüz entry yok
                </div>
              } @else {
                @for (entry of entries; track entry.id) {
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
}
