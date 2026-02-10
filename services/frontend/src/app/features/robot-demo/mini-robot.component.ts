import {
  Component,
  ElementRef,
  ViewChild,
  AfterViewInit,
  OnDestroy,
  Input,
  ChangeDetectionStrategy,
} from "@angular/core";
import * as THREE from "three";

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

    // --- Champions Trophy Cup (tall, elegant) ---
    const cupPoints: THREE.Vector2[] = [];
    cupPoints.push(new THREE.Vector2(0.0, -0.6));
    cupPoints.push(new THREE.Vector2(0.55, -0.6));
    cupPoints.push(new THREE.Vector2(0.7, -0.4));
    cupPoints.push(new THREE.Vector2(0.8, -0.1));
    cupPoints.push(new THREE.Vector2(0.82, 0.2));
    cupPoints.push(new THREE.Vector2(0.78, 0.5));
    cupPoints.push(new THREE.Vector2(0.68, 0.75));
    cupPoints.push(new THREE.Vector2(0.55, 0.95));
    cupPoints.push(new THREE.Vector2(0.5, 1.05));
    cupPoints.push(new THREE.Vector2(0.52, 1.1));
    cupPoints.push(new THREE.Vector2(0.58, 1.12));
    cupPoints.push(new THREE.Vector2(0.58, 1.18));
    cupPoints.push(new THREE.Vector2(0.0, 1.18));
    const cup = this.w(new THREE.LatheGeometry(cupPoints, 20));
    cup.position.set(0, 0.1, 0);
    m.add(cup);

    // --- Outer rim (top lip) ---
    const rimOuter = this.w(new THREE.TorusGeometry(0.57, 0.035, 6, 20));
    rimOuter.position.set(0, 1.29, 0);
    rimOuter.rotation.x = Math.PI / 2;
    m.add(rimOuter);

    // --- Left handle (big ear) ---
    const hL = this.w(new THREE.TorusGeometry(0.45, 0.035, 8, 14, Math.PI));
    hL.position.set(-1.05, 0.55, 0);
    hL.rotation.y = Math.PI / 2;
    hL.rotation.z = -0.15;
    m.add(hL);

    // --- Right handle (big ear) ---
    const hR = this.w(new THREE.TorusGeometry(0.45, 0.035, 8, 14, Math.PI));
    hR.position.set(1.05, 0.55, 0);
    hR.rotation.y = -Math.PI / 2;
    hR.rotation.z = 0.15;
    m.add(hR);

    // --- Handle connectors (top & bottom) ---
    for (const side of [-1, 1]) {
      const cTop = this.w(new THREE.CylinderGeometry(0.04, 0.04, 0.18, 6));
      cTop.rotation.z = Math.PI / 2;
      cTop.position.set(side * 0.9, 0.9, 0);
      m.add(cTop);
      const cBot = this.w(new THREE.CylinderGeometry(0.04, 0.04, 0.18, 6));
      cBot.rotation.z = Math.PI / 2;
      cBot.position.set(side * 0.9, 0.2, 0);
      m.add(cBot);
    }

    // --- Decorative band around cup ---
    const band = this.w(new THREE.TorusGeometry(0.76, 0.025, 6, 20));
    band.position.set(0, 0.45, 0);
    band.rotation.x = Math.PI / 2;
    m.add(band);

    // --- Stem (narrow) ---
    const stem = this.w(new THREE.CylinderGeometry(0.08, 0.14, 0.4, 8));
    stem.position.set(0, -0.7, 0);
    m.add(stem);

    // --- Stem knob ---
    const knob = this.w(new THREE.SphereGeometry(0.14, 8, 6));
    knob.position.set(0, -0.55, 0);
    m.add(knob);

    // --- Base column ---
    const baseCol = this.w(new THREE.CylinderGeometry(0.2, 0.35, 0.2, 10));
    baseCol.position.set(0, -1.0, 0);
    m.add(baseCol);

    // --- Base plate ---
    const basePlate = this.w(new THREE.CylinderGeometry(0.65, 0.75, 0.1, 12));
    basePlate.position.set(0, -1.18, 0);
    m.add(basePlate);

    // --- Base bottom rim ---
    const baseRim = this.w(new THREE.TorusGeometry(0.73, 0.03, 6, 14));
    baseRim.position.set(0, -1.24, 0);
    baseRim.rotation.x = Math.PI / 2;
    m.add(baseRim);

    // --- Base top rim ---
    const baseTopRim = this.w(new THREE.TorusGeometry(0.63, 0.025, 6, 14));
    baseTopRim.position.set(0, -1.12, 0);
    baseTopRim.rotation.x = Math.PI / 2;
    m.add(baseTopRim);

    // --- Nameplate ---
    const plate = this.w(new THREE.BoxGeometry(0.45, 0.1, 0.02));
    plate.position.set(0, -1.15, 0.66);
    m.add(plate);

    return m;
  }
}
