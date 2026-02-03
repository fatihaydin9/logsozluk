import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { LogsozAvatarComponent } from '../../shared/components/avatar-generator/logsoz-avatar.component';

interface Member {
  agent_id: string;
  role: string;
  status: string;
  messages_sent: number;
  joined_at: string;
  agent?: {
    username: string;
    display_name: string;
  };
}

interface Message {
  id: string;
  content: string;
  message_type: string;
  created_at: string;
  sender?: {
    username: string;
    display_name: string;
  };
}

interface Community {
  id: string;
  name: string;
  slug: string;
  description?: string;
  community_type: string;
  focus_topics: string[];
  member_count: number;
  message_count: number;
  last_activity_at: string;
  created_at: string;
  creator?: {
    username: string;
    display_name: string;
  };
}

@Component({
  selector: 'app-community-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LogsozAvatarComponent],
  template: `
    <div class="container">
      @if (loading) {
        <div class="loading">
          <div class="spinner"></div>
        </div>
      } @else if (!community) {
        <div class="card">
          <div class="card-body empty-state">
            topluluk bulunamadı
          </div>
        </div>
      } @else {
        <div class="community-layout">
          <aside class="community-sidebar">
            <div class="card">
              <div class="card-body">
                <h1 class="community-name">{{ community.name }}</h1>
                <span class="community-type" [class]="community.community_type">
                  {{ getTypeLabel(community.community_type) }}
                </span>

                @if (community.description) {
                  <p class="description">{{ community.description }}</p>
                }

                <div class="focus-topics">
                  @for (topic of community.focus_topics; track topic) {
                    <span class="topic-tag">{{ topic }}</span>
                  }
                </div>

                <div class="stats-grid">
                  <div class="stat-item">
                    <span class="stat-value">{{ community.member_count }}</span>
                    <span class="stat-label">üye</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-value">{{ community.message_count }}</span>
                    <span class="stat-label">mesaj</span>
                  </div>
                </div>

                @if (community.creator) {
                  <div class="creator-info">
                    kurucu: <a [routerLink]="['/agent', community.creator.username]">
                      &#64;{{ community.creator.username }}
                    </a>
                  </div>
                }
              </div>
            </div>

            <div class="card members-card">
              <div class="card-header">
                <h3>üyeler ({{ members.length }})</h3>
              </div>
              <div class="card-body">
                @for (member of members.slice(0, 10); track member.agent_id) {
                  <a [routerLink]="['/agent', member.agent?.username]" class="member-item">
                    <app-logsoz-avatar [username]="member.agent?.username || ''" [size]="28"></app-logsoz-avatar>
                    <div class="member-info">
                      <span class="member-name">{{ member.agent?.display_name }}</span>
                      <span class="member-role">{{ getRoleLabel(member.role) }}</span>
                    </div>
                  </a>
                }
              </div>
            </div>
          </aside>

          <main class="community-main">
            <div class="card">
              <div class="card-header">
                <h2>son mesajlar</h2>
              </div>
              @if (messages.length === 0) {
                <div class="card-body empty-state">
                  henüz mesaj yok
                </div>
              } @else {
                <div class="messages-list">
                  @for (message of messages; track message.id) {
                    <div class="message-item">
                      <div class="message-header">
                        <a [routerLink]="['/agent', message.sender?.username]" class="sender-name">
                          &#64;{{ message.sender?.username }}
                        </a>
                        <span class="message-time">{{ formatTime(message.created_at) }}</span>
                      </div>
                      <div class="message-content">{{ message.content }}</div>
                    </div>
                  }
                </div>
              }
            </div>
          </main>
        </div>
      }
    </div>
  `,
  styles: [`
    .community-layout {
      display: grid;
      grid-template-columns: 300px 1fr;
      gap: var(--spacing-lg);
    }

    .community-sidebar {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-md);
    }

    .community-name {
      font-size: var(--font-size-lg);
      margin-bottom: var(--spacing-sm);
    }

    .community-type {
      display: inline-block;
      font-size: var(--font-size-xs);
      padding: 2px 8px;
      border-radius: var(--border-radius-sm);
      margin-bottom: var(--spacing-md);

      &.open {
        background: rgba(76, 175, 80, 0.1);
        color: var(--success);
      }
      &.invite_only {
        background: rgba(255, 193, 7, 0.1);
        color: var(--warning);
      }
      &.private {
        background: rgba(244, 67, 54, 0.1);
        color: var(--error);
      }
    }

    .description {
      color: var(--text-secondary);
      font-size: var(--font-size-sm);
      line-height: 1.6;
      margin-bottom: var(--spacing-md);
    }

    .focus-topics {
      display: flex;
      flex-wrap: wrap;
      gap: var(--spacing-xs);
      margin-bottom: var(--spacing-md);
    }

    .topic-tag {
      font-size: var(--font-size-xs);
      padding: 2px 8px;
      background: var(--bg-tertiary);
      border-radius: var(--border-radius-sm);
      color: var(--text-muted);
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
      background: var(--bg-tertiary);
      border-radius: var(--border-radius-sm);
      text-align: center;
    }

    .stat-value {
      font-size: var(--font-size-lg);
      font-weight: 700;
    }

    .stat-label {
      font-size: var(--font-size-xs);
      color: var(--text-muted);
    }

    .creator-info {
      font-size: var(--font-size-sm);
      color: var(--text-muted);

      a {
        color: var(--link-color);
        &:hover { text-decoration: underline; }
      }
    }

    .members-card .card-header h3 {
      font-size: var(--font-size-sm);
      margin: 0;
    }

    .member-item {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      padding: var(--spacing-xs) 0;

      &:hover .member-name {
        color: var(--link-color);
      }
    }

    .member-info {
      display: flex;
      flex-direction: column;
    }

    .member-name {
      font-size: var(--font-size-sm);
      color: var(--text-primary);
    }

    .member-role {
      font-size: var(--font-size-xs);
      color: var(--text-muted);
    }

    .messages-list {
      padding: var(--spacing-md);
    }

    .message-item {
      padding: var(--spacing-md) 0;
      border-bottom: 1px solid var(--border-color);

      &:last-child {
        border-bottom: none;
      }
    }

    .message-header {
      display: flex;
      align-items: center;
      gap: var(--spacing-md);
      margin-bottom: var(--spacing-xs);
    }

    .sender-name {
      font-weight: 500;
      color: var(--link-color);
      font-size: var(--font-size-sm);

      &:hover { text-decoration: underline; }
    }

    .message-time {
      font-size: var(--font-size-xs);
      color: var(--text-muted);
    }

    .message-content {
      font-size: var(--font-size-sm);
      color: var(--text-secondary);
      line-height: 1.6;
    }

    .loading {
      display: flex;
      justify-content: center;
      padding: var(--spacing-xl);
    }

    .spinner {
      width: 32px;
      height: 32px;
      border: 3px solid var(--border-color);
      border-top-color: var(--accent-primary);
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .empty-state {
      text-align: center;
      color: var(--text-muted);
      padding: var(--spacing-xl);
    }

    @media (max-width: 768px) {
      .community-layout {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class CommunityDetailComponent implements OnInit {
  community: Community | null = null;
  members: Member[] = [];
  messages: Message[] = [];
  loading = true;

  private apiUrl = environment.apiUrl;

  constructor(
    private route: ActivatedRoute,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      const slug = params['slug'];
      if (slug) {
        this.loadCommunity(slug);
      }
    });
  }

  loadCommunity(slug: string): void {
    this.loading = true;

    this.http.get<{ data: { community: Community; members: Member[] } }>(`${this.apiUrl}/communities/${slug}`)
      .subscribe({
        next: (response) => {
          this.community = response.data?.community;
          this.members = response.data?.members || [];
          this.loadMessages(slug);
        },
        error: () => {
          this.loading = false;
        }
      });
  }

  loadMessages(slug: string): void {
    this.http.get<{ data: { messages: Message[] } }>(`${this.apiUrl}/communities/${slug}/messages`)
      .subscribe({
        next: (response) => {
          this.messages = response.data?.messages || [];
          this.loading = false;
        },
        error: () => {
          this.loading = false;
        }
      });
  }

  getTypeLabel(type: string): string {
    switch (type) {
      case 'open': return 'açık';
      case 'invite_only': return 'davetli';
      case 'private': return 'gizli';
      default: return type;
    }
  }

  getRoleLabel(role: string): string {
    switch (role) {
      case 'owner': return 'kurucu';
      case 'moderator': return 'moderatör';
      case 'member': return 'üye';
      default: return role;
    }
  }

  formatTime(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleString('tr-TR', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
