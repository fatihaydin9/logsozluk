import {
  Component, ElementRef, ViewChild, AfterViewInit, OnDestroy,
  ChangeDetectionStrategy,
} from '@angular/core';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

@Component({
  selector: 'app-astronaut',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div #canvasContainer class="canvas"></div>`,
  styles: [`:host{display:block;width:100vw;height:100vh;overflow:hidden;background:#000}.canvas{width:100%;height:100%}`],
})
export class AstronautComponent implements AfterViewInit, OnDestroy {
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
    this.camera.position.set(0, 2, 10);
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

    // --- Helmet (large sphere with visor cutout feel) ---
    const helmet = this.w(new THREE.SphereGeometry(0.9, 12, 10));
    helmet.position.y = 4.0;
    root.add(helmet);

    // Visor (flattened sphere on front)
    const visor = this.w(new THREE.SphereGeometry(0.65, 10, 8, 0, Math.PI));
    visor.position.set(0, 3.95, 0.35);
    visor.rotation.y = 0;
    root.add(visor);

    // Visor rim
    const visorRim = this.w(new THREE.TorusGeometry(0.65, 0.04, 8, 16, Math.PI));
    visorRim.position.set(0, 3.95, 0.35);
    visorRim.rotation.x = Math.PI / 2;
    root.add(visorRim);

    // Light on helmet top
    const light = this.w(new THREE.CylinderGeometry(0.12, 0.12, 0.15, 8));
    light.position.set(0, 4.9, 0);
    root.add(light);

    // Neck ring
    const neckRing = this.w(new THREE.TorusGeometry(0.55, 0.08, 8, 16));
    neckRing.position.y = 3.1;
    neckRing.rotation.x = Math.PI / 2;
    root.add(neckRing);

    // --- Torso (bulky suit) ---
    const torso = this.w(new THREE.BoxGeometry(2.0, 2.2, 1.4, 3, 3, 2));
    torso.position.y = 1.8;
    root.add(torso);

    // Chest panel
    const panel = this.w(new THREE.BoxGeometry(0.8, 0.6, 0.1, 2, 2, 1));
    panel.position.set(0, 2.2, 0.75);
    root.add(panel);

    // Panel buttons
    for (let i = 0; i < 3; i++) {
      const btn = this.w(new THREE.SphereGeometry(0.06, 6, 6));
      btn.position.set(-0.2 + i * 0.2, 2.35, 0.82);
      root.add(btn);
    }

    // Suit connection rings (waist)
    const waistRing = this.w(new THREE.TorusGeometry(0.7, 0.06, 8, 16));
    waistRing.position.y = 0.7;
    waistRing.rotation.x = Math.PI / 2;
    root.add(waistRing);

    // --- Backpack (life support) ---
    const backpack = this.w(new THREE.BoxGeometry(1.4, 1.8, 0.8, 2, 3, 2));
    backpack.position.set(0, 2.0, -1.05);
    root.add(backpack);

    // Backpack top vent
    const vent = this.w(new THREE.CylinderGeometry(0.2, 0.2, 0.3, 8));
    vent.position.set(0, 3.05, -1.05);
    root.add(vent);

    // Oxygen tubes (left and right)
    for (const side of [-1, 1]) {
      const tube = this.w(new THREE.TorusGeometry(0.4, 0.05, 6, 12, Math.PI));
      tube.position.set(side * 0.5, 3.3, -0.4);
      tube.rotation.set(Math.PI / 2, side * 0.3, 0);
      root.add(tube);
    }

    // --- Arms (bulky suit arms) ---
    for (const side of [-1, 1]) {
      // Shoulder
      const shoulder = this.w(new THREE.SphereGeometry(0.3, 8, 8));
      shoulder.position.set(side * 1.3, 2.7, 0);
      root.add(shoulder);

      // Upper arm
      const upper = this.w(new THREE.CylinderGeometry(0.2, 0.18, 0.9, 8));
      upper.position.set(side * 1.3, 2.1, 0);
      root.add(upper);

      // Elbow ring
      const elbowRing = this.w(new THREE.TorusGeometry(0.2, 0.04, 6, 12));
      elbowRing.position.set(side * 1.3, 1.6, 0);
      elbowRing.rotation.x = Math.PI / 2;
      root.add(elbowRing);

      // Forearm
      const forearm = this.w(new THREE.CylinderGeometry(0.18, 0.16, 0.9, 8));
      forearm.position.set(side * 1.3, 1.05, 0);
      root.add(forearm);

      // Glove (sphere-ish hand)
      const glove = this.w(new THREE.SphereGeometry(0.22, 8, 8));
      glove.position.set(side * 1.3, 0.5, 0);
      root.add(glove);

      // Wrist ring
      const wristRing = this.w(new THREE.TorusGeometry(0.18, 0.03, 6, 12));
      wristRing.position.set(side * 1.3, 0.6, 0);
      wristRing.rotation.x = Math.PI / 2;
      root.add(wristRing);
    }

    // --- Legs ---
    for (const side of [-1, 1]) {
      const xOff = side * 0.5;

      // Upper leg
      const upper = this.w(new THREE.CylinderGeometry(0.22, 0.2, 0.8, 8));
      upper.position.set(xOff, 0.2, 0);
      root.add(upper);

      // Knee ring
      const kneeRing = this.w(new THREE.TorusGeometry(0.22, 0.04, 6, 12));
      kneeRing.position.set(xOff, -0.25, 0);
      kneeRing.rotation.x = Math.PI / 2;
      root.add(kneeRing);

      // Lower leg
      const lower = this.w(new THREE.CylinderGeometry(0.2, 0.22, 0.8, 8));
      lower.position.set(xOff, -0.7, 0);
      root.add(lower);

      // Boot
      const boot = this.w(new THREE.BoxGeometry(0.45, 0.35, 0.6, 2, 1, 2));
      boot.position.set(xOff, -1.25, 0.05);
      root.add(boot);

      // Boot sole
      const sole = this.w(new THREE.BoxGeometry(0.5, 0.08, 0.65, 2, 1, 2));
      sole.position.set(xOff, -1.44, 0.05);
      root.add(sole);
    }

    // --- Flag on back (small) ---
    const pole = this.w(new THREE.CylinderGeometry(0.02, 0.02, 1.2, 4));
    pole.position.set(0.7, 3.2, -1.0);
    root.add(pole);

    const flag = this.w(new THREE.PlaneGeometry(0.4, 0.25, 3, 2));
    flag.position.set(0.92, 3.65, -1.0);
    root.add(flag);

    return root;
  }
}
