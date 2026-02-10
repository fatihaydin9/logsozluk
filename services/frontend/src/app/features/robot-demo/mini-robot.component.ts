import * as THREE from "three";

import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  Input,
  OnDestroy,
  ViewChild,
} from "@angular/core";

@Component({
  selector: "app-mini-robot",
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div #c class="mini-robot"></div>`,
  styles: [
    `
      :host {
        display: block;
      }
      .mini-robot {
        width: 100%;
        height: 100%;
      }
    `,
  ],
})
export class MiniRobotComponent implements AfterViewInit, OnDestroy {
  @Input() size = 220;
  @ViewChild("c", { static: true }) container!: ElementRef<HTMLDivElement>;
  private renderer!: THREE.WebGLRenderer;
  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private animId = 0;
  private monitor!: THREE.Group;
  private fc = 0;

  ngAfterViewInit(): void {
    const el = this.container.nativeElement;
    el.style.width = this.size + "px";
    el.style.height = this.size + "px";

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

  private buildMonitor(): THREE.Group {
    const m = new THREE.Group();
    const seg = 10;

    // --- Cup body: wide flared top → narrow waist (V-shape like Champions League) ---
    const pts: THREE.Vector2[] = [
      new THREE.Vector2(0.18, 0),
      new THREE.Vector2(0.22, 0.15),
      new THREE.Vector2(0.3, 0.35),
      new THREE.Vector2(0.45, 0.6),
      new THREE.Vector2(0.62, 0.85),
      new THREE.Vector2(0.72, 1.0),
      new THREE.Vector2(0.75, 1.05),
      new THREE.Vector2(0.72, 1.1),
    ];
    const cup = this.w(new THREE.LatheGeometry(pts, seg));
    cup.position.set(0, -0.3, 0);
    m.add(cup);

    // --- Top rim ---
    const rim = this.w(new THREE.TorusGeometry(0.72, 0.025, 4, seg));
    rim.position.set(0, 0.8, 0);
    rim.rotation.x = Math.PI / 2;
    m.add(rim);

    // --- Double-tube side handles with joint rings ---
    for (const side of [-1, 1]) {
      // Outer handle curve
      const outer = new THREE.CubicBezierCurve3(
        new THREE.Vector3(side * 0.58, 0.1, 0),
        new THREE.Vector3(side * 1.25, 0.15, 0),
        new THREE.Vector3(side * 1.3, 0.85, 0),
        new THREE.Vector3(side * 0.68, 0.7, 0),
      );
      m.add(this.w(new THREE.TubeGeometry(outer, 16, 0.025, 4, false)));
      // Inner handle curve (parallel, slightly closer)
      const inner = new THREE.CubicBezierCurve3(
        new THREE.Vector3(side * 0.52, 0.05, 0),
        new THREE.Vector3(side * 1.1, 0.12, 0),
        new THREE.Vector3(side * 1.15, 0.8, 0),
        new THREE.Vector3(side * 0.62, 0.65, 0),
      );
      m.add(this.w(new THREE.TubeGeometry(inner, 16, 0.025, 4, false)));
      // Cross-braces connecting the two tubes
      for (const t of [0.3, 0.5, 0.7]) {
        const p1 = outer.getPoint(t);
        const p2 = inner.getPoint(t);
        const brace = new THREE.CubicBezierCurve3(p1, p1, p2, p2);
        m.add(this.w(new THREE.TubeGeometry(brace, 2, 0.015, 4, false)));
      }
      // Joint ring at lower attachment
      const lowerJoint = this.w(new THREE.TorusGeometry(0.08, 0.015, 4, 8));
      lowerJoint.position.set(side * 0.55, 0.08, 0);
      lowerJoint.rotation.y = Math.PI / 2;
      m.add(lowerJoint);
      // Joint ring at upper attachment
      const upperJoint = this.w(new THREE.TorusGeometry(0.08, 0.015, 4, 8));
      upperJoint.position.set(side * 0.65, 0.68, 0);
      upperJoint.rotation.y = Math.PI / 2;
      m.add(upperJoint);
    }

    // --- Stem ---
    const stem = this.w(new THREE.CylinderGeometry(0.06, 0.1, 0.5, 6));
    stem.position.set(0, -0.55, 0);
    m.add(stem);

    // --- Stem knob ---
    const knob = this.w(new THREE.SphereGeometry(0.1, 6, 4));
    knob.position.set(0, -0.35, 0);
    m.add(knob);

    // --- Base top tier ---
    const bt = this.w(new THREE.CylinderGeometry(0.25, 0.35, 0.12, 8));
    bt.position.set(0, -0.88, 0);
    m.add(bt);

    // --- Base bottom tier ---
    const bb = this.w(new THREE.CylinderGeometry(0.45, 0.55, 0.1, 8));
    bb.position.set(0, -1.0, 0);
    m.add(bb);

    // --- Base rim ---
    const br = this.w(new THREE.TorusGeometry(0.53, 0.02, 4, 8));
    br.position.set(0, -1.06, 0);
    br.rotation.x = Math.PI / 2;
    m.add(br);

    // --- Nameplate ---
    const plate = this.w(new THREE.BoxGeometry(0.35, 0.06, 0.01));
    plate.position.set(0, -0.95, 0.38);
    m.add(plate);

    return m;
  }
}
