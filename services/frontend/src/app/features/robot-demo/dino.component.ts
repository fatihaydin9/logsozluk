import {
  Component, ElementRef, ViewChild, AfterViewInit, OnDestroy,
  ChangeDetectionStrategy,
} from '@angular/core';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

@Component({
  selector: 'app-dino',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div #canvasContainer class="canvas"></div>`,
  styles: [`:host{display:block;width:100vw;height:100vh;overflow:hidden;background:#000}.canvas{width:100%;height:100%}`],
})
export class DinoComponent implements AfterViewInit, OnDestroy {
  @ViewChild('canvasContainer', { static: true }) container!: ElementRef<HTMLDivElement>;
  private renderer!: THREE.WebGLRenderer;
  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private controls!: OrbitControls;
  private animId = 0;
  private group!: THREE.Group;

  ngAfterViewInit(): void {
    this.initScene();
    this.group = this.build();
    this.scene.add(this.group);
    this.animate();
    window.addEventListener('resize', this.onResize);
  }
  ngOnDestroy(): void {
    cancelAnimationFrame(this.animId);
    window.removeEventListener('resize', this.onResize);
    this.controls.dispose();
    this.renderer.dispose();
  }

  private initScene(): void {
    const el = this.container.nativeElement;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x000000);
    this.camera = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, 0.1, 100);
    this.camera.position.set(0, 3, 12);
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(el.clientWidth, el.clientHeight);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    el.appendChild(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.target.set(0, 2, 0);
    this.controls.update();
  }
  private animate = (): void => {
    this.animId = requestAnimationFrame(this.animate);
    this.group.rotation.y += 0.003;
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  };
  private onResize = (): void => {
    const el = this.container.nativeElement;
    this.camera.aspect = el.clientWidth / el.clientHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(el.clientWidth, el.clientHeight);
  };

  private m(): THREE.MeshBasicMaterial {
    return new THREE.MeshBasicMaterial({ color: 0xff0000, wireframe: true });
  }
  private w(g: THREE.BufferGeometry): THREE.Mesh {
    return new THREE.Mesh(g, this.m());
  }

  private build(): THREE.Group {
    const root = new THREE.Group();

    // --- Head ---
    const head = this.w(new THREE.BoxGeometry(1.2, 0.8, 1.6, 3, 2, 3));
    head.position.set(0, 4.8, 1.8);
    head.rotation.x = 0.15;
    root.add(head);

    // Upper jaw extension
    const snout = this.w(new THREE.BoxGeometry(1.0, 0.4, 1.0, 2, 1, 2));
    snout.position.set(0, 4.65, 2.8);
    root.add(snout);

    // Lower jaw
    const jaw = this.w(new THREE.BoxGeometry(0.9, 0.3, 1.4, 2, 1, 3));
    jaw.position.set(0, 4.25, 2.3);
    root.add(jaw);

    // Teeth (upper)
    for (let i = 0; i < 5; i++) {
      const tooth = this.w(new THREE.ConeGeometry(0.06, 0.2, 4));
      tooth.position.set(-0.3 + i * 0.15, 4.35, 2.8 + (i % 2) * 0.15);
      tooth.rotation.x = Math.PI;
      root.add(tooth);
    }

    // Teeth (lower)
    for (let i = 0; i < 4; i++) {
      const tooth = this.w(new THREE.ConeGeometry(0.05, 0.15, 4));
      tooth.position.set(-0.22 + i * 0.15, 4.4, 2.6 + (i % 2) * 0.12);
      root.add(tooth);
    }

    // Eyes
    for (const side of [-1, 1]) {
      const eye = this.w(new THREE.SphereGeometry(0.15, 8, 8));
      eye.position.set(side * 0.45, 5.05, 2.2);
      root.add(eye);

      // Brow ridge
      const brow = this.w(new THREE.BoxGeometry(0.35, 0.1, 0.3, 2, 1, 1));
      brow.position.set(side * 0.45, 5.2, 2.2);
      root.add(brow);
    }

    // Head crest / ridges
    for (let i = 0; i < 3; i++) {
      const ridge = this.w(new THREE.BoxGeometry(0.15, 0.12, 0.4, 1, 1, 2));
      ridge.position.set(0, 5.3, 1.5 + i * 0.4);
      root.add(ridge);
    }

    // --- Neck ---
    const neck = this.w(new THREE.CylinderGeometry(0.4, 0.5, 1.2, 8));
    neck.position.set(0, 3.9, 1.0);
    neck.rotation.x = -0.4;
    root.add(neck);

    // --- Torso ---
    const torso = this.w(new THREE.BoxGeometry(1.6, 2.4, 2.0, 3, 4, 3));
    torso.position.set(0, 2.5, 0);
    root.add(torso);

    // Ribs hint (horizontal lines on torso)
    for (let i = 0; i < 4; i++) {
      const rib = this.w(new THREE.TorusGeometry(0.7, 0.03, 4, 12, Math.PI));
      rib.position.set(0, 3.2 - i * 0.45, 0.2);
      rib.rotation.y = Math.PI / 2;
      rib.rotation.x = Math.PI / 2;
      root.add(rib);
    }

    // --- Tiny Arms (T-Rex signature!) ---
    for (const side of [-1, 1]) {
      const shoulder = this.w(new THREE.SphereGeometry(0.15, 6, 6));
      shoulder.position.set(side * 0.85, 3.3, 0.6);
      root.add(shoulder);

      const upperArm = this.w(new THREE.CylinderGeometry(0.08, 0.07, 0.4, 6));
      upperArm.position.set(side * 0.95, 3.0, 0.7);
      upperArm.rotation.z = side * 0.3;
      root.add(upperArm);

      const forearm = this.w(new THREE.CylinderGeometry(0.06, 0.05, 0.35, 6));
      forearm.position.set(side * 1.0, 2.7, 0.85);
      forearm.rotation.x = -0.5;
      root.add(forearm);

      // Two claws
      for (let c = 0; c < 2; c++) {
        const claw = this.w(new THREE.ConeGeometry(0.03, 0.15, 4));
        claw.position.set(side * 1.0 + c * 0.06 * side, 2.48, 0.95);
        claw.rotation.x = -0.3;
        root.add(claw);
      }
    }

    // --- Legs (massive) ---
    for (const side of [-1, 1]) {
      const xOff = side * 0.55;

      // Hip
      const hip = this.w(new THREE.SphereGeometry(0.3, 8, 8));
      hip.position.set(xOff, 1.3, 0);
      root.add(hip);

      // Thigh
      const thigh = this.w(new THREE.CylinderGeometry(0.3, 0.22, 1.2, 8));
      thigh.position.set(xOff, 0.5, 0.15);
      thigh.rotation.x = 0.1;
      root.add(thigh);

      // Knee
      const knee = this.w(new THREE.SphereGeometry(0.24, 8, 8));
      knee.position.set(xOff, -0.15, 0.2);
      root.add(knee);

      // Shin (reverse joint feel)
      const shin = this.w(new THREE.CylinderGeometry(0.2, 0.15, 1.0, 8));
      shin.position.set(xOff, -0.75, 0.05);
      shin.rotation.x = -0.15;
      root.add(shin);

      // Ankle
      const ankle = this.w(new THREE.SphereGeometry(0.16, 6, 6));
      ankle.position.set(xOff, -1.3, 0);
      root.add(ankle);

      // Foot (3-toed)
      const footBase = this.w(new THREE.BoxGeometry(0.5, 0.12, 0.4, 2, 1, 1));
      footBase.position.set(xOff, -1.45, 0.15);
      root.add(footBase);

      for (let t = -1; t <= 1; t++) {
        const toe = this.w(new THREE.ConeGeometry(0.06, 0.35, 4));
        toe.position.set(xOff + t * 0.15, -1.45, 0.5);
        toe.rotation.x = Math.PI / 2;
        root.add(toe);
      }
    }

    // --- Tail (long, segmented) ---
    const tailSegs = 8;
    for (let i = 0; i < tailSegs; i++) {
      const t = i / tailSegs;
      const radius = 0.35 * (1 - t * 0.8);
      const seg = this.w(new THREE.CylinderGeometry(radius, radius * 0.85, 0.5, 6));
      const angle = t * 0.3;
      seg.position.set(0, 1.8 + i * 0.15 * Math.sin(angle), -1.0 - i * 0.55);
      seg.rotation.x = Math.PI / 2 + angle;
      root.add(seg);
    }

    // Tail spikes (top of tail)
    for (let i = 0; i < 5; i++) {
      const spike = this.w(new THREE.ConeGeometry(0.04, 0.2, 4));
      spike.position.set(0, 2.15 + i * 0.04, -1.2 - i * 0.55);
      root.add(spike);
    }

    return root;
  }
}
