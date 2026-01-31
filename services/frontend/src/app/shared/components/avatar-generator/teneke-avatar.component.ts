import { Component, Input, OnChanges, SimpleChanges, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { AvatarGeneratorService } from './avatar-generator.service';
import { AvatarConfig, DEFAULT_AVATAR } from './avatar.types';

@Component({
  selector: 'app-teneke-avatar',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="teneke-avatar"
      [style.width.px]="size"
      [style.height.px]="size"
      [innerHTML]="avatarSvg"
    ></div>
  `,
  styles: [`
    .teneke-avatar {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      overflow: hidden;
      background: #E8E8E8;
    }

    :host ::ng-deep svg {
      width: 100%;
      height: 100%;
    }
  `]
})
export class TenekeAvatarComponent implements OnChanges {
  @Input() username?: string;
  @Input() config?: AvatarConfig;
  @Input() size: number = 48;

  avatarSvg: SafeHtml = '';

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

    const svg = this.avatarService.generateSVG(avatarConfig, this.size);
    this.avatarSvg = this.sanitizer.bypassSecurityTrustHtml(svg);
  }
}
