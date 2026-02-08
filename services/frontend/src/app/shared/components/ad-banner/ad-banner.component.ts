import {
  AfterViewInit,
  Component,
  ElementRef,
  Inject,
  Input,
  PLATFORM_ID,
  ViewChild,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

declare global {
  interface Window {
    adsbygoogle: any[];
  }
}

@Component({
  selector: 'app-ad-banner',
  standalone: true,
  template: `
    <div class="ad-wrapper" [class.full-width]="fullWidth">
      <span class="ad-label">reklam</span>
      <div class="ad-slot" #adContainer>
        <ins class="adsbygoogle"
          [style.display]="'block'"
          [attr.data-ad-client]="'ca-pub-4502512303411179'"
          [attr.data-ad-slot]="adSlot"
          [attr.data-ad-format]="adFormat"
          [attr.data-full-width-responsive]="fullWidth ? 'true' : null">
        </ins>
      </div>
    </div>
  `,
  styles: [`
    .ad-wrapper {
      position: relative;
      width: 100%;
      min-height: 100px;
      background: rgba(28, 28, 32, 0.6);
      border: 1px solid rgba(63, 63, 70, 0.4);
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .ad-label {
      display: block;
      text-align: center;
      font-size: 9px;
      color: rgba(113, 113, 122, 0.5);
      text-transform: uppercase;
      letter-spacing: 0.1em;
      padding: 4px 0 2px;
    }

    .ad-slot {
      width: 100%;
      display: flex;
      justify-content: center;

      ins {
        width: 100%;
      }
    }

    .full-width {
      border-radius: 0;
      border-left: none;
      border-right: none;
    }
  `],
})
export class AdBannerComponent implements AfterViewInit {
  @Input() adSlot = '';
  @Input() adFormat: 'auto' | 'horizontal' | 'rectangle' = 'auto';
  @Input() fullWidth = false;

  @ViewChild('adContainer') adContainer!: ElementRef;

  private isBrowser: boolean;

  constructor(@Inject(PLATFORM_ID) platformId: Object) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  ngAfterViewInit(): void {
    if (!this.isBrowser) return;

    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch {
      // AdSense not loaded yet or ad blocker active
    }
  }
}
