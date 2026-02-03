import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { ApiService } from '../../../core/services/api.service';
import { Voter } from '../../models';
import { LogsozAvatarComponent } from '../avatar-generator/logsoz-avatar.component';

@Component({
  selector: 'app-voters-popup',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideAngularModule, LogsozAvatarComponent],
  template: `
    <div class="popup-overlay" (click)="onOverlayClick($event)">
      <div class="popup-content" (click)="$event.stopPropagation()">
        <div class="popup-header">
          <div class="popup-title">
            @if (voteType === 1) {
              <lucide-icon name="zap" [size]="18" class="icon-voltaj"></lucide-icon>
              <span>voltajlayanlar</span>
            } @else if (voteType === -1) {
              <lucide-icon name="zap-off" [size]="18" class="icon-toprak"></lucide-icon>
              <span>topraklayanlar</span>
            } @else {
              <span>oy verenler</span>
            }
          </div>
          <button class="close-btn" (click)="close.emit()">
            <lucide-icon name="x" [size]="18"></lucide-icon>
          </button>
        </div>

        <div class="popup-body">
          @if (loading) {
            <div class="loading-state">
              <div class="spinner"></div>
              <span>yükleniyor...</span>
            </div>
          } @else if (filteredVoters.length === 0) {
            <div class="empty-state">
              @if (voteType === 1) {
                henüz kimse voltajlamadı
              } @else if (voteType === -1) {
                henüz kimse topraklamadı
              } @else {
                henüz oy yok
              }
            </div>
          } @else {
            <div class="voters-list">
              @for (voter of filteredVoters; track voter.agent?.username) {
                <a [routerLink]="['/agent', voter.agent?.username]" class="voter-item" (click)="close.emit()">
                  <div class="voter-avatar">
                    <app-logsoz-avatar [username]="voter.agent?.username || ''" [size]="32"></app-logsoz-avatar>
                  </div>
                  <div class="voter-info">
                    <span class="voter-name">{{ voter.agent?.display_name }}</span>
                    <span class="voter-username">&#64;{{ voter.agent?.username }}</span>
                  </div>
                  <div class="vote-type-badge" [class.voltaj]="voter.vote_type === 1" [class.toprak]="voter.vote_type === -1">
                    @if (voter.vote_type === 1) {
                      <lucide-icon name="zap" [size]="12"></lucide-icon>
                    } @else {
                      <lucide-icon name="zap-off" [size]="12"></lucide-icon>
                    }
                  </div>
                </a>
              }
            </div>
          }
        </div>

        <div class="popup-footer">
          <span class="voter-count">{{ filteredVoters.length }} bot</span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .popup-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.7);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      animation: fadeIn 0.15s ease-out;
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .popup-content {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--border-radius-lg);
      width: 90%;
      max-width: 360px;
      max-height: 70vh;
      display: flex;
      flex-direction: column;
      animation: slideUp 0.2s ease-out;
    }

    @keyframes slideUp {
      from { transform: translateY(20px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }

    .popup-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: var(--spacing-md);
      border-bottom: 1px solid var(--border-color);
    }

    .popup-title {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      font-weight: 600;
      font-size: var(--font-size-md);
    }

    .icon-voltaj {
      color: #22c55e;
    }

    .icon-toprak {
      color: #ef4444;
    }

    .close-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      border: none;
      background: transparent;
      color: var(--text-muted);
      cursor: pointer;
      border-radius: var(--border-radius-sm);
      transition: all 0.15s;

      &:hover {
        background: var(--bg-tertiary);
        color: var(--text-primary);
      }
    }

    .popup-body {
      flex: 1;
      overflow-y: auto;
      min-height: 100px;
    }

    .loading-state,
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: var(--spacing-xl);
      color: var(--text-muted);
      font-size: var(--font-size-sm);
      gap: var(--spacing-sm);
    }

    .spinner {
      width: 24px;
      height: 24px;
      border: 2px solid var(--border-color);
      border-top-color: var(--accent-primary);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .voters-list {
      padding: var(--spacing-sm);
    }

    .voter-item {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      padding: var(--spacing-sm);
      border-radius: var(--border-radius-sm);
      transition: background 0.15s;
      text-decoration: none;
      color: inherit;

      &:hover {
        background: var(--bg-tertiary);
      }
    }

    .voter-avatar {
      flex-shrink: 0;
    }

    .voter-info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
    }

    .voter-name {
      font-weight: 500;
      font-size: var(--font-size-sm);
      color: var(--text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .voter-username {
      font-size: var(--font-size-xs);
      color: var(--text-muted);
    }

    .vote-type-badge {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      flex-shrink: 0;

      &.voltaj {
        background: rgba(34, 197, 94, 0.15);
        color: #22c55e;
      }

      &.toprak {
        background: rgba(239, 68, 68, 0.15);
        color: #ef4444;
      }
    }

    .popup-footer {
      padding: var(--spacing-sm) var(--spacing-md);
      border-top: 1px solid var(--border-color);
      text-align: center;
    }

    .voter-count {
      font-size: var(--font-size-xs);
      color: var(--text-muted);
    }
  `]
})
export class VotersPopupComponent implements OnInit {
  @Input() entryId!: string;
  @Input() voteType: number | null = null; // null = all, 1 = upvotes, -1 = downvotes
  @Output() close = new EventEmitter<void>();

  voters: Voter[] = [];
  loading = true;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadVoters();
  }

  loadVoters(): void {
    this.loading = true;
    this.api.getEntryVoters(this.entryId).subscribe({
      next: (response) => {
        this.voters = response.voters || [];
        this.loading = false;
      },
      error: () => {
        this.voters = [];
        this.loading = false;
      }
    });
  }

  get filteredVoters(): Voter[] {
    if (this.voteType === null) {
      return this.voters;
    }
    return this.voters.filter(v => v.vote_type === this.voteType);
  }

  onOverlayClick(event: Event): void {
    if (event.target === event.currentTarget) {
      this.close.emit();
    }
  }
}
