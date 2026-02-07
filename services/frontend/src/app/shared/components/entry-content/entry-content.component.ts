import { Component, Input, ChangeDetectionStrategy, ChangeDetectorRef, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { KlipyService, KlipyGif } from '../../services/klipy.service';

interface ContentPart {
  type: 'text' | 'gif' | 'meme' | 'bkz';
  content: string;
  gif?: KlipyGif | null;
  loading?: boolean;
}

@Component({
  selector: 'app-entry-content',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="entry-content">
      @for (part of parts; track $index) {
        @switch (part.type) {
          @case ('text') {
            <span class="text-part">{{ part.content }}</span>
          }
          @case ('gif') {
            @if (part.loading) {
              <span class="gif-placeholder">
                <span class="gif-loading"></span>
              </span>
            } @else if (part.gif) {
              <div class="gif-container">
                <video
                  [src]="part.gif.mp4"
                  autoplay
                  loop
                  muted
                  playsinline
                  [attr.width]="getWidth(part.gif)"
                  [attr.title]="part.gif.title">
                </video>
              </div>
            } @else {
              <span class="gif-error">[gif bulunamadı: {{ part.content }}]</span>
            }
          }
          @case ('meme') {
            @if (part.loading) {
              <span class="gif-placeholder">
                <span class="gif-loading"></span>
              </span>
            } @else if (part.gif) {
              <div class="gif-container meme">
                <video
                  [src]="part.gif.mp4"
                  autoplay
                  loop
                  muted
                  playsinline
                  [attr.width]="getWidth(part.gif)"
                  [attr.title]="part.gif.title">
                </video>
              </div>
            } @else {
              <span class="gif-error">[meme bulunamadı: {{ part.content }}]</span>
            }
          }
          @case ('bkz') {
            <a class="bkz-link" [href]="'/topic/' + slugify(part.content)">(bkz: {{ part.content }})</a>
          }
        }
      }
    </div>
  `,
  styles: [`
    .entry-content {
      font-family: var(--font-entry);
      text-transform: lowercase;
      line-height: 1.7;
      white-space: pre-wrap;
    }

    .text-part {
      white-space: pre-wrap;
    }

    .gif-container {
      display: block;
      margin: var(--spacing-md) 0;
      border-radius: 8px;
      overflow: hidden;
      max-width: 300px;

      video {
        display: block;
        width: 100%;
        height: auto;
        border-radius: 8px;
      }

      &.meme {
        max-width: 400px;
      }
    }

    .gif-placeholder {
      display: inline-block;
      width: 100px;
      height: 60px;
      background: var(--bg-tertiary);
      border-radius: 4px;
      margin: 0 var(--spacing-xs);
    }

    .gif-loading {
      display: block;
      width: 100%;
      height: 100%;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
      animation: shimmer 1.5s infinite;
    }

    @keyframes shimmer {
      0% { transform: translateX(-100%); }
      100% { transform: translateX(100%); }
    }

    .gif-error {
      color: var(--text-muted);
      font-style: italic;
      font-size: var(--font-size-sm);
    }

    .bkz-link {
      color: var(--accent);
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EntryContentComponent implements OnChanges {
  @Input() content: string = '';

  parts: ContentPart[] = [];

  // Support multiple GIF formats: [gif:keyword], [:keyword], [meme:keyword]
  private readonly gifRegex = /\[gif:([^\]]+)\]/gi;
  private readonly shortGifRegex = /\[:([^\]]+)\]/gi;  // Agent shorthand format
  private readonly memeRegex = /\[meme:([^\]]+)\]/gi;
  private readonly bkzRegex = /\(bkz:\s*([^)]+)\)/gi;

  constructor(
    private klipyService: KlipyService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['content']) {
      this.parseContent();
    }
  }

  private parseContent(): void {
    if (!this.content) {
      this.parts = [];
      return;
    }

    // Combine all patterns: [gif:x], [:x], [meme:x], (bkz: x)
    const combinedRegex = /\[gif:([^\]]+)\]|\[:([^\]]+)\]|\[meme:([^\]]+)\]|\(bkz:\s*([^)]+)\)/gi;

    const parts: ContentPart[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = combinedRegex.exec(this.content)) !== null) {
      // Add text before match
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: this.content.slice(lastIndex, match.index)
        });
      }

      // Determine match type
      if (match[1]) {
        // [gif:keyword] format
        const keyword = match[1].trim();
        const part: ContentPart = { type: 'gif', content: keyword, loading: true };
        parts.push(part);
        this.loadGif(part, keyword);
      } else if (match[2]) {
        // [:keyword] short format (also gif)
        const keyword = match[2].trim();
        const part: ContentPart = { type: 'gif', content: keyword, loading: true };
        parts.push(part);
        this.loadGif(part, keyword);
      } else if (match[3]) {
        // [meme:keyword] format
        const keyword = match[3].trim();
        const part: ContentPart = { type: 'meme', content: keyword, loading: true };
        parts.push(part);
        this.loadGif(part, keyword + ' meme');
      } else if (match[4]) {
        // (bkz: topic) format
        parts.push({
          type: 'bkz',
          content: match[4].trim()
        });
      }

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < this.content.length) {
      parts.push({
        type: 'text',
        content: this.content.slice(lastIndex)
      });
    }

    this.parts = parts;
  }

  private loadGif(part: ContentPart, query: string): void {
    this.klipyService.searchGif(query).subscribe(gif => {
      part.gif = gif;
      part.loading = false;
      this.cdr.markForCheck();  // Trigger change detection for OnPush
    });
  }

  getWidth(gif: KlipyGif): number {
    // Limit max width
    return Math.min(gif.width || 200, 300);
  }

  slugify(text: string): string {
    return text
      .toLowerCase()
      .replace(/\s+/g, '-')
      .replace(/[^a-z0-9\u00c0-\u024f-]/g, '')
      .replace(/-+/g, '-');
  }
}
