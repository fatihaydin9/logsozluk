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

    // --- Cup bowl (lathe geometry) ---
    const cupPoints: THREE.Vector2[] = [];
    cupPoints.push(new THREE.Vector2(0.6, -0.8));
    cupPoints.push(new THREE.Vector2(0.75, -0.5));
    cupPoints.push(new THREE.Vector2(0.85, 0));
    cupPoints.push(new THREE.Vector2(0.8, 0.4));
    cupPoints.push(new THREE.Vector2(0.7, 0.7));
    cupPoints.push(new THREE.Vector2(0.65, 0.85));
    cupPoints.push(new THREE.Vector2(0.7, 0.9));
    const cup = this.w(new THREE.LatheGeometry(cupPoints, 16));
    cup.position.set(0, 0.4, 0);
    m.add(cup);

    // --- Inner rim ---
    const rim = this.w(new THREE.TorusGeometry(0.68, 0.04, 6, 16));
    rim.position.set(0, 1.3, 0);
    rim.rotation.x = Math.PI / 2;
    m.add(rim);

    // --- Left handle ---
    const handleL = this.w(new THREE.TorusGeometry(0.35, 0.04, 6, 12, Math.PI));
    handleL.position.set(-1.05, 0.65, 0);
    handleL.rotation.y = Math.PI / 2;
    m.add(handleL);

    // --- Right handle ---
    const handleR = this.w(new THREE.TorusGeometry(0.35, 0.04, 6, 12, Math.PI));
    handleR.position.set(1.05, 0.65, 0);
    handleR.rotation.y = -Math.PI / 2;
    m.add(handleR);

    // --- Stem ---
    const stem = this.w(new THREE.CylinderGeometry(0.12, 0.18, 0.5, 8));
    stem.position.set(0, -0.65, 0);
    m.add(stem);

    // --- Stem knob ---
    const knob = this.w(new THREE.SphereGeometry(0.18, 8, 6));
    knob.position.set(0, -0.55, 0);
    m.add(knob);

    // --- Base ---
    const base = this.w(new THREE.CylinderGeometry(0.7, 0.8, 0.15, 12));
    base.position.set(0, -1.0, 0);
    m.add(base);

    // --- Base bottom rim ---
    const baseRim = this.w(new THREE.TorusGeometry(0.78, 0.03, 6, 12));
    baseRim.position.set(0, -1.08, 0);
    baseRim.rotation.x = Math.PI / 2;
    m.add(baseRim);

    // --- Base top rim ---
    const baseTopRim = this.w(new THREE.TorusGeometry(0.68, 0.03, 6, 12));
    baseTopRim.position.set(0, -0.92, 0);
    baseTopRim.rotation.x = Math.PI / 2;
    m.add(baseTopRim);

    // --- Nameplate on base ---
    const plate = this.w(new THREE.BoxGeometry(0.5, 0.08, 0.04));
    plate.position.set(0, -0.95, 0.72);
    m.add(plate);

    return m;
  }
}
