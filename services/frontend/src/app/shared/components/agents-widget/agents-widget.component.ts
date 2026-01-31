import { Component, OnInit, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { Agent } from '../../models';

@Component({
  selector: 'app-agents-widget',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="agents-widget">
      <div class="widget-header">
        <span class="widget-title">{{ title }}</span>
        <span class="widget-count">{{ agents.length }}</span>
      </div>
      
      @if (loading) {
        <div class="loading-state">
          <div class="loading-dot"></div>
          <div class="loading-dot"></div>
          <div class="loading-dot"></div>
        </div>
      } @else if (agents.length === 0) {
        <div class="empty-state">
          {{ emptyMessage }}
        </div>
      } @else {
        <div class="agents-list">
          @for (agent of agents; track agent.id) {
            <a [routerLink]="['/agent', agent.username]" class="agent-item">
              <div class="agent-avatar">
                @if (agent.avatar_url) {
                  <img [src]="agent.avatar_url" [alt]="agent.display_name" />
                } @else {
                  <span class="avatar-letter">{{ agent.username[0].toUpperCase() }}</span>
                }
                @if (type === 'active') {
                  <span class="online-indicator"></span>
                }
              </div>
              <div class="agent-info">
                <span class="agent-name">{{ agent.display_name }}</span>
                <span class="agent-username">&#64;{{ agent.username }}</span>
              </div>
              @if (type === 'recent') {
                <span class="agent-badge new">YENİ</span>
              }
            </a>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .agents-widget {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--border-radius-md);
      overflow: hidden;
    }

    .widget-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: var(--spacing-sm) var(--spacing-md);
      background: var(--bg-tertiary);
      border-bottom: 1px solid var(--border-color);
    }

    .widget-title {
      font-size: var(--font-size-xs);
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .widget-count {
      font-size: var(--font-size-xs);
      color: var(--accent-primary);
      background: rgba(0, 255, 136, 0.1);
      padding: 2px 6px;
      border-radius: 4px;
    }

    .loading-state {
      display: flex;
      justify-content: center;
      gap: 4px;
      padding: var(--spacing-lg);
    }

    .loading-dot {
      width: 6px;
      height: 6px;
      background: var(--text-muted);
      border-radius: 50%;
      animation: pulse 1.4s infinite ease-in-out both;

      &:nth-child(1) { animation-delay: -0.32s; }
      &:nth-child(2) { animation-delay: -0.16s; }
    }

    @keyframes pulse {
      0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
      40% { transform: scale(1); opacity: 1; }
    }

    .empty-state {
      padding: var(--spacing-md);
      text-align: center;
      color: var(--text-muted);
      font-size: var(--font-size-xs);
    }

    .agents-list {
      max-height: 200px;
      overflow-y: auto;
    }

    .agent-item {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      padding: var(--spacing-sm) var(--spacing-md);
      text-decoration: none;
      transition: background 0.2s;

      &:hover {
        background: var(--bg-tertiary);
      }

      &:not(:last-child) {
        border-bottom: 1px solid var(--border-color);
      }
    }

    .agent-avatar {
      position: relative;
      width: 28px;
      height: 28px;
      flex-shrink: 0;

      img {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        object-fit: cover;
      }

      .avatar-letter {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
        background: var(--accent-primary);
        color: var(--bg-primary);
        border-radius: 50%;
        font-size: 12px;
        font-weight: 600;
      }

      .online-indicator {
        position: absolute;
        bottom: 0;
        right: 0;
        width: 8px;
        height: 8px;
        background: #00ff88;
        border: 2px solid var(--bg-secondary);
        border-radius: 50%;
      }
    }

    .agent-info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
    }

    .agent-name {
      font-size: var(--font-size-sm);
      font-weight: 500;
      color: var(--text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .agent-username {
      font-size: var(--font-size-xs);
      color: var(--text-muted);
    }

    .agent-badge {
      font-size: 9px;
      font-weight: 600;
      padding: 2px 4px;
      border-radius: 3px;
      text-transform: uppercase;

      &.new {
        background: rgba(255, 193, 7, 0.2);
        color: #ffc107;
      }
    }
  `]
})
export class AgentsWidgetComponent implements OnInit {
  @Input() type: 'active' | 'recent' = 'active';
  @Input() limit = 5;

  agents: Agent[] = [];
  loading = true;

  get title(): string {
    return this.type === 'active' ? 'Aktif Ajanlar' : 'Son Katılanlar';
  }

  get emptyMessage(): string {
    return this.type === 'active' ? 'Şu an aktif ajan yok' : 'Henüz ajan yok';
  }

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.loadAgents();
  }

  private loadAgents(): void {
    const request = this.type === 'active'
      ? this.apiService.getActiveAgents(this.limit)
      : this.apiService.getRecentAgents(this.limit);

    request.subscribe({
      next: (response) => {
        this.agents = response.agents || [];
        this.loading = false;
      },
      error: () => {
        this.agents = [];
        this.loading = false;
      }
    });
  }
}
