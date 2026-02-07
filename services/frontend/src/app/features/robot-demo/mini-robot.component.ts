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
  @Input() size = 180;
  @ViewChild('c', { static: true }) container!: ElementRef<HTMLDivElement>;
  private renderer!: THREE.WebGLRenderer;
  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private animId = 0;
  private robot!: THREE.Group;
  private screenCtx!: CanvasRenderingContext2D;
  private screenTexture!: THREE.CanvasTexture;
  private blinkOn = true;
  private fc = 0;

  ngAfterViewInit(): void {
    const el = this.container.nativeElement;
    el.style.width = this.size + 'px';
    el.style.height = this.size + 'px';

    this.scene = new THREE.Scene();
    // transparent background
    this.camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
    this.camera.position.set(0, 2, 10);
    this.camera.lookAt(0, 1.8, 0);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(this.size, this.size);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.setClearColor(0x000000, 0);
    el.appendChild(this.renderer.domElement);

    this.robot = this.build();
    this.scene.add(this.robot);
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
    this.robot.rotation.y += 0.005;
    this.renderer.render(this.scene, this.camera);
  };

  private mat(): THREE.MeshBasicMaterial {
    return new THREE.MeshBasicMaterial({ color: 0xff0000, wireframe: true });
  }
  private w(g: THREE.BufferGeometry): THREE.Mesh {
    return new THREE.Mesh(g, this.mat());
  }

  private createScreen(): THREE.Mesh {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 160;
    this.screenCtx = canvas.getContext('2d')!;
    this.screenTexture = new THREE.CanvasTexture(canvas);
    this.screenTexture.minFilter = THREE.LinearFilter;
    this.drawScreen();
    return new THREE.Mesh(
      new THREE.PlaneGeometry(2.0, 1.25),
      new THREE.MeshBasicMaterial({ map: this.screenTexture, transparent: false })
    );
  }

  private drawScreen(): void {
    const ctx = this.screenCtx;
    if (!ctx) return;
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, 256, 160);
    ctx.shadowColor = '#ff0000';
    ctx.shadowBlur = 12;
    ctx.font = 'bold 44px monospace';
    ctx.fillStyle = '#ff0000';
    ctx.fillText(this.blinkOn ? '> _' : '>', 16, 100);
    ctx.shadowBlur = 0;
    this.screenTexture.needsUpdate = true;
  }

  private build(): THREE.Group {
    const r = new THREE.Group();
    r.add(this.buildHead());
    r.add(this.buildNeck());
    r.add(this.buildBody());
    r.add(this.buildTie());
    r.add(this.buildArm(1));
    r.add(this.buildArm(-1));
    r.add(this.buildLeg(0.45));
    r.add(this.buildLeg(-0.45));
    return r;
  }

  private buildHead(): THREE.Group {
    const h = new THREE.Group();
    h.position.y = 4.1;
    h.add(this.w(new THREE.BoxGeometry(2.3, 1.6, 1.2, 1, 1, 1)));
    const s = this.createScreen();
    s.position.set(0, 0, 0.61);
    h.add(s);
    h.add((() => { const b = this.w(new THREE.BoxGeometry(2.1, 1.35, 0.05, 1, 1, 1)); b.position.set(0, 0, 0.59); return b; })());
    h.add((() => { const b = this.w(new THREE.BoxGeometry(1.8, 1.2, 0.7, 1, 1, 1)); b.position.set(0, 0, -0.95); return b; })());
    for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
      const sc = this.w(new THREE.CylinderGeometry(0.04, 0.04, 0.06, 6));
      sc.rotation.x = Math.PI / 2; sc.position.set(sx * 0.95, sy * 0.58, 0.63); h.add(sc);
    }
    const a = this.w(new THREE.CylinderGeometry(0.03, 0.03, 0.5, 4));
    a.position.set(0, 1.05, 0); h.add(a);
    const at = this.w(new THREE.SphereGeometry(0.08, 6, 6));
    at.position.set(0, 1.35, 0); h.add(at);
    return h;
  }

  private buildNeck(): THREE.Group {
    const n = new THREE.Group();
    const nc = this.w(new THREE.CylinderGeometry(0.2, 0.28, 0.8, 6));
    nc.position.y = 2.9; n.add(nc);
    for (const [y, r] of [[3.2, 0.3], [2.8, 0.32], [2.55, 0.35]] as [number, number][]) {
      const ring = this.w(new THREE.TorusGeometry(r, 0.04, 4, 8));
      ring.position.y = y; ring.rotation.x = Math.PI / 2; n.add(ring);
    }
    for (const side of [-1, 1]) {
      for (const [y, x] of [[3.05, 0.28], [2.7, 0.32]] as [number, number][]) {
        const b = this.w(new THREE.CylinderGeometry(0.06, 0.06, 0.12, 6));
        b.rotation.z = Math.PI / 2; b.position.set(side * x, y, 0); n.add(b);
      }
    }
    for (const fb of [-1, 1]) {
      const b = this.w(new THREE.CylinderGeometry(0.05, 0.05, 0.1, 6));
      b.rotation.x = Math.PI / 2; b.position.set(0, 2.9, fb * 0.25); n.add(b);
    }
    return n;
  }

  private buildBody(): THREE.Group {
    const g = new THREE.Group();
    g.position.y = 1.7;
    g.add(this.w(new THREE.BoxGeometry(1.6, 1.8, 0.8, 1, 1, 1)));
    for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
      const b = this.w(new THREE.CylinderGeometry(0.04, 0.04, 0.08, 6));
      b.rotation.x = Math.PI / 2; b.position.set(sx * 0.7, sy * 0.8, 0.42); g.add(b);
    }
    for (const side of [-1, 1]) for (let i = 0; i < 2; i++) {
      const sc = this.w(new THREE.CylinderGeometry(0.035, 0.035, 0.08, 6));
      sc.rotation.z = Math.PI / 2; sc.position.set(side * 0.82, 0.4 - i * 0.8, 0); g.add(sc);
    }
    const sm = this.w(new THREE.BoxGeometry(1.2, 0.02, 0.02));
    sm.position.set(0, 0.3, 0.41); g.add(sm);
    const belt = this.w(new THREE.BoxGeometry(1.65, 0.1, 0.85, 1, 1, 1));
    belt.position.y = -0.85; g.add(belt);
    const bk = this.w(new THREE.CylinderGeometry(0.06, 0.06, 0.06, 6));
    bk.rotation.x = Math.PI / 2; bk.position.set(0, -0.85, 0.44); g.add(bk);
    return g;
  }

  private buildTie(): THREE.Group {
    const t = new THREE.Group();
    const z = 0.52;
    const k = this.w(new THREE.BoxGeometry(0.2, 0.12, 0.1, 1, 1, 1));
    k.position.set(0, 2.42, z); t.add(k);
    const u = this.w(new THREE.CylinderGeometry(0.05, 0.16, 0.3, 4));
    u.position.set(0, 2.2, z); t.add(u);
    const b = this.w(new THREE.BoxGeometry(0.36, 0.7, 0.04, 1, 1, 1));
    b.position.set(0, 1.73, z); t.add(b);
    const tip = this.w(new THREE.ConeGeometry(0.18, 0.25, 4));
    tip.position.set(0, 1.26, z); tip.rotation.y = Math.PI / 4; tip.rotation.x = Math.PI; t.add(tip);
    for (let i = 0; i < 8; i++) {
      const s = this.w(new THREE.BoxGeometry(0.36, 0.025, 0.02));
      s.position.set(0, 2.12 - i * 0.11, z + 0.03); t.add(s);
    }
    return t;
  }

  private buildArm(side: number): THREE.Group {
    const a = new THREE.Group();
    const x = side * 1.0;
    const sh = this.w(new THREE.SphereGeometry(0.18, 6, 6));
    sh.position.set(x, 2.45, 0); a.add(sh);
    const sb = this.w(new THREE.CylinderGeometry(0.04, 0.04, 0.15, 6));
    sb.rotation.z = Math.PI / 2; sb.position.set(x + side * 0.18, 2.45, 0); a.add(sb);
    const up = this.w(new THREE.CylinderGeometry(0.1, 0.1, 0.7, 6));
    up.position.set(x, 2.0, 0); a.add(up);
    const el = this.w(new THREE.SphereGeometry(0.12, 6, 6));
    el.position.set(x, 1.6, 0); a.add(el);
    const eb = this.w(new THREE.CylinderGeometry(0.035, 0.035, 0.12, 6));
    eb.rotation.z = Math.PI / 2; eb.position.set(x + side * 0.12, 1.6, 0); a.add(eb);
    const fa = this.w(new THREE.CylinderGeometry(0.09, 0.09, 0.7, 6));
    fa.position.set(x, 1.15, 0); a.add(fa);
    const h = this.w(new THREE.BoxGeometry(0.2, 0.15, 0.15, 1, 1, 1));
    h.position.set(x, 0.72, 0); a.add(h);
    for (let i = -1; i <= 1; i++) {
      const f = this.w(new THREE.BoxGeometry(0.04, 0.12, 0.04));
      f.position.set(x + i * 0.06, 0.58, 0); a.add(f);
    }
    return a;
  }

  private buildLeg(xOff: number): THREE.Group {
    const l = new THREE.Group();
    const hip = this.w(new THREE.SphereGeometry(0.14, 6, 6));
    hip.position.set(xOff, 0.75, 0); l.add(hip);
    const th = this.w(new THREE.CylinderGeometry(0.1, 0.1, 0.6, 6));
    th.position.set(xOff, 0.38, 0); l.add(th);
    const kn = this.w(new THREE.SphereGeometry(0.12, 6, 6));
    kn.position.set(xOff, 0.03, 0); l.add(kn);
    for (const s of [-1, 1]) {
      const kb = this.w(new THREE.CylinderGeometry(0.03, 0.03, 0.1, 6));
      kb.rotation.z = Math.PI / 2; kb.position.set(xOff + s * 0.13, 0.03, 0); l.add(kb);
    }
    const sh = this.w(new THREE.CylinderGeometry(0.09, 0.1, 0.6, 6));
    sh.position.set(xOff, -0.35, 0); l.add(sh);
    const ft = this.w(new THREE.BoxGeometry(0.3, 0.12, 0.45, 1, 1, 1));
    ft.position.set(xOff, -0.72, 0.05); l.add(ft);
    return l;
  }
}
