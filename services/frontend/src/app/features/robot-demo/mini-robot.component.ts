import {
  Component, ElementRef, ViewChild, AfterViewInit, OnDestroy, Input,
  ChangeDetectionStrategy,
} from '@angular/core';
import * as THREE from 'three';

@Component({
  selector: 'app-mini-robot',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div #c class="mini-robot"></div>`,
  styles: [`:host{display:block}.mini-robot{width:100%;height:100%}`],
})
export class MiniRobotComponent implements AfterViewInit, OnDestroy {
  @Input() size = 220;
  @ViewChild('c', { static: true }) container!: ElementRef<HTMLDivElement>;
  private renderer!: THREE.WebGLRenderer;
  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private animId = 0;
  private monitor!: THREE.Group;
  private screenCtx!: CanvasRenderingContext2D;
  private screenTexture!: THREE.CanvasTexture;
  private blinkOn = true;
  private fc = 0;

  ngAfterViewInit(): void {
    const el = this.container.nativeElement;
    el.style.width = this.size + 'px';
    el.style.height = this.size + 'px';

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
    this.camera.position.set(0, 0, 5);
    this.camera.lookAt(0, 0, 0);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(this.size, this.size);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.setClearColor(0x000000, 0);
    el.appendChild(this.renderer.domElement);

    this.monitor = this.buildMonitor();
    this.scene.add(this.monitor);
    this.animate();
  }

  ngOnDestroy(): void {
    cancelAnimationFrame(this.animId);
    this.renderer.dispose();
  }

  private animate = (): void => {
    this.animId = requestAnimationFrame(this.animate);
    this.fc++;
    if (this.fc % 40 === 0) {
      this.blinkOn = !this.blinkOn;
      this.drawScreen();
    }
    this.monitor.rotation.y = Math.sin(this.fc * 0.008) * 0.4;
    this.monitor.rotation.x = Math.sin(this.fc * 0.005) * 0.05;
    this.renderer.render(this.scene, this.camera);
  };

  private mat(): THREE.MeshBasicMaterial {
    return new THREE.MeshBasicMaterial({ color: 0x8b0000, wireframe: true });
  }
  private w(g: THREE.BufferGeometry): THREE.Mesh {
    return new THREE.Mesh(g, this.mat());
  }

  /* ------------------------------------------------------------------ */
  /*  Screen texture                                                     */
  /* ------------------------------------------------------------------ */

  private createScreen(): THREE.Mesh {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 320;
    this.screenCtx = canvas.getContext('2d')!;
    this.screenTexture = new THREE.CanvasTexture(canvas);
    this.screenTexture.minFilter = THREE.LinearFilter;
    this.drawScreen();
    return new THREE.Mesh(
      new THREE.PlaneGeometry(2.2, 1.38),
      new THREE.MeshBasicMaterial({ map: this.screenTexture, transparent: false })
    );
  }

  private drawScreen(): void {
    const ctx = this.screenCtx;
    if (!ctx) return;
    const W = 512, H = 320;

    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, W, H);

    // scanlines
    ctx.strokeStyle = 'rgba(255, 0, 0, 0.025)';
    for (let y = 0; y < H; y += 3) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }

    // glow
    ctx.shadowColor = '#ff0000';
    ctx.shadowBlur = 20;

    ctx.font = 'bold 90px monospace';
    ctx.fillStyle = '#ff0000';
    ctx.fillText(this.blinkOn ? '> _' : '>', 30, 200);

    ctx.shadowBlur = 0;
    this.screenTexture.needsUpdate = true;
  }

  /* ------------------------------------------------------------------ */
  /*  Detailed CRT Monitor                                               */
  /* ------------------------------------------------------------------ */

  private buildMonitor(): THREE.Group {
    const m = new THREE.Group();

    // --- Main casing ---
    const casing = this.w(new THREE.BoxGeometry(2.6, 1.8, 1.3, 1, 1, 1));
    m.add(casing);

    // --- Screen ---
    const screen = this.createScreen();
    screen.position.set(0, 0.05, 0.66);
    m.add(screen);

    // --- Bezel frame (inner) ---
    const bezel = this.w(new THREE.BoxGeometry(2.3, 1.48, 0.04, 1, 1, 1));
    bezel.position.set(0, 0.05, 0.64);
    m.add(bezel);

    // --- Outer bezel rim (thicker frame edge) ---
    // top
    const rimT = this.w(new THREE.BoxGeometry(2.5, 0.06, 0.15, 1, 1, 1));
    rimT.position.set(0, 0.82, 0.6);
    m.add(rimT);
    // bottom
    const rimB = this.w(new THREE.BoxGeometry(2.5, 0.06, 0.15, 1, 1, 1));
    rimB.position.set(0, -0.72, 0.6);
    m.add(rimB);
    // left
    const rimL = this.w(new THREE.BoxGeometry(0.06, 1.48, 0.15, 1, 1, 1));
    rimL.position.set(-1.22, 0.05, 0.6);
    m.add(rimL);
    // right
    const rimR = this.w(new THREE.BoxGeometry(0.06, 1.48, 0.15, 1, 1, 1));
    rimR.position.set(1.22, 0.05, 0.6);
    m.add(rimR);

    // --- Corner screws on bezel (4 corners) ---
    for (const sx of [-1, 1]) {
      for (const sy of [-1, 1]) {
        // screw body
        const screw = this.w(new THREE.CylinderGeometry(0.05, 0.05, 0.08, 6));
        screw.rotation.x = Math.PI / 2;
        screw.position.set(sx * 1.08, sy * 0.68 + 0.05, 0.69);
        m.add(screw);
        // screw slot (cross line)
        const slot = this.w(new THREE.BoxGeometry(0.06, 0.01, 0.01));
        slot.position.set(sx * 1.08, sy * 0.68 + 0.05, 0.74);
        m.add(slot);
      }
    }

    // --- CRT back bulge ---
    const back = this.w(new THREE.BoxGeometry(2.0, 1.3, 0.8, 1, 1, 1));
    back.position.set(0, 0, -1.05);
    m.add(back);

    // --- Back vent grille (horizontal lines) ---
    for (let i = 0; i < 5; i++) {
      const vent = this.w(new THREE.BoxGeometry(1.2, 0.02, 0.02));
      vent.position.set(0, 0.35 - i * 0.15, -1.46);
      m.add(vent);
    }

    // --- Back panel screws ---
    for (const sx of [-1, 1]) {
      for (const sy of [-1, 1]) {
        const bs = this.w(new THREE.CylinderGeometry(0.04, 0.04, 0.06, 6));
        bs.rotation.x = Math.PI / 2;
        bs.position.set(sx * 0.85, sy * 0.5, -1.46);
        m.add(bs);
      }
    }

    // --- Side panel details ---
    for (const side of [-1, 1]) {
      // vent slots on sides
      for (let i = 0; i < 4; i++) {
        const sv = this.w(new THREE.BoxGeometry(0.02, 0.02, 0.6));
        sv.position.set(side * 1.31, 0.3 - i * 0.15, -0.2);
        m.add(sv);
      }
      // side screws
      for (const sy of [-1, 1]) {
        const ss = this.w(new THREE.CylinderGeometry(0.04, 0.04, 0.06, 6));
        ss.rotation.z = Math.PI / 2;
        ss.position.set(side * 1.32, sy * 0.65, 0);
        m.add(ss);
      }
    }

    // --- Power LED (bottom right of bezel) ---
    const led = this.w(new THREE.SphereGeometry(0.04, 6, 6));
    led.position.set(1.0, -0.68, 0.67);
    m.add(led);

    // --- Power button (bottom right) ---
    const pwrBtn = this.w(new THREE.CylinderGeometry(0.06, 0.06, 0.06, 8));
    pwrBtn.rotation.x = Math.PI / 2;
    pwrBtn.position.set(0.8, -0.68, 0.67);
    m.add(pwrBtn);

    // --- Bottom label plate ---
    const label = this.w(new THREE.BoxGeometry(0.6, 0.08, 0.04, 1, 1, 1));
    label.position.set(0, -0.72, 0.67);
    m.add(label);

    // --- Antenna ---
    const antenna = this.w(new THREE.CylinderGeometry(0.025, 0.025, 0.6, 4));
    antenna.position.set(0, 1.2, 0);
    m.add(antenna);
    const antTip = this.w(new THREE.SphereGeometry(0.07, 6, 6));
    antTip.position.set(0, 1.55, 0);
    m.add(antTip);

    // --- Small stand/base ---
    const standNeck = this.w(new THREE.CylinderGeometry(0.15, 0.2, 0.3, 6));
    standNeck.position.set(0, -1.05, 0);
    m.add(standNeck);

    const standBase = this.w(new THREE.BoxGeometry(1.2, 0.08, 0.8, 1, 1, 1));
    standBase.position.set(0, -1.24, 0);
    m.add(standBase);

    // stand base screws
    for (const sx of [-1, 1]) {
      const sbs = this.w(new THREE.CylinderGeometry(0.03, 0.03, 0.04, 6));
      sbs.position.set(sx * 0.45, -1.19, 0);
      m.add(sbs);
    }

    // --- Rubber feet ---
    for (const sx of [-1, 1]) {
      for (const sz of [-1, 1]) {
        const foot = this.w(new THREE.CylinderGeometry(0.06, 0.06, 0.04, 6));
        foot.position.set(sx * 0.5, -1.3, sz * 0.3);
        m.add(foot);
      }
    }

    return m;
  }
}
