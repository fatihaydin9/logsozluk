import { Component, ChangeDetectionStrategy } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-wireframe-gallery',
  standalone: true,
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="gallery">
      <h1>3D Wireframe Gallery</h1>
      <div class="grid">
        @for (item of items; track item.path) {
          <a [routerLink]="item.path" class="card">
            <div class="icon">{{ item.icon }}</div>
            <div class="name">{{ item.name }}</div>
            <div class="desc">{{ item.desc }}</div>
          </a>
        }
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      min-height: 100vh;
      background: #000;
      color: #ff0000;
    }
    .gallery {
      max-width: 900px;
      margin: 0 auto;
      padding: 48px 24px;
    }
    h1 {
      text-align: center;
      font-family: monospace;
      font-size: 28px;
      margin-bottom: 48px;
      letter-spacing: 2px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 24px;
    }
    .card {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 32px 16px;
      border: 1px solid #ff0000;
      text-decoration: none;
      color: #ff0000;
      font-family: monospace;
      transition: background 0.2s, transform 0.2s;
      cursor: pointer;
    }
    .card:hover {
      background: rgba(255, 0, 0, 0.08);
      transform: translateY(-4px);
    }
    .icon {
      font-size: 48px;
      margin-bottom: 16px;
    }
    .name {
      font-size: 18px;
      font-weight: bold;
      margin-bottom: 8px;
    }
    .desc {
      font-size: 12px;
      opacity: 0.7;
      text-align: center;
    }
  `],
})
export class WireframeGalleryComponent {
  items = [
    { path: '/robot', icon: '🤖', name: 'Robot', desc: 'Vintage kurmalı robot' },
    { path: '/wireframe/astronaut', icon: '🧑‍🚀', name: 'Astronaut', desc: 'Uzay giysili astronot' },
    { path: '/wireframe/dino', icon: '🦖', name: 'T-Rex', desc: 'Dinozor T-Rex' },
    { path: '/wireframe/spider', icon: '🕷️', name: 'Spider Mech', desc: 'Mekanik örümcek' },
    { path: '/wireframe/skull', icon: '💀', name: 'Skull', desc: 'Anatomik kafatası' },
  ];
}
