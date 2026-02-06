import { Component, Input, OnChanges, SimpleChanges, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { AvatarGeneratorService } from './avatar-generator.service';
import { AvatarConfig, COLORS, DEFAULT_AVATAR } from './avatar.types';

@Component({
  selector: 'app-logsoz-avatar',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="logsoz-avatar"
      [class.has-ring]="ringVisible"
      [style.width.px]="size"
      [style.height.px]="size"
      [style.--avatar-color]="avatarColor"
      [style.--ring-width.px]="ringWidth"
    >
      <div class="avatar-inner" [innerHTML]="avatarSvg"></div>
    </div>
  `,
  styles: [`
    .logsoz-avatar {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      overflow: hidden;
      background: #ECECEC;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .logsoz-avatar.has-ring {
      border: var(--ring-width) solid var(--avatar-color);
      box-shadow: 0 0 8px color-mix(in srgb, var(--avatar-color) 40%, transparent);
    }

    .logsoz-avatar.has-ring:hover {
      transform: scale(1.08);
      box-shadow: 0 0 14px color-mix(in srgb, var(--avatar-color) 60%, transparent);
    }

    .avatar-inner {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    :host ::ng-deep svg {
      width: 100%;
      height: 100%;
    }
  `]
})
export class LogsozAvatarComponent implements OnChanges {
  @Input() username?: string;
  @Input() config?: AvatarConfig;
  @Input() size: number = 48;
  @Input() showRing: boolean = true;

  avatarSvg: SafeHtml = '';
  avatarColor: string = '#E74C3C';
  ringWidth: number = 4;
  ringVisible: boolean = true;

  constructor(
    private avatarService: AvatarGeneratorService,
    private sanitizer: DomSanitizer
  ) {}

  ngOnChanges(changes: SimpleChanges): void {
    this.generateAvatar();
  }

  private generateAvatar(): void {
    let avatarConfig: AvatarConfig;

    if (this.config) {
      avatarConfig = this.config;
    } else if (this.username) {
      avatarConfig = this.avatarService.generateFromSeed(this.username);
    } else {
      avatarConfig = DEFAULT_AVATAR;
    }

    this.avatarColor = COLORS[avatarConfig.color].main;
    this.ringWidth = Math.max(2, Math.round(this.size * 0.06));
    this.ringVisible = this.showRing && this.size >= 32;

    const svg = this.avatarService.generateSVG(avatarConfig, this.size);
    this.avatarSvg = this.sanitizer.bypassSecurityTrustHtml(svg);
  }
}
